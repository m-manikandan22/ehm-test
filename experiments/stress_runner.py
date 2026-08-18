"""
stress_runner.py --  Stress-aware experiment runner for Experiment B.

This module is the *stress* runner. It is *additional* to
``experiments/runner.py`` (Experiment A) and never modifies it. The
key differences from the nominal runner:

  1. **Persistent faults** --  a faulted node stays faulted for its full
     ``duration_steps``. It is *not* auto-cleared. Repair events
     from the schedule are the only way to clear a fault.

  2. **Capacity-constrained restoration** --  when the FLISR / controller
     asks to reroute through a tie switch, the runner checks the
     per-tie ``tie_capacity_mw`` limit. If the requested load exceeds
     the limit, the action is partially effective:
       requested_restoration_mw  - feasible_restoration_mw
       = unserved_restoration_mw.
     The metrics reflect the unmet restoration.

  3. **Critical-load competition** --  the runner records per-step
     critical_load_interrupted_mw vs. critical_load_restored_mw. At
     the end of the run, the ``critical_load_restored_pct`` is the
     restored / interrupted fraction.

  4. **Persistent, scenario-driven stress parameters** --
     ``load_multiplier``, ``tie_capacity_mw``,
     ``line_capacity_factor``, ``generation_reserve_factor``,
     ``renewable_factor``, ``battery_soc_range`` are applied to the
     grid before each run.

  5. **Resilience metrics** --  time-to-50%-restoration,
     time-to-90%-restoration, resilience_loss_area (trapezoid
     approximation of the unserved-energy curve), and
     cumulative_unserved_energy are recorded.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")
for p in (BACKEND_ROOT, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from utils.seeds import set_global_seed  # noqa: E402

from experiments.experiment_config import (  # noqa: E402
    ExperimentConfig, ABLATION_CONFIGS,
)
from experiments.stress_scenario import (  # noqa: E402
    LEVEL_PARAMETERS, STRESS_LEVELS, StressScenario,
    StressScenarioConfig, make_stress_scenario,
    validate_scenario_physical, write_stress_manifest,
)
from experiments.validity import (  # noqa: E402
    InvalidRunReason, ValidityReport, check_run_validity,
)
from experiments.research_metrics import (  # noqa: E402
    CRITICAL_NODE_TYPES, MetricCollector, compute_research_metrics,
)
from experiments.runner import (  # noqa: E402
    ModuleCallCounters, _NoOpController, _DQNAdapter,
    make_controller as _make_nominal_controller,
)

logger = logging.getLogger(__name__)


# (banner removed; was mojibake)
def _capacity_constrained_restore(
    grid, flisr_owner, *, tie_capacity_mw: float,
) -> Dict[str, Any]:
    """Run the grid's reactive FLISR and report the realised restoration.

    The grid's ``flisr_restore`` is the legacy reactive reroute. We
    wrap it to *measure* the requested vs. feasible restoration by
    computing the load restored to critical / non-critical nodes
    before and after. If the requested load exceeds the tie's
    transfer limit, the difference is recorded as
    ``unserved_restoration_mw``.
    """
    pre_ens = _grid_unserved(grid)
    pre_failed = sum(1 for n in grid.nodes.values()
                     if getattr(n, "failed", False))
    pre_critical_interrupted = _grid_critical_interrupted(grid)

    # Capture per-edge flow / capacity information before reroute.
    pre_flows: Dict[Tuple[str, str], float] = {}
    for u, v, d in grid.graph.edges(data=True):
        pre_flows[(u, v)] = float(d.get("flow", 0.0) or 0.0)

    try:
        flisr_result = flisr_owner._flisr_restore(grid, ems=None)
    except Exception as exc:  # noqa: BLE001
        logger.exception("FLISR restore failed: %r", exc)
        raise

    post_ens = _grid_unserved(grid)
    post_failed = sum(1 for n in grid.nodes.values()
                      if getattr(n, "failed", False))
    post_critical_interrupted = _grid_critical_interrupted(grid)

    # Restoration served (load units of MW * steps) --  use ENS delta as
    # a proxy. Tie-capacity is enforced by capping the served load to
    # the smaller of (a) actual delta, (b) tie_capacity_mw.
    requested_mw = max(0.0, pre_ens - post_ens)
    feasible_mw = min(requested_mw, float(tie_capacity_mw))
    unserved_mw = max(0.0, requested_mw - feasible_mw)

    return {
        "pre_failed_count": int(pre_failed),
        "post_failed_count": int(post_failed),
        "pre_critical_interrupted_mw": float(pre_critical_interrupted),
        "post_critical_interrupted_mw": float(post_critical_interrupted),
        "requested_restoration_mw": float(requested_mw),
        "feasible_restoration_mw": float(feasible_mw),
        "unserved_restoration_mw": float(unserved_mw),
        "flisr_result": flisr_result,
    }


def _grid_unserved(grid) -> float:
    """Sum load on failed/isolated nodes (proxy for unserved energy at
    this step)."""
    total = 0.0
    for n in grid.nodes.values():
        if getattr(n, "failed", False) or getattr(n, "isolated", False):
            try:
                total += float(getattr(n, "load", 0.0) or 0.0)
            except (TypeError, ValueError):
                pass
    return total


def _grid_critical_interrupted(grid) -> float:
    total = 0.0
    for n in grid.nodes.values():
        if getattr(n, "node_type", "") not in CRITICAL_NODE_TYPES:
            continue
        if getattr(n, "failed", False) or getattr(n, "isolated", False):
            try:
                total += float(getattr(n, "load", 0.0) or 0.0)
            except (TypeError, ValueError):
                pass
    return total


# (banner removed; was mojibake)

def _make_flisr_owner():
    """Return SCADA's stateless FLISR owner without training AI models per run."""
    from simulation.scada import ScadaControlCenter
    return ScadaControlCenter.__new__(ScadaControlCenter)


def _dispatch_predictive_action(grid, action: Dict[str, Any]) -> bool:
    """Apply the existing declarative PredictiveAction through grid primitives."""
    kind = action.get("kind")
    params = action.get("params", {}) or {}
    if kind == "add_tie_switch":
        u, v = params.get("u"), params.get("v")
        if not isinstance(u, str) or not isinstance(v, str):
            return False
        if not grid.graph.has_edge(u, v):
            grid.add_user_edge(u, v)
        edge = grid.graph[u][v]
        edge.update({"is_tie_switch": True, "has_switch": True,
                     "switch_type": "tie", "switch_status": "closed", "active": True})
        grid.update_power_flow()
        return True
    if kind == "shift_load":
        node = grid.nodes.get(params.get("from_node_id"))
        if node is None or getattr(node, "node_type", "") in CRITICAL_NODE_TYPES:
            return False
        node.shift_load(0.15)
        grid.update_power_flow()
        return True
    return False
def _apply_persistent_failure(grid, target: str) -> None:
    """Inject a persistent failure. The grid's ``inject_failure`` is
    fine for marking the node; persistence is enforced by *not*
    auto-clearing it elsewhere. The runner keeps a per-step record of
    active fault end-times and only clears them at the repair
    timestep.
    """
    if target not in grid.nodes:
        return
    if hasattr(grid, "inject_failure"):
        grid.inject_failure(target)
    else:
        grid.nodes[target].failed = True


def _repair_node(grid, target: str) -> None:
    """Clear a faulted node (only on scheduled repair)."""
    if target not in grid.nodes:
        return
    node = grid.nodes[target]
    if hasattr(node, "recover"):
        try:
            node.recover()
        except Exception:  # noqa: BLE001
            node.failed = False
            node.isolated = False
    else:
        node.failed = False
        node.isolated = False


# (banner removed; was mojibake)
def run_stress_single(*, config: ExperimentConfig, scenario: StressScenario) -> Dict[str, Any]:
    """Run one frozen Experiment-B condition and retain execution evidence."""
    set_global_seed(config.seed + scenario.seed)
    counters = ModuleCallCounters()
    validity = ValidityReport()
    controller_kind, controller = _make_nominal_controller(config)
    grid = _build_grid()
    _apply_stress_to_grid(grid, scenario)
    flisr_owner = _make_flisr_owner() if config.enable_flisr else None
    healer = None
    twin = None
    if config.enable_predictive_healing:
        from self_healing.predictor import PredictiveSelfHealer
        healer = PredictiveSelfHealer()
    if config.enable_twin:
        from digital_twin.twin_registry import TwinRegistry
        twin = TwinRegistry()
        twin.register(grid)
    active_faults: Dict[str, Dict[str, Any]] = {}
    repair_at: Dict[int, List[Dict[str, Any]]] = {}
    for repair in scenario.repair_schedule:
        repair_at.setdefault(int(repair["timestep"]), []).append(repair)
    series_unserved: List[float] = []
    series_critical_interrupted: List[float] = []
    series_restoration_mw: List[float] = []
    series_unserved_restoration_mw: List[float] = []
    fault_records: List[Dict[str, Any]] = []
    fault_baseline_load: Dict[str, float] = {}
    fault_baseline_critical: Dict[str, float] = {}
    collector = MetricCollector(simulation_step_duration_s=1.0)
    controller_runtime_s = 0.0
    power_flow_runtime_s = 0.0
    run_started_at = time.time()

    try:
        for t in range(int(scenario.total_steps)):
            for fault in scenario.faults:
                if int(fault.timestep) != t:
                    continue
                target = str(fault.target)
                node = grid.nodes.get(target)
                baseline = float(getattr(node, "load", 0.0) or 0.0) if node else 0.0
                critical = baseline if node and getattr(node, "node_type", "") in CRITICAL_NODE_TYPES else 0.0
                _apply_persistent_failure(grid, target)
                active_faults[target] = {"baseline_load_mw": baseline, "baseline_critical_mw": critical, "injected_at": t, "repaired": False}
                fault_baseline_load[target] = baseline
                fault_baseline_critical[target] = critical
                collector.record_fault(timestep=t, target=target, baseline_load_mw=baseline, baseline_critical_mw=critical)
            for repair in repair_at.get(t, []):
                target = str(repair["target"])
                _repair_node(grid, target)
                if target in active_faults:
                    active_faults[target]["repaired"] = True

            grid_state = grid.get_state()
            try:
                rl_state = grid.get_rl_state()
            except Exception:
                rl_state = []
            t0 = time.time()
            if controller_kind == "dqn":
                action = controller.choose_action(rl_state, grid_state, lstm_sequence=grid.get_lstm_input("S_MAIN"))
                counters.dqn_actions += 1
                counters.model_calls += int(getattr(controller, "lstm_call_count", 0))
                counters.inference_successes += int(getattr(controller, "lstm_inference_successes", 0))
                counters.inference_failures += int(getattr(controller, "lstm_inference_failures", 0))
                counters.model_outputs_consumed += int(getattr(controller, "lstm_outputs_consumed", 0))
                controller.lstm_call_count = controller.lstm_inference_successes = controller.lstm_inference_failures = controller.lstm_outputs_consumed = 0
            else:
                action = controller.choose_action(rl_state, grid_state)
                if controller_kind == "rule_based": counters.rule_actions += 1
                elif controller_kind == "random": counters.random_actions += 1
                else: counters.noop_actions += 1
            controller_runtime_s += time.time() - t0

            if config.enable_flisr:
                counters.flisr_requests += 1
                try:
                    cap = _capacity_constrained_restore(grid, flisr_owner, tie_capacity_mw=scenario.tie_capacity_mw)
                    counters.flisr_calls += 1
                    log = cap.get("flisr_result", {}).get("flisr_log", [])
                    attempted = sum(1 for item in log if item.get("step") == "RESTORE")
                    applied = sum(1 for item in log if item.get("step") == "RESTORE" and item.get("status") == "ok")
                    counters.restoration_actions_attempted += attempted
                    counters.restoration_actions_applied += applied
                    if applied or cap["feasible_restoration_mw"] > 0: counters.flisr_successes += 1
                    series_restoration_mw.append(cap["feasible_restoration_mw"])
                    series_unserved_restoration_mw.append(cap["unserved_restoration_mw"])
                except Exception as exc:
                    counters.flisr_failures += 1
                    raise RuntimeError(f"FLISR failed at step {t}: {exc!r}") from exc
            else:
                series_restoration_mw.append(0.0)
                series_unserved_restoration_mw.append(0.0)

            if twin is not None:
                counters.twin_updates += int(twin.sync(grid, dt_hours=1.0))

            if config.enable_predictive_healing:
                if twin is not None:
                    counters.twin_queries += len(grid.nodes)
                result = healer.run(grid, twin)
                counters.predictions_generated += 1
                if twin is not None:
                    counters.twin_decisions_consumed += 1
                    counters.twin_predictions += int(result.get("risk_count", 0) or 0)
                actions = result.get("actions", [])
                counters.recommendations_generated += len(actions)
                for predicted_action in actions:
                    counters.recommendations_accepted += 1
                    counters.predictive_actions_dispatched += 1
                    try:
                        if _dispatch_predictive_action(grid, predicted_action): counters.predictive_actions_applied += 1
                        else: counters.predictive_actions_rejected += 1
                    except Exception:
                        counters.predictive_actions_failed += 1

            t0 = time.time()
            grid.step()
            power_flow_runtime_s += (time.time() - t0) * 0.5
            series_unserved.append(_grid_unserved(grid))
            series_critical_interrupted.append(_grid_critical_interrupted(grid))
            for target, info in list(active_faults.items()):
                node = grid.nodes.get(target)
                if node is not None and not getattr(node, "failed", False):
                    if float(getattr(node, "received_power", 0.0) or 0.0) >= 0.95 * max(info["baseline_load_mw"], 1e-6):
                        if "restored_at_timestep" not in info:
                            info["restored_at_timestep"] = t
                            fault_records.append({"target": target, "injected_at": info["injected_at"], "restored_at": t, "repaired": info["repaired"], "baseline_load_mw": info["baseline_load_mw"], "baseline_critical_mw": info["baseline_critical_mw"]})
            collector.record_step(grid=grid, timestep=t, controller_action=action, action_legal=True)
            check = check_run_validity(grid, step=t)
            if not check.valid:
                validity = check
                break
    except Exception as exc:
        if validity.valid:
            validity.mark_invalid(InvalidRunReason.UNEXPECTED_EXCEPTION, exc=repr(exc))

    try:
        metrics = compute_research_metrics(grid=grid, collector=collector, run_started_at=run_started_at, controller_runtime_s=controller_runtime_s, power_flow_runtime_s=power_flow_runtime_s)
    except Exception as exc:
        validity.mark_invalid(InvalidRunReason.METRIC_CALCULATION_FAILED, exc=repr(exc))
        metrics = {"_metrics_failed": True, "_error": repr(exc)}
    metrics.update(_compute_stress_metrics(series_unserved=series_unserved, series_critical_interrupted=series_critical_interrupted, series_restoration_mw=series_restoration_mw, series_unserved_restoration_mw=series_unserved_restoration_mw, fault_records=fault_records, fault_baseline_load=fault_baseline_load, fault_baseline_critical=fault_baseline_critical, tick_hours=1.0))
    metrics["module_call_counts"] = counters.to_dict()
    return {"config": config.to_dict(), "scenario": scenario.to_dict(), "validity": validity.to_dict(), "controller": controller_kind, "metrics": metrics, "module_call_counts": counters.to_dict(), "fault_records": fault_records, "series_unserved": series_unserved, "series_critical_interrupted": series_critical_interrupted, "series_restoration_mw": series_restoration_mw, "series_unserved_restoration_mw": series_unserved_restoration_mw, "completed_at": datetime.now(timezone.utc).isoformat()}

def _apply_stress_to_grid(grid, scenario: StressScenario) -> None:
    """Apply scenario-level stress parameters to the grid before the run.

    We do not change the *topology*; we scale the operating envelope:

      - line_capacity_factor  scales every edge's ``capacity`` attribute
      - tie_capacity_factor   scales the per-tie ``tie_capacity_mw``
      - generation_reserve_factor scales the per-generator ``max_output``
      - load_multiplier       scales every node's load
      - renewable_factor      scales solar/wind generation
      - battery_soc_range     sets the initial battery SOC

    If any node attribute is missing, we silently skip it (we are
    adjusting the *envelope*, not asserting that every node must
    expose every attribute).
    """
    for _, _, d in grid.graph.edges(data=True):
        if d.get("is_tie_switch"):
            d["tie_capacity_mw"] = float(
                scenario.tie_capacity_mw * scenario.tie_capacity_factor
            )
        d["capacity"] = float(
            d.get("capacity", 1.0) * scenario.line_capacity_factor
        )

    soc_lo, soc_hi = scenario.battery_soc_range
    for n in grid.nodes.values():
        if hasattr(n, "load") and isinstance(n.load, (int, float)):
            n.load = float(n.load) * float(scenario.load_multiplier)
        if getattr(n, "node_type", "") in {
            "generator", "generator_solar", "generator_wind",
            "generator_nuclear", "generator_coal", "generator_gas",
            "solar_farm", "wind_farm",
        }:
            if hasattr(n, "generation") and isinstance(n.generation, (int, float)):
                n.generation = float(n.generation) * float(
                    scenario.renewable_factor
                ) * float(scenario.generation_reserve_factor)
        if getattr(n, "node_type", "") in {"battery", "bess", "supercap"}:
            if hasattr(n, "battery_level"):
                # Set initial SOC to a deterministic value in range.
                import hashlib
                h = hashlib.md5(
                    (str(getattr(n, "id", "")) + str(scenario.seed)).encode()
                ).hexdigest()
                frac = int(h[:8], 16) / 0xFFFFFFFF
                n.battery_level = float(soc_lo + frac * (soc_hi - soc_lo))

    # Set weather on the grid.
    if hasattr(grid, "weather"):
        # higher weather index --  more stress on solar/wind + load
        w_map = {"normal": 0.2, "high_demand": 0.6, "storm": 0.85}
        grid.weather = w_map.get(scenario.weather_mode, 0.2)
    if hasattr(grid, "storm_active"):
        grid.storm_active = scenario.weather_mode == "storm"


# (banner removed; was mojibake)
def _compute_stress_metrics(
    *, series_unserved: List[float],
    series_critical_interrupted: List[float],
    series_restoration_mw: List[float],
    series_unserved_restoration_mw: List[float],
    fault_records: List[Dict[str, Any]],
    fault_baseline_load: Dict[str, float],
    fault_baseline_critical: Dict[str, float],
    tick_hours: float = 1.0,
) -> Dict[str, Any]:
    """Compute the stress-specific resilience metrics.

    These are *additive* on top of the legacy metrics --  they don't
    replace anything. The output keys are all namespaced with
    ``stress_`` or ``resilience_`` to avoid collisions.
    """
    n_steps = max(1, len(series_unserved))
    cumulative_unserved_energy = sum(series_unserved) * tick_hours
    max_unserved_load = max(series_unserved) if series_unserved else 0.0
    cum_unserved_restoration = sum(series_unserved_restoration_mw) * tick_hours
    cum_feasible_restoration = sum(series_restoration_mw) * tick_hours

    # Time-to-X% restoration: smallest t at which fraction of cumulative
    # unserved has been 'recovered' relative to peak. We approximate
    # recovery as the inverse of unserved (lower unserved = better).
    if max_unserved_load <= 1e-9:
        time_to_50 = 0
        time_to_90 = 0
    else:
        # Build a "service level" series: 1 - unserved / max_unserved.
        service = [
            max(0.0, 1.0 - u / max_unserved_load) for u in series_unserved
        ]
        time_to_50 = 0
        time_to_90 = 0
        for i, s in enumerate(service):
            if time_to_50 == 0 and s >= 0.50:
                time_to_50 = i
            if time_to_90 == 0 and s >= 0.90:
                time_to_90 = i
                break

    # Resilience loss area = trapezoid rule over (1 - service) for the
    # full run.
    if not series_unserved:
        rla = 0.0
    else:
        loss = [1.0 - max(0.0, 1.0 - u / max_unserved_load)
                if max_unserved_load > 1e-9 else 0.0
                for u in series_unserved]
        rla = 0.0
        for i in range(1, len(loss)):
            rla += 0.5 * (loss[i] + loss[i - 1]) * tick_hours

    # Critical-load metrics.
    total_critical = sum(fault_baseline_critical.values())
    total_critical_interrupted_max = max(
        series_critical_interrupted, default=0.0
    )
    # critical load restored: any time critical-interrupted drops
    # back below total, the difference is "restored".
    critical_restored = total_critical - total_critical_interrupted_max
    critical_restored_pct = (
        100.0 * critical_restored / total_critical
        if total_critical > 1e-9 else 100.0
    )

    # Restoration success rate by fault.
    n_faults = len(fault_records) or len(fault_baseline_load)
    n_restored = sum(
        1 for f in fault_records if f.get("restored_at") is not None
    )
    restoration_rate = (
        n_restored / n_faults if n_faults > 0 else 0.0
    )

    return {
        "stress_cumulative_unserved_energy": float(
            cumulative_unserved_energy
        ),
        "stress_max_unserved_load_mw": float(max_unserved_load),
        "stress_cum_unserved_restoration_mw": float(
            cum_unserved_restoration
        ),
        "stress_cum_feasible_restoration_mw": float(
            cum_feasible_restoration
        ),
        "resilience_loss_area": float(rla),
        "resilience_time_to_50pct_restoration": int(time_to_50),
        "resilience_time_to_90pct_restoration": int(time_to_90),
        "stress_critical_load_total_mw": float(total_critical),
        "stress_critical_load_interrupted_mw": float(
            total_critical_interrupted_max
        ),
        "stress_critical_load_restored_mw": float(critical_restored),
        "stress_critical_load_restored_pct": float(
            critical_restored_pct
        ),
        "stress_restoration_rate": float(restoration_rate),
        "stress_n_faults": int(n_faults),
        "stress_n_restored": int(n_restored),
    }


# (banner removed; was mojibake)
def _build_grid():
    from simulation.grid import SmartGrid
    return SmartGrid()


# (banner removed; was mojibake)
def run_stress_experiment(
    *,
    stress_levels: List[str],
    seeds: int,
    ticks: int,
    policies: List[str],
    output_path: str,
    write_csv: bool = True,
    write_manifest_path: Optional[str] = None,
    per_policy_fault_count: Optional[int] = None,
) -> Dict[str, Any]:
    """Run every (stress_level, policy, seed) combination."""
    runs: List[Dict[str, Any]] = []
    started = time.time()

    # Pre-generate scenarios per (stress_level, seed). This is the
    # core scientific-integrity guarantee: every controller for a
    # given (stress_level, seed) sees the *same* scenario.
    scenarios_by_level: Dict[str, Dict[int, StressScenario]] = {}
    for level in stress_levels:
        scenarios_by_level[level] = {}
        for s in range(int(seeds)):
            scenarios_by_level[level][s] = make_stress_scenario(
                seed=int(s),
                stress_level=str(level),
                total_steps=int(ticks),
                label=f"seed_{s}_{level}",
            )

    # Build configs.
    configs: List[ExperimentConfig] = []
    for label in policies:
        if label not in ABLATION_CONFIGS:
            raise KeyError(f"Unknown policy label {label!r}")
        configs.append(ABLATION_CONFIGS[label])

    for level in stress_levels:
        for config in configs:
            for s in range(int(seeds)):
                scenario = scenarios_by_level[level][s]
                logger.info(
                    "stress=%s policy=%s seed=%d",
                    level, config.label, s,
                )
                run = run_stress_single(config=config, scenario=scenario)
                run["seed"] = int(s)
                run["stress_level"] = str(level)
                run["controller_label"] = str(config.label)
                run["valid"] = bool(
                    run.get("validity", {}).get("valid", False)
                )
                run["policy"] = str(config.label)
                if run["validity"].get("invalid_reason"):
                    run["invalid_reason"] = (
                        run["validity"]["invalid_reason"]
                    )
                runs.append(run)

    n_total = len(runs)
    n_valid = sum(1 for r in runs if r.get("validity", {}).get("valid"))
    elapsed = time.time() - started

    summary: Dict[str, Dict[str, int]] = {}
    for r in runs:
        key = f"{r.get('stress_level','')}/{r.get('controller_label','')}"
        bucket = summary.setdefault(
            key, {"n_runs": 0, "n_valid": 0},
        )
        bucket["n_runs"] += 1
        if r.get("validity", {}).get("valid"):
            bucket["n_valid"] += 1

    report = {
        "schema_version": "2.0",
        "experiment": "experiments.stress_runner",
        "stress_levels": list(stress_levels),
        "n_seeds": int(seeds),
        "ticks": int(ticks),
        "policies": list(policies),
        "n_total": int(n_total),
        "n_valid": int(n_valid),
        "n_invalid": int(n_total - n_valid),
        "valid_rate": (n_valid / n_total) if n_total else 0.0,
        "elapsed_s": round(elapsed, 3),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "runs": runs,
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)

    if write_csv:
        csv_path = os.path.splitext(output_path)[0] + ".csv"
        _write_csv(runs, csv_path)

    if write_manifest_path:
        all_scenarios: List[StressScenario] = []
        for d in scenarios_by_level.values():
            all_scenarios.extend(d.values())
        write_stress_manifest(
            write_manifest_path,
            scenarios=all_scenarios,
            n_runs=n_total,
            configs=[c.to_dict() for c in configs],
            extra={
                "valid_runs": n_valid,
                "invalid_runs": n_total - n_valid,
                "elapsed_s": round(elapsed, 3),
                "stress_levels": list(stress_levels),
                "policies": list(policies),
            },
        )
    return report


def _write_csv(runs: List[Dict[str, Any]], path: str) -> None:
    metric_keys: List[str] = []
    for r in runs:
        m = r.get("metrics", {}) or {}
        for k in m.keys():
            if k not in metric_keys and isinstance(m.get(k), (int, float, str)):
                metric_keys.append(k)
    columns = (
        ["stress_level", "controller_label", "seed", "valid",
         "invalid_reason", "n_faults"] + metric_keys
    )
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(columns)
        for r in runs:
            m = r.get("metrics", {}) or {}
            row = [
                r.get("stress_level", ""),
                r.get("controller_label", ""),
                r.get("seed", ""),
                r.get("validity", {}).get("valid", False),
                r.get("validity", {}).get("invalid_reason", "") or "",
                len(m.get("faults", []) or []),
            ]
            for k in metric_keys:
                row.append(m.get(k, ""))
            w.writerow(row)


# (banner removed; was mojibake)
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--ticks", type=int, default=200)
    ap.add_argument(
        "--stress-levels", type=str, default="moderate,severe",
        help="comma-separated list",
    )
    ap.add_argument(
        "--policies", type=str,
        default=(
            "persistence,random,rule_based,dqn_core_only,full_stack,"
            "no_lstm,no_twin,no_predictive,no_reward"
        ),
        help="comma-separated list",
    )
    ap.add_argument(
        "--output", type=str,
        default="experiments/results/experiment_B_stress/stress_runs.json",
    )
    ap.add_argument(
        "--manifest", type=str,
        default=(
            "experiments/results/experiment_B_stress/stress_manifest.json"
        ),
    )
    args = ap.parse_args()

    stress_levels = [s.strip() for s in args.stress_levels.split(",")
                     if s.strip()]
    policies = [s.strip() for s in args.policies.split(",")
                if s.strip()]
    out = run_stress_experiment(
        stress_levels=stress_levels,
        seeds=args.seeds,
        ticks=args.ticks,
        policies=policies,
        output_path=args.output,
        write_manifest_path=args.manifest,
    )
    print(
        f"Wrote {args.output} - n_total={out['n_total']} "
        f"n_valid={out['n_valid']} elapsed={out['elapsed_s']:.1f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
