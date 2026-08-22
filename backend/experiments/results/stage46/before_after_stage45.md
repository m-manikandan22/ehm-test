# Stage 46 — Before/After Stage-45 vs Stage-46

Per-cell means (full_stack only) on the 6 metrics, paired Wilcoxon signed-rank test (10 seeds).

## Per-cell means (ENS, MWh)

| Controller | Scenario | n_45 | mean_45 | n_46 | mean_46 | delta | p (paired) |
|---|---|---:|---:|---:|---:|---:|---:|
| random | A | 10 | 0.5874 | 10 | 0.5850 | -0.0024 | 0.3173 |
| random | E | 10 | 1.6184 | 10 | 1.6094 | -0.0091 | 0.1797 |
| random | I | 10 | 0.5919 | 10 | 0.5895 | -0.0024 | 0.3173 |
| random | J | 10 | 2.0198 | 10 | 2.0198 | +0.0000 | 1.0000 |
| rule_based | A | 10 | 4.8733 | 10 | 4.7884 | -0.0849 | 0.0679 |
| rule_based | E | 10 | 9.7608 | 10 | 9.6493 | -0.1115 | 0.0679 |
| rule_based | I | 10 | 4.8733 | 10 | 4.7884 | -0.0849 | 0.0679 |
| rule_based | J | 10 | 44.2272 | 10 | 44.1464 | -0.0808 | 0.4652 |
| trained_dqn | A | 10 | 4.8147 | 10 | 4.7069 | -0.1078 | 0.1441 |
| trained_dqn | E | 10 | 9.6182 | 10 | 9.4572 | -0.1611 | 0.2733 |
| trained_dqn | I | 10 | 4.8422 | 10 | 4.7565 | -0.0857 | 0.1441 |
| trained_dqn | J | 10 | 42.6406 | 10 | 42.8321 | +0.1915 | 0.4652 |
| untrained_dqn | A | 10 | 2.4983 | 10 | 2.4983 | +0.0000 | 1.0000 |
| untrained_dqn | E | 10 | 5.3846 | 10 | 5.3846 | +0.0000 | 1.0000 |
| untrained_dqn | I | 10 | 2.5341 | 10 | 2.5341 | +0.0000 | 1.0000 |
| untrained_dqn | J | 10 | 26.9532 | 10 | 26.8839 | -0.0693 | 0.6547 |

## Paired before/after (Stage-46 vs Stage-45)

| cell | scen | metric | mean_45 | mean_46 | diff | p |
|---|---|---|---:|---:|---:|---:|
| random | A | energy_not_served_mwh | 0.5874 | 0.5850 | -0.0024 | 0.3173 |
| random | E | energy_not_served_mwh | 1.6184 | 1.6094 | -0.0091 | 0.1797 |
| random | I | energy_not_served_mwh | 0.5919 | 0.5895 | -0.0024 | 0.3173 |
| random | J | energy_not_served_mwh | 2.0198 | 2.0198 | +0.0000 | 1.0000 |
| rule_based | A | energy_not_served_mwh | 4.8733 | 4.7884 | -0.0849 | 0.0679 |
| rule_based | E | energy_not_served_mwh | 9.7608 | 9.6493 | -0.1115 | 0.0679 |
| rule_based | I | energy_not_served_mwh | 4.8733 | 4.7884 | -0.0849 | 0.0679 |
| rule_based | J | energy_not_served_mwh | 44.2272 | 44.1464 | -0.0808 | 0.4652 |
| trained_dqn | A | energy_not_served_mwh | 4.8147 | 4.7069 | -0.1078 | 0.1441 |
| trained_dqn | E | energy_not_served_mwh | 9.6182 | 9.4572 | -0.1611 | 0.2733 |
| trained_dqn | I | energy_not_served_mwh | 4.8422 | 4.7565 | -0.0857 | 0.1441 |
| trained_dqn | J | energy_not_served_mwh | 42.6406 | 42.8321 | +0.1915 | 0.4652 |
| untrained_dqn | A | energy_not_served_mwh | 2.4983 | 2.4983 | +0.0000 | 1.0000 |
| untrained_dqn | E | energy_not_served_mwh | 5.3846 | 5.3846 | +0.0000 | 1.0000 |
| untrained_dqn | I | energy_not_served_mwh | 2.5341 | 2.5341 | +0.0000 | 1.0000 |
| untrained_dqn | J | energy_not_served_mwh | 26.9532 | 26.8839 | -0.0693 | 0.6547 |