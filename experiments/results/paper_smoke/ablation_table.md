# Ablation table

## Per-policy summary
| controller_label | weather_mode | n_faults_mean | restoration_rate_mean | voltage_violation_count_mean | energy_not_served_mwh_mean |
|---|---|---|---|---|---|
| full_stack |  | 2.0 | 0.0 | 0.0 | 0.41197653170059184 |
| no_lstm |  | 2.0 | 0.0 | 0.0 | 0.43974845226733517 |
| no_twin |  | 2.0 | 0.0 | 0.0 | 0.40658284060375244 |
| no_predictive |  | 2.0 | 0.0 | 0.0 | 0.36391129502094843 |
| no_reward |  | 2.0 | 0.0 | 0.0 | 0.4149085970113311 |
| dqn_core_only |  | 2.0 | 0.0 | 0.0 | 0.25268507404167295 |
| rule_based |  | 2.0 | 0.0 | 0.0 | 0.4324890187223254 |
| random |  | 2.0 | 0.0 | 0.0 | 0.34977247132517925 |
| persistence |  | 2.0 | 0.0 | 0.0 | 0.40934027544076373 |

## Paired comparison (anchor = rule_based)