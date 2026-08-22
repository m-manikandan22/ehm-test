"""
stage47_training.py — Stage 47 DQN Training with Corrected Storage Observation

Trains a NEW DQN using the repaired storage observation representation
(grid-scale STORAGE_BAT and STORAGE_SC SOC directly, not masked by houses).

Checkpoint: dqn_stage47_storage_aware.pt (NEVER overwrites dqn_stage44.pt)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import torch

from simulation.grid import SmartGrid
from utils.seeds import derive_stream_seeds, set_global_seed

from experiments.experiment_config import ExperimentConfig
from experiments.runner import (
    _dispatch_action,
    _aggregate_grid_load_and_gen,
)
from experiments.train_scenario_generator import (
    TrainingScenario,
    apply_training_scenario,
    sample_training_scenarios,
)
from models.rl_agent import (
    DQNAgent,
    EXTENDED_STATE_DIM,
    build_extended_state,
)


HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "checkpoints" / "dqn_stage47_storage_aware.pt"
RESULTS_DIR = HERE / "results" / "stage47"


def _git_sha() -> str:
    try:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=repo_root,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "no_git"


def _build_frozen_lstm(master_seed: int):
    """Build the LSTM forecaster once per run, RNG-forked."""
    import numpy as _np
    stream_seeds = derive_stream_seeds(master_seed)
    _np_state = _np.random.get_state()
    with torch.random.fork_rng(devices=[]):
        from models.lstm_model import DemandForecaster
        forecaster = DemandForecaster()
    _np.random.set_state(_np_state)
    return forecaster, stream_seeds


def _lstm_predict(fc, history: list) -> float:
    """Predict next-step load using only past observations."""
    seq = list(history)
    if not seq:
        return 0.5
    if len(seq) < 10:
        seq = [seq[0]] * (10 - len(seq)) + seq
    return float(fc.predict([[l, g, w] for l, g, w in seq]))


def _apply_health_override(grid, registry, health_override: Dict[str, float]) -> None:
    """Pre-age the named twins if the registry is available."""
    if not health_override or registry is None:
        return
    try:
        from experiments.info_flow import _pre_age_twins
        _pre_age_twins(registry, health_override)
    except Exception:
        pass


def _build_twin_registry(grid):
    try:
        from experiments.info_flow import _build_twin_registry
        return _build_twin_registry(grid)
    except Exception:
        return None


def _tick_twin(grid, registry) -> None:
    if registry is None:
        return
    try:
        from experiments.info_flow import _tick_twin_registry
        _tick_twin_registry(grid, registry)
    except Exception:
        pass


def _twin_features(registry) -> Dict[str, float]:
    out = {"max_risk": 0.0, "mean_risk": 0.0, "high_frac": 0.0}
    if registry is None:
        return out
    try:
        from experiments.info_flow import _twin_risk_map
        vals = list(_twin_risk_map(registry).values())
        if vals:
            out["max_risk"] = float(max(vals))
            out["mean_risk"] = float(sum(vals) / len(vals))
            out["high_frac"] = float(
                sum(1 for r in vals if r >= 0.5) / len(vals)
            )
    except Exception:
        pass
    return out


def train_stage47_dqn(
    *,
    master_seed: int = 42,  # Different from Stage-44 seed (0)
    episodes: int = 50,     # More episodes for learning
    steps_per_episode: int = 80,
    output_path: Optional[str] = None,
    state_dim: Optional[int] = None,
) -> dict:
    """Train the Stage-47 DQN with corrected storage observation."""

    if state_dim is None:
        state_dim = EXTENDED_STATE_DIM

    stream_seeds = derive_stream_seeds(int(master_seed))
    torch.manual_seed(int(stream_seeds["training"]))
    agent = DQNAgent(state_dim=int(state_dim))

    # Build the LSTM forecaster once (RNG-forked).
    lstm_forecaster, _ = _build_frozen_lstm(int(master_seed))

    # Sample the training scenarios.
    scenarios = sample_training_scenarios(
        master_seed=int(master_seed),
        n_episodes=int(episodes),
        total_steps=int(steps_per_episode),
    )

    # Per-episode log buffer.
    log: Dict[str, Any] = {
        "master_seed": int(master_seed),
        "stream_seeds": dict(stream_seeds),
        "episodes": int(episodes),
        "steps_per_episode": int(steps_per_episode),
        "scenario_labels": [s.label for s in scenarios],
        "scenario_conditions": [s.condition for s in scenarios],
        "mean_reward_per_episode": [],
        "action_counts_per_episode": [],
        "num_failed_per_episode": [],
        "num_isolated_per_episode": [],
        "twin_max_risk_per_episode": [],
        "forecast_feature_per_episode": [],
        "battery_soc_per_episode": [],
        "supercap_soc_per_episode": [],
        "storage_action_1_per_episode": [],   # use_battery
        "storage_action_2_per_episode": [],   # use_supercapacitor
        "reward_components_per_episode": [],
    }

    total_step = 0
    for ep, scenario in enumerate(scenarios):
        env_seed = int(stream_seeds["environment"]) + ep * 10_007
        set_global_seed(int(master_seed) + ep)
        grid = SmartGrid(seed=int(master_seed) + ep, rng_seed=env_seed)
        apply_training_scenario(grid, scenario)
        try:
            grid.update_power_flow()
        except Exception:
            pass

        registry = _build_twin_registry(grid)
        if registry is not None and scenario.health_override:
            _apply_health_override(grid, registry, scenario.health_override)

        # Per-step LSTM history deque (only past observations).
        from collections import deque
        lstm_history: "deque" = deque(maxlen=10)
        weather_proxy = max(0.0, min(1.0, scenario.demand_multiplier - 1.0))

        # Pre-stage faults to a per-step schedule.
        faults_by_step: Dict[int, list] = {}
        for t, target in scenario.fault_plan:
            faults_by_step.setdefault(int(t), []).append(str(target))

        ep_reward = 0.0
        ep_actions: Counter = Counter()
        ep_num_failed: List[int] = []
        ep_num_isolated: List[int] = []
        ep_twin_max: List[float] = []
        ep_forecast: List[float] = []
        ep_battery: List[float] = []
        ep_supercap: List[float] = []
        ep_storage_1: List[int] = []  # action 1 count
        ep_storage_2: List[int] = []  # action 2 count
        ep_components_log: List[Dict[str, float]] = []

        for step in range(int(scenario.total_steps)):
            # Apply scheduled faults at the start of the step.
            for target in faults_by_step.get(step, []):
                try:
                    grid.inject_failure(target)
                except Exception:
                    pass

            try:
                grid.update_power_flow()
            except Exception:
                pass

            # Tick the twin registry BEFORE we read its features.
            _tick_twin(grid, registry)

            # Past-only LSTM input.
            try:
                _l, _g = _aggregate_grid_load_and_gen(grid)
                lstm_history.append((_l, _g, weather_proxy))
            except Exception:
                pass

            # Real LSTM prediction (no future data).
            forecast = _lstm_predict(lstm_forecaster, list(lstm_history))

            # Twin features for this step.
            tfeats = _twin_features(registry)

            # State vector with CORRECTED storage observation.
            try:
                rl_state = grid.get_rl_state()
            except Exception:
                rl_state = [0.0] * 72
            try:
                grid_state = grid.get_state()
            except Exception:
                grid_state = None

            # Use the corrected _storage_level from runner (reads only STORAGE_BAT/SC)
            from experiments.runner import _storage_level
            battery_soc = _storage_level(grid, "battery")
            supercap_soc = _storage_level(grid, "supercap")

            extended = build_extended_state(
                rl_state,
                predicted_load=forecast,
                battery_soc=battery_soc,
                supercap_soc=supercap_soc,
                twin_max_risk=tfeats["max_risk"],
                twin_mean_risk=tfeats["mean_risk"],
                twin_high_frac=tfeats["high_frac"],
            )

            decision = agent.select_action(
                extended, predicted_load=forecast,
                grid_state=grid_state,
            )
            action_id = int(decision["action_id"])
            ep_actions[action_id] += 1
            if action_id == 1:
                ep_storage_1.append(1)
            if action_id == 2:
                ep_storage_2.append(1)

            try:
                _dispatch_action(grid, action_id)
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

            # Build the *next* state vector AFTER the step.
            try:
                _l, _g = _aggregate_grid_load_and_gen(grid)
                lstm_history.append((_l, _g, weather_proxy))
            except Exception:
                pass
            next_forecast = _lstm_predict(
                lstm_forecaster, list(lstm_history),
            )
            next_tfeats = _twin_features(registry)
            try:
                next_rl_state = grid.get_rl_state()
            except Exception:
                next_rl_state = rl_state
            next_battery_soc = _storage_level(grid, "battery")
            next_supercap_soc = _storage_level(grid, "supercap")
            next_extended = build_extended_state(
                next_rl_state,
                predicted_load=next_forecast,
                battery_soc=next_battery_soc,
                supercap_soc=next_supercap_soc,
                twin_max_risk=next_tfeats["max_risk"],
                twin_mean_risk=next_tfeats["mean_risk"],
                twin_high_frac=next_tfeats["high_frac"],
            )

            # Reward with conditional supercap bonus.
            try:
                pre_sc = 0.0
                if grid_state is not None and grid_state.get("nodes"):
                    for nid, n in grid_state["nodes"].items():
                        nt = str(n.get("node_type", ""))
                        if nt == "house" or nt == "supercap":
                            pre_sc = max(
                                pre_sc,
                                float(n.get("supercap_level", 0.0) or 0.0),
                            )
            except Exception:
                pre_sc = 0.0
            post_sc = float(_storage_level(grid, "supercap"))
            reward_components = agent._compute_reward_components(
                grid_state,
                action_name=decision["action_name"],
                supercap_level_pre=pre_sc,
                supercap_level_post=post_sc,
            )
            reward = float(reward_components["total"])
            ep_reward += reward
            agent.store_experience(
                extended, action_id, reward, next_extended, done=False,
            )
            total_step += 1
            ep_components_log.append(reward_components)

            # Bookkeeping.
            sys = (grid_state or {}).get("system", {})
            ep_num_failed.append(int(sys.get("failed_count", 0)))
            ep_num_isolated.append(int(sys.get("isolated_count", 0)))
            ep_twin_max.append(float(tfeats["max_risk"]))
            ep_forecast.append(float(forecast))
            ep_battery.append(float(battery_soc))
            ep_supercap.append(float(supercap_soc))

        log["mean_reward_per_episode"].append(
            ep_reward / max(1, int(scenario.total_steps))
        )
        log["action_counts_per_episode"].append(
            {int(k): int(v) for k, v in ep_actions.items()}
        )
        if ep_components_log:
            comp_keys = (
                "stability_voltage", "stability_freq", "balance_penalty",
                "failed_penalty", "isolated_penalty", "loss_penalty",
                "supercap_spike_bonus", "reroute_bonus",
            )
            agg = {
                k: float(np.mean([c[k] for c in ep_components_log]))
                for k in comp_keys
            }
            log.setdefault(
                "reward_components_per_episode", []
            ).append(agg)
        log["num_failed_per_episode"].append(ep_num_failed)
        log["num_isolated_per_episode"].append(ep_num_isolated)
        log["twin_max_risk_per_episode"].append(ep_twin_max)
        log["forecast_feature_per_episode"].append(ep_forecast)
        log["battery_soc_per_episode"].append(ep_battery)
        log["supercap_soc_per_episode"].append(ep_supercap)
        log["storage_action_1_per_episode"].append(len(ep_storage_1))
        log["storage_action_2_per_episode"].append(len(ep_storage_2))

    # Persist the checkpoint.
    out = output_path or str(DEFAULT_OUTPUT)
    agent.save_checkpoint(
        out,
        seeds=dict(stream_seeds),
        git_sha=_git_sha(),
        extra={
            "pipeline": "stage47_training",
            "master_seed": int(master_seed),
            "episodes": int(episodes),
            "steps_per_episode": int(steps_per_episode),
            "total_transitions": int(total_step),
            "mean_reward_per_episode": log["mean_reward_per_episode"],
            "action_counts_per_episode": log["action_counts_per_episode"],
            "scenario_labels": log["scenario_labels"],
            "scenario_conditions": log["scenario_conditions"],
            "final_epsilon": float(agent.epsilon),
            "storage_observation": "corrected_grid_only",
        },
    )

    log["checkpoint_path"] = out
    log["total_transitions"] = int(total_step)

    # Persist the training log alongside the checkpoint.
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = RESULTS_DIR / "training_log.json"
    log_path.write_text(
        json.dumps(log, indent=2, default=str), encoding="utf-8",
    )

    return log


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--master-seed", type=int, default=42)
    ap.add_argument("--episodes", type=int, default=50)
    ap.add_argument("--steps", type=int, default=80)
    ap.add_argument("--output", type=str, default=None)
    args = ap.parse_args()
    log = train_stage47_dqn(
        master_seed=args.master_seed,
        episodes=args.episodes,
        steps_per_episode=args.steps,
        output_path=args.output,
    )
    print(json.dumps(log, indent=2, default=str))


if __name__ == "__main__":
    main()