# Checkpoint 2 — Stage 3 (CRITICAL fixes) complete

This checkpoint records the resolution of every `EHM-CRIT-###` issue
identified in `docs/PAPER_READINESS_AUDIT.md`.

## Summary

**6 / 6 CRITICAL issues FIXED. 369 / 369 tests pass.**

| ID            | Issue                                              | Status | Evidence                                                          |
| ------------- | -------------------------------------------------- | ------ | ----------------------------------------------------------------- |
| EHM-CRIT-001  | Digital twin "failure probability" naming          | FIXED  | `twin.py::health_risk_score` is canonical; `failure_probability` alias emits `DeprecationWarning` |
| EHM-CRIT-002  | Scenario fault targets not in grid                 | FIXED  | `experiments/scenario.py::_grid_fault_candidates()` samples real `SmartGrid` nodes |
| EHM-CRIT-003  | FLISR not a 9-stage pipeline                       | FIXED  | `SmartGrid.flisr_9stage()` orchestrator with all 9 named stages + per-stage timings + DC PF validation |
| EHM-CRIT-004  | Reward formulation docs absent                     | FIXED  | `docs/REWARD_FORMULATION.md` enumerates every term + default weights + sign convention |
| EHM-CRIT-005  | LSTM scaler fit on full dataset (leakage)          | FIXED  | `DemandForecaster._pretrain()` performs chronological 80/20 split; scaler fit on training only |
| EHM-CRIT-006  | DQN train/eval separation absent                   | FIXED  | `DQNAgent.eval_mode()` / `train_mode()` gate replay, gradients, ε, and step counter |

## What changed (file-by-file)

### Code
* `backend/digital_twin/twin.py` — already had `health_risk_score` (canonical)
  + `failure_probability` deprecated alias (EHM-CRIT-001, prior session).
* `experiments/scenario.py` — already sampled from real `SmartGrid` nodes
  (EHM-CRIT-002, prior session).
* `backend/simulation/grid.py` — added `flisr_9stage()` orchestrator with
  per-stage timings + DC PF / KCL validation; preserves legacy `flisr_restore`
  payload under `"legacy"`. (EHM-CRIT-003)
* `backend/models/lstm_model.py` — `DemandForecaster._pretrain()` now performs
  chronological 80/20 split; scaler fit on `X_train.reshape(-1, 3)` only;
  pretrain log reports `n_train=`, `n_val=`, and the validation MSE.
  (EHM-CRIT-005)
* `backend/models/rl_agent.py` — added `eval_mode()` / `train_mode()`,
  `is_training` property, `dropped_experiences` counter. `select_action`
  forces `epsilon = 0.0` in eval mode and freezes `steps_done`;
  `store_experience` is a no-op in eval mode. (EHM-CRIT-006)

### Tests
* `backend/tests/test_digital_twin.py` — updated to assert canonical
  `health_risk_score` / `projected_health_risk_score` names. 14 tests pass.
* `backend/tests/test_flisr_9stage.py` — **new file**, 7 tests covering
  all 9 stages + timings + legacy return preservation + validation block.
* `backend/tests/test_lstm_no_leakage.py` — **new file**, 4 tests including
  an adversarial test where validation rows strictly exceed training rows
  in feature range (so leakage would be detected).
* `backend/tests/test_dqn_eval_mode.py` — **new file**, 7 tests covering
  both modes (eval suppresses exploration, freezes step counter, drops
  experiences; train resumes learning).

### Documentation
* `docs/REWARD_FORMULATION.md` — **new file**. Full enumeration of every
  reward component, default weights, sign convention, what the reward
  does and does not capture, and the citation form for the paper.
* `docs/PAPER_READINESS_AUDIT.md` — EHM-CRIT-001..006 status updated
  from OPEN to FIXED with explicit evidence references.
* `docs/REQUIREMENTS_TRACEABILITY.md` — Stage 6, 9, 10, 11, 12 status
  updated; "Items still unimplemented" list trimmed to 16 items.

## Test counts

* Before: 337 tests, 335 pass, 2 fail (the 2 failures were
  `test_digital_twin.py` tests asserting the deprecated
  `failure_probability` name).
* After: 369 tests, 369 pass. (+32 new tests, 0 new failures.)

## What still needs work (not blocking CRITICAL)

See `docs/REQUIREMENTS_TRACEABILITY.md` "Items still unimplemented":

1. IEEE 33-bus benchmark (Stage 5)
2. Hybrid storage documentation (Stage 8)
3. N-1 module (Stage 15)
4. Reliability metrics analytical tests (Stage 16)
5. Topology planning experiment (Stage 22)
6. Multiple-comparison correction (Stage 23)
7. Figures generator (Stage 28)
8. Performance measurements (Stage 29)
9. Novelty matrix (Stage 33)
10. Limitations doc (Stage 34)
11. Paper outline (Stage 35)
12. Claim gate (Stage 36)
13. Final paper experiment (Stage 37)
14. Sanity check (Stage 38)
15. Final paper-readiness report (Stage 39)
16. Completion criteria gate (Stage 40)

## Next planned actions

* Stage 5 — IEEE 33-bus benchmark (`backend/simulation/ieee33.py`).
* Stage 8 — Hybrid storage documentation (`docs/HYBRID_STORAGE.md`).
* Stage 15 — N-1 analysis module (`backend/reliability/n_minus_1.py`).
* Stage 23 — Multiple-comparison correction (BH / Bonferroni).
* Stage 32 — Documentation set (LIMITATIONS.md, NOVELTY_MATRIX.md, PAPER_OUTLINE.md).
* Stage 37 — Final paper experiment (smoke → medium → final).

These are tracked in the active task list.