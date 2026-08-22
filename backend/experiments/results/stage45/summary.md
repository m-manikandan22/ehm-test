# Stage 45 — Validation Summary

Stage-45 replaces the Stage-44 metric loop with the physics-coupled ``stage45_metrics.Stage45MetricCollector`` (per-load-node service log). The paired-fingerprint contract is preserved: every (controller, ablation) cell sees an identical environment at every (scenario, seed).

FP invalid pairs: 0

## Cells (controller × scenario × ablation)

| controller | scenario | ablation | n | ENS mean (95% CI) | CMI mean (95% CI) | restoration rate mean |
|---|---|---|---:|---|---|---|
| random | A | full_stack | 10 | 0.5874 (0.3540-0.8705) | 172.7000 (121.5000-228.4025) | 0.492 (0.435-0.552) |
| random | E | full_stack | 10 | 1.6184 (1.1348-2.1455) | 275.2000 (196.0000-357.7000) | 0.574 (0.526-0.627) |
| random | I | full_stack | 10 | 0.5919 (0.3564-0.8767) | 178.5000 (126.4000-232.0050) | 0.472 (0.420-0.531) |
| random | J | full_stack | 10 | 2.0198 (1.6986-2.3972) | 3446.3000 (2955.4900-3919.0175) | 0.086 (0.017-0.167) |
| rule_based | A | full_stack | 10 | 4.8733 (4.0582-5.8478) | 394.7000 (361.7000-432.2000) | 0.378 (0.231-0.516) |
| rule_based | E | full_stack | 10 | 9.7608 (8.6947-10.9381) | 595.5000 (537.0000-655.7000) | 0.155 (0.055-0.272) |
| rule_based | I | full_stack | 10 | 4.8733 (4.0582-5.8478) | 394.7000 (361.7000-432.2000) | 0.378 (0.231-0.516) |
| rule_based | J | full_stack | 10 | 44.2272 (38.3935-50.4705) | 4245.9000 (3806.3875-4735.9150) | 0.083 (0.031-0.141) |
| trained_dqn | A | full_stack | 10 | 4.8147 (3.9941-5.7992) | 382.9000 (354.0000-420.0000) | 0.385 (0.235-0.524) |
| trained_dqn | A | no_ems | 10 | 4.8147 (3.9941-5.7992) | 382.9000 (354.0000-420.0000) | 0.385 (0.235-0.524) |
| trained_dqn | A | no_lstm | 10 | 4.8147 (3.9941-5.7992) | 382.9000 (354.0000-420.0000) | 0.385 (0.235-0.524) |
| trained_dqn | A | no_predictive | 10 | 4.8147 (3.9941-5.7992) | 382.9000 (354.0000-420.0000) | 0.385 (0.235-0.524) |
| trained_dqn | A | no_twin | 10 | 4.8147 (3.9941-5.7992) | 382.9000 (354.0000-420.0000) | 0.385 (0.235-0.524) |
| trained_dqn | E | full_stack | 10 | 9.6182 (8.5457-10.8235) | 585.6000 (528.6000-644.5000) | 0.209 (0.119-0.307) |
| trained_dqn | E | no_ems | 10 | 9.6182 (8.5457-10.8235) | 585.6000 (528.6000-644.5000) | 0.209 (0.119-0.307) |
| trained_dqn | E | no_lstm | 10 | 9.6182 (8.5457-10.8235) | 585.6000 (528.6000-644.5000) | 0.209 (0.119-0.307) |
| trained_dqn | E | no_predictive | 10 | 9.6182 (8.5457-10.8235) | 585.6000 (528.6000-644.5000) | 0.209 (0.119-0.307) |
| trained_dqn | E | no_twin | 10 | 9.6182 (8.5457-10.8235) | 585.6000 (528.6000-644.5000) | 0.209 (0.119-0.307) |
| trained_dqn | I | full_stack | 10 | 4.8422 (4.0288-5.8183) | 389.5000 (358.6000-426.7000) | 0.378 (0.231-0.516) |
| trained_dqn | I | no_ems | 10 | 4.8422 (4.0288-5.8183) | 389.5000 (358.6000-426.7000) | 0.378 (0.231-0.516) |
| trained_dqn | I | no_lstm | 10 | 4.8422 (4.0288-5.8183) | 389.5000 (358.6000-426.7000) | 0.378 (0.231-0.516) |
| trained_dqn | I | no_predictive | 10 | 4.8422 (4.0288-5.8183) | 389.5000 (358.6000-426.7000) | 0.378 (0.231-0.516) |
| trained_dqn | I | no_twin | 10 | 4.8422 (4.0288-5.8183) | 389.5000 (358.6000-426.7000) | 0.378 (0.231-0.516) |
| trained_dqn | J | full_stack | 10 | 42.6406 (37.3188-48.2515) | 3958.8000 (3606.8725-4339.7325) | 0.124 (0.064-0.186) |
| trained_dqn | J | no_ems | 10 | 42.6406 (37.3188-48.2515) | 3958.8000 (3606.8725-4339.7325) | 0.124 (0.064-0.186) |
| trained_dqn | J | no_lstm | 10 | 42.6406 (37.3188-48.2515) | 3958.8000 (3606.8725-4339.7325) | 0.124 (0.064-0.186) |
| trained_dqn | J | no_predictive | 10 | 42.6406 (37.3188-48.2515) | 3958.8000 (3606.8725-4339.7325) | 0.124 (0.064-0.186) |
| trained_dqn | J | no_twin | 10 | 42.6406 (37.3188-48.2515) | 3958.8000 (3606.8725-4339.7325) | 0.124 (0.064-0.186) |
| untrained_dqn | A | full_stack | 10 | 2.4983 (1.2590-3.7073) | 263.4000 (191.1975-330.7000) | 0.475 (0.336-0.596) |
| untrained_dqn | A | no_ems | 10 | 2.4983 (1.2590-3.7073) | 263.4000 (191.1975-330.7000) | 0.475 (0.336-0.596) |
| untrained_dqn | A | no_lstm | 10 | 2.4983 (1.2590-3.7073) | 263.4000 (191.1975-330.7000) | 0.475 (0.336-0.596) |
| untrained_dqn | A | no_predictive | 10 | 2.4983 (1.2590-3.7073) | 263.4000 (191.1975-330.7000) | 0.475 (0.336-0.596) |
| untrained_dqn | A | no_twin | 10 | 2.4983 (1.2590-3.7073) | 263.4000 (191.1975-330.7000) | 0.475 (0.336-0.596) |
| untrained_dqn | E | full_stack | 10 | 5.3846 (2.7232-7.9244) | 431.2000 (285.0950-572.9000) | 0.250 (0.117-0.395) |
| untrained_dqn | E | no_ems | 10 | 5.3846 (2.7232-7.9244) | 431.2000 (285.0950-572.9000) | 0.250 (0.117-0.395) |
| untrained_dqn | E | no_lstm | 10 | 5.3846 (2.7232-7.9244) | 431.2000 (285.0950-572.9000) | 0.250 (0.117-0.395) |
| untrained_dqn | E | no_predictive | 10 | 5.3846 (2.7232-7.9244) | 431.2000 (285.0950-572.9000) | 0.250 (0.117-0.395) |
| untrained_dqn | E | no_twin | 10 | 5.3846 (2.7232-7.9244) | 431.2000 (285.0950-572.9000) | 0.250 (0.117-0.395) |
| untrained_dqn | I | full_stack | 10 | 2.5341 (1.2746-3.7608) | 278.3000 (202.1950-346.2000) | 0.442 (0.320-0.540) |
| untrained_dqn | I | no_ems | 10 | 2.5341 (1.2746-3.7608) | 278.3000 (202.1950-346.2000) | 0.442 (0.320-0.540) |
| untrained_dqn | I | no_lstm | 10 | 2.5341 (1.2746-3.7608) | 278.3000 (202.1950-346.2000) | 0.442 (0.320-0.540) |
| untrained_dqn | I | no_predictive | 10 | 2.5341 (1.2746-3.7608) | 278.3000 (202.1950-346.2000) | 0.442 (0.320-0.540) |
| untrained_dqn | I | no_twin | 10 | 2.5341 (1.2746-3.7608) | 278.3000 (202.1950-346.2000) | 0.442 (0.320-0.540) |
| untrained_dqn | J | full_stack | 10 | 26.9532 (13.0951-40.6742) | 3789.2000 (3109.5975-4462.0225) | 0.064 (0.026-0.108) |
| untrained_dqn | J | no_ems | 10 | 26.9532 (13.0951-40.6742) | 3789.2000 (3109.5975-4462.0225) | 0.064 (0.026-0.108) |
| untrained_dqn | J | no_lstm | 10 | 26.9532 (13.0951-40.6742) | 3789.2000 (3109.5975-4462.0225) | 0.064 (0.026-0.108) |
| untrained_dqn | J | no_predictive | 10 | 26.9532 (13.0951-40.6742) | 3789.2000 (3109.5975-4462.0225) | 0.064 (0.026-0.108) |
| untrained_dqn | J | no_twin | 10 | 26.9532 (13.0951-40.6742) | 3789.2000 (3109.5975-4462.0225) | 0.064 (0.026-0.108) |

