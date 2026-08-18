# Ablation table

## Per-policy summary
| controller_label | weather_mode | n_faults_mean | restoration_rate_mean | voltage_violation_count_mean | energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| full_stack |  | 2.0 | 0.0 | 0.0 | 0.04284694831527269 |
| no_lstm |  | 2.0 | 0.0 | 0.0 | 0.029518109166759118 |
| no_twin |  | 2.0 | 0.0 | 0.0 | 0.02752894480153014 |
| no_predictive |  | 2.0 | 0.0 | 0.0 | 0.03468075722112621 |
| no_reward |  | 2.0 | 0.0 | 0.0 | 0.03233468747280479 |
| dqn_core_only |  | 2.0 | 0.0 | 0.0 | 0.013112010922797922 |
| rule_based |  | 2.0 | 0.0 | 0.0 | 0.04151330163494269 |
| random |  | 2.0 | 0.0 | 0.0 | 0.018904947228799755 |
| persistence |  | 2.0 | 0.0 | 0.0 | 0.013533192174433089 |

## Paired comparison (anchor = rule_based)