# RUN COMPLETENESS REPORT — Corrected Experiment B

## 1. Dataset source

- File: `correction_audit_phase1/experiment_B_corrected_rerun/experiment_B_runs.json`
- Git commit: `None`

## 2. Totals

| Item | Expected | Observed |
|---|---|---|
| Total runs | 540 | 540 |
| Valid runs | 540 | 540 |
| Invalid runs | 0 | 0 |

**Verdict: PASS**

## 3. Design axes

| Axis | Expected | Observed | Verdict |
|---|---|---|---|
| Unique seeds | 30 | 30 | PASS |
| Stress levels | 2 (`moderate`, `severe`) | ['moderate', 'severe'] | PASS |
| Unique policies | 9 | 9 | PASS |

Policies observed:
- `dqn_core_only`
- `full_stack`
- `no_lstm`
- `no_predictive`
- `no_reward`
- `no_twin`
- `persistence`
- `random`
- `rule_based`

## 4. seed x stress x policy completeness

- Expected combinations: `30 seeds x 2 levels x 9 policies = 540`
- Observed combinations: 540
- Duplicated combinations: 0
- Missing combinations: 0

Every seed x stress x policy combination occurs **exactly once**.

## 5. Per-policy / per-level counts

| stress_level | policy | n_runs | n_valid |
|---|---|---:|---:|
| moderate | dqn_core_only | 30 | 30 |
| moderate | full_stack | 30 | 30 |
| moderate | no_lstm | 30 | 30 |
| moderate | no_predictive | 30 | 30 |
| moderate | no_reward | 30 | 30 |
| moderate | no_twin | 30 | 30 |
| moderate | persistence | 30 | 30 |
| moderate | random | 30 | 30 |
| moderate | rule_based | 30 | 30 |
| severe | dqn_core_only | 30 | 30 |
| severe | full_stack | 30 | 30 |
| severe | no_lstm | 30 | 30 |
| severe | no_predictive | 30 | 30 |
| severe | no_reward | 30 | 30 |
| severe | no_twin | 30 | 30 |
| severe | persistence | 30 | 30 |
| severe | random | 30 | 30 |
| severe | rule_based | 30 | 30 |

## 6. Overall verdict: **PASS**

_Raw results were not modified by this audit._
