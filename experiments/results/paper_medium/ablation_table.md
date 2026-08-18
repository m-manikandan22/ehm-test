# Ablation table

## Per-policy summary
| controller_label | weather_mode | n_faults_mean | restoration_rate_mean | voltage_violation_count_mean | energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| full_stack |  | 3.0 | 0.0 | 0.0 | 1.0585896129508672 |
| no_lstm |  | 3.0 | 0.0 | 0.0 | 1.0818948158809938 |
| no_twin |  | 3.0 | 0.0 | 0.0 | 1.1203872466704456 |
| no_predictive |  | 3.0 | 0.0 | 0.0 | 1.1037283348173403 |
| no_reward |  | 3.0 | 0.0 | 0.0 | 1.0479605189154766 |
| dqn_core_only |  | 3.0 | 0.0 | 0.0 | 0.6349337930847618 |
| rule_based |  | 3.0 | 0.0 | 0.0 | 1.0621715470983695 |
| random |  | 3.0 | 0.0 | 0.0 | 1.0610585097912988 |
| persistence |  | 3.0 | 0.0 | 0.0 | 1.0577839629879158 |

## Paired comparison (anchor = rule_based)