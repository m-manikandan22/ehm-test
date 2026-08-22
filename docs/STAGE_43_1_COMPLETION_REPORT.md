# Stage 43.1 — Completion Report

## Verdict

**PARTIAL — CONTINUE** (diagnostic gate closed; repair gate pending).

Stage 43.1 was a *diagnosis-only* stage by mandate ("do NOT make DQN
score better; first diagnose"). All evidence has been collected,
audited, classified, and a minimal-repair recommendation produced.
No repair has been applied. No score has been tuned. No 100-seed
run has been performed.

## What Stage 43.1 produced

### Documents

| Doc                                                | Section |
|----------------------------------------------------|---------|
| `STAGE_43_1_DQN_DIAGNOSIS_PLAN.md`                 | Plan    |
| `STAGE_43_1_ACTION_MASK_AUDIT.md`                  | Audit 1 |
| `STAGE_43_1_Q_VALUE_AUDIT.md`                      | Audit 2 |
| `STAGE_43_1_REWARD_AUDIT.md`                       | Audit 3 |
| `STAGE_43_1_CONTROLLED_STATE_ANALYSIS.md`          | Audit 4 |
| `STAGE_43_1_LSTM_TRAINING_ALIGNMENT.md`            | Audit 5 |
| `STAGE_43_1_TWIN_TRAINING_ALIGNMENT.md`            | Audit 6 |
| `STAGE_43_1_TRAINING_DATA_AUDIT.md`                | Audit 7 |
| `STAGE_43_1_REPAIR_RECOMMENDATION.md`              | Repair  |
| `STAGE_43_1_COMPLETION_REPORT.md`                  | This    |

### Code

* `backend/experiments/stage43_1_diag.py` — diagnostic harness with
  seven sections (action_mask_audit, q_value_audit, reward_audit,
  training_data_audit, controlled_state_tests, lstm_alignment_audit,
  twin_alignment_audit) plus four plotting helpers and a
  `manifest.json` writer.

### Artefacts under `backend/experiments/results/stage43_1/`

```
action_validity_distribution.json
q_values.json
action_reward_statistics.json
controlled_states.json
lstm_alignment.json
twin_alignment.json
training_data.json
mask_summary.json
manifest.json
figures/q_value_distribution.png
figures/action_reward_distribution.png
figures/action_distribution_over_training.png
figures/mask_validity_distribution.png
figures/mask_selected_action.png
```

## Hypothesis matrix (closure of plan)

| Hypothesis                                              | Verdict | Evidence doc                              |
|---------------------------------------------------------|:-------:|-------------------------------------------|
| H1 — Mask-induced collapse                              | NO      | `STAGE_43_1_ACTION_MASK_AUDIT.md`         |
| H2 — Reward-induced collapse                            | PARTIAL | `STAGE_43_1_REWARD_AUDIT.md`              |
| H3 — Training-data-limited                              | YES     | `STAGE_43_1_TRAINING_DATA_AUDIT.md`       |
| H4 — Environment-mismatch (LSTM, twin, faults)          | YES     | `STAGE_43_1_LSTM_TRAINING_ALIGNMENT.md`, `STAGE_43_1_TWIN_TRAINING_ALIGNMENT.md` |
| H5 — State-representation-limited                      | YES     | `STAGE_43_1_Q_VALUE_AUDIT.md`, `STAGE_43_1_CONTROLLED_STATE_ANALYSIS.md` |
| H6 — Optimisation instability                           | NO      | `STAGE_43_1_TRAINING_DATA_AUDIT.md`       |
| H7 — Action-effect-too-weak                             | NO      | `STAGE_43_1_CONTROLLED_STATE_ANALYSIS.md` |
| H8 — Implementation bug                                 | NO      | `STAGE_43_1_CONTROLLED_STATE_ANALYSIS.md` |

**Root-cause classification: I. MIXED** — B (reward) + D
(state-representation-limited) + G (environment-mismatch).

## Headline numbers (one-line summaries)

| Audit            | Headline                                                                  |
|------------------|---------------------------------------------------------------------------|
| Mask             | Mask returns `{0,1,2,3,4}` in every step; not the cause.                  |
| Q-values         | Trained net picks action 2 in 8/8 probe states. Q2 always highest.        |
| Reward           | Action 2 chosen 92% by *untrained* net; mean reward -71.6 vs -21.8 for action 4. |
| Controlled states| Action 2 selected in 5/5 deterministic cases including a faulty grid.     |
| LSTM alignment   | Training feature range [0.74, 1.08] vs LSTM [0.30, 0.49] — no overlap.    |
| Twin alignment   | Training max_risk = 0.0; only Scenario H ever produces ≥ 0.5.             |
| Training data    | 1600 transitions, 0 failures, balance always positive (mean 18.09).        |

## Repair recommendation (summary)

See `STAGE_43_1_REPAIR_RECOMMENDATION.md`. Minimum principled repair:
**R1** (use real LSTM feature) + **R2** (inject faults / pre-aged
twins) + **R4** (zero-mean final-layer init). R3 (reward redesign)
is held in reserve if R1+R2+R4 are insufficient.

## Why the verdict is **PARTIAL — CONTINUE** and not PASS

1. **The collapse is fully diagnosed.** No ambiguity about whether
   the mask, optimisation, or a code bug is the cause.
2. **No repair has been applied.** Stage 43.1 was diagnosis-only.
3. **The collapse cannot be cleared without a re-trained DQN.** The
   trained network as it stands today is unfit for the paper claims
   that rely on it. We will not make paper claims from it.
4. **A Stage-44 honest-repair stage is required.** It must run a
   10-seed validation (max), not 100, and must report action
   *diversity* before any score.

## Why the verdict is **not BLOCKED**

1. The Stage-43 architecture repair (RNG isolation, persistent EMS,
   predictive physical effect, ENS would-be-load, action 0/4 fix,
   scenario multiplier persistence, twin/LSTM channels at correct
   positions, frozen eval, checkpoint I/O) is intact.
2. The diagnostic harness is reusable for Stage-44.
3. All repair candidates have minimal, evidence-anchored edits.
4. No paper claims were written. No 100-seed run was started. No
   reward weight was tuned.

## Anti-cherry-picking checklist

- [x] **No 100-seed run.** Maximum run count during Stage 43.1
  diagnostics was 800 transitions (audit re-run) and 200 evaluation
  steps × 5 seeds × 5 scenarios for the mask audit.
- [x] **No tuning to win.** Reward weights untouched.
- [x] **No cherry-picking.** All scenarios included in audit; no
  scenario was filtered out.
- [x] **No fabricating improvement.** The collapse to action 2 is
  reported *as a failure*, not as a feature.
- [x] **No final-paper claims.** No claim is made that the DQN
  outperforms any baseline.
- [x] **All artefacts saved under `experiments/results/stage43_1/`.**

## Stage gate

* **Stage 43 (architecture repair):** PASS (per
  `STAGE_43_COMPLETION_REPORT.md`).
* **Stage 43.1 (diagnosis):** PASS for the diagnostic mandate.
* **Stage 44 (honest repair):** PENDING — gated on:
  - applying R1+R2+R4 (or an equivalent minimal repair),
  - re-running the diagnostic harness and confirming
    `n_action=0 + n_action=1 + n_action=3 > 100` in 800 transitions,
  - re-running the 10-seed × 5-scenario validation and confirming
    `fraction_action_2 < 0.7` per scenario.

## Files

- `backend/experiments/stage43_1_diag.py`
- `backend/experiments/results/stage43_1/*`
- `docs/STAGE_43_1_*.md`
