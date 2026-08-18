# EHM Benchmark Report

- Generated from: `smoke.json`
- Total runs: **120** (seeds=2, policies=2, scenarios=10, weather modes=3)
- Wall-clock: 108.86 s

## Per-metric aggregates (mean ± std, 95% CI)

| Metric | random | rule_based |
|---|---|---|
| `energy_not_supplied` | 1.010 ± 1.329  (0.673–1.346) | 1.010 ± 1.329  (0.673–1.346) |
| `fault_detection_f1` | 1.000 ± 0.000  (1.000–1.000) | 1.000 ± 0.000  (1.000–1.000) |
| `forecast_rmse` | 0.724 ± 0.286  (0.652–0.797) | 0.724 ± 0.286  (0.652–0.797) |
| `restoration_time` | 24.000 ± 12.101  (20.938–27.062) | 24.000 ± 12.101  (20.938–27.062) |
| `rl_reward` | -218.061 ± 55.445  (-232.090–-204.031) | -190.729 ± 59.391  (-205.757–-175.701) |
| `saidi_proxy` | 4.824 ± 8.621  (2.642–7.005) | 4.832 ± 8.617  (2.652–7.013) |

## Paired t-test: rule_based vs random

| Metric | t-statistic | Significant (|t| > 1.96) |
|---|---|---|
| `energy_not_supplied` | +0.000 | no |
| `fault_detection_f1` | +0.000 | no |
| `forecast_rmse` | +0.000 | no |
| `restoration_time` | +0.000 | no |
| `rl_reward` | +18.848 | **YES** |
| `saidi_proxy` | +1.000 | no |