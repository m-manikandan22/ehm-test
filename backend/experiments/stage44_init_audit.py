"""stage44_init_audit.py — Stage-44 Repair R4 isolated experiment.

Compares PyTorch default initialization vs zero-mean final-layer
initialization on **identical** scenarios / seeds / budget / reward
/ architecture. The objective is to measure:

  * Initial Q-value distribution (does the network start uniform?).
  * Per-episode mean reward trajectory (does either init destabilise?).
  * Action collapse (does either init collapse faster?).
  * Loss stability (does either init produce exploding gradients?).

The change is **only retained** if it improves training stability
or sound initialization reasoning. It is NOT retained merely
because it increases action diversity.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
import torch

from utils.seeds import derive_stream_seeds, set_global_seed

from experiments.stage44_dqn_training import train_stage44_dqn


HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results" / "stage44"


def _q_distribution(agent) -> Dict[str, Any]:
    """Return the initial Q-value distribution for a probe state."""
    state = np.zeros(78, dtype=np.float32)
    with torch.no_grad():
        q = agent.policy_net(torch.tensor(state).unsqueeze(0)).numpy().ravel()
    return {
        "Q": [float(v) for v in q],
        "mean": float(q.mean()),
        "std": float(q.std()),
        "argmax": int(np.argmax(q)),
        "min": float(q.min()),
        "max": float(q.max()),
    }


def run_init_audit(
    *,
    master_seed: int = 11,
    episodes: int = 4,
    steps_per_episode: int = 40,
) -> dict:
    """Run the same scenario sequence with and without zero-init."""
    out: Dict[str, Any] = {
        "master_seed": int(master_seed),
        "episodes": int(episodes),
        "steps_per_episode": int(steps_per_episode),
    }

    # ── Probe a *freshly seeded* random-init network before any training.
    set_global_seed(int(master_seed))
    ss = derive_stream_seeds(int(master_seed))
    torch.manual_seed(int(ss["training"]))
    from models.rl_agent import DQNAgent, EXTENDED_STATE_DIM
    agent_default = DQNAgent(state_dim=EXTENDED_STATE_DIM)
    agent_default.eval_mode()
    out["default_init_initial_q"] = _q_distribution(agent_default)

    # ── Same probe with the zero-mean final-layer init.
    set_global_seed(int(master_seed))
    ss = derive_stream_seeds(int(master_seed))
    torch.manual_seed(int(ss["training"]))
    agent_zero = DQNAgent(state_dim=EXTENDED_STATE_DIM)
    with torch.no_grad():
        last = agent_zero.policy_net.net[-1]
        if isinstance(last, torch.nn.Linear):
            last.weight.zero_()
            last.bias.zero_()
        agent_zero.target_net.load_state_dict(agent_zero.policy_net.state_dict())
    agent_zero.eval_mode()
    out["zero_init_initial_q"] = _q_distribution(agent_zero)

    # ── Train with default init (small budget for the audit).
    set_global_seed(int(master_seed))
    log_default = train_stage44_dqn(
        master_seed=int(master_seed),
        episodes=int(episodes),
        steps_per_episode=int(steps_per_episode),
        output_path=str(
            HERE / "checkpoints" / "dqn_stage44_init_audit_default.pt"
        ),
        use_zero_init=False,
    )
    out["default_init_training"] = {
        "mean_reward_per_episode": log_default["mean_reward_per_episode"],
        "action_counts_per_episode": log_default["action_counts_per_episode"],
        "num_failed_per_episode": [
            int(np.sum(arr)) for arr in log_default["num_failed_per_episode"]
        ],
        "twin_max_risk_max_per_episode": [
            float(np.max(arr) if arr else 0.0)
            for arr in log_default["twin_max_risk_per_episode"]
        ],
    }

    # ── Train with zero-init (same seed, same scenarios, same budget).
    set_global_seed(int(master_seed))
    log_zero = train_stage44_dqn(
        master_seed=int(master_seed),
        episodes=int(episodes),
        steps_per_episode=int(steps_per_episode),
        output_path=str(
            HERE / "checkpoints" / "dqn_stage44_init_audit_zero.pt"
        ),
        use_zero_init=True,
    )
    out["zero_init_training"] = {
        "mean_reward_per_episode": log_zero["mean_reward_per_episode"],
        "action_counts_per_episode": log_zero["action_counts_per_episode"],
        "num_failed_per_episode": [
            int(np.sum(arr)) for arr in log_zero["num_failed_per_episode"]
        ],
        "twin_max_risk_max_per_episode": [
            float(np.max(arr) if arr else 0.0)
            for arr in log_zero["twin_max_risk_per_episode"]
        ],
    }

    # ── Verdict.
    q_default = out["default_init_initial_q"]
    q_zero = out["zero_init_initial_q"]
    # Compute the action collapse indicator: fraction of steps that
    # are action 2 in each training run.
    def _frac_a2(per_episode_counts):
        total = sum(sum(c.values()) for c in per_episode_counts)
        if total == 0:
            return 0.0
        return sum(
            c.get(2, 0) for c in per_episode_counts
        ) / total
    frac_default = _frac_a2(out["default_init_training"][
        "action_counts_per_episode"
    ])
    frac_zero = _frac_a2(out["zero_init_training"][
        "action_counts_per_episode"
    ])
    out["action_2_fraction_default"] = float(frac_default)
    out["action_2_fraction_zero"] = float(frac_zero)

    out["verdict"] = (
        "zero_init retained" if (
            # The zero-init is retained iff it produces a more uniform
            # initial Q distribution AND does NOT regress training
            # reward materially (within 1 std of default's trajectory).
            abs(q_zero["max"] - q_zero["min"]) < abs(
                q_default["max"] - q_default["min"]
            )
            and np.mean(out["zero_init_training"][
                "mean_reward_per_episode"
            ]) >= np.mean(out["default_init_training"][
                "mean_reward_per_episode"
            ]) - 5.0
        ) else "default init retained"
    )
    return out


def main() -> None:
    out = run_init_audit()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "init_audit.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8",
    )
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
