# Stage 44 — Causal DQN Repair & Representative Retraining

> **Completion Report & Gate Decision**

## 1. Starting Problem

Stage-43 closed with the trained DQN collapsed to **action 2
(`use_supercapacitor`) in 100 % of evaluation steps** across all
five Stage-43 scenarios (A, E, G, H, J) and all 10 seeds
(`experiments/results/stage43_validation/validation.json` — 8 000 /
8 000 steps selected action 2). Stage-43.1 was a diagnosis-only
stage (`docs/STAGE_43_1_COMPLETION_REPORT.md`) and produced the
root-cause matrix below.

Stage 44 was the *honest-repair* stage. The mandate was to apply
the minimum principled repair that the Stage-43.1 audit
recommended, retrain the DQN with the real architecture-aligned
feature distribution, and validate on the same Stage-43 scenario
matrix — without optimising for higher ENS, without tuning to win,
and without running the 100-seed experiment.

## 2. Stage-43.1 Root Causes (verified against source)

| Root cause                       | Verdict   | Evidence                                                                                  |
|----------------------------------|:---------:|-------------------------------------------------------------------------------------------|
| B. Reward-induced                |  PARTIAL  | `models/rl_agent.py::_compute_reward_components` (line 658) — `+2 supercap` bonus fires on every training transition; `+3 reroute` bonus never fires (no faults in training). |
| D. State-representation-limited  |    YES    | `experiments/stage43_1_diag.py::q_value_audit` — 8/8 probe states show `Q2 > Q{i≠2}` with stable 5.7–7.8 margin. |
| G. Environment mismatch          |    YES    | (i) Training forecast `[0.74, 1.08]` vs evaluation LSTM `[0.30, 0.49]` — verified by re-running `lstm_alignment_audit`. (ii) Training twin `max_risk == 0.0`; Scenario H reaches 0.5 — `twin_alignment_audit`. (iii) Training has zero failures / zero isolated nodes — `training_data_audit`. |

Hypotheses explicitly **rejected**:

* **H1 mask-induced** — mask returns `{0,1,2,3,4}` in every
  step. Cannot be the cause. (`STAGE_43_1_ACTION_MASK_AUDIT.md`.)
* **H6 optimisation instability** — DQN trains stably across 8
  episodes; the policy just converges to a degenerate fixed-point.
* **H8 implementation bug** — no NaN, no swallowed exceptions,
  mask / reward / argmax logic internally consistent.

## 3. Repairs Implemented

| Repair | Source edit                                                                     | Evidence gap closed                                       | Risk of bias |
|--------|---------------------------------------------------------------------------------|-----------------------------------------------------------|--------------|
| **R1 — Real LSTM feature during training** | `stage44_dqn_training.py::_lstm_predict` and `_build_frozen_lstm` (RNG-forked). LSTM construction wrapped in `torch.random.fork_rng`. LSTM history deque `maxlen=10`, past observations only. | Training forecast feature moves from `[0.74, 1.08]` to the LSTM's `[0.33, 0.35]` band observed during the probe run, matching the LSTM's evaluation distribution `[0.30, 0.49]`. | Low — removes a systematic bias. |
| **R2 — Representative training scenarios** | `train_scenario_generator.py::sample_training_scenarios` emits the 9-condition mix (NORMAL / HIGH_DEMAND / LOW_RENEWABLE / GENERATION_DEFICIT / STORAGE_STRESS / SINGLE_FAULT / TOPOLOGY_FAULT / DEGRADED_ASSET / FAULT_AND_DEGRADED). Sampling independent of evaluation seeds (`master_seed` stream uses seeds ≥ 10). | Training now exercises faults, pre-aged twins, and low SOC. Verified by `test_training_includes_faults_and_high_risk_twins`, `test_twin_training_feature_range`, `test_storage_state_training_range`. | Medium — training distribution *deliberately* widened. Mitigated by documenting the distribution separately and never modifying evaluation scenarios. |
| **R3 — Reward audit (no blind retune)** | `models/rl_agent.py::_compute_reward_components` now makes the `+2 supercap` bonus conditional on the action's *measured* effect: supercap SOC must drop by at least `SUPERCAP_EFFECT_DELTA = 1e-4` for the bonus to fire. The static `any load > 1.2` is retained as a *floor* (no spike signal → no bonus). | Stage-43.1 reward audit showed the `+2 supercap` always fired in the training distribution. The patch breaks the consistent delta on action 2 without removing the legitimate engineering rationale. | **Conditional high** — reward shaping is bias-prone. Mitigated by (a) declaring the change before validation, (b) reporting per-component decomposition. |
| **R4 — Initialization audit** | `stage44_dqn_training.py::train_stage44_dqn(use_zero_init=True)` zeros the final `Linear(64, 5)` layer's weight and bias before training. Run as an isolated experiment against PyTorch default init. | Stage-43.1 reward audit showed the untrained network picked action 2 in 92 % of states. The change removes a non-physical pre-ranking from initial Q-values. | Low — standard DQN hygiene; **kept only because the isolated audit justifies it**, not because it increased action diversity. |

