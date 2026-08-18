# Statistics

## Baseline (per-policy)

```json
[
  {
    "controller_label": "random",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.4534948515845336,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 27.209691095072007,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "rule_based",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.3966704142567185,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 23.800224855403076,
    "voltage_violation_count_mean": 0.0
  }
]
```

## Ablation (per-policy)

```json
[
  {
    "controller_label": "full_stack",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.41197653170059184,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 24.718591902035485,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_lstm",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.43974845226733517,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 26.38490713604008,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_twin",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.40658284060375244,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 24.394970436225147,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_predictive",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.36391129502094843,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 21.834677701256904,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_reward",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.4149085970113311,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 24.894515820679874,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "dqn_core_only",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.25268507404167295,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 15.161104442500365,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "rule_based",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.4324890187223254,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 25.949341123339533,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "random",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.34977247132517925,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 20.986348279510764,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "persistence",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 4.666666666666667,
    "energy_not_served_mwh_mean": 0.40934027544076373,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 2.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 24.560416526445774,
    "voltage_violation_count_mean": 0.0
  }
]
```
