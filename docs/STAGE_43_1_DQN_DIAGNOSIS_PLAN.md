# Stage 43.1 — DQN Diagnosis Plan

## Problem statement

The Stage-43 10-seed validation (`experiments/results/stage43_validation/summary.md`)
shows the trained DQN **collapsed to action 2 (`use_supercapacitor`)**
in 8000 / 8000 evaluation steps, and the policy is identical across
all (scenario, seed) tuples.

This stage does **not** attempt to make the DQN score better. It
asks: *why* does the policy collapse, and is the explanation
defensible?

## Hypotheses (test plan)

| # | Hypothesis | Test |
|---|------------|------|
| H1 | **Mask-induced.** The action mask eliminates actions 0, 1, 3, 4 in most evaluation states, leaving only action 2 as physically possible. | Action-mask audit (§3). Compute fraction of timesteps each action is valid. |
| H2 | **Reward-induced.** `compute_reward` over-rewards action 2 (`use_supercapacitor`) via the conditional `+2.0` "spike" bonus; training amplifies this on a noisy spike-positive action distribution. | Reward decomposition (§5, §6). Compute mean reward per action during training and per-component breakdown. |
| H3 | **Training-data-limited.** ~1600 transitions and ~78-dim state are too few for a 5-action controller to learn a non-degenerate policy. | Training-data audit (§8). Track when collapse begins; measure state coverage. |
| H4 | **Training-scenario-mismatch.** Training scenario is a clean (no-fault) grid; evaluation scenarios A/E/G/H/J contain faults and stress. | State-diversity audit (§10). Compare training vs evaluation feature distributions. |
| H5 | **State-representation-limited.** The 78-dim extended vector does not distinguish situations that would require different actions. | Controlled-state tests (§7). Probe a deterministic state family; observe Q-values. |
| H6 | **Optimization-unstable.** Bellman targets / replay buffer / target-net sync produce divergence or bias. | Training-data audit (§8) — plot loss, ε, target updates. |
| H7 | **Action-effect-limited.** Action effects are too weak / short-lived (especially `shift_load` after `_apply_time_curves`) to generate useful learning signals. | Controlled-state tests + reward audit. Quantify per-action immediate reward consequence. |
| H8 | **Implementation bug.** The reward, mask, or state vector is wrong in a way that hasn't yet been caught. | Code review + cross-check reward on every step of training run. |

## Test matrix

```
A. Action-mask audit  ─→ H1  ─→ docs/STAGE_43_1_ACTION_MASK_AUDIT.md
B. Q-value audit      ─→ H5, H6, H8 ─→ docs/STAGE_43_1_Q_VALUE_AUDIT.md
C. Reward audit       ─→ H2, H7  ─→ docs/STAGE_43_1_REWARD_AUDIT.md
D. Training audit     ─→ H3, H6, H9 ─→ docs/STAGE_43_1_TRAINING_DATA_AUDIT.md
E. Controlled states  ─→ H5, H7, H8 ─→ docs/STAGE_43_1_CONTROLLED_STATE_ANALYSIS.md
F. LSTM alignment     ─→ H4      ─→ docs/STAGE_43_1_LSTM_TRAINING_ALIGNMENT.md
G. Twin alignment     ─→ H4      ─→ docs/STAGE_43_1_TWIN_TRAINING_ALIGNMENT.md
```

## Constraints

- No 100-seed run.
- No algorithm changes prior to diagnosis.
- No reward change until root cause is established.
- All experimentation in 10 seeds or fewer.

## Deliverables

- `docs/STAGE_43_1_DQN_DIAGNOSIS_PLAN.md` (this file).
- `docs/STAGE_43_1_ACTION_MASK_AUDIT.md` + `experiments/results/stage43_1/action_validity_distribution.json`.
- `docs/STAGE_43_1_Q_VALUE_AUDIT.md` + `q_values.json` + `q_value_distribution.png`.
- `docs/STAGE_43_1_REWARD_AUDIT.md` + `action_reward_statistics.json` + `action_reward_distribution.png`.
- `docs/STAGE_43_1_CONTROLLED_STATE_ANALYSIS.md` + `controlled_states.json`.
- `docs/STAGE_43_1_LSTM_TRAINING_ALIGNMENT.md`.
- `docs/STAGE_43_1_TWIN_TRAINING_ALIGNMENT.md`.
- `docs/STAGE_43_1_REPAIR_RECOMMENDATION.md`.
- `docs/STAGE_43_1_COMPLETION_REPORT.md`.

## Process

For each hypothesis:

1. Make measurement (artifact under `experiments/results/stage43_1/`).
2. Write the audit doc with **evidence**, not interpretation.
3. Update root-cause table as data arrives.
4. Only after data is complete, propose a repair.
