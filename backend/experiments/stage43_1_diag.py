"""stage43_1_diag.py — one-shot diagnostic harness for Stage 43.1.

This script is *instrumentation only*. It does not change the
training pipeline or the reward. It produces:

  * experiments/results/stage43_1/
      - action_validity_distribution.json
      - q_values.json
      - action_reward_statistics.json
      - controlled_states.json
      - lstm_alignment.json
      - twin_alignment.json
      - training_data.json
      - figures/

Stage 43.1 forbids changing the system to make the DQN score
better. Anything that mutates the algorithm must wait for the
STAGE_43_1_REPAIR_RECOMMENDATION.md step.

Usage:
    python -m experiments.stage43_1_diag
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import torch

from simulation.grid import SmartGrid
from utils.seeds import derive_stream_seeds, make_rng, set_global_seed

from experiments.experiment_config import ExperimentConfig
from experiments.runner import (
    _aggregate_grid_load_and_gen,
    _build_grid,
    _select_action,
)
from experiments.scenario_matrix import build_scenario, get_scenario_spec

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results" / "stage43_1"
RESULTS.mkdir(parents=True, exist_ok=True)
(RESULTS / "figures").mkdir(parents=True, exist_ok=True)
CHECKPOINT = HERE / "checkpoints" / "dqn_extended.pt"

ACTION_NAMES = [
    "increase_generation",
    "use_battery",
    "use_supercapacitor",
    "shift_load",
    "reroute_energy",
]


# ---------------------------------------------------------------------
# A. Action-mask audit
# ---------------------------------------------------------------------

def action_mask_audit(seeds: int = 5) -> None:
    """For every (scenario, seed), record per-timestep:
      - valid actions returned by the trained DQN's mask
      - selected action
    Aggregate the count of (valid_actions, selected_action) tuples.
    """
    from models.rl_agent import DQNAgent, EXTENDED_STATE_DIM

    # Load trained network once.
    agent = DQNAgent.load_checkpoint(
        str(CHECKPOINT), state_dim=EXTENDED_STATE_DIM, eval_mode=True,
    )

    scenario_labels = ["A", "E", "G", "H", "J"]
    aggregated: List[Dict[str, Any]] = []

    for slabel in scenario_labels:
        for seed in range(seeds):
            spec = get_scenario_spec(slabel)
            scenario = build_scenario(seed=seed, spec=spec)
            set_global_seed(seed)
            ss = derive_stream_seeds(seed)
            grid = _build_grid(seed, rng_seed=ss["environment"])
            controller_rng = make_rng(ss["controller"])
            valid_counter = Counter()
            selected_counter = Counter()
            per_step: List[Dict[str, Any]] = []

            for step in range(scenario.total_steps):
                # inject faults
                for f in scenario.faults:
                    if f.timestep == step:
                        try:
                            grid.inject_failure(f.target)
                        except Exception:
                            pass
                try:
                    grid.update_power_flow()
                except Exception:
                    pass

                cfg = ExperimentConfig(label="trained_dqn_seed")
                _ = _aggregate_grid_load_and_gen(grid)
                action = _select_action(
                    cfg, grid, controller_rng, agent=agent,
                    predicted_load=0.5,
                    risk_map={},
                    twin_features={},
                )
                # The mask lookup happens inside the agent — but we can
                # rebuild it directly to record *what the mask said*.
                valid = agent._valid_actions_mask(grid.get_state())
                valid_counter[tuple(sorted(valid))] += 1
                selected_counter[int(action)] += 1
                per_step.append({
                    "step": step,
                    "valid_actions": list(valid),
                    "selected": int(action),
                    "balance": grid.get_state()["system"]["balance"],
                    "failed_count": grid.get_state()["system"]["failed_count"],
                    "isolated_count": grid.get_state()["system"]["isolated_count"],
                })
                # Advance the grid so subsequent steps see a different state.
                try:
                    grid.step()
                except Exception:
                    pass

            aggregated.append({
                "scenario": slabel,
                "seed": seed,
                "valid_action_sets": {
                    ",".join(str(a) for a in sorted(k)): int(v)
                    for k, v in valid_counter.items()
                },
                "selected_actions": {
                    str(int(k)): int(v) for k, v in selected_counter.items()
                },
                "n_steps": sum(valid_counter.values()),
                "per_step": per_step,
            })

    out = {
        "n_seeds_per_scenario": seeds,
        "scenarios": scenario_labels,
        "results": aggregated,
    }
    (RESULTS / "action_validity_distribution.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8",
    )


# ---------------------------------------------------------------------
# B. Q-value audit
# ---------------------------------------------------------------------

def q_value_audit(n_states: int = 8) -> None:
    """For n_states representative states, record Q0..Q4 and the
    selected (greedy) action.
    """
    from models.rl_agent import (
        DQNAgent,
        EXTENDED_STATE_DIM,
        build_extended_state,
    )

    agent = DQNAgent.load_checkpoint(
        str(CHECKPOINT), state_dim=EXTENDED_STATE_DIM, eval_mode=True,
    )

    set_global_seed(11)
    grid = SmartGrid(seed=11)
    grid.update_power_flow()

    states: List[Dict[str, Any]] = []

    def record_state(name: str, *,
                     battery: float = 0.5, supercap: float = 0.5,
                     twin_max: float = 0.0, twin_mean: float = 0.0,
                     twin_high: float = 0.0,
                     forecast: float = 0.5,
                     extra: Dict[str, Any] | None = None) -> None:
        base = list(grid.get_rl_state())
        ext = build_extended_state(
            base, predicted_load=forecast,
            battery_soc=battery, supercap_soc=supercap,
            twin_max_risk=twin_max, twin_mean_risk=twin_mean,
            twin_high_frac=twin_high,
        )
        with torch.no_grad():
            q = agent.policy_net(
                torch.tensor(ext, dtype=torch.float32).unsqueeze(0)
            ).numpy().ravel().tolist()
        mask = agent._valid_actions_mask(grid.get_state())
        chosen = int(np.argmax([q[a] if a in mask else -1e9 for a in range(5)]))
        states.append({
            "name": name,
            "Q": q,
            "valid_actions": list(mask),
            "argmax_within_mask": chosen,
            "forecast": forecast,
            "battery_soc": battery,
            "supercap_soc": supercap,
            "twin_max_risk": twin_max,
            "twin_mean_risk": twin_mean,
            "twin_high_frac": twin_high,
            **(extra or {}),
        })

    # Diverse probe states
    record_state("baseline", battery=0.5, supercap=0.5, forecast=0.5)
    record_state("low_battery", battery=0.05, supercap=0.5, forecast=0.5)
    record_state("full_battery", battery=0.95, supercap=0.5, forecast=0.5)
    record_state("low_supercap", battery=0.5, supercap=0.05, forecast=0.5)
    record_state("high_supercap", battery=0.5, supercap=0.95, forecast=0.5)
    record_state("low_forecast", battery=0.5, supercap=0.5, forecast=0.05)
    record_state("high_forecast", battery=0.5, supercap=0.5, forecast=1.5)
    record_state("high_twin_risk", battery=0.5, supercap=0.5,
                 twin_max=0.9, twin_mean=0.6, twin_high=0.4)

    out = {
        "state_dim": EXTENDED_STATE_DIM,
        "states": states,
    }
    (RESULTS / "q_values.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8",
    )


# ---------------------------------------------------------------------
# C. Reward audit (training transitions)
# ---------------------------------------------------------------------

def reward_audit(episodes: int = 4, steps: int = 200) -> None:
    """Re-run the training loop with logging only (no checkpoints, no
    gradient updates) to record per-step
      (state, action, reward_per_component, next_state).
    This instruments the reward the *training* distribution sees.
    """
    from models.rl_agent import (
        DQNAgent,
        EXTENDED_STATE_DIM,
        build_extended_state,
        ACTIONS,
    )
    from experiments.runner import _dispatch_action

    set_global_seed(0)
    ss = derive_stream_seeds(0)
    torch.manual_seed(ss["training"])

    # Don't re-train the network — we want the *untrained* network's
    # action distribution and the *reward function's* action-conditional
    # signal. Both are independent of the loaded checkpoint.
    agent = DQNAgent(state_dim=EXTENDED_STATE_DIM)
    agent.eval_mode()

    rewards_per_action: Dict[int, List[float]] = defaultdict(list)
    full_components_per_action: Dict[int, List[Dict[str, float]]] = defaultdict(list)
    state_features: Dict[str, List[float]] = defaultdict(list)
    action_counts: Counter = Counter()
    n_transitions = 0

    for ep in range(episodes):
        env_seed = int(ss["environment"]) + ep * 10_007
        set_global_seed(0 + ep)
        grid = SmartGrid(seed=0 + ep, rng_seed=env_seed)
        for step in range(steps):
            try:
                grid.update_power_flow()
            except Exception:
                pass
            state = grid.get_rl_state()
            grid_state = grid.get_state()
            forecast = max(0.05, min(2.0,
                _aggregate_grid_load_and_gen(grid)[0] / 20.0))
            ext = build_extended_state(
                state, predicted_load=forecast,
                battery_soc=max(0.0, min(1.0,
                    sum(getattr(n, "battery_level", 0.0) or 0.0
                        for n in grid.nodes.values()) /
                    max(1, len(grid.nodes)))),
                supercap_soc=max(0.0, min(1.0,
                    sum(getattr(n, "supercap_level", 0.0) or 0.0
                        for n in grid.nodes.values()) /
                    max(1, len(grid.nodes)))),
            )
            decision = agent.select_action(
                ext, predicted_load=forecast, grid_state=grid_state,
            )
            action_id = int(decision["action_id"])
            action_name = ACTIONS[action_id]["name"]
            action_counts[action_id] += 1

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

            next_grid_state = grid.get_state()
            reward = agent.compute_reward(grid_state, action_name=action_name)
            rewards_per_action[action_id].append(float(reward))
            comp = _reward_components(grid_state, action_name)
            full_components_per_action[action_id].append(comp)

            # State-feature snapshot for the diversity audit.
            sys = grid_state["system"]
            state_features["balance"].append(float(sys["balance"]))
            state_features["avg_voltage"].append(float(sys["avg_voltage"]))
            state_features["avg_frequency"].append(float(sys["avg_frequency"]))
            state_features["num_failed"].append(float(sys["failed_count"]))
            state_features["num_isolated"].append(float(sys["isolated_count"]))
            state_features["forecast_feature"].append(float(forecast))
            n_transitions += 1

    # Aggregate per action.
    summary = []
    for aid in range(5):
        rs = rewards_per_action[aid]
        comps = full_components_per_action[aid]
        if not rs:
            summary.append({"action_id": aid,
                            "name": ACTION_NAMES[aid],
                            "n": 0})
            continue
        per_comp = defaultdict(list)
        for c in comps:
            for k, v in c.items():
                per_comp[k].append(v)
        summary.append({
            "action_id": aid,
            "name": ACTION_NAMES[aid],
            "n": len(rs),
            "mean_reward": float(np.mean(rs)),
            "median_reward": float(np.median(rs)),
            "std_reward": float(np.std(rs)),
            "min_reward": float(np.min(rs)),
            "max_reward": float(np.max(rs)),
            "mean_components": {k: float(np.mean(v))
                                for k, v in per_comp.items()},
        })

    out = {
        "n_transitions": n_transitions,
        "episodes": episodes,
        "steps_per_episode": steps,
        "action_counts": dict(action_counts),
        "per_action": summary,
        "state_features": {k: v for k, v in state_features.items()},
    }
    (RESULTS / "action_reward_statistics.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8",
    )


def _reward_components(grid_state: dict, action_name: str) -> Dict[str, float]:
    """Reproduce the reward components of compute_reward()."""
    nodes = grid_state.get("nodes", {})
    system = grid_state.get("system", {})
    avg_voltage = system.get("avg_voltage", 1.0)
    avg_freq = system.get("avg_frequency", 50.0)
    balance = system.get("balance", 0.0)
    total_energy_loss = system.get("total_energy_loss", 0.0)
    num_failed = sum(1 for n in nodes.values() if n.get("failed"))
    num_isolated = sum(1 for n in nodes.values() if n.get("isolated"))
    return {
        "stability_voltage": 5.0 * (1.0 - abs(avg_voltage - 1.0) / 0.1),
        "stability_freq":    3.0 * (1.0 - abs(avg_freq - 50.0) / 1.5),
        "balance_penalty":  -4.0 * abs(balance),
        "failed_penalty":   -10.0 * num_failed,
        "isolated_penalty": -6.0 * num_isolated,
        "loss_penalty":     -0.2 * total_energy_loss,
        "supercap_spike_bonus": 2.0 if (
            action_name == "use_supercapacitor"
            and any(n.get("load", 0) > 1.2 for n in nodes.values())
        ) else 0.0,
        "reroute_bonus":     3.0 if (
            action_name == "reroute_energy"
            and (num_failed > 0 or num_isolated > 0)
        ) else 0.0,
    }


# ---------------------------------------------------------------------
# D. Training-data audit
# ---------------------------------------------------------------------

def training_data_audit() -> None:
    """Inspect the existing checkpoint and replay-buffer artefacts.
    Drop a training_data.json with: episode count, total transitions,
    ε, mean reward per episode, per-step action distribution if
    available in the checkpoint's ``extra`` block."""
    payload = torch.load(str(CHECKPOINT), map_location="cpu",
                         weights_only=False)
    extra = dict(payload.get("extra", {}) or {})
    out = {
        "state_dim": int(payload.get("state_dim", -1)),
        "steps_done": int(payload.get("steps_done", -1)),
        "epsilon": float(payload.get("epsilon", 0.0)),
        "seeds": dict(payload.get("seeds", {}) or {}),
        "git_sha": str(payload.get("git_sha", "")),
        "extra": extra,
    }
    (RESULTS / "training_data.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8",
    )


