# EHM-simulation — Research Tables

_Generated from `experiments.tables`._

## Run summary

- Total runs: **9**, valid: **9** (100.0 %).
- Anchor policy for paired comparison: `full_stack`.

## Per-policy summary

Mean ± std over all valid runs of each configuration. Cells with `n=0` mean the metric was not produced for that policy.

| Policy | n | Active modules | Disabled modules | SAIFI (faults/node) | SAIDI (steps) | MAIFI (events/node) | ASAI | ENS (step·count) | Avg restoration (steps) | Critical-load restored (%) | Successful restorations | Islands | Isolated nodes | Actions taken | Switching operations | Illegal actions | Load-shedding events | Battery dispatches | Voltage violations | Frequency deviations | Line overloads | Vmin (pu) | Vmax (pu) | Vavg (pu) | Operating cost (USD) | Outage cost (USD) | Carbon (kg) | Run time (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `full_stack` | 3 | dqn, lstm, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | — | 0.020 ± 0.000 | 0.000 ± 0.000 | 20.000 ± 0.000 | 0.000 ± 0.000 | 10.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 20.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 980.000 ± 0.000 | 0.000 ± 0.000 | 0.950 ± 0.000 | 1.000 ± 0.000 | 0.961 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.084 ± 0.007 |
| `no_lstm` | 3 | dqn, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | lstm | 0.020 ± 0.000 | 0.000 ± 0.000 | 20.000 ± 0.000 | 0.000 ± 0.000 | 10.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 20.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 980.000 ± 0.000 | 0.000 ± 0.000 | 0.950 ± 0.000 | 1.000 ± 0.000 | 0.961 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.074 ± 0.003 |
| `no_twin` | 3 | dqn, lstm, predictive_healing, reward_shaping, flisr, ems, storage, xai | digital_twin | 0.020 ± 0.000 | 0.000 ± 0.000 | 20.000 ± 0.000 | 0.000 ± 0.000 | 10.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 20.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 980.000 ± 0.000 | 0.000 ± 0.000 | 0.950 ± 0.000 | 1.000 ± 0.000 | 0.961 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.095 ± 0.021 |

## Paired comparison vs `full_stack`

Each row is a paired test on (anchor, other) matched by (seed, weather). `d` is Cohen's d (paired); positive `mean_diff` means anchor > other for that metric.

| Other | Metric | n | mean_diff | t | p(t) | Wilcoxon p | Cohen's d | Effect | Sig@0.05 |
|---|---|---|---|---|---|---|---|---|---|
| `no_lstm` | `saifi` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `saidi` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `maifi` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `asai` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `ens` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `no_lstm` | `critical_load_restored_pct` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `successful_restoration_count` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `number_of_islands` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `isolated_nodes` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `actions_taken` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `switching_operations` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `illegal_actions_attempted` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `load_shedding_events` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `battery_dispatch_events` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `voltage_violation_count` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `frequency_deviation_count` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `line_overload_count` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `minimum_voltage_pu` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `maximum_voltage_pu` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `average_voltage_pu` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `operating_cost_usd` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `outage_cost_usd` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `carbon_kg` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_lstm` | `runtime_s` | 3 | 0.0105 | 2.470 | 0.0437 | 0.1088 | 1.426 | large | yes |
| `no_twin` | `saifi` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `saidi` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `maifi` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `asai` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `ens` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `no_twin` | `critical_load_restored_pct` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `successful_restoration_count` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `number_of_islands` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `isolated_nodes` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `actions_taken` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `switching_operations` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `illegal_actions_attempted` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `load_shedding_events` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `battery_dispatch_events` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `voltage_violation_count` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `frequency_deviation_count` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `line_overload_count` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `minimum_voltage_pu` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `maximum_voltage_pu` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `average_voltage_pu` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `operating_cost_usd` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `outage_cost_usd` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `carbon_kg` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `no_twin` | `runtime_s` | 3 | -0.0106 | -0.674 | 0.5823 | 1.0000 | -0.389 | small | no |
