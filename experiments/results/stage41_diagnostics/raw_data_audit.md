# Stage 41 — Raw-data audit

Source: `experiments/results/paper_final_stage26/raw/` (80 runs, 4 controllers).

## Controllers and run counts

| Controller | n_runs |
|---|---:|
| `dqn_core_only` | 20 |
| `full_stack` | 20 |
| `random` | 20 |
| `rule_based` | 20 |

## Distribution of `n_faults`

| Controller | n | mean | std | min | median | max | 95 % CI |
|---|---:|---:|---:|---:|---:|---:|---|
| `dqn_core_only` | 20 | 3.0000 | 0.0000 | 3.0000 | 3.0000 | 3.0000 | [3.0000, 3.0000] |
| `full_stack` | 20 | 3.0000 | 0.0000 | 3.0000 | 3.0000 | 3.0000 | [3.0000, 3.0000] |
| `random` | 20 | 3.0000 | 0.0000 | 3.0000 | 3.0000 | 3.0000 | [3.0000, 3.0000] |
| `rule_based` | 20 | 3.0000 | 0.0000 | 3.0000 | 3.0000 | 3.0000 | [3.0000, 3.0000] |

## Distribution of `n_restored`

| Controller | n | mean | std | min | median | max | 95 % CI |
|---|---:|---:|---:|---:|---:|---:|---|
| `dqn_core_only` | 20 | 2.8500 | 0.3663 | 2.0000 | 3.0000 | 3.0000 | [2.6894, 3.0106] |
| `full_stack` | 20 | 2.8500 | 0.3663 | 2.0000 | 3.0000 | 3.0000 | [2.6894, 3.0106] |
| `random` | 20 | 2.8500 | 0.3663 | 2.0000 | 3.0000 | 3.0000 | [2.6894, 3.0106] |
| `rule_based` | 20 | 2.8500 | 0.3663 | 2.0000 | 3.0000 | 3.0000 | [2.6894, 3.0106] |

## Distribution of `restoration_rate`

| Controller | n | mean | std | min | median | max | 95 % CI |
|---|---:|---:|---:|---:|---:|---:|---|
| `dqn_core_only` | 20 | 0.9500 | 0.1221 | 0.6667 | 1.0000 | 1.0000 | [0.8965, 1.0035] |
| `full_stack` | 20 | 0.9500 | 0.1221 | 0.6667 | 1.0000 | 1.0000 | [0.8965, 1.0035] |
| `random` | 20 | 0.9500 | 0.1221 | 0.6667 | 1.0000 | 1.0000 | [0.8965, 1.0035] |
| `rule_based` | 20 | 0.9500 | 0.1221 | 0.6667 | 1.0000 | 1.0000 | [0.8965, 1.0035] |

## Distribution of `avg_restoration_steps`

| Controller | n | mean | std | min | median | max | 95 % CI |
|---|---:|---:|---:|---:|---:|---:|---|
| `dqn_core_only` | 20 | 4.8000 | 0.8813 | 4.0000 | 4.6667 | 7.0000 | [4.4138, 5.1862] |
| `full_stack` | 20 | 4.8000 | 0.8813 | 4.0000 | 4.6667 | 7.0000 | [4.4138, 5.1862] |
| `random` | 20 | 4.8000 | 0.8813 | 4.0000 | 4.6667 | 7.0000 | [4.4138, 5.1862] |
| `rule_based` | 20 | 4.8000 | 0.8813 | 4.0000 | 4.6667 | 7.0000 | [4.4138, 5.1862] |

## Distribution of `actions_taken`

| Controller | n | mean | std | min | median | max | 95 % CI |
|---|---:|---:|---:|---:|---:|---:|---|
| `dqn_core_only` | 20 | 80.0000 | 0.0000 | 80.0000 | 80.0000 | 80.0000 | [80.0000, 80.0000] |
| `full_stack` | 20 | 80.0000 | 0.0000 | 80.0000 | 80.0000 | 80.0000 | [80.0000, 80.0000] |
| `random` | 20 | 80.0000 | 0.0000 | 80.0000 | 80.0000 | 80.0000 | [80.0000, 80.0000] |
| `rule_based` | 20 | 80.0000 | 0.0000 | 80.0000 | 80.0000 | 80.0000 | [80.0000, 80.0000] |

## Distribution of `voltage_violation_count`

| Controller | n | mean | std | min | median | max | 95 % CI |
|---|---:|---:|---:|---:|---:|---:|---|
| `dqn_core_only` | 20 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] |
| `full_stack` | 20 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] |
| `random` | 20 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] |
| `rule_based` | 20 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] |

## Distribution of `critical_load_interruption_steps`

| Controller | n | mean | std | min | median | max | 95 % CI |
|---|---:|---:|---:|---:|---:|---:|---|
| `dqn_core_only` | 20 | 0.5000 | 1.0513 | 0.0000 | 0.0000 | 3.0000 | [0.0392, 0.9608] |
| `full_stack` | 20 | 0.5000 | 1.0513 | 0.0000 | 0.0000 | 3.0000 | [0.0392, 0.9608] |
| `random` | 20 | 0.5000 | 1.0513 | 0.0000 | 0.0000 | 3.0000 | [0.0392, 0.9608] |
| `rule_based` | 20 | 0.5000 | 1.0513 | 0.0000 | 0.0000 | 3.0000 | [0.0392, 0.9608] |

## Distribution of `total_customer_minutes_interrupted`

