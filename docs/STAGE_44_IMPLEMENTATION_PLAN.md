# Stage 44 — Implementation Plan

> **Causal DQN Repair & Representative Retraining**

## 1. Confirmed Stage-43.1 Root Causes

The Stage-43.1 audit matrix (`docs/STAGE_43_1_COMPLETION_REPORT.md`)
classified the trained-DQN collapse as **MIXED (I)**. We re-verified
each root cause against the source code before accepting it:

| Root cause                              | Verdict | Verification evidence                                                      |
|-----------------------------------------|:-------:|----------------------------------------------------------------------------|
| B. Reward-induced                       |  PARTIAL | `models/rl_agent.py::compute_reward` (line 632) emits a consistent `+2.0` on `use_supercapacitor` whenever `load > 1.2` is present anywhere in the grid (Stage-43.1 reward audit). The `+3.0` reroute bonus never fires because training has `num_failed=num_isolated=0` (verified by re-running the training loop in eval mode). |
| D. State-representation-limited         |    YES   | 8/8 probe states in `stage43_1_diag.py::q_value_audit` show `Q2 > Q{i≠2}` with a stable 5.7–7.8 margin. The network *reads* the state (Q-values move), but the rank order never flips. |
| G. Environment mismatch (training ↔ eval) |    YES   | (1) Training forecast range `[0.74, 1.08]` vs LSTM eval range `[0.30, 0.49]` — verified by re-running `lstm_alignment_audit`. (2) Training twin features are uniformly `0.0`; Scenario H reaches `0.50` — verified in `twin_alignment_audit`. (3) Training has zero failures and zero isolated nodes (training-data audit). |

Hypotheses explicitly **rejected**:
* **H1 mask-induced** — mask always returns `{0,1,2,3,4}` on a healthy
  grid (Stage-43.1 action-mask audit). Cannot be the cause.
* **H6 optimisation instability** — `dqn_training.py` trains stably
  across 8 episodes; the policy just converges to a degenerate
  fixed-point (training-data audit).
* **H8 implementation bug** — no NaN, no swallowed exceptions, the
  mask / reward / argmax logic is internally consistent.

The collapse is real, diagnosed, and **not** caused by the network
failing to learn — it is caused by training never exposing the
network to the states/rewards it would need to learn anything other
than "always `use_supercapacitor`".

## 2. Proposed Repairs

Stage 44 applies the **minimal principled repair** that the
Stage-43.1 audit recommended. Each repair is annotated with its
scientific justification, the evidence gap it closes, and its
expected risk of bias.

| Repair | What | Evidence gap closed | Risk of bias |
|--------|------|--------------------|--------------|
| **R1 — Real LSTM feature during training** | Replace the `aggregate_load/20` stand-in (range 0.74–1.08) with the actual LSTM prediction (range 0.30–0.49) during the training loop. | LSTM training-vs-evaluation distribution mismatch (`STAGE_43_1_LSTM_TRAINING_ALIGNMENT.md`). | Low. *Removes* a systematic bias. |
| **R2 — Representative training scenarios** | Build a separate `train_scenario_generator.py` that injects controlled mixtures of NORMAL, HIGH DEMAND, LOW RENEWABLE, GENERATION DEFICIT, STORAGE STRESS, SINGLE FAULT, TOPOLOGY FAULT, DEGRADED ASSET, and FAULT + DEGRADED. Sampled independently of the evaluation scenario seeds. | Training distribution lacks faults / high-risk twins / low SOC (`STAGE_43_1_TRAINING_DATA_AUDIT.md`, `STAGE_43_1_TWIN_TRAINING_ALIGNMENT.md`). | Medium. Training distribution *deliberately* widened. Mitigated by documenting the distribution separately and by never modifying evaluation scenarios. |
| **R3 — Reward audit (no blind retune)** | Decompose reward into physical-validity components. Decide whether `+2 supercap` has a legitimate physical rationale. If it does, retain and document; if it does not, redesign it to be conditional on the action's *measured* effect. | `+2 supercap` always fires in the training distribution; `+3 reroute` never fires (`STAGE_43_1_REWARD_AUDIT.md`). | **High if not careful.** Reward shaping is the most bias-prone change. Mitigated by (a) declaring the change before validation, (b) reporting per-component decomposition, and (c) running the controlled-state and information-ablation tests after the change. |
| **R4 — Initialization audit** | Isolated experiment comparing existing PyTorch default init vs zero-mean / scaled final-layer init on **identical** scenarios, seeds, budget, architecture, reward. Measure initial Q-value distribution, training stability, action collapse. | The untrained net already collapses to action 2 in 92% of states (Stage-43.1 reward audit). | Low. Standard DQN practice. **Only retained if justified by training stability or sound initialization reasoning, not action diversity.** |