## Pairwise: trained_dqn vs rule_based

| scenario | ablation | metric | mean_diff | Cohen's d | p (Wilcoxon) |
|---|---|---|---:|---:|---:|
| A | full_stack | energy_not_served_mwh | -5.0408 | nan | nan |
| A | full_stack | total_customer_minutes_interrupted | -282.0000 | nan | nan |
| A | full_stack | restoration_rate | 0.0714 | nan | nan |
| A | full_stack | avg_restoration_steps | -54.8333 | nan | nan |
| A | full_stack | critical_load_interruption_steps | -53.0000 | nan | nan |
| A | full_stack | voltage_violation_count | 0.0000 | nan | nan |
| E | full_stack | energy_not_served_mwh | -9.8608 | nan | nan |
| E | full_stack | total_customer_minutes_interrupted | -526.0000 | nan | nan |
| E | full_stack | restoration_rate | -0.0455 | nan | nan |
| E | full_stack | avg_restoration_steps | -32.3333 | nan | nan |
| E | full_stack | critical_load_interruption_steps | -38.0000 | nan | nan |
| E | full_stack | voltage_violation_count | 0.0000 | nan | nan |
| I | full_stack | energy_not_served_mwh | -5.0408 | nan | nan |
| I | full_stack | total_customer_minutes_interrupted | -282.0000 | nan | nan |
| I | full_stack | restoration_rate | 0.0714 | nan | nan |
| I | full_stack | avg_restoration_steps | -54.8333 | nan | nan |
| I | full_stack | critical_load_interruption_steps | -53.0000 | nan | nan |
| I | full_stack | voltage_violation_count | 0.0000 | nan | nan |
| J | full_stack | energy_not_served_mwh | -57.3955 | nan | nan |
| J | full_stack | total_customer_minutes_interrupted | -1995.0000 | nan | nan |
| J | full_stack | restoration_rate | -0.0714 | nan | nan |
| J | full_stack | avg_restoration_steps | -49.0000 | nan | nan |
| J | full_stack | critical_load_interruption_steps | -165.0000 | nan | nan |
| J | full_stack | voltage_violation_count | 0.0000 | nan | nan |