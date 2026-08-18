# FINAL CORRECTED EXPERIMENT AUDIT — Experiment B

Date: 2026-08-05  |  Dataset: `correction_audit_phase1/experiment_B_corrected_rerun/experiment_B_runs.json`  |  Status: **FINAL**

---

## 1. Executive summary

The corrected Experiment B dataset is **complete and valid** (540/540 runs, 0 invalid; 30 seeds × 2 stress levels × 9 policies). The technical corrections in Phase 1 (TC-001 FLISR interface, TC-002 predictive dispatch, TC-003 twin lifecycle, TC-004 LSTM instrumentation, TC-005 no-twin fallback removal) are reflected in the corrected run: FLISR now executes every tick for every FLISR-enabled policy, and the Twin/LSTM/Predictive/DQN stages record per-run execution counters.

**What the corrected data support:** FLISR-enabled controllers reduce cumulative unserved energy versus the no-action baselines at both stress levels with Holm-corrected p < 0.05 — e.g. `full_stack` vs `persistence` severe median ENS **1329.8 vs 6223.7** (rel. change -78.3 %, Cliff's δ = -1.0).

**What the corrected data do NOT support:** every AI-stage claim (Twin, LSTM, Predictive, Reward shaping), the DQN-vs-rule-based claim, and all three remaining primary outcomes (restoration time, critical-load restoration, SAIDI) are INCONCLUSIVE — the AI stages do not alter the recorded grid trajectory (all DQN-based arms are bit-identical per seed) and the three outcomes are instrument-saturated. The 'computationally efficient' claim is CONTRADICTED (controller runtime ~100x `rule_based`).

## 2. Verdict

> **VERDICT: B — PAPER-READY WITH DISCLOSED LIMITATIONS.**

The corrected dataset is a valid scientific artifact and the reported favorable result (FLISR reduces ENS vs no-action baselines) is real and statistically robust. The paper may proceed **provided it**: (a) reports the AI-stage null results as observed rather than tuned; (b) discloses the saturated primary outcomes and the predictive null activation; (c) reports the computational overhead honestly; and (d) limits claims to the single SUPPORTED claim per `CORRECTED_CLAIM_AUDIT.md`. This is not verdict A because the headline pre-registered hypotheses (full_stack vs rule_based on PO1–PO4) are not supported, and not C/D because the data, modules, and analysis pipeline are all internally valid.

## 3. Scope and provenance

- **Source of truth:** `correction_audit_phase1/experiment_B_corrected_rerun/experiment_B_runs.json` (+ `.csv`, `experiment_B_manifest.json`). Frozen; read-only throughout this audit.
- **Design (frozen):** `correction_audit_phase1/CORRECTED_EXPERIMENT_MANIFEST.json`.
- **Corrections:** `correction_audit_phase1/TECHNICAL_CORRECTION_LOG.md` (TC-001…TC-006).
- **Pre-registration:** `paper_results_experiment_B/PRIMARY_OUTCOMES.md` (4 primary outcomes, Holm family = 4 per (level, pair)).
- **No reruns, no parameter changes, no post-result tuning.**

## 4. Dataset completeness

| check | result |
|---|---|
| Runs | 540 (540 valid, 0 invalid) |
| Design grid | 30 seeds × 2 levels × 9 policies = 540 combos, none missing, none duplicated |
| Per-cell n | 30 |
| Detail | `RUN_COMPLETENESS_REPORT.md` — PASS |

## 5. Module execution audit

| module | evidence |
|---|---|
| FLISR | 200 calls/run for FLISR-enabled policies; 0 for others |
| Digital Twin | 9800 updates/run for twin-enabled policies; 0 for `no_twin` |
| LSTM | 200 model calls/run for LSTM-enabled policies; 0 for `no_lstm` |
| Predictive | 200 assessments/run; **0 recommendations ever reached the grid (null activation)** |
| Verdicts | 4 PASS, 14 PASS WITH LIMITATION, 0 FAIL (`MODULE_EXECUTION_AUDIT.md`) |

## 6. Statistical analysis (primary outcomes)

Paired Wilcoxon signed-rank by seed; Holm-Bonferroni across the four primary outcomes within each (stress level, controller pair). Raw and adjusted p-values both stored. Full 64-row table: `CORRECTED_STATISTICAL_ANALYSIS.csv/.md/.json`.

## 7. Primary outcome results

| outcome | severe FS vs persistence | severe FS vs random | severe FS vs rule_based |
|---|---:|---:|---:|
| PO1 ENS (median) | 1329.8 vs 6223.7 | 1329.8 vs 6223.7 | 1329.8 vs 1309.9 |
| PO1 raw p / Holm p | 1.73e-6 / 6.94e-6 | 1.73e-6 / 6.94e-6 | 0.102 / 0.408 |
| PO2 restoration time | 0 vs 0 (saturated) | 0 vs 0 (saturated) | 0 vs 0 (saturated) |
| PO3 critical load % | 100 vs 100 (saturated) | 100 vs 100 (saturated) | 100 vs 100 (saturated) |
| PO4 SAIDI | 0 vs 0 (saturated) | 0 vs 0 (saturated) | 0 vs 0 (saturated) |

Only PO1 discriminates; PO1 is SUPPORTED vs persistence/random, INCONCLUSIVE vs rule_based (rule_based slightly better in medians). `PRIMARY_OUTCOMES_RESULTS.md`.

## 8. Ablation analysis

`full_stack` is numerically identical to every ablation (`no_lstm`, `no_twin`, `no_predictive`, `no_reward`) on every outcome at every seed. Diagnosis: the AI stages execute but never alter the recorded grid trajectory; module counters prove execution, and the ablation is reported as execution-presence evidence, not benefit. `ABLATION_ANALYSIS.md`.

## 9. Baseline analysis

- **Favorable:** `full_stack` ENS vs `persistence`/`random`: moderate 501.2 vs 909.4, severe 1329.8 vs 6223.7 (Holm p < 0.05).
- **Unfavorable:** `rule_based` median ENS is slightly lower than `full_stack` (moderate 449.7 vs 501.2; severe 1309.9 vs 1329.8) and not statistically different on PO1; `dqn_core_only` is identical to `full_stack`.
- **Cost:** `full_stack` controller runtime ~100x `rule_based`.
`BASELINE_ANALYSIS.md`, `SECONDARY_METRIC_MEDIANS.csv`.

## 10. Saturation recheck

FULL SATURATION (zero unique values) for `saidi`, `resilience_time_to_50pct_restoration`, `stress_critical_load_restored_pct`, `switching_operations`, `stress_restoration_rate` — i.e. three of four pre-registered primary outcomes cannot discriminate controllers by instrumentation, not by controller behavior. GOOD VARIANCE on ENS, resilience loss area, voltage violations, line overloads. `SATURATION_RECHECK.md`.

## 11. Experiment A vs B

Experiment A (nominal, 900 records, 100 seeds) vs Experiment B (stress, 540 records, 30 seeds) are reported **side-by-side, never pooled**. The A-vs-B loader bug (n = 0) is fixed. Stress escalation on shared seeds shows ENS rising from A nominal to B severe (e.g. `full_stack` 30 → 80) with voltage collapse indicators (average voltage 0.96 → 0.22 pu). `EXPERIMENT_A_VS_B_CORRECTED.md/.csv`.

## 12. Tables and figures

- Tables: 7 markdown tables (with matching .csv): Table1_experimental_configuration.md, Table2_baseline_comparison.md, Table3_primary_outcomes.md, Table4_ablation_study.md, Table5_statistical_significance_effect_sizes.md, Table6_module_execution_evidence.md, Table7_experiment_A_vs_B.md.
- Figures: 10 PNG/PDF figures: fig01_ens_by_policy.png, fig02_saturated_restoration_metrics.png, fig03_critical_load_restoration.png, fig04_saidi_saifi.png, fig05_resilience_comparison.png, fig06_baseline_comparison.png, fig07_ablation_comparison.png, fig08_runtime_computational_cost.png, fig09_experiment_a_vs_b.png, fig10_module_execution_evidence.png.
All generated from corrected data only (`step10_tables.py`, `step11_figures.py`).

## 13. Claim audit

| classification | count | claims |
|---|---|---|
| SUPPORTED | 1 | FLISR-enabled EHM reduces ENS vs no-action baselines |
| CONTRADICTED | 1 | EHM is computationally efficient |
| INCONCLUSIVE | 9 | ENS-vs-rule_based, restoration time, critical load, SAIDI, Twin, LSTM, Predictive, Reward shaping, DQN-vs-rule_based |
| NOT TESTED | 2 | real-world validation, publication-grade IEEE-13 validation |

`CORRECTED_CLAIM_AUDIT.md`.

## 14. Limitation audit

L1 simulation-only; L2 synthetic 49-node testbed; L3 demonstrative IEEE-13; L4 n = 30; L5 predictive null activation; L6 twin lifecycle; L7 weather/fault simplification; L8 instrumentation saturation; L9 DQN trajectory decoupling; L10 computational cost; L11 A/B not pooled; L12 reward shaping not instrumented; L13 no post-result tuning; L14 generalisability. `LIMITATION_AUDIT.md`.

## 15. Final independent audit

**23 PASS, 1 PASS WITH NOTE, 0 FAIL** across the 24-item checklist (the note is the disclosed predictive null activation). `FINAL_INDEPENDENT_AUDIT.md`.

## 16. Artifacts manifest

| artifact | path |
|---|---|
| Corrected dataset | `correction_audit_phase1/experiment_B_corrected_rerun/experiment_B_runs.json` (+ `.csv`, `experiment_B_manifest.json`) |
| Frozen manifest | `correction_audit_phase1/CORRECTED_EXPERIMENT_MANIFEST.json` |
| Correction log | `correction_audit_phase1/TECHNICAL_CORRECTION_LOG.md` |
| Pre-registration | `paper_results_experiment_B/PRIMARY_OUTCOMES.md` |
| Statistics | `CORRECTED_STATISTICAL_ANALYSIS.csv/.md/.json` |
| Reports | `RUN_COMPLETENESS_REPORT.md`, `MODULE_EXECUTION_AUDIT.md`, `PRIMARY_OUTCOMES_RESULTS.md`, `ABLATION_ANALYSIS.md`, `BASELINE_ANALYSIS.md`, `SATURATION_RECHECK.md`, `EXPERIMENT_A_VS_B_CORRECTED.md`, `CORRECTED_CLAIM_AUDIT.md`, `LIMITATION_AUDIT.md`, `FINAL_INDEPENDENT_AUDIT.md` |
| Tables | `tables/Table1..Table7` (.csv + .md) |
| Figures | `figures/fig01..fig10` (.png + .pdf) |

---

_This audit performed no reruns, modified no raw values, and tuned nothing. All numbers are re-derived from the frozen corrected dataset._