# ---------------------------------------------------------------------
# E. Controlled state tests
# ---------------------------------------------------------------------

def controlled_state_tests() -> None:
    """Build five deterministic states A-E and for each:
      - compute valid actions under the trained agent's mask
      - compute Q0..Q4 from the trained policy net
      - record selected action
    """
    from models.rl_agent import (
        DQNAgent,
        EXTENDED_STATE_DIM,
        build_extended_state,
    )

    agent = DQNAgent.load_checkpoint(
        str(CHECKPOINT), state_dim=EXTENDED_STATE_DIM, eval_mode=True,
    )

    cases = [
        {"name": "A_deficit",
         "balanced_state": False, "balance_override": -3.0,
         "forecast": 1.2, "battery": 0.4, "supercap": 0.6,
         "twin_max": 0.0, "twin_mean": 0.0, "twin_high": 0.0,
         "has_failed": False,
         "open_ties": False},
        {"name": "B_spike",
         "balanced_state": True,
         "any_load_gt_1_2": True,
         "forecast": 0.5, "battery": 0.5, "supercap": 0.5,
         "twin_max": 0.0, "twin_mean": 0.0, "twin_high": 0.0,
         "has_failed": False,
         "open_ties": False},
        {"name": "C_sustained_deficit",
         "balanced_state": False, "balance_override": -5.0,
         "forecast": 0.5, "battery": 0.2, "supercap": 0.4,
         "twin_max": 0.0, "twin_mean": 0.0, "twin_high": 0.0,
         "has_failed": False,
         "open_ties": False},
        {"name": "D_topology_fault",
         "balanced_state": True,
         "any_load_gt_1_2": False,
         "forecast": 0.5, "battery": 0.5, "supercap": 0.5,
         "twin_max": 0.0, "twin_mean": 0.0, "twin_high": 0.0,
         "has_failed": True,
         "open_ties": True},
        {"name": "E_high_demand",
         "balanced_state": False, "balance_override": -1.0,
         "any_load_gt_1_2": True,
         "forecast": 1.5, "battery": 0.5, "supercap": 0.5,
         "twin_max": 0.0, "twin_mean": 0.0, "twin_high": 0.0,
         "has_failed": False,
         "open_ties": False},
    ]

    rows: List[Dict[str, Any]] = []
    for case in cases:
        # Construct a grid state consistent with the case's signals.
        set_global_seed(99)
        grid = SmartGrid(seed=99)
        grid.update_power_flow()
        # Override the published system aggregates by patching
        # get_state output through a wrapper.
        gs = grid.get_state()
        if "any_load_gt_1_2" in case and case["any_load_gt_1_2"]:
            # Force at least one node to look like a spike.
            for n in grid.nodes.values():
                n.load = 1.5
                break
            gs = grid.get_state()
        if "balance_override" in case:
            # Patch the system dict (the agent reads gs["system"]["balance"]).
            gs["system"]["balance"] = float(case["balance_override"])
        if "has_failed" in case and case["has_failed"]:
            # Mark the first node as failed for masking.
            any_node = next(iter(grid.nodes.values()))
            any_node.failed = True
            gs = grid.get_state()

        base = list(grid.get_rl_state())
        ext = build_extended_state(
            base, predicted_load=case["forecast"],
            battery_soc=case["battery"], supercap_soc=case["supercap"],
            twin_max_risk=case["twin_max"], twin_mean_risk=case["twin_mean"],
            twin_high_frac=case["twin_high"],
        )
        with torch.no_grad():
            q = agent.policy_net(
                torch.tensor(ext, dtype=torch.float32).unsqueeze(0)
            ).numpy().ravel().tolist()
        mask = agent._valid_actions_mask(gs)
        chosen = int(np.argmax([q[a] if a in mask else -1e9 for a in range(5)]))
        reward = agent.compute_reward(gs, action_name=ACTION_NAMES[chosen])
        # Per-component reward for this case
        comp = _reward_components(gs, ACTION_NAMES[chosen])
        rows.append({
            "case": case["name"],
            "Q": q,
            "valid_actions": list(mask),
            "selected_action": int(chosen),
            "selected_name": ACTION_NAMES[chosen],
            "reward": float(reward),
            "reward_components": comp,
            "balance_reported": float(gs["system"]["balance"]),
            "any_load_gt_1_2": bool(
                any(n.get("load", 0) > 1.2 for n in gs["nodes"].values())
            ),
            "has_failed_in_state": bool(
                any(n.get("failed") for n in gs["nodes"].values())
            ),
        })

    out = {"cases": rows}
    (RESULTS / "controlled_states.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8",
    )


