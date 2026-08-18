# Stage 42.5 — RL vs Heuristic: Where the Decisions Actually Come From (`STAGE_42_5_RL_VS_HEURISTIC.md`)

**Date:** 2026-08-18
**Status:** Empirical audit complete.

## Question

Does the "AI stack" (LSTM + DQN + digital twin) actually drive the decisions
that the Stage-42 experiment attributed to it? The Stage-42 completion report
claimed the LSTM "changes action selection". This audit checks what is really
reaching the decision.

## Findings

### 1. The LSTM forecast never reaches action selection

`predicted_load` is passed to `select_action(state, predicted_load, grid_state)`
and consumed **only** inside `_build_reasoning` (a human-readable string).
The action is chosen by `masked_q.argmax()` over Q-values; the mask reads
`balance`, `spike`, `failed`, `isolated` — never `predicted_load`.

**Empirical proof** (`_stage425_diag.py` section B): for identical state,
`predicted_load` ∈ {0.05, 0.5, 0.95, 0.12345} produces the **same action
(3)** in every case; only the reasoning string changes ("Low demand
predicted…" vs "High demand predicted…").

### 2. The `full_stack` vs `no_lstm` action difference is a torch-RNG artifact

Stage 42 measured different action distributions for `full_stack` vs
`no_lstm` and reported it as "LSTM changes action selection". The real
mechanism:

- `run_single` constructs `DemandForecaster()` (runner.py:346) **before**
  `DQNAgent()` (runner.py:366-369).
- LSTM training consumes the shared torch RNG; therefore the DQN's random
  weight initialisation differs depending on whether the LSTM was built.
- **Empirical proof** (`_stage425_diag.py` section C): with the same seed,
  DQN weights built after LSTM construction vs built alone are **not
  identical** (max |Δw| = 0.2474); Q-values differ completely and
  `argmax` flips.
- Controlled experiment (10 seeds, Scenario A): `full_stack` action mix is
  `{use_scap 0.36, reroute 0.37, shift_load 0.27}` while the *same* DQN mask
  config **without** LSTM construction (`dqn_mask`) is `{shift_load 0.77,
  use_scap 0.12, reroute 0.11}` — the weight-init artifact dominates the
  reported difference (ENS 1.3527 vs 1.0623).

**Conclusion:** the LSTM's forecast has zero causal effect on decisions. The
LSTM flag changes decisions only through the random weight initialisation of
an unrelated network.

### 3. The DQN evaluated in the experiment is untrained

`run_single` constructs `DQNAgent()`, calls `eval_mode()`, and never calls
`smart_warmup`, `store_experience`, or `_train_step` (training calls exist
only in `scada.py:62` and `check_tensor.py:9`).

**Empirical proof** (`_stage425_diag.py` section F): freshly constructed
agent has replay buffer size **0**, `steps_done` **0**, and is in eval mode.
The paper DQN is a random-weight MLP behind a hand-coded rule mask.

### 4. The mask, not the network, decides

In `select_action` (rl_agent.py:301-361) the valid-action set is derived
entirely from hand-coded rules:
- `balance < −0.1` → actions {0, 1}
- any node `load > 1.2` (spike) → +2
- any failed/isolated → +4
- action 3 always allowed

Q-values (random weights) only rank within this hand-coded set.

**Mask effect, measured** (10 seeds, Scenario A):
- `dqn_unmasked` (same network, mask disabled via `grid_state=None`):
  ENS 1.1461, actions {shift_load 0.52, use_batt 0.30, inc_gen 0.16}
- `dqn_mask` (mask on): ENS 1.0623, actions {shift_load 0.77}

The mask does change behaviour, but both variants are untrained random
networks — the "RL" contribution is a heuristic mask plus random weights.

### 5. Training works when actually invoked (control)

To confirm the network can learn at all, a `smart_warmup`-trained DQN was
compared to the untrained one (5 seeds, Scenario A):
- untrained: ENS 1.3704, shift_load share 0.785
- trained (150-step rule-bootstrap + 40 gradient steps): ENS 1.0651,
  shift_load share 0.905; buffer filled to 150.

Training does change the policy — but the harness never invokes it, so the
reported DQN results are for an untrained network.

### 6. The digital twin is dead wiring for the DQN

The runner injects `grid_state["system"]["health_aware_load_shift"] = True`
when the twin risk map is high (runner.py:183-185) — but `select_action`'s
mask never reads that key (rl_agent.py:322-332).

**Empirical proof** (`_stage425_diag.py` section E): action with the key
present vs absent is identical (3 in both cases).

The twin *does* affect the rule-based controller (health-aware bias forces
action 3) — see the twin controlled test in the completion report — but for
the DQN path the twin signal is never consumed.

### 7. Reward shaping flag is dead

`enable_reward_shaping` is read nowhere in `runner.py`; `no_reward` runs are
identical to `full_stack` by construction (the reward function is never
called in the harness — there is no learning loop to reward).

## Bottom line

| Module | Reported role | Actual role in harness |
|---|---|---|
| LSTM forecast | changes action selection | reasoning-string decoration only |
| DQN | learned controller | untrained random MLP + hand-coded mask |
| Twin health bias | DQN health-aware override | never read by DQN mask; affects rule_based only |
| Reward shaping | ablation row | flag never read |

The architecture contains no verified learned or predictive signal reaching
the decision in the evaluated configuration.
