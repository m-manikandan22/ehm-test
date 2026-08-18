# CORRECTED STATISTICAL ANALYSIS — Experiment B (540 runs)

Paired by seed (n = 30 per level x policy). Differences defined as **full_stack minus comparator** (a - b).

Primary test: Wilcoxon signed-rank (asymptotic, zero-diffs dropped). Robustness: paired t-test.
Effect sizes: Cliff's delta (pre-registered, computed alongside Wilcoxon) and paired Cohen's d.

Holm-Bonferroni correction applied across the **four pre-registered primary outcomes within each controller pair** at each stress level (family per PRIMARY_OUTCOMES.md).

## Full comparison table

### moderate: full_stack vs persistence

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 501.2 | 909.4 | -394.5 | -48.10 | 0 | 1.734e-06 | 6.938e-06 | 1.509e-11 | 6.036e-11 | -1.000 | -1.947 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

### moderate: full_stack vs random

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 501.2 | 909.4 | -394.5 | -48.10 | 0 | 1.734e-06 | 6.938e-06 | 1.509e-11 | 6.036e-11 | -1.000 | -1.947 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

### moderate: full_stack vs rule_based

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 501.2 | 449.7 | -3.399 | -1.02 | 199 | 0.4908 | 1 | 0.2408 | 0.963 | -0.067 | 0.219 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

### moderate: full_stack vs dqn_core_only

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 501.2 | 501.2 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

### moderate: full_stack vs no_lstm

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 501.2 | 501.2 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

### moderate: full_stack vs no_twin

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 501.2 | 501.2 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

### moderate: full_stack vs no_predictive

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 501.2 | 501.2 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

### moderate: full_stack vs no_reward

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 501.2 | 501.2 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

### severe: full_stack vs persistence

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 1330 | 6224 | -4787 | -78.33 | 0 | 1.734e-06 | 6.938e-06 | 1.216e-27 | 4.865e-27 | -1.000 | -7.738 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

### severe: full_stack vs random

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 1330 | 6224 | -4787 | -78.33 | 0 | 1.734e-06 | 6.938e-06 | 1.216e-27 | 4.865e-27 | -1.000 | -7.738 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

### severe: full_stack vs rule_based

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 1330 | 1310 | 13.14 | 0.72 | 153 | 0.102 | 0.408 | 0.2574 | 1 | 0.067 | 0.211 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

### severe: full_stack vs dqn_core_only

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 1330 | 1330 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

### severe: full_stack vs no_lstm

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 1330 | 1330 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

### severe: full_stack vs no_twin

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 1330 | 1330 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

### severe: full_stack vs no_predictive

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 1330 | 1330 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

### severe: full_stack vs no_reward

| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PO1_ens | stress_cumulative_unserved_energy | 30 | 1330 | 1330 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO2_restoration_time | resilience_time_to_50pct_restoration | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO3_critical_load | stress_critical_load_restored_pct | 30 | 100 | 100 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |
| PO4_saidi | saidi | 30 | 0 | 0 | 0 | 0.00 | 0 | 1 | 1 | 1 | 1 | 0.000 | 0.000 |

## Holm family justification

PRIMARY_OUTCOMES.md: "Multiple-comparison correction: Holm correction across the four primary outcomes for each pair of controllers."
The family is therefore **4 tests per (stress level, controller pair)**, applied to the raw Wilcoxon p-values. Raw and Holm-adjusted p-values are both stored.

_Raw results were not modified._
