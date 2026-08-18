# Statistics

## Baseline (per-policy)

```json
[
  {
    "controller_label": "random",
    "n_total_runs": 1,
    "n_valid_runs": 1,
    "actions_taken_mean": 10.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.02524861434326258,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 10.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 1.514916860595755,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "rule_based",
    "n_total_runs": 1,
    "n_valid_runs": 1,
    "actions_taken_mean": 10.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.02953659743338227,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 10.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 1.7721958460029361,
    "voltage_violation_count_mean": 0.0
  }
]
```

## Ablation (per-policy)

```json
[
  {
    "controller_label": "full_stack",
    "n_total_runs": 1,
    "n_valid_runs": 1,
    "actions_taken_mean": 10.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.04636124310739201,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 10.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 2.7816745864435206,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_lstm",
    "n_total_runs": 1,
    "n_valid_runs": 1,
    "actions_taken_mean": 10.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.027520520351166738,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 10.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 1.6512312210700046,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_twin",
    "n_total_runs": 1,
    "n_valid_runs": 1,
    "actions_taken_mean": 10.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.0410909822845754,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 10.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 2.4654589370745246,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_predictive",
    "n_total_runs": 1,
    "n_valid_runs": 1,
    "actions_taken_mean": 10.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.03435111176654692,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 10.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 2.061066705992815,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_reward",
    "n_total_runs": 1,
    "n_valid_runs": 1,
    "actions_taken_mean": 10.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.029470502775347775,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 10.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 1.7682301665208666,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "dqn_core_only",
    "n_total_runs": 1,
    "n_valid_runs": 1,
    "actions_taken_mean": 10.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.015628333672005886,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 10.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 0.9377000203203532,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "rule_based",
    "n_total_runs": 1,
    "n_valid_runs": 1,
    "actions_taken_mean": 10.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.03697186273592694,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 10.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 2.2183117641556165,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "random",
    "n_total_runs": 1,
    "n_valid_runs": 1,
    "actions_taken_mean": 10.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.015757864711995077,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 10.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 0.9454718827197047,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "persistence",
    "n_total_runs": 1,
    "n_valid_runs": 1,
    "actions_taken_mean": 10.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.015498830609446639,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 10.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 0.9299298365667983,
    "voltage_violation_count_mean": 0.0
  }
]
```