# ---------------------------------------------------------------------
# F + G. LSTM + Twin alignment audits
# ---------------------------------------------------------------------

def lstm_alignment_audit() -> None:
    """Compare the LSTM forecast distribution to the stand-in
    feature used during DQN training (``_aggregate_load/20`` clipped)."""
    from collections import deque
    from models.lstm_model import DemandForecaster

    set_global_seed(31)
    grid = SmartGrid(seed=31)
    forecaster = DemandForecaster()
    history = deque(maxlen=10)
    rows = []
    for step in range(60):
        grid.update_power_flow()
        load, gen = _aggregate_grid_load_and_gen(grid)
        history.append((load, gen, 0.2))
        # LSTM prediction uses up-to-10 past observations.
        lstm_pred = forecaster.predict(
            [[l, g, w] for l, g, w in list(history)],
        )
        # Training-time stand-in: aggregate_load / 20 clipped.
        train_feat = max(0.05, min(2.0, load / 20.0))
        rows.append({
            "step": step,
            "lstm_prediction": float(lstm_pred),
            "training_feature": float(train_feat),
            "aggregate_load": float(load),
        })
        try:
            grid.step()
        except Exception:
            pass
    out = {"rows": rows,
           "note": "training_feature = aggregate_load / 20, clipped [0.05, 2.0]; "
                   "lstm_prediction = output of DemandForecaster"}
    (RESULTS / "lstm_alignment.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8",
    )


