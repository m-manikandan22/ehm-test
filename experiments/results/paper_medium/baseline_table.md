# Baseline table

## Per-policy summary
| controller_label | weather_mode | n_faults_mean | restoration_rate_mean | voltage_violation_count_mean | energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| random | normal | 3.0 | 0.0 | 0.0 | 0.9979211169197765 |
| rule_based | normal | 3.0 | 0.0 | 0.0 | 1.1916962247524305 |

## Paired comparison (anchor = rule_based)
| controller_label | anchor_label | n_pairs | delta_restoration_rate_mean | delta_voltage_violation_count_mean | delta_energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| random | rule_based | 1 | 0.0 | 0.0 | 0.061220737682819604 |
