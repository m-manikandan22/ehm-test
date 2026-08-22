"""train_scenario_generator.py — Stage-44 representative training scenarios.

Stage-43.1 (`docs/STAGE_43_1_TRAINING_DATA_AUDIT.md`,
`docs/STAGE_43_1_TWIN_TRAINING_ALIGNMENT.md`) found that the
Stage-43 DQN trained on a single distribution:

  * clean / no-fault,
  * healthy twin (``max_risk == 0``),
  * forecast stand-in (not the real LSTM),
  * storage full at start,
  * no degradation.

The trained policy collapsed to ``use_supercapacitor`` because the
network never observed any other transition structure. To make the
DQN reachable states overlap with evaluation states, the **training**
distribution must be widened — but **independently** of the
evaluation scenarios. We never copy evaluation scenarios into
training.

This module builds a ``TrainingScenario`` record that bundles the
following knobs for a single episode:

  * ``condition``             : one of NORMAL / HIGH_DEMAND /
                                LOW_RENEWABLE / GENERATION_DEFICIT /
                                STORAGE_STRESS / SINGLE_FAULT /
                                TOPOLOGY_FAULT / DEGRADED_ASSET /
                                FAULT_AND_DEGRADED.
  * ``demand_multiplier``     : scales aggregate demand.
  * ``renewable_multiplier``  : scales renewable generation.
  * ``battery_soc_init``      : initial battery SOC override.
  * ``supercap_soc_init``     : initial supercap SOC override.
  * ``health_override``       : pre-aged twin health values.
  * ``fault_plan``            : list of ``(timestep, target)`` injected
                                faults.
  * ``total_steps``           : episode length.

The training loop in ``stage44_dqn_training.py`` consumes a list of
``TrainingScenario`` records, one per episode. Sampling is done via a
deterministic sampler (``sample_training_scenarios``) so the same
master seed always produces the same sequence of conditions.

This module is **independent** of ``experiments/scenario_matrix.py``:
it does not import or reuse any evaluation-scenario definition. The
evaluation scenarios remain untouched.
"""
from __future__ import annotations

import dataclasses
from typing import Dict, List, Optional, Tuple

from utils.seeds import make_rng


# ---------------------------------------------------------------------
# Condition taxonomy (Stage-44 Repair R2)
# ---------------------------------------------------------------------

# These are *engineering conditions*, not evaluation scenarios.
# Each condition corresponds to a different operating regime the
# DQN should encounter during training so its Q-values become
# state-dependent instead of converging to one action.
CONDITIONS = (
    "NORMAL",
    "HIGH_DEMAND",
    "LOW_RENEWABLE",
    "GENERATION_DEFICIT",
    "STORAGE_STRESS",
    "SINGLE_FAULT",
    "TOPOLOGY_FAULT",
    "DEGRADED_ASSET",
    "FAULT_AND_DEGRADED",
)


@dataclasses.dataclass
class TrainingScenario:
    """One training episode specification.

    Mirrors the fields of ``experiments.scenario_matrix.ScenarioSpec``
    but is **not** derived from it; the two are intentionally
    independent.
    """

    label: str
    condition: str
    total_steps: int = 80
    demand_multiplier: float = 1.0
    renewable_multiplier: float = 1.0
    battery_soc_init: Optional[float] = None
    supercap_soc_init: Optional[float] = None
    health_override: Dict[str, float] = dataclasses.field(default_factory=dict)
    fault_plan: List[Tuple[int, str]] = dataclasses.field(default_factory=list)
    description: str = ""


# ---------------------------------------------------------------------
# Condition → parameter mapping
# ---------------------------------------------------------------------
# Each condition sets the operating regime. The mapping is *engineering
# intent*, not a reward shaping device — the reward function
# (``models/rl_agent.compute_reward``) is unchanged at this stage.

_CONDITION_PROFILE: Dict[str, Dict[str, object]] = {
    "NORMAL": {
        "demand_multiplier": 1.0,
        "renewable_multiplier": 1.0,
        "battery_soc_init": 0.8,
        "supercap_soc_init": 0.8,
        "health_override": {},
        "fault_plan": [],
    },
    "HIGH_DEMAND": {
        "demand_multiplier": 1.5,
        "renewable_multiplier": 1.0,
        "battery_soc_init": 0.7,
        "supercap_soc_init": 0.7,
        "health_override": {},
        "fault_plan": [],
    },
    "LOW_RENEWABLE": {
        "demand_multiplier": 1.0,
        "renewable_multiplier": 0.2,
        "battery_soc_init": 0.7,
        "supercap_soc_init": 0.6,
        "health_override": {},
        "fault_plan": [],
    },
    "GENERATION_DEFICIT": {
        "demand_multiplier": 1.3,
        "renewable_multiplier": 0.5,
        "battery_soc_init": 0.3,
        "supercap_soc_init": 0.5,
        "health_override": {},
        "fault_plan": [],
    },
    "STORAGE_STRESS": {
        # Both storages start near empty — exercises the
        # "no SOC available" branch of the action mask.
        "demand_multiplier": 1.2,
        "renewable_multiplier": 0.8,
        "battery_soc_init": 0.05,
        "supercap_soc_init": 0.05,
        "health_override": {},
        "fault_plan": [],
    },
    "SINGLE_FAULT": {
        "demand_multiplier": 1.0,
        "renewable_multiplier": 1.0,
        "battery_soc_init": 0.6,
        "supercap_soc_init": 0.6,
        "health_override": {},
        "fault_plan": [(40, "AUTO_PICK")],
    },
    "TOPOLOGY_FAULT": {
        # A topology-fault candidate is a pole/transformer node; the
        # actual target is chosen at apply-time from the grid.
        "demand_multiplier": 1.0,
        "renewable_multiplier": 1.0,
        "battery_soc_init": 0.6,
        "supercap_soc_init": 0.6,
        "health_override": {},
        "fault_plan": [(35, "AUTO_PICK")],
    },
    "DEGRADED_ASSET": {
        # Pre-age a non-critical pole so the twin reports risk ~0.5+.
        "demand_multiplier": 1.0,
        "renewable_multiplier": 1.0,
        "battery_soc_init": 0.7,
        "supercap_soc_init": 0.7,
        "health_override": {"POLE_PICK": 0.25},
        "fault_plan": [],
    },
    "FAULT_AND_DEGRADED": {
        "demand_multiplier": 1.0,
        "renewable_multiplier": 1.0,
        "battery_soc_init": 0.5,
        "supercap_soc_init": 0.5,
        "health_override": {"POLE_PICK": 0.2},
        "fault_plan": [(45, "POLE_PICK")],
    },
}


# ---------------------------------------------------------------------
# Candidate helpers
# ---------------------------------------------------------------------


def _healable_pole_candidates() -> List[str]:
    """Return the IDs of pole/transformer nodes that can be faulted."""
    try:
        from simulation.grid import SmartGrid
        g = SmartGrid()
    except Exception:
        return []
    return sorted(
        nid for nid, n in g.nodes.items()
        if getattr(n, "node_type", "") in {"pole", "transformer"}
        and not getattr(n, "failed", False)
    )


def _pole_candidates_for_health() -> List[str]:
    """Pole candidates for pre-ageing (same set as healable)."""
    return _healable_pole_candidates()


# ---------------------------------------------------------------------
# Scenario construction
# ---------------------------------------------------------------------


def build_training_scenario(
    *,
    seed: int,
    condition: str,
    total_steps: int = 80,
) -> TrainingScenario:
    """Construct a single ``TrainingScenario`` for ``condition``.

    ``seed`` drives the deterministic choice of:
      * fault targets for ``SINGLE_FAULT`` / ``TOPOLOGY_FAULT`` /
        ``FAULT_AND_DEGRADED`` (from the set of healable poles);
      * pole target for ``DEGRADED_ASSET`` / ``FAULT_AND_DEGRADED``
        pre-ageing.

    The output is fully deterministic given the (seed, condition)
    pair — re-running it produces a byte-identical scenario.
    """
    if condition not in _CONDITION_PROFILE:
        raise ValueError(f"Unknown condition: {condition}")
    profile = dict(_CONDITION_PROFILE[condition])
    rng = make_rng(seed * 101 + CONDITIONS.index(condition))
    poles = _healable_pole_candidates()
    pole_for_health = _pole_candidates_for_health()
    if not poles:
        poles = ["DUMMY"]
    if not pole_for_health:
        pole_for_health = ["DUMMY"]

    # Resolve AUTO_PICK fault targets.
    fault_plan: List[Tuple[int, str]] = []
    for t, target in profile.get("fault_plan", []):
        if target == "AUTO_PICK":
            target = str(rng.choice(poles))
        elif target == "POLE_PICK":
            target = str(rng.choice(pole_for_health))
        fault_plan.append((int(t), str(target)))

    # Resolve POLE_PICK in health_override.
    health_override: Dict[str, float] = {}
    for k, v in profile.get("health_override", {}).items():
        if k == "POLE_PICK":
            k = str(rng.choice(pole_for_health))
        health_override[k] = float(v)

    return TrainingScenario(
        label=f"T_{condition}_{seed}",
        condition=condition,
        total_steps=int(total_steps),
        demand_multiplier=float(profile.get("demand_multiplier", 1.0)),
        renewable_multiplier=float(profile.get("renewable_multiplier", 1.0)),
        battery_soc_init=(
            float(profile["battery_soc_init"])
            if profile.get("battery_soc_init") is not None else None
        ),
        supercap_soc_init=(
            float(profile["supercap_soc_init"])
            if profile.get("supercap_soc_init") is not None else None
        ),
        health_override=dict(health_override),
        fault_plan=list(fault_plan),
        description=(
            f"Training condition={condition}, seed={seed}, "
            f"d={profile.get('demand_multiplier', 1.0)}, "
            f"r={profile.get('renewable_multiplier', 1.0)}"
        ),
    )


