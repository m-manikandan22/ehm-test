# Statistics

## Baseline (per-policy)

```json
[
  {
    "controller_label": "random",
    "n_total_runs": 5,
    "n_valid_runs": 5,
    "actions_taken_mean": 50.0,
    "critical_load_interruption_steps_mean": 0.4,
    "energy_not_served_mwh_mean": 1.5916936683019114,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 5.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 50.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 95.50162009811467,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "rule_based",
    "n_total_runs": 5,
    "n_valid_runs": 5,
    "actions_taken_mean": 50.0,
    "critical_load_interruption_steps_mean": 0.4,
    "energy_not_served_mwh_mean": 1.5509790916976296,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 5.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 50.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 93.05874550185774,
    "voltage_violation_count_mean": 0.0
  }
]
```

## Ablation (per-policy)

```json
[
  {
    "controller_label": "full_stack",
    "n_total_runs": 5,
    "n_valid_runs": 5,
    "actions_taken_mean": 50.0,
    "critical_load_interruption_steps_mean": 0.4,
    "energy_not_served_mwh_mean": 1.666715968605154,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 5.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 50.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 100.00295811630927,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_lstm",
    "n_total_runs": 5,
    "n_valid_runs": 5,
    "actions_taken_mean": 50.0,
    "critical_load_interruption_steps_mean": 0.4,
    "energy_not_served_mwh_mean": 1.7558902626134416,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 5.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 50.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 105.35341575680641,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_twin",
    "n_total_runs": 5,
    "n_valid_runs": 5,
    "actions_taken_mean": 50.0,
    "critical_load_interruption_steps_mean": 0.4,
    "energy_not_served_mwh_mean": 1.5973693463882086,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 5.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 50.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 95.84216078329247,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_predictive",
    "n_total_runs": 5,
    "n_valid_runs": 5,
    "actions_taken_mean": 50.0,
    "critical_load_interruption_steps_mean": 0.4,
    "energy_not_served_mwh_mean": 1.5523657469971963,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 5.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 50.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 93.1419448198319,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_reward",
    "n_total_runs": 5,
    "n_valid_runs": 5,
    "actions_taken_mean": 50.0,
    "critical_load_interruption_steps_mean": 0.4,
    "energy_not_served_mwh_mean": 1.607683259780302,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 5.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 50.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 96.46099558681802,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "dqn_core_only",
    "n_total_runs": 5,
    "n_valid_runs": 5,
    "actions_taken_mean": 50.0,
    "critical_load_interruption_steps_mean": 0.4,
    "energy_not_served_mwh_mean": 0.9030777952628745,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 5.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 50.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 54.18466771577238,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "rule_based",
    "n_total_runs": 5,
    "n_valid_runs": 5,
    "actions_taken_mean": 50.0,
    "critical_load_interruption_steps_mean": 0.4,
    "energy_not_served_mwh_mean": 1.6427783513245473,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 5.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 50.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 98.56670107947267,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "random",
    "n_total_runs": 5,
    "n_valid_runs": 5,
    "actions_taken_mean": 50.0,
    "critical_load_interruption_steps_mean": 0.4,
    "energy_not_served_mwh_mean": 1.5094255754085542,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 5.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 50.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 90.56553452451308,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "persistence",
    "n_total_runs": 5,
    "n_valid_runs": 5,
    "actions_taken_mean": 50.0,
    "critical_load_interruption_steps_mean": 16.0,
    "energy_not_served_mwh_mean": 1.6030029894618878,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 5.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 50.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 96.18017936771327,
    "voltage_violation_count_mean": 0.0
  }
]
```
