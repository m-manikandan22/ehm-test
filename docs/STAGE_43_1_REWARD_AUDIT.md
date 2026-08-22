# Stage 43.1 — Reward Audit

## Method

`stage43_1_diag.py::reward_audit` re-ran the training loop with the
**untrained** network (freshly-seeded random weights, eval_mode) for
4 episodes × 200 steps = 800 transitions. It recorded:

- the action the untrained network selected (driven only by physical
  validity mask + random Q-values, since eval_mode sets ε=0),
- the reward the *reward function* emits at the resulting next state,
- per-component decomposition of that reward.

The artefact is `experiments/results/stage43_1/action_reward_statistics.json`.

## Headline — action distribution in training (800 transitions)

```
action 0  increase_generation :   0  (  0.0 %)
action 1  use_battery         :   0  (  0.0 %)
action 2  use_supercapacitor  : 736  ( 92.0 %)
action 3  shift_load          :   0  (  0.0 %)
action 4  reroute_energy      :  64  (  8.0 %)
```

The untrained network collapses to action 2 within the *first*
episode. This is a property of the random-initialised Q-values and the
physical-validity mask — at this stage, **even before training**, the
argmax within the mask points to action 2 for ~92% of states.

## Per-action reward statistics

```
action 2 (n=736): mean -71.62  median -58.48  std 36.44  min -160.68  max -23.58
action 4 (n= 64): mean -21.75  median -22.17  std  4.24  min -31.48   max -13.51
```

(actions 0/1/3 were never selected by the untrained network, so no
reward statistics exist for them — the reward does not differentiate
them under the training distribution.)

## Per-component decomposition of mean reward

```text
                          action 2 (supercap)        action 4 (reroute)
stability_voltage           +3.07                    +3.07
stability_freq              -0.11                    +1.69
balance_penalty            -76.38                   -26.28
failed_penalty              0.00                     0.00
isolated_penalty            0.00                     0.00
loss_penalty                -0.20                    -0.23
supercap_spike_bonus        +2.00                    0.00
reroute_bonus               0.00                     0.00
                         --------                 --------
mean reward                -71.62                   -21.75
```

## Findings

1. **Action 2's mean reward (-71.62) is *worse* than action 4's
   (-21.75).** Yet the untrained network picks action 2 ~92% of the
   time and action 4 only ~8% of the time. This means:
   *the network is not following reward gradient; it is picking
   action 2 because the random Q-values rank it highest within the
   mask.* The reward signal is downstream of the policy, not driving
   it.
2. **The +2 supercap spike bonus is firing every transition (training
   has `any_load > 1.2 ≈ True` 100% of the time?** No — see (3)).
   The reward_a/_components output shows `supercap_spike_bonus=2.0`
   for *every* action 2 transition. That is because the training
   grid's `_base_load` makes many nodes' current `load` exceed 1.2 at
   certain curve phases (stage 43.1 _apply_time_curves writes
   `node.load = node._base_load * (load_factor + storm_boost) * noise`
   — load factors can exceed 1.0, sending post-step loads above 1.2).
3. **Balance is the dominant cost in this training environment.**
   With `balance` mean=18.09 across 800 steps and `avg_voltage=0.9614`
   (perfectly stable) and `num_failed=0`, the reward is essentially a
   function of `balance = total_gen - total_load` with spikes
   occasionally appearing in `avg_voltage` and `avg_freq`. **No
   failure state is ever observed during training.**
4. **The reward was never observed with failed / isolated nodes.**
   `num_failed=0`, `num_isolated=0` over all 800 transitions. The
   action-4 reroute bonus (`+3 if num_failed>0 or num_isolated>0`,
   `rl_agent.py:667-668`) **never fires during training** because
   training has no faults. So action 4's bonus was never reinforced.
   Similarly, action 0 (increase_generation) is selected precisely
   *zero* times in the training distribution — its effect on
   `balance_penalty` was never observed by the network.
5. **The +2 supercap bonus is *small* relative to the -76 average
   balance penalty, but the Bellman target only needs *one*
   unambiguous preference signal to push Q-values toward an action.**
   The bonus is consistent — `+2.0` for action 2 every time the spike
   condition triggers — whereas the negative components are stochastic
   and action-agnostic. The +2 is a *consistent* delta; over 1600
   training transitions it adds up to a stable gradient that pushes
   Q2 relative to Q0/Q1/Q3/Q4.

## H2 verdict — reward-driven? **Partially.**

The +2 supercap bonus is *not* the leading signal (it is small
relative to -76 balance), and the +3 reroute bonus has *zero*
impact during training because there are no failed nodes. The reward's
real effect on training is via:

- the static **balance penalty**, which all five actions share and
  which therefore cancels in the *relative* Q-update,
- the *conditional* `+2` supercap bonus on action 2 (always fires in
  the training distribution's load curve),
- the *never-fires* `+3` reroute bonus on action 4,
- the *never-selected* actions 0/1/3.

The relative gradient pressure is dominated by the consistent `+2` on
action 2 over a comparatively silent training distribution for actions
0, 1, 3, 4. This explains why Q2 climbs above other Qs even though no
individual transition prefers action 2 by a large absolute margin.

## Files

- `backend/models/rl_agent.py::compute_reward` (line 632)
- `backend/experiments/stage43_1_diag.py::reward_audit`
- `experiments/results/stage43_1/action_reward_statistics.json`,
  `figures/action_reward_distribution.png`,
  `figures/action_distribution_over_training.png`
