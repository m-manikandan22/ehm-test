# Stage 41 — 100-Seed Final-Experiment Configuration (Stage-23 target)

> **Purpose**: define the 100-seed final experiment that the paper
> needs (Stage-23 in the master plan). Stage 41 explicitly does **not**
> run this experiment; it only **configures** it, so the Stage-23 run
> is a single, deterministic, reproducible invocation once the
> Stage-42 harness wiring bug is fixed.

---

## 0. Why this document exists

The Stage-26 paper run used 20 seeds. The user prompt
(`EHM PHASE 41`) is explicit:

> *"Do NOT run the 100-seed experiment yet, add new AI technologies,
> or write the final paper."*

So this is a **configuration** document, not an experiment. It
specifies the exact CLI invocation, the expected statistical output,
the failure-mode handling, and the acceptance criteria for the
Stage-23 final experiment.

---

## 1. Pre-conditions (Stage-42 work, BLOCKING)

Before this experiment can be run, the following Stage-42 work must
be done:

1. **Wire `enable_lstm`, `enable_twin`, `enable_predictive_healing`,
   `enable_reward_shaping`, `enable_ems` flags into
   `runner.run_single`.** Without this, the per-module ablation rows
   are no-ops (see `docs/STAGE_41_INFORMATION_FLOW.md`).
2. **Seed `SmartGrid` construction per run** (EHM-HIGH-009). The
   `runner.py` must derive every RNG from a single root seed
   (`utils.seeds.make_rng(seed)`).
3. **Decouple storage dispatch from simulation-clock advance.** The
   frozen-clock concern is *partially retired* for the dqn_core_only
   comparison, but the per-module ablation still needs both clocks
   advancing for every row.

These three fixes are *the* Stage-42 deliverable. The 100-seed
experiment is the validation step for that deliverable.

---

## 2. Experiment specification

### 2.1 Scenario

* **Grid**: 49-node EHM grid (default).
* **Horizon**: 80 ticks (one full day, `LOAD_CURVE` and
  `SOLAR_CURVE`/`WIND_CURVE` cover one cycle).
* **Faults**: 3 faults injected at random timesteps in `[5, 75]`
  (same default as Stage-26).
* **Seeds**: 100 seeds, `seed = 0..99`.
* **Controllers**: `random`, `rule_based`, `dqn_core_only`,
  `full_stack`.
* **Ablation labels**: `full_stack`, `no_lstm`, `no_twin`,
  `no_predictive`, `no_reward`, `no_ems`, `dqn_core_only`.

Total runs: 100 seeds × (4 controllers + 6 ablation labels) = 1000
runs. Estimated wall-clock at Stage-26 throughput: ~30 minutes on
the Stage-26 hardware baseline.

### 2.2 Reproducibility command (Stage-23 final)

```bash
cd backend
python -m experiments.stage26_pipeline \
    --stage final \
    --seeds 100 --ticks 80 --faults 3 \
    --ablation full \
    --output ../experiments/results/paper_final_stage23
```

This invokes `stage26_pipeline.py --stage final` with the 100-seed
budget and the full ablation matrix. The output layout is the same
as Stage-26 (canonical Stage 26 layout:
`raw/aggregated/statistics/tables/figures/logs/manifest.json/summary.md`).

### 2.3 Expected statistical output

For each controller pair (anchor = `rule_based`), 5 metrics × 3
controllers = 15 paired comparisons. For the ablation, 5 modules ×
6 labels = 30 paired comparisons. Total: 45 paired comparisons with
Benjamini-Hochberg correction.

The expected effect sizes (from Stage-26 20-seed data):

| Comparison | Expected mean diff | Expected effect size |
|---|---:|---:|
| `dqn_core_only` vs `rule_based` (ENS) | +0.614 MWh | d = 1.37 |
| `dqn_core_only` vs `rule_based` (CMI) | +36.8 min | d = 1.37 |
| `full_stack` vs `rule_based` (ENS) | ≈ 0 | d ≈ 0 |
| `random` vs `rule_based` (ENS) | ≈ 0 | d ≈ 0 |

The 100-seed run should narrow the CI by sqrt(5) ≈ 2.24× and
strengthen the Wilcoxon p-value. The expected p-value for the
primary comparison (`dqn_core_only` vs `rule_based` on ENS) at
100 seeds is **p < 1e-6** based on the Stage-26 effect size.

For the ablation rows (after the Stage-42 harness wiring fix), we
have *no a priori expectation* — that's the point of running it.
The Stage-41 honest framing predicts:

* `no_lstm` vs `full_stack` on ENS: mean diff near 0 (LSTM is not
  wired in Stage-26; once wired, the contribution depends on how the
  LSTM output is consumed).
* `no_twin` vs `full_stack` on ENS: mean diff near 0 unless a
  consumer of `health_risk_score` is added.
* `no_predictive` vs `full_stack` on ENS: depends on how
  `enable_predictive_healing` is wired; Stage-41 has no evidence.

---

## 3. Acceptance criteria

The 100-seed final experiment **passes** if all of the following
hold:

1. **Reproducibility**: `git_sha` is recorded (requires moving the
   project into git). If `git_sha` is still `UNKNOWN`, document that
   in the manifest.
2. **Validity**: 0 invalid runs (or the invalid-run reasons are
   documented and the analysis excludes them).
3. **Sign convention**: every paired comparison's `mean_difference`
   has the documented sign (anchor - other for lower-is-better,
   other - anchor for higher-is-better). Pin via
   `tests/test_metric_direction_audit.py`.
4. **Primary contribution holds**: `dqn_core_only` ENS / CMI is
   significantly lower than `rule_based` at p < 1e-6 (or stricter)
   with Cohen's d > 1.0.
5. **Ablation rows discriminate**: the 5 ablation labels
   (`full_stack`, `no_lstm`, `no_twin`, `no_predictive`, `no_reward`)
   produce *different* per-seed ENS distributions — i.e. the
   harness-wiring fix actually worked. If the rows are still
   indistinguishable, the harness wiring is still broken and the
   fix is incomplete.
6. **Effect sizes reported**: Cohen's d with qualitative label
   (negligible / small / medium / large) for every comparison.
7. **BH correction applied**: 45 raw p-values corrected, all
   reported.
8. **Manifest records every dependency version** (Python, numpy,
   scipy, networkx, pandas, torch, matplotlib).

---

## 4. Failure-mode handling

* If the 100-seed run exposes a seed where the runner crashes, the
  seed is recorded as invalid in `manifest.json` with the
  `InvalidRunReason`. The aggregate statistics exclude the invalid
  run. Document this as a known limitation in `docs/LIMITATIONS.md`.
* If the harness-wiring fix produces *more* variance per ablation
  row than the Stage-26 numbers, that's evidence the wiring is
  working. Report it honestly — the Stage-26 numbers are an
  under-estimate of the per-module variance.
* If the `dqn_core_only` advantage *shrinks* at 100 seeds, report
  that honestly. Do not cherry-pick seeds to recover the Stage-26
  effect size.

---

## 5. Documentation requirements

After the 100-seed run, update:

* `docs/FINAL_PAPER_READINESS_REPORT.md` — section 5 (Main Results),
  section 6 (Ablation), section 18 (Scores).
* `docs/PAPER_OUTLINE.md` — section 3.4 (Experiments), section 3.5
  (Discussion), section 3.6 (Conclusion).
* `docs/STAGE_41_COMPLETION_REPORT.md` — section 8 (100-seed
  outcome) and section 21 (final status).

---

## 6. What this configuration does NOT specify

* The Stage-42 harness-wiring fix itself. That is a code change to
  `runner.py`, not a configuration.
* The seeding fix for `SmartGrid` construction (EHM-HIGH-009).
* The scenario matrix implementation (A-J, see
  `docs/STAGE_41_SCENARIO_MATRIX.md`). The Stage-23 final
  experiment uses the *default* scenario, not the harder ones.

---

## 7. Honest framing

> **The 100-seed final experiment is configured but not run.** The
> configuration is deterministic, reproducible, and has explicit
> acceptance criteria. Running it requires the Stage-42 harness-
> wiring fix (which is the actual scientific blocker) — without
> that fix, the 100-seed run would just reproduce the Stage-26
> numbers at higher precision. The Stage-42 wiring fix is the work
> that unlocks a *new* result.