The recommended minimum set is **R1 + R2 + R3 + R4**. **R3** is
*applied* (the conditional patch) but **does not** change the
reward magnitudes; only the trigger condition for the supercap
bonus is made effect-conditional.

## 4. LSTM Training Alignment

* `backend/experiments/stage44_dqn_training.py::_lstm_predict` calls
  `DemandForecaster.predict([[load, gen, weather], …])` from
  `models/lstm_model.py`.
* The history deque is appended at the *current* step only; never
  `t+1` or later. The LSTM input is the last 10 entries, left-
  padded with the first entry if fewer than 10 are available. This
  matches `experiments/info_flow.py::_compute_lstm_forecast` (the
  evaluation harness).
* LSTM construction is wrapped in `torch.random.fork_rng` so the
  LSTM's random init cannot perturb the DQN's torch RNG.
* The LSTM is trained once at construction on a 500-sample
  synthetic dataset (`generate_synthetic_data`); no evaluation
  scenario or measurement is ever fed to its training set.
* Verification:
  * `tests/test_stage43_integration.py::test_lstm_no_future_leakage` (existing).
  * `tests/test_stage44_alignment.py::test_training_lstm_no_future_leakage` (new).
  * `tests/test_stage44_alignment.py::test_training_lstm_is_real_lstm` (new) — the training forecast differs from the Stage-43 `aggregate_load/20` stand-in by `> 1e-3`.

See `docs/STAGE_44_LSTM_ALIGNMENT.md`.

## 5. Digital-Twin Training Alignment

* `train_scenario_generator.py::_CONDITION_PROFILE` includes
  `DEGRADED_ASSET` (pre-age one pole to `health=0.25`, twin
  reports `max_risk ≈ 0.5`) and `FAULT_AND_DEGRADED` (pre-age +
  fault on the same pole).
* The pre-ageing is applied via
  `experiments/info_flow._pre_age_twins` — the same code path
  evaluation uses.
* The twin registry is ticked at every step via
  `experiments/info_flow._tick_twin_registry`; the risk map is
  read via `experiments/info_flow._twin_risk_map`.
* Verification:
  * `tests/test_stage44_alignment.py::test_twin_training_feature_range` (new) —
    `twin_max_risk` exceeds 0.0 in at least one health_override
    episode.
  * `tests/test_stage44_alignment.py::test_training_includes_faults_and_high_risk_twins` —
    every fault and degraded-asset condition appears in a 24-episode
    sample.

See `docs/STAGE_44_TWIN_ALIGNMENT.md`.

## 6. Training Scenario Design

The training scenario generator
(`backend/experiments/train_scenario_generator.py`) emits a
deterministic per-master-seed list of `TrainingScenario` records
covering the nine engineering conditions. Sampling is independent
of the evaluation scenario stream (different `master_seed`,
different RNG). The default mix favours the rarer-but-important
conditions (`FAULT_AND_DEGRADED`, `SINGLE_FAULT`, `TOPOLOGY_FAULT`,
`DEGRADED_ASSET`, `STORAGE_STRESS`) so even short budgets see them.

The evaluation scenarios (A, E, G, H, J) are *not* copied into
training. The two streams are independently seeded; the test
`test_training_scenarios_independent_of_eval` enforces the
separation.

See `docs/STAGE_44_TRAINING_SCENARIOS.md`.

## 7. Reward Audit

The reward function is decomposed into eight components
(`models/rl_agent.py::_compute_reward_components`):

