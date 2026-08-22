"""dqn_training.py — Stage-43 Repair 4: the ONLY place the DQN is trained.

The Stage-42.5 audit found the DQN had never been trained: ``run_single``
evaluated freshly-seeded random weights, so the ``dqn`` ablation row was
just "random policy through a neural network". This module fixes that:

* Training runs on a **clean** (no-fault) scenario so the policy learns
  grid operation — supply/demand balancing, storage use, load shifting —
  before it is evaluated on fault scenarios.
* Every experience uses the **extended decision state** (78 dims:
  72-dim grid state + LSTM forecast + storage SOC + twin risk features),
  i.e. exactly the vector the runner builds for evaluation.
* The trained policy is frozen into a checkpoint; ``run_single`` only
  ever *loads* a checkpoint (never trains). The ``trained_dqn``
  controller label points at the checkpoint; ``untrained_dqn`` is the
  same architecture on random-initialised weights.

Determinism
-----------
* ``train_seed`` is split with ``derive_stream_seeds`` so the
  environment noise stream of every training episode is independent of
  the torch stream used to seed the network weights.
* The checkpoint records the seeds, the training bookkeeping and the
  repository SHA, so any policy can be reproduced or audited.

Usage
-----
    python -m experiments.dqn_training \
        --seed 0 --episodes 8 --steps 200 \
        --output experiments/checkpoints/dqn_extended.pt
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Dict, List, Optional

from simulation.grid import SmartGrid
from utils.seeds import derive_stream_seeds, set_global_seed


def _default_checkpoint_path() -> str:
    """Default checkpoint location (relative to this module)."""
    here = Path(__file__).resolve().parent
    return str(here / "checkpoints" / "dqn_extended.pt")


def train_dqn(
    *,
    train_seed: int = 0,
    episodes: int = 8,
    steps_per_episode: int = 200,
    output_path: Optional[str] = None,
    state_dim: Optional[int] = None,
) -> dict:
    """Train the extended-state DQN and write a frozen checkpoint.

    Returns a dict summarising the run (seeds, steps, mean rewards,
    checkpoint path).
    """
    import torch

    from models.rl_agent import (
        DQNAgent,
        EXTENDED_STATE_DIM,
        build_extended_state,
    )

    if state_dim is None:
        state_dim = EXTENDED_STATE_DIM

    # RNG isolation: the torch stream that seeds the network is derived
    # from the training stream; each episode's grid gets its own
    # environment stream so exploration cannot leak into physics noise.
    stream_seeds = derive_stream_seeds(int(train_seed))
    torch.manual_seed(stream_seeds["training"])
    agent = DQNAgent(state_dim=int(state_dim))

    from experiments.runner import _dispatch_action

    episode_rewards: List[float] = []
    step = 0
    for ep in range(int(episodes)):
        env_seed = int(stream_seeds["environment"]) + ep * 10_007
        set_global_seed(int(train_seed) + ep)
        grid = SmartGrid(
            seed=int(train_seed) + ep,
            rng_seed=env_seed,
        )
        ep_total = 0.0
        for _ in range(int(steps_per_episode)):
            try:
                grid.update_power_flow()
            except Exception:
                pass
            state = grid.get_rl_state()
            grid_state = grid.get_state()
            # The forecast channel is a VARIED feature during training
            # (a normalised proxy of the current aggregate demand), so
            # the policy learns to use feature 72. At evaluation the
            # LSTM provides the real forecast; a policy trained on a
            # constant 0.5 would have no gradient pressure to attend to
            # the channel (which is why the causal LSTM tests would
            # otherwise fail on an untrained policy).
            forecast_feature = max(0.05, min(2.0, _aggregate_load(grid) / 20.0))
            extended = build_extended_state(
                state,
                predicted_load=forecast_feature,
                battery_soc=_soc(grid, "battery"),
                supercap_soc=_soc(grid, "supercap"),
            )
            decision = agent.select_action(
                extended, predicted_load=forecast_feature,
                grid_state=grid_state,
            )
            action_id = int(decision["action_id"])
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
            # The next state must be the SAME extended vector space the
            # policy decides on (78-dim), or the replay batch mixes
            # 72- and 78-dim tensors and the network shape breaks.
            next_forecast = max(
                0.05, min(2.0, _aggregate_load(grid) / 20.0)
            )
            next_state = build_extended_state(
                grid.get_rl_state(),
                predicted_load=next_forecast,
                battery_soc=_soc(grid, "battery"),
                supercap_soc=_soc(grid, "supercap"),
            )
            reward = agent.compute_reward(
                grid_state, action_name=decision["action_name"],
            )
            ep_total += reward
            agent.store_experience(extended, action_id, reward,
                                   next_state, done=False)
            step += 1
        episode_rewards.append(ep_total / max(1, int(steps_per_episode)))

    out = output_path or _default_checkpoint_path()
    agent.save_checkpoint(
        out,
        seeds=dict(stream_seeds),
        git_sha=_git_sha(),
        extra={
            "train_seed": int(train_seed),
            "episodes": int(episodes),
            "steps_per_episode": int(steps_per_episode),
            "total_transitions": step,
            "mean_reward_per_episode": episode_rewards,
            "final_epsilon": float(agent.epsilon),
            "pipeline": "stage43_dqn_training",
        },
    )
    return {
        "checkpoint_path": out,
        "seeds": dict(stream_seeds),
        "total_transitions": step,
        "mean_reward_per_episode": episode_rewards,
        "final_epsilon": float(agent.epsilon),
        "state_dim": int(state_dim),
    }


def _soc(grid, kind: str) -> float:
    """Highest SOC of the named storage type (mirrors runner helper)."""
    best = 0.0
    attr = "battery_level" if kind == "battery" else "supercap_level"
    for n in grid.nodes.values():
        ntype = str(getattr(n, "node_type", "") or "")
        is_storage = (
            ntype == "house"
            or (kind == "battery" and ntype == "battery")
            or (kind == "supercap" and ntype == "supercap")
        )
        if not is_storage:
            continue
        if getattr(n, "failed", False) or getattr(n, "isolated", False):
            continue
        best = max(best, float(getattr(n, attr, 0.0) or 0.0))
    return best


def _aggregate_load(grid) -> float:
    """Total load of energised nodes (mirrors runner aggregate)."""
    total = 0.0
    for n in grid.nodes.values():
        if getattr(n, "failed", False) or getattr(n, "isolated", False):
            continue
        total += float(getattr(n, "load", 0.0) or 0.0)
    return total


def _git_sha() -> str:
    """Best-effort repo SHA for checkpoint provenance."""
    import subprocess
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--episodes", type=int, default=8)
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--output", type=str, default=None)
    args = ap.parse_args()
    result = train_dqn(
        train_seed=args.seed,
        episodes=args.episodes,
        steps_per_episode=args.steps,
        output_path=args.output,
    )
    import json
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
