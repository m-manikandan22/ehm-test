# Baseline table

## Per-policy summary
| controller_label | weather_mode | n_faults_mean | restoration_rate_mean | voltage_violation_count_mean | energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| random | normal | 5.0 | 0.0 | 0.0 | 1.5916936683019114 |
| rule_based | normal | 5.0 | 0.0 | 0.0 | 1.5509790916976296 |

## Paired comparison (anchor = rule_based)
| controller_label | anchor_label | n_pairs | delta_restoration_rate_mean | delta_voltage_violation_count_mean | delta_energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| random | rule_based | 1 | 0.0 | 0.0 | 0.009592426755654193 |