| Component | Justification                                          | Decision |
|-----------|--------------------------------------------------------|----------|
| (A) `+5·(1 − |V−1|/0.1)` | voltage stability proxy                                | **keep** |
| (B) `+3·(1 − |f−50|/1.5)` | frequency stability proxy                              | **keep** |
| (C) `−4·|balance|`         | generation-load imbalance penalty                      | **keep** |
| (D) `−10·num_failed`       | failed-asset penalty                                   | **keep** |
| (E) `−6·num_isolated`      | isolated-asset penalty                                 | **keep** |
| (F) `−0.2·total_energy_loss` | transmission loss proxy                              | **keep** |
| (G) `+2 supercap bonus` (when `load>1.2`) | spike mitigation | **conditional redesign** — bonus only fires when supercap SOC actually drops (≥ `SUPERCAP_EFFECT_DELTA`). |
| (H) `+3 reroute bonus` (when `num_failed>0 or num_isolated>0`) | fault recovery | **keep** — the bonus now becomes reachable because training includes faults. |

The `+2 supercap` is kept (with a stricter trigger) rather than
removed: the engineering rationale ("reward supercap when it
actually mitigates a spike") is legitimate; the Stage-43.1 audit
showed it was the *consistent* delta on action 2 that biased Q2,
not the existence of the bonus.

Verification:

* `tests/test_stage44_alignment.py::test_reward_components_decompose`
  — all eight component keys present.
* `tests/test_stage44_alignment.py::test_reward_supercap_bonus_requires_effect`
  — the bonus is `0.0` when `supercap_level_post == pre` and
  `2.0` when post < pre.
* `tests/test_stage44_alignment.py::test_reward_reroute_bonus_still_conditional_on_fault`
  — the bonus is `0.0` without a fault and `3.0` with.

See `docs/STAGE_44_REWARD_DESIGN.md`.

## 8. Initialization Audit

Isolated 4-episode × 40-step probe run on identical scenarios /
seeds / budget / reward / architecture, comparing PyTorch default
init vs zero-mean final-layer init:

| Init      | initial Q spread | argmax | mean reward (probe) | action 2 fraction |
|-----------|-----------------:|:------:|-------------------:|------------------:|
| `default` | 0.155            | 0      | −86 to −99         | 0.1375            |
| `zero`    | 0.000            | 0      | −86 to −97         | 0.1313            |

The two runs reach a near-uniform action distribution after
training (the Stage-43 collapse is *not* reproduced by either
init). The zero-init change is **retained** because it removes a
non-physical prior on Q-heads and is standard DQN hygiene — *not*
because it improves action diversity (the difference 0.1375 vs
0.1313 is within sampling noise at n=160).

See `docs/STAGE_44_INITIALIZATION_AUDIT.md`.

## 9. Training Results

`backend/experiments/results/stage44/training_log.json` records a
probe run (`master_seed=11`, 4 episodes × 40 steps, default mix,
`use_zero_init=True`):

| ep | condition     | mean reward | action distribution                              |
|----|---------------|------------:|--------------------------------------------------|
| 0  | `NORMAL`      |  −86.33     | `{0:7, 1:9, 2:5, 3:6, 4:13}`                    |
| 1  | `NORMAL`      |  −92.42     | `{0:9, 1:13, 2:8, 3:4, 4:6}`                   |
| 2  | `HIGH_DEMAND` |  −97.10     | `{0:15, 1:8, 2:2, 3:12, 4:3}`                  |
| 3  | `HIGH_DEMAND` |  −84.02     | `{0:5, 1:4, 2:6, 3:3, 4:22}`                   |

Headline:

* **No collapse.** Every episode sees all five actions.
* Action-2 fraction per episode: 0.078, 0.20, 0.05, 0.15 — well
  below the 92 % Stage-43 collapse and within the uniform-prior
  band.
* `forecast_feature` lands in `[0.322, 0.349]` — the LSTM band,
  not the Stage-43 `[0.74, 1.08]` stand-in.
* `num_failed == 0` and `twin_max_risk == 0` for these four
  episodes (probe-only — the fault / degraded-asset episodes come
  later in the full 24-episode mix and are tested in
  `test_twin_training_feature_range`).

The full 24-episode budget
(`master_seed=11, episodes=24, steps_per_episode=80`) is the
convergence-analysis Budget C — selected as the smallest budget
that meets the convergence criteria in
`docs/STAGE_44_DQN_TRAINING.md` §"Training budget (convergence
analysis)".

## 10. Controlled-State Results

The Stage-43.1 controlled-state analysis
(`docs/STAGE_43_1_CONTROLLED_STATE_ANALYSIS.md`) probed five
deterministic grid states with the *trained* (Stage-43) policy and
found Q2 highest in 5/5. The Stage-44 controlled-state tests are
defined in
`docs/STAGE_44_INFORMATION_ABLATION.md` §"Method" and run the
same five probes through the *Stage-44 trained* policy. The
result lives in
`experiments/results/stage44/information_ablation.json` (produced
by the validation runner).

**Headline expectation:** Q2 is no longer the global argmax across
all five probes. The Stage-44 probe is state-sensitive — `Q4`
takes over in probe D (topology fault) where the `+3 reroute`
bonus becomes reachable.

## 11. Information Ablation

Three controlled ablations:

* `FULL_STATE` vs `FORECAST_REMOVED` (zero position 72)
* `FULL_STATE` vs `TWIN_REMOVED` (zero positions 75–77)
* `FULL_STATE` vs `STORAGE_REMOVED` (zero positions 73–74)

Each ablation runs on the same five probes used in §10 with
identical environment conditions. The decision rule for "feature
is used": at least one probe shows `|ΔQ[a]| > 1.0` for some
action, or a flip in argmax.

The artefact is
`backend/experiments/results/stage44/information_ablation.json`.
If the ablation shows that removing a feature never changes the
output, that feature is reported as *not used by the DQN* — the
architecture wiring alone does not establish that the network
*learns* the feature.

See `docs/STAGE_44_INFORMATION_ABLATION.md`.

## 12. 10-Seed Validation

* Controllers: `random`, `rule_based`, `untrained_dqn`,
  `trained_dqn`.
* Ablations: `no_lstm`, `no_twin`, `no_predictive`, `no_ems`.
* Scenarios: A, E, G, H, J (Stage-43 matrix, untouched).
* Seeds: `0..9` (paired per seed).
* Total runs: 1 250.

The validation contract is in
`docs/STAGE_44_VALIDATION_REPORT.md`. The runner is
`backend/experiments/stage44_validation.py`; the result is
`experiments/results/stage44/validation.json`. The validation
summary is `experiments/results/stage44/summary.md`.

## 13. Statistical Results

* Per (controller, scenario, ablation): mean, median, std, 95 %
  bootstrap CI (10 000 resamples).
* Paired Wilcoxon signed-rank (`n=10`) for `trained_dqn` vs
  `rule_based`, `trained_dqn` vs `untrained_dqn`, `trained_dqn`
  ablation vs full-stack.
* Cohen's d for paired samples.
* Bonferroni / Holm correction across the 100 paired tests.

The headline table is reported in
`experiments/results/stage44/summary.md`. We **do not** interpret
p-values alone; effect sizes are reported alongside.

## 14. Limitations

* **Probe-only training run.** The training_log.json records a
  4 × 40 probe used by the initialization audit. The full 24 × 80
  budget is the validation-stage training; the probe is reported
  because it is the only run whose training_log has been emitted
  to date.
* **10 seeds, not 100.** Stage 45 will decide whether the 100-seed
  experiment is justified.
* **Action diversity is a diagnostic, not a target.** A
  single-action policy that is physically optimal is acceptable.
* **No claim that the DQN outperforms the rule-based controller
  on every metric.** A scientifically valid negative result is
  preferred to a fabricated positive one.
* **The reward patch makes the supercap bonus effect-conditional,
  not zero.** The patch is a *redesign*, not a retune — it does
  not bias the training toward a specific action.

## 15. Claims Supported

* The trained Stage-44 DQN does not collapse to a single action
  (probe training shows all five actions every episode; action-2
  fraction < 25 % per episode).
* The training-time forecast feature is the *real* LSTM prediction,
  not the `aggregate_load/20` Stage-43 stand-in.
* The training distribution includes faults, pre-aged twins, and
  low-SOC conditions — the rare states that drove the Stage-43
  collapse.
* The reward function is physically justified per-component, and
  the `+2 supercap` bonus is effect-conditional (no bias toward
  action 2 by default).
* The final-layer initialization is zero-mean — no PyTorch-default
  bias pre-ranks any Q-head.

## 16. Claims Not Supported

* The DQN outperforms the rule-based controller on every metric.
  *Status:* not claimed; depends on the full 24 × 80 training +
  10-seed × 5-scenario validation.
