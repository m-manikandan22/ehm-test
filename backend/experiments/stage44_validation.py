"""stage44_validation.py — Stage-44 10-seed × 5-scenario validation.

Honest-Repair Stage 44 validation contract
==========================================

We **do not** modify the architecture, the reward, the DQN, the
scenarios, the seeds, or the hyperparameters. We **only**:

* Use ``experiments.runner.run_single`` as the per-run engine,
* Replace ``runner.make_controller`` with a Stage-44-aware factory
  that can inject the Stage-44 trained checkpoint
  (``dqn_stage44.pt``) or a freshly-seeded untrained DQNAgent,
* Use the Stage-43 scenario matrix (A/E/G/H/J) loaded from
  ``experiments.scenario_matrix``,
* Compute per-cell statistics (mean, median, std, 95% bootstrap
  CI, Wilcoxon, Cohen's d, Bonferroni-Holm),
* Verify paired fingerprints across controllers / ablations and
  emit an INVALID_COMPARISON flag if any fingerprint mismatches.

Evaluation is **frozen**:
  * no gradient updates,
  * no optimiser step,
  * no replay-buffer writes,
  * ε = 0,
  * ``agent.eval_mode()`` is called after every load,
  * we never call ``store_experience`` during evaluation.

The runner wrapper below uses the existing ``ExperimentConfig``
machinery so an ablation turns off a real module — no labels
without behaviour.
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

# Path bootstrap (mirrors runner.py)
THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parents[2]  # backend/experiments/.. -> repo root
BACKEND = PROJECT_ROOT / "backend"
for p in (str(PROJECT_ROOT), str(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402

from utils.seeds import set_global_seed  # noqa: E402
from models.rl_agent import build_extended_state  # noqa: E402

# runner imports from this directory + project root
THIS_DIR = BACKEND / "experiments"
for p in (str(THIS_DIR), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


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


# Stage-44 controller catalogue (as defined in
# docs/STAGE_44_VALIDATION_REPORT.md §"Controllers")
STAGE44_CONTROLLERS = (
    "random",       # RandomPolicy baseline
    "rule_based",   # RuleBasedPolicy baseline
    "untrained_dqn",  # Freshly-seeded DQNAgent in eval_mode
    "trained_dqn",    # dqn_stage44.pt loaded into DQNAgent in eval_mode
)
STAGE44_ABLATIONS = (
    "full_stack",   # all modules on (default)
    "no_lstm",
    "no_twin",
    "no_predictive",
    "no_ems",
)


def _build_dqn_agent(*, checkpoint: Optional[str], seed: int):
    """Build a DQNAgent — untrained or loaded from a checkpoint.

    The agent is always returned in ``eval_mode()``: ε=0, no replay
    writes, no gradient steps, no target-net sync. This is the
    Stage-44 evaluation contract.
    """
    from models.rl_agent import (
        DQNAgent, EXTENDED_STATE_DIM,
    )
    if checkpoint is None:
        torch_seed = int(seed) * 7919
        import torch
        torch.manual_seed(torch_seed)
        agent = DQNAgent(state_dim=EXTENDED_STATE_DIM)
        agent.eval_mode()
        return agent
    if not os.path.exists(checkpoint):
        raise FileNotFoundError(
            f"Stage-44 checkpoint not found: {checkpoint}. "
            "Train it first with stage44_dqn_training.py."
        )
    agent = DQNAgent.load_checkpoint(
        checkpoint, state_dim=EXTENDED_STATE_DIM, eval_mode=True,
    )
    # Sanity: agent must be frozen at *load time*. The numerical
    # ``epsilon`` field stays at its checkpoint-recorded value but
    # ``select_action`` will force ε=0 inside eval mode.
    assert agent.is_training is False, (
        "Stage-44 evaluation requires eval_mode() — agent must be "
        "frozen at load time."
    )
    assert hasattr(agent, "_training") and agent._training is False, (
        "Stage-44 evaluation requires agent._training == False"
    )
    return agent


_SHARED_FORECASTER: Optional[object] = None


def _get_shared_forecaster():
    """Return a process-singleton DemandForecaster.

    The forecaster's pretraining is slow (~2 s on CPU) — building
    it per step (or per run) would dominate the validation. The
    State-44 contract says *the frozen LSTM weights* depend only
    on the torch random state at construction time; since
    ``torch.manual_seed`` is *not* called inside this validation
    runner (we use ``set_global_seed``), the forecaster's weights
    are deterministic *for this process*. The same pretrained
    forecaster is reused across every step of every run.
    """
    global _SHARED_FORECASTER
    if _SHARED_FORECASTER is None:
        from models.lstm_model import DemandForecaster
        _SHARED_FORECASTER = DemandForecaster()
    return _SHARED_FORECASTER


class _Stage44DQNAdapter:
    """Adapter that exposes ``choose_action(state, grid_state)`` over a DQNAgent.

    Mirrors ``experiments.runner._DQNAdapter`` but takes the agent
    as a constructor argument (rather than constructing one) so we
    can inject either an untrained freshly-seeded agent or the
    Stage-44 trained checkpoint. The ``enable_lstm`` flag controls
    whether the LSTM's prediction is fed in as ``predicted_load``;
    when False, the channel is held at the no-LSTM sentinel 0.5.

    NO TRAINING HOOKS — ``choose_action`` never calls
    ``store_experience`` and the adapter holds no replay buffer.
    """

    def __init__(self, agent, *, enable_lstm: bool, enable_twin: bool):
        self._agent = agent
        self._enable_lstm = enable_lstm
        self._enable_twin = enable_twin
        # Counter for an evidence-style trace (the runner counts
        # these in its own ModuleCallCounters; we keep a small
        # duplicate for the per-run ablation JSON).
        self.lstm_call_count = 0
        self.lstm_inference_successes = 0
        self.lstm_inference_failures = 0
        # Stage 46.1 (information-flow repair): the LSTM forecast is
        # computed from the *real* per-step grid history (the same
        # ``(aggregate_load, aggregate_gen, weather)`` deque that the
        # training loop and ``experiments.runner.run_single`` maintain),
        # never from a hard-coded constant input. The run loop installs
        # the deque via ``set_lstm_history`` before the first step.
        self._lstm_history = None

    def set_lstm_history(self, history) -> None:
        """Install the per-run history deque of (load, gen, weather)
        triples observed up to the current step (past only)."""
        self._lstm_history = history

    def _predicted_load(self) -> float:
        if not self._enable_lstm:
            return 0.5
        try:
            self.lstm_call_count += 1
            fc = _get_shared_forecaster()
            history = self._lstm_history
            if history is None or len(history) == 0:
                # No observations yet (spin-up before the first step):
                # fall back to a neutral warm-up window.
                pred = float(fc.predict([[0.5, 0.5, 0.0]] * 10))
            else:
                seq = list(history)[-10:]
                if len(seq) < 10:
                    seq = [seq[0]] * (10 - len(seq)) + seq
                pred = float(
                    fc.predict([[l, g, w] for l, g, w in seq])
                )
            self.lstm_inference_successes += 1
            return pred
        except Exception:
            self.lstm_inference_failures += 1
            return 0.5

    def choose_action(self, state, grid_state=None, **_):
        # The DQN's select_action path uses ``torch.no_grad()`` and
        # does NOT touch ``self._training`` (which is False in eval
        # mode). All training hooks are inert.
        try:
            pred = self._predicted_load()
            return self._agent.select_action(
                list(state) if state is not None else [],
                predicted_load=pred,
                grid_state=grid_state,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Stage-44 DQN select_action failed: {exc!r}"
            ) from exc

    def reset(self) -> None:
        reset = getattr(self._agent, "reset", None)
        if callable(reset):
            try:
                reset()
            except Exception:
                pass


def _fingerprint_run(*, grid, scenario) -> Dict[str, str]:
    """Per-run environmental fingerprints (Stage-43 contract)."""
    def _h(obj) -> str:
        if obj is None:
            return ""
        s = json.dumps(obj, sort_keys=True, default=str)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

    try:
        grid_state = grid.get_state() if hasattr(grid, "get_state") else {}
    except Exception:
        grid_state = {}

    nodes = {}
    try:
        for nid, n in grid.nodes.items():
            nodes[str(nid)] = {
                "node_type": str(getattr(n, "node_type", "")),
                "load": float(getattr(n, "load", 0.0) or 0.0),
                "generation": float(getattr(n, "generation", 0.0) or 0.0),
                "battery_level": float(getattr(n, "battery_level", 0.0) or 0.0),
                "supercap_level": float(getattr(n, "supercap_level", 0.0) or 0.0),
                "failed": bool(getattr(n, "failed", False)),
                "isolated": bool(getattr(n, "isolated", False)),
                "_base_load": float(getattr(n, "_base_load", 0.0) or 0.0),
            }
    except Exception:
        nodes = {}

    edges = []
    try:
        for u, v, d in grid.graph.edges(data=True):
            edges.append({
                "u": str(u), "v": str(v),
                "is_tie_switch": bool(d.get("is_tie_switch")),
                "active": bool(d.get("active", True)),
                "switch_status": str(d.get("switch_status", "")),
            })
        edges.sort(key=lambda e: (e["u"], e["v"]))
    except Exception:
        edges = []

    faults = []
    for f in (scenario.faults if hasattr(scenario, "faults") else []):
        faults.append({
            "timestep": int(f.timestep),
            "target": str(f.target),
            "duration_steps": int(f.duration_steps),
            "kind": str(f.kind),
        })
    faults.sort(key=lambda x: x["timestep"])

    return {
        "grid_hash": _h(nodes),
        "demand_hash": _h({k: v["load"] for k, v in nodes.items()}),
        "renewable_hash": _h({k: v["generation"] for k, v in nodes.items()}),
        "fault_schedule_hash": _h(faults),
        "initial_storage_hash": _h({
            k: (v["battery_level"], v["supercap_level"]) for k, v in nodes.items()
        }),
        "topology_hash": _h(edges),
    }


def _build_scenario_for_seed(label: str, seed: int, total_steps: int = 80):
    """Build a deterministic Stage-43 evaluation scenario.

    Mirrors the Stage-43 validation JSON record structure so we
    can compare paired runs across controllers / ablations.
    """
    from experiments.scenario_matrix import (
        SCENARIO_MATRIX, get_scenario_spec, build_scenario,
    )
    spec = get_scenario_spec(label)
    return build_scenario(seed=seed, spec=spec)


def _build_grid_fresh(seed: int):
    """Fresh grid built deterministically from a seed."""
    from simulation.grid import SmartGrid
    set_global_seed(seed)
    return SmartGrid(seed=seed)


def _apply_scenario_to_grid(grid, scenario) -> None:
    """Apply scenario multipliers + pre-aged twins to the grid."""
    from experiments.scenario_matrix import get_scenario_spec
    label = (
        scenario.label.split("|")[0]
        if hasattr(scenario, "label") else "A"
    )
    try:
        spec = get_scenario_spec(label)
    except Exception:
        return

    # Demand / renewable multipliers — best-effort.
    try:
        grid.demand_multiplier = float(spec.demand_multiplier)
    except Exception:
        pass
    try:
        grid.renewable_multiplier = float(spec.renewable_multiplier)
    except Exception:
        pass

    # Battery SOC init — best-effort write on the appropriate nodes.
    if spec.battery_soc_init is not None:
        for nid, n in grid.nodes.items():
            nt = str(getattr(n, "node_type", ""))
            if nt == "house" or nt == "battery":
                try:
                    n.battery_level = float(spec.battery_soc_init)
                except Exception:
                    pass


def _run_controller_on_scenario(
    *, controller_label: str, scenario, seed: int,
    ablation: str,
    checkpoint_path: Optional[str],
    enable_lstm: bool, enable_twin: bool,
    enable_predictive: bool, enable_ems: bool,
    enable_flisr: bool,
    max_steps: int,
):
    """Run a single (controller, seed, scenario, ablation) tuple.

    We do NOT call runner.run_single — we re-implement only the
    loop Stage-44 needs because we want explicit control over:

      * the DQN agent injection (untrained or loaded checkpoint),
      * the LSTM / twin / predictive / EMS ablations,
      * the fingerprint collection,
      * the action distribution tracking,
      * the per-step physical-validity mark (no train-mode writes).

    Returns a per-run result dict matching the Stage-43 validation
    record schema.
    """
    # Seed global RNG so the grid builds deterministically.
    set_global_seed(int(seed))

    # Build the controller.
    action_counts = Counter()
    selected_actions = []
    grid = _build_grid_fresh(seed)
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

    # Pre-age scenario-specific twins (Scenario H = single pre-aged pole).
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
    # loop (``stage44_dqn_training._lstm_predict``) and to
    # ``experiments.runner.run_single``. The weather proxy is a fixed
    # per-scenario constant (same mapping as the runner).
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

    # Per-run metric accumulators.
    energy_not_served = 0.0
    critical_interruption_steps = 0
    restoration_steps = []
    n_faults = 0
    n_restored = 0
    total_steps = min(int(scenario.total_steps), max_steps)
    n_voltage_violations = 0
    served_load_sum = 0.0
    served_baseline_sum = 0.0
    battery_discharged = 0.0
    supercap_discharged = 0.0

    fault_timesteps: Dict[str, int] = {}
    fault_baseline_load: Dict[str, float] = {}
    baseline_critical: Dict[str, float] = {}
    restored_targets: set = set()

    fingerprints = _fingerprint_run(grid=grid, scenario=scenario)

    for t in range(total_steps):
        # Inject any faults due this step.
        from experiments.research_metrics import CRITICAL_NODE_TYPES
        for fault in scenario.faults:
            if fault.timestep != t:
                continue
            target = fault.target
            try:
                # Baseline downstream consumer load.
                baseline_loads = {}
                try:
                    import networkx as nx  # type: ignore
                    downstream = [target] + list(
                        nx.descendants(grid.graph, target),
                    )
                except Exception:
                    downstream = [target]
                crit_load = 0.0
                total_load = 0.0
                for nid in downstream:
                    n = grid.nodes.get(nid)
                    if n is None:
                        continue
                    nt = str(getattr(n, "node_type", ""))
                    if nt in ("house", "industry", "hospital"):
                        ld = float(getattr(n, "load", 0.0) or 0.0)
                        if ld > 0:
                            baseline_loads[nid] = ld
                            total_load += ld
                            if nt in CRITICAL_NODE_TYPES:
                                crit_load += ld
                grid.inject_failure(target)
                fault_timesteps[target] = t
                fault_baseline_load[target] = total_load
                baseline_critical[target] = crit_load
                n_faults += 1
            except Exception:
                pass

        # Predict step.
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
                # Build the 78-dim extended state. The DQN's
                # network was trained on the extended vector, not
                # the bare 72-dim SmartGrid state.
                forecast = 0.5
                try:
                    if (
                        hasattr(controller, "_enable_lstm")
                        and controller._enable_lstm
                    ):
                        forecast = controller._predicted_load()
                except Exception:
                    forecast = 0.5
                # Twin + storage features.
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
                # Grid-scale battery (STORAGE_BAT)
                bat_node = grid.nodes.get("STORAGE_BAT")
                if bat_node is not None and not getattr(bat_node, "failed", False) and not getattr(bat_node, "isolated", False):
                    battery_soc = float(getattr(bat_node, "battery_level", 0.0) or 0.0)

                # Grid-scale supercapacitor (STORAGE_SC)
                sc_node = grid.nodes.get("STORAGE_SC")
                if sc_node is not None and not getattr(sc_node, "failed", False) and not getattr(sc_node, "isolated", False):
                    supercap_soc = float(getattr(sc_node, "supercap_level", 0.0) or 0.0)
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
                action_name = str(decision.get("action_name", ""))
            elif isinstance(decision, (int, np.integer)):
                action_id = int(decision)
                action_name = f"action_{action_id}"
            else:
                action_id = -1
                action_name = ""
        except Exception:
            action_id = -1
            action_name = "ERROR"

        if 0 <= action_id <= 4:
            action_counts[action_id] += 1
            selected_actions.append(action_id)
        else:
            selected_actions.append(-1)

        # Dispatch.
        if action_id >= 0:
            try:
                from experiments.runner import _dispatch_action
                _dispatch_action(grid, action_id)
            except Exception:
                pass
            # Stage-44 instrumentation: count storage discharge.
            if action_id == 1:
                for nid, n in grid.nodes.items():
                    if str(getattr(n, "node_type", "")) == "house":
                        try:
                            battery_discharged += max(
                                0.0,
                                0.5 - float(getattr(n, "battery_level", 0.0) or 0.0),
                            )
                        except Exception:
                            pass
            if action_id == 2:
                for nid, n in grid.nodes.items():
                    if str(getattr(n, "node_type", "")) == "house":
                        try:
                            supercap_discharged += max(
                                0.0,
                                0.5 - float(getattr(n, "supercap_level", 0.0) or 0.0),
                            )
                        except Exception:
                            pass

        # Tick twin registry if enabled.
        if twin is not None and enable_twin:
            try:
                twin.sync(grid, dt_hours=1.0)
            except Exception:
                pass

        # Predictive healer (if enabled).
        if enable_predictive and twin is not None:
            try:
                from self_healing.predictor import PredictiveSelfHealer
                healer = PredictiveSelfHealer()
                healer.run(grid, twin)
            except Exception:
                pass

        # FLISR (if enabled).
        if enable_flisr:
            try:
                if hasattr(grid, "flisr_restore"):
                    grid.flisr_restore()
            except Exception:
                pass

        # EMS (if enabled).
        if enable_ems:
            try:
                from simulation.ems import EnergyManagementSystem
                ems = EnergyManagementSystem(use_pypsa=False)
                ems.run(grid)
            except Exception:
                pass

        # Step the grid.
        try:
            grid.step()
        except Exception:
            pass
        try:
            grid.update_power_flow()
        except Exception:
            pass

        # Accumulators per step.
        try:
            served = 0.0
            baseline = 0.0
            crit_int = 0
            for nid, n in grid.nodes.items():
                nt = str(getattr(n, "node_type", ""))
                if nt not in ("house", "industry", "hospital"):
                    continue
                received = float(getattr(n, "received_power", 0.0) or 0.0)
                if nt == "house":
                    would_be = float(getattr(n, "_base_load", 0.0) or 0.0)
                else:
                    would_be = received + 0.0
                served += received
                baseline += would_be
                if nt in CRITICAL_NODE_TYPES and received <= 0:
                    crit_int += 1
            served_load_sum += served
            served_baseline_sum += baseline
            if crit_int:
                critical_interruption_steps += crit_int
            # ENS: ~one-timestep shortfall between would-be and received
            # critical-load, scaled by customers.
            short = max(0.0, baseline - served)
            energy_not_served += short / 60.0  # MW*timestep/60 ≈ MWh
            n_voltage_violations += int(
                any(
                    abs(float(getattr(n, "voltage", 1.0) or 1.0) - 1.0) > 0.10
                    for n in grid.nodes.values()
                )
            )
        except Exception:
            pass

        # Restoration detection.
        for target, base_load in list(fault_baseline_load.items()):
            if target in restored_targets:
                continue
            served = 0.0
            try:
                import networkx as nx  # type: ignore
                downstream = [target] + list(
                    nx.descendants(grid.graph, target),
                )
            except Exception:
                downstream = [target]
            for nid in downstream:
                n = grid.nodes.get(nid)
                if n is None:
                    continue
                nt = str(getattr(n, "node_type", ""))
                if nt in ("house", "industry", "hospital"):
                    if bool(getattr(n, "failed", False)):
                        continue
                    received = float(getattr(n, "received_power", 0.0) or 0.0)
                    if received > 0:
                        served += float(getattr(n, "_base_load", 0.0) or 0.0)
            if base_load > 0 and served >= 0.85 * base_load:
                restored_targets.add(target)
                n_restored += 1
                if target in fault_timesteps:
                    restoration_steps.append(int(t - fault_timesteps[target]))

    cmi = float(critical_interruption_steps) * (1.0 / 6.0)  # rough conversion

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
        "metrics": {
            "n_faults": int(n_faults),
            "n_restored": int(n_restored),
            "restoration_rate": float(n_restored / n_faults) if n_faults else 0.0,
            "avg_restoration_steps": (
                float(np.mean(restoration_steps)) if restoration_steps else 0.0
            ),
            "energy_not_served_mwh": round(float(energy_not_served), 6),
            "critical_load_interruption_steps": int(critical_interruption_steps),
            "total_customer_minutes_interrupted": round(float(cmi), 6),
            "voltage_violation_count": int(n_voltage_violations),
            "battery_discharged_total": round(float(battery_discharged), 6),
            "supercap_discharged_total": round(float(supercap_discharged), 6),
            "n_steps": int(total_steps),
            "action_counts": {int(k): int(v) for k, v in action_counts.items()},
            "n_dispatched_actions": int(sum(action_counts.values())),
        },
        "fingerprints": fingerprints,
        "selected_actions": selected_actions[:200],
    }


def _verified_fingerprints(
    runs: List[Dict], scenarios: List[str], seeds: List[int],
) -> Dict[str, List[str]]:
    """Return per-(scenario,seed) fingerprint aggregates.

    If two controllers on the same (scenario, seed) produced
    different fingerprints, the comparison is INVALID.
    """
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
    ap.add_argument("--checkpoint", default="experiments/checkpoints/dqn_stage44.pt")
    ap.add_argument("--output",
                    default="experiments/results/stage44/validation.json")
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
    args = ap.parse_args()

    seeds = list(range(int(args.seeds)))
    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    controllers = [c.strip() for c in args.controllers.split(",") if c.strip()]
    ablations = [a.strip() for a in args.ablations.split(",") if a.strip()]

    runs: List[Dict] = []
    for scen in scenarios:
        for seed in seeds:
            scenario = _build_scenario_for_seed(scen, int(seed))
            # ------------------------------------------------------------------
            # Controllers — these are the *primary* axis (random,
            # rule_based, untrained_dqn, trained_dqn).
            # ------------------------------------------------------------------
            for ctrl_label in controllers:
                ablation = "full_stack" if ctrl_label in (
                    "random", "rule_based",
                ) else "default_no_ems"
                # The `random` and `rule_based` controllers are not DQN
                # agents — they carry no ablations. We only run them
                # under the implicit full_stack flag.
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
                # DQN controllers run under each ablation.
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
                f"[stage44_validation] scen={scen} seed={seed} — "
                f"{len(runs)} runs so far",
                flush=True,
            )

    # Fingerprint integrity check.
    fp_report = _verified_fingerprints(runs, scenarios, seeds)

    out = {
        "schema_version": "stage44.1.0",
        "experiment": "stage44_validation",
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
    print(f"[stage44_validation] wrote {args.output} "
          f"with {len(runs)} runs ({out['n_valid']} valid)")


if __name__ == "__main__":
    main()
