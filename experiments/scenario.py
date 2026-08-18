"""
scenario.py — Deterministic scenario generator for fair baseline comparison.

Why this exists
---------------
A research-grade experiment must ensure that every controller (random,
rule-based, DQN-only, full EHM) faces *identical* conditions for a
given seed. Previously, each policy ran with its own independent RNG,
so the comparison was contaminated by different fault locations and
different load perturbations.

This module fixes that by separating:

  - **Scenario generation** — deterministic from ``seed``. Produces
    a ``Scenario`` object containing a fault schedule, a weather mode,
    and a list of fault timestamps.
  - **Scenario replay** — the runner calls ``Scenario.replay()`` to
    inject faults at the pre-determined timesteps into a fresh
    ``SmartGrid``. Every controller receives the same fault at the
    same timestep.

The ``Scenario`` object also captures reproducibility metadata (git
commit if available, library versions, weather mode) so the experiment
manifest can point to the exact inputs.
"""
from __future__ import annotations

import json
import os
import platform
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


@dataclass
class FaultEvent:
    """A single fault event to be replayed during a scenario run.

    Attributes
    ----------
    timestep : int
        Timestep at which to inject the fault.
    target : str
        Node-id to fail (e.g. ``"H12"``).
    duration_steps : int
        How long the fault persists before it is healed (default 1).
    """

    timestep: int
    target: str
    duration_steps: int = 1

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class Scenario:
    """A reproducible scenario describing what happens to a SmartGrid.

    Attributes
    ----------
    seed : int
        Seed that produced this scenario. Same seed → identical
        scenario.
    weather_mode : str
        ``"normal"``, ``"high_demand"``, or ``"storm"``. The runner
        applies the matching weather profile to the grid.
    faults : List[FaultEvent]
        Pre-determined list of faults to inject. Each controller sees
        exactly this list.
    total_steps : int
        Total number of simulation steps in this scenario.
    label : str
        Human-readable label.
    created_at : str
        ISO-8601 UTC timestamp at scenario creation.
    software : Dict[str, str]
        Library versions recorded for reproducibility.
    """

    seed: int
    weather_mode: str
    faults: List[FaultEvent]
    total_steps: int
    label: str = "default"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    software: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        out = asdict(self)
        out["faults"] = [f.to_dict() for f in self.faults]
        return out

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------

    def replay(self, grid, *, on_fault=None) -> int:
        """Replay the scenario onto a fresh grid.

        The ``on_fault`` callback (if given) is invoked once per fault
        after the grid has registered the failure. The caller uses this
        hook to record fault timestamps for restoration-time tracking.

        Returns the number of faults successfully injected.
        """
        n_injected = 0
        for fault in self.faults:
            if fault.timestep >= self.total_steps:
                continue
            try:
                grid.inject_failure(fault.target)
            except Exception:  # noqa: BLE001 - propagate via exception type
                raise
            n_injected += 1
            if on_fault is not None:
                try:
                    on_fault(fault)
                except Exception:  # noqa: BLE001
                    raise
        return n_injected


# ── Library-version snapshot ─────────────────────────────────────────────
def _software_versions() -> Dict[str, str]:
    versions = {
        "python":  f"{sys.version_info.major}.{sys.version_info.minor}"
                   f".{sys.version_info.micro}",
        "platform": platform.platform(),
    }
    try:
        import numpy as _np
        versions["numpy"] = _np.__version__
    except ImportError:
        versions["numpy"] = "missing"
    try:
        import torch as _torch
        versions["torch"] = _torch.__version__
        versions["cuda"] = "available" if _torch.cuda.is_available() else "unavailable"
    except ImportError:
        versions["torch"] = "missing"
    try:
        import networkx as _nx
        versions["networkx"] = _nx.__version__
    except ImportError:
        versions["networkx"] = "missing"
    try:
        import pandapower as _pp
        versions["pandapower"] = _pp.__version__
    except ImportError:
        versions["pandapower"] = "missing"
    return versions


def _git_commit() -> str:
    """Return the current git HEAD commit if available, else 'unknown'."""
    try:
        import subprocess  # noqa: PLC0415 - local import
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return out.decode("ascii", errors="ignore").strip()[:40]
    except Exception:  # noqa: BLE001
        return "unknown"


# ── Deterministic scenario factory ───────────────────────────────────────
_SCENARIO_GRID_CACHE = None


def _grid_fault_candidates() -> List[str]:
    """Return real FLISR-operable node ids from the default 49-node grid.

    Only nodes whose failure actually disconnects downstream load AND that
    reactive FLISR can physically heal are used: main-feeder distribution
    poles (``P_*``) and transformers (``T_*``). These are the assets
    protected by sectionalizing/reclosing devices. House / leaf loads and
    lateral poles are excluded because a failure there cannot be rerouted
    around, which would bias restoration metrics toward zero for every
    policy. The grid is built once and cached so repeated scenario
    generation stays cheap and deterministic.
    """
    global _SCENARIO_GRID_CACHE
    if _SCENARIO_GRID_CACHE is None:
        from simulation.grid import SmartGrid
        _SCENARIO_GRID_CACHE = SmartGrid()
    return sorted(
        nid for nid, n in _SCENARIO_GRID_CACHE.nodes.items()
        if getattr(n, "node_type", "") in ("pole", "transformer")
        and not nid.startswith("L")
        and not getattr(n, "failed", False)
    )


def make_scenario(
    *,
    seed: int,
    total_steps: int,
    fault_count: int,
    weather_mode: str = "normal",
    label: str = "default",
) -> Scenario:
    """Build a deterministic ``Scenario`` from a seed.

    Same seed → same fault list. Different seed → different fault
    list. The faults are sampled from the set of node ids actually
    present in the default 49-node SmartGrid (distribution poles and
    transformers) so any controller can replay them on a real grid.
    """
    import random as _random
    rng = _random.Random(int(seed))

    candidates = _grid_fault_candidates()
    if not candidates:
        # Safety fallback if the grid is unavailable: never invent
        # synthetic ids the runner cannot inject.
        candidates = ["S_MAIN"]

    faults: List[FaultEvent] = []
    # Spread the faults across the run; keep the first fault after
    # step 5 to give controllers a chance to settle.
    if fault_count <= 0 or total_steps <= 6:
        fault_count = 0
    for _ in range(int(fault_count)):
        step = rng.randint(5, max(5, total_steps - 2))
        target = rng.choice(candidates)
        duration = rng.randint(1, 3)
        faults.append(FaultEvent(
            timestep=step, target=target, duration_steps=duration,
        ))
    faults.sort(key=lambda f: f.timestep)

    return Scenario(
        seed=int(seed),
        weather_mode=weather_mode,
        faults=faults,
        total_steps=int(total_steps),
        label=label,
        software=_software_versions(),
    )


# ── Manifest writer ─────────────────────────────────────────────────────
def write_manifest(
    path: str,
    *,
    experiment_name: str,
    configs: List[dict],
    scenarios: List[Scenario],
    n_runs: int,
    extra: Optional[Dict[str, object]] = None,
) -> None:
    """Write a manifest describing the entire experiment to ``path``.

    The manifest captures inputs enough to reproduce the run later:
      - experiment name, timestamp, git commit
      - every configuration used
      - every scenario used (fault list + weather mode)
      - python / library versions
      - total run count
    """
    payload = {
        "experiment_name": experiment_name,
        "date": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "n_runs": int(n_runs),
        "configs": configs,
        "scenarios": [s.to_dict() for s in scenarios],
        "software": _software_versions(),
    }
    if extra:
        payload.update(extra)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)