def sample_training_scenarios(
    *,
    master_seed: int,
    n_episodes: int,
    total_steps: int = 80,
    mix: Optional[Dict[str, int]] = None,
) -> List[TrainingScenario]:
    """Sample a deterministic sequence of training scenarios.

    The mix defaults to a roughly uniform draw over the nine
    conditions (with a slight bias toward faults + degraded-asset
    states so the network sees the rare-but-important transitions
    more often).

    The same ``master_seed`` always yields the same sequence — that
    is the training-distribution contract.
    """
    if mix is None:
        # Roughly uniform, with a small bias toward the rarer but
        # important states (FAULT, DEGRADED_ASSET, FAULT_AND_DEGRADED,
        # STORAGE_STRESS). Each condition appears at least once per
        # ``len(CONDITIONS)`` episodes. Order matters: the rarer
        # conditions are placed FIRST so even short training budgets
        # (e.g. 4 episodes in the init audit) actually see them.
        mix = {
            "FAULT_AND_DEGRADED": 3,
            "SINGLE_FAULT":       3,
            "TOPOLOGY_FAULT":     3,
            "DEGRADED_ASSET":     3,
            "STORAGE_STRESS":     3,
            "NORMAL":             2,
            "HIGH_DEMAND":        2,
            "LOW_RENEWABLE":      2,
            "GENERATION_DEFICIT": 2,
        }

    rng = make_rng(int(master_seed))
    pool: List[str] = []
    for cond, count in mix.items():
        if cond not in CONDITIONS:
            continue
        pool.extend([cond] * int(count))
    # If the pool is shorter than n_episodes, cycle it; if longer,
    # truncate. The choice preserves order — we never *replace*
    # conditions with something else.
    if n_episodes <= len(pool):
        chosen = pool[:n_episodes]
    else:
        chosen = list(pool)
        # Cycle until we reach n_episodes.
        i = 0
        while len(chosen) < n_episodes:
            chosen.append(pool[i % len(pool)])
            i += 1

    out: List[TrainingScenario] = []
    for ep, cond in enumerate(chosen):
        # Per-episode seed = master_seed + ep * 1009 (cheap decorrelation).
        ep_seed = int(master_seed) * 1009 + ep * 31
        out.append(
            build_training_scenario(
                seed=ep_seed, condition=cond, total_steps=total_steps,
            )
        )
    return out


# ---------------------------------------------------------------------
# Convenience: apply a TrainingScenario to a SmartGrid
# ---------------------------------------------------------------------


def apply_training_scenario(grid, scenario: TrainingScenario) -> None:
    """Mutate ``grid`` to reflect ``scenario``'s initial conditions.

    Mirrors ``runner.py``'s scenario-application pattern: it sets the
    demand / renewable multipliers on the grid, scales consumer
    base-load, and writes storage SOC overrides. Twin pre-ageing and
    fault injection are **not** applied here — those are applied by
    the training loop at the appropriate timesteps so they remain
    observable in the state channel rather than silently baked in.
    """
    if scenario.demand_multiplier != 1.0 or scenario.renewable_multiplier != 1.0:
        try:
            grid.demand_multiplier = float(scenario.demand_multiplier)
            grid.renewable_multiplier = float(scenario.renewable_multiplier)
        except Exception:
            pass
        for n in grid.nodes.values():
            nt = getattr(n, "node_type", "")
            if nt in ("hospital", "industry", "hospital_icu"):
                base = float(getattr(n, "_base_load", 0.0) or 0.0)
                setattr(n, "_base_load", base * scenario.demand_multiplier)
                setattr(n, "load", base * scenario.demand_multiplier)

    if scenario.battery_soc_init is not None:
        for n in grid.nodes.values():
            nt = getattr(n, "node_type", "")
            if nt == "house" or nt == "battery":
                setattr(n, "battery_level", float(scenario.battery_soc_init))
    if scenario.supercap_soc_init is not None:
        for n in grid.nodes.values():
            nt = getattr(n, "node_type", "")
            if nt == "house" or nt == "supercap":
                setattr(n, "supercap_level", float(scenario.supercap_soc_init))
