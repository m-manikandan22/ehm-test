# Statistics

## Baseline (per-policy)

```json
[
  {
    "controller_label": "random",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 20.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.2741199720814627,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 20.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 16.447198324887758,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "rule_based",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 20.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.3842642121774003,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 20.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 23.055852730644006,
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
    "actions_taken_mean": 20.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.33604863355042563,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 20.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 20.162918013025543,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_lstm",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 20.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.3746489056127497,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 20.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 22.478934336764983,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_twin",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 20.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.3735492639413203,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 20.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 22.412955836479227,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_predictive",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 20.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.3656034502985503,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 20.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 21.936207017913024,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_reward",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 20.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.34907554990135387,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 20.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 20.944532994081243,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "dqn_core_only",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 20.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.2074770876687132,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 20.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 12.448625260122789,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "rule_based",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 20.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.3476908487050103,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 20.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 20.861450922300627,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "random",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 20.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.27750243721989193,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 20.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 16.65014623319352,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "persistence",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 20.0,
    "critical_load_interruption_steps_mean": 0.0,
    "energy_not_served_mwh_mean": 0.26570357703521924,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 3.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 20.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 15.94221462211315,
    "voltage_violation_count_mean": 0.0
  }
]
```
