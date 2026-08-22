# Stage 43.1 — Repair Recommendation

## Root-cause classification

Following the Stage-43.1 audit matrix (`A..I`), the collapse is
**MIXED (I)**, dominated by three causes:

- **B. Reward-induced** (small consistent `+2` on action 2 against
  a never-firing `+3` on action 4). Evidence: `STAGE_43_1_REWARD_AUDIT.md`.
- **D. State-representation-limited** (78-dim state is read by the
  network, but the Q-rank doesn't flip under any feature variation).
  Evidence: `STAGE_43_1_Q_VALUE_AUDIT.md`,
  `STAGE_43_1_CONTROLLED_STATE_ANALYSIS.md`.
- **G. Environment-mismatch** (training has no failures / no
  high-risk twins / LSTM feature range ~0.94 vs evaluation ~0.38).
  Evidence: `STAGE_43_1_TRAINING_DATA_AUDIT.md`,
  `STAGE_43_1_LSTM_TRAINING_ALIGNMENT.md`,
  `STAGE_43_1_TWIN_TRAINING_ALIGNMENT.md`.

Hypotheses explicitly **rejected**:

- **H1 (mask-induced)**: mask returns `{0,1,2,3,4}` in every step.
  See `STAGE_43_1_ACTION_MASK_AUDIT.md`.
- **H8 (implementation bug)**: Q-values, mask, reward decomposition
  all sum correctly; no NaN, no swallowed exceptions.

The diagnosis plan (`STAGE_43_1_DQN_DIAGNOSIS_PLAN.md`) enumerated H1–H8;
this is the closure of that plan.

## Repair principles (Stage-44 only — not Stage-43)

The Stage-43 mandate is **first diagnose, then minimal repair**, with
no tuning to win. The proposed repairs below are therefore:

1. **Scientifically justified** — each repair maps directly to a
   measured evidence gap;
2. **Minimal** — they do not introduce new AI technologies, they
   modify existing ones;
3. **Bias-risk-annotated** — each repair lists its risk of biasing
   the result upward;
4. **Independently testable** — each repair has a verification that
   does *not* require rerunning the 10-seed validation to "win".

None of these repairs will be applied as part of Stage 43.1.
Stage 43.1 produces **diagnosis only**.

### Repair R1 — Use the real LSTM feature during training

* **Current problem**: at training time the network is fed
  `aggregate_load/20 ∈ [0.74, 1.08]`. At evaluation time the LSTM
  output lands in `[0.30, 0.49]`. The two distributions do not
  overlap.
* **Evidence**: `STAGE_43_1_LSTM_TRAINING_ALIGNMENT.md`.
* **Minimal fix**: replace `forecast_feature = aggregate_load / 20`
  with `forecast_feature = lstm.predict(history_window)` in
  `dqn_training.py::train_dqn`. Match the LSTM's training-time
  pretraining so the LSTM sees the same input scale at training and
  evaluation.
* **Why scientifically justified**: the network's input distribution
  must equal its evaluation distribution or the network underfits by
  design. This is a fairness fix, not a metric fix.
* **Expected effect**: action selection will be *more diverse* across
  the 78-dim state space. *Not* an expected improvement in score —
  it is an expected improvement in **state-space coverage**. The
  score may go *down* in the short term as the network relearns.
* **Risk of bias**: low. The repair removes a *systematic bias*
  against LSTM-driven scenarios; it does not introduce a new bias.
* **Required test**: re-run `lstm_alignment_audit`; require
  `training_feature.mean ≈ lstm_prediction.mean ± 0.05`.
* **Required validation**: re-run the 10-seed × 5-scenario
  validation. Report **action diversity** (fraction of non-action-2
  steps) before/after. Do not report score.

### Repair R2 — Inject controlled faults / pre-aged twins into training

* **Current problem**: training had `num_failed = num_isolated = 0`
  for all 800 audit transitions; twin `max_risk = 0.0` for Scenario A
  across all seeds. The +3 reroute bonus and the +2 supercap bonus
  never compete on a real fault during training.
* **Evidence**: `STAGE_43_1_TRAINING_DATA_AUDIT.md`,
  `STAGE_43_1_TWIN_TRAINING_ALIGNMENT.md`.
* **Minimal fix**: add a `train_fault_schedule` to `train_dqn` that
  injects (a) `health_override` events mirroring Scenario H, and (b)
  `fault_injection` events at random steps. Use the same RNG stream
  isolation pattern (`derive_stream_seeds`).
* **Why scientifically justified**: the DQN cannot learn a fault-handling
  policy it has never observed. This matches the Stage-43 mandate that
  evaluation scenarios must be **reachable** in training.
* **Expected effect**: action-4 frequency in training increases from
  ~8% to ~25–35% (target, not guarantee). Q4 will then receive
  gradient and may rise above Q2 in fault states.
* **Risk of bias**: medium. Adding faults during training is a
  *deliberate* change in training distribution. To minimise bias, use
  the same fault distribution as the evaluation scenarios (A/E/G/H/J).
* **Required test**: re-run `reward_audit` and confirm `n_action=4`
  > 100 in 800 transitions.
* **Required validation**: re-run the 10-seed × 5-scenario
  validation. Report action distribution per scenario.

### Repair R3 — Re-design the reward signal

* **Current problem**: the +2 supercap bonus fires for every action-2
  transition in the training distribution; the +3 reroute bonus
  fires zero times; the balance penalty dominates the magnitude.
  Net: actions 0/1/3 are never *reinforced* (never selected), action
  2 is consistently reinforced, action 4 is rarely selected and never
  reinforced.
* **Evidence**: `STAGE_43_1_REWARD_AUDIT.md`.
* **Minimal fix options** (any one, not all):
  - **R3a (preferred)**: make bonuses *small relative to balance
    penalty* AND *conditional on the action's measured effect*. E.g.
    `if action == "use_supercapacitor" and next_state.balance < prev_balance: reward += 2`.
  - **R3b**: zero out the action-conditional bonuses entirely and
    rely on the balance/voltage/frequency signals; verify that
    action diversity emerges naturally from environment dynamics.
  - **R3c**: introduce a *small* penalty for repeated same-action
    use across a sliding window of N steps. This breaks the
    "always-action-2" basin without introducing a heuristic.
* **Why scientifically justified**: a reward that cannot differentiate
  actions across the reachable state space is *information-free* —
  it cannot support learning a policy. R3a is the closest to current
  semantics with the smallest change; R3b is the most aggressive
  reset.
* **Expected effect**: action 0/1/3 will see non-zero reward
  variance, which gives the Q-network gradient signal.
* **Risk of bias**: high. Reward shaping is the most bias-prone
  change in a reinforcement learning study. The risk is mitigated
  by (a) declaring the change *before* running validation, and
  (b) reporting action diversity + per-component decomposition
  instead of summary score.
* **Required test**: re-run `reward_audit`; require
  `n_action=0 + n_action=1 + n_action=3 > 100` in 800 transitions.
* **Required validation**: 10-seed × 5-scenario; report per-action
  frequency. No summary score.

### Repair R4 — Re-initialise the policy with action-conditional priors

* **Current problem**: the *untrained* network already collapses to
  action 2 in 92% of transitions because random Q-values plus the
  mask happen to put action 2 on top. Training reinforces a starting
  bias.
* **Evidence**: `STAGE_43_1_REWARD_AUDIT.md` §"Headline".
* **Minimal fix**: zero-mean-initialise the policy net's last linear
  layer (or scale it by 0.1) so all five Q-heads start near zero
  rather than the natural PyTorch default that can favour one
  head by 5–10.
* **Why scientifically justified**: removes a non-physical bias
  from initial conditions. The Q-network should not be able to
  express "action 2 is best" before seeing any data.
* **Expected effect**: action distribution at random init moves
  closer to uniform. **Then** training can find the action with the
  best gradient signal.
* **Risk of bias**: low. This is a standard DQN practice.
* **Required test**: re-run `reward_audit` with the new init; require
  the action distribution to fall within `[15%, 25%]` per action
  (i.e. within ±10pp of uniform 20%).
* **Required validation**: 10-seed × 5-scenario.

### Repair ordering (Stage-44 candidate)

A *minimum* principled repair is **R1 + R2 + R4**. R3 is more
disruptive; it should be attempted *after* R1+R2+R4 are shown to be
insufficient.

The Stage-43.1 completion-report verdict (`STAGE_43_1_COMPLETION_REPORT.md`)
records the order and the gates.

## What is *not* in the repair list

* No 100-seed run.
* No tuning of reward weights to maximise score.
* No cherry-picked scenario selection.
* No new AI technology.
* No replacing of working modules (LSTM, twin, EMS, FLISR all stay).
* No final-paper claims until a Stage-44 controlled validation has
  completed.

## Files

- `backend/experiments/dqn_training.py` (R1, R2, R4 edit targets)
- `backend/models/rl_agent.py::compute_reward` (R3 edit target)
- `experiments/results/stage43_1/*` (all evidence)
