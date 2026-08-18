# Technical correction log

## TC-001 — FLISR runner-to-owner interface disconnected

| Field | Record |
|---|---|
| Classification | B. REQUIRED INTERFACE REPAIR |
| File | `experiments/stress_runner.py` |
| Function/class | `_capacity_constrained_restore`, `run_stress_single` |
| Previous behavior | Historical Experiment B checked/called `grid.flisr_restore`, but the concrete restoration implementation is `simulation.scada.ScadaControlCenter._flisr_restore(grid, ems)`. |
| Corrected behavior | The stress runner constructs the SCADA FLISR owner without training AI models and invokes `_flisr_restore(grid, ems=None)` when `enable_flisr=True`. |
| Evidence defective | Archived 540-run Experiment B has zero `flisr_calls` across FLISR-enabled policies; `SmartGrid` does not provide the expected callable while SCADA owns the restoration implementation. |
| Why necessary | The intended restoration mechanism otherwise never executes in Experiment B. |
| Experimental parameters changed | No. |
| Tests added | `test_flisr_is_invoked_and_changes_network_state_when_feasible`, `test_no_flisr_ablation_disables_flisr`. |
| Validation result | PASS: execution-path tests pass; smoke records nonzero FLISR calls for FLISR-enabled policies and zero calls for FLISR-disabled policies. |

## TC-002 — Predictive recommendations were counted without dispatch evidence

| Field | Record |
|---|---|
| Classification | A. VERIFIED BUG FIX / EXECUTION-PATH REPAIR |
| File | `experiments/stress_runner.py` |
| Function/class | `_dispatch_predictive_action`, predictive block in `run_stress_single` |
| Previous behavior | The runner counted predictor `action_count` as predictive actions but did not dispatch declarative `PredictiveAction` records to grid primitives. |
| Corrected behavior | The runner now separately records predictions, recommendations, accepted recommendations, dispatched actions, applied actions, rejections, and failures. Existing action kinds are dispatched through grid primitives. |
| Evidence defective | `backend/self_healing/predictor.py` states the module is pure and that the caller must apply declarative actions. |
| Why necessary | A recommendation is not evidence of network control participation. |
| Experimental parameters changed | No. |
| Tests added | `test_predictive_action_dispatch_path`. |
| Validation result | PASS: dispatch primitive applies a tie-switch action in deterministic test. Smoke generated zero recommendations under frozen twin risk logic; this is reported as observed null activation, not tuned. |

## TC-003 — Digital twin lifecycle was tied to predictive controller

| Field | Record |
|---|---|
| Classification | A. VERIFIED BUG FIX |
| File | `experiments/stress_runner.py` |
| Function/class | `run_stress_single` |
| Previous behavior | The twin was created only inside the predictive-healing block. `no_predictive` has `enable_twin=True` but recorded zero twin updates. |
| Corrected behavior | The twin is instantiated and synchronized whenever `enable_twin=True`; predictive consumes it only when predictive healing is also enabled. |
| Evidence defective | `ExperimentConfig` is the stated source of truth and lists `digital_twin` active for `no_predictive`; the prior smoke matrix showed `no_predictive` twin updates = 0. |
| Why necessary | Active-module labels must correspond to runtime execution. |
| Experimental parameters changed | No. |
| Tests added | Covered by smoke component activation matrix. |
| Validation result | PASS: fresh smoke matrix records twin updates for all `enable_twin=True` policies, including `no_predictive`. |

## TC-004 — LSTM execution evidence missing

| Field | Record |
|---|---|
| Classification | A. VERIFIED BUG FIX / INSTRUMENTATION |
| File | `experiments/runner.py`, `experiments/stress_runner.py` |
| Function/class | `_DQNAdapter`, `ModuleCallCounters`, `run_stress_single` |
| Previous behavior | The DQN adapter did not provide per-run evidence that the LSTM forecaster was called/consumed or disabled by `no_lstm`. |
| Corrected behavior | The DQN adapter gates the forecaster on `enable_lstm` and records model calls, inference successes/failures, and consumed outputs. |
| Evidence defective | Controller labels alone could not prove model participation or ablation suppression. |
| Why necessary | Execution evidence is required for ablation validity. |
| Experimental parameters changed | No. |
| Tests added | `test_twin_and_lstm_activation_contracts`; smoke matrix validates model-call counts. |
| Validation result | PASS: smoke records model calls for LSTM-enabled DQN policies and zero calls for No-LSTM/DQN-core/baselines. |

## TC-005 — No-Twin observable-risk fallback refused/removed

| Field | Record |
|---|---|
| Classification | D. EXPERIMENTAL DESIGN CHANGE — REFUSED |
| File | `backend/self_healing/predictor.py` |
| Function/class | `PredictiveSelfHealer.run`, removed `assess_observable_state` |
| Previous behavior | A prior working-tree change introduced a new non-twin observable-risk model for `twin_registry=None`. |
| Corrected behavior | Removed the fallback and restored the frozen twin-driven predictor contract: without a twin registry, predictive assessment yields no twin-derived risks. |
| Evidence defective | No repository evidence found that the frozen Experiment B specified a new observable-risk model for No-Twin. `PredictiveSelfHealer` documentation identifies the twin registry as the risk source. |
| Why necessary | Adding a new risk model would alter ablation behavior and the frozen hypothesis. |
| Experimental parameters changed | No; an unverified design change was removed. |
| Tests added | Smoke matrix reports No-Twin predictive calls but zero twin updates and zero recommendations under frozen logic. |
| Validation result | PASS: No-Twin bypasses twin and does not receive artificial substitute risk. |

## TC-006 — Stress-runner CLI Windows console encoding failure

| Field | Record |
|---|---|
| Classification | B. REQUIRED INTERFACE REPAIR |
| File | `experiments/stress_runner.py` |
| Function/class | `main` |
| Previous behavior | The CLI printed mojibake/non-CP1252 text and raised `UnicodeEncodeError` on Windows after writing outputs. |
| Corrected behavior | Completion print is ASCII-only. |
| Evidence defective | Fresh smoke run wrote JSON/CSV/manifest but exited nonzero during console printing. |
| Why necessary | Experiment execution must return successful status after successful run/write. |
| Experimental parameters changed | No. |
| Tests added | `py_compile`; smoke output verified from disk. |
| Validation result | PASS: source compiles after print repair. |

## Analysis findings pending full corrected rerun

- Experiment A data exists in `paper_results/raw/baseline_results.json`; historical A-vs-B `n=0` was caused by loader assumptions around missing/nominal stress-level fields. This is an analysis correction to apply only when regenerating A-vs-B.
- Holm family is established from `paper_results_experiment_B/PRIMARY_OUTCOMES.md`: Holm correction across the four primary outcomes for each controller pair, retaining raw and adjusted p-values.
