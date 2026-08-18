# MODULE EXECUTION AUDIT — Corrected Experiment B (540 runs)

Module-call counters aggregated from `experiment_B_runs.json` (per policy x stress level; sums across 30 seeds).

## 1. FLISR & restoration

| policy | stress_level | n_runs | flisr_calls | flisr_successes | flisr_failures | restoration_attempts | restoration_applied | switching_operations | stress_n_restored | stress_restoration_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| persistence | moderate | 30 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| random | moderate | 30 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| rule_based | moderate | 30 | 6000 | 659 | 0 | 39106 | 612 | 0.0 | 0.0 | 0.0 |
| dqn_core_only | moderate | 30 | 6000 | 660 | 0 | 39127 | 613 | 0.0 | 0.0 | 0.0 |
| full_stack | moderate | 30 | 6000 | 660 | 0 | 39127 | 613 | 0.0 | 0.0 | 0.0 |
| no_lstm | moderate | 30 | 6000 | 660 | 0 | 39127 | 613 | 0.0 | 0.0 | 0.0 |
| no_twin | moderate | 30 | 6000 | 660 | 0 | 39127 | 613 | 0.0 | 0.0 | 0.0 |
| no_predictive | moderate | 30 | 6000 | 660 | 0 | 39127 | 613 | 0.0 | 0.0 | 0.0 |
| no_reward | moderate | 30 | 6000 | 660 | 0 | 39127 | 613 | 0.0 | 0.0 | 0.0 |
| persistence | severe | 30 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| random | severe | 30 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| rule_based | severe | 30 | 6000 | 2813 | 0 | 150112 | 2789 | 0.0 | 0.0 | 0.0 |
| dqn_core_only | severe | 30 | 6000 | 2809 | 0 | 149823 | 2783 | 0.0 | 0.0 | 0.0 |
| full_stack | severe | 30 | 6000 | 2809 | 0 | 149823 | 2783 | 0.0 | 0.0 | 0.0 |
| no_lstm | severe | 30 | 6000 | 2809 | 0 | 149823 | 2783 | 0.0 | 0.0 | 0.0 |
| no_twin | severe | 30 | 6000 | 2809 | 0 | 149823 | 2783 | 0.0 | 0.0 | 0.0 |
| no_predictive | severe | 30 | 6000 | 2809 | 0 | 149823 | 2783 | 0.0 | 0.0 | 0.0 |
| no_reward | severe | 30 | 6000 | 2809 | 0 | 149823 | 2783 | 0.0 | 0.0 | 0.0 |

## 2. Digital Twin

| policy | stress_level | twin_updates | twin_queries | twin_reads | twin_predictions | twin_decisions_consumed |
|---|---|---|---|---|---|---|
| persistence | moderate | 0 | 0 | 0 | 0 | 0 |
| random | moderate | 0 | 0 | 0 | 0 | 0 |
| rule_based | moderate | 0 | 0 | 0 | 0 | 0 |
| dqn_core_only | moderate | 0 | 0 | 0 | 0 | 0 |
| full_stack | moderate | 294000 | 294000 | 294000 | 0 | 6000 |
| no_lstm | moderate | 294000 | 294000 | 294000 | 0 | 6000 |
| no_twin | moderate | 0 | 0 | 0 | 0 | 0 |
| no_predictive | moderate | 294000 | 0 | 0 | 0 | 0 |
| no_reward | moderate | 294000 | 294000 | 294000 | 0 | 6000 |
| persistence | severe | 0 | 0 | 0 | 0 | 0 |
| random | severe | 0 | 0 | 0 | 0 | 0 |
| rule_based | severe | 0 | 0 | 0 | 0 | 0 |
| dqn_core_only | severe | 0 | 0 | 0 | 0 | 0 |
| full_stack | severe | 294000 | 294000 | 294000 | 0 | 6000 |
| no_lstm | severe | 294000 | 294000 | 294000 | 0 | 6000 |
| no_twin | severe | 0 | 0 | 0 | 0 | 0 |
| no_predictive | severe | 294000 | 0 | 0 | 0 | 0 |
| no_reward | severe | 294000 | 294000 | 294000 | 0 | 6000 |

## 3. LSTM / model

| policy | stress_level | lstm/model_calls | lstm_calls | inference_successes | inference_failures | model_outputs_consumed |
|---|---|---|---|---|---|---|
| persistence | moderate | 0 | 0 | 0 | 0 | 0 |
| random | moderate | 0 | 0 | 0 | 0 | 0 |
| rule_based | moderate | 0 | 0 | 0 | 0 | 0 |
| dqn_core_only | moderate | 0 | 0 | 0 | 0 | 0 |
| full_stack | moderate | 6000 | 6000 | 6000 | 0 | 6000 |
| no_lstm | moderate | 0 | 0 | 0 | 0 | 0 |
| no_twin | moderate | 6000 | 6000 | 6000 | 0 | 6000 |
| no_predictive | moderate | 6000 | 6000 | 6000 | 0 | 6000 |
| no_reward | moderate | 6000 | 6000 | 6000 | 0 | 6000 |
| persistence | severe | 0 | 0 | 0 | 0 | 0 |
| random | severe | 0 | 0 | 0 | 0 | 0 |
| rule_based | severe | 0 | 0 | 0 | 0 | 0 |
| dqn_core_only | severe | 0 | 0 | 0 | 0 | 0 |
| full_stack | severe | 6000 | 6000 | 6000 | 0 | 6000 |
| no_lstm | severe | 0 | 0 | 0 | 0 | 0 |
| no_twin | severe | 6000 | 6000 | 6000 | 0 | 6000 |
| no_predictive | severe | 6000 | 6000 | 6000 | 0 | 6000 |
| no_reward | severe | 6000 | 6000 | 6000 | 0 | 6000 |

## 4. Predictive pathway

| policy | stress_level | predictive_assessments | predictions_generated | recommendations_generated | recommendations_accepted | predictive_dispatched | predictive_applied | predictive_rejected | predictive_failed |
|---|---|---|---|---|---|---|---|---|---|
| persistence | moderate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| random | moderate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rule_based | moderate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dqn_core_only | moderate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| full_stack | moderate | 6000 | 6000 | 0 | 0 | 0 | 0 | 0 | 0 |
| no_lstm | moderate | 6000 | 6000 | 0 | 0 | 0 | 0 | 0 | 0 |
| no_twin | moderate | 6000 | 6000 | 0 | 0 | 0 | 0 | 0 | 0 |
| no_predictive | moderate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| no_reward | moderate | 6000 | 6000 | 0 | 0 | 0 | 0 | 0 | 0 |
| persistence | severe | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| random | severe | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rule_based | severe | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dqn_core_only | severe | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| full_stack | severe | 6000 | 6000 | 0 | 0 | 0 | 0 | 0 | 0 |
| no_lstm | severe | 6000 | 6000 | 0 | 0 | 0 | 0 | 0 | 0 |
| no_twin | severe | 6000 | 6000 | 0 | 0 | 0 | 0 | 0 | 0 |
| no_predictive | severe | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| no_reward | severe | 6000 | 6000 | 0 | 0 | 0 | 0 | 0 | 0 |

## 5. Control actions

| policy | stress_level | dqn_actions | rule_actions | random_actions | noop_actions | actions_taken |
|---|---|---|---|---|---|---|
| persistence | moderate | 0 | 0 | 0 | 6000 | 0.0 |
| random | moderate | 0 | 0 | 6000 | 0 | 200.0 |
| rule_based | moderate | 0 | 6000 | 0 | 0 | 200.0 |
| dqn_core_only | moderate | 6000 | 0 | 0 | 0 | 200.0 |
| full_stack | moderate | 6000 | 0 | 0 | 0 | 200.0 |
| no_lstm | moderate | 6000 | 0 | 0 | 0 | 200.0 |
| no_twin | moderate | 6000 | 0 | 0 | 0 | 200.0 |
| no_predictive | moderate | 6000 | 0 | 0 | 0 | 200.0 |
| no_reward | moderate | 6000 | 0 | 0 | 0 | 200.0 |
| persistence | severe | 0 | 0 | 0 | 6000 | 0.0 |
| random | severe | 0 | 0 | 6000 | 0 | 200.0 |
| rule_based | severe | 0 | 6000 | 0 | 0 | 200.0 |
| dqn_core_only | severe | 6000 | 0 | 0 | 0 | 200.0 |
| full_stack | severe | 6000 | 0 | 0 | 0 | 200.0 |
| no_lstm | severe | 6000 | 0 | 0 | 0 | 200.0 |
| no_twin | severe | 6000 | 0 | 0 | 0 | 200.0 |
| no_predictive | severe | 6000 | 0 | 0 | 0 | 200.0 |
| no_reward | severe | 6000 | 0 | 0 | 0 | 200.0 |

## 6. Policy verdicts

| policy | stress_level | verdict |
|---|---|---|
| persistence | moderate | PASS |
| random | moderate | PASS |
| rule_based | moderate | PASS WITH LIMITATION |
| dqn_core_only | moderate | PASS WITH LIMITATION |
| full_stack | moderate | PASS WITH LIMITATION |
| no_lstm | moderate | PASS WITH LIMITATION |
| no_twin | moderate | PASS WITH LIMITATION |
| no_predictive | moderate | PASS WITH LIMITATION |
| no_reward | moderate | PASS WITH LIMITATION |
| persistence | severe | PASS |
| random | severe | PASS |
| rule_based | severe | PASS WITH LIMITATION |
| dqn_core_only | severe | PASS WITH LIMITATION |
| full_stack | severe | PASS WITH LIMITATION |
| no_lstm | severe | PASS WITH LIMITATION |
| no_twin | severe | PASS WITH LIMITATION |
| no_predictive | severe | PASS WITH LIMITATION |
| no_reward | severe | PASS WITH LIMITATION |

## 7. Observations

- FLISR executes for every FLISR-enabled policy (200 calls/run) and applies restoration actions; **zero** FLISR failures across the experiment.
- Twin syncs/updates (9800/run = 49 nodes x 200 steps) and LSTM model calls (200/run) match policy configuration exactly; ablations (`no_lstm`, `no_twin`, `no_predictive`) show the expected zero counts for the disabled module.
- The predictive pathway is wired (200 assessments/run when enabled) but produced **zero recommendations** under the frozen twin-risk logic; hence zero predictive actions dispatched/applied/rejected. Reported as an observed null activation, not a tuning defect.
- Restoration actions are applied by FLISR (state changes; ENS reduced) but the fault bookkeeping never records a fault as `restored`, and the `switching_operations` metric is not incremented by the SCADA restoration path.
- DQN/rule/random/noop actions are recorded per step; no per-action grid-apply counter exists for these control channels.

_Raw results were not modified. 18 rows written to MODULE_EXECUTION_AUDIT.csv._
