# Ablation table

## Per-policy summary
| controller_label | weather_mode | n_faults_mean | restoration_rate_mean | voltage_violation_count_mean | energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| full_stack |  | 2.0 | 0.0 | 0.0 | 0.04636124310739201 |
| no_lstm |  | 2.0 | 0.0 | 0.0 | 0.027520520351166738 |
| no_twin |  | 2.0 | 0.0 | 0.0 | 0.0410909822845754 |
| no_predictive |  | 2.0 | 0.0 | 0.0 | 0.03435111176654692 |
| no_reward |  | 2.0 | 0.0 | 0.0 | 0.029470502775347775 |
| dqn_core_only |  | 2.0 | 0.0 | 0.0 | 0.015628333672005886 |
| rule_based |  | 2.0 | 0.0 | 0.0 | 0.03697186273592694 |
| random |  | 2.0 | 0.0 | 0.0 | 0.015757864711995077 |
| persistence |  | 2.0 | 0.0 | 0.0 | 0.015498830609446639 |

## Paired comparison (anchor = rule_based)