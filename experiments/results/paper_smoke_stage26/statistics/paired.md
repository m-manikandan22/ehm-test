# Paired comparison vs `rule_based`

## Per-policy summary
| controller_label | weather_mode | n_faults_mean | restoration_rate_mean | voltage_violation_count_mean | energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| dqn_core_only | normal | 1.0 | 0.0 | 0.0 | 0.026615062522130504 |
| full_stack | normal | 1.0 | 0.0 | 0.0 | 0.07166659951934645 |
| random | normal | 1.0 | 0.0 | 0.0 | 0.056291762935180956 |
| rule_based | normal | 1.0 | 0.0 | 0.0 | 0.0685825503825789 |

## Paired comparison (anchor = rule_based)
| controller_label | anchor_label | n_pairs | delta_restoration_rate_mean | delta_voltage_violation_count_mean | delta_energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| dqn_core_only | rule_based | 2 | 0.0 | 0.0 | -0.041967487860448405 |
| full_stack | rule_based | 2 | 0.0 | 0.0 | 0.0030840491367675332 |
| random | rule_based | 2 | 0.0 | 0.0 | -0.012290787447397956 |
