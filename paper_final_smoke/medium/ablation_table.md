# Ablation table

## Per-policy summary
| controller_label | weather_mode | n_faults_mean | restoration_rate_mean | voltage_violation_count_mean | energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| full_stack |  | 4.0 | 0.0 | 0.0 | 0.7510931362670981 |
| no_lstm |  | 4.0 | 0.0 | 0.0 | 0.6548562952566889 |
| no_twin |  | 4.0 | 0.0 | 0.0 | 0.651405777025004 |
| no_predictive |  | 4.0 | 0.0 | 0.0 | 0.7477578227663141 |
| no_reward |  | 4.0 | 0.0 | 0.0 | 0.7884899706617948 |
| dqn_core_only |  | 4.0 | 0.0 | 0.0 | 0.45205929234860287 |
| rule_based |  | 4.0 | 0.0 | 0.0 | 0.6611913639375996 |
| random |  | 4.0 | 0.0 | 0.0 | 0.6872342698773942 |
| persistence |  | 4.0 | 0.0 | 0.0 | 0.7683624179865544 |

## Paired comparison (anchor = rule_based)