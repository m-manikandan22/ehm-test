# Stage 46.1 — Completion Report

## 1. Objective

Verify and repair the information-flow/ablation mechanism for the frozen
Stage-44 DQN so the Stage-45 ablation claims are grounded in evidence,
and produce a five-level evidence chain (feature → state → Q → action →
physical outcome) for LSTM, Digital Twin, EMS, and Predictive-healing
information paths — without retraining or modifying the checkpoint.

## 2. Constraint compliance

| Constraint                             | Status |
|----------------------------------------|--------|
| No retraining                          | ✓      |
| No architecture change                 | ✓      |
| No reward / hyperparameter change      | ✓      |
| No validation-seed change              | ✓      |
| Checkpoint byte-identical              | ✓ SHA-256 `eb7bbed…` before and after |
| No 100-seed run                        | ✓ (2-seed diagnostic only) |
| No manufactured ablation effects       | ✓ (policy-pinning honestly documented) |

## 3. Root cause

The Stage-45 ablation degeneracy has three independent causes, only one
of which is a wiring bug:

1. **LSTM eval wiring bug (fixed):** the validation harness fed a
   hard-coded constant window to the forecaster (`0.6099` on every
   scenario) instead of the real history the training loop and production
   runner use; `no_lstm` was the only cell that differed at all (0.5
   sentinel). Repair: real per-run `deque(maxlen=10)` of
   `(load, gen, weather)` installed via `set_lstm_history` in both
   validation loops; forecast now varies 0.06–0.22 across the Stage-45
   scenarios.
2. **Twin scenario coverage:** correctly wired, but twin risk is zero on
   A/E/I/J (degradation keeps health ≥ 0.4); only scenario H carries a
   health_override and shows a strong channel (‖ΔQ‖ = 6.38).
3. **EMS/Predictive are external:** their effects never reach the DQN
   observation by design (verified empirically).

## 4. What was delivered

### Code
- `backend/experiments/stage44_validation.py` — `set_lstm_history()`,
  real-history `_predicted_load()`, per-run deque + weather proxy +
  per-step append in `_run_controller_on_scenario`.
- `backend/experiments/stage45_validation.py` — same repair in its loop.
- `backend/experiments/stage46_1_information_flow.py` — single-state
  ablation experiment (5 configs × 9 states) + checkpoint hash guard.
- `backend/experiments/stage46_1_scan_argmax_flips.py` — 320-step
  argmax-flip scan (A/E/I/J).
- `backend/experiments/stage46_1_check_lstm_wiring.py` — wiring smoke test.
- `backend/tests/test_stage46_1_information_flow.py` — 8 tests, all pass.

### Results (`backend/experiments/results/stage46_1/`)
- `checkpoint_hash.json` — SHA-256 before/after, unchanged.
- `state_comparison.json` — 36 records (per-feature diffs incl. full 78-dim
  states).
- `q_value_comparison.json` — 36 records (all 5 heads, dQ, argmax).
- `action_comparison.json` — 36 records (argmax, validity, physical
  outcomes from identical snapshots).
- `information_sensitivity.json` — 36 rows (per feature block: Δstate,
  ΔQ, Δargmax, Δphysical).
- `manifest.json` — provenance (checkpoint hash, configs, feature blocks,
  git SHA).
- `validation_40runs.json` / `validation_manifest.json` — 40-run repaired
  harness diagnostic.

### Documentation
- `docs/STAGE_46_1_IMPLEMENTATION_PLAN.md`
- `docs/STAGE_46_1_INFORMATION_FLOW_TRACE.md`
- `docs/STAGE_46_1_STATE_LAYOUT.md`
- `docs/STAGE_46_1_ABLATION_AUDIT.md`
- `docs/STAGE_46_1_COMPLETION_REPORT.md` (this file)

## 5. Evidence-chain verdict

| Channel     | L1 feature | L2 state | L3 Q | L4 action | L5 physical |
|-------------|-----------|----------|------|-----------|-------------|
| LSTM        | ✓         | ✓        | ✓    | ✗ (pinned policy) | ✗ |
| Twin        | ✓         | ✓ (H)    | ✓ (H) | ✗ | ✗ |
| EMS         | ✗ (external, by design) | — | — | — | — |
| Predictive  | ✗ (external, pure API)  | — | — | — | — |

## 6. Residual risk / limits

- The 40-run diagnostic is descriptive (2 seeds), not inferential; no
  significance claims are made.
- The forecast weather-proxy convention differs slightly from training
  (`0.2/0.85/0.5` vs `demand_multiplier-1`), documented in the state-layout
  doc.
- Action-level ablation differentiation requires either scenarios that
  push transformer health below 0.4 (to activate the twin channel) or a
  re-trained policy whose action gap admits feature-scale perturbations —
  both explicitly out of scope here.

## 7. Recommendation for downstream stages

- When reporting ablation results, describe the degeneracy as a property
  of the frozen policy's action-selection margin on the scenario set, and
  cite the now-correct LSTM wiring as the removed confound.
- Future stage may re-run the Stage-45 ablation table after any retraining
  to populate L4/L5 evidence with a policy that is not pinned to a single
  action.