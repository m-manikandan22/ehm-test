"""
stress_scenario.py — Stress scenario generator for Experiment B.

This module is the *new* scenario generator for the stress / constrained
self-healing experiment. It is *deliberately* independent of
``experiments.scenario.py`` (Experiment A) and never overwrites it.

Design constraints
------------------
1. The stress levels must be *controller-independent* — selection of
   stress level values is based on physical / operational dimensions,
   not on which controller performs best.
2. Faults must be *persistent*: a fault remains on the asset for its
   full ``duration_steps`` and is only cleared by an explicit repair
   event. This prevents the original Experiment A saturation
   (``duration_steps=1-3`` always auto-cleared before controllers
   matter).
3. Restoration must be *capacity-constrained*: tie switches have a
   finite transfer limit; line capacities and generation headroom are
   configurable. A restoration that exceeds a limit is partially
   effective (the unmet portion is recorded as
   ``unserved_restoration_mw``).
4. Critical-load competition is real: hospital / ICU / substation /
   microgrid-root assets compete for limited restoration capacity.

Output schema
-------------
``StressScenario`` extends ``Scenario`` with:
  - stress_level           : str   ("nominal" | "moderate" | "severe" | "extreme")
  - load_multiplier        : float (scales all demand)
  - generation_reserve_factor : float (scales spare feeder / generator capacity)
  - tie_capacity_factor    : float (multiplier on tie-switch transfer limit)
  - line_capacity_factor   : float (multiplier on every line's rating)
  - battery_soc_range      : (lo, hi) initial SOC window
  - renewable_factor       : float (multiplier on solar/wind)
  - weather_mode           : str   (passed through)
  - max_concurrent_faults  : int   (peak number of simultaneously-failed assets)
  - fault_duration_range   : (lo, hi) inclusive step range
  - critical_load_fraction : float (fraction of disconnected load that
                             must be restored to fully serve critical
                             loads; competition is real when
                             available_capacity < demand)
  - capacity_constraints   : dict  (explicit per-edge capacity overrides
                             in MW; applied to tie switches first)
  - repair_schedule        : list  of {timestep, target} repair events

Pairwise-deterministic
----------------------
Same seed → same scenario. Different seed → different scenario. All
randomness is sourced from a single ``random.Random(seed)`` so the
experiment is reproducible.
"""
from __future__ import annotations

import json
import os
import random as _random
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from experiments.scenario import (
    FaultEvent, Scenario, _git_commit, _software_versions,
)


# ── Stress-level vocabulary ──────────────────────────────────────────────
STRESS_NOMINAL  = "nominal"
STRESS_MODERATE = "moderate"
STRESS_SEVERE   = "severe"
STRESS_EXTREME  = "extreme"

STRESS_LEVELS: Tuple[str, ...] = (
    STRESS_NOMINAL, STRESS_MODERATE, STRESS_SEVERE, STRESS_EXTREME,
)


# ── Controller-independent per-level parameter sets ─────────────────────
#
# Each level is defined by physical / operational dimensions only.
# The numbers below are derived from the Experiment A baseline:
#   - baseline fault duration 1-3 ticks (auto-cleared before FLISR)
#   - baseline 3 faults per run, never overlapping
#   - baseline 200 ticks per run
#   - baseline single weather mode "normal"
#
# The stress benchmark must produce scenarios that *demand* different
# controller decisions, not merely stress the GPU.
#
# Ranges are derived from the simulation's 200-tick time-scale. Faults
# that last >40 ticks (~1/5 of the run) cannot be ignored; they require
# active restoration.

