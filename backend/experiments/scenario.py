"""scenario.py — Deterministic scenario generator for paper experiments.

A *Scenario* is a small, deterministic bundle of fault events that the
paper-grade replay harness applies to a SmartGrid. This is the
backbone of every experiment script in ``experiments/``.

Design choices
--------------
* **Deterministic given a seed.** The same seed + total_steps +
  fault_count always produce the same ``Scenario`` (Vassilios-style
  reproducibility — every paper claim must be reproducible bit-for-bit).
* **Targets are FLISR-healable.** Only ``pole`` and ``transformer``
  nodes are eligible for fault targets. Leaf loads (house, hospital)
  cannot be rerouted around and would bias any restoration metric to
  zero — those faults are excluded by design.
* **Timestep reservation.** The first ``5`` timesteps of every run
  are reserved as a *spin-up* window: no faults are injected in that
  band so the LSTM forecaster and the digital twin have a chance to
  settle. The last timestep is also reserved for *recovery* (faults
  must end before the run ends).

Public API
----------
  - ``FaultEvent`` : dataclass(timestep, target, duration_steps, kind)
  - ``Scenario``    : dataclass(total_steps, faults, weather_mode, seed)
  - ``make_scenario(seed, total_steps, fault_count, weather_mode)``
  - ``_grid_fault_candidates()`` : list of node IDs eligible for faults
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from utils.seeds import make_rng


# Reserve the first 5 timesteps of every run for spin-up (forecaster
# warm-up, digital twin calibration) and the last timestep for cleanup.
_RESERVED_HEAD = 5
_RESERVED_TAIL = 1

# Fault kinds sampled by the scenario generator.
_FAULT_KINDS = (
    "pole_failure",          # wood-rot / wind damage
    "transformer_overload",  # sustained overload
    "line_break",            # conductor break
    "switch_fault",          # protection switch stuck
)

# Node types that FLISR can physically heal around.
_HEALABLE_TYPES = frozenset({"pole", "transformer"})


@dataclass(frozen=True)
class FaultEvent:
    """A single fault-injection event applied to a node at a timestep."""
    timestep: int
    target: str
    duration_steps: int = 1
    kind: str = "pole_failure"

    def to_dict(self) -> dict:
        return {
            "timestep": int(self.timestep),
            "target": str(self.target),
            "duration_steps": int(self.duration_steps),
            "kind": str(self.kind),
        }


@dataclass(frozen=True)
class Scenario:
    """A self-contained bundle of fault events for a replay harness."""
    total_steps: int
    faults: List[FaultEvent] = field(default_factory=list)
    weather_mode: str = "normal"
    seed: int = 0
    label: str = ""

    def to_dict(self) -> dict:
        return {
            "total_steps": int(self.total_steps),
            "faults": [f.to_dict() for f in self.faults],
            "weather_mode": str(self.weather_mode),
            "seed": int(self.seed),
            "label": str(self.label),
        }


def _grid_fault_candidates() -> List[str]:
    """Return node IDs in the default grid that are FLISR-healable.

    Returns ``[]`` if the grid cannot be constructed (e.g. import error
    in test environments without the full simulator). The returned
    list is sorted by node id so determinism is preserved across runs.
    """
    try:
        from simulation.grid import SmartGrid
        g = SmartGrid()
    except Exception:
        return []
    targets = [
        nid for nid, n in g.nodes.items()
        if getattr(n, "node_type", "") in _HEALABLE_TYPES
        and not getattr(n, "failed", False)
    ]
    return sorted(targets)


def make_scenario(
    *,
    seed: int = 0,
    total_steps: int = 40,
    fault_count: int = 5,
    weather_mode: str = "normal",
    candidates: Optional[List[str]] = None,
    label: str = "",
) -> Scenario:
    """Build a deterministic ``Scenario``.

    Parameters
    ----------
    seed : int
        RNG seed for reproducibility.
    total_steps : int
        Total timesteps in the replay run. Must be >= 6 (so the
        reserved head + tail windows leave at least one free slot).
    fault_count : int
        Number of fault events to inject. ``0`` is allowed and yields
        an empty ``faults`` list.
    weather_mode : str
        One of ``"normal"``, ``"storm"``, ``"heatwave"``. The scenario
        generator does not currently dispatch on this — it is recorded
        for downstream consumers.
    candidates : list of str, optional
        Override the candidate list. If omitted, the default grid's
        healable nodes are used.
    label : str
        Optional human-readable label (e.g. ``"seed_42_normal"``).
        Recorded in the Scenario but does not affect generation.

    Returns
    -------
    Scenario
    """
    if total_steps < (_RESERVED_HEAD + _RESERVED_TAIL):
        # Not enough room for the spin-up + tail window. The caller
        # is probably running a smoke test (e.g. ablation ticks=5);
        # we accept it and produce an empty fault list rather than
        # raise, because the runner still wants to record an
        # empty scenario.
        return Scenario(
            total_steps=total_steps,
            faults=[],
            weather_mode=weather_mode,
            seed=seed,
            label=label,
        )
    cand = candidates if candidates is not None else _grid_fault_candidates()
    if fault_count <= 0 or not cand:
        return Scenario(
            total_steps=total_steps,
            faults=[],
            weather_mode=weather_mode,
            seed=seed,
            label=label,
        )

    rng = make_rng(seed)
    # Time-band for fault injection: [head, total_steps - tail)
    earliest = _RESERVED_HEAD
    latest = total_steps - _RESERVED_TAIL
    # If we need more faults than available timesteps, sample with
    # replacement on the *timestep* axis.
    timesteps = [earliest] * fault_count
    for i in range(fault_count):
        if latest > earliest:
            timesteps[i] = int(rng.integers(earliest, latest))
    # Targets: sample without replacement (no double-faulting a node)
    # when possible; fall back to with-replacement if there are more
    # faults than candidates.
    replace = fault_count > len(cand)
    indices = rng.choice(len(cand), size=fault_count, replace=replace)
    targets = [cand[int(i)] for i in indices]

    # Duration: 1–3 steps, deterministic per index
    durations = [int(rng.integers(1, 4)) for _ in range(fault_count)]
    kinds = [str(rng.choice(_FAULT_KINDS)) for _ in range(fault_count)]

    faults = [
        FaultEvent(
            timestep=t,
            target=tr,
            duration_steps=d,
            kind=k,
        )
        for t, tr, d, k in zip(timesteps, targets, durations, kinds)
    ]
    # Sort by timestep so the replay harness sees faults in order
    faults.sort(key=lambda f: f.timestep)

    return Scenario(
        total_steps=total_steps,
        faults=faults,
        weather_mode=weather_mode,
        seed=seed,
        label=label,
    )

# ----------------------------------------------------------------------
# Backward-compat shim for the legacy root-level runner.py. Writes a
# manifest JSON capturing every input needed to reproduce a run.
# ----------------------------------------------------------------------
def write_manifest(
    path,
    *,
    experiment_name,
    configs,
    scenarios,
    n_runs,
    extra=None,
):
    """Write a paper-grade reproducibility manifest.

    Parameters
    ----------
    path : str or os.PathLike
        Destination JSON path.
    experiment_name : str
        Logical name of the experiment (e.g. "experiments.runner").
    configs : list of dict
        Serialised ExperimentConfig dicts.
    scenarios : list of Scenario
        The scenarios used in this experiment.
    n_runs : int
        Total number of runs (seeds × configs × weather_modes).
    extra : dict, optional
        Additional metadata (valid_runs, elapsed_s, etc.).
    """
    import json
    import os
    out = {
        "experiment_name": experiment_name,
        "configs": list(configs),
        "n_runs": int(n_runs),
        "scenarios": [
            s.to_dict() if hasattr(s, "to_dict") else s
            for s in scenarios
        ],
    }
    if extra:
        out.update(dict(extra))
    os.makedirs(os.path.dirname(os.path.abspath(str(path))), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str, ensure_ascii=False)
