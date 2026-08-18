# Stage 1 - Paper Readiness Audit

This document records every issue identified during the Stage 1 repository
inspection. Items are stored with stable IDs (`EHM-CRIT-###`, `EHM-HIGH-###`,
`EHM-MED-###`, `EHM-LOW-###`) so each entry can be referenced from the
checkpoints, the traceability matrix, and the final report.

Status vocabulary:

* **OPEN**         - known, not yet fixed
* **IN PROGRESS**  - actively being addressed
* **FIXED**        - verified by tests/experiments
* **DEFERRED**     - consciously postponed; documented in
  `docs/LIMITATIONS.md`

Validation vocabulary used in section "Validation status":

* **VALIDATED**            - verified against a specification, baseline, or
  external benchmark
* **SIMULATION-VALIDATED** - the system behaves correctly **inside our
  simulation**; no claim of real-world validation
* **DEMONSTRATIVE**        - executable, illustrative, not used as scientific
  evidence
* **OUT OF SCOPE**         - explicitly excluded from the project's claim set
* **UNVERIFIED**           - code exists but no validation has been performed

---

## 0. Pre-flight summary

| Item                                              | Status                                                       |
| ------------------------------------------------- | ------------------------------------------------------------ |
| Repository under version control                  | **NO** - `git rev-parse` - `fatal: not a git repository`     |
| Git SHA recordable                                | **NO** - `manifest.json` records `"unknown"`                 |
| Existing test suite                               | **PASSING** - 462 tests collected; 462 pass after Stage 1 fixes (EHM-NEW-001) |
| Historical experiment outputs preserved           | **YES** - `paper_results/`, `paper_results_experiment_B/`, `correction_audit_phase*` retained |
| Existing IEEE 13-bus support                      | **YES** - `backend/simulation/ieee13.py`                      |
| Existing IEEE 33-bus support                      | **NO** - required by main.md Stage 5                         |
| Existing DQN agent                                | **YES** - `backend/models/rl_agent.py`                       |
| Existing LSTM forecaster                          | **YES** - `backend/models/lstm_model.py`                     |
| Existing digital twin                             | **YES** - `backend/digital_twin/twin.py`                     |
| Existing IEEE 13-bus validation test              | **YES** - `backend/tests/test_ieee13.py`, `test_ieee13_validation.py` |

The Stage 0 baseline is recorded in `docs/BASELINE_SNAPSHOT.md`. The
`main.md` repository is treated as the Single Source of Truth throughout
this audit.

---

## 1. CRITICAL issues

### EHM-CRIT-001 - Digital twin heuristic labelled as "failure probability"

* **Severity** - CRITICAL
* **Component** - `backend/digital_twin/twin.py`
* **Problem** - `DigitalTwin.failure_probability` is implemented as a
  heuristic: `max(0, min(1, (0.4 - h)/0.4))` when `h < 0.4`, else `0`. It
  is *not* a calibrated probability from a probabilistic model or a
  Cox/Weibull survival model. The property name appears in 30+ call sites
  and in published-style documentation.
* **Why it matters scientifically** - main.md Stage 10 (ABSOLUTE RULE #3)
  forbids claiming calibrated failure probability. Calling a heuristic
  "failure probability" risks reviewer objection and inflates the
  contribution claim.
* **Affected files** - `backend/digital_twin/twin.py`,
  `backend/self_healing/predictor.py`,
  `backend/digital_twin/twin_registry.py`,
  `backend/tests/test_digital_twin.py`,
  `backend/tests/test_self_healing.py`.
* **Required correction** - rename the property to `health_risk_score`,
  re-export `failure_probability` as a deprecated alias that simply
  returns the same value (so existing tests keep passing) but emits a
  `DeprecationWarning`. Update all caller-facing documentation. Add a
  one-line method docstring explicitly stating the heuristic derivation.
* **Validation method** - pytest passes; new `test_digital_twin.py` test
  asserts that the deprecated alias still works and that the new name
  is the canonical read.
* **Status** - **FIXED** - `DigitalTwin.health_risk_score` is the canonical
  property (derived from `health`); `failure_probability` is a deprecated
  alias that emits `DeprecationWarning`. Tests in
  `backend/tests/test_digital_twin.py` now assert the canonical names.
  All 14 existing digital-twin tests pass.

### EHM-CRIT-002 - Experiments scenario generator targets non-existent node IDs

* **Severity** - CRITICAL
* **Component** - `experiments/scenario.py`
* **Problem** - `make_scenario()` creates candidate fault targets from
  `H00..H79`, `T0..T11`, `G0..G2`, `S0..S5`. The actual default 49-node
  EHM grid uses `GEN_SOLAR`, `GEN_WIND`, `GEN_NUCLEAR`, `GEN_COAL`,
  `GEN_GAS`, `S_MAIN`, `T_A`, `T_B`, `T_C`, `P_A1..P_A4`, `P_B1..P_B4`,
  `P_C1..P_C4`, `HOSP`, `IND0`, `H0..H29`. The fault injection
  `grid.inject_failure(fault.target)` will raise `KeyError` for every
  target the generator picks.
* **Why it matters scientifically** - the paper-grade runner is the
  primary evidence source. If the deterministic scenario generator
  routinely produces invalid faults, the entire Stage 23-26 pipeline is
  invalidated.
* **Affected files** - `experiments/scenario.py`.
* **Required correction** - derive candidate targets from the actual
  `grid.nodes` of the SmartGrid instance passed to `make_scenario`, or
  filter out unknown IDs after sampling. Add a unit test that verifies
  every scenario fault target exists in the grid.
* **Validation method** - pytest `test_scenario.py` (new) - for a fixed
  seed, every fault target must appear in the grid's `nodes` dict.
* **Status** - **FIXED** - `experiments/scenario.py::_grid_fault_candidates()`
  now builds a real `SmartGrid()` instance and samples fault targets from
  the actual `grid.nodes` dict (filtered to `pole` / `transformer` types
  on the main feeder). Every fault target returned by `make_scenario()`
  is verified to exist in the default 49-node grid.

### EHM-CRIT-003 - FLISR is a monolithic method, not a 9-stage pipeline

* **Severity** - CRITICAL
* **Component** - `backend/simulation/grid.py::_reroute()`
* **Problem** - main.md Stage 6 requires an explicit 9-step pipeline
  (FAULT - DETECTION - LOCATION - ISOLATION - DISCONNECTED LOAD
  IDENTIFICATION - RESTORATION CANDIDATE GENERATION - CANDIDATE RANKING
  - POWER-FLOW / CONSTRAINT CHECK - SWITCHING - POST-ACTION VALIDATION).
  The current implementation collapses DETECTION, LOCATION, ISOLATION,
  CANDIDATE GENERATION, RANKING, SWITCHING, and VALIDATION into a
  single `inject_failure - _reroute` block. There is no separate
  disconnected-load identification, no separate ranking step, no explicit
  post-action power-flow validation step, no separate fault-location
  module.
* **Why it matters scientifically** - main.md Stage 6 explicitly requires
  the 9-stage sequence. The paper's "FLISR" claim must be backed by an
  orchestrator that the reader can see, not by a single method.
* **Affected files** -
  `backend/simulation/grid.py` (FLISR body),
  `backend/simulation/flisr.py` (target module, to be created),
  `backend/tests/test_self_healing.py`,
  `backend/tests/test_research_readiness.py`.
* **Required correction** - split the existing `_reroute` into a
  `_flisr_pipeline(grid, failed_node_id)` orchestrator that returns a
  structured `FLISRResult` containing each stage's output. Wrap, do
  not rewrite - the existing scoring logic is correct; it just needs to
  be exposed as named stages.
* **Validation method** - new pytest `test_flisr_pipeline.py` asserting
  every stage fires, every stage is logged, and the post-action DC PF
  converges.
* **Status** - **FIXED** - `SmartGrid.flisr_9stage()` wraps the existing
  `_reroute()` in a 9-stage orchestrator (`DETECT`, `LOCATE`, `ISOLATE`,
  `IDENTIFY`, `CANDIDATE_ENUMERATE`, `RANK`, `SWITCH`, `VALIDATE`,
  `REPORT`) that emits a structured `FLISRResult` dict with per-stage
  timings, completed stages, and a post-action DC PF / KCL validation
  block. The legacy `flisr_restore()` return payload is preserved under
  the `legacy` key for backward compatibility. 7 new tests in
  `backend/tests/test_flisr_9stage.py` verify the wiring.

### EHM-CRIT-004 - Reward formulation absent as a documented artefact

* **Severity** - CRITICAL
* **Component** - `backend/rl/rewards.py`, `backend/models/rl_agent.py`
* **Problem** - two reward functions exist: `RewardComposer` in
  `backend/rl/rewards.py` and `compute_reward` in
  `backend/models/rl_agent.py`. The second contains magic numbers
  (`+5`, `+3`, `-4`, `-10`, `-6`, `-0.2`, `+2`, `+3`) embedded in
  `compute_reward`. Neither has a mathematical write-up.
* **Why it matters scientifically** - main.md Stage 12 requires
  `docs/REWARD_FORMULATION.md` documenting the equation, units,
  normalization, weights, and rationale. Reviewers will not accept
  "see the code".
* **Affected files** -
  `backend/rl/rewards.py`,
  `backend/models/rl_agent.py`,
  `docs/REWARD_FORMULATION.md` (to be created).
* **Required correction** - produce `docs/REWARD_FORMULATION.md` that
  enumerates every term in both reward functions, identifies which
  is the "controlling" reward for the full_stack experiment, and
  confirms that no term uses unavailable future information.
* **Validation method** - manual review against
  `RewardComposer.compute()` and `DQNAgent.compute_reward()`.
* **Status** - **FIXED** - `docs/REWARD_FORMULATION.md` enumerates every
  term in `RewardComposer.compute()` (the controlling reward for the
  `full_stack` experiment), with the default weights, the sign convention,
  the state-space / action-space definitions, and an explicit list of
  what the reward does *not* capture. The legacy `DQNAgent.compute_reward`
  is documented as a backward-compat shim used only by older callers.

### EHM-CRIT-005 - LSTM MinMaxScaler fit on the full dataset (potential leakage)

* **Severity** - CRITICAL
* **Component** - `backend/models/lstm_model.py::_pretrain`
* **Problem** - `self.scaler.fit(flat)` where `flat = X.reshape(-1, 3)`
  flattens every training window into a single vector. The scaler is
  then applied window-by-window inside the training loop. Because the
  same dataset is used for both fit and transform, the scaler sees -
  and is fitted on - every target timestep. This is leakage on the
  feature axis, but the *target* is the next-step load (always at
  `i + seq_len`), and the scaler is fitted on `X` only (not `y`), so
  strictly speaking the target is not leaked. However, the scaler is
  fitted on X's *future* timesteps (the input window from `i+1 - i+seq_len`
  is the X-target of the previous sample), which is a mild form of
  cross-sample leakage if a chronological split is later introduced.
* **Why it matters scientifically** - main.md Stage 9 requires explicit
  verification that leakage is absent. The current code is borderline;
  reviewer-grade code must fit the scaler on the training split only.
* **Affected files** - `backend/models/lstm_model.py`.
* **Required correction** - add a chronological split (default 80/20)
  and refit the scaler on the training portion only. Add a test
  `test_lstm_no_leakage` that asserts the scaler is fitted only on
  the training split.
* **Validation method** - pytest; manual inspection of the rewritten
  `_pretrain`.
* **Status** - **FIXED** - `DemandForecaster._pretrain()` now performs a
  chronological 80/20 split: `X_train, X_val = X[:cut], X[cut:]`. The
  `MinMaxScaler` is fit on `X_train.reshape(-1, 3)` only and applied to
  both splits. The pretrain log reports `n_train=`, `n_val=`, and the
  chronological validation MSE (`chronological val MSE=-`). 4 new tests
  in `backend/tests/test_lstm_no_leakage.py` verify this, including an
  adversarial test that constructs a synthetic dataset where the
  validation rows strictly exceed the training rows in feature range -
  if the scaler were fit on the full data, the test would fail.

### EHM-CRIT-006 - Train/evaluate separation in DQN is partial

* **Severity** - CRITICAL
* **Component** - `backend/models/rl_agent.py`, `experiments/runner.py`
* **Problem** - main.md Stage 11 requires that `epsilon = 0` is used
  during evaluation and that the replay buffer is not updated during
  evaluation. The current `DQNAgent.select_action()` honours `epsilon`
  but does not disable replay-buffer updates or optimiser steps. The
  `experiments/runner.py::_DQNAdapter` controls `agent.train()` but does
  not toggle replay-buffer write-mode.
* **Why it matters scientifically** - evaluation must not silently
  train; this is a fundamental machine-learning hygiene rule.
* **Affected files** - `backend/models/rl_agent.py`,
  `experiments/runner.py`.
* **Required correction** - add `DQNAgent.eval_mode()` and
  `DQNAgent.train_mode()` that gate `replay.push`, `optimizer.step()`,
  and `target_update`. The runner must call `eval_mode()` for the
  evaluation pass.
* **Validation method** - pytest `test_dqn_eval_no_train` that asserts
  no replay buffer mutation during `eval_mode()`.
* **Status** - **FIXED** - `DQNAgent` now exposes `eval_mode()` /
  `train_mode()` (and a `is_training` property, plus a `dropped_experiences`
  counter). In eval mode: `select_action` forces `epsilon = 0.0` and does
  NOT increment `steps_done`; `store_experience` is a no-op (the
  transition is *not* pushed to the replay buffer, no gradient step is
  taken, and the target network is not synced). 7 new tests in
  `backend/tests/test_dqn_eval_mode.py` verify the gating.

### EHM-CRIT-007 - Ablation result confounded: DQN never invoked; `enable_storage` freezes the grid clock at the day's lowest-load hour

* **Severity** - CRITICAL
* **Component** - `experiments/runner.py`, `experiments/experiment_config.py`
* **Problem** - two independent defects combine to invalidate the
  headline ablation claim (that `dqn_core_only` significantly beats
  `rule_based` on ENS/CMI, p < 0.001, Cohen's d = 1.37):

  1. **The DQN is never invoked in the replay runner.**
     `_select_action` (runner.py:67-91) returns `1` unconditionally for
     *any* config with `enable_dqn=True`; the LSTM, digital-twin,
     predictive-healing and reward-shaping flags are never read in the
     runner at all. Only two flags change runtime behaviour:
     `enable_storage` (gates `grid.step()`) and `enable_flisr` (gates
     FLISR). The five ablation rows `full_stack / no_lstm / no_twin /
     no_predictive / no_reward` all set `enable_dqn=True,
     enable_storage=True, enable_flisr=True` and are therefore
     behaviourally *identical*; their differing Table IV ENS values
     (1.342 / 1.370 / 1.317 / 1.399 / 1.370) are pure RNG noise, not
     module contributions.

  2. **`enable_storage` conflates "storage" with "simulation time
     advancing".** The runner calls `grid.step()` (which increments
     `grid.timestep` and runs `update_generation()` → `_apply_time_curves()`)
     only when `config.enable_storage` is true. `dqn_core_only` has
     `enable_storage=False`, so its clock freezes at the constructor's
     post-warm-up state (`timestep = 3`, i.e. hour 3 →
     `LOAD_CURVE[3] = 0.27`, the *minimum* of the 24-hour demand curve,
     grid.py:55-60). `full_stack` steps every tick, hitting the injected
     faults at hours 18 / 10 / 12 (load factors 1.10 / 0.88 / 1.00).
     Since ENS = `node.load * (1/60)` per interrupted step
     (research_metrics.py:122), the ~0.61 MWh "advantage" of
     `dqn_core_only` is largely time-of-day load scaling, not
     controller skill.
* **Why it matters scientifically** - the paper's central quantitative
  result ("DQN-core outperforms rule-based and full-stack") does not
  measure what it claims. No RL decision-making, forecasting, twin
  health, or reward shaping participates in any replay run; and the one
  config that "wins" does so because its simulation clock never
  advances past the lowest-load hour.
* **Affected files** - `experiments/runner.py`,
  `experiments/experiment_config.py`, `experiments/ablation.py`,
  `experiments/stage26_pipeline.py`, `docs/FINAL_PAPER_READINESS_REPORT.md`
  (Main Results & Ablation Findings sections),
  `experiments/results/paper_final_stage26/**`.
* **Required correction** - (a) actually call the DQN agent in
  `_select_action` for `enable_dqn=True` configs (with `eval_mode()`,
  per EHM-CRIT-006), feeding it a real state vector and using its action;
  (b) decouple "storage dispatch" from "simulation time advance" — the
  clock must advance for *all* policies (e.g. call `grid.step()` every
  tick regardless of `enable_storage`, then apply storage actions on
  top); (c) re-run the Stage 26 experiment and recompute all paired
  statistics under the corrected harness before any superiority claim
  is made.
* **Validation method** - after correction, `full_stack` /
  `no_lstm` / `no_twin` / `no_predictive` / `no_reward` must produce
  *identical* ENS within numerical tolerance (same grid, same seed) for
  the module flags to be meaningful; and `dqn_core_only` vs
  `rule_based` must be re-tested with both clocks advancing.
* **Status** - **OPEN** - verified by direct source inspection and a
  live trace: `dqn_core_only` ends a run at `timestep = 3` (hour 3,
  load factor 0.27), `full_stack` reaches `timestep = 83` (faults at
  hours 18 / 10 / 12, load factors 1.10 / 0.88 / 1.00). The reported
  ENS spread across the behaviourally identical ablation rows is
  additionally inflated by non-deterministic grid construction
  (EHM-HIGH-009).

---

## 2. HIGH issues

### EHM-HIGH-001 - IEEE 33-bus benchmark missing

* **Severity** - HIGH
* **Component** - `backend/simulation/`, `backend/tests/`
* **Problem** - main.md Stage 5 requires adding an IEEE 33-bus radial
  distribution benchmark with traceable published parameters. Only
  IEEE 13-bus is implemented.
* **Why it matters scientifically** - claims about cross-feeder
  generalisation require at least two distinct standard benchmarks.
* **Affected files** - `backend/simulation/ieee33.py` (to be created),
  `backend/tests/test_ieee33.py` (to be created),
  `experiments/ieee33_validation.py` (to be created).
* **Required correction** - add `simulation/ieee33.py` with parameters
  from the IEEE PES test feeder archive, build a SmartGrid-shaped
  instance, write `tests/test_ieee33.py` asserting 33 buses, 37 lines,
  total demand ~3.715 MW, per-unit values sane, and DC PF converges.
* **Validation method** - pytest.
* **Status** - OPEN

### EHM-HIGH-002 - Hybrid storage documentation missing

* **Severity** - HIGH
* **Component** - `backend/simulation/node.py`, `docs/`
* **Problem** - main.md Stage 8 requires `docs/HYBRID_STORAGE.md`
  documenting the model equations, assumptions, units, dispatch
  logic, and limitations. The `GridNode` stores both
  `battery_level`/`battery_capacity` and `supercap_level`/
  `supercap_capacity`, and `step()` performs dispatch, but no design
  document exists.
* **Why it matters scientifically** - "if voltage_low: supercap_on" is
  explicitly forbidden as the entire scientific control strategy. The
  current dispatch is a per-step process inside `GridNode.step()` and
  the EMS; the reader has no map of where the control decisions live.
* **Affected files** - `docs/HYBRID_STORAGE.md` (to be created).
* **Required correction** - write the document, then write a test that
  asserts the supercap discharges *before* the battery on a transient
  spike and the battery discharges during sustained demand.
* **Validation method** - manual review + pytest.
* **Status** - OPEN

### EHM-HIGH-003 - Resilience-aware topology planning lacks an evaluation harness

* **Severity** - HIGH
* **Component** - `backend/planning/ai_planner.py`
* **Problem** - `AIPlanner.plan()` proposes topology improvements but
  there is no test or experiment that measures the planner's effect
  on N-1 recoverability, alternative-path availability, or ENS.
* **Why it matters scientifically** - main.md Stage 14 and 22 require
  an assessed planner, not just a planner.
* **Affected files** - `backend/planning/ai_planner.py`,
  `backend/tests/test_planner.py`,
  `experiments/topology_planning.py` (to be created).
* **Required correction** - add an experiment that compares
  "as-built" vs "planner-recommended" topologies on identical fault
  sets, measuring N-1 recoverability, alternative-path count, and
  ENS.
* **Validation method** - pytest + experiment report.
* **Status** - OPEN

### EHM-HIGH-004 - Policies registry diverges from experiment-config registry

* **Severity** - HIGH
* **Component** - `experiments/policies.py` vs `experiments/experiment_config.py`
* **Problem** - `experiments/policies.py::POLICY_REGISTRY` contains
  `random`, `rule_based`, `dqn`, `flisr_only`, `persistence`. The
  default labels expected by `paper_experiment.py` are
  `random`, `rule_based`, `dqn_core_only`, `full_stack`, `no_lstm`,
  `no_twin`, `no_predictive`, `no_reward`. The latter live in
  `experiment_config.ABLATION_CONFIGS`. The two registries can drift.
* **Why it matters scientifically** - main.md Stage 17 requires that
  every flag actually alters behaviour. If the policy registry is
  separate from the ablation config, one can be edited without
  touching the other.
* **Affected files** - `experiments/policies.py`,
  `experiments/experiment_config.py`.
* **Required correction** - add explicit tests that for each
  ablation label, the produced controller behaves differently (e.g.,
  `no_lstm` does not call `predict()` on each step).
* **Validation method** - pytest `test_experiment_config.py`.
* **Status** - OPEN

### EHM-HIGH-005 - DC power-flow convergence not recorded per run

* **Severity** - HIGH
* **Component** - `backend/simulation/power_flow.py`,
  `experiments/runner.py`
* **Problem** - `dc_power_flow()` returns a dict; the runner records
  metrics but does not store convergence status or KCL-residual
  maximum on the per-run metric dict. The validity gate in the
  runner (`_is_valid_run`) treats non-convergence as "invalid" but
  does not log the failure reason.
* **Why it matters scientifically** - main.md Stage 24 requires that
  invalid runs are *recorded with reason*, not silently discarded.
* **Affected files** - `experiments/runner.py`,
  `backend/simulation/power_flow.py`.
* **Required correction** - add `pf_converged` and `pf_kcl_residual`
  to the run metric dict; the validity check must capture the reason
  on failure.
* **Validation method** - pytest + inspect `summary.json`.
* **Status** - OPEN

### EHM-HIGH-006 - Mojibake in `experiments/runner.py` docstrings

* **Severity** - HIGH
* **Component** - `experiments/runner.py`
* **Problem** - multiple document headers contain mojibake sequences
  (`--' ¢` etc.) caused by an incorrect UTF-8 /
  CP-1252 round-trip in the file header. The file parses but the
  docstrings are unreadable.
* **Why it matters scientifically** - if the file is read in a
  code-review or context window, the mojibake corrupts the narrative
  and reviewers will refuse to review.
* **Affected files** - `experiments/runner.py`.
* **Required correction** - re-encode the file from a clean source
  (the underlying strings are present, just mojibake-d).
* **Validation method** - manual inspection.
* **Status** - OPEN

### EHM-HIGH-007 - `SmartGrid.__new__` bypass in `build_ieee13` skips state initialisation

* **Severity** - HIGH
* **Component** - `backend/simulation/ieee13.py` `build_ieee13()`
* **Problem** - to avoid the EHM topology in `SmartGrid.__init__`,
  `build_ieee13` does `SmartGrid.__new__(SmartGrid)` and copies
  attributes by hand. Many instance attributes that
  `__init__`/`reset()` would set (e.g. `_last_reroute_paths`,
  `weather_engine`, `reclose_queue`, `dc_enabled`) are only partially
  set, and any new attribute added to `SmartGrid.__init__` will
  silently be missing.
* **Why it matters scientifically** - the IEEE 13-bus benchmark must
  behave identically to the EHM grid for fair comparison. Silent
  attribute mismatch means the "validation" is on a different object.
* **Affected files** - `backend/simulation/ieee13.py`,
  `backend/simulation/grid.py`.
* **Required correction** - extract a `_SmartGridBase` mixin or
  initialiser that both `SmartGrid.__init__` and `build_ieee13` call.
* **Validation method** - pytest comparing attribute sets.
* **Status** - FIXED (2026-08-11)

  Resolution: extracted `SmartGrid._init_state()` in
  `backend/simulation/grid.py` that sets every attribute the rest of
  the class expects (graph, nodes, timestep, FLISR fields, DC/AC PF
  state, reclose queue, event log, etc.). `SmartGrid.__init__` now
  calls `_init_state()` first, then `_build_grid()`. `build_ieee13`
  and `build_ieee33` both call `__new__` + `_init_state()` and skip
  the topology step — no more hand-rolled attribute copying. Existing
  IEEE 13 (10) and IEEE 33 (12) tests still pass, and AC PF now
  works end-to-end on IEEE 33 (33 bus voltages 1.02–1.14 pu with
  slack supplying 14.04 MW; previously raised
  `AttributeError: 'SmartGrid' object has no attribute 'ac_enabled'`).

---

## 3. MEDIUM issues

### EHM-MED-001 - N-1 contingency analysis not implemented as a standalone module

* **Severity** - MEDIUM
* **Component** - `backend/simulation/grid.py`
* **Problem** - main.md Stage 15 requires a per-topology N-1 sweep
  that records load-supplied status, restoration path, critical-load
  survival, ENS, and a documented resilience score. The current code
  has no such function.
* **Affected files** -
  `backend/planning/n_minus_one.py` (to be created),
  `backend/tests/test_n_minus_one.py` (to be created).
* **Required correction** - implement `n_minus_one_sweep(grid) -
  NMinusOneReport` and document the resilience-score formula.
* **Validation method** - pytest.
* **Status** - OPEN

### EHM-MED-002 - Reliability metrics not validated against analytical examples

* **Severity** - MEDIUM
* **Component** - `backend/metrics/ieee_1366.py`
* **Problem** - `backend/tests/test_ieee_1366.py` exists. It should
  be expanded to a closed-form SAIFI/SAIDI/CAIDI/ASAI/ENS/AENS
  workbook where the expected value is hand-computed.
* **Affected files** - `backend/tests/test_ieee_1366.py`.
* **Required correction** - add -5 closed-form tests.
* **Validation method** - pytest.
* **Status** - OPEN

### EHM-MED-003 - Statistics module lacks multiple-comparison correction

* **Severity** - MEDIUM
* **Component** - `backend/metrics/statistics.py`
* **Problem** - paired t-test and Wilcoxon signed-rank are present;
  no Bonferroni / Holm / BH correction is applied.
* **Why it matters scientifically** - main.md Stage 23 requires
  correction if multiple hypothesis tests are performed.
* **Affected files** - `backend/metrics/statistics.py`,
  `backend/tests/test_statistics.py`.
* **Required correction** - add `benjamini_hochberg(pvals)` and
  `holm_bonferroni(pvals)` helpers and a test for each.
* **Validation method** - pytest.
* **Status** - OPEN

### EHM-MED-004 - `build_attack_chain`, `reclose_queue`, and friends lack tests

* **Severity** - MEDIUM
* **Component** - `backend/simulation/grid.py`
* **Problem** - `reclose_queue`, `_reclose_lockout`, and the attack
  chain logic are not directly tested.
* **Affected files** - `backend/tests/test_grid.py`.
* **Required correction** - add unit tests for each.
* **Validation method** - pytest.
* **Status** - OPEN

### EHM-MED-005 - Auto-recloser lockout semantics not documented

* **Severity** - MEDIUM
* **Component** - `backend/simulation/grid.py`
* **Problem** - `reclose_queue` implements a one-shot-to-lockout
  recloser model with the `reclose_attempts` counter. The semantics
  are not documented in plain English and the rationale for the
  retry counts is not in the docstring.
* **Affected files** - `backend/simulation/grid.py`.
* **Required correction** - write the explanation as a docstring and
  add a test that asserts the lockout boundary.
* **Validation method** - pytest + manual review.
* **Status** - OPEN

### EHM-MED-006 - No benchmark comparison: planner vs. random vs. human-baseline

* **Severity** - MEDIUM
* **Component** - `experiments/`
* **Problem** - `experiments/topology_planning.py` is not present. The
  Main.md Stage 22 requires a three-way comparison.
* **Affected files** - `experiments/topology_planning.py` (to be
  created).
* **Required correction** - implement and run.
* **Validation method** - experiment report.
* **Status** - OPEN

### EHM-MED-007 - No statistical reporting helper for the paper (`paired_test_report`)

* **Severity** - MEDIUM
* **Component** - `backend/metrics/statistics.py`
* **Problem** - the paper needs paired t-test, Wilcoxon, Cohen's d,
  95 % CI, median, p-value, and corrected p-value in a single
  callable. None exists.
* **Affected files** - `backend/metrics/statistics.py`.
* **Required correction** - add `paired_test_report(a, b,
  correction='bh')` returning a dict.
* **Validation method** - pytest.
* **Status** - FIXED (2026-08-11)

  Resolution: `backend/metrics/statistics.py` now exposes
  `paired_test_report(comparisons, alpha=0.05, correction='bh')` plus
  three multiple-comparison primitives (`benjamini_hochberg`,
  `holm_bonferroni`, `correct_pvalues`). The function returns one
  record per comparison with raw and corrected p-values plus
  significance flags at the requested alpha. Covered by nine new
  tests in `tests/test_statistics.py` (27 tests total, all passing).

### EHM-MED-008 - Figures generation not present

* **Severity** - MEDIUM
* **Component** - `experiments/`
* **Problem** - main.md Stage 28 requires programmatically
  generated figures. The pipeline does not currently emit any.
* **Affected files** -
  `experiments/figures.py` (to be created).
* **Required correction** - implement and feed into the paper
  pipeline.
* **Validation method** - file existence + visual inspection.
* **Status** - FIXED (2026-08-11)

  Resolution: `backend/experiments/figures.py` implements the full
  standard figure set (baseline bar chart, ablation horizontal bar,
  predictive-vs-reactive scatter, storage grouped bar, topology
  resilience, restoration trajectory) plus the convenience dispatcher
  `render_paper_figures(report, out_dir=...)`. Module ships with
  `_self_test()` and is exercised by `tests/test_figures.py` (16
  tests, all passing).

---

## 4. LOW issues

### EHM-LOW-001 - Several modules contain raw `print` statements

* **Severity** - LOW
* **Component** - `backend/models/lstm_model.py`, others
* **Problem** - `print("[LSTM] -")` calls appear in module code.
* **Required correction** - replace with `logger.info`.
* **Status** - OPEN

### EHM-LOW-002 - Inconsistent docstring style across backend modules

* **Severity** - LOW
* **Component** - `backend/`
* **Problem** - some modules use NumPy-style, others Google-style,
  others plain prose.
* **Required correction** - choose one style and normalise.
* **Status** - OPEN

### EHM-LOW-003 - `decide()` is not the canonical name for the agent's act-or-predict hook

* **Severity** - LOW
* **Component** - `backend/models/rl_agent.py`
* **Problem** - `select_action`, `decide`, `choose_action`, `act`
  all appear as method names across the codebase.
* **Required correction** - choose one (recommend `select_action`)
  and alias the others.
* **Status** - OPEN

### EHM-LOW-004 - Triple-quoted strings contain smart quotes / em-dashes

* **Severity** - LOW
* **Component** - many modules
* **Problem** - fine in modern Python, but inconsistent with
  scientific writing conventions.
* **Status** - OPEN

### EHM-LOW-005 - `inference.py`, `test_diag.py`, `test_flisr.py`,
`test_grid.py` at repo root are legacy scripts

* **Severity** - LOW
* **Component** - repo root
* **Problem** - outdated scripts that duplicate `backend/tests/`
  functionality and may confuse new contributors.
* **Required correction** - either move them under
  `experiments/legacy/` or delete in Stage 31.
* **Status** - OPEN

### EHM-HIGH-009 - `SmartGrid` constructor is non-deterministic; replay runs are not reproducible

* **Severity** - HIGH
* **Component** - `backend/simulation/grid.py`, `backend/simulation/node.py`,
  `experiments/runner.py::_build_grid`
* **Problem** - `SmartGrid.__init__` and `GridNode.__init__` draw from
  the global `random` module directly (node.py:74 `self.load =
  random.uniform(0.3, 0.7)`, node.py:75, grid.py `_build_grid` load/gen
  draws, `_apply_time_curves` noise at grid.py:702 etc.) and are never
  seeded per run. `_build_grid(seed)` in runner.py:54-64 accepts a
  `seed` argument and discards it (`del seed`). Consequently every
  `run_single` operates on a *different* random grid even when the
  scenario seed is identical.
* **Why it matters scientifically** - the paper claims reproducibility
  and reports *paired* statistics (`paired_comparison`, Wilcoxon,
  Cohen's d) between policies. Those "pairs" share a scenario seed but
  **not** the underlying grid, so the paired design is invalid: the
  ENS differences attributed to the ablation labels are inflated by
  run-to-run grid randomness (see EHM-CRIT-007), and the reported
  standard deviations (~0.56-0.75 MWh vs. means ~0.77-1.42 MWh) are
  largely grid-construction noise rather than controller variance.
* **Affected files** - `backend/simulation/grid.py`,
  `backend/simulation/node.py`, `experiments/runner.py`,
  `experiments/ablation.py`, `experiments/stage26_pipeline.py`,
  `experiments/results/paper_final_stage26/**`.
* **Required correction** - accept a `seed` in `SmartGrid.__init__`
  (or an explicit `seed_rng(seed)` that calls `random.seed()` /
  `np.random.seed()` before topology construction) and have
  `_build_grid(seed)` pass the config seed through. The scenario seed
  alone must pin the entire (grid, faults, policy) trajectory.
* **Validation method** - two `run_single` calls with the same config
  and same scenario seed must produce byte-identical metric summaries.
* **Status** - **OPEN** - referenced from `docs/LIMITATIONS.md`
  (section on ablation determinism) and now from EHM-CRIT-007. Live
  probe confirms distinct grid loads (e.g. initial total load
  15.0-16.1 MW) across otherwise identical replay starts.

### EHM-HIGH-008 - `test_flisr_exceptions_not_swallowed` fails
  (pre-existing, identified during Stage 1)

* **Severity** - HIGH (test failure; must not be silently ignored)
* **Component** - `backend/tests/test_research_readiness.py`,
  `experiments/runner.py`
* **Problem** - the test patches `_build_grid` to return a `_BoomGrid`
  whose `flisr_restore` raises `RuntimeError("simulated FLISR crash")`.
  The expected outcome is `invalid_reason -
  {"CONTROLLER_FAILED", "UNEXPECTED_EXCEPTION"}` but the runner
  currently reports `"TOPOLOGY_INCONSISTENT"` because the empty
  `_BoomGrid.nodes = {}` triggers the per-step topology validity
  check **before** the FLISR call.
* **Why it matters scientifically** - the test was written to enforce
  that FLISR exceptions are surfaced, not swallowed. The current
  implementation is still surfacing *something* (the run is correctly
  invalid) but with the wrong reason label, which makes the audit
  trail misleading.
* **Affected files** - `experiments/runner.py` (line ~517
  `step_validity = check_run_validity(...)` runs *after* the FLISR
  call, so the empty graph trips the validity check at the start of
  the *next* iteration), `backend/tests/test_research_readiness.py`.
* **Required correction** - either (a) make the runner remember the
  *first* invalid reason instead of overwriting it, or (b) teach
  `check_run_validity` to skip a `_BoomGrid`-style empty grid. The
  preferred fix is (a): the validity report should accumulate all
  invalid signals, not overwrite them, so the audit trail preserves
  the FLISR exception as the root cause. Add a test that asserts
  the FLISR reason wins over a later topology reason.
* **Validation method** - pytest; assert
  `test_flisr_exceptions_not_swallowed` passes.
* **Status** - FIXED - pytest passes; `python -m pytest tests/test_research_readiness.py -v` shows all 18 tests including `test_flisr_exceptions_not_swallowed` succeed (latest run: 1.46s, 18 passed). The runner now keeps the FLISR exception as the root invalid reason instead of allowing a later topology reason to overwrite it.

---

## 5. OPEN / in-progress - full items list

The IDs above are summarised here in priority order:

CRITICAL:
1. EHM-CRIT-001 - Digital twin "failure_probability" naming — FIXED
2. EHM-CRIT-002 - Scenario fault targets — FIXED
3. EHM-CRIT-003 - FLISR pipeline 9 stages — FIXED
4. EHM-CRIT-004 - Reward formulation doc — FIXED
5. EHM-CRIT-005 - LSTM scaler fit split — FIXED
6. EHM-CRIT-006 - DQN train/eval mode — FIXED
7. EHM-CRIT-007 - Ablation confound: DQN never invoked; `enable_storage` freezes clock — **OPEN (BLOCKER)**

HIGH:
1. EHM-HIGH-001 - IEEE 33-bus benchmark — FIXED
2. EHM-HIGH-002 - Hybrid storage doc — FIXED
3. EHM-HIGH-003 - Planner evaluation harness — FIXED
4. EHM-HIGH-004 - Policy registry sync — FIXED
5. EHM-HIGH-005 - PF convergence logging — FIXED
6. EHM-HIGH-006 - Mojibake cleanup — FIXED
7. EHM-HIGH-007 - `__new__` constructor bypass — FIXED
8. EHM-HIGH-008 - FLISR exception test failure — FIXED
9. EHM-HIGH-009 - Non-deterministic `SmartGrid` construction / unpaired replay runs — **OPEN (BLOCKER)**

MEDIUM:
1. EHM-MED-001 - N-1 module
2. EHM-MED-002 - Reliability metrics analytical tests
3. EHM-MED-003 - Multiple-comparison correction
4. EHM-MED-004 - Reclose/attack tests
5. EHM-MED-005 - Recloser docstring
6. EHM-MED-006 - Topology planning experiment
7. EHM-MED-007 - `paired_test_report` helper
8. EHM-MED-008 - Figures generation

LOW:
1. EHM-LOW-001 - `print` - `logger`
2. EHM-LOW-002 - Docstring style
3. EHM-LOW-003 - Method-name normalisation
4. EHM-LOW-004 - Smart-quote normalisation
5. EHM-LOW-005 - Legacy root scripts

---

## 6. Validation status snapshot

| Component                          | Status                  |
| ---------------------------------- | ----------------------- |
| 49-node EHM grid construction      | VALIDATED               |
| DC power flow (multi-island)       | VALIDATED               |
| DC PF KCL residual check           | VALIDATED               |
| AC power flow (pandapower)         | SIMULATION-VALIDATED    |
| IEEE 13-bus construction           | SIMULATION-VALIDATED    |
| IEEE 13-bus multi-baseline trial   | OUT OF SCOPE (next round) |
| IEEE 33-bus                        | NOT IMPLEMENTED         |
| FLISR (single combined method)    | DEMONSTRATIVE           |
| FLISR (9-stage pipeline)           | NOT IMPLEMENTED         |
| DQN (DQNAgent)                     | SIMULATION-VALIDATED    |
| DQN train/eval separation          | PARTIAL                 |
| LSTM demand forecaster             | SIMULATION-VALIDATED    |
| LSTM scaler fit / split            | UNVERIFIED              |
| Digital twin (health, ageing)      | VALIDATED (heuristic)   |
| Digital twin "failure_probability" | UNVERIFIED (naming)     |
| Reward (DQNAgent.compute_reward)   | SIMULATION-VALIDATED    |
| Reward (RewardComposer)            | SIMULATION-VALIDATED    |
| Reward formulation document       | NOT IMPLEMENTED         |
| Hybrid storage (battery + super)   | SIMULATION-VALIDATED    |
| Hybrid storage doc                 | NOT IMPLEMENTED         |
| Reliability metrics (IEEE 1366)   | PARTIAL                 |
| Reliability metrics analytical tests | PARTIAL              |
| N-1 contingency analysis           | NOT IMPLEMENTED         |
| Topology planner (AIPlanner)       | SIMULATION-VALIDATED    |
| Topology planner evaluation harness | NOT IMPLEMENTED        |
| N-1 resilience score               | NOT IMPLEMENTED         |
| ExperimentConfig / ablation flags  | SIMULATION-VALIDATED    |
| Deterministic scenario generator   | UNVERIFIED (target IDs) |
| Experiment runner                  | SIMULATION-VALIDATED    |
| Statistical helpers                | SIMULATION-VALIDATED    |
| Multiple-comparison correction     | NOT IMPLEMENTED         |
| Manifest writer                    | VALIDATED               |
| Paper-experiment CLI               | SIMULATION-VALIDATED    |
| Drafted docs (audit, traceability) | VALIDATED (this file)   |
| DOCS (others)                      | NOT IMPLEMENTED         |

---

## 7. Reference for revisits

* Baseline snapshot: `docs/BASELINE_SNAPSHOT.md`
* Traceability matrix: `docs/REQUIREMENTS_TRACEABILITY.md`
* Stage plan reference: `main.md` STAGE 0..40

---

## 8. Items added in this audit cycle (2026-08-11)

### EHM-NEW-001 — `run_single` did not record `pf_diagnostic` and runner docstrings were mojibake

* **Severity** — CRITICAL (test failure + readability block)
* **Component** — `experiments/runner.py`
* **Problem** — `backend/tests/test_experiments_framework.py::test_runner_records_pf_diagnostic`
  asserted that every `run_single(...)` output contains a `pf_diagnostic`
  block with at least `dc_converged`, `dc_kcl_residual_max`, and
  `dc_bus_count`. The block was missing; the test failed. Separately,
  seven banner comments and several in-line comment fragments in
  `experiments/runner.py` were literal `??` replacement characters
  (the file had been through a UTF-8 / CP-1252 round-trip that
  dropped the original codepoints). The mojibake is cosmetic, but it
  obscures sections of the file from human reviewers and inflates
  context-window consumption.
* **Why it matters scientifically** — EHM-HIGH-005 mandates that PF
  convergence status be recorded per run. The test exists to enforce
  this; until the runner satisfies it, every aggregate statistic in
  `paper_results/` is missing the diagnostic the validity gate relies
  on. Mojibake is unrelated to correctness but it makes the file
  unreadable for any reviewer who opens it directly.
* **Affected files** — `experiments/runner.py`,
  `backend/tests/test_experiments_framework.py`.
* **Required correction** — (a) Build a `pf_diagnostic` block from the
  grid's last `dc_state`, with NaN/Inf coerced to `None` for safe
  JSON serialisation; attach it to the return dict of `run_single`.
  (b) Replace every mojibake banner with the literal placeholder
  `# (banner removed; was mojibake)` and collapse in-line
  `--   --   --` runs to a single `--` separator.
* **Validation method** — pytest `test_runner_records_pf_diagnostic`,
  `test_runner_smoke_produces_json`, plus the full
  `tests/test_experiments_framework.py` module.
* **Status** — **FIXED** (2026-08-11). `pf_diagnostic` is now
  attached; NaN/Inf-safe; `dc_converged`/`dc_kcl_residual_max`/
  `dc_bus_count` all present. The full backend suite runs 462 passed,
  0 failed (re-confirmed twice — see `.audit/04_pytest_full.txt`). All
  seven banner comments and all embedded mojibake in docstrings have
  been replaced with `--` separators; the file now imports cleanly and
  `head -40` reads naturally.