LEVEL_PARAMETERS: Dict[str, Dict[str, Any]] = {
    # Level 0 — nominal / reference (matches Experiment A characteristics
    # but with longer faults to ensure persistence; in the nominal-level
    # benchmark the *topology* is the same so the comparison is fair).
    STRESS_NOMINAL: {
        "fault_count": 3,
        "fault_duration_range": (3, 8),
        "max_concurrent_faults": 1,
        "load_multiplier": 1.0,
        "generation_reserve_factor": 1.0,
        "tie_capacity_factor": 1.0,
        "line_capacity_factor": 1.0,
        "battery_soc_range": (0.5, 0.9),
        "renewable_factor": 1.0,
        "weather_mode": "normal",
        "critical_load_fraction": 1.0,   # no competition at nominal
        "tie_capacity_mw": 8.0,          # default per-tie limit
        "fault_inject_probability": 1.0, # always inject scheduled faults
    },
    # Level 1 — moderate: longer faults, sometimes overlapping, reduced
    # tie capacity, critical-load competition emerges.
    STRESS_MODERATE: {
        "fault_count": 5,
        "fault_duration_range": (10, 20),
        "max_concurrent_faults": 2,
        "load_multiplier": 1.2,
        "generation_reserve_factor": 0.9,
        "tie_capacity_factor": 0.7,
        "line_capacity_factor": 0.85,
        "battery_soc_range": (0.3, 0.7),
        "renewable_factor": 0.85,
        "weather_mode": "normal",
        "critical_load_fraction": 0.7,
        "tie_capacity_mw": 5.6,
        "fault_inject_probability": 0.85,
    },
    # Level 2 — severe: high loading, multiple persistent faults, N-1
    # style contingencies, critical-load competition guaranteed.
    STRESS_SEVERE: {
        "fault_count": 8,
        "fault_duration_range": (25, 50),
        "max_concurrent_faults": 3,
        "load_multiplier": 1.5,
        "generation_reserve_factor": 0.7,
        "tie_capacity_factor": 0.4,
        "line_capacity_factor": 0.7,
        "battery_soc_range": (0.2, 0.5),
        "renewable_factor": 0.6,
        "weather_mode": "storm",
        "critical_load_fraction": 0.4,
        "tie_capacity_mw": 3.2,
        "fault_inject_probability": 0.9,
    },
    # Level 3 — extreme: peak demand, persistent N-2 faults, severely
    # limited restoration capacity. Used only if scientifically useful.
    STRESS_EXTREME: {
        "fault_count": 12,
        "fault_duration_range": (50, 100),
        "max_concurrent_faults": 4,
        "load_multiplier": 1.8,
        "generation_reserve_factor": 0.5,
        "tie_capacity_factor": 0.25,
        "line_capacity_factor": 0.55,
        "battery_soc_range": (0.1, 0.3),
        "renewable_factor": 0.4,
        "weather_mode": "storm",
        "critical_load_fraction": 0.25,
        "tie_capacity_mw": 2.0,
        "fault_inject_probability": 0.95,
    },
}


@dataclass
class StressScenarioConfig:
    """The full, controller-independent parameter set for a stress run."""

    stress_level: str
    ticks: int
    fault_count: int
    fault_duration_range: Tuple[int, int]
    max_concurrent_faults: int
    load_multiplier: float
    generation_reserve_factor: float
    tie_capacity_factor: float
    line_capacity_factor: float
    battery_soc_range: Tuple[float, float]
    renewable_factor: float
    weather_mode: str
    critical_load_fraction: float
    tie_capacity_mw: float
    fault_inject_probability: float
    seed: int
    label: str = "stress"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["fault_duration_range"] = list(self.fault_duration_range)
        d["battery_soc_range"] = list(self.battery_soc_range)
        return d


@dataclass
class StressScenario:
    """A reproducible stress scenario describing what happens to a grid."""

    seed: int
    weather_mode: str
    stress_level: str
    faults: List[FaultEvent]
    total_steps: int
    load_multiplier: float
    generation_reserve_factor: float
    tie_capacity_factor: float
    line_capacity_factor: float
    battery_soc_range: Tuple[float, float]
    renewable_factor: float
    critical_load_fraction: float
    tie_capacity_mw: float
    fault_inject_probability: float
    repair_schedule: List[Dict[str, Any]] = field(default_factory=list)
    label: str = "stress"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    software: Dict[str, str] = field(default_factory=dict)
    config: Optional[StressScenarioConfig] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "seed": self.seed,
            "weather_mode": self.weather_mode,
            "stress_level": self.stress_level,
            "faults": [f.to_dict() for f in self.faults],
            "total_steps": self.total_steps,
            "load_multiplier": self.load_multiplier,
            "generation_reserve_factor": self.generation_reserve_factor,
            "tie_capacity_factor": self.tie_capacity_factor,
            "line_capacity_factor": self.line_capacity_factor,
            "battery_soc_range": list(self.battery_soc_range),
            "renewable_factor": self.renewable_factor,
            "critical_load_fraction": self.critical_load_fraction,
            "tie_capacity_mw": self.tie_capacity_mw,
            "fault_inject_probability": self.fault_inject_probability,
            "repair_schedule": list(self.repair_schedule),
            "label": self.label,
            "created_at": self.created_at,
            "software": dict(self.software),
        }
        if self.config is not None:
            out["config"] = self.config.to_dict()
        return out


# ── Default candidate fault target ids ────────────────────────────────────
def _default_candidates() -> List[str]:
    """Faultable feeder assets in the concrete 49-node Experiment-B grid."""
    return ["P_A1", "P_A2", "P_A3", "P_B1", "P_B2", "P_B3", "P_C1", "P_C2", "P_C3"]

def make_stress_scenario(
    *,
    seed: int,
    stress_level: str,
    total_steps: int,
    config: Optional[StressScenarioConfig] = None,
    candidate_targets: Optional[List[str]] = None,
    label: Optional[str] = None,
) -> StressScenario:
    """Build a deterministic stress scenario.

    Parameters
    ----------
    seed : int
        Master RNG seed. Same seed → same scenario.
    stress_level : str
        One of STRESS_LEVELS.
    total_steps : int
        Number of simulation ticks.
    config : StressScenarioConfig, optional
        If None, the level defaults are used.
    candidate_targets : list, optional
        Override the default set of fault target ids (used for testing).
    label : str, optional
        Human-readable label.
    """
    if stress_level not in LEVEL_PARAMETERS:
        raise ValueError(
            f"Unknown stress_level {stress_level!r}; "
            f"valid: {STRESS_LEVELS}"
        )
    if config is None:
        lvl = LEVEL_PARAMETERS[stress_level]
        config = StressScenarioConfig(
            stress_level=stress_level,
            ticks=int(total_steps),
            fault_count=int(lvl["fault_count"]),
            fault_duration_range=tuple(lvl["fault_duration_range"]),  # type: ignore[arg-type]
            max_concurrent_faults=int(lvl["max_concurrent_faults"]),
            load_multiplier=float(lvl["load_multiplier"]),
            generation_reserve_factor=float(lvl["generation_reserve_factor"]),
            tie_capacity_factor=float(lvl["tie_capacity_factor"]),
            line_capacity_factor=float(lvl["line_capacity_factor"]),
            battery_soc_range=tuple(lvl["battery_soc_range"]),  # type: ignore[arg-type]
            renewable_factor=float(lvl["renewable_factor"]),
            weather_mode=str(lvl["weather_mode"]),
            critical_load_fraction=float(lvl["critical_load_fraction"]),
            tie_capacity_mw=float(lvl["tie_capacity_mw"]),
            fault_inject_probability=float(lvl["fault_inject_probability"]),
            seed=int(seed),
        )

    rng = _random.Random(int(seed))
    candidates = candidate_targets or _default_candidates()

    # ── Sample faults ────────────────────────────────────────────────────
    n_scheduled = max(1, int(config.fault_count))
    fault_dur_lo, fault_dur_hi = config.fault_duration_range
    faults: List[FaultEvent] = []
    # Spread faults across the run; allow some overlap (max_concurrent).
    earliest = max(5, int(total_steps * 0.05))
    latest   = max(earliest + 1, int(total_steps) - 1)

    for _ in range(n_scheduled):
        ts = rng.randint(earliest, latest)
        target = rng.choice(candidates)
        duration = rng.randint(
            int(fault_dur_lo),
            max(int(fault_dur_lo), int(fault_dur_hi)),
        )
        # Clamp duration so the fault doesn't outlast the run.
        if ts + duration >= int(total_steps):
            duration = max(1, int(total_steps) - ts - 1)
        faults.append(FaultEvent(
            timestep=int(ts), target=str(target),
            duration_steps=int(duration),
        ))
    faults.sort(key=lambda f: f.timestep)

    # ── Enforce ``max_concurrent_faults`` ─────────────────────────────────
    # If we have too many overlapping faults, push some later. This is
    # *not* tuning to favour any controller; it is a physical limit
    # on what the test grid can plausibly experience.
    max_concurrent = max(1, int(config.max_concurrent_faults))
    active_until = [0] * max_concurrent  # end-time of each slot
    cleaned: List[FaultEvent] = []
    for f in faults:
        # Find the earliest slot whose end-time is <= f.timestep.
        slot = min(range(max_concurrent), key=lambda i: active_until[i])
        if active_until[slot] > f.timestep:
            # Defer the fault by (active_until[slot] - f.timestep) steps.
            new_ts = int(active_until[slot])
            if new_ts >= int(total_steps) - 1:
                # Skip — no room; keeps the schedule physically feasible.
                continue
            f = FaultEvent(
                timestep=new_ts, target=f.target,
                duration_steps=f.duration_steps,
            )
        active_until[slot] = int(f.timestep) + int(f.duration_steps)
        cleaned.append(f)
    cleaned.sort(key=lambda f: f.timestep)
    faults = cleaned

    # ── Repair schedule ──────────────────────────────────────────────────
    # Repairs happen at a delayed timestep after the fault injection.
    repair_schedule: List[Dict[str, Any]] = []
    for f in faults:
        # Repair occurs at f.timestep + 2 * duration (persistent fault).
        repair_t = min(
            int(total_steps) - 1,
            int(f.timestep) + 2 * int(f.duration_steps) + 1,
        )
        repair_schedule.append({
            "timestep": int(repair_t),
            "target": str(f.target),
            "source_fault": {"timestep": int(f.timestep),
                             "target": str(f.target)},
        })

    return StressScenario(
        seed=int(seed),
        weather_mode=config.weather_mode,
        stress_level=stress_level,
        faults=faults,
        total_steps=int(total_steps),
        load_multiplier=float(config.load_multiplier),
        generation_reserve_factor=float(config.generation_reserve_factor),
        tie_capacity_factor=float(config.tie_capacity_factor),
        line_capacity_factor=float(config.line_capacity_factor),
        battery_soc_range=tuple(config.battery_soc_range),  # type: ignore[arg-type]
        renewable_factor=float(config.renewable_factor),
        critical_load_fraction=float(config.critical_load_fraction),
        tie_capacity_mw=float(config.tie_capacity_mw),
        fault_inject_probability=float(config.fault_inject_probability),
        repair_schedule=repair_schedule,
        label=label or f"seed_{seed}_{stress_level}",
        software=_software_versions(),
        config=config,
    )


# ── Physical-feasibility validator ───────────────────────────────────────
def validate_scenario_physical(scenario: StressScenario,
                               grid_node_ids: Optional[List[str]] = None,
                               min_nodes: int = 1) -> Tuple[bool, List[str]]:
    """Return (ok, list_of_issues).

    Validates that the scenario is *physically feasible* — the kind of
    sanity check a careful power-system engineer would do.
    """
    issues: List[str] = []
    if scenario.total_steps <= 0:
        issues.append("total_steps must be positive")
    if not scenario.faults:
        issues.append("faults list is empty (benchmark would saturate)")
    if not (0.0 < scenario.load_multiplier < 10.0):
        issues.append(
            f"load_multiplier={scenario.load_multiplier} out of plausible range"
        )
    if not (0.05 <= scenario.tie_capacity_factor <= 2.0):
        issues.append(
            f"tie_capacity_factor={scenario.tie_capacity_factor} out of range"
        )
    if not (0.05 <= scenario.line_capacity_factor <= 2.0):
        issues.append(
            f"line_capacity_factor={scenario.line_capacity_factor} out of range"
        )
    if scenario.tie_capacity_mw < 0.1:
        issues.append(
            f"tie_capacity_mw={scenario.tie_capacity_mw} below physical floor"
        )
    if not (0.0 < scenario.critical_load_fraction <= 1.0):
        issues.append(
            f"critical_load_fraction={scenario.critical_load_fraction} invalid"
        )
    if grid_node_ids is not None:
        valid = set(grid_node_ids)
        unknown = [f.target for f in scenario.faults
                   if f.target not in valid]
        if unknown and min_nodes > 0:
            issues.append(
                f"fault targets not present in grid: {sorted(set(unknown))[:5]}"
            )
    for f in scenario.faults:
        if f.timestep < 0:
            issues.append(f"negative fault timestep: {f.timestep}")
        if f.timestep >= scenario.total_steps:
            issues.append(
                f"fault timestep {f.timestep} >= total_steps {scenario.total_steps}"
            )
        if f.duration_steps < 1:
            issues.append(
                f"fault duration_steps must be >= 1, got {f.duration_steps}"
            )
    ok = (len(issues) == 0)
    return ok, issues


# ── Manifest writer ─────────────────────────────────────────────────────
def write_stress_manifest(path: str, *, scenarios: List[StressScenario],
                          n_runs: int, configs: List[Dict[str, Any]],
                          extra: Optional[Dict[str, Any]] = None) -> None:
    payload: Dict[str, Any] = {
        "experiment_name": "experiments.stress_scenario",
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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True, default=str)