The recommended *minimum* set is **R1 + R2**. **R3** is held in
reserve and only deployed if the controlled-state tests show the
policy remains degenerate after R1+R2+R4. **R4** is run as an
isolated experiment first; the change is only kept if the isolated
experiment justifies it.

## 3. Why Each Repair is Necessary

* **R1 — LSTM alignment.** Without R1, position 72 of the state
  vector lives in `[0.74, 1.08]` during training and `[0.30, 0.49]`
  during evaluation. The network never sees the evaluation
  distribution and cannot learn to use the LSTM channel. The
  Stage-43.1 repair recommendation calls this the **primary** fix.
* **R2 — Representative scenarios.** Without R2, the network never
  observes a fault, never sees a high-risk twin, and never trains on
  a storage-stress state. The Stage-43 architecture repair made the
  network *able* to use these features, but the training loop
  withheld the data. R2 is necessary to make `num_failed > 0`,
  `twin_max_risk > 0.5`, and `battery_soc < 0.2` reachable during
  training.
* **R3 — Reward audit.** Without R3, even after R1+R2 the same
  static `+2 supercap` bonus will fire on every transition in the
  new wider training distribution (because spike loads > 1.2 still
  occur). The reward must be either (a) physically justified *and*
  conditional on the action's measured effect, or (b) redesigned so
  it cannot pre-select a single action.
* **R4 — Initialization audit.** Without R4 we cannot tell whether
  the action-2 collapse is partly a PyTorch-default-init artefact.
  Running the isolated experiment lets us keep or discard the change
  on evidence rather than intuition.

## 4. What Must NOT Change

* The 78-dim extended state vector layout (`models/rl_agent.py`).
* The action catalogue and physical-validity mask semantics
  (`models/rl_agent.py::_valid_actions_mask`).
* The evaluation scenarios A, E, G, H, J
  (`experiments/scenario_matrix.py`).
* The evaluation fingerprint contract (`grid/demand/renewable/fault`
  hashes must match across paired controllers).
* The training/evaluation separation (`eval_mode`, no replay writes,
  no gradient updates during evaluation).
* The information-flow wiring (`info_flow.py`) — LSTM / twin / EMS /
  predictive paths are the *same* code paths used by evaluation.
* The reward function may be redesigned, but the new form must be
  physically justified; we will not blindly tweak coefficients.
* We must **not**:
  - Optimize for higher ENS improvement.
  - Tune the reward until the DQN beats the rule-based controller.
  - Force action diversity.
  - Remove difficult scenarios.
  - Cherry-pick seeds.
  - Modify evaluation scenarios to help the DQN.
  - Use evaluation data for training.
  - Leak future information.
  - Fabricate results.
  - Run the 100-seed final experiment.
  - Add new AI technologies (GNN, MARL, LLM, transformers).

## 5. New Tests

| Test | Purpose |
|------|---------|
| `test_training_lstm_no_future_leakage()` | Verify the LSTM input to the network during training is built only from `t <= current_step` observations, never from `t+1` or later. |
| `test_training_lstm_is_real_lstm()` | Verify the forecast feature during training is the output of `DemandForecaster.predict(history)`, NOT `aggregate_load/20`. |
| `test_training_includes_faults_and_high_risk_twins()` | Verify the training scenarios generator emits episodes with `num_failed > 0` and `twin_max_risk >= 0.5`. |
| `test_twin_training_feature_range()` | Verify the network sees a range of twin features during training (`max_risk` ≥ 0.5 in some transitions; not always 0). |
| `test_storage_state_training_range()` | Verify the network sees high / medium / low SOC for both battery and supercap during training. |
| `test_training_scenarios_independent_of_eval()` | Verify the training scenario seeds are disjoint from the evaluation scenario seeds (`0..9` for eval; `1000..1009` for training). |
| `test_eval_never_trains_*` (existing) | Reinforce the contract that evaluation never updates weights. |
| `test_init_audit_*` | Verify the initialization experiment is runnable and produces the comparison JSON. |

## 6. Training Design

* **Frozen LSTM** is trained **once** on a synthetic dataset
  generated inside `train_scenario_generator.py`, using only training
  seeds (no evaluation data). Its weights are then frozen and
  reused across every training episode.
* **Scenario sampler** — a new module
  `experiments/train_scenario_generator.py` that emits a list of
  ``Scenario``-like objects per episode with controlled mixtures of
  the 9 conditions listed in §2.
* **Training budget** — defined by a small convergence analysis with
  three candidate budgets (e.g. 8/16/24 episodes × 200 steps). The
  budget is selected by looking at training reward, validation
  reward, loss stability, and policy stability. The diagnostic
  budget (8×200) is not the final budget.
* **RNG isolation** — preserved via `derive_stream_seeds`; the
  frozen LSTM construction is wrapped in `torch.random.fork_rng` so
  it cannot perturb the training RNG.
