# EXPERIMENT B — FINAL RESULTS

This is the final, peer-reviewable report for the stress / constrained self-healing validation experiment.

## 1. Configuration

- Experiment ID: `EHM-paper-30seed-stress-v1`
- Frozen at: `2026-08-04T22:55:00.000000+00:00`
- Stress levels: `moderate, severe`
- Seeds: 30 (0..29)
- Ticks per run: 200
- Controllers evaluated: 5 baselines + 6 ablations
- Pre-registered primary outcomes: `stress_cumulative_unserved_energy, resilience_time_to_50pct_restoration, stress_critical_load_restored_pct, saidi`

## 2. Run summary

- Total runs: **540**
- Valid runs: **540** (100.00%)

## 3. Pre-registered primary outcomes

Wilcoxon signed-rank (paired by seed) against anchor `full_stack`, Holm-corrected across all comparisons.

| level | anchor | other | metric | n | median_anchor | median_other | rel diff (%) | p_holm | Cliff's delta | classification |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| moderate | full_stack | persistence | `stress_cumulative_unserved_energy` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | -0.001 | **INCONCLUSIVE** |
| moderate | full_stack | persistence | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | persistence | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | persistence | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | random | `stress_cumulative_unserved_energy` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | -0.001 | **INCONCLUSIVE** |
| moderate | full_stack | random | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | random | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | random | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | rule_based | `stress_cumulative_unserved_energy` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | -0.001 | **INCONCLUSIVE** |
| moderate | full_stack | rule_based | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | rule_based | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | rule_based | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | dqn_core_only | `stress_cumulative_unserved_energy` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | dqn_core_only | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | dqn_core_only | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | dqn_core_only | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_lstm | `stress_cumulative_unserved_energy` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_lstm | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_lstm | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_lstm | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_twin | `stress_cumulative_unserved_energy` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_twin | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_twin | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_twin | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_predictive | `stress_cumulative_unserved_energy` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_predictive | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_predictive | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_predictive | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_reward | `stress_cumulative_unserved_energy` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_reward | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_reward | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| moderate | full_stack | no_reward | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | persistence | `stress_cumulative_unserved_energy` | 30 | 8364.415 | 8239.249 | 1.52 | 1.0000 | 0.133 | **INCONCLUSIVE** |
| severe | full_stack | persistence | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | persistence | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | persistence | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | random | `stress_cumulative_unserved_energy` | 30 | 8364.415 | 8239.249 | 1.52 | 1.0000 | 0.133 | **INCONCLUSIVE** |
| severe | full_stack | random | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | random | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | random | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | rule_based | `stress_cumulative_unserved_energy` | 30 | 8364.415 | 8239.249 | 1.52 | 1.0000 | 0.133 | **INCONCLUSIVE** |
| severe | full_stack | rule_based | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | rule_based | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | rule_based | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | dqn_core_only | `stress_cumulative_unserved_energy` | 30 | 8364.415 | 8364.415 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | dqn_core_only | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | dqn_core_only | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | dqn_core_only | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_lstm | `stress_cumulative_unserved_energy` | 30 | 8364.415 | 8364.415 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_lstm | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_lstm | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_lstm | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_twin | `stress_cumulative_unserved_energy` | 30 | 8364.415 | 8364.415 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_twin | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_twin | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_twin | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_predictive | `stress_cumulative_unserved_energy` | 30 | 8364.415 | 8364.415 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_predictive | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_predictive | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_predictive | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_reward | `stress_cumulative_unserved_energy` | 30 | 8364.415 | 8364.415 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_reward | `resilience_time_to_50pct_restoration` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_reward | `stress_critical_load_restored_pct` | 30 | 100.000 | 100.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |
| severe | full_stack | no_reward | `saidi` | 30 | 0.000 | 0.000 | 0.00 | 1.0000 | 0.000 | **INCONCLUSIVE** |

## 4. Validity gates

| stress level | controller | n | valid (%) |
|---|---|---:|---:|
| moderate | dqn_core_only | 30 | 100.0 |
| moderate | full_stack | 30 | 100.0 |
| moderate | no_lstm | 30 | 100.0 |
| moderate | no_predictive | 30 | 100.0 |
| moderate | no_reward | 30 | 100.0 |
| moderate | no_twin | 30 | 100.0 |
| moderate | persistence | 30 | 100.0 |
| moderate | random | 30 | 100.0 |
| moderate | rule_based | 30 | 100.0 |
| severe | dqn_core_only | 30 | 100.0 |
| severe | full_stack | 30 | 100.0 |
| severe | no_lstm | 30 | 100.0 |
| severe | no_predictive | 30 | 100.0 |
| severe | no_reward | 30 | 100.0 |
| severe | no_twin | 30 | 100.0 |
| severe | persistence | 30 | 100.0 |
| severe | random | 30 | 100.0 |
| severe | rule_based | 30 | 100.0 |

## 5. Runtime cost

| stress level | controller | mean ctrl-rt (s) | mean wallclock (s) |
|---|---|---:|---:|
| moderate | dqn_core_only | 0.000 | 0.000 |
| moderate | full_stack | 0.000 | 0.000 |
| moderate | no_lstm | 0.000 | 0.000 |
| moderate | no_predictive | 0.000 | 0.000 |
| moderate | no_reward | 0.000 | 0.000 |
| moderate | no_twin | 0.000 | 0.000 |
| moderate | persistence | 0.000 | 0.000 |
| moderate | random | 0.000 | 0.000 |
| moderate | rule_based | 0.000 | 0.000 |
| severe | dqn_core_only | 0.000 | 0.000 |
| severe | full_stack | 0.000 | 0.000 |
| severe | no_lstm | 0.000 | 0.000 |
| severe | no_predictive | 0.000 | 0.000 |
| severe | no_reward | 0.000 | 0.000 |
| severe | no_twin | 0.000 | 0.000 |
| severe | persistence | 0.000 | 0.000 |
| severe | random | 0.000 | 0.000 |
| severe | rule_based | 0.000 | 0.000 |

## 6. Honest reporting

The pre-registered primary outcomes are reported **as-is**. Outcomes with insufficient paired variance are reported as `INCONCLUSIVE`. The benchmark was frozen before the final experiment was run and was **not** retuned based on results.
