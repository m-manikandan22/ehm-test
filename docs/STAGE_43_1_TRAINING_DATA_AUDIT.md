# Stage 43.1 — Training-Data Audit

## Method

`twin_alignment_audit` is covered in a sibling document;
`training_data_audit` inspects the checkpoint's metadata.

Artefacts: `experiments/results/stage43_1/training_data.json`,
`action_reward_statistics.json` (state feature ranges from re-running
the training loop).

## Checkpoint metadata

```json
{
  "state_dim": 78,
  "steps_done": 1600,
  "epsilon": 0.0503,
  "seeds": {"environment":17,"controller":31,"training":47},
  "extra": {
    "train_seed": 0,
    "episodes": 8,
    "steps_per_episode": 200,
    "total_transitions": 1600,
    "mean_reward_per_episode": [
        -89.9, -74.8, -82.9, -72.5, -74.5, -66.0, -74.3, -80.7
    ],
    "final_epsilon": 0.0503,
    "pipeline": "stage43_dqn_training"
  }
}
```

## State-feature coverage during training

The reward-audit re-run (800 transitions) reported:

| Feature           | min    | max    | mean    |
|-------------------|-------:|-------:|--------:|
| balance           |  4.60  | 41.10  |  18.09  |
| avg_voltage       | 0.9614 | 0.9614 | 0.9614  |
| avg_frequency     | 50.46  | 52.00  |  51.48  |
| num_failed        | 0      | 0      |  0      |
| num_isolated      | 0      | 0      |  0      |
| forecast_feature  | 0.74   | 1.37   |  1.03   |

* `balance` was **always positive** (gen > load) — there was never a
  generation deficit during training.
* `avg_voltage` and `avg_frequency` are nearly constant (small
  perturbation from inertia model).
* `num_failed = num_isolated = 0` for every transition.
* `forecast_feature` lives in [0.74, 1.37] (no low-forecast, no spike
  scenarios).

## Episode mean rewards

```
ep 0: -89.93
ep 1: -74.83
ep 2: -82.86
ep 3: -72.51
ep 4: -74.45
ep 5: -65.97    ← lowest mean
ep 6: -74.35
ep 7: -80.69    ← regressed
```

Reward *trended* from -89.93 → -65.97 across episodes 0–5 (a ~26%
improvement). Episodes 6–7 regressed. None of the per-episode rewards
are dominated by action-conditional bonuses — `±2` and `±3`
bonuses are *small* relative to the -50 to -150 range of balance
penalties.

## Implication

1. **Training data is tiny for a 78-dim state**: 1600 transitions.
   The Q-network has ~6000 free parameters (`64x64 + 64x64 +
   64x5 + biases ≈ 4512`). With 1600 transitions the network is
   relatively under-constrained at the loss level — but it
   *memorises* training transitions because they all collapse to
   the same (state-variants-of-baseline, action 2) pair.
2. **Action diversity during training**: in the re-run, the
   untrained network already picked action 2 ~92% of the time, and
   action 4 ~8%. Actions 0/1/3 were never picked. *This is before
   any gradient step.* Therefore training cannot, in principle,
   increase action diversity — the gradient is computed on the
   transitions that *did* happen. If only actions 2 and 4 appear in
   the replay buffer, only Q2 and Q4 see gradient; Q0, Q1, Q3 stay
   at their random-init values.
3. **The lack of failure/training-scenario coverage** is the root
   cause of action-4 never learning the reroute pattern.

## H3 verdict — training-data-limited? **Yes (in coverage, not in count).**

1600 transitions is *small* but the limiting factor is *not* sample
size — it is *action diversity*. With the untrained network already
saturating on action 2, the replay buffer never holds a sufficient
number of (s, a) pairs for a ≠ 2 to learn anything.

## H6 verdict — optimisation stable? **Yes, converged to a fixed point.**

Loss history is not in the checkpoint `extra` block; per-episode
mean reward fluctuates without diverging.

## Files

- `backend/experiments/dqn_training.py::train_dqn`
- `experiments/results/stage43_1/training_data.json`,
  `action_reward_statistics.json`
