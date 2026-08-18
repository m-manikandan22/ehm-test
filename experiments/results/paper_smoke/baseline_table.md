# Baseline table

## Per-policy summary
| controller_label | weather_mode | n_faults_mean | restoration_rate_mean | voltage_violation_count_mean | energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| random | normal | 2.0 | 0.0 | 0.0 | 0.4534948515845336 |
| rule_based | normal | 2.0 | 0.0 | 0.0 | 0.3966704142567185 |

## Paired comparison (anchor = rule_based)
| controller_label | anchor_label | n_pairs | delta_restoration_rate_mean | delta_voltage_violation_count_mean | delta_energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| random | rule_based | 1 | 0.0 | 0.0 | -0.02019649082915359 |