def twin_alignment_audit(seeds: int = 3) -> None:
    from experiments.info_flow import (
        _build_twin_registry,
        _tick_twin_registry,
        _twin_risk_map,
        _pre_age_twins,
    )
    from digital_twin.twin_registry import TwinRegistry

    by_scenario: Dict[str, List[float]] = {}
    for slabel in ["A", "H"]:
        all_max = []
        all_mean = []
        for seed in range(seeds):
            spec = get_scenario_spec(slabel)
            scenario = build_scenario(seed=seed, spec=spec)
            set_global_seed(seed)
            ss = derive_stream_seeds(seed)
            grid = _build_grid(seed, rng_seed=ss["environment"])
            reg = _build_twin_registry(grid)
            if slabel == "H":
                # Pre-age per spec.
                _pre_age_twins(reg, spec.health_override)
            for step in range(scenario.total_steps):
                for f in scenario.faults:
                    if f.timestep == step:
                        try:
                            grid.inject_failure(f.target)
                        except Exception:
                            pass
                _tick_twin_registry(grid, reg)
                try:
                    grid.step()
                except Exception:
                    pass
            risk_map = _twin_risk_map(reg)
            vals = list(risk_map.values())
            if vals:
                all_max.append(max(vals))
                all_mean.append(float(np.mean(vals)))
        by_scenario[slabel] = {
            "max_risk_max_overall": float(max(all_max)) if all_max else None,
            "mean_risk_mean_over_seeds":
                float(np.mean(all_mean)) if all_mean else None,
            "n_seeds": seeds,
            "max_risk_per_seed": all_max,
            "mean_risk_per_seed": all_mean,
        }

    out = {
        "scenarios": by_scenario,
        "note": ("Training environment (clean grid, no faults) has "
                 "max_risk typically ≤ 0.05; H pre-ages an asset to "
                 "force high risk."),
    }
    (RESULTS / "twin_alignment.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8",
    )


