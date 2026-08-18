# Component activation matrix

Smoke matrix: 36 completed runs.

| Policy | FLISR | Twin updates/queries | LSTM calls | Predictive predictions | Recs/dispatch/applied | Validation |
|---|---:|---:|---:|---:|---:|---|
| dqn_core_only | True / 200 | 0 / 0 | 0 | 0 | 0 / 0 / 0 | PASS |
| full_stack | True / 200 | 9800 / 9800 | 200 | 200 | 0 / 0 / 0 | PASS |
| no_lstm | True / 200 | 9800 / 9800 | 0 | 200 | 0 / 0 / 0 | PASS |
| no_predictive | True / 200 | 9800 / 0 | 200 | 0 | 0 / 0 / 0 | PASS |
| no_reward | True / 200 | 9800 / 9800 | 200 | 200 | 0 / 0 / 0 | PASS |
| no_twin | True / 200 | 0 / 0 | 200 | 200 | 0 / 0 / 0 | PASS |
| persistence | False / 0 | 0 / 0 | 0 | 0 | 0 / 0 / 0 | PASS |
| random | False / 0 | 0 / 0 | 0 | 0 | 0 / 0 / 0 | PASS |
| rule_based | True / 200 | 0 / 0 | 0 | 0 | 0 / 0 / 0 | PASS |
