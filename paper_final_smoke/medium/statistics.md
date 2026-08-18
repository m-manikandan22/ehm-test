# Statistics

## Baseline (per-policy)

```json
[
  {
    "controller_label": "random",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.3333333333333333,
    "energy_not_served_mwh_mean": 0.6659730733676358,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 4.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 39.95838440205815,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "rule_based",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.3333333333333333,
    "energy_not_served_mwh_mean": 0.7190339803979381,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 4.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 43.142038823876256,
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
    "critical_load_interruption_steps_mean": 0.3333333333333333,
    "energy_not_served_mwh_mean": 0.7510931362670981,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 4.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 45.06558817602589,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_lstm",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.3333333333333333,
    "energy_not_served_mwh_mean": 0.6548562952566889,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 4.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 39.2913777154013,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_twin",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.3333333333333333,
    "energy_not_served_mwh_mean": 0.651405777025004,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 4.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 39.08434662150023,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_predictive",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.3333333333333333,
    "energy_not_served_mwh_mean": 0.7477578227663141,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 4.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 44.86546936597882,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "no_reward",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.3333333333333333,
    "energy_not_served_mwh_mean": 0.7884899706617948,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 4.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 47.30939823970768,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "dqn_core_only",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.3333333333333333,
    "energy_not_served_mwh_mean": 0.45205929234860287,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 4.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 27.12355754091617,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "rule_based",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.3333333333333333,
    "energy_not_served_mwh_mean": 0.6611913639375996,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 4.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 39.67148183625597,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "random",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 0.3333333333333333,
    "energy_not_served_mwh_mean": 0.6872342698773942,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 4.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 41.23405619264361,
    "voltage_violation_count_mean": 0.0
  },
  {
    "controller_label": "persistence",
    "n_total_runs": 3,
    "n_valid_runs": 3,
    "actions_taken_mean": 30.0,
    "critical_load_interruption_steps_mean": 8.333333333333334,
    "energy_not_served_mwh_mean": 0.7683624179865544,
    "illegal_actions_attempted_mean": 0.0,
    "n_faults_mean": 4.0,
    "n_restored_mean": 0.0,
    "n_steps_mean": 30.0,
    "restoration_rate_mean": 0.0,
    "total_customer_minutes_interrupted_mean": 46.10174507919324,
    "voltage_violation_count_mean": 0.0
  }
]
```
