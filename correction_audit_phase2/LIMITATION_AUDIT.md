# LIMITATION AUDIT — Corrected Experiment B

Every limitation below is disclosed so that the paper can state precisely what the corrected 540-run dataset can and cannot support. None of these limitations were introduced by the analysis; all are properties of the frozen experiment.

## L1. Simulation-only, no field evidence

All metrics are counts computed inside the simulator (quasi-steady power flow on a synthetic 49-node grid). They are self-consistent and reproducible but are not measurements against a calibrated physical system. No hardware-in-the-loop and no field deployment evidence exists. Claims requiring real-world validation are classified NOT TESTED in the claim audit.

## L2. Demonstrative 49-node testbed, not a real distribution feeder

The grid is a synthetic 49-node network constructed from the city layout, not a real utility feeder. Topology, line ratings, and load placement are author-defined, so absolute metric values (ENS in MW·steps, SAIFI per customer) carry no external calibration.

## L3. IEEE-13 work is demonstrative, not publication-grade

The IEEE-13 material in this repository is a balanced positive-sequence per-unit equivalent with `validation_status: "demonstrative"`; it is not the full three-phase unbalanced IEEE-13 reference. Experiment B itself does not benchmark against IEEE-13. The 'validated on IEEE-13' claim is classified NOT TESTED.

## L4. Modest sample size: n = 30 paired seeds per (stress level, policy)

n = 30 is the pre-registered minimum for the paired Wilcoxon test at alpha = 0.05 and was fixed before the experiment (deviation from the initial 100-seed freeze is documented in the manifest). With 30 seeds the study has limited power to detect small effects, which strengthens the case for reporting null results as INCONCLUSIVE rather than as proof of equality.

## L5. Predictive pathway null activation (observed, not tuned)

Across all 540 runs the predictive self-healer executed 12000 assessments but generated **0 recommendations** that reached the grid. Under the frozen twin-risk logic no restoration action was ever dispatched by the predictive pathway, so (a) the ablation comparisons involving the predictive stage cannot measure its contribution, and (b) the correct statement is 'the predictive stage was not observed to activate', not 'it had no effect'. This was not tuned or repaired after results were known (TC-002, TC-005).

## L6. Digital Twin lifecycle assumptions

A `TwinRegistry` is created inside every timestep and discarded, so twin history/ageing does not accumulate across the run. The twin synchronises and is queried (9800 updates / run for twin-enabled policies) but its output feeds a predictive consumer that produces no actionable recommendations in this benchmark. The twin's influence on grid trajectories is therefore untested, not merely small.

## L7. Weather and fault simplification

Only two deterministic stress profiles (moderate / severe) with static load multipliers, fault counts and durations are used; weather is limited to `normal` vs `storm`. There is no stochastic weather model, no time-varying fault dynamics, and no cascading-failure or cyber-attack scenario in Experiment B. Results do not generalise outside these profiles.

## L8. Instrumentation saturation (measured, not tuned)

Several pre-registered metrics are fully saturated in the corrected data, meaning they cannot discriminate controllers:

| metric | unique values | min | max | sd |
|---|---:|---:|---:|---:|
| saidi | 1 | 0 | 0 | 0 |
| resilience_time_to_50pct_restoration | 1 | 0 | 0 | 0 |
| stress_critical_load_restored_pct | 1 | 100 | 100 | 0 |
| switching_operations | 1 | 0 | 0 | 0 |
| stress_restoration_rate | 1 | 0 | 0 | 0 |

Root causes (see SATURATION_RECHECK.md): SAIDI = 0 because no fault is ever recorded as `restored`; time-to-50%-restoration = 0 because service is 1.0 at step 0; critical-load restoration = 100 because the recorded restoration MW can exceed the recorded interruption baseline; `switching_operations` is not incremented by the FLISR tie-switch closure path. **Three of the four pre-registered primary outcomes (PO2, PO3, PO4) are therefore non-discriminating by instrumentation.**

## L9. AI-stage outcomes are bit-identical per seed (DQN trajectory decoupling)

All DQN-based policies (`dqn_core_only`, `full_stack`, and every ablation) produce numerically identical outcomes at every seed. Module counters prove LSTM, Twin, Predictive and DQN execute where enabled, but the actions produced by these stages do not change the grid trajectory recorded in this benchmark (DQN actions are counted but not dispatched to grid primitives; the predictive stage generates no recommendations). The ablation comparisons therefore measure execution presence, not benefit.

## L10. Computational cost is not a selling point

Paired per seed, `full_stack` vs `rule_based`:

| level | metric | median full_stack | median rule_based | ratio |
|---|---|---:|---:|---:|
| moderate | runtime_s | 1.297 | 0.692 | 1.875 |
| moderate | controller_runtime_s | 0.4118 | 0.0038 | 108.4 |
| moderate | power_flow_runtime_s | 0.2727 | 0.2271 | 1.201 |
| severe | runtime_s | 1.127 | 0.6224 | 1.811 |
| severe | controller_runtime_s | 0.3516 | 0.0037 | 95.03 |
| severe | power_flow_runtime_s | 0.1982 | 0.1701 | 1.165 |

`full_stack` is roughly 100x more expensive in controller runtime with no measurable reliability gain over `rule_based` in this benchmark. Any claim of 'computationally efficient' is contradicted.

## L11. Experiment A vs B are not pooled

Experiment A (nominal; 900 records, 100 seeds, python 3.11 / torch 2.2.2) and Experiment B (stress; 540 records, 30 seeds, python 3.14 / torch 2.11.0) differ in disturbance profiles, fault durations, load/capacity margins, and software stack. They are compared side-by-side only, and paired escalations are exploratory descriptive tests on the 30 shared seeds.

## L12. Reward shaping is not separately instrumented

`no_reward` differs from `full_stack` only in the DQN training signal; because DQN actions never alter the recorded grid trajectory, the reward-shaping stage cannot be isolated from the DQN-stage null effect. Its ablation is reported as execution-level evidence only.

## L13. No post-result tuning

The corrected dataset is the frozen rerun; no architecture, controller, scenario, threshold, or metric was changed to manufacture a result. Saturation, null activation, and the computational overhead are reported as observed.

## L14. Generalisability

Because of L1-L9, the only scientifically supported claim is the directional one: FLISR-enabled controllers reduce cumulative unserved energy relative to no-action baselines under these two stress profiles. No quantitative value transfers to any real or other simulated network without re-benchmarking.
