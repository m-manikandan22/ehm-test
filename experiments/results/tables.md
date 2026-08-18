# EHM-simulation — Research Tables

_Generated from `experiments.tables`._

## Run summary

- Total runs: **12**, valid: **12** (100.0 %).
- Anchor policy for paired comparison: `rule_based`.

## Per-policy summary

Mean ± std over all valid runs of each configuration. Cells with `n=0` mean the metric was not produced for that policy.

| Policy | n | Active modules | Disabled modules | SAIFI (faults/node) | SAIDI (steps) | MAIFI (events/node) | ASAI | ENS (step·count) | Avg restoration (steps) | Critical-load restored (%) | Successful restorations | Islands | Isolated nodes | Actions taken | Switching operations | Illegal actions | Load-shedding events | Battery dispatches | Voltage violations | Frequency deviations | Line overloads | Vmin (pu) | Vmax (pu) | Vavg (pu) | Operating cost (USD) | Outage cost (USD) | Carbon (kg) | Run time (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `dqn_core_only` | 2 | dqn, flisr | lstm, digital_twin, predictive_healing, reward_shaping, ems, storage, xai | 0.020 ± 0.000 | 0.000 ± 0.000 | 15.000 ± 0.000 | 0.000 ± 0.000 | 10.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 15.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 735.000 ± 0.000 | 0.000 ± 0.000 | 0.950 ± 0.000 | 1.000 ± 0.000 | 0.961 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.053 ± 0.007 |
| `full_stack` | 2 | dqn, lstm, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | — | 0.020 ± 0.000 | 0.000 ± 0.000 | 15.000 ± 0.000 | 0.000 ± 0.000 | 10.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 15.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 735.000 ± 0.000 | 0.000 ± 0.000 | 0.950 ± 0.000 | 1.000 ± 0.000 | 0.961 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.109 ± 0.073 |
| `no_lstm` | 2 | dqn, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | lstm | 0.020 ± 0.000 | 0.000 ± 0.000 | 15.000 ± 0.000 | 0.000 ± 0.000 | 10.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 15.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 735.000 ± 0.000 | 0.000 ± 0.000 | 0.950 ± 0.000 | 1.000 ± 0.000 | 0.961 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.052 ± 0.002 |
| `no_predictive` | 2 | dqn, lstm, digital_twin, reward_shaping, flisr, ems, storage, xai | predictive_healing | 0.020 ± 0.000 | 0.000 ± 0.000 | 15.000 ± 0.000 | 0.000 ± 0.000 | 10.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 15.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 735.000 ± 0.000 | 0.000 ± 0.000 | 0.950 ± 0.000 | 1.000 ± 0.000 | 0.961 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.051 ± 0.005 |
| `random` | 2 | — | dqn, lstm, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | 0.020 ± 0.000 | 0.000 ± 0.000 | 15.000 ± 0.000 | 0.000 ± 0.000 | 10.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 15.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 735.000 ± 0.000 | 0.000 ± 0.000 | 0.950 ± 0.000 | 1.000 ± 0.000 | 0.961 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.040 ± 0.003 |
| `rule_based` | 2 | flisr | dqn, lstm, digital_twin, predictive_healing, reward_shaping, ems, storage, xai | 0.020 ± 0.000 | 0.000 ± 0.000 | 15.000 ± 0.000 | 0.000 ± 0.000 | 10.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 15.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 735.000 ± 0.000 | 0.000 ± 0.000 | 0.950 ± 0.000 | 1.000 ± 0.000 | 0.961 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.055 ± 0.014 |

## Paired comparison vs `rule_based`

Each row is a paired test on (anchor, other) matched by (seed, weather). `d` is Cohen's d (paired); positive `mean_diff` means anchor > other for that metric.

| Other | Metric | n | mean_diff | t | p(t) | Wilcoxon p | Cohen's d | Effect | Sig@0.05 |
|---|---|---|---|---|---|---|---|---|---|
| `dqn_core_only` | `saifi` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `saidi` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `maifi` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `asai` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `ens` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `dqn_core_only` | `critical_load_restored_pct` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `successful_restoration_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `number_of_islands` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `isolated_nodes` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `actions_taken` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `switching_operations` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `illegal_actions_attempted` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `load_shedding_events` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `battery_dispatch_events` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `voltage_violation_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `frequency_deviation_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `line_overload_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `minimum_voltage_pu` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `maximum_voltage_pu` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `average_voltage_pu` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `operating_cost_usd` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `outage_cost_usd` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `carbon_kg` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `dqn_core_only` | `runtime_s` | 2 | 0.0016 | 0.333 | 0.8137 | 0.6547 | 0.236 | small | no |
| `full_stack` | `saifi` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `saidi` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `maifi` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `asai` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `ens` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `full_stack` | `critical_load_restored_pct` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `successful_restoration_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `number_of_islands` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `isolated_nodes` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `actions_taken` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `switching_operations` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `illegal_actions_attempted` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `load_shedding_events` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `battery_dispatch_events` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `voltage_violation_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `frequency_deviation_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `line_overload_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `minimum_voltage_pu` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `maximum_voltage_pu` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `average_voltage_pu` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `operating_cost_usd` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `outage_cost_usd` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `carbon_kg` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `full_stack` | `runtime_s` | 2 | -0.0541 | -1.282 | 0.3645 | 0.1797 | -0.907 | large | no |
| `no_lstm` | `saifi` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `saidi` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `maifi` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `asai` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `ens` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `no_lstm` | `critical_load_restored_pct` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `successful_restoration_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `number_of_islands` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `isolated_nodes` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `actions_taken` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `switching_operations` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `illegal_actions_attempted` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `load_shedding_events` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `battery_dispatch_events` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `voltage_violation_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `frequency_deviation_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `line_overload_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `minimum_voltage_pu` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `maximum_voltage_pu` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `average_voltage_pu` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `operating_cost_usd` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `outage_cost_usd` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `carbon_kg` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `runtime_s` | 2 | 0.0029 | 0.362 | 0.7980 | 0.6547 | 0.256 | small | no |
| `no_predictive` | `saifi` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `saidi` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `maifi` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `asai` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `ens` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `no_predictive` | `critical_load_restored_pct` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `successful_restoration_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `number_of_islands` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `isolated_nodes` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `actions_taken` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `switching_operations` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `illegal_actions_attempted` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `load_shedding_events` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `battery_dispatch_events` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `voltage_violation_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `frequency_deviation_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `line_overload_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `minimum_voltage_pu` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `maximum_voltage_pu` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `average_voltage_pu` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `operating_cost_usd` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `outage_cost_usd` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `carbon_kg` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_predictive` | `runtime_s` | 2 | 0.0040 | 0.622 | 0.6600 | 0.6547 | 0.440 | small | no |
| `random` | `saifi` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `saidi` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `maifi` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `asai` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `ens` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `random` | `critical_load_restored_pct` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `successful_restoration_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `number_of_islands` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `isolated_nodes` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `actions_taken` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `switching_operations` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `illegal_actions_attempted` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `load_shedding_events` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `battery_dispatch_events` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `voltage_violation_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `frequency_deviation_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `line_overload_count` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `minimum_voltage_pu` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `maximum_voltage_pu` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `average_voltage_pu` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `operating_cost_usd` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `outage_cost_usd` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `carbon_kg` | 2 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `runtime_s` | 2 | 0.0141 | 1.899 | 0.1793 | 0.1797 | 1.343 | large | no |
