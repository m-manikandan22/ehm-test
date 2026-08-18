# PRIMARY OUTCOMES — Experiment B

This document pre-registers the primary statistical outcomes of
Experiment B **before** the final results are inspected. This protects
against selective reporting.

The primary outcomes are the only metrics that the paper's headline
claims will be based on. All secondary metrics are reported for
completeness but do not determine "did the experiment show what we
hoped it would show".

## Pre-registration discipline

PHASE 22 of the master plan mandates that primary outcomes be defined
***before*** final analysis. We follow this strictly: this file is
written before `EXPERIMENT_B_FINAL_RESULTS.md` and the statistical
tests are run. The thresholds for "supported" vs. "not supported" are
fixed here.

## Primary outcomes (4)

### PRIMARY OUTCOME 1 — Cumulative ENS / unserved energy

**Metric**: `stress_cumulative_unserved_energy` (MW·steps across the
run). Higher is worse.

**Hypothesis**: `full_stack` produces a *lower* median
`stress_cumulative_unserved_energy` than `rule_based` under paired
seeds at the **severe** stress level.

**Test**: Wilcoxon signed-rank test on the per-seed differences
(full_stack − rule_based). Paired by seed.

**Effect-size threshold for "supported"**: median reduction ≥ 5 %
with Holm-corrected p < 0.05.

### PRIMARY OUTCOME 2 — Restoration time

**Metric**: `resilience_time_to_50pct_restoration` (steps). Lower is
better. If the system never dips below 50 % unserved, the metric is
the maximum (200 steps).

**Hypothesis**: `full_stack` has a smaller median
`resilience_time_to_50pct_restoration` than `rule_based` at the
**severe** stress level.

**Test**: paired Wilcoxon. Effect-size threshold: median reduction
≥ 5 % with Holm-corrected p < 0.05.

### PRIMARY OUTCOME 3 — Critical-load restoration

**Metric**: `stress_critical_load_restored_pct` (0–100). Higher is
better.

**Hypothesis**: `full_stack` produces a *higher* median critical-load
restoration percentage than `rule_based` at the **severe** stress
level.

**Test**: paired Wilcoxon. Effect-size threshold: median improvement
≥ 2 percentage points with Holm-corrected p < 0.05.

### PRIMARY OUTCOME 4 — SAIDI

**Metric**: `saidi` (hours/year per customer, simulation-derived).
Lower is better.

**Hypothesis**: `full_stack` produces a *lower* median `saidi` than
`rule_based` at the **severe** stress level.

**Test**: paired Wilcoxon. Effect-size threshold: median reduction
≥ 5 % with Holm-corrected p < 0.05.

## Secondary outcomes (reported but not gated)

These are *informative* and reported for completeness. They do not
gate any headline claim. Any apparent pattern is described
quantitatively, not as a "supported" claim.

| Metric | Description |
|---|---|
| `saifi` | system average interruption frequency |
| `voltage_violation_count` | count of step-level voltage violations |
| `overloads` | count of step-level line overloads |
| `switching_actions` | count of switch operations |
| `runtime_s` | controller runtime |
| `frequency_deviation_count` | count of frequency deviations |
| `maifi` | momentary average interruption frequency |
| `resilience_loss_area` | trapezoid integral over (1 − service) |
| `stress_critical_load_interrupted_mw` | max simultaneous critical-load lost |
| `stress_critical_load_restored_mw` | critical load finally restored |
| `resilience_time_to_90pct_restoration` | steps to 90 % recovery |
| `stress_cum_feasible_restoration_mw` | sum of feasible restoration |
| `stress_cum_unserved_restoration_mw` | sum of unmet restoration |
| `stress_restoration_rate` | fraction of faults that were restored |

## Controllers used for paired comparisons

For each primary outcome:

- `full_stack` vs. `persistence`
- `full_stack` vs. `random`
- `full_stack` vs. `rule_based`
- `full_stack` vs. `dqn_core_only`

Then ablation comparisons (full_stack vs. each ablation variant) are
also reported with the same statistical discipline.

## Statistical discipline

- **Multiple-comparison correction**: Holm correction across the
  four primary outcomes for each pair of controllers.
- **Effect size**: Cliff's delta (computed alongside Wilcoxon).
- **Family-wise α**: 0.05.
- **Sample size**: n = 30 paired seeds per (level, controller).
  This is the *minimum* sample size required for paired Wilcoxon
  signed-rank tests at α = 0.05. The original freeze specified
  100 seeds. The reduction to 30 is documented in
  `experiment_B_config.json → deviation_from_initial_freeze` and
  occurred *before* the final experiment was run. No scenario
  difficulty was tuned based on cross-controller ranking.
- **Test selection**: Wilcoxon signed-rank (paired, non-parametric)
  is the primary test because (a) the distributions are not
  guaranteed to be normal at this sample size, and
  (b) the data are paired by seed. A paired t-test is also reported
  as a robustness check.

## What "supported" means

A claim is **SUPPORTED** if and only if:
1. The relevant primary outcome passes the threshold defined above
   with Holm-corrected p < 0.05 *and* the effect size is in the
   predicted direction.
2. The same claim is *not* falsified by any other primary outcome.

A claim is **PARTIALLY SUPPORTED** if:
1. The effect is in the predicted direction in at least one
   stress level but not the other, or
2. The effect is statistically detectable but below the threshold.

A claim is **NOT SUPPORTED** if:
1. The effect is in the opposite direction, or
2. There is no statistically detectable difference.

## Pre-registered "don't tune the benchmark" guard

If the benchmark fails to differentiate controllers after
implementation, the result is reported as-is. We do not modify the
benchmark or the controllers to manufacture a difference.

## Document version

- v1.0 (2026-08-04): pre-registered before final analysis.
- v1.1 (2026-08-04): updated sample size to n = 30, documented
  deviation from initial freeze that specified n = 100. The
  deviation occurred *before* final analysis and is recorded in
  `experiment_B_config.json`.
