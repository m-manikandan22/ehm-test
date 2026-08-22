"""runner.py — Paper-grade replay runner.

The runner is the workhorse of the ablation study (Stage 19). Given an
``ExperimentConfig`` and a ``Scenario``, it:

  1. Builds a SmartGrid.
  2. For each timestep ``0..total_steps``:
        * If the config has EMS + storage enabled and the timestep
          > spin-up, let the EMS dispatch.
        * Otherwise fall back to a rule-based action (or random if
          the random policy is selected).
        * If the scenario has a fault at this timestep, inject it
          with ``grid.inject_failure(target)``.
        * Record the step in ``MetricCollector``.
  3. Evaluate the result with ``ValidityReport`` (Stage 24).
  4. Return a dict with the schema documented in
     ``docs/CHECKPOINT_3_ABLATION.md`` (built later).

Determinism
-----------
Each ``run_single`` first calls ``set_global_seed(run_seed)`` — this seeds
Python ``random``, NumPy, and PyTorch. Because ``SmartGrid`` draws its
loads/generators from the global ``random`` module, grid construction is
then fully reproducible per seed (EHM-HIGH-009). The DQN agent (when
``enable_dqn``) is constructed after seeding, so its network weights are
also deterministic per seed; it is run in ``eval_mode()`` (greedy, no
replay) (EHM-CRIT-007a). The random policy draws from its own
``make_rng(seed)`` Generator, so it stays deterministic too.

Control loop (EHM-CRIT-007b)
----------------------------
The simulation clock is *decoupled* from storage: ``grid.step()`` is
called on **every** timestep for **every** policy (persistence, random,
rule-based and DQN alike), so loads and generation evolve identically
regardless of the config's ``enable_storage`` flag. The policy's chosen
action is then applied through ``_dispatch_action`` (mirroring SCADA's
canonical ``_dispatch_control_signal``) — the DQN's action really
changes the grid.

Limitations
-----------
* The runner is a *thin* harness — the heavy lifting (FLISR 9-stage,
  EMS optimisation, predictive healing) is done by the existing
  modules. We don't reimplement them here.
* The ``enable_lstm`` / ``enable_twin`` / ``enable_predictive_healing``
  / ``enable_reward_shaping`` / ``enable_ems`` flags do not (yet) gate
  any behaviour inside this loop, so the ``no_lstm`` / ``no_twin`` /
  ``no_predictive`` / ``no_reward`` rows are expected to reproduce the
  ``full_stack`` trajectory exactly for the same seed. This is the
  honesty check the harness must pass before those modules are wired in.
* The DQN is evaluated on its freshly-seeded weights (no pre-training
  checkpoint is loaded); ``eval_mode()`` guarantees greedy, repeatable
  decisions.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import networkx  # noqa: E402  -- Stage-46: explicit NX exception family

from simulation.grid import SmartGrid
from utils.seeds import derive_stream_seeds, make_rng, set_global_seed

from experiments.experiment_config import ExperimentConfig
from experiments.info_flow import (
    _aggregate_grid_load_and_gen,
    _build_twin_registry,
    _compute_lstm_forecast,
    _high_risk_assets,
    _predictive_preparation,
    _run_ems,
    _tick_twin_registry,
    _twin_risk_map,
)
from experiments.research_metrics import MetricCollector
from experiments.scenario import Scenario
from experiments.validity import check_run_validity


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _build_grid(seed: int = 0, rng_seed: Optional[int] = None) -> SmartGrid:
    """Construct a deterministic SmartGrid for ``seed``.

    SmartGrid's default constructor is non-deterministic (each call
    randomises loads from the global RNG). EHM-HIGH-009: we seed the
    global RNG first and pass the seed into ``SmartGrid(seed=...)`` so
    the same seed always yields the same grid.

    ``rng_seed`` (Stage-43 RNG isolation): when given, the grid owns an
    independent environment RNG, so controller inference can never
    perturb grid physics noise.
    """
    set_global_seed(seed)
    return SmartGrid(seed=seed, rng_seed=rng_seed)


def _git_sha() -> str:
    """Best-effort Git commit SHA of the repository ('' if not under Git)."""
    try:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=repo_root,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:  # noqa: BLE001
        pass
    return "no_git"


# Canonical action-id → effect mapping. Mirrors the ``ACTIONS`` catalogue
# in ``models.rl_agent`` and the dispatch semantics in
# ``ScadaControlCenter._dispatch_control_signal``.
_ACTION_NAMES: Dict[int, str] = {
    0: "increase_generation",
    1: "use_battery",
    2: "use_supercapacitor",
    3: "shift_load",
    4: "reroute_energy",
}


def _dispatch_action(grid, action_id: int) -> str:
    """Apply the physical effect of a controller action to the grid.

    Mirrors ``ScadaControlCenter._dispatch_control_signal`` so an action
    id means the same thing in the ablation harness as in the production
    control loop. Defensive ``getattr`` calls keep stub grids (unit
    tests) from crashing on missing physical attributes.

    Stage-43 (Repair 3): every action now has a real, persistent effect
    on the grid, and no action touches a failed or isolated node
    (physical validity — actions 1–3 can no longer 'serve' a dead node
    and deflate its ENS):
      * 0 increase_generation → ramp the first non-failed conventional
            generator (gas/coal/nuclear). GAS generation is not
            rewritten by ``_apply_time_curves``, so the effect persists.
      * 1 use_battery         → discharge 0.2 MW from every energised
            battery node (houses + dedicated battery storage).
      * 2 use_supercapacitor  → discharge 0.1 MW from every energised
            supercap node (houses + dedicated storage).
      * 3 shift_load          → defer 0.15 MW from every energised
            consumer node that has load to defer.
      * 4 reroute_energy      → real tie-switch closure
            (``SmartGrid.reroute_energy``): closes the open tie that
            re-energises the most isolated nodes.
    """
    name = _ACTION_NAMES.get(int(action_id), "do_nothing")

    def _alive(n) -> bool:
        return not (
            getattr(n, "failed", False) or getattr(n, "isolated", False)
        )

    if name == "increase_generation":
        target = grid.nodes.get("G0")
        if target is not None and _alive(target):
            target.increase_generation(0.5)
        else:
            for node in grid.nodes.values():
                if (
                    str(getattr(node, "node_type", "")).startswith("generator")
                    and _alive(node)
                    and hasattr(node, "increase_generation")
                ):
                    node.increase_generation(0.5)
                    break
    elif name == "use_battery":
        for node in grid.nodes.values():
            if _alive(node) and (
                getattr(node, "node_type", "") == "house"
                or getattr(node, "node_type", "") == "battery"
            ):
                level = float(getattr(node, "battery_level", 0.0) or 0.0)
                if level > 0.2:
                    node.use_battery(0.2)
                    # Stage-45 (Physics-coupled metric audit): the
                    # BFS source-broadening fix in ``grid.py``
                    # recognises any live node with ``generation > 0``
                    # as a BFS source. ``_apply_time_curves`` overwrites
                    # ``generation`` on the next ``step()`` and
                    # ``node.step()`` then sets ``generation = 0`` for
                    # house nodes outside the daylight window (solar
                    # curve gate). We set a per-step marker so the
                    # discharge survives the next ``node.step()``
                    # regardless of time-of-day.
                    try:
                        cur_signal = float(
                            getattr(node, "_discharge_signal_mw", 0.0) or 0.0
                        )
                        node._discharge_signal_mw = cur_signal + 0.2
                    except Exception:  # noqa: BLE001
                        pass
    elif name == "use_supercapacitor":
        for node in grid.nodes.values():
            if _alive(node) and (
                getattr(node, "node_type", "") == "house"
                or getattr(node, "node_type", "") == "supercap"
            ):
                level = float(getattr(node, "supercap_level", 0.0) or 0.0)
                if level > 0.1:
                    node.use_supercapacitor(0.1)
    elif name == "shift_load":
        for node in grid.nodes.values():
            if _alive(node) and getattr(node, "node_type", "") in _CONSUMER_TYPES:
                if float(getattr(node, "load", 0.0) or 0.0) > 0.001:
                    node.shift_load(0.15)
                    # Stage-45 (Physics-coupled metric audit): the
                    # ENS formula is Σ (P_demand − P_served) × Δt.
                    # ``P_demand`` is the node's *baseline demand*
                    # (``_base_load`` for non-houses, ``would_be_load``
                    # for houses). ``shift_load`` deflates the current
                    # ``load`` but does NOT update ``_base_load`` —
                    # so the metric's baseline demand stays unchanged
                    # and shift_load looks invisible to ENS. We
                    # persist the deflation by bumping ``_base_load``
                    # down to match the shifted current load.
                    try:
                        cur_load = float(
                            getattr(node, "load", 0.0) or 0.0
                        )
                        cur_base = float(
                            getattr(node, "_base_load", 0.0) or 0.0
                        )
                        # The current load should never exceed the
                        # baseline after a legal shift.
                        node._base_load = min(cur_base, cur_load)
                    except Exception:  # noqa: BLE001
                        pass
    elif name == "reroute_energy":
        # Stage-46 (action-layer integrity): the reroute method
        # ``SmartGrid.reroute_energy`` is now hardened against
        # ``NetworkX.NodeNotFound`` -- it pre-seeds the candidate
        # graph with every live node as a singleton and skips
        # nodes that are not in the candidate graph. We still
        # catch any unexpected exception so the controller loop
        # never crashes, but we explicitly log the failure reason
        # (success / no_feasible_action / action_error) so the
        # audit can distinguish "controller chose action 4" from
        # "action 4 was actually physically performed".
        if not hasattr(grid, "reroute_energy"):
            return "reroute_energy:invalid_target"
        try:
            result = grid.reroute_energy()
        except (networkx.NetworkXError,) as e:
            return f"reroute_energy:action_error:{type(e).__name__}"
        except Exception as e:  # noqa: BLE001
            return f"reroute_energy:action_error:{type(e).__name__}"
        if not isinstance(result, dict):
            return "reroute_energy:no_feasible_action"
        if result.get("closed"):
            return "reroute_energy:success"
        return "reroute_energy:no_feasible_action"
    return name


def _select_action(cfg: ExperimentConfig, grid, rng,
                   agent=None, predicted_load: float = 0.5,
                   risk_map: Optional[Dict[str, float]] = None,
                   twin_features: Optional[Dict[str, float]] = None) -> int:
    """Pick the controller action for this step.

    Behaviour per config:
      * ``enable_dqn`` True  → invoke the DQN agent in eval mode with
                               the Stage-43 *extended* state vector
                               (72-dim grid state + LSTM forecast +
                               storage SOC + digital-twin risk features)
                               and use its action (EHM-CRIT-007a).
      * rule_based           → 1 if any deficit, else 0
      * random               → uniform over all 5 actions
      * ``persistence``      → always 0 (no-op)

    Stage-42 health-aware behaviour: when ``cfg.enable_twin`` is True
    AND at least one asset is high-risk, the rule_based / random
    policies prefer action 3 (shift_load) — this is controller
    *behaviour* in the policy itself, not an action mask.

    ``twin_features`` (Stage-43 Repair 6): dict with keys
    ``max_risk``, ``mean_risk``, ``high_frac`` computed from the
    digital-twin registry; these enter the DQN state vector so the
    twin's health assessment actually reaches the decision.
    """
    # Stage-42: if digital twin is enabled and a high-risk asset
    # exists, the rule_based / random policies prefer load shedding
    # (action 3). This is the documented "health-aware restoration
    # preference" — it lives in the policy, not in an action mask.
    _health_aware_bias = False
    if cfg.enable_twin and risk_map is not None:
        _health_aware_bias = any(r >= 0.5 for r in risk_map.values())

    if cfg.enable_dqn and agent is not None:
        state = grid.get_rl_state()
        grid_state = grid.get_state() if hasattr(grid, "get_state") else None
        feat = twin_features or {}
        # Stage-43 (Repair 5+6): assemble the extended decision state.
        from models.rl_agent import build_extended_state
        extended_state = build_extended_state(
            state,
            predicted_load=predicted_load,
            battery_soc=_storage_level(grid, "battery"),
            supercap_soc=_storage_level(grid, "supercap"),
            twin_max_risk=float(feat.get("max_risk", 0.0)),
            twin_mean_risk=float(feat.get("mean_risk", 0.0)),
            twin_high_frac=float(feat.get("high_frac", 0.0)),
        )
        decision = agent.select_action(
            extended_state, predicted_load=predicted_load,
            grid_state=grid_state,
        )
        agent._last_decision = dict(decision)
        return int(decision["action_id"])
    label = cfg.label
    if label == "persistence":
        return 0
    if label == "random":
        # Stage-42: health-aware random: if high-risk asset present,
        # prefer action 3 (shift_load) at higher rate.
        if _health_aware_bias and float(rng.random()) < 0.5:
            return 3
        return int(rng.integers(0, len(_ACTION_NAMES)))
    if label == "rule_based" or not cfg.enable_dqn:
        # Stage-42: health-aware rule-based: if high-risk asset, shed
        # 15% load (action 3). Otherwise fall back to deficit logic.
        if _health_aware_bias:
            return 3
        for n in grid.nodes.values():
            deficit = float(getattr(n, "deficit", 0.0) or 0.0)
            if deficit > 0.0:
                return 1
        return 0
    return 1


def _storage_level(grid, kind: str) -> float:
    """Grid-scale storage SOC for the DQN decision state.

    Reads ONLY the dedicated grid storage node (STORAGE_BAT or STORAGE_SC),
    NOT house storage. House storage is autonomous and not directly
    controllable by the DQN.
    """
    if kind == "battery":
        node = grid.nodes.get("STORAGE_BAT")
        if node is not None and not getattr(node, "failed", False) and not getattr(node, "isolated", False):
            return float(getattr(node, "battery_level", 0.0) or 0.0)
        return 0.0
    elif kind == "supercap":
        node = grid.nodes.get("STORAGE_SC")
        if node is not None and not getattr(node, "failed", False) and not getattr(node, "isolated", False):
            return float(getattr(node, "supercap_level", 0.0) or 0.0)
        return 0.0
    return 0.0


# ----------------------------------------------------------------------
# Single run
# ----------------------------------------------------------------------

def _node_load(node) -> float:
    """Best-effort load extraction; returns 0.0 for stub nodes."""
    return float(getattr(node, "load", 0.0) or 0.0)


def _node_type(node) -> str:
    return str(getattr(node, "node_type", "") or "")


def _node_failed(node) -> bool:
    return bool(
        getattr(node, "failed", False)
        or getattr(node, "isolated", False)
    )


_CONSUMER_TYPES = ("house", "hospital", "industry", "hospital_icu")
_CRITICAL_TYPES = ("hospital", "hospital_icu")


def run_single(
    *,
    config: ExperimentConfig,
    scenario: Scenario,
    run_seed: Optional[int] = None,
) -> dict:
    """Run a single (config, scenario) pair and return a serialisable dict.

    The returned dict has the schema::

        {
          "config":         { ... config.to_dict() ... },
          "scenario":       { ... scenario.to_dict() ... },
          "validity":       { ... ValidityReport.to_dict() ... },
          "metrics":        { ... MetricCollector.summary() ... },
          "controller_label": config.label,
          "active_modules":  config.active_modules(),
          "disabled_modules": config.disabled_modules(),
        }

    ``run_seed`` overrides ``config.seed`` and is the seed used for the
    grid, the DQN weights and the random policy. Batch callers pass the
    scenario's seed so grid and scenario stay consistent per seed.
    """
    effective_seed = config.seed if run_seed is None else int(run_seed)
    # Determinism: pin Python / NumPy / PyTorch RNGs before anything is
    # constructed so the grid, the DQN weights and the random policy all
    # reproduce for the same seed (EHM-HIGH-009, EHM-CRIT-007a).
    set_global_seed(effective_seed)
    # Stage-43 (RNG isolation): split the master seed into independent
    # per-stream seeds so the controller and the training pipeline can
    # never perturb the environment noise stream.
    stream_seeds = derive_stream_seeds(effective_seed)
    grid = _build_grid(effective_seed, rng_seed=stream_seeds["environment"])
    controller_rng = make_rng(stream_seeds["controller"])
    collector = MetricCollector()
    # Track controller exceptions for the validity report.
    controller_exceptions: list = []

    # Stage-42: decode the scenario spec (encoded in scenario.label).
    _spec_label = "A"
    _spec_demand_mult = 1.0
    _spec_renew_mult = 1.0
    _spec_battery_soc = None
    _spec_health_override: Dict[str, float] = {}
    try:
        from experiments.scenario_matrix import SCENARIO_MATRIX as _SM
        _SM_BY_LABEL = {s.label: s for s in _SM}
        if scenario.label and "|" in scenario.label:
            parts = scenario.label.split("|")
            _spec_label = parts[0]
            for p in parts[1:]:
                if p.startswith("d="):
                    _spec_demand_mult = float(p.split("=", 1)[1])
                elif p.startswith("r="):
                    _spec_renew_mult = float(p.split("=", 1)[1])
                elif p.startswith("soc="):
                    v = p.split("=", 1)[1]
                    _spec_battery_soc = None if v == "na" else float(v)
            if _spec_label in _SM_BY_LABEL:
                _spec_health_override = dict(
                    _SM_BY_LABEL[_spec_label].health_override
                )
    except Exception:
        pass

    # Apply spec multipliers to the grid.
    # Stage-43 (Repair 2): the demand / renewable multipliers are stored
    # ON the grid and applied by ``_apply_time_curves`` every step, so
    # they persist for the whole run instead of being overwritten by the
    # load / solar / wind curves. For consumers whose load is static
    # (hospital, industry, transformer feeders) we still scale the base
    # load once here — that IS the persistent effect for those nodes.
    if _spec_demand_mult != 1.0 or _spec_renew_mult != 1.0:
        try:
            grid.demand_multiplier = float(_spec_demand_mult)
            grid.renewable_multiplier = float(_spec_renew_mult)
            for n in grid.nodes.values():
                nt = getattr(n, "node_type", "")
                if nt in ("hospital", "industry", "hospital_icu"):
                    base = float(getattr(n, "_base_load", 0.0) or 0.0)
                    setattr(n, "_base_load", base * _spec_demand_mult)
                    setattr(n, "load", base * _spec_demand_mult)
        except Exception:
            pass

    # Apply spec battery SOC override.
    if _spec_battery_soc is not None:
        try:
            for n in grid.nodes.values():
                nt = getattr(n, "node_type", "")
                if nt == "house" or nt == "battery":
                    setattr(n, "battery_level", float(_spec_battery_soc))
        except Exception:
            pass

    # Stage-42 wiring: initialise the digital-twin registry and the
    # LSTM history. Both are gated by config flags inside the loop.
    _twin_registry = None
    if config.enable_twin or config.enable_predictive_healing:
        try:
            _twin_registry = _build_twin_registry(grid)
            # Apply spec pre-ageing (Scenario H and similar).
            if _spec_health_override:
                from experiments.info_flow import _pre_age_twins
                _pre_age_twins(_twin_registry, _spec_health_override)
        except Exception:
            _twin_registry = None
    # LSTM forecaster: construct ONCE per run (training is expensive).
    # Stage-43 (RNG isolation): LSTM pretraining must be RNG-neutral —
    # it is wrapped in a torch RNG fork and the numpy global state is
    # restored afterwards, so ``enable_lstm`` can no longer change the
    # DQN's random-initialised weights (Stage-42.5 finding 6).
    _lstm_forecaster = None
    if config.enable_lstm:
        try:
            import numpy as _np
            import torch as _torch
            _np_state = _np.random.get_state()
            with _torch.random.fork_rng(devices=[]):
                from models.lstm_model import DemandForecaster
                _lstm_forecaster = DemandForecaster()
            _np.random.set_state(_np_state)
        except Exception:
            _lstm_forecaster = None
    # LSTM history: (aggregate_load, aggregate_gen, weather) tuples
    # from timesteps <= current step. No future data.
    _lstm_history: "deque[tuple[float, float, float]]" = __import__(
        "collections"
    ).deque(maxlen=10)
    # Approximate weather proxy from scenario.weather_mode (Stage-42
    # honest framing: the LSTM's third channel is currently a
    # scenario-level constant, not per-step weather).
    _weather_proxy = {
        "normal": 0.2,
        "storm": 0.85,
        "heatwave": 0.5,
    }.get(str(getattr(scenario, "weather_mode", "normal")), 0.2)

    # DQN agent — invoked in eval mode (greedy, no replay buffer writes)
    # so the ablation measures the policy, not an in-run training loop.
    # Stage-43 (RNG isolation): the torch stream is re-seeded from the
    # training stream immediately before construction, so the DQN's
    # weights depend ONLY on the training seed — never on whether the
    # LSTM was built first (Stage-42.5 finding 6).
    agent = None
    if config.enable_dqn:
        import torch  # type: ignore
        from models.rl_agent import DQNAgent, EXTENDED_STATE_DIM

        # Stage-43 (Repair 4): the DQN is NEVER trained inside an
        # experiment run. ``config.checkpoint_path`` points at a frozen
        # policy produced by ``dqn_training.py``; ``trained_dqn`` loads
        # it. Without a checkpoint the agent keeps freshly seeded,
        # random-initialised weights — that IS the ``untrained_dqn``
        # policy, and its training stream is re-seeded so the weights
        # depend only on the seed (Stage-42.5 finding 6).
        torch.manual_seed(stream_seeds["training"])
        ckpt = getattr(config, "checkpoint_path", None) or ""
        if ckpt and os.path.exists(ckpt):
            try:
                agent = DQNAgent.load_checkpoint(
                    ckpt, state_dim=EXTENDED_STATE_DIM, eval_mode=True,
                )
            except Exception as exc:
                controller_exceptions.append(("checkpoint", repr(exc)))
                agent = DQNAgent(state_dim=EXTENDED_STATE_DIM)
                agent.eval_mode()
        else:
            agent = DQNAgent(state_dim=EXTENDED_STATE_DIM)
            agent.eval_mode()

    faults_by_step: Dict[int, list] = {}
    for f in scenario.faults:
        faults_by_step.setdefault(f.timestep, []).append(f)

    # Per-fault stabilisation tracker (fault dataclass is frozen, so we
    # keep side-state in a dict keyed by fault id).
    _fault_state: Dict[int, Dict[str, int]] = {}

    # Stage-43: per-step pre-action environment observation trace
    # (aggregate load, aggregate gen). Used to prove paired controllers
    # share the identical environment stream (RNG isolation).
    _env_trace: list = []

    # Stage-43 (Repair 8): the EMS is a PERSISTENT controller built ONCE
    # per run, so its storage SOC drains and its decisions carry over
    # between steps (a fresh EMS per step could never learn anything).
    _ems_instance = None
    if config.enable_ems:
        try:
            from simulation.ems import EnergyManagementSystem
            _ems_instance = EnergyManagementSystem(use_pypsa=False)
        except Exception:
            _ems_instance = None

    # Stage-43 (Repair 6): digital-twin feature vector that reaches the
    # DQN decision each step (computed AFTER the twin registry tick).
    _twin_features: Dict[str, float] = {
        "max_risk": 0.0, "mean_risk": 0.0, "high_frac": 0.0,
    }

    # Stage-43 (Repair 12): XAI artifacts recorded when enable_xai.
    _xai_trace: list = []

    for step in range(scenario.total_steps):
        # Fault injection
        for f in faults_by_step.get(step, []):
            try:
                grid.inject_failure(f.target)
            except Exception as exc:
                controller_exceptions.append(
                    ("inject_failure", repr(exc))
                )
            baseline_load = sum(
                _node_load(n) for n in grid.nodes.values()
                if _node_type(n) in _CONSUMER_TYPES
            )
            baseline_critical = sum(
                _node_load(n) for n in grid.nodes.values()
                if _node_type(n) in _CRITICAL_TYPES
            )
            collector.record_fault(
                timestep=f.timestep,
                target=f.target,
                baseline_load_mw=baseline_load,
                baseline_critical_mw=baseline_critical,
                duration_steps=f.duration_steps,
            )

        # Observe current state
        try:
            grid.update_power_flow()
        except Exception:
            pass

        # ---- Stage-42: append observation to LSTM history (past only).
        try:
            _l, _g = _aggregate_grid_load_and_gen(grid)
            _lstm_history.append((_l, _g, _weather_proxy))
            _env_trace.append(
                (round(float(_l), 6), round(float(_g), 6))
            )
        except Exception:
            pass

        # ---- Stage-42: tick the digital-twin registry if enabled.
        if config.enable_twin and _twin_registry is not None:
            try:
                _tick_twin_registry(grid, _twin_registry)
            except Exception:
                pass

        # ---- Stage-43 (Repair 6): reduce the twin registry to the
        # feature vector that reaches the DQN decision this step.
        try:
            if _twin_registry is not None:
                _risk_vals = list(
                    _twin_risk_map(_twin_registry).values()
                )
                if _risk_vals:
                    _twin_features = {
                        "max_risk": float(max(_risk_vals)),
                        "mean_risk": float(sum(_risk_vals) / len(_risk_vals)),
                        "high_frac": float(
                            sum(1 for r in _risk_vals if r >= 0.5)
                            / len(_risk_vals)
                        ),
                    }
        except Exception:
            _twin_features = {
                "max_risk": 0.0, "mean_risk": 0.0, "high_frac": 0.0,
            }

        # ---- Stage-42: predictive-healer reads twin risk map and
        # records preparation events. Stage-43 (Repair 7): when the
        # predictive-healing module is enabled it also takes a REAL
        # physical action — pre-closing the nearest open tie switch to
        # each high-risk asset so the grid is prepared for a potential
        # fault (``apply_physical=True``).
        if config.enable_predictive_healing and _twin_registry is not None:
            try:
                _predictive_preparation(
                    grid,
                    _twin_risk_map(_twin_registry),
                    metric_collector=collector,
                    apply_physical=True,
                )
            except Exception:
                pass

        # ---- Stage-42: LSTM forecast (gated by enable_lstm).
        if config.enable_lstm and _lstm_forecaster is not None:
            try:
                seq = list(_lstm_history)
                if len(seq) < 10:
                    seq = [seq[0]] * (10 - len(seq)) + seq if seq else [
                        (0.5, 0.5, _weather_proxy)
                    ] * 10
                # Use the pre-built forecaster; no retraining per step.
                predicted_load = float(
                    _lstm_forecaster.predict(
                        [[load, gen, weather] for load, gen, weather in seq]
                    )
                )
                collector.record_lstm_forecast(predicted_load)
            except Exception:
                predicted_load = 0.5
        else:
            # Stage-41 default: 0.5 sentinel. Documented in the audit.
            predicted_load = 0.5

        # Compute risk map for health-aware controllers.
        _risk_map: Dict[str, float] = {}
        if _twin_registry is not None:
            try:
                _risk_map = _twin_risk_map(_twin_registry)
            except Exception:
                _risk_map = {}

        # Controller action (controller stream only — never the
        # environment stream, Stage-43 RNG isolation).
        action = _select_action(
            config, grid, controller_rng, agent=agent,
            predicted_load=predicted_load, risk_map=_risk_map,
            twin_features=_twin_features,
        )

        # Stage-43 (Repair 12): record the decision's reasoning +
        # confidence for the XAI trail when enable_xai.
        if config.enable_xai and agent is not None:
            _last = getattr(agent, "_last_decision", None)
            if _last is not None:
                _xai_trace.append({
                    "timestep": int(step),
                    "action": int(action),
                    "reasoning": str(_last.get("reasoning", "")),
                    "confidence": float(_last.get("confidence", 0.0)),
                    "epsilon": float(_last.get("epsilon", 0.0)),
                })

        # Apply the action's physical effect (every policy — the DQN's
        # chosen action must actually change the grid, EHM-CRIT-007a).
        # Stage-43 (Repair 12): enable_storage gates the storage-using
        # actions (1 use_battery, 2 use_supercapacitor) — when storage
        # is disabled those actions are no-ops by design.
        if hasattr(grid, "nodes"):
            try:
                _action_id = int(action)
                if (not config.enable_storage
                        and _action_id in (1, 2)):
                    pass
                else:
                    _dispatch_action(grid, action)
            except Exception as exc:
                controller_exceptions.append(("dispatch", repr(exc)))

        # Advance the simulation clock on EVERY timestep for EVERY policy
        # — storage must not gate time advancement (EHM-CRIT-007b).
        try:
            if hasattr(grid, "step"):
                grid.step()
        except Exception as exc:
            controller_exceptions.append(("step", repr(exc)))

        # ---- Stage-42: EMS dispatch if enabled (after grid.step so
        # the EMS sees the post-step imbalance). Stage-43 (Repair 8):
        # ONE persistent EMS instance is reused across steps — its SOC
        # drains and its dispatch history carry over.
        if config.enable_ems and _ems_instance is not None:
            try:
                _run_ems(
                    grid,
                    metric_collector=collector,
                    ems_instance=_ems_instance,
                )
            except Exception:
                pass

        # Let FLISR restore if enabled
        if config.enable_flisr and step % 4 == 0 and step > 0:
            try:
                if hasattr(grid, "flisr_9stage"):
                    grid.flisr_9stage()
                elif hasattr(grid, "flisr_restore"):
                    grid.flisr_restore()
            except Exception as exc:
                controller_exceptions.append(("flisr", repr(exc)))

        # Record (settle the grid state after the step / FLISR)
        try:
            grid.update_power_flow()
        except Exception:
            pass
        collector.record_step(
            grid=grid,
            timestep=step,
            controller_action=action,
            action_legal=True,
        )

        # Mark each fault "restored" the first time its *own* contribution
        # to failed-node count stops growing. The legacy "no failed nodes
        # at all" criterion is unsatisfiable in practice because the
        # faulted component itself stays ``failed=True`` permanently.
        #
        # Restoration criterion: a fault is restored once the cumulative
        # count of failed nodes has stabilised for ``>= 4`` consecutive
        # steps following the fault. "Stabilised" means the failed-node
        # count is unchanged across two consecutive snapshots -- this is
        # the proxy for "no more downstream load shedding is occurring".
        #
        # The criterion is deterministic, uses only past grid state, and
        # does not depend on any unavailable future information.
        if config.enable_flisr:
            failed_count = sum(
                1 for n in grid.nodes.values() if _node_failed(n)
            )
            for f in scenario.faults:
                if f.timestep > step:
                    continue
                fid = id(f)
                state = _fault_state.setdefault(
                    fid, {"last_failed_count": -1, "stable_steps": 0,
                          "restored": False},
                )
                if state["restored"]:
                    continue
                if f.timestep == step:
                    state["last_failed_count"] = failed_count
                    state["stable_steps"] = 0
                    continue
                last = state["last_failed_count"]
                stable = state["stable_steps"]
                if failed_count == last:
                    stable = stable + 1
                else:
                    stable = 0
                state["last_failed_count"] = failed_count
                state["stable_steps"] = stable
                if stable >= 4:
                    state["restored"] = True
                    collector.mark_restoration_complete(
                        fault_target=f.target, timestep=step,
                    )

    validity = check_run_validity(grid)

    # ── Stage-43 (Repair 13): environment fingerprints ─────────────────
    # Grid / demand / renewable / fault hashes let paired comparisons
    # prove the controllers saw the IDENTICAL environment.
    fingerprints = _environment_fingerprints(grid, scenario)

    # ── DC PF diagnostic capture (EHM-HIGH-005) ──────────────────────
    # Capture convergence + KCL residual from the last DC PF run. If
    # the grid doesn't expose dc_state (e.g. stub grid in unit tests),
    # we record NaN as a sentinel so the JSON stays serialisable.
    pf_diag: Dict[str, float] = {
        "dc_converged": -1,        # -1 = unavailable; 0 = no; 1 = yes
        "dc_kcl_residual_max": float("nan"),
        "dc_bus_count": 0,
    }
    try:
        dc_state = getattr(grid, "dc_state", None)
        if dc_state is not None:
            pf_diag["dc_converged"] = 1 if bool(getattr(dc_state, "converged", False)) else 0
            pf_diag["dc_kcl_residual_max"] = float(
                getattr(dc_state, "kcl_residual_max", float("nan"))
            )
            pf_diag["dc_bus_count"] = int(getattr(dc_state, "bus_count", 0) or 0)
    except Exception:
        pass

    if controller_exceptions:
        from experiments.validity import ValidityReport, InvalidRunReason
        rep = ValidityReport(
            valid=False,
            invalid_reason=InvalidRunReason.CONTROLLER_FAILED.value,
            timestamp_step=0,
            notes={"controller_exceptions": controller_exceptions},
            details={"controller": repr(controller_exceptions[-1])},
        )
        validity = rep
    return {
        "config": config.to_dict(),
        "scenario": scenario.to_dict(),
        "validity": validity.to_dict(),
        "metrics": collector.summary(),
        "controller_label": config.label,
        "active_modules": config.active_modules(),
        "disabled_modules": config.disabled_modules(),
        "pf_diagnostic": pf_diag,
        # Stage-43 (RNG isolation): record every stream seed + repo SHA
        # so any run can be reproduced or audited.
        "seeds": dict(stream_seeds),
        "git_sha": _git_sha(),
        "environment_trace": list(_env_trace),
        "fingerprints": fingerprints,
        "xai_trace": list(_xai_trace),
    }


def _environment_fingerprints(grid, scenario) -> Dict[str, str]:
    """Deterministic SHA-256 fingerprints of the environment inputs a
    controller sees: topology+static params (grid), demand profile
    (base loads × demand multiplier), renewable profile (base
    generation × renewable multiplier) and the fault plan. Paired
    comparisons must have matching fingerprints for every stream."""
    import hashlib as _hashlib

    def _h(obj) -> str:
        try:
            payload = json.dumps(obj, sort_keys=True, default=str)
        except Exception:  # noqa: BLE001
            payload = repr(obj)
        return _hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    grid_hash, demand_hash, renew_hash = {}, {}, {}
    for nid, n in grid.nodes.items():
        ntype = str(getattr(n, "node_type", "") or "")
        grid_hash[nid] = ntype
        if ntype in ("house", "hospital", "industry", "hospital_icu"):
            demand_hash[nid] = (
                float(getattr(n, "_base_load", 0.0) or 0.0)
                * float(getattr(grid, "demand_multiplier", 1.0) or 1.0)
            )
        if ntype in ("generator_solar", "generator_wind"):
            renew_hash[nid] = (
                float(getattr(n, "_base_generation", 0.0) or 0.0)
                * float(getattr(grid, "renewable_multiplier", 1.0) or 1.0)
            )
    fault_hash = [
        {"target": f.target, "t": f.timestep, "d": f.duration_steps}
        for f in getattr(scenario, "faults", [])
    ]
    return {
        "grid_hash": _h(grid_hash),
        "demand_hash": _h(demand_hash),
        "renewable_hash": _h(renew_hash),
        "fault_hash": _h(fault_hash),
    }


# ----------------------------------------------------------------------
# Batch runner
# ----------------------------------------------------------------------

def run_experiment(
    *,
    configs: List[ExperimentConfig],
    seeds: int = 1,
    ticks: int = 50,
    faults_per_run: int = 5,
    weather_modes: Optional[List[str]] = None,
    output_path: Optional[str] = None,
    write_csv: bool = False,
    write_manifest_path: Optional[str] = None,
) -> dict:
    """Run a batch of (config, seed, weather_mode, scenario) tuples and
    persist the results.

    The return value is the manifest dict (also written to
    ``output_path``); if ``output_path`` is None, no file is written.
    """
    from experiments.scenario import make_scenario

    if weather_modes is None:
        weather_modes = ["normal"]

    runs: List[dict] = []
    manifest = {
        "schema_version": 1,
        "seeds": int(seeds),
        "ticks": int(ticks),
        "faults_per_run": int(faults_per_run),
        "weather_modes": list(weather_modes),
        "configs": [c.label for c in configs],
        "runs": [],
    }

    for seed_id in range(seeds):
        for weather in weather_modes:
            for cfg in configs:
                scenario = make_scenario(
                    seed=seed_id,
                    total_steps=ticks,
                    fault_count=faults_per_run,
                    weather_mode=weather,
                )
                result = run_single(
                    config=cfg, scenario=scenario, run_seed=seed_id,
                )
                result["seed_id"] = seed_id
                result["seed"] = seed_id
                result["weather_mode"] = weather
                runs.append(result)
                manifest["runs"].append({
                    "controller_label": cfg.label,
                    "seed_id": seed_id,
                    "seed": seed_id,
                    "weather_mode": weather,
                    "scenario": result["scenario"],
                    "metrics": result["metrics"],
                    "validity": result["validity"],
                })

    manifest["n_total"] = len(runs)
    manifest["n_runs"] = len(runs)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)

    if write_manifest_path:
        Path(write_manifest_path).parent.mkdir(parents=True, exist_ok=True)
        with open(write_manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)

    return manifest