| Controller | n | mean | std | min | median | max | 95 % CI |
|---|---:|---:|---:|---:|---:|---:|---|
| `dqn_core_only` | 20 | 44.4760 | 33.0458 | 7.7899 | 37.0937 | 123.6611 | [29.9931, 58.9590] |
| `full_stack` | 20 | 80.6373 | 46.1898 | 25.2536 | 81.2493 | 181.2432 | [60.3937, 100.8808] |
| `random` | 20 | 80.5983 | 43.5384 | 21.3970 | 86.3736 | 159.5766 | [61.5168, 99.6799] |
| `rule_based` | 20 | 81.2934 | 43.3734 | 19.0329 | 79.7241 | 155.7884 | [62.2842, 100.3026] |

## Distribution of `energy_not_served_mwh`

| Controller | n | mean | std | min | median | max | 95 % CI |
|---|---:|---:|---:|---:|---:|---:|---|
| `dqn_core_only` | 20 | 0.7413 | 0.5508 | 0.1298 | 0.6182 | 2.0610 | [0.4999, 0.9826] |
| `full_stack` | 20 | 1.3440 | 0.7698 | 0.4209 | 1.3542 | 3.0207 | [1.0066, 1.6813] |
| `random` | 20 | 1.3433 | 0.7256 | 0.3566 | 1.4396 | 2.6596 | [1.0253, 1.6613] |
| `rule_based` | 20 | 1.3549 | 0.7229 | 0.3172 | 1.3287 | 2.5965 | [1.0381, 1.6717] |

## Distribution of `n_steps`

| Controller | n | mean | std | min | median | max | 95 % CI |
|---|---:|---:|---:|---:|---:|---:|---|
| `dqn_core_only` | 20 | 80.0000 | 0.0000 | 80.0000 | 80.0000 | 80.0000 | [80.0000, 80.0000] |
| `full_stack` | 20 | 80.0000 | 0.0000 | 80.0000 | 80.0000 | 80.0000 | [80.0000, 80.0000] |
| `random` | 20 | 80.0000 | 0.0000 | 80.0000 | 80.0000 | 80.0000 | [80.0000, 80.0000] |
| `rule_based` | 20 | 80.0000 | 0.0000 | 80.0000 | 80.0000 | 80.0000 | [80.0000, 80.0000] |

## Saturation flags (zero variance)

If a metric has zero variance across all 20 runs of a controller, it cannot differentiate controllers.

| Controller | Metric | std | min == max? |
|---|---|---:|---|
| `dqn_core_only` | `n_faults` | 0.0000 | yes |
| `dqn_core_only` | `n_restored` | 0.3663 | no |
| `dqn_core_only` | `restoration_rate` | 0.1221 | no |
| `dqn_core_only` | `avg_restoration_steps` | 0.8813 | no |
| `dqn_core_only` | `actions_taken` | 0.0000 | yes |
| `dqn_core_only` | `voltage_violation_count` | 0.0000 | yes |
| `dqn_core_only` | `critical_load_interruption_steps` | 1.0513 | no |
| `dqn_core_only` | `total_customer_minutes_interrupted` | 33.0458 | no |
| `dqn_core_only` | `energy_not_served_mwh` | 0.5508 | no |
| `dqn_core_only` | `n_steps` | 0.0000 | yes |
| `full_stack` | `n_faults` | 0.0000 | yes |
| `full_stack` | `n_restored` | 0.3663 | no |
| `full_stack` | `restoration_rate` | 0.1221 | no |
| `full_stack` | `avg_restoration_steps` | 0.8813 | no |
| `full_stack` | `actions_taken` | 0.0000 | yes |
| `full_stack` | `voltage_violation_count` | 0.0000 | yes |
| `full_stack` | `critical_load_interruption_steps` | 1.0513 | no |
| `full_stack` | `total_customer_minutes_interrupted` | 46.1898 | no |
| `full_stack` | `energy_not_served_mwh` | 0.7698 | no |
| `full_stack` | `n_steps` | 0.0000 | yes |
| `random` | `n_faults` | 0.0000 | yes |
| `random` | `n_restored` | 0.3663 | no |
| `random` | `restoration_rate` | 0.1221 | no |
| `random` | `avg_restoration_steps` | 0.8813 | no |
| `random` | `actions_taken` | 0.0000 | yes |
| `random` | `voltage_violation_count` | 0.0000 | yes |
| `random` | `critical_load_interruption_steps` | 1.0513 | no |
| `random` | `total_customer_minutes_interrupted` | 43.5384 | no |
| `random` | `energy_not_served_mwh` | 0.7256 | no |
| `random` | `n_steps` | 0.0000 | yes |
| `rule_based` | `n_faults` | 0.0000 | yes |
| `rule_based` | `n_restored` | 0.3663 | no |
| `rule_based` | `restoration_rate` | 0.1221 | no |
| `rule_based` | `avg_restoration_steps` | 0.8813 | no |
| `rule_based` | `actions_taken` | 0.0000 | yes |
| `rule_based` | `voltage_violation_count` | 0.0000 | yes |
| `rule_based` | `critical_load_interruption_steps` | 1.0513 | no |
| `rule_based` | `total_customer_minutes_interrupted` | 43.3734 | no |
| `rule_based` | `energy_not_served_mwh` | 0.7229 | no |
| `rule_based` | `n_steps` | 0.0000 | yes |

## Outlier report (> 3 SD)

| Controller | Metric | n_outliers | values |
|---|---|---:|---|