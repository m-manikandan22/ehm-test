# FAILURE CASE ANALYSIS — Experiment B

This document examines, seed-by-seed, when the proposed EHM `full_stack` controller outperforms, ties, or is outperformed by `rule_based` under the **severe** stress level. The primary metric is `stress_cumulative_unserved_energy` (lower is better).

Categories are based on the percentage difference of `full_stack` against `rule_based` on the same seed.



## Summary

- `full_stack` **wins** (≥ 5 % ENS reduction): 0 / 30 seeds
- `full_stack` **ties** (|Δ| < 5 %): 30 / 30 seeds
- `full_stack` **loses** (≥ 5 % ENS increase): 0 / 30 seeds


## WINS cases (0)


## TIES cases (30)

- **Seed 21** (`severe`):
  - Faults: 8 scheduled, durations [36, 32, 47, 34, 30, 50, 32, 27]
  - full_stack: ENS=8267.8, crit_load_restored=100.0%, actions=200
  - rule_based: ENS=8513.3, crit_load_restored=100.0%, actions=200
  - rule_based issued 200 rule actions.

- **Seed 8** (`severe`):
  - Faults: 8 scheduled, durations [29, 47, 27, 37, 31, 43, 25, 39]
  - full_stack: ENS=8001.2, crit_load_restored=100.0%, actions=200
  - rule_based: ENS=8237.5, crit_load_restored=100.0%, actions=200
  - rule_based issued 200 rule actions.

- **Seed 0** (`severe`):
  - Faults: 8 scheduled, durations [41, 50, 29, 47, 36, 38, 50, 40]
  - full_stack: ENS=8038.4, crit_load_restored=100.0%, actions=200
  - rule_based: ENS=8224.1, crit_load_restored=100.0%, actions=200
  - rule_based issued 200 rule actions.


*…27 more seeds in this category omitted for brevity.*


## LOSES cases (0)


## Caveats

- 'Wins' and 'losses' are *relative to* the same-seed rule_based baseline. They are not absolute claims about validity.
- This analysis is anchored to the severe stress level. The moderate level is the reference / nominal-equivalent and is reported separately.