# ---------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------

def _plot_q_values() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    data = json.loads(
        (RESULTS / "q_values.json").read_text(encoding="utf-8"),
    )
    states = data["states"]
    labels = [s["name"] for s in states]
    qs = np.array([s["Q"] for s in states])
    fig, ax = plt.subplots(figsize=(8.0, 4.5), dpi=110)
    width = 0.15
    x = np.arange(len(states))
    for i, aname in enumerate(ACTION_NAMES):
        ax.bar(x + (i - 2) * width, qs[:, i], width, label=aname)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Q-value (untrained scale)")
    ax.set_title("Q0..Q4 across representative states (trained DQN)")
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(RESULTS / "figures" / "q_value_distribution.png")
    plt.close(fig)


def _plot_reward_distribution() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    data = json.loads(
        (RESULTS / "action_reward_statistics.json").read_text(encoding="utf-8"),
    )
    per = [p for p in data["per_action"] if p["n"] > 0]
    labels = [p["name"] for p in per]
    means = [p["mean_reward"] for p in per]
    medians = [p["median_reward"] for p in per]
    stds = [p["std_reward"] for p in per]
    fig, ax = plt.subplots(figsize=(7.0, 4.0), dpi=110)
    x = np.arange(len(per))
    ax.errorbar(x, means, yerr=stds, fmt="o", color="black",
                label="mean ± std", capsize=4)
    ax.scatter(x, medians, marker="_", s=200, color="red", label="median")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("per-step reward (training distribution)")
    ax.set_title("Reward statistics by action (training distribution)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS / "figures" / "action_reward_distribution.png")
    plt.close(fig)


def _plot_action_collapse() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    data = json.loads(
        (RESULTS / "action_reward_statistics.json").read_text(encoding="utf-8"),
    )
    counts = data["action_counts"]
    labels = [ACTION_NAMES[int(k)] for k in sorted(counts.keys())]
    values = [counts[k] for k in sorted(counts.keys())]
    fig, ax = plt.subplots(figsize=(6.5, 3.8), dpi=110)
    ax.bar(labels, values)
    ax.set_ylabel("training-step count")
    ax.set_title("Action distribution during training (untrained policy)")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(RESULTS / "figures" / "action_distribution_over_training.png")
    plt.close(fig)


def _plot_mask_audit() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    data = json.loads(
        (RESULTS / "action_validity_distribution.json").read_text(
            encoding="utf-8",
        ),
    )
    # Per-scenario: percent of steps where action i is valid.
    rows = []
    for r in data["results"]:
        per_action = Counter()
        n_steps = 0
        for valid_set, c in r["valid_action_sets"].items():
            for v in valid_set:
                per_action[v] += c
            n_steps += c
        rows.append({
            "scenario": r["scenario"],
            "seed": r["seed"],
            "fractions": {
                ACTION_NAMES[a]: (per_action.get(a, 0) / max(1, n_steps))
                for a in range(5)
            },
            "selected_counts": r["selected_actions"],
        })
    # Average over seeds per scenario.
    by_sc: Dict[str, List[Dict[str, float]]] = defaultdict(list)
    for row in rows:
        by_sc[row["scenario"]].append(row["fractions"])
    avg_frac = {
        s: {a: float(np.mean([r[a] for r in fs]))
            for a in ACTION_NAMES}
        for s, fs in by_sc.items()
    }
    scenarios = sorted(avg_frac.keys())
    actions = ACTION_NAMES
    fig, ax = plt.subplots(figsize=(8.0, 4.0), dpi=110)
    xs = np.arange(len(scenarios))
    width = 0.15
    for i, a in enumerate(actions):
        vals = [avg_frac[s][a] for s in scenarios]
        ax.bar(xs + (i - 2) * width, vals, width, label=a)
    ax.set_xticks(xs)
    ax.set_xticklabels(scenarios)
    ax.set_ylabel("fraction of steps where action is valid")
    ax.set_title("Physical-validity mask coverage per scenario")
    ax.legend(fontsize=8, ncols=2, loc="upper center")
    fig.tight_layout()
    fig.savefig(RESULTS / "figures" / "mask_validity_distribution.png")
    plt.close(fig)
    # Selected-action distribution.
    sel_counts_by_sc: Dict[str, Counter] = {}
    for r in rows:
        sel_counts_by_sc.setdefault(r["scenario"], Counter())
        for a, c in r["selected_counts"].items():
            sel_counts_by_sc[r["scenario"]][int(a)] += c
    fig, ax = plt.subplots(figsize=(8.0, 4.0), dpi=110)
    for i, a in enumerate(actions):
        vals = [sel_counts_by_sc[s].get(i, 0) for s in scenarios]
        ax.bar(xs + (i - 2) * width, vals, width, label=a)
    ax.set_xticks(xs)
    ax.set_xticklabels(scenarios)
    ax.set_ylabel("steps where action was chosen (trained DQN)")
    ax.set_title("Selected action per scenario (trained DQN, eval mode)")
    ax.legend(fontsize=8, ncols=2)
    fig.tight_layout()
    fig.savefig(RESULTS / "figures" / "mask_selected_action.png")
    plt.close(fig)
    # Also persist the averages for the markdown.
    (RESULTS / "mask_summary.json").write_text(
        json.dumps({"per_scenario_average_fraction_valid": avg_frac,
                    "per_scenario_selected_counts":
                        {s: dict(c) for s, c in sel_counts_by_sc.items()}},
                   indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    print("[A] Action-mask audit ...")
    action_mask_audit(seeds=5)
    print("[A] plotting ...")
    _plot_mask_audit()

    print("[B] Q-value audit ...")
    q_value_audit()
    _plot_q_values()

    print("[C] Reward audit ...")
    reward_audit()
    _plot_reward_distribution()
    _plot_action_collapse()

    print("[D] Training-data audit ...")
    training_data_audit()

    print("[E] Controlled state tests ...")
    controlled_state_tests()

    print("[F] LSTM alignment ...")
    lstm_alignment_audit()

    print("[G] Twin alignment ...")
    twin_alignment_audit()

    # Summary across all diagnoses (used by the markdown audit docs).
    manifest = {
        "produced": [
            "action_validity_distribution.json",
            "q_values.json",
            "action_reward_statistics.json",
            "controlled_states.json",
            "lstm_alignment.json",
            "twin_alignment.json",
            "training_data.json",
            "mask_summary.json",
            "figures/q_value_distribution.png",
            "figures/action_reward_distribution.png",
            "figures/action_distribution_over_training.png",
            "figures/mask_validity_distribution.png",
            "figures/mask_selected_action.png",
        ],
    }
    (RESULTS / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8",
    )
    print(f"[Stage 43.1] Diagnostic artifacts saved to {RESULTS}")


if __name__ == "__main__":
    main()