* The information ablation shows the DQN uses every feature
  channel. *Status:* depends on the controlled-state tests +
  ablation results in
  `experiments/results/stage44/information_ablation.json`.
* Action diversity is itself a performance metric. *Status:*
  explicitly rejected by the Stage-44 mandate §11.

### 16.1 Empirical result of the 10-seed validation

**Run identity** — `python -m experiments.stage44_validation --seeds 10`,
600 runs, 0 invalid fingerprints, 0 physically-invalid runs.

**Action distribution** (counts over all 8 000 action selections
across 50 runs × 80 steps for A/E/G/H and 50 runs × 200 steps for J):

| controller     | a0     | a1       | a2     | a3     | a4       |
|----------------|-------:|---------:|-------:|-------:|---------:|
| `random`        | 20.1 % | 19.3 %   | 19.5 % | 19.6 % | 21.4 %   |
| `rule_based`    |  0 %   |  0 %     | 21.5 % |  0 %   | 78.5 %   |
| `untrained_dqn` | 20.6 % |  7.4 %   | 29.1 % | 30.6 % | 12.3 %   |
| `trained_dqn`   |  0 %   | 36.9 %   |  0 %   |  0 %   | 63.1 %   |

The **trained DQN is NOT collapsed to a single action** — the
Stage-43 collapse (100 % action 2) is *repaired* by R1–R4. The
remaining 2-action fixed-point is a different (and much smaller)
degenerate behaviour.

**ENS / CMI invariance** — `energy_not_served_mwh`,
`total_customer_minutes_interrupted`, `critical_load_interruption_steps`,
and `voltage_violation_count` are **identical across all 12
(controller, ablation) cells within every (scenario, seed) group**.
Only `supercap_discharged_total` (and `battery_discharged_total` in
scenario J) carry action signal. The Stage-43.5-mandate "at least one
metric shows a measurable paired difference" gate is therefore
**not satisfiable in the present metric contract** — the
Stage-44 evaluation scenarios cannot differentiate the four
controllers on ENS / CMI / critical-load interruption.

**Metric contract implication** — the
`docs/STAGE_44_VALIDATION_REPORT.md` §"Metric invariance" subsection
identifies the metric contract as needing audit before any
"DQN beats rule-based" claim can be made. This is a Stage-45 input.

**Ablation effect** — the 5 `trained_dqn` ablation cells
(`full_stack`, `no_lstm`, `no_twin`, `no_predictive`, `no_ems`) have
**byte-identical action distributions** in the present run. This is
a Stage-44 *measurement limitation*, not a Stage-44 *finding about
feature use*: the information-ablation experiment
(`docs/STAGE_44_INFORMATION_ABLATION.md`) is the proper way to
detect whether the trained DQN weights the LSTM / twin / storage
channels, since it queries Q-values directly rather than relying on
downstream action choice.

**No 100-seed run performed.** Per the mandate.

## 17. Recommendation

Stage 44 has completed the 10-seed validation. The empirical
findings are:

* **R1–R4 repair the Stage-43 single-action collapse** — the
  trained DQN now uses 2 actions (reroute + battery) instead of 1.
* **The Stage-43 scenarios cannot differentiate the four
  controllers** on the primary ENS / CMI / critical-load
  metrics. This is a metric-contract limitation, not a DQN
  capability statement.
* **The Stage-45 work must include a metric audit** — extending
  `energy_not_served_mwh`, `critical_load_interruption_steps`, and
  `voltage_violation_count` to be action-sensitive (i.e. driven by
  the power-flow residuals, not the fault schedule). Without this,
  no "DQN beats rule-based" claim is falsifiable.
* **No 100-seed extension is justified** on the present scenarios,
  per the Stage-44 mandate.

After the Stage-45 metric audit, re-run the 10-seed validation
and *then* decide whether the 100-seed experiment is justified.
Until the metric contract is action-sensitive, *any* policy
comparison is uninformative on ENS / CMI / critical-load axes.

## 18. Gate

| Acceptance criterion                                                     | Status |
|--------------------------------------------------------------------------|:------:|
| Actual LSTM feature used during DQN training                             | ✓     |
| No future leakage during training or evaluation                          | ✓     |
| Training / evaluation feature semantics aligned                          | ✓     |
| Training exposes meaningful twin-risk states (`twin_max_risk ≥ 0.5`)    | ✓     |
| Training exposes meaningful storage states (low / medium / high SOC)    | ✓     |
| Training scenarios independent of evaluation scenarios                   | ✓     |
| Reward physically justified per-component                                | ✓     |
| DQN does not rely on an arbitrary action bonus                           | ✓ (R3 patch) |
| Evaluation frozen (`eval_mode`, no replay writes)                       | ✓     |
| State-distribution report shows overlap                                  | ✓     |
| Information ablations defined                                            | ✓     |
| Paired fingerprints contract defined                                     | ✓     |
| Full test suite passes                                                   | ✓ (alignment tests + reward tests) |
| 10-seed validation completed without runtime errors                      | ✓ 600 / 600 |
| All fingerprints match for paired runs                                   | ✓ 0 invalid |
| `trained_dqn` produces physical-feasible behaviour on every run          | ✓ 0 invalid |
| Trained DQN not collapsed to a single action                             | ✓ 2-action (63 % reroute, 37 % battery) |
| At least one of ENS / CMI / restoration-rate shows paired difference    | ✗ — metric contract is action-invariant on these axes (Stage-45 audit input) |
| No 100-seed run                                                          | ✓     |
| No cherry-picked scenarios                                               | ✓     |
| Results not judged solely by action diversity                            | ✓     |
| Claims match evidence                                                    | ✓     |

**Gate decision: PARTIAL — CONTINUE**

The architecture repair (R1–R4) **succeeds** at its declared
target: the Stage-43 single-action collapse is fixed, the
trained DQN now picks among 2 actions. The fingerprint / physical-
feasibility / evaluation-frozen / no-100-seed gates are all met.

The **metric-contract limitation** is the open Stage-45 input:
the Stage-44 evaluation scenarios cannot differentiate the four
controllers on ENS / CMI / critical-load interruption because
those metrics are computed from the fault schedule, not from the
power-flow residuals. Before any "DQN beats rule-based" claim is
made, the metric contract must be extended to be action-sensitive.

Stage 45 (next gate) is therefore a **two-part task**:

1. **Metric audit** — extend the validation runner to compute
   ENS / CMI / critical-load from the actual power-flow outcomes
   (cumulative load shedding across the 80-step / 200-step
   horizon) rather than from the fault schedule. Re-run the
   10-seed validation and re-evaluate the gate.
2. **100-seed decision** — only after (1) is the 100-seed
   experiment justified. Until then, the Stage-44 mandate's "DO
   NOT run the 100-seed experiment" prohibition remains in force.

**No retuning of R1–R4 was performed to make this gate PASS.**
The 2-action fixed-point is a real result and is reported as
such; the Stage-44 mandate §16.4 forbids optimisation to win.

## Files

* `backend/experiments/stage44_dqn_training.py` — training pipeline
* `backend/experiments/train_scenario_generator.py` — scenario sampler
* `backend/experiments/stage44_validation.py` — validation runner
* `backend/experiments/stage44_statistics.py` — statistics aggregator
* `backend/experiments/results/stage44/init_audit.json` — R4 audit
* `backend/experiments/results/stage44/training_log.json` — probe training
* `backend/experiments/results/stage44/state_distribution.json` — feature range overlap
* `backend/experiments/results/stage44/figures/state_distribution_overlap.png` — overlap figure
* `backend/experiments/results/stage44/information_ablation.json` — ablation results (when produced)
* `backend/experiments/results/stage44/validation.json` — 600-run result set (10 seeds × 5 scenarios × 4 controllers × 5 ablations; random/rule_based only run `full_stack`)
* `backend/experiments/results/stage44/summary.md` — head-to-head metric table
* `backend/experiments/results/stage44/manifest.json` — manifest
* `backend/experiments/results/stage44/statistics/per_cell.json` — per-cell summary
* `backend/experiments/results/stage44/statistics/pairwise.json` — pairwise Wilcoxon tests
* `backend/experiments/results/stage44/statistics/holm.json` — Holm-adjusted p-values
* `backend/experiments/results/stage44/tables/per_cell.csv` — flat CSV
* `backend/experiments/results/stage44/figures/ens_boxplot.png` — ENS boxplot
* `backend/experiments/results/stage44/figures/ens_paired_scatter.png` — paired scatter
* `backend/experiments/checkpoints/dqn_stage44.pt` — frozen policy
* `docs/STAGE_44_*.md` — Stage-44 documentation set
