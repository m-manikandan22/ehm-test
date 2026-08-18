# EHM-simulation — Research Tables

_Generated from `experiments.tables`._

## Run summary

- Total runs: **600**, valid: **600** (100.0 %).
- Anchor policy for paired comparison: `full_stack`.

## Per-policy summary

Mean ± std over all valid runs of each configuration. Cells with `n=0` mean the metric was not produced for that policy.

| Policy | n | Active modules | Disabled modules | SAIFI (faults/node) | SAIDI (steps) | MAIFI (events/node) | ASAI | ENS (step·count) | Avg restoration (steps) | Critical-load restored (%) | Successful restorations | Islands | Isolated nodes | Actions taken | Switching operations | Illegal actions | Load-shedding events | Battery dispatches | Voltage violations | Frequency deviations | Line overloads | Vmin (pu) | Vmax (pu) | Vavg (pu) | Operating cost (USD) | Outage cost (USD) | Carbon (kg) | Run time (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `dqn_core_only` | 100 | dqn, flisr | lstm, digital_twin, predictive_healing, reward_shaping, ems, storage, xai | 0.061 ± 0.000 | 0.000 ± 0.000 | 197.300 ± 4.480 | -2.000 ± 0.000 | 30.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 200.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 12.870 ± 41.130 | 9667.700 ± 219.522 | 5.540 ± 6.428 | 0.855 ± 0.286 | 1.000 ± 0.000 | 0.959 ± 0.006 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.586 ± 0.104 |
| `full_stack` | 100 | dqn, lstm, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | — | 0.061 ± 0.000 | 0.000 ± 0.000 | 197.300 ± 4.480 | -2.000 ± 0.000 | 30.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 200.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 12.870 ± 41.130 | 9667.700 ± 219.522 | 5.540 ± 6.428 | 0.855 ± 0.286 | 1.000 ± 0.000 | 0.959 ± 0.006 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.515 ± 0.102 |
| `no_lstm` | 100 | dqn, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | lstm | 0.061 ± 0.000 | 0.000 ± 0.000 | 197.300 ± 4.480 | -2.000 ± 0.000 | 30.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 200.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 12.870 ± 41.130 | 9667.700 ± 219.522 | 5.540 ± 6.428 | 0.855 ± 0.286 | 1.000 ± 0.000 | 0.959 ± 0.006 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.531 ± 0.082 |
| `no_predictive` | 100 | dqn, lstm, digital_twin, reward_shaping, flisr, ems, storage, xai | predictive_healing | 0.061 ± 0.000 | 0.000 ± 0.000 | 197.300 ± 4.480 | -2.000 ± 0.000 | 30.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 200.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 12.870 ± 41.130 | 9667.700 ± 219.522 | 5.540 ± 6.428 | 0.855 ± 0.286 | 1.000 ± 0.000 | 0.959 ± 0.006 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.386 ± 0.093 |
| `no_reward` | 100 | dqn, lstm, digital_twin, predictive_healing, flisr, ems, storage, xai | reward_shaping | 0.061 ± 0.000 | 0.000 ± 0.000 | 197.300 ± 4.480 | -2.000 ± 0.000 | 30.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 200.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 12.870 ± 41.130 | 9667.700 ± 219.522 | 5.540 ± 6.428 | 0.855 ± 0.286 | 1.000 ± 0.000 | 0.959 ± 0.006 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.666 ± 0.144 |
| `no_twin` | 100 | dqn, lstm, predictive_healing, reward_shaping, flisr, ems, storage, xai | digital_twin | 0.061 ± 0.000 | 0.000 ± 0.000 | 197.300 ± 4.480 | -2.000 ± 0.000 | 30.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 200.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 12.870 ± 41.130 | 9667.700 ± 219.522 | 5.540 ± 6.428 | 0.855 ± 0.286 | 1.000 ± 0.000 | 0.959 ± 0.006 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.531 ± 0.101 |

## Paired comparison vs `full_stack`

Each row is a paired test on (anchor, other) matched by (seed, weather). `d` is Cohen's d (paired); positive `mean_diff` means anchor > other for that metric.

| Other | Metric | n | mean_diff | t | p(t) | Wilcoxon p | Cohen's d | Effect | Sig@0.05 |
|---|---|---|---|---|---|---|---|---|---|
| `dqn_core_only` | `saifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `saidi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `maifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `asai` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `ens` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `dqn_core_only` | `critical_load_restored_pct` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `successful_restoration_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `number_of_islands` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `isolated_nodes` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `actions_taken` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `switching_operations` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `illegal_actions_attempted` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `load_shedding_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `battery_dispatch_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `voltage_violation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `frequency_deviation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `line_overload_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `minimum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `maximum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `average_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `operating_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `outage_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `carbon_kg` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `runtime_s` | 100 | -0.0715 | -4.808 | 0.0000 | 0.0261 | -0.481 | small | yes |
| `no_lstm` | `saifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `saidi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `maifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `asai` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `ens` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `no_lstm` | `critical_load_restored_pct` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `successful_restoration_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `number_of_islands` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `isolated_nodes` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `actions_taken` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `switching_operations` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `illegal_actions_attempted` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `load_shedding_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `battery_dispatch_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `voltage_violation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `frequency_deviation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `line_overload_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `minimum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `maximum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `average_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `operating_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `outage_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `carbon_kg` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `runtime_s` | 100 | -0.0168 | -1.300 | 0.1960 | 0.3910 | -0.130 | negligible | no |
| `no_predictive` | `saifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `saidi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `maifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `asai` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `ens` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `no_predictive` | `critical_load_restored_pct` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `successful_restoration_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `number_of_islands` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `isolated_nodes` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `actions_taken` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `switching_operations` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `illegal_actions_attempted` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `load_shedding_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `battery_dispatch_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `voltage_violation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `frequency_deviation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `line_overload_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `minimum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `maximum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `average_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `operating_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `outage_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `carbon_kg` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `runtime_s` | 100 | 0.1287 | 9.453 | 0.0000 | 0.0000 | 0.945 | large | yes |
| `no_reward` | `saifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `saidi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `maifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `asai` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `ens` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `no_reward` | `critical_load_restored_pct` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `successful_restoration_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `number_of_islands` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `isolated_nodes` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `actions_taken` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `switching_operations` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `illegal_actions_attempted` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `load_shedding_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `battery_dispatch_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `voltage_violation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `frequency_deviation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `line_overload_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `minimum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `maximum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `average_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `operating_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `outage_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `carbon_kg` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_reward` | `runtime_s` | 100 | -0.1510 | -8.711 | 0.0000 | 0.0000 | -0.871 | large | yes |
| `no_twin` | `saifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `saidi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `maifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `asai` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `ens` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `no_twin` | `critical_load_restored_pct` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `successful_restoration_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `number_of_islands` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `isolated_nodes` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `actions_taken` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `switching_operations` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `illegal_actions_attempted` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `load_shedding_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `battery_dispatch_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `voltage_violation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `frequency_deviation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `line_overload_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `minimum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `maximum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `average_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `operating_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `outage_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `carbon_kg` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `runtime_s` | 100 | -0.0162 | -1.081 | 0.2823 | 0.4852 | -0.108 | negligible | no |
