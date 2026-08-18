# Paired comparison vs `rule_based`

## Per-policy summary
| controller_label | weather_mode | n_faults_mean | restoration_rate_mean | voltage_violation_count_mean | energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| dqn_core_only | normal | 3.0 | 0.95 | 0.0 | 0.7412668330835009 |
| full_stack | normal | 3.0 | 0.95 | 0.0 | 1.3439542712060253 |
| random | normal | 3.0 | 0.95 | 0.0 | 1.3433055912256067 |
| rule_based | normal | 3.0 | 0.95 | 0.0 | 1.3548901594476463 |

## Paired comparison (anchor = rule_based)
| controller_label | anchor_label | n_pairs | delta_restoration_rate_mean | delta_voltage_violation_count_mean | delta_energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| dqn_core_only | rule_based | 20 | 0.0 | 0.0 | -0.6136233263641454 |
| full_stack | rule_based | 20 | 0.0 | 0.0 | -0.0109358882416212 |
| random | rule_based | 20 | 0.0 | 0.0 | -0.01158456822203958 |