* **Replay buffer, target network, ε-schedule, gradient clip,
  Adam optimiser** — unchanged from `models/rl_agent.py`.

## 7. Evaluation Design

* **Evaluation scenarios** are the same Stage-43 scenarios A, E, G,
  H, J — never modified to help the DQN.
* **Fingerprints** — every run records `grid/demand/renewable/fault`
  hashes; paired controllers on the same seed must show identical
  hashes. Mismatches are invalid runs.
* **Controller set** — `random`, `rule_based`, `untrained_dqn`,
  `trained_dqn`.
* **Ablation set** — `no_lstm`, `no_twin`, `no_predictive`, `no_ems`.
* **Mode** — `eval_mode()` only. No replay writes, no gradient
  updates, no target-net sync.
* **Metrics** — ENS, CMI, restoration rate, restoration time,
  critical-load interruption, voltage violation count, battery
  usage, supercap usage, renewable utilisation, grid import, action
  distribution.
* **Action diversity is a *diagnostic*, not a target.** A
  single-action policy that is physically optimal is acceptable.

## 8. Statistical Design

* 10 seeds per (controller, scenario, ablation). Paired per seed.
* Report: mean, median, std, 95% CI where appropriate, Wilcoxon
  signed-rank for paired comparisons, Cohen's d effect size.
* Multiple-comparison correction where the number of hypotheses
  justifies it (Bonferroni or Holm).
* Do not interpret p-values alone. Report effect sizes.
* Do not claim significance from n=10 if the effect size is small.

## 9. Acceptance Criteria

A Stage-44 result is acceptable only if:

* [ ] The DQN receives the actual LSTM feature during training
  (range overlap with evaluation).
* [ ] No future leakage during training or evaluation.
* [ ] Training and evaluation feature semantics are aligned.
* [ ] Training exposes meaningful twin-risk states
  (`twin_max_risk` ≥ 0.5 in some transitions).
* [ ] Training exposes meaningful storage states (high/medium/low
  SOC for both battery and supercap).
* [ ] Training scenarios are independent of evaluation scenarios.
* [ ] The reward is physically justified or has been redesigned so
  it cannot pre-select a single action.
* [ ] The DQN does not rely on an arbitrary action bonus.
* [ ] Evaluation is frozen (`eval_mode`, no replay writes).
* [ ] The state distribution report shows validation states are not
  fully outside the training domain.
* [ ] Information ablations are valid (the network responds to the
  LSTM / twin / storage features).
* [ ] Paired fingerprints match.
* [ ] The full test suite passes.
* [ ] The 10-seed validation is completed.
* [ ] Results are not judged solely by action diversity.
* [ ] Claims match evidence.

## 10. Failure Conditions

* **Stage 44 fails** if:
  - The 10-seed validation cannot complete without run-time errors.
  - The trained DQN still collapses to a single action *and* that
    action is provably sub-optimal under the learned reward.
  - The LSTM feature during training is still the
    `aggregate_load/20` stand-in.
  - Any future leakage is detected by the no-leakage test.
  - The state-distribution report shows validation states fully
    outside the training domain.
  - Fingerprints differ between paired runs.
* **Negative result is acceptable** — a scientifically valid negative
  result is preferred to a fabricated positive one. If the DQN does
  not beat the rule-based controller, we **report it** and do not
  tune to win.

## 11. Out-of-Scope (Stage-45 and beyond)

* 100-seed experiment (Stage 45 will decide whether it is justified).
* Final research paper writing.
* New AI technologies.
* Adding new metrics or scenarios beyond what the Stage-43 contract
  requires.

## 12. Documents to Produce

| Document | Status |
|----------|--------|
| `docs/STAGE_44_IMPLEMENTATION_PLAN.md` | this file |
| `docs/STAGE_44_TRAINING_SCENARIOS.md` | describes the training scenario generator |
| `docs/STAGE_44_REWARD_DESIGN.md` | reward audit + redesign rationale |
| `docs/STAGE_44_LSTM_ALIGNMENT.md` | LSTM training-time vs evaluation-time alignment |
| `docs/STAGE_44_TWIN_ALIGNMENT.md` | digital-twin feature range during training |
| `docs/STAGE_44_STATE_DISTRIBUTION.md` | training vs validation distribution comparison |
| `docs/STAGE_44_DQN_TRAINING.md` | training design, budget selection, RNG isolation |
| `docs/STAGE_44_INITIALIZATION_AUDIT.md` | R4 isolated experiment results |
| `docs/STAGE_44_INFORMATION_ABLATION.md` | information ablation results |
| `docs/STAGE_44_VALIDATION_REPORT.md` | 10-seed validation summary |
| `docs/STAGE_44_COMPLETION_REPORT.md` | final completion report with claims/gate |
