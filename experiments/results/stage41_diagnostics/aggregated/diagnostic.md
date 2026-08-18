# Stage 41 — Diagnostic per-controller summary

5 seeds × 80 ticks × 3 faults (default scenario).

| Controller | n_valid | ENS mean ± std | CMI mean ± std | restoration_rate | critical_load_steps |
|---|---:|---|---|---|---|
| `random` | 5 | 1.1065 ± 0.7903 | 66.3897 ± 47.4199 | 1.0000 ± 0.0000 | 0.0000 ± 0.0000 |
| `rule_based` | 5 | 1.6807 ± 0.7285 | 100.8396 ± 43.7123 | 1.0000 ± 0.0000 | 0.0000 ± 0.0000 |
| `dqn_core_only` | 5 | 1.3675 ± 0.6987 | 82.0495 ± 41.9195 | 1.0000 ± 0.0000 | 0.0000 ± 0.0000 |
| `full_stack` | 5 | 1.3675 ± 0.6987 | 82.0495 ± 41.9195 | 1.0000 ± 0.0000 | 0.0000 ± 0.0000 |

## Paired comparison vs `rule_based` (anchor − other)

Positive diff means rule_based is worse (other better for lower-is-better metrics).
| Other | Metric | mean_diff | t | p | Cohen's d | Effect | Sig? |
|---|---|---:|---:|---:|---:|---|:---:|
| `dqn_core_only` | `energy_not_served_mwh` | 0.3132 | 1.710 | 0.126 | 0.764 | medium | no |
| `dqn_core_only` | `total_customer_minutes_interrupted` | 18.7901 | 1.710 | 0.126 | 0.764 | medium | no |
| `dqn_core_only` | `restoration_rate` | 0.0000 | 0.000 | 1.000 | 0.000 | negligible | no |
| `full_stack` | `energy_not_served_mwh` | 0.3132 | 1.710 | 0.126 | 0.764 | medium | no |
| `full_stack` | `total_customer_minutes_interrupted` | 18.7901 | 1.710 | 0.126 | 0.764 | medium | no |
| `full_stack` | `restoration_rate` | 0.0000 | 0.000 | 1.000 | 0.000 | negligible | no |
| `random` | `energy_not_served_mwh` | 0.5742 | 2.961 | 0.008 | 1.324 | large | yes |
| `random` | `total_customer_minutes_interrupted` | 34.4499 | 2.961 | 0.008 | 1.324 | large | yes |
| `random` | `restoration_rate` | 0.0000 | 0.000 | 1.000 | 0.000 | negligible | no |