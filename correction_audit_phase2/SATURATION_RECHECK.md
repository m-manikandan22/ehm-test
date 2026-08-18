# SATURATION RECHECK — Corrected Experiment B

Does corrected FLISR execution change the historical saturation pattern? Each metric is classified over the corrected 540-run dataset.

| metric | full-saturation flag | unique values | CV | distinct policy medians (severe) | classification |
|---|---:|---:|---:|---:|---|
| SAIFI | saifi | 3 | 0.230 | 1 | PARTIAL SATURATION |
| SAIDI | saidi | 1 | 0.000 | 1 | FULL SATURATION |
| ENS | ens | 3 | 0.230 | 1 | PARTIAL SATURATION |
| Stress cumulative ENS | stress_cumulative_unserved_energy | 180 | 1.167 | 3 | GOOD VARIANCE |
| Restoration time (s) | restoration_time_seconds | 1 | 0.000 | 1 | FULL SATURATION |
| Time-to-50% restoration (steps) | resilience_time_to_50pct_restoration | 1 | 0.000 | 1 | FULL SATURATION |
| Critical-load restoration (%) | stress_critical_load_restored_pct | 1 | 0.000 | 1 | FULL SATURATION |
| Voltage violations | voltage_violation_count | 102 | 0.415 | 3 | GOOD VARIANCE |
| Switching operations | switching_operations | 1 | 0.000 | 1 | FULL SATURATION |
| Resilience loss area | resilience_loss_area | 180 | 0.353 | 3 | GOOD VARIANCE |
| Restoration rate | stress_restoration_rate | 1 | 0.000 | 1 | FULL SATURATION |
| Isolated nodes | isolated_nodes | 18 | 0.248 | 1 | PARTIAL SATURATION |
| Line overloads | line_overload_count | 61 | 1.221 | 3 | GOOD VARIANCE |
| Frequency deviations | frequency_deviation_count | 64 | 0.162 | 1 | PARTIAL SATURATION |

## Interpretation

**Corrected FLISR execution changed the ENS picture.** Historically FLISR never executed (`flisr_calls` = 0) and all FLISR-enabled arms looked identical to persistence. In the corrected data FLISR executes every timestep for every FLISR-enabled policy (200 calls/run), applies restoration actions, and reduces unserved energy:

| stress | median ENS persistence/random | median ENS rule_based | median ENS full_stack |
|---|---:|---:|---:|
| moderate | 909.4 / 909.4 | 449.7 | 501.2 |
| severe | 6223.7 / 6223.7 | 1309.9 | 1329.8 |

**However**, four pre-registered primary metrics remain fully saturated in the corrected data: `saidi` (=0), `resilience_time_to_50pct_restoration` (=0), `stress_critical_load_restored_pct` (=100), `switching_operations` (=0). The `stress_restoration_rate` is 0 for all arms (no fault is ever recorded as restored). These are measurement-instrumentation ceilings/floors, not evidence about controller quality, and are reported as observed.

## Why saturation persists (corrected execution evidence)

- `saidi` is derived from the IEEE-1366 formula over restoration events; with no fault recorded as `restored` (`successful_restoration_count` = 0 everywhere), SAIDI = 0 for every run.
- `resilience_time_to_50pct_restoration` is computed as the first step index at which service >= 0.5; because service is 1.0 at step 0 (before faults begin), the recorded value is 0 for every run. The pre-registered "max = 200" floor for never-recovering runs is not realised by the recorded value.
- `stress_critical_load_restored_pct` = 100 because the recorded `stress_critical_load_restored_mw` can go negative when the max simultaneous interrupted load exceeds the run-level total; every run records 100%.
- `switching_operations` is not incremented by the SCADA `_flisr_restore` path (restoration actions applied via tie-switch closures are counted in `restoration_actions_applied`, not in `switching_operations`).

_No raw values were modified._
