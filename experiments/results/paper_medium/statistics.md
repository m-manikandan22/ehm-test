# Statistics

## Baseline (per-policy)

```json
[
  {
    "controller_label": "random",
    "n_total_runs": 10,
    "n_valid_runs": 10,
    "actions_taken_mean": 60.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.9979211169197765,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 60.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 59.875267015186544,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "rule_based",
    "n_total_runs": 10,
    "n_valid_runs": 10,
    "actions_taken_mean": 60.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 1.1916962247524305,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 60.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 71.50177348514589,
    "voltage_violation_count_mean": 0.0
  }
]
```

## Ablation (per-policy)

```json
[
  {
    "controller_label": "full_stack",
    "n_total_runs": 10,
    "n_valid_runs": 10,
    "actions_taken_mean": 60.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 1.0585896129508672,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 60.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 63.51537677705202,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_lstm",
    "n_total_runs": 10,
    "n_valid_runs": 10,
    "actions_taken_mean": 60.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 1.0818948158809938,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 60.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 64.91368895285957,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_twin",
    "n_total_runs": 10,
    "n_valid_runs": 10,
    "actions_taken_mean": 60.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 1.1203872466704456,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 60.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 67.22323480022673,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_predictive",
    "n_total_runs": 10,
    "n_valid_runs": 10,
    "actions_taken_mean": 60.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 1.1037283348173403,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 60.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 66.22370008904039,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_reward",
    "n_total_runs": 10,
    "n_valid_runs": 10,
    "actions_taken_mean": 60.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 1.0479605189154766,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 60.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 62.87763113492868,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "dqn_core_only",
    "n_total_runs": 10,
    "n_valid_runs": 10,
    "actions_taken_mean": 60.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.6349337930847618,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 60.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 38.096027585085665,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "rule_based",
    "n_total_runs": 10,
    "n_valid_runs": 10,
    "actions_taken_mean": 60.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 1.0621715470983695,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 60.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 63.73029282590225,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "random",
    "n_total_runs": 10,
    "n_valid_runs": 10,
    "actions_taken_mean": 60.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 1.0610585097912988,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 60.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 63.663510587477944,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "persistence",
    "n_total_runs": 10,
    "n_valid_runs": 10,
    "actions_taken_mean": 60.0,
    "critical_load_interruption_steps_mean": 1.2,
    "energy_not_served_mwh_mean": 1.0577839629879158,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 60.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 63.46703777927494,
    "voltage_violation_count_mean": 0.0
  }
]
```
