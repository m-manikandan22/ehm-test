# RESILIENCE CURVES — Text Summary

Step-level service series are recorded in the runner when available. If the runner does not record them, we report the runner's *cumulative* resilience metrics only and do not interpolate.


## Stress level: moderate

| Controller | n | cumulative_unserved_energy (med) | resilience_loss_area (med) | t50 (med) | t90 (med) |
|---|---|---|---|---|---|
| dqn_core_only | 30 | 0.0 | 0.0 | 0.0 | 0.0 |
| full_stack | 30 | 0.0 | 0.0 | 0.0 | 0.0 |
| no_lstm | 30 | 0.0 | 0.0 | 0.0 | 0.0 |
| no_predictive | 30 | 0.0 | 0.0 | 0.0 | 0.0 |
| no_reward | 30 | 0.0 | 0.0 | 0.0 | 0.0 |
| no_twin | 30 | 0.0 | 0.0 | 0.0 | 0.0 |
| persistence | 30 | 0.0 | 0.0 | 0.0 | 0.0 |
| random | 30 | 0.0 | 0.0 | 0.0 | 0.0 |
| rule_based | 30 | 0.0 | 0.0 | 0.0 | 0.0 |

## Stress level: severe

| Controller | n | cumulative_unserved_energy (med) | resilience_loss_area (med) | t50 (med) | t90 (med) |
|---|---|---|---|---|---|
| dqn_core_only | 30 | 8364.4 | 172.5 | 0.0 | 0.0 |
| full_stack | 30 | 8364.4 | 172.5 | 0.0 | 0.0 |
| no_lstm | 30 | 8364.4 | 172.5 | 0.0 | 0.0 |
| no_predictive | 30 | 8364.4 | 172.5 | 0.0 | 0.0 |
| no_reward | 30 | 8364.4 | 172.5 | 0.0 | 0.0 |
| no_twin | 30 | 8364.4 | 172.5 | 0.0 | 0.0 |
| persistence | 30 | 8239.2 | 172.5 | 0.0 | 0.0 |
| random | 30 | 8239.2 | 172.5 | 0.0 | 0.0 |
| rule_based | 30 | 8239.2 | 172.5 | 0.0 | 0.0 |


Cumulative unserved energy is the *primary* resilience metric per `PRIMARY_OUTCOMES.md`. The resilience_loss_area and t50 / t90 columns are *secondary* outcomes reported for completeness.
