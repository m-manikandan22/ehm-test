# Table 2 — Baseline comparison (full_stack vs baselines, primary outcomes)

| stress_level | comparison | outcome | metric | median_full_stack | median_baseline | median_diff | rel_diff_pct | wilcoxon_p_raw | wilcoxon_p_holm | cliffs_delta | cohens_d |
|---|---|---|---|---|---|---|---|---|---|---|---|
| moderate | full_stack vs persistence | PO1_ens | stress_cumulative_unserved_energy | 501.2 | 909.4 | -394.5 | -48.1 | 1.734e-06 | 6.938e-06 | -1 | -1.947 |
| moderate | full_stack vs persistence | PO2_restoration_time | resilience_time_to_50pct_restoration | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| moderate | full_stack vs persistence | PO3_critical_load | stress_critical_load_restored_pct | 100 | 100 | 0 | 0 | 1 | 1 | 0 | 0 |
| moderate | full_stack vs persistence | PO4_saidi | saidi | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| moderate | full_stack vs random | PO1_ens | stress_cumulative_unserved_energy | 501.2 | 909.4 | -394.5 | -48.1 | 1.734e-06 | 6.938e-06 | -1 | -1.947 |
| moderate | full_stack vs random | PO2_restoration_time | resilience_time_to_50pct_restoration | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| moderate | full_stack vs random | PO3_critical_load | stress_critical_load_restored_pct | 100 | 100 | 0 | 0 | 1 | 1 | 0 | 0 |
| moderate | full_stack vs random | PO4_saidi | saidi | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| moderate | full_stack vs rule_based | PO1_ens | stress_cumulative_unserved_energy | 501.2 | 449.7 | -3.399 | -1.018 | 0.4908 | 1 | -0.06667 | 0.2187 |
| moderate | full_stack vs rule_based | PO2_restoration_time | resilience_time_to_50pct_restoration | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| moderate | full_stack vs rule_based | PO3_critical_load | stress_critical_load_restored_pct | 100 | 100 | 0 | 0 | 1 | 1 | 0 | 0 |
| moderate | full_stack vs rule_based | PO4_saidi | saidi | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| moderate | full_stack vs dqn_core_only | PO1_ens | stress_cumulative_unserved_energy | 501.2 | 501.2 | 0 | 0 | 1 | 1 | 0 | 0 |
| moderate | full_stack vs dqn_core_only | PO2_restoration_time | resilience_time_to_50pct_restoration | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| moderate | full_stack vs dqn_core_only | PO3_critical_load | stress_critical_load_restored_pct | 100 | 100 | 0 | 0 | 1 | 1 | 0 | 0 |
| moderate | full_stack vs dqn_core_only | PO4_saidi | saidi | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| severe | full_stack vs persistence | PO1_ens | stress_cumulative_unserved_energy | 1330 | 6224 | -4787 | -78.33 | 1.734e-06 | 6.938e-06 | -1 | -7.738 |
| severe | full_stack vs persistence | PO2_restoration_time | resilience_time_to_50pct_restoration | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| severe | full_stack vs persistence | PO3_critical_load | stress_critical_load_restored_pct | 100 | 100 | 0 | 0 | 1 | 1 | 0 | 0 |
| severe | full_stack vs persistence | PO4_saidi | saidi | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| severe | full_stack vs random | PO1_ens | stress_cumulative_unserved_energy | 1330 | 6224 | -4787 | -78.33 | 1.734e-06 | 6.938e-06 | -1 | -7.738 |
| severe | full_stack vs random | PO2_restoration_time | resilience_time_to_50pct_restoration | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| severe | full_stack vs random | PO3_critical_load | stress_critical_load_restored_pct | 100 | 100 | 0 | 0 | 1 | 1 | 0 | 0 |
| severe | full_stack vs random | PO4_saidi | saidi | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| severe | full_stack vs rule_based | PO1_ens | stress_cumulative_unserved_energy | 1330 | 1310 | 13.14 | 0.7246 | 0.102 | 0.408 | 0.06667 | 0.2109 |
| severe | full_stack vs rule_based | PO2_restoration_time | resilience_time_to_50pct_restoration | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| severe | full_stack vs rule_based | PO3_critical_load | stress_critical_load_restored_pct | 100 | 100 | 0 | 0 | 1 | 1 | 0 | 0 |
| severe | full_stack vs rule_based | PO4_saidi | saidi | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| severe | full_stack vs dqn_core_only | PO1_ens | stress_cumulative_unserved_energy | 1330 | 1330 | 0 | 0 | 1 | 1 | 0 | 0 |
| severe | full_stack vs dqn_core_only | PO2_restoration_time | resilience_time_to_50pct_restoration | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| severe | full_stack vs dqn_core_only | PO3_critical_load | stress_critical_load_restored_pct | 100 | 100 | 0 | 0 | 1 | 1 | 0 | 0 |
| severe | full_stack vs dqn_core_only | PO4_saidi | saidi | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |