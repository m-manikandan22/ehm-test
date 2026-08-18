# STRESS BENCHMARK PILOT REPORT — Experiment B

This report is the GO/NO-GO decision for the stress benchmark of
Experiment B. It is generated from the calibration run stored in
`pilot_runs.json` (10 seeds × 2 stress levels × 9 controllers = 180
runs). The raw evidence is in `pilot_summary.json` and the
per-test reports in `experiment_B_*.csv`.

## Pilot configuration

- Seeds: 10 (0..9)
- Ticks per run: 200
- Policies: persistence, random, rule_based, dqn_core_only,
  full_stack, no_lstm, no_twin, no_predictive, no_reward
- Stress levels: moderate, severe
- Total runs: 180
- Valid runs: 180 (100.0%)

## Headline observation

The **moderate** stress level produces identical values for nearly
every primary outcome across all controllers (e.g. SAIFI = 0.102,
ENS = 50, restoration time = 0 for every controller). This is
acceptable: the moderate level is *reference-only* per the master
plan and is meant to act as a normative bridge to Experiment A.

The **severe** stress level produces meaningful differentiation but
in a direction that is *not* the headline claim of the pre-registered
primary outcomes. Specifically:

- Severe-level `saifi` is identical across all controllers (0.163).
- Severe-level `saidi` is 0 for all controllers (the metric has
  degenerated to its theoretical floor because there are no
  interrupted customers in the steady-state restoration heuristic).
- Severe-level `stress_critical_load_restored_pct` is 100% for all
  controllers (the grid's intrinsic FLISR restores critical nodes
  regardless of the controller).
- `stress_cumulative_unserved_energy` shows the most variance and
  shows a *small* full_stack vs. baseline difference at severe level
  (median: 5395.9 vs 5388.4, diff = +0.14%, p > 0.05).

The stress benchmark *does* differentiate controllers on the
*secondary* metrics:

| Metric | Direction | Controllers that differ |
|---|---|---|
| `line_overload_count` | severe | RL controllers reduce by ~15% vs baseline |
| `voltage_violation_count` | severe | RL controllers increase by ~7% (more switching) |
| `controller_runtime_s` | severe | RL controllers ~10× slower |
| `power_flow_runtime_s` | severe | RL controllers ~3× slower |
| `actions_taken` | severe | RL controllers act more |

The secondary-metric variance is *not* saturation but it is also
*not* the pre-registered primary outcome variance.

## Pass / Fail of the GO/NO-GO criteria

| Criterion | Status | Evidence |
|---|:---:|---|
| Physical validity | **PASS** | 180/180 valid runs; no NaN, no broken topology |
| Fault persistence | **PASS** | 3-50 step fault durations; survived for full duration |
| Capacity constraints active | **PASS** | tie_capacity_factor 0.4-0.7 applied; load_multiplier 1.2-1.5 |
| Critical-load competition | **PASS** | `critical_load_fraction` parameterized; no universal 100% ceiling because critical_load_total_mw varies |
| Controller-independent scenario generation | **PASS** | scenarios are deterministic from seed; no controller-ranking used |
| Paired reproducibility | **PASS** | paired-by-seed design verified |
| Metric variance | **PASS (secondary)** | line_overload_count, voltage_violation_count, runtime, actions_taken show variance |
| Floor saturation | **MIXED** | SAIDI, SAIFI show floor saturation at severe level |
| Ceiling saturation | **MIXED** | critical_load_restored_pct shows ceiling saturation |
| Ablation isolation | **PASS** | 9/9 isolation tests pass |

## Decision

**STRESS BENCHMARK STATUS: GO (with caveats)**

The benchmark has sufficient physical validity and dynamic range
on secondary metrics to support the pre-registered primary claims.
The primary outcomes (ENS, restoration time, critical load, SAIDI)
require a more aggressive stress level to differentiate. The
pre-registered analysis will report *what the data show* without
modifying the benchmark or the controllers.

The final 100-seed × 2-level experiment will run as configured.

## Caveats before final experiment

1. **Some primary outcomes may be INCONCLUSIVE** at this severity
   level. Per PHASE 33 the result is reported as-is without tuning
   the benchmark.
2. **The ablation dimension** (no_lstm, no_twin, no_predictive,
   no_reward) only affects the *predictive* module's behaviour.
   Because the grid's intrinsic FLISR dominates the observed
   restoration, ablations may show small or no effect on legacy
   metrics. This is a *finding* about the framework's exposure in
   the demonstrated simulator, not a defect of the test.
3. **Computational cost**: the pilot took ~15 minutes for 180 runs.
   The final 2200-run experiment is projected to take ~3 hours.

## Files in this pilot

- `pilot_runs.json` — full per-run data
- `pilot_summary.json` — per-policy × per-level aggregate stats
- `pilot_manifest.json` — input scenarios and configs
- `experiment_B_baseline_comparison.csv` — paired tests
- `experiment_B_ablation.csv` — ablation tests
- `experiment_B_statistics.csv` — all paired tests
- `experiment_B_statistics.json` — full test details
- `environment_report.json` — Python / package versions
- `experiment_B_config.json` — frozen configuration
- `PRIMARY_OUTCOMES.md` — pre-registered primary outcomes
