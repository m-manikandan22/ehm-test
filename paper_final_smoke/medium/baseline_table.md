# Baseline table

## Per-policy summary
| controller_label | weather_mode | n_faults_mean | restoration_rate_mean | voltage_violation_count_mean | energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| random | normal | 4.0 | 0.0 | 0.0 | 0.6659730733676358 |
| rule_based | normal | 4.0 | 0.0 | 0.0 | 0.7190339803979381 |

## Paired comparison (anchor = rule_based)
| controller_label | anchor_label | n_pairs | delta_restoration_rate_mean | delta_voltage_violation_count_mean | delta_energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| random | rule_based | 1 | 0.0 | 0.0 | -0.23915777840463248 |
