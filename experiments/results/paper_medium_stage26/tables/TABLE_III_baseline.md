# TABLE III -- Baseline comparison

## Per-policy summary
| controller_label | weather_mode | n_faults_mean | restoration_rate_mean | voltage_violation_count_mean | energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| dqn_core_only | normal | 2.0 | 0.0 | 0.0 | 0.36074474370978576 |
| full_stack | normal | 2.0 | 0.0 | 0.0 | 0.5747436535338889 |
| random | normal | 2.0 | 0.0 | 0.0 | 0.579505473203184 |
| rule_based | normal | 2.0 | 0.0 | 0.0 | 0.52976118022196 |

## Paired comparison (anchor = rule_based)
| controller_label | anchor_label | n_pairs | delta_restoration_rate_mean | delta_voltage_violation_count_mean | delta_energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| dqn_core_only | rule_based | 5 | 0.0 | 0.0 | -0.16901643651217418 |
| full_stack | rule_based | 5 | 0.0 | 0.0 | 0.044982473311928936 |
| random | rule_based | 5 | 0.0 | 0.0 | 0.049744292981224056 |
