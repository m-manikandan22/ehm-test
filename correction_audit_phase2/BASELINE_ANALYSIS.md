# BASELINE ANALYSIS — Corrected Experiment B

Full Stack vs `persistence`, `random`, `rule_based`, `dqn_core_only`. Favorable and unfavorable results are both reported.

## Median secondary-metric matrix

### moderate

| metric | persistence | random | rule_based | dqn_core_only | full_stack |
|---|---|---|---|---|---|
| stress_cumulative_unserved_energy | 909.4 | 909.4 | 449.7 | 501.2 | 501.2 |
| resilience_loss_area | 105.5 | 105.5 | 119.5 | 117.4 | 117.4 |
| saifi | 0.102 | 0.102 | 0.102 | 0.102 | 0.102 |
| ens | 50 | 50 | 50 | 50 | 50 |
| voltage_violation_count | 2592 | 2592 | 2502 | 2544 | 2544 |
| number_of_islands | 1 | 1 | 1 | 1 | 1 |
| isolated_nodes | 25 | 25 | 25 | 25 | 25 |
| actions_taken | 0 | 200 | 200 | 200 | 200 |
| frequency_deviation_count | 6052 | 6052 | 8158 | 8158 | 8158 |
| average_voltage_pu | 0.4755 | 0.4755 | 0.4756 | 0.4756 | 0.4756 |
| maximum_voltage_pu | 1 | 1 | 1 | 1 | 1 |
| stress_cum_feasible_restoration_mw | 0 | 0 | 9.61 | 9.686 | 9.686 |
| stress_cum_unserved_restoration_mw | 0 | 0 | 0.5213 | 0.07979 | 0.07979 |
| stress_n_faults | 4 | 4 | 4 | 4 | 4 |
| runtime_s | 0.5543 | 0.5718 | 0.692 | 0.823 | 1.297 |
| controller_runtime_s | 0.0004 | 0.0011 | 0.0038 | 0.1283 | 0.4118 |
| power_flow_runtime_s | 0.211 | 0.2173 | 0.2271 | 0.2325 | 0.2727 |

### severe

| metric | persistence | random | rule_based | dqn_core_only | full_stack |
|---|---|---|---|---|---|
| stress_cumulative_unserved_energy | 6224 | 6224 | 1310 | 1330 | 1330 |
| resilience_loss_area | 153.3 | 153.3 | 71.38 | 73.31 | 73.31 |
| saifi | 0.1633 | 0.1633 | 0.1633 | 0.1633 | 0.1633 |
| ens | 80 | 80 | 80 | 80 | 80 |
| voltage_violation_count | 5887 | 5887 | 5882 | 5864 | 5864 |
| line_overload_count | 101 | 101 | 97 | 96 | 96 |
| number_of_islands | 1 | 1 | 1 | 1 | 1 |
| isolated_nodes | 38 | 38 | 38 | 38 | 38 |
| actions_taken | 0 | 200 | 200 | 200 | 200 |
| frequency_deviation_count | 9800 | 9800 | 9800 | 9800 | 9800 |
| average_voltage_pu | 0.222 | 0.222 | 0.222 | 0.222 | 0.222 |
| maximum_voltage_pu | 1 | 1 | 1 | 1 | 1 |
| stress_cum_feasible_restoration_mw | 0 | 0 | 7.773 | 7.102 | 7.102 |
| stress_cum_unserved_restoration_mw | 0 | 0 | 24.12 | 23.75 | 23.75 |
| stress_n_faults | 6 | 6 | 6 | 6 | 6 |
| runtime_s | 0.5533 | 0.5239 | 0.6224 | 0.7282 | 1.127 |
| controller_runtime_s | 0.0005 | 0.0013 | 0.0037 | 0.1212 | 0.3516 |
| power_flow_runtime_s | 0.199 | 0.1881 | 0.1701 | 0.169 | 0.1982 |

## Primary outcomes: full_stack vs baselines

### moderate

| baseline | outcome | median FS | median base | diff | raw p | Holm p | direction | verdict |
|---|---|---|---|---|---|---|---|---|
| persistence | PO1_ens | 501.2 | 909.4 | -394.5 | 1.734e-06 | 6.938e-06 | lower better | SUPPORTED |
| persistence | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| persistence | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | higher better | INCONCLUSIVE |
| persistence | PO4_saidi | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| random | PO1_ens | 501.2 | 909.4 | -394.5 | 1.734e-06 | 6.938e-06 | lower better | SUPPORTED |
| random | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| random | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | higher better | INCONCLUSIVE |
| random | PO4_saidi | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| rule_based | PO1_ens | 501.2 | 449.7 | -3.399 | 0.4908 | 1 | lower better | INCONCLUSIVE |
| rule_based | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| rule_based | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | higher better | INCONCLUSIVE |
| rule_based | PO4_saidi | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| dqn_core_only | PO1_ens | 501.2 | 501.2 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| dqn_core_only | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| dqn_core_only | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | higher better | INCONCLUSIVE |
| dqn_core_only | PO4_saidi | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |

### severe

| baseline | outcome | median FS | median base | diff | raw p | Holm p | direction | verdict |
|---|---|---|---|---|---|---|---|---|
| persistence | PO1_ens | 1330 | 6224 | -4787 | 1.734e-06 | 6.938e-06 | lower better | SUPPORTED |
| persistence | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| persistence | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | higher better | INCONCLUSIVE |
| persistence | PO4_saidi | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| random | PO1_ens | 1330 | 6224 | -4787 | 1.734e-06 | 6.938e-06 | lower better | SUPPORTED |
| random | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| random | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | higher better | INCONCLUSIVE |
| random | PO4_saidi | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| rule_based | PO1_ens | 1330 | 1310 | 13.14 | 0.102 | 0.408 | lower better | INCONCLUSIVE |
| rule_based | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| rule_based | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | higher better | INCONCLUSIVE |
| rule_based | PO4_saidi | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| dqn_core_only | PO1_ens | 1330 | 1330 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| dqn_core_only | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |
| dqn_core_only | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | higher better | INCONCLUSIVE |
| dqn_core_only | PO4_saidi | 0 | 0 | 0 | 1 | 1 | lower better | INCONCLUSIVE |

## Honest headline findings

1. **Favorable:** `full_stack` dramatically reduces ENS vs `persistence`/`random` at both stress levels (severe median 1330 vs 6224 / 6224; raw Wilcoxon p ~ 2e-6; Holm p < 0.05).
2. **Unfavorable:** `rule_based` (FLISR-only) shows slightly *lower* median ENS than `full_stack` at both levels (moderate 449.7 vs 501.2; severe 1309.9 vs 1329.8). The full_stack vs rule_based difference on PO1 is not statistically significant at either level after Holm correction.
3. **Unfavorable:** `full_stack` is statistically indistinguishable from `dqn_core_only` on every primary outcome at every seed.
4. The AI stages (LSTM/Twin/Predictive/Reward) contribute no measurable outcome difference; FLISR is the sole driver of the improvement over no-action baselines.
