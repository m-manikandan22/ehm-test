# Ablation table

## Per-policy summary
| controller_label | weather_mode | n_faults_mean | restoration_rate_mean | voltage_violation_count_mean | energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| full_stack |  | 5.0 | 0.0 | 0.0 | 1.666715968605154 |
| no_lstm |  | 5.0 | 0.0 | 0.0 | 1.7558902626134416 |
| no_twin |  | 5.0 | 0.0 | 0.0 | 1.5973693463882086 |
| no_predictive |  | 5.0 | 0.0 | 0.0 | 1.5523657469971963 |
| no_reward |  | 5.0 | 0.0 | 0.0 | 1.607683259780302 |
| dqn_core_only |  | 5.0 | 0.0 | 0.0 | 0.9030777952628745 |
| rule_based |  | 5.0 | 0.0 | 0.0 | 1.6427783513245473 |
| random |  | 5.0 | 0.0 | 0.0 | 1.5094255754085542 |
| persistence |  | 5.0 | 0.0 | 0.0 | 1.6030029894618878 |

## Paired comparison (anchor = rule_based)