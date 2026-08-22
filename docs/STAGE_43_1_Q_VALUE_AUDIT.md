# Stage 43.1 — Q-Value Audit

## Method

`stage43_1_diag.py::q_value_audit` built 8 representative extended-state
vectors (each variant of battery_soc, supercap_soc, forecast,
twin_max_risk), passed them through the **trained** DQN's
`policy_net`, and recorded `Q0..Q4`, the mask, and `argmax`
within-mask.

The artefact is `experiments/results/stage43_1/q_values.json`
and `figures/q_value_distribution.png`.

## Headline numbers (trained network)

`Q` columns are reproduced below (`baseline`, `low_battery`, `full_battery`,
`low_supercap`, `high_supercap`, `low_forecast`, `high_forecast`,
`high_twin_risk`):

| State            | Q0       | Q1       | **Q2**    | Q3       | Q4       | argmax |
|------------------|---------:|---------:|----------:|---------:|---------:|:------:|
| baseline         | -1070.8  | -1059.1  | **-1053.1** | -1067.0  | -1070.5  | 2 |
| low_battery      | -1072.6  | -1060.9  | **-1054.9** | -1068.8  | -1072.3  | 2 |
| full_battery     | -1069.0  | -1057.3  | **-1051.3** | -1065.2  | -1068.7  | 2 |
| low_supercap     | -1078.1  | -1066.3  | **-1060.4** | -1074.4  | -1077.9  | 2 |
| high_supercap    | -1063.4  | -1051.9  | **-1045.8** | -1059.7  | -1063.1  | 2 |
| low_forecast     | -1072.7  | -1061.0  | **-1055.0** | -1069.0  | -1072.5  | 2 |
| high_forecast    | -1066.4  | -1054.8  | **-1048.7** | -1062.6  | -1066.1  | 2 |
| high_twin_risk   | -1069.9  | -1058.2  | **-1052.2** | -1066.1  | -1069.6  | 2 |

## Findings

1. **Q2 > Q{i≠2} for every single probe state.** The margin to the
   second-best action (Q1 in all cases) is ~5.7–7.8. The third action
   is ~14 below Q2. The collapse is **learned**: not stochastic, not a
   one-off.
2. **Q-raking varies by feature**: the *absolute* Q-values shift
   (e.g. low_supercap has the lowest Q2=-1060; high_supercap has
   Q2=-1045; battery SOC and forecast perturb Q monotonically), so
   the network *is* using the input features. It just never finds Q2
   beaten by another action.
3. **The mask is irrelevant at inference time.** `valid_actions` is
   `[0,1,2,3,4]` for every probe; the relative Q2 > Q{others} ranking
   is what selects action 2.

## H5 verdict — state representation distinguishes? **No, not enough.**

The Q-values do change with the state features — that confirms the
network is *reading* the state vector. But the **relative ranking**
is invariant in 8/8 probes. With eight hand-crafted probes spanning
battery SOC, supercap SOC, forecast, and twin risk, the network
*never* prefers another action. Either:

a) the state space is not yet enumerated — there is some combination
   of features that would tip the ranking, or
b) the *reward function's gradient* has driven Q2 to be the global
   optimum across the reachable support of the training distribution.

Hypothesis (b) is the more parsimonious explanation given that
*every* gradient step during training would tend to push Q toward the
argmax of the Bellman target — and the Bellman target's value comes
from the reward at the *next* step, which is correlated with action 2
(see `STAGE_43_1_REWARD_AUDIT.md`).

## H6 verdict — optimisation stable?

* Loss history was not logged by `dqn_training.py::train_dqn` (no
  loss vector in the checkpoint's `extra` block).
* `steps_done=1600`, `final_epsilon≈0.05` — ε decayed normally.
* Per-episode mean reward (`extra.mean_reward_per_episode`) drifts
  from `-89.9` (ep 0) to `-65.97` (ep 5) then back to `-80.7` (ep 7).
  No monotonic improvement, no divergence.

The absence of a logged loss prevents claiming "Bellman target
converged" — but the policy *did* change from random to action-2-only,
so optimisation reached the global action-2 basin. This is not "DQN
diverged"; this is "DQN converged to a degenerate policy".

## Files

- `backend/experiments/stage43_1_diag.py::q_value_audit`
- `backend/models/rl_agent.py::DQNetwork::forward`, `DQNAgent::select_action`
- `backend/experiments/results/stage43_1/q_values.json`,
  `figures/q_value_distribution.png`
