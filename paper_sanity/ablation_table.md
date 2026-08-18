# Ablation table

## Per-policy summary
| controller_label | weather_mode | n_faults_mean | restoration_rate_mean | voltage_violation_count_mean | energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| full_stack |  | 3.0 | 0.0 | 0.0 | 0.33604863355042563 |
| no_lstm |  | 3.0 | 0.0 | 0.0 | 0.3746489056127497 |
| no_twin |  | 3.0 | 0.0 | 0.0 | 0.3735492639413203 |
| no_predictive |  | 3.0 | 0.0 | 0.0 | 0.3656034502985503 |
| no_reward |  | 3.0 | 0.0 | 0.0 | 0.34907554990135387 |
| dqn_core_only |  | 3.0 | 0.0 | 0.0 | 0.2074770876687132 |
| rule_based |  | 3.0 | 0.0 | 0.0 | 0.3476908487050103 |
| random |  | 3.0 | 0.0 | 0.0 | 0.27750243721989193 |
| persistence |  | 3.0 | 0.0 | 0.0 | 0.26570357703521924 |

## Paired comparison (anchor = rule_based)