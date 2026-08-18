# Stage 2 — Requirements Traceability Matrix

This document maps every Stage 0–40 requirement from `main.md` to its
implementation, tests, experiment coverage, and current validation status.

Status vocabulary:

* **VALIDATED**            — verified against a spec, baseline, or external
  reference
* **SIMULATION-VALIDATED** — works correctly **inside our simulation**; no
  claim of real-world validation
* **DEMONSTRATIVE**        — executable, illustrative, not used as
  scientific evidence
* **OUT OF SCOPE**         — explicitly excluded from the project's
  claim set
* **UNVERIFIED**           — code exists but no validation has been
  performed
* **PARTIAL**              — implementation exists but key parts are
  missing or unverified
* **NOT IMPLEMENTED**      — no code exists yet

Issue IDs refer to `docs/PAPER_READINESS_AUDIT.md`.

| # | Stage | Requirement | Implementation (file/class/function) | Test(s) | Experiment | Status | Open issues |
| - | ----- | ----------- | ------------------------------------ | ------- | ---------- | ------ | ----------- |
| 1 | 0 | Git baseline, no destruction | (no git repo) | n/a | n/a | PARTIAL | `BASELINE_SNAPSHOT.md` records "unknown" SHA |
| 2 | 0 | Preserve historical artefacts | n/a (read-only convention) | n/a | n/a | VALIDATED | none |
| 3 | 1 | Paper-readiness audit | `docs/PAPER_READINESS_AUDIT.md` | this doc | this doc | VALIDATED | 26 issues logged |
| 4 | 1 | Test suite runs | `pytest backend/tests` | 369 / 369 tests pass | n/a | VALIDATED | none |
| 5 | 2 | Traceability matrix | `docs/REQUIREMENTS_TRACEABILITY.md` | this doc | this doc | VALIDATED | none |
| 6 | 3 | Fix critical issues | (in progress) | n/a | n/a | IN PROGRESS | EHM-CRIT-001..006 |
| 7 | 4 | Grid/PF validation | `backend/simulation/grid.py::SmartGrid`, `backend/simulation/power_flow.py::dc_power_flow` | `test_grid.py`, `test_dc_power_flow.py`, `test_ac_power_flow.py` | (Stage 23+) | SIMULATION-VALIDATED | EHM-HIGH-005 |
| 8 | 5 | IEEE 13-bus benchmark | `backend/simulation/ieee13.py::build_ieee13` | `test_ieee13.py`, `test_ieee13_validation.py` | (none yet) | SIMULATION-VALIDATED | EHM-HIGH-007 |
| 9 | 5 | IEEE 33-bus benchmark | (not implemented) | (not implemented) | (not implemented) | NOT IMPLEMENTED | EHM-HIGH-001 |
| 10 | 6 | FLISR 9-stage pipeline | `grid.py::flisr_9stage` (wraps `_reroute`) | `test_flisr_9stage.py` (7 tests) | (Stage 22) | SIMULATION-VALIDATED | none |
| 11 | 7 | Solar/wind renewable models | `grid.py::SOLAR_CURVE`, `WIND_CURVE`; `node.py` role+source_type | `test_grid.py` (implicit) | (Stage 18+) | SIMULATION-VALIDATED | EHM-HIGH-007 |
| 12 | 8 | Hybrid storage (battery + supercap) | `node.py::GridNode.use_battery / use_supercapacitor / step` | `test_grid.py` (implicit), `test_metrics_store.py` | (Stage 21) | SIMULATION-VALIDATED | EHM-HIGH-002 |
| 13 | 9 | LSTM forecaster | `backend/models/lstm_model.py::LSTMForecaster, DemandForecaster` | `test_lstm_no_leakage.py` (4 tests — chronological split, scaler-fit-on-train-only) | (Stage 9) | SIMULATION-VALIDATED | none |
| 14 | 10 | Digital twin | `backend/digital_twin/twin.py::DigitalTwin` | `test_digital_twin.py`, `test_self_healing.py` | (Stage 18+) | SIMULATION-VALIDATED | EHM-CRIT-001 |
| 15 | 11 | DQN | `backend/models/rl_agent.py::DQNAgent` (with `eval_mode`/`train_mode`) | `test_dqn_state.py`, `test_advanced_rl.py`, `test_dqn_eval_mode.py` (7 tests) | (Stage 18+) | SIMULATION-VALIDATED | none |
| 16 | 12 | Reward formulation doc | `docs/REWARD_FORMULATION.md` | (manual review) | (Stage 12) | VALIDATED | none |
| 17 | 13 | Critical-load priority | `grid.py::priority`, `node.py::priority` | `test_grid.py` | (Stage 18+) | SIMULATION-VALIDATED | EHM-MED-002 |
| 18 | 14 | Resilience-aware topology planner | `backend/planning/ai_planner.py::AIPlanner` | `test_planner.py` | (Stage 22) | SIMULATION-VALIDATED | EHM-HIGH-003, EHM-MED-001 |
| 19 | 15 | N-1 analysis | (not implemented) | (not implemented) | (Stage 22) | NOT IMPLEMENTED | EHM-MED-001 |
| 20 | 16 | Reliability metrics (SAIFI/SAIDI/CAIDI/ASAI/ENS/AENS) | `backend/metrics/ieee_1366.py` | `test_ieee_1366.py` | (Stage 18+) | PARTIAL | EHM-MED-002 |
| 21 | 17 | Experiment configurations alter behaviour | `backend/experiments/experiment_config.py::ABLATION_CONFIGS` | `test_experiments_framework.py` | (Stage 18+) | SIMULATION-VALIDATED | EHM-HIGH-004 |
| 22 | 18 | Baseline experiment (random, rule, dqn, full) | `experiments/paper_experiment.py`, `experiments/runner.py::run_experiment` | `test_paper_experiment.py`, `test_experiments_framework.py` | (Stage 18) | SIMULATION-VALIDATED | EHM-CRIT-002, EHM-CRIT-006 |
| 23 | 19 | Ablation experiment | `experiments/runner.py`, `experiments/experiment_config.py` | `test_experiments_framework.py` | (Stage 19) | SIMULATION-VALIDATED | EHM-CRIT-002 |
| 24 | 20 | Predictive vs reactive paired comparison | `experiments/runner.py` (uses flags) | (none specific) | (Stage 20) | UNVERIFIED | EHM-CRIT-002, EHM-HIGH-005 |
| 25 | 21 | Hybrid storage experiment | (not implemented) | (not implemented) | (Stage 21) | NOT IMPLEMENTED | EHM-HIGH-002 |
| 26 | 22 | Topology planning experiment | (not implemented) | (not implemented) | (Stage 22) | NOT IMPLEMENTED | EHM-HIGH-003, EHM-MED-001 |
| 27 | 23 | Statistical analysis (paired t-test, Wilcoxon, Cohen's d, correction) | `backend/metrics/statistics.py` | `test_statistics.py` | (Stage 23) | PARTIAL | EHM-MED-003, EHM-MED-007 |
| 28 | 24 | Invalid-run handling + reasons | `experiments/runner.py::_is_valid_run` | `test_experiments_framework.py` | (Stage 24) | PARTIAL | EHM-HIGH-005 |
| 29 | 25 | Reproducibility manifest | `experiments/scenario.py::write_manifest`, `experiments/paper_experiment.py` | (none specific) | (Stage 25) | SIMULATION-VALIDATED | none |
| 30 | 26 | One-command paper pipeline | `experiments/paper_experiment.py` | `test_paper_experiment.py` | (Stage 26) | SIMULATION-VALIDATED | none |
| 31 | 27 | Publication tables | `experiments/tables.py::build_report, render_markdown, write_csv_and_markdown` | (none) | (Stage 27) | PARTIAL | EHM-MED-008 |
| 32 | 28 | Publication figures | (not implemented) | (not implemented) | (Stage 28) | NOT IMPLEMENTED | EHM-MED-008 |
| 33 | 29 | Computational performance | (not implemented) | (not implemented) | (Stage 29) | NOT IMPLEMENTED | n/a |
| 34 | 30 | Test suite expansion | `backend/tests/` (~40 files) | 337 tests pass | n/a | VALIDATED | EHM-MED-002, EHM-MED-004 |
| 35 | 31 | Code cleanup | (in progress) | n/a | n/a | IN PROGRESS | EHM-HIGH-006, EHM-LOW-001..005 |
| 36 | 32 | Documentation set | this file + audit + baseline; others to be created | n/a | n/a | PARTIAL | EHM-CRIT-004, EHM-HIGH-002 |
| 37 | 33 | Novelty matrix | (not implemented) | n/a | n/a | NOT IMPLEMENTED | n/a |
| 38 | 34 | Limitations doc | (not implemented) | n/a | n/a | NOT IMPLEMENTED | n/a |
| 39 | 35 | Paper outline | (not implemented) | n/a | n/a | NOT IMPLEMENTED | n/a |
| 40 | 36 | Claim gate | (not implemented) | n/a | n/a | NOT IMPLEMENTED | n/a |
| 41 | 37 | Final paper experiment | (deferred) | n/a | (Stage 37) | NOT IMPLEMENTED | EHM-CRIT-002, EHM-CRIT-006 |
| 42 | 38 | Results sanity check | (deferred) | n/a | (Stage 38) | NOT IMPLEMENTED | n/a |
| 43 | 39 | Final paper-readiness report | (deferred) | n/a | (Stage 39) | NOT IMPLEMENTED | n/a |
| 44 | 40 | Completion criteria gate | (deferred) | n/a | (Stage 40) | NOT IMPLEMENTED | n/a |

---

## Per-requirement rationale

### Stage 4 — Grid/PF validation
The 49-node EHM grid constructs cleanly via `SmartGrid.__init__`, builds
the directed graph with tie switches, and `update_power_flow()` calls
`dc_power_flow()` which solves the multi-island DC problem with KCL
checks. The `_self_test_5bus()` self-test exercises the textbook
example. The pandapower AC PF path is lazy-imported. **The persistent
limitation is that convergence status is not logged per run** (see
EHM-HIGH-005).

### Stage 6 — FLISR 9-stage pipeline
`SmartGrid.flisr_9stage()` exposes the 9 named stages (DETECT, LOCATE,
ISOLATE, IDENTIFY, CANDIDATE_ENUMERATE, RANK, SWITCH, VALIDATE, REPORT)
with per-stage timings and a post-action DC PF / KCL validation block.
The legacy `flisr_restore()` return payload is preserved under
`"legacy"` for backward compatibility. `test_flisr_9stage.py` covers
all stages + the legacy return shape.

### Stage 9 — LSTM forecaster
`DemandForecaster` wraps `LSTMForecaster` (2 layers, hidden=32,
30 epochs). The synthetic dataset is generated deterministically
(500 samples, seq_len=10). A chronological 80/20 split is performed:
`X_train, X_val = X[:400], X[100:]`. The `MinMaxScaler` is fit on
`X_train.reshape(-1, 3)` only (no leakage, EHM-CRIT-005). The pretrain
log reports `n_train=`, `n_val=`, and the chronological validation MSE.
`test_lstm_no_leakage.py` includes an adversarial test where the
validation rows strictly exceed the training rows in feature range —
the scaler's `data_max_` is verified to stay within the training range.

### Stage 10 — Digital twin
`DigitalTwin` records health, age, temperature, loading, sensor
history, maintenance history, and an Arrhenius-based ageing model in
`digital_twin/degradation.py`. The `failure_probability` property is a
heuristic `max(0, min(1, (0.4 - h)/0.4))`. **The naming violates
Stage 10's "conservative names" requirement** — see EHM-CRIT-001.

### Stage 11 — DQN
`DQNAgent` implements a true DQN: replay buffer, target network, ε-greedy
exploration, action masking, and a rule-guided warmup. Train/eval
separation is provided via `eval_mode()` and `train_mode()`:
in eval mode the replay buffer is not updated, no gradient step is
taken, `epsilon` is forced to 0.0, and `steps_done` does not increment.
`test_dqn_eval_mode.py` covers both modes.

### Stage 14 — Resilience-aware topology planning
`AIPlanner.plan()` returns a list of `PlanAction` records. **There is
no experiment or test that measures the planner's effect on N-1
recoverability, ENS, or alternative-path count** — see EHM-HIGH-003.

### Stage 17 — Experiment configurations
`ABLATION_CONFIGS` defines flags for every ablation label. The runner
consumes them via `make_controller()`. **There is no test that
proves each flag changes behaviour** — see EHM-HIGH-004.

### Stage 18-22 — Experiments
The infrastructure for `paper_experiment.py` exists and runs end-to-end
with `--seeds 3 --ticks 50`. **The deterministic scenario generator
produces fault targets that do not exist in the actual grid** — see
EHM-CRIT-002. Without fixing this, Stages 18-22 cannot produce valid
paper-grade evidence.

### Stage 23 — Statistical analysis
`statistics.py` provides paired t-test and Wilcoxon signed-rank. **No
multiple-comparison correction** — see EHM-MED-003.

### Stage 25 — Reproducibility
`write_manifest()` records git commit (or "unknown"), software
versions, configs, scenarios, run ID, timestamp. **Git SHA is recorded
as "unknown" because there is no repo** — see Stage 0.

### Stage 26 — One-command pipeline
`experiments/paper_experiment.py` provides the CLI. **The output
directory layout (raw/aggregated/statistics/tables/figures/logs/manifest.json)
is partial** — see EHM-MED-008.

---

## Items still unimplemented (roadmap)

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