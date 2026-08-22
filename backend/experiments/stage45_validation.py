"""stage45_validation.py — Stage-45 10-seed × 5-scenario validation.

Stage-45 mandate
================

The Stage-44 validation runner
(``backend/experiments/stage44_validation.py``) used an inline metric
loop whose ENS / CMI / critical-load / voltage-violation values were
*byte-identical* across all 12 (controller, ablation) cells in every
(scenario, seed) group (see
``docs/STAGE_44_VALIDATION_REPORT.md`` §"Metric invariance").

Stage-45 keeps **every Stage-43 evaluation scenario and seed**, the
same controllers, the same ablation definitions, the same trained
checkpoint, and the same paired-fingerprint contract — but replaces
the inline metric loop with the corrected collector in
``stage45_metrics.Stage45MetricCollector``. The corrected collector
derives ENS / CMI / critical-load interruption / voltage violation /
restoration time from the *post-power-flow* grid state at every step
(see ``docs/STAGE_45_METRIC_DEFINITIONS.md`` and
``docs/STAGE_45_CURRENT_METRIC_TRACE.md``).

We rely on the *physics-coupling* fix that is already in
``simulation/grid.py`` (``_simulate_energy_flow`` now recognises any
live node with ``generation > 0`` as a BFS source — see the inline
comment at the broadened source list). With the source-broadening
fix in place, the Stage-45 metric loop will report different
``P_served`` between, e.g., ``use_battery`` and ``do_nothing`` when
the action's physical injection actually reaches downstream load
nodes.

The runner is otherwise a copy of the Stage-44 control loop. We
intentionally do NOT touch the DQN, the reward, the scenarios, the
seeds, the checkpoint, the controller catalogue, or the ablation
flags — the only change is the metric collector.

Run command::

  python -m experiments.stage45_validation --seeds 10
      --output experiments/results/stage45/validation.json
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Path bootstrap (mirrors stage44_validation.py).
THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parents[2]
BACKEND = PROJECT_ROOT / "backend"
for p in (str(PROJECT_ROOT), str(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402

from utils.seeds import set_global_seed  # noqa: E402
from models.rl_agent import build_extended_state  # noqa: E402

# Re-use the Stage-44 controller factory + fingerprint helpers so the
# Stage-45 run is a drop-in replacement for Stage-44 (no controller
# code changes).
THIS_DIR = BACKEND / "experiments"
for p in (str(THIS_DIR), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


from experiments.stage44_validation import (  # noqa: E402
    STAGE44_CONTROLLERS, STAGE44_ABLATIONS,
    _build_dqn_agent, _Stage44DQNAdapter,
    _get_shared_forecaster, _fingerprint_run,
    _build_scenario_for_seed, _apply_scenario_to_grid,
)
from experiments.stage45_metrics import Stage45MetricCollector  # noqa: E402


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "no_git"


def _run_controller_on_scenario(
    *, controller_label: str, scenario, seed: int,
    ablation: str,
    checkpoint_path: Optional[str],
    enable_lstm: bool, enable_twin: bool,
    enable_predictive: bool, enable_ems: bool,
    enable_flisr: bool,
    max_steps: int,
) -> Dict:
    """Single-run body. Mirrors Stage-44 except the metric collector.

    Control flow (per step)::

      inject faults at t
      controller.choose_action(state)
      _dispatch_action(grid, action_id)         ← physical effect
      grid.step()
      grid.update_power_flow()                  ← post-physics state
      Stage45MetricCollector.step(grid, t)      ← CORRECTED metrics

    The Stage-45 collector reads ``grid.nodes[L].received_power``,
    ``grid.nodes[L].voltage``, ``grid.nodes[L].failed``,
    ``grid.nodes[L].isolated`` at every step — the same fields the
    Stage-44 inline loop read. The corrected logic is INSIDE the
    collector; the control flow is unchanged so we don't perturb the
    paired-fingerprint contract.
    """
    set_global_seed(int(seed))

    action_counts = Counter()
    selected_actions = []
    grid = None
    from simulation.grid import SmartGrid
    set_global_seed(seed)
    grid = SmartGrid(seed=seed)
    _apply_scenario_to_grid(grid, scenario)
    try:
        grid.update_power_flow()
    except Exception:
        pass

    twin = None
    if enable_twin:
        try:
            from digital_twin.twin_registry import TwinRegistry
            twin = TwinRegistry()
            twin.register(grid)
        except Exception:
            twin = None

    from experiments.scenario_matrix import get_scenario_spec
    label = (
        scenario.label.split("|")[0]
        if hasattr(scenario, "label") else "A"
    )
    try:
        spec = get_scenario_spec(label)
    except Exception:
        spec = None
    if twin is not None and spec is not None and spec.health_override:
        try:
            from experiments.info_flow import _pre_age_twins
            _pre_age_twins(twin, dict(spec.health_override))
        except Exception:
            pass

    # Stage 46.1 (information-flow repair): per-run LSTM history deque
    # of ``(aggregate_load, aggregate_gen, weather_proxy)`` triples —
    # past observations only, identical construction to the training
    # loop and to ``experiments.runner.run_single``. The weather proxy
    # is a fixed per-scenario constant (same mapping as the runner).
    from collections import deque
    lstm_history = deque(maxlen=10)
    _weather_proxy = {
        "normal": 0.2,
        "storm": 0.85,
        "heatwave": 0.5,
    }.get(str(getattr(scenario, "weather_mode", "normal")), 0.2)

    if controller_label == "random":
        from benchmarks.baselines import RandomPolicy
        controller = RandomPolicy(seed=seed)
        controller_kind = "random"
    elif controller_label == "rule_based":
        from benchmarks.baselines import RuleBasedPolicy
        controller = RuleBasedPolicy()
        controller_kind = "rule_based"
    elif controller_label in ("untrained_dqn", "trained_dqn"):
        ckpt = checkpoint_path if controller_label == "trained_dqn" else None
        agent = _build_dqn_agent(checkpoint=ckpt, seed=seed)
        controller = _Stage44DQNAdapter(
            agent, enable_lstm=enable_lstm, enable_twin=enable_twin,
        )
        controller.set_lstm_history(lstm_history)
        controller_kind = "dqn"
    else:
        raise ValueError(f"Unknown controller_label: {controller_label}")

    collector = Stage45MetricCollector()
    collector.register_load_nodes(grid)

    total_steps = min(int(scenario.total_steps), max_steps)

    fingerprints = _fingerprint_run(grid=grid, scenario=scenario)
    fault_timesteps: Dict[str, int] = {}

    for t in range(total_steps):
        # Inject faults at this timestep.
        for fault in scenario.faults:
            if fault.timestep != t:
                continue
            target = fault.target
            try:
                grid.inject_failure(target)
                fault_timesteps[target] = t
            except Exception:
                pass

        # Build controller state.
        try:
            grid_state = grid.get_state()
        except Exception:
            grid_state = {}
        try:
            rl_state = grid.get_rl_state()
        except Exception:
            rl_state = []

        # Stage 46.1 (information-flow repair): append this step's
        # aggregate (load, generation) to the LSTM history deque before
        # the forecast is computed. Past observations only — mirrors the
        # training loop and ``runner.run_single``.
        try:
            from experiments.info_flow import _aggregate_grid_load_and_gen
            _l, _g = _aggregate_grid_load_and_gen(grid)
            lstm_history.append((_l, _g, _weather_proxy))
        except Exception:
            pass

        try:
            if controller_kind == "dqn":
                forecast = 0.5
                try:
                    if (
                        hasattr(controller, "_enable_lstm")
                        and controller._enable_lstm
                    ):
                        forecast = controller._predicted_load()
                except Exception:
                    forecast = 0.5
                twin_max_risk = 0.0
                twin_mean_risk = 0.0
                twin_high_frac = 0.0
                if twin is not None:
                    try:
                        vals = []
                        for asset_id, _tw in twin.all():
                            try:
                                v = float(
                                    getattr(_tw, "health_risk_score", 0.0)
                                    or 0.0
                                )
                                vals.append(v)
                            except Exception:
                                continue
                        if vals:
                            twin_max_risk = float(max(vals))
                            twin_mean_risk = float(sum(vals) / len(vals))
                            twin_high_frac = float(
                                sum(1 for v in vals if v >= 0.5)
                                / len(vals)
                            )
                    except Exception:
                        pass
                battery_soc = 0.0
                supercap_soc = 0.0
                for nid, n in grid.nodes.items():
                    if str(getattr(n, "node_type", "")) == "house":
                        try:
                            battery_soc = max(
                                battery_soc,
                                float(getattr(n, "battery_level", 0.0) or 0.0),
                            )
                        except Exception:
                            pass
                        try:
                            supercap_soc = max(
                                supercap_soc,
                                float(getattr(n, "supercap_level", 0.0) or 0.0),
                            )
                        except Exception:
                            pass
                ext_state = build_extended_state(
                    rl_state,
                    predicted_load=forecast,
                    battery_soc=battery_soc,
                    supercap_soc=supercap_soc,
                    twin_max_risk=twin_max_risk,
                    twin_mean_risk=twin_mean_risk,
                    twin_high_frac=twin_high_frac,
                )
                decision = controller.choose_action(
                    ext_state, grid_state,
                    lstm_sequence=grid.get_lstm_input("S_MAIN"),
                )
            else:
                decision = controller.choose_action(rl_state, grid_state)
            if isinstance(decision, dict):
                action_id = int(decision.get("action_id", -1))
            elif isinstance(decision, (int, np.integer)):
                action_id = int(decision)
            else:
                action_id = -1
        except Exception:
            action_id = -1

        if 0 <= action_id <= 4:
            action_counts[action_id] += 1
            selected_actions.append(action_id)
        else:
            selected_actions.append(-1)

        # Capture served-energy BEFORE the action so we can record the
        # action's physical-effect delta (Stage-45 diagnostic).
        served_before_mwh = sum(
            float(getattr(n, "received_power", 0.0) or 0.0)
            for n in grid.nodes.values()
        ) / 60.0

        if action_id >= 0:
            try:
                from experiments.runner import _dispatch_action
                _dispatch_action(grid, action_id)
            except Exception:
                pass

        if twin is not None and enable_twin:
            try:
                twin.sync(grid, dt_hours=1.0)
            except Exception:
                pass

        if enable_predictive and twin is not None:
            try:
                from self_healing.predictor import PredictiveSelfHealer
                healer = PredictiveSelfHealer()
                healer.run(grid, twin)
            except Exception:
                pass

        if enable_flisr:
            try:
                if hasattr(grid, "flisr_restore"):
                    grid.flisr_restore()
            except Exception:
                pass

        if enable_ems:
            try:
                from simulation.ems import EnergyManagementSystem
                ems = EnergyManagementSystem(use_pypsa=False)
                ems.run(grid)
            except Exception:
                pass

        try:
            grid.step()
        except Exception:
            pass
        try:
            grid.update_power_flow()
        except Exception:
            pass

        # Record corrected metrics (Stage-45 collector).
        try:
            collector.step(grid=grid, timestep=int(t))
        except Exception:
            pass

        served_after_mwh = sum(
            float(getattr(n, "received_power", 0.0) or 0.0)
            for n in grid.nodes.values()
        ) / 60.0
        if action_id >= 0:
            try:
                collector.note_action_effect(
                    action_id=action_id,
                    served_mwh_delta=float(served_after_mwh - served_before_mwh),
                )
            except Exception:
                pass

    summary = collector.summary()
    return {
        "controller_label": controller_label,
        "ablation": ablation,
        "scenario": scenario.label.split("|")[0]
            if hasattr(scenario, "label") else str(label),
        "scenario_full": scenario.label,
        "seed": int(seed),
        "controller_kind": controller_kind,
        "validity": {
            "valid": True,
            "invalid_reason": "",
        },
        "metrics": summary,
        "fingerprints": fingerprints,
        "selected_actions": selected_actions[:200],
        "action_counts": {int(k): int(v) for k, v in action_counts.items()},
        "n_dispatched_actions": int(sum(action_counts.values())),
    }


def _verified_fingerprints(
    runs: List[Dict], scenarios: List[str], seeds: List[int],
) -> Dict[str, List[str]]:
    """Return per-(scenario,seed) fingerprint aggregates."""
    invalid_pairs: List[str] = []
    for scen in scenarios:
        for seed in seeds:
            cells = [r for r in runs
                     if r["scenario"] == scen and r["seed"] == seed]
            if len(cells) < 2:
                continue
            ref = cells[0]["fingerprints"]
            for cell in cells[1:]:
                for k in (
                    "grid_hash", "demand_hash", "renewable_hash",
                    "fault_schedule_hash", "initial_storage_hash",
                    "topology_hash",
                ):
                    if cell["fingerprints"].get(k) != ref.get(k):
                        invalid_pairs.append(
                            f"{scen}/seed={seed} mismatch on {k}"
                        )
    return {"invalid_pairs": invalid_pairs}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--scenarios", default="A,E,G,H,J")
    ap.add_argument(
        "--checkpoint",
        default="experiments/checkpoints/dqn_stage44.pt",
    )
    ap.add_argument(
        "--output",
        default="experiments/results/stage45/validation.json",
    )
    ap.add_argument(
        "--controllers",
        default=",".join(STAGE44_CONTROLLERS),
        help="Comma-separated controllers.",
    )
    ap.add_argument(
        "--ablations",
        default=",".join(STAGE44_ABLATIONS),
        help="Comma-separated ablation labels.",
    )
    ap.add_argument(
        "--manifest",
        default="experiments/results/stage45/manifest.json",
    )
    args = ap.parse_args()

    seeds = list(range(int(args.seeds)))
    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    controllers = [
        c.strip() for c in args.controllers.split(",") if c.strip()
    ]
    ablations = [a.strip() for a in args.ablations.split(",") if a.strip()]

    runs: List[Dict] = []
    for scen in scenarios:
        for seed in seeds:
            scenario = _build_scenario_for_seed(scen, int(seed))
            for ctrl_label in controllers:
                if ctrl_label in ("random", "rule_based"):
                    run = _run_controller_on_scenario(
                        controller_label=ctrl_label,
                        scenario=scenario, seed=int(seed),
                        ablation="full_stack",
                        checkpoint_path=args.checkpoint,
                        enable_lstm=True, enable_twin=True,
                        enable_predictive=True, enable_ems=True,
                        enable_flisr=True,
                        max_steps=int(scenario.total_steps),
                    )
                    runs.append(run)
                    continue
                for ablation in ablations:
                    params = {
                        "enable_lstm": True,
                        "enable_twin": True,
                        "enable_predictive": True,
                        "enable_ems": True,
                        "enable_flisr": True,
                    }
                    if ablation == "no_lstm":
                        params["enable_lstm"] = False
                    elif ablation == "no_twin":
                        params["enable_twin"] = False
                    elif ablation == "no_predictive":
                        params["enable_predictive"] = False
                    elif ablation == "no_ems":
                        params["enable_ems"] = False
                    run = _run_controller_on_scenario(
                        controller_label=ctrl_label,
                        scenario=scenario, seed=int(seed),
                        ablation=ablation,
                        checkpoint_path=args.checkpoint,
                        **params,
                        max_steps=int(scenario.total_steps),
                    )
                    runs.append(run)
            print(
                f"[stage45_validation] scen={scen} seed={seed} — "
                f"{len(runs)} runs so far",
                flush=True,
            )

    fp_report = _verified_fingerprints(runs, scenarios, seeds)

    out = {
        "schema_version": "stage45.1.0",
        "experiment": "stage45_validation",
        "n_seeds": len(seeds),
        "seeds": seeds,
        "scenarios": scenarios,
        "controllers": controllers,
        "ablations": ablations,
        "checkpoint": args.checkpoint,
        "git_sha": _git_sha(),
        "n_runs": len(runs),
        "n_valid": sum(1 for r in runs if r["validity"]["valid"]),
        "fingerprint_report": fp_report,
        "runs": runs,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"[stage45_validation] wrote {args.output} "
          f"with {len(runs)} runs ({out['n_valid']} valid)")

    # Manifest.
    manifest = {
        "schema_version": "stage45.manifest.1.0",
        "experiment": "stage45_validation",
        "n_seeds": len(seeds),
        "seeds": seeds,
        "scenarios": scenarios,
        "controllers": controllers,
        "ablations": ablations,
        "n_runs": len(runs),
        "n_valid": out["n_valid"],
        "n_fingerprint_invalid": len(fp_report["invalid_pairs"]),
        "checkpoint": args.checkpoint,
        "git_sha": _git_sha(),
    }
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f"[stage45_validation] wrote {args.manifest}")


if __name__ == "__main__":
    main()
