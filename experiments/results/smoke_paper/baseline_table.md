# EHM-simulation — Research Tables

_Generated from `experiments.tables`._

## Run summary

- Total runs: **6**, valid: **6** (100.0 %).
- Anchor policy for paired comparison: `rule_based`.

## Per-policy summary

Mean ± std over all valid runs of each configuration. Cells with `n=0` mean the metric was not produced for that policy.

| Policy | n | Active modules | Disabled modules | SAIFI (faults/node) | SAIDI (steps) | MAIFI (events/node) | ASAI | ENS (step·count) | Avg restoration (steps) | Critical-load restored (%) | Successful restorations | Islands | Isolated nodes | Actions taken | Switching operations | Illegal actions | Load-shedding events | Battery dispatches | Voltage violations | Frequency deviations | Line overloads | Vmin (pu) | Vmax (pu) | Vavg (pu) | Operating cost (USD) | Outage cost (USD) | Carbon (kg) | Run time (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `random` | 3 | — | dqn, lstm, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | 0.020 ± 0.000 | 0.000 ± 0.000 | 20.000 ± 0.000 | 0.000 ± 0.000 | 10.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 20.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 980.000 ± 0.000 | 0.000 ± 0.000 | 0.950 ± 0.000 | 1.000 ± 0.000 | 0.961 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.054 ± 0.004 |
| `rule_based` | 3 | flisr | dqn, lstm, digital_twin, predictive_healing, reward_shaping, ems, storage, xai | 0.020 ± 0.000 | 0.000 ± 0.000 | 20.000 ± 0.000 | 0.000 ± 0.000 | 10.000 ± 0.000 | — | 100.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 20.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 980.000 ± 0.000 | 0.000 ± 0.000 | 0.950 ± 0.000 | 1.000 ± 0.000 | 0.961 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.056 ± 0.003 |

## Paired comparison vs `rule_based`

Each row is a paired test on (anchor, other) matched by (seed, weather). `d` is Cohen's d (paired); positive `mean_diff` means anchor > other for that metric.

| Other | Metric | n | mean_diff | t | p(t) | Wilcoxon p | Cohen's d | Effect | Sig@0.05 |
|---|---|---|---|---|---|---|---|---|---|
| `random` | `saifi` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `saidi` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `maifi` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `asai` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `ens` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `restoration_time_steps` | 0 | — | — | — | — | — | — | n<2; cannot compute paired test |
| `random` | `critical_load_restored_pct` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `successful_restoration_count` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `number_of_islands` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `isolated_nodes` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `actions_taken` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `switching_operations` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `illegal_actions_attempted` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `load_shedding_events` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `battery_dispatch_events` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `voltage_violation_count` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `frequency_deviation_count` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `line_overload_count` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `minimum_voltage_pu` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `maximum_voltage_pu` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `average_voltage_pu` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `operating_cost_usd` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `outage_cost_usd` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `carbon_kg` | 3 | 0.0000 | 0.000 | 1.0000 | 1.0000 | 0.000 | negligible | no |
| `random` | `runtime_s` | 3 | 0.0017 | 0.464 | 0.7047 | 0.2850 | 0.268 | small | no |
