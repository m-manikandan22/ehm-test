# EHM-simulation — Research Tables

_Generated from `experiments.tables`._

## Run summary

- Total runs: **500**, valid: **500** (100.0 %).
- Anchor policy for paired comparison: `rule_based`.

## Per-policy summary

Mean ± std over all valid runs of each configuration. Cells with `n=0` mean the metric was not produced for that policy.

| Policy | n | Active modules | Disabled modules | SAIFI (faults/node) | SAIDI (steps) | MAIFI (events/node) | ASAI | ENS (step·count) | Avg restoration (steps) | Critical-load restored (%) | Successful restorations | Islands | Isolated nodes | Actions taken | Switching operations | Illegal actions | Load-shedding events | Battery dispatches | Voltage violations | Frequency deviations | Line overloads | Vmin (pu) | Vmax (pu) | Vavg (pu) | Operating cost (USD) | Outage cost (USD) | Carbon (kg) | Run time (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `dqn_core_only` | 100 | dqn, flisr | lstm, digital_twin, predictive_healing, reward_shaping, ems, storage, xai | 0.061 ± 0.000 | 0.000 ± 0.000 | 197.300 ± 4.480 | -2.000 ± 0.000 | 30.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 200.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 12.870 ± 41.130 | 9667.700 ± 219.522 | 5.540 ± 6.428 | 0.855 ± 0.286 | 1.000 ± 0.000 | 0.959 ± 0.006 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.391 ± 0.090 |
| `full_stack` | 100 | dqn, lstm, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | — | 0.061 ± 0.000 | 0.000 ± 0.000 | 197.300 ± 4.480 | -2.000 ± 0.000 | 30.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 200.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 12.870 ± 41.130 | 9667.700 ± 219.522 | 5.540 ± 6.428 | 0.855 ± 0.286 | 1.000 ± 0.000 | 0.959 ± 0.006 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.570 ± 0.124 |
| `persistence` | 100 | — | dqn, lstm, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | 0.061 ± 0.000 | 0.000 ± 0.000 | 196.530 ± 6.084 | -2.000 ± 0.000 | 30.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 12.870 ± 41.130 | 9629.970 ± 298.133 | 5.470 ± 6.322 | 0.855 ± 0.286 | 1.000 ± 0.000 | 0.959 ± 0.006 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.172 ± 0.083 |
| `random` | 100 | — | dqn, lstm, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | 0.061 ± 0.000 | 0.000 ± 0.000 | 196.530 ± 6.084 | -2.000 ± 0.000 | 30.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 200.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 12.870 ± 41.130 | 9629.970 ± 298.133 | 5.470 ± 6.322 | 0.855 ± 0.286 | 1.000 ± 0.000 | 0.959 ± 0.006 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.103 ± 0.212 |
| `rule_based` | 100 | flisr | dqn, lstm, digital_twin, predictive_healing, reward_shaping, ems, storage, xai | 0.061 ± 0.000 | 0.000 ± 0.000 | 196.530 ± 6.084 | -2.000 ± 0.000 | 30.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 200.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 12.870 ± 41.130 | 9629.970 ± 298.133 | 5.470 ± 6.322 | 0.855 ± 0.286 | 1.000 ± 0.000 | 0.959 ± 0.006 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.200 ± 0.090 |

## Paired comparison vs `rule_based`

Each row is a paired test on (anchor, other) matched by (seed, weather). `d` is Cohen's d (paired); positive `mean_diff` means anchor > other for that metric.

| Other | Metric | n | mean_diff | t | p(t) | Wilcoxon p | Cohen's d | Effect | Sig@0.05 |
|---|---|---|---|---|---|---|---|---|---|
| `dqn_core_only` | `saifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `saidi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `maifi` | 100 | -0.7700 | -1.468 | 0.1441 | 0.1705 | -0.147 | negligible | no |
| `dqn_core_only` | `asai` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `ens` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `dqn_core_only` | `critical_load_restored_pct` | 100 | -0.0000 | -0.332 | 0.7413 | 0.7577 | -0.033 | negligible | no |
| `dqn_core_only` | `successful_restoration_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `number_of_islands` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `isolated_nodes` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `actions_taken` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `switching_operations` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `illegal_actions_attempted` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `load_shedding_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `battery_dispatch_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `voltage_violation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `frequency_deviation_count` | 100 | -37.7300 | -1.468 | 0.1441 | 0.1705 | -0.147 | negligible | no |
| `dqn_core_only` | `line_overload_count` | 100 | -0.0700 | -0.192 | 0.8489 | 0.8857 | -0.019 | negligible | no |
| `dqn_core_only` | `minimum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `maximum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `average_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `operating_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `outage_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `carbon_kg` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `runtime_s` | 100 | -0.1907 | -13.889 | 0.0000 | 0.0000 | -1.389 | large | yes |
| `full_stack` | `saifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `saidi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `maifi` | 100 | -0.7700 | -1.468 | 0.1441 | 0.1705 | -0.147 | negligible | no |
| `full_stack` | `asai` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `ens` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `full_stack` | `critical_load_restored_pct` | 100 | -0.0000 | -0.332 | 0.7413 | 0.7577 | -0.033 | negligible | no |
| `full_stack` | `successful_restoration_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `number_of_islands` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `isolated_nodes` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `actions_taken` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `switching_operations` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `illegal_actions_attempted` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `load_shedding_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `battery_dispatch_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `voltage_violation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `frequency_deviation_count` | 100 | -37.7300 | -1.468 | 0.1441 | 0.1705 | -0.147 | negligible | no |
| `full_stack` | `line_overload_count` | 100 | -0.0700 | -0.192 | 0.8489 | 0.8857 | -0.019 | negligible | no |
| `full_stack` | `minimum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `maximum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `average_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `operating_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `outage_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `carbon_kg` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `runtime_s` | 100 | -0.3703 | -23.685 | 0.0000 | 0.0000 | -2.369 | large | yes |
| `persistence` | `saifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `saidi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `maifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `asai` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `ens` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `persistence` | `critical_load_restored_pct` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `successful_restoration_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `number_of_islands` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `isolated_nodes` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `actions_taken` | 100 | 200.0000 | 0.000 | 1.0000 | 0.0000 | 0.000 | negligible | no |
| `persistence` | `switching_operations` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `illegal_actions_attempted` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `load_shedding_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `battery_dispatch_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `voltage_violation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `frequency_deviation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `line_overload_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `minimum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `maximum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `average_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `operating_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `outage_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `carbon_kg` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `persistence` | `runtime_s` | 100 | 0.0283 | 2.274 | 0.0237 | 0.3514 | 0.227 | small | yes |
| `random` | `saifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `saidi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `maifi` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `asai` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `ens` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `random` | `critical_load_restored_pct` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `successful_restoration_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `number_of_islands` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `isolated_nodes` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `actions_taken` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `switching_operations` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `illegal_actions_attempted` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `load_shedding_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `battery_dispatch_events` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `voltage_violation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `frequency_deviation_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `line_overload_count` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `minimum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `maximum_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `average_voltage_pu` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `operating_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `outage_cost_usd` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `carbon_kg` | 100 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `runtime_s` | 100 | 0.0967 | 4.485 | 0.0000 | 0.0000 | 0.449 | small | yes |
