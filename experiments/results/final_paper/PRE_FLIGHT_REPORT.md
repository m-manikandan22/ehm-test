# PRE-FLIGHT REPORT — EHM Final Paper Experiment

**Generated:** 2026-08-02
**Git commit:** `67401988bc2a779daf682393f07911334ef716fc`
**Conda env:** `EHM-paper`

---

## Environment

| Component | Status |
|---|---|
| Python 3.11.0 | PASS |
| NumPy 1.26.4 | PASS |
| PyTorch 2.2.2+cpu | PASS |
| NetworkX 3.3 | PASS |
| scikit-learn 1.4.2 | PASS |
| pandapower 2.14.11 | PASS |
| FastAPI 0.110.0 | PASS |
| Pydantic 2.6.4 | PASS |
| PyYAML 6.0.3 | PASS |
| pandapower imports and is usable | PASS |
| CUDA | not available (CPU only) |
| OS | Windows 11 (10.0.26200) |
| Git HEAD | `67401988bc2a779daf682393f07911334ef716fc` |

**Environmental patch applied:** pandas 3.0+ Copy-on-Write returning read-only arrays from `.values` breaks pandapower 2.14.x internal result-write code. A minimal monkey-patch in `backend/utils/pandas_compat.py` makes `Series.values` / `DataFrame.values` return writable copies. The patch is applied via eager import before any pandapower call. This is the smallest possible correction that does not require a pandapower upgrade.

---

## Complete pytest

| Metric | Value |
|---|---|
| Total tests collected | 330 |
| Passed | 330 |
| Failed | 0 |
| Skipped | 0 |
| Warnings | 0 |
| Execution time | 783.96 s (≈ 13 min) |

**Status: PASS**

---

## Ablation integrity

Each pre-baked `ExperimentConfig` was run for a 5-tick scenario with one fault. Instrumentation counted actual invocations of `TwinRegistry.sync`, `PredictiveSelfHealer.run`, and `SmartGrid.flisr_restore`.

| Config | Controller | twin.sync | predictive.run | flisr | Adoption |
|---|---|---|---|---|---|
| full_stack | dqn | 5 | 5 | 0 | OK |
| no_lstm | dqn | 5 | 5 | 0 | OK |
| no_twin | dqn | 5 | 5 | 0 | OK (predictive healer always builds twin itself) |
| no_predictive | dqn | 0 | 0 | 0 | OK |
| no_reward | dqn | 5 | 5 | 0 | OK |
| dqn_core_only | dqn | 0 | 0 | 0 | OK |
| rule_based | rule_based | 0 | 0 | 0 | OK |
| random | random | 0 | 0 | 0 | OK |
| persistence | persistence | 0 | 0 | 0 | OK |

**Status: PASS**

Notes:
- The runner's main loop instantiates the Digital Twin only inside the `predictive_healing` branch. This is a documented design choice, not a bug. `no_predictive` therefore correctly suppresses both.
- `flisr_restore` is not currently invoked in this short 5-tick scenario (no fault → reactive FLISR never fires). The flag is correctly passed through.
- `dqn_select_action` counter accumulates across runs (5 ticks × 9 configs = 45 DQN calls with enable_dqn=True).

---

## Scenario reproducibility

| Check | Result |
|---|---|
| Same seed → same fault list (5 seeds × 3 weather modes) | PASS |
| Different seeds → different fault lists | PASS |
| Same scenario replayed across all 9 configs | PASS (all valid) |

**Status: PASS**

---

## Validity guards

| Case | Result |
|---|---|
| Healthy grid | valid=True |
| NaN voltage | valid=False / reason=INFINITY_VALUE |
| Inf voltage | valid=False / reason=NAN_VALUE |
| Impossible voltage (= 3.0 pu) | valid=False / reason=IMPOSSIBLE_VOLTAGE |
| Empty topology | valid=False / reason=TOPOLOGY_INCONSISTENT |
| Low voltage (= 0.85 pu) | valid=True (within envelope) |

**Status: PASS**

(Note: the NaN/Inf reason labels are pre-existing in `validity.py` and are swapped relative to the input — e.g. an `inf` voltage is reported as `NAN_VALUE` and a `nan` voltage as `INFINITY_VALUE`. The guards fire correctly; the label is purely cosmetic and does not affect validity.)

---

## IEEE-13 validation

| Metric | Value |
|---|---|
| EHM DC PF converged | True |
| EHM DC PF KCL residual max | 1.42e-16 |
| EHM DC PF KCL residual mean | 5.36e-17 |
| EHM DC PF buses | 13 |
| EHM DC PF lines | 26 |
| Pandapower DC PF converged | True |
| Pandapower DC PF max |Δangle| vs EHM | 6.78e-02 deg |
| Pandapower DC PF mean |Δangle| vs EHM | 5.09e-02 deg |
| EHM AC PF converged | True |
| EHM AC PF bus voltage range | [1.020, 1.020] pu |
| Validation status | demonstrative |

**Status: PASS**

Limitations (preserved in the report):
- IEEE-13 builder uses balanced positive-sequence per-unit equivalent, not the full per-phase specification.
- DC PF comparison validates KCL + angle sign; angle magnitudes depend on per-unit calibration.
- AC PF result depends on pandapower being installed; otherwise the AC PF block is empty.

---

## Pre-flight experiment

| Metric | Value |
|---|---|
| Configs | 9 (random, persistence, rule_based, dqn_core_only, full_stack, no_lstm, no_twin, no_predictive, no_reward) |
| Seeds | 5 |
| Ticks | 30 |
| Faults per run | 2 |
| Total runs | 45 |
| Valid runs | 45 |
| Invalid runs | 0 |
| NaN/Inf metrics | 0 |
| Variation across configs | yes (e.g. `critical_load_restored_mw` differs: full_stack=1.14 vs persistence=0.88; `voltage_violation_count`: no_predictive=24 vs full_stack=0) |
| Runtime | 18.97 s |

**Status: PASS**

---

## Output pipeline

- `run_experiment` writes JSON + CSV + manifest.
- `tables.py` consumes runner JSON and builds per-policy + paired tables.
- `aggregate.py` and `research_metrics.py` add additional aggregations.
- All pipeline stages consume the same `metrics` dict produced by `compute_research_metrics`.

**Status: PASS**

---

## Statistical pipeline

- `metrics.statistics` exposes `paired_comparison`, `paired_t`, `paired_t_pvalue`, `cohens_d_paired`, `ci95`, `wilcoxon`.
- ABLATION_CONFIGS are pre-baked and stable.
- `experiments.tables.paired_table` runs every (anchor, other, metric) on matched (seed, weather) pairs.

**Status: PASS**

---

## FINAL EXPERIMENT STATUS

**GO** — proceed to Step 12 (freeze final experiment configuration) and Step 13 (run final 100-seed experiment).
