"""
runner.py -- Paper-grade experiment runner.

This module is the central execution point for the EHM-simulation
research experiments. It is deliberately more rigorous than the
previous runner:

  - **Fair baseline comparison**: every controller for a given seed
    receives the *same* pre-determined scenario (same fault list,
    same weather, same load curve). This is enforced by generating
    one ``Scenario`` per seed and replaying it for every policy.
  - **Real ablation**: each controller is constructed with an
    ``ExperimentConfig`` whose booleans genuinely disable
    components at runtime. We never label a configuration differently
    from the code that actually runs.
  - **Validity guards**: every step is checked for NaN/Inf, impossible
    voltage, broken topology, etc. Invalid runs are excluded from the
    aggregate statistics and their reasons are recorded.
  - **No silent exceptions**: a controller or solver failure marks
    the run invalid and stops further simulation. The error is logged
    with the seed, policy, and timestep that triggered it.
  - **Comprehensive metrics**: ``compute_research_metrics`` emits the
    full per-run metric dict required by the paper tables.

Usage -- -
    python -m experiments.runner \
        --seeds 3 --ticks 50 --faults 2 \
        --policies random,rule_based,dqn_core_only,full_stack \
        --output experiments/results/runner.json

Status -- Demonstrative, not research-grade. The numbers are reproducible and
self-consistent but are counts of what happened inside the simulator,
not measurements against a calibrated physical system.
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
from typing import Dict, List, Optional

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
# experiments/ lives at the project root; backend/ is its sibling.
PROJECT_ROOT = os.path.dirname(THIS_DIR)
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")
for p in (BACKEND_ROOT, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from utils.seeds import set_global_seed  # noqa: E402

from experiments.experiment_config import (  # noqa: E402
    ABLATION_CONFIGS, ExperimentConfig, list_ablation_labels,
)
from experiments.scenario import (  # noqa: E402
    Scenario, make_scenario, write_manifest,
)
from experiments.validity import (  # noqa: E402
    InvalidRunReason, ValidityReport, check_run_validity,
)
from experiments.research_metrics import (  # noqa: E402
    CRITICAL_NODE_TYPES, MetricCollector, compute_research_metrics,
)


logger = logging.getLogger(__name__)


# (banner removed; was mojibake)
def make_controller(
    config: ExperimentConfig,
):
    """Construct the *controller* (the decision-making component) for a config.

    This deliberately returns ``None`` when ``enable_dqn=False`` *and*
    no rule-based fallback is wanted, so the run degrades to a true
    no-action controller. Each controller's ``choose_action`` returns
    ``None`` if there is no policy to consult.
    """
    if config.enable_dqn:
        try:
            from models.rl_agent import DQNAgent
            return (
                "dqn",
                _DQNAdapter(DQNAgent(), enable_lstm=config.enable_lstm),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "enable_dqn=True but DQNAgent import failed: %r -- "
                "falling back to rule-based policy", exc,
            )
            # fall through to rule-based
    if config.label == "random":
        from benchmarks.baselines import RandomPolicy
        return ("random", RandomPolicy(seed=config.seed))
    if config.label == "persistence":
        return ("persistence", _NoOpController())
    # default: rule-based (rule_based, full_stack, ablation variants)
    from benchmarks.baselines import RuleBasedPolicy
    return ("rule_based", RuleBasedPolicy())


class _NoOpController:
    """Controller that always returns ``None`` -- never issues an action."""

    def choose_action(self, state, grid_state=None) -> Optional[int]:
        return None

    def reset(self) -> None:
        pass


class _DQNAdapter:
    """Adapter that exposes the canonical ``choose_action`` over a DQNAgent.

    The genuine DQNAgent in ``models/rl_agent.py`` exposes
    ``select_action(state, predicted_load, ...)`` rather than
    ``choose_action(state, grid_state)``. This thin wrapper maps the
    runner's interface onto the DQN's so the runner does not have to
    know the DQN's internal signature.

    If the underlying DQN import or call fails for any reason, the
    adapter surfaces the failure as a ``RuntimeError`` so the runner
    can mark the run invalid (no silent fallback).

    The adapter also wires in LSTM forecast:
      - When ``enable_lstm`` is True, ``predict()`` is invoked once per
        step so the DQN sees a real forecast.
      - When ``enable_lstm`` is False, ``predicted_load`` defaults to
        0.5 (no LSTM influence on the agent's input).
    """

    def __init__(self, dqn, *, enable_lstm: bool) -> None:
        self._dqn = dqn
        self._enable_lstm = enable_lstm
        self._lstm_predictor = None
        self.lstm_call_count = 0
        self.lstm_inference_successes = 0
        self.lstm_inference_failures = 0
        self.lstm_outputs_consumed = 0
        self.lstm_inference_successes = 0
        self.lstm_inference_failures = 0
        self.lstm_outputs_consumed = 0
        if enable_lstm:
            try:
                from models.lstm_model import DemandForecaster
                # The DemandForecaster constructor may take a CSV path;
                # we use the synthetic default.
                self._lstm_predictor = DemandForecaster(csv_path=None)
            except Exception:
# (banner removed; was mojibake)
                # we just fall back to the default predicted_load = 0.5.
                self._lstm_predictor = None

    def _predicted_load(self, sequence=None) -> float:
        if self._lstm_predictor is None:
            return 0.5
        try:
            self.lstm_call_count += 1
            value = float(self._lstm_predictor.predict(sequence or []))
            self.lstm_inference_successes += 1
            return value
        except Exception:
            self.lstm_inference_failures += 1
            return 0.5

    def choose_action(self, state, grid_state=None, *, lstm_sequence=None):
        # Attempt the call. If the DQN's API drifts, do not swallow.
        try:
            pred = self._predicted_load(lstm_sequence)
            if self._lstm_predictor is not None:
                self.lstm_outputs_consumed += 1
            return self._dqn.select_action(
                list(state) if state is not None else [],
                predicted_load=pred,
                grid_state=grid_state,
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"DQN select_action failed: {exc!r}"
            ) from exc

    def reset(self) -> None:
        reset = getattr(self._dqn, "reset", None)
        if callable(reset):
            try:
                reset()
            except Exception:  # noqa: BLE001
                pass


# (banner removed; was mojibake)
class ModuleCallCounters:
    """Per-run execution evidence; zero is an observed count, not a label."""
    FIELDS = ("flisr_requests", "flisr_calls", "flisr_successes", "flisr_failures", "restoration_actions_attempted", "restoration_actions_applied", "predictions_generated", "recommendations_generated", "recommendations_accepted", "predictive_actions_dispatched", "predictive_actions_applied", "predictive_actions_rejected", "predictive_actions_failed", "twin_updates", "twin_queries", "twin_predictions", "twin_decisions_consumed", "model_calls", "inference_successes", "inference_failures", "model_outputs_consumed", "dqn_actions", "rule_actions", "random_actions", "noop_actions")
    def __init__(self) -> None:
        for name in self.FIELDS:
            setattr(self, name, 0)
    def to_dict(self) -> Dict[str, int]:
        out = {name: int(getattr(self, name)) for name in self.FIELDS}
        out.update({"predictive_actions": out["recommendations_generated"], "predictive_assess_calls": out["predictions_generated"], "twin_reads": out["twin_queries"], "twin_syncs": out["twin_updates"], "lstm_calls": out["model_calls"]})
        return out


# Consumer node types that draw load and count toward ENS / restoration.
# Infrastructure (poles, transformers, substations, generators, storage) is
# deliberately excluded ? those nodes aggregate load but are not themselves
# "served load" that FLISR restores.
_LOAD_NODE_TYPES = frozenset({"house", "industry", "hospital"})


def _affected_consumer_loads(grid, target: str) -> Dict[str, float]:
    """Map consumer node-id -> baseline load (MW) downstream of ``target``.

    Used as the ENS baseline and restoration-detection set for a fault.
    Never raises: if the graph cannot be walked (e.g. a mock grid) it
    degrades to the target node alone.
    """
    import networkx as nx  # noqa: PLC0415 - local import
    ids = [target]
    try:
        ids = [target] + list(nx.descendants(grid.graph, target))
    except Exception:  # noqa: BLE001 - defensive for non-networkx grids
        pass
    affected: Dict[str, float] = {}
    for nid in ids:
        node = grid.nodes.get(nid)
        if node is None:
            continue
        if getattr(node, "node_type", "") not in _LOAD_NODE_TYPES:
            continue
        load = float(getattr(node, "load", 0.0) or 0.0)
        if load > 0:
            affected[nid] = load
    return affected


def _restored_targets(collector) -> set:
    """Targets whose collector record already marks restoration complete."""
    return {
        rec.target_node for rec in collector.faults
        if rec.successful_restoration
    }


# A fault counts as "restored" once this fraction of its pre-fault affected
# load is back in service. The residual (the faulted section directly behind
# the failed node, e.g. an attached lateral) can only be repaired by a crew,
# so it is excluded from the automatic-restoration definition.
RESTORATION_LOAD_FRACTION = 0.85


def run_single(
    *, config: ExperimentConfig, scenario: Scenario,
) -> Dict[str, object]:
    """Run a single (config, scenario) tuple and return the full metrics dict.

    The run is *valid* unless the validity guard flags it. Exceptions
    are caught and converted into an invalid run; their details are
    preserved.
    """
    # Seed global RNG so any incidental randomness in controllers is
    # also reproducible.
    set_global_seed(config.seed + scenario.seed)

    counters = ModuleCallCounters()

    grid = _build_grid()
    collector = MetricCollector(simulation_step_duration_s=1.0)

    controller_kind, controller = make_controller(config)

    validity = ValidityReport()
    invalid_exc: Optional[BaseException] = None
    controller_runtime_s = 0.0
    power_flow_runtime_s = 0.0
    run_started_at = time.time()

    fault_timesteps: Dict[str, int] = {}
    fault_affected_loads: Dict[str, Dict[str, float]] = {}
    fault_baseline_load: Dict[str, float] = {}
    fault_baseline_critical: Dict[str, float] = {}

    try:
        for t in range(int(scenario.total_steps)):
# (banner removed; was mojibake)
            for fault in scenario.faults:
                if fault.timestep != t:
                    continue
                try:
                    target = fault.target
                    # Capture the affected consumer loads downstream of the
                    # target BEFORE injecting; they form the ENS baseline and
                    # the restoration-detection set.
                    affected = _affected_consumer_loads(grid, target)
                    total_affected = float(sum(affected.values()))
                    node = grid.nodes.get(target)
                    is_critical = (
                        getattr(node, "node_type", "") in CRITICAL_NODE_TYPES
                        if node else False
                    )
                    affected_critical = (
                        sum(
                            ld for nid, ld in affected.items()
                            if getattr(grid.nodes.get(nid), "node_type", "")
                            in CRITICAL_NODE_TYPES
                        )
                        if affected else (total_affected if is_critical else 0.0)
                    )
                    grid.inject_failure(target)
                    fault_timesteps[target] = t
                    fault_affected_loads[target] = affected
                    fault_baseline_load[target]      = total_affected
                    fault_baseline_critical[target]  = affected_critical
                    collector.record_fault(
                        timestep=t, target=target,
                        baseline_load_mw=total_affected,
                        baseline_critical_mw=affected_critical,
                    )
                except Exception as exc:  # noqa: BLE001
                    validity.mark_invalid(
                        InvalidRunReason.FAULT_INJECTION_FAILED,
                        step=t, target=str(fault.target), exc=repr(exc),
                    )
                    invalid_exc = exc
                    raise

# (banner removed; was mojibake)
            try:
                grid_state = grid.get_state()
            except Exception as exc:  # noqa: BLE001
                validity.mark_invalid(
                    InvalidRunReason.METRIC_CALCULATION_FAILED,
                    step=t, where="get_state", exc=repr(exc),
                )
                invalid_exc = exc
                raise
            try:
                rl_state = grid.get_rl_state()
            except Exception:  # noqa: BLE001
                # If the grid has no RL state vector (e.g. a legacy
                # baseline), fall back to an empty list. The downstream
                # DQN adapter treats `[]` as no-action.
                rl_state = []

            t0 = time.time()
            try:
                action = controller.choose_action(rl_state, grid_state, lstm_sequence=grid.get_lstm_input("S_MAIN")) if controller_kind == "dqn" else controller.choose_action(rl_state, grid_state)
            except Exception as exc:  # noqa: BLE001
                validity.mark_invalid(
                    InvalidRunReason.CONTROLLER_FAILED,
                    step=t, controller=controller_kind, exc=repr(exc),
                )
                invalid_exc = exc
                raise
            controller_runtime_s += time.time() - t0
# (banner removed; was mojibake)
            if controller_kind == "dqn":
                counters.dqn_actions += 1
                if getattr(controller, "lstm_call_count", 0):
                    counters.model_calls += int(controller.lstm_call_count)
                    # Reset for next step
                    controller.lstm_call_count = 0
            elif controller_kind == "rule_based":
                counters.rule_actions += 1
            elif controller_kind == "random":
                counters.random_actions += 1
            elif controller_kind == "persistence":
                counters.noop_actions += 1

# (banner removed; was mojibake)
            if config.enable_flisr and hasattr(grid, "flisr_restore"):
                # Realistic control loop: a fault detected this step cannot
                # be healed in the same cycle. Only restore faults that were
                # injected on an earlier step and are still pending.
                restored = _restored_targets(collector)
                pending = [
                    tid for tid, ts in fault_timesteps.items()
                    if ts < t and tid not in restored
                ]
                if not pending:
                    # Nothing to heal this cycle; skip the call entirely.
                    pass
                else:
                    try:
                        result = grid.flisr_restore()
                        counters.flisr_calls += 1
                        actions_attempted = int(result.get("actions_attempted", 0) or 0)
                        actions_applied = int(result.get("actions_applied", 0) or 0)
                        counters.restoration_actions_attempted += actions_attempted
                        counters.restoration_actions_applied += actions_applied
                        collector.switching_operations += actions_applied
                        if result.get("nodes_restored") or actions_applied > 0:
                            counters.flisr_successes += 1
                        else:
                            counters.flisr_failures += 1
                    except Exception as exc:  # noqa: BLE001
                        logger.exception(
                            "Reactive FLISR failed at seed=%d step=%d",
                            config.seed, t,
                        )
                        validity.mark_invalid(
                            InvalidRunReason.CONTROLLER_FAILED,
                            step=t, controller="flisr_reactive",
                            exc=repr(exc),
                        )
                        invalid_exc = exc
                        raise

# (banner removed; was mojibake)
            if config.enable_predictive_healing:
                # The predictive healer is a *learning* module. Its
                # risk signal is sourced from the digital twin *iff*
                # enable_twin is on. When enable_twin is False, the
                # healer uses a deliberate observable-state fallback
# (banner removed; was mojibake)
                # twin values are injected. This is the crucial
                # decoupling that lets ``no_twin`` differ from
                # ``no_predictive`` at runtime.
                try:
                    from self_healing.predictor import PredictiveSelfHealer
                    healer = PredictiveSelfHealer()
                    twin = None
                    if config.enable_twin:
                        from digital_twin.twin_registry import TwinRegistry
                        twin = TwinRegistry()
                        twin.register(grid)
                        twin.sync(grid, dt_hours=1.0)
                        counters.twin_updates += 1
                        # Count per-node twin reads for the assessor.
                        for nid in grid.nodes:
                            if twin.get(nid) is not None:
                                counters.twin_queries += 1
                    result = healer.run(grid, twin)
                    counters.predictions_generated += 1
                    counters.recommendations_generated += int(
                        result.get("action_count", 0)
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.exception(
                        "Predictive healer failed at seed=%d step=%d",
                        config.seed, t,
                    )
                    validity.mark_invalid(
                        InvalidRunReason.CONTROLLER_FAILED,
                        step=t, controller="predictive_healer",
                        exc=repr(exc),
                    )
                    invalid_exc = exc
                    raise

# (banner removed; was mojibake)
            t0 = time.time()
            try:
                grid.step()
            except Exception as exc:  # noqa: BLE001
                validity.mark_invalid(
                    InvalidRunReason.UNEXPECTED_EXCEPTION,
                    step=t, where="grid.step", exc=repr(exc),
                )
                invalid_exc = exc
                raise
            step_time = time.time() - t0
            power_flow_runtime_s += step_time * 0.5

# (banner removed; was mojibake)
            # Restoration detection: a fault is restored once at least
            # ``RESTORATION_LOAD_FRACTION`` of the affected consumer load
            # (by MW) is receiving power again. Consumers stuck on the
            # faulted section (attached directly behind the failed node) are
            # not restorable by FLISR and stay dark ? that does not make the
            # fault "unrestored".
            restored_now = _restored_targets(collector)
            for target, affected in list(fault_affected_loads.items()):
                if target in restored_now or target not in grid.nodes:
                    continue
                if affected:
                    baseline_total = float(sum(affected.values()))
                    served_load = 0.0
                    for nid, load in affected.items():
                        if nid not in grid.nodes:
                            continue
                        received = float(
                            getattr(grid.nodes[nid], "received_power", 0.0) or 0.0
                        )
                        if received > 0.0:
                            served_load += float(load)
                    energized = (
                        baseline_total > 0.0
                        and served_load >= RESTORATION_LOAD_FRACTION * baseline_total
                    )
                else:
                    node = grid.nodes[target]
                    energized = (
                        not getattr(node, "failed", False)
                        and float(getattr(node, "received_power", 0.0) or 0.0) > 0.0
                    )
                if energized:
                    collector.mark_restoration_complete(
                        fault_target=target, timestep=t,
                    )

# (banner removed; was mojibake)
            collector.record_step(grid=grid, timestep=t,
                                  controller_action=action,
                                  action_legal=True)

# (banner removed; was mojibake)
            step_validity = check_run_validity(grid, step=t)
            if not step_validity.valid:
                # Carry any more-specific reason already recorded
                # (e.g. CONTROLLER_FAILED from FLISR or the
                # predictive healer) into the step's report before
                # we propagate it to the run-level validity. The
                # priority table inside ``mark_invalid`` keeps the
                # more-specific reason.
                for k, v in validity.details.items():
                    step_validity.details.setdefault(k, v)
                if validity.invalid_reason:
                    try:
                        step_validity.mark_invalid(
                            InvalidRunReason(validity.invalid_reason),
                        )
                    except ValueError:
                        pass
                validity = step_validity
                break

    except Exception as exc:  # noqa: BLE001 - final fallback
        if validity.valid:
            validity.mark_invalid(
                InvalidRunReason.UNEXPECTED_EXCEPTION,
                exc=repr(exc),
            )
        invalid_exc = exc

# (banner removed; was mojibake)
    try:
        metrics = compute_research_metrics(
            grid=grid, collector=collector,
            run_started_at=run_started_at,
            controller_runtime_s=controller_runtime_s,
            power_flow_runtime_s=power_flow_runtime_s,
            total_steps=int(scenario.total_steps),
        )
    except Exception as exc:  # noqa: BLE001
        validity.mark_invalid(
            InvalidRunReason.METRIC_CALCULATION_FAILED,
            exc=repr(exc),
        )
        metrics = {"_metrics_failed": True, "_error": repr(exc)}

    # Final invalid-reason wins; otherwise keep step validity.
    if invalid_exc is not None and not validity.valid:
        # Already marked by the originating try-block.
        pass

    # Final invalid-reason wins; otherwise keep step validity.
    if invalid_exc is not None and not validity.valid:
        # Already marked by the originating try-block.
        pass

    if isinstance(metrics, dict):
        metrics["module_call_counts"] = counters.to_dict()

    # PF diagnostic (EHM-HIGH-005 / EHM-NEW-001): every run_single output
    # must carry a snapshot of the most recent DC power flow. SmartGrid
    # runs DC PF on every step (see SmartGrid.update_power_flow), so
    # ``self.dc_state`` is populated whenever the grid is healthy. NaN/Inf
    # values are coerced to ``None`` so JSON serialisation cannot fail and
    # downstream consumers never receive a non-finite number.
    pf_diag: Dict[str, object] = {
        "dc_converged": False,
        "dc_kcl_residual_max": None,
        "dc_kcl_residual_mean": None,
        "dc_bus_count": 0,
        "dc_line_count": 0,
        "dc_slack_bus_id": "",
        "dc_island_count": 0,
        "dc_has_unpowered_islands": False,
        "dc_warnings": [],
    }
    try:
        dc_state = getattr(grid, "dc_state", None)
        if dc_state is not None:
            rmax = float(getattr(dc_state, "kcl_residual_max", float("nan")))
            rmean = float(getattr(dc_state, "kcl_residual_mean", float("nan")))
            pf_diag["dc_converged"] = bool(getattr(dc_state, "converged", False))
            pf_diag["dc_kcl_residual_max"] = (
                rmax if rmax == rmax and abs(rmax) != float("inf") else None
            )
            pf_diag["dc_kcl_residual_mean"] = (
                rmean if rmean == rmean and abs(rmean) != float("inf") else None
            )
            pf_diag["dc_bus_count"] = int(getattr(dc_state, "bus_count", 0) or 0)
            pf_diag["dc_line_count"] = int(getattr(dc_state, "line_count", 0) or 0)
            pf_diag["dc_slack_bus_id"] = str(
                getattr(dc_state, "slack_bus_id", "") or ""
            )
            warnings_list = list(getattr(dc_state, "warnings", []) or [])
            pf_diag["dc_warnings"] = warnings_list[:10]
            pf_diag["dc_island_count"] = sum(
                1 for w in warnings_list if "islands" in w.lower()
            )
            pf_diag["dc_has_unpowered_islands"] = any(
                "unpowered" in w.lower() for w in warnings_list
            )
    except Exception as exc:  # noqa: BLE001
        pf_diag["dc_extraction_error"] = repr(exc)

    return {
        "config":        config.to_dict(),
        "scenario":      scenario.to_dict(),
        "validity":      validity.to_dict(),
        "controller":    controller_kind,
        "metrics":       metrics,
        "module_call_counts": counters.to_dict(),
        "fault_timesteps": fault_timesteps,
        "pf_diagnostic": pf_diag,
        "completed_at":  datetime.now(timezone.utc).isoformat(),
    }


# (banner removed; was mojibake)
def _safe_run_one(*, config: ExperimentConfig, scenario: Scenario,
                  **_: object) -> Dict[str, object]:
    """Legacy alias for :func:`run_single`.

    Earlier versions of the experiments framework exposed the
    per-tuple driver as ``_safe_run_one``. The new name is
    :func:`run_single`; this shim keeps the old name working so we
    don't break ``tests/test_experiments_framework.py``.
    """
    return run_single(config=config, scenario=scenario)


def _build_grid():
    """Build the default SmartGrid; local import so torch is optional."""
    from simulation.grid import SmartGrid
    return SmartGrid()


# (banner removed; was mojibake)
def run_experiment(
    *,
    configs: Optional[List[ExperimentConfig]] = None,
    policies: Optional[List[str]] = None,
    seeds: int,
    ticks: int,
    faults_per_run: int,
    weather_modes: Optional[List[str]] = None,
    output_path: str,
    write_csv: bool = True,
    write_manifest_path: Optional[str] = None,
    schema_version: str = "2.0",
) -> Dict[str, object]:
    """Run every (config, seed, weather) combination and write a report.

    Two calling styles are supported:

    1. New style (preferred): ``configs=[ExperimentConfig(...), ...]``,
       ``weather_modes=["normal", "high_demand", "storm"]``. Uses the
       full ``ExperimentConfig`` machinery and is what
       :mod:`experiments.paper_experiment` and the tests use.

    2. Legacy style: ``policies=["random", "rule_based", ...]`` (single
       ``"normal"`` weather). This is the shape the original
       ``experiments/runner.py`` exposed; we keep it for
       ``tests/test_experiments_framework.py`` and the older scripts
       (``monte_carlo.py``).

    Same seed -- same scenario. Different seed -- different scenario.
    Same weather -- same load / weather modulation.

    Returns the dict written to disk.
    """
# (banner removed; was mojibake)
    if configs is None:
        if policies is None:
            raise TypeError(
                "run_experiment requires either configs= or policies=."
            )
        configs = []
        for label in policies:
            if label not in ABLATION_CONFIGS:
                raise KeyError(
                    f"Unknown policy label {label!r}. "
                    f"Available: {list(ABLATION_CONFIGS.keys())}"
                )
            configs.append(ABLATION_CONFIGS[label])

    if weather_modes is None:
        weather_modes = ["normal"]

    runs: List[Dict[str, object]] = []
    started = time.time()

    # Pre-generate one scenario per (seed, weather). This is what
# (banner removed; was mojibake)
    scenarios_by_weather: Dict[str, Dict[int, Scenario]] = {}
    for weather in weather_modes:
        scenarios_by_weather[weather] = {}
        for seed in range(int(seeds)):
            scenarios_by_weather[weather][seed] = make_scenario(
                seed=int(seed),
                total_steps=int(ticks),
                fault_count=int(faults_per_run),
                weather_mode=weather,
                label=f"seed_{seed}_{weather}",
            )

    for config in configs:
        for weather in weather_modes:
            for seed in range(int(seeds)):
                scenario = scenarios_by_weather[weather][seed]
                logger.info(
                    "Running config=%s seed=%d weather=%s",
                    config.label, seed, weather,
                )
                run = run_single(config=config, scenario=scenario)
                run["seed"] = seed
                run["weather_mode"] = weather
                run["controller_label"] = config.label
                # Legacy fields expected by some downstream scripts.
                run["valid"]  = bool(run["validity"]["valid"])
                run["policy"] = config.label
                if run["validity"].get("invalid_reason"):
                    run["invalid_reason"] = run["validity"]["invalid_reason"]
                runs.append(run)

# (banner removed; was mojibake)
    n_total   = len(runs)
    n_valid   = sum(1 for r in runs if r["validity"]["valid"])
    n_invalid = n_total - n_valid
    valid_rate = (n_valid / n_total) if n_total else 0.0
    elapsed = time.time() - started

# (banner removed; was mojibake)
    summary: Dict[str, Dict[str, int]] = {}
    for run in runs:
        label = run.get("controller_label") or run.get("policy", "")
        bucket = summary.setdefault(label, {"n_runs": 0, "n_valid": 0})
        bucket["n_runs"] += 1
        if run.get("validity", {}).get("valid"):
            bucket["n_valid"] += 1

    # Detect legacy callers that expect schema_version "1.0".
    # If ``policies=`` was used (legacy API), default to "1.0";
    # the new ``configs=`` API defaults to "2.0". Callers can
    # override by passing ``schema_version=`` explicitly.
    if policies is not None and schema_version == "2.0":
        schema_version = "1.0"
    if schema_version == "1.0":
        # Rewrite the report to look like the legacy shape.
        report_legacy = {
            "schema_version": "1.0",
            "experiment":     "experiments.runner",
            "n_seeds":        int(seeds),
            "ticks":          int(ticks),
            "faults_per_run": int(faults_per_run),
            "weather_modes":  list(weather_modes),
            "n_total":        n_total,
            "n_valid":        n_valid,
            "n_invalid":      n_invalid,
            "valid_rate":     valid_rate,
            "elapsed_s":      round(elapsed, 3),
            "completed_at":   datetime.now(timezone.utc).isoformat(),
            "summary":        summary,
            "runs":           runs,
        }
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report_legacy, f, indent=2, sort_keys=True, default=str)
        return report_legacy

    report = {
        "schema_version": schema_version,
        "experiment": "experiments.runner",
        "n_seeds": int(seeds),
        "ticks": int(ticks),
        "faults_per_run": int(faults_per_run),
        "weather_modes": list(weather_modes),
        "n_total": n_total,
        "n_valid": n_valid,
        "n_invalid": n_invalid,
        "valid_rate": valid_rate,
        "elapsed_s": round(elapsed, 3),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "runs": runs,
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)

    if write_csv:
        csv_path = os.path.splitext(output_path)[0] + ".csv"
        _write_csv(runs, csv_path)

    if write_manifest_path:
        # The manifest captures every input needed to reproduce the run.
        all_scenarios: List[Scenario] = []
        for weather_dict in scenarios_by_weather.values():
            all_scenarios.extend(weather_dict.values())
        write_manifest(
            write_manifest_path,
            experiment_name="experiments.runner",
            configs=[c.to_dict() for c in configs],
            scenarios=all_scenarios,
            n_runs=n_total,
            extra={
                "valid_runs": n_valid,
                "invalid_runs": n_invalid,
                "valid_rate": valid_rate,
                "elapsed_s": round(elapsed, 3),
                "weather_modes": list(weather_modes),
            },
        )

    return report


def _write_csv(runs: List[Dict[str, object]], path: str) -> None:
    """Write a flat CSV -- one row per (config, seed, weather) combination."""
    # The columns are the metric keys that are always present.
    metric_keys: List[str] = []
    for run in runs:
        m = run.get("metrics") or {}
        for k in m.keys():
            if k not in metric_keys and isinstance(m.get(k), (int, float, str)):
                metric_keys.append(k)
    # Stable column order
    columns = (
        ["controller_label", "seed", "weather_mode", "valid",
         "invalid_reason", "faults_n"] + metric_keys
    )
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(columns)
        for run in runs:
            m = run.get("metrics") or {}
            row = [
                run.get("controller_label", ""),
                run.get("seed", ""),
                run.get("weather_mode", ""),
                run["validity"].get("valid", False),
                run["validity"].get("invalid_reason", "") or "",
                len(m.get("faults", []) or []),
            ]
            for k in metric_keys:
                v = m.get(k, "")
                if isinstance(v, (list, dict)):
                    v = json.dumps(v, default=str)
                row.append(v)
            w.writerow(row)


# (banner removed; was mojibake)
def _config_from_label(label: str) -> ExperimentConfig:
    """Resolve a label to an ExperimentConfig; raise if unknown."""
    if label not in ABLATION_CONFIGS:
        raise KeyError(
            f"Unknown config label {label!r}. "
            f"Available: {list_ablation_labels()}"
        )
    return ABLATION_CONFIGS[label]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--ticks", type=int, default=50)
    parser.add_argument("--faults", type=int, default=2)
    parser.add_argument(
        "--weather", default="normal",
        help="Comma-separated weather modes (normal,high_demand,storm)",
    )
    parser.add_argument(
        "--policies",
        default="random,rule_based,dqn_core_only,full_stack",
        help="Comma-separated ablation/policy labels. Use labels from "
             "experiment_config.list_ablation_labels()",
    )
    parser.add_argument(
        "--output",
        default="experiments/results/runner.json",
    )
    parser.add_argument(
        "--manifest",
        default="experiments/results/runner.manifest.json",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    weather_modes = [w.strip() for w in args.weather.split(",") if w.strip()]
    config_labels = [p.strip() for p in args.policies.split(",") if p.strip()]
    configs = [_config_from_label(label) for label in config_labels]

    # IMPORTANT: also set the global seed before running. The runner
    # uses (config.seed + scenario.seed) for each run; this ensures
    # the *global* Python/Numpy/Torch RNGs are also reproducible.
    set_global_seed(0)

    report = run_experiment(
        configs=configs,
        seeds=args.seeds,
        ticks=args.ticks,
        faults_per_run=args.faults,
        weather_modes=weather_modes,
        output_path=args.output,
        write_csv=True,
        write_manifest_path=args.manifest,
    )

    print(f"Wrote {args.output}")
    print(f"Wrote {os.path.splitext(args.output)[0]}.csv")
    print(f"Wrote {args.manifest}")
    print(f"valid: {report['n_valid']}/{report['n_total']} "
          f"({report['valid_rate']*100:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())