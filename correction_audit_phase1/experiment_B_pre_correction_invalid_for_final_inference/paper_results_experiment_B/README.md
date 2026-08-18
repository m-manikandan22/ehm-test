# Paper Results — Experiment B (Stress / Constrained Self-Healing)

This directory contains the complete peer-reviewable evidence for Experiment B. It is intentionally kept separate from the Experiment A deliverables in `paper_results/` and from the prototype directory `experiments/results/`.

## Layout

- `experiment_B_config.json` — frozen configuration (PHASE 17)
- `experiment_B_manifest.json` — input scenarios and configs
- `PRIMARY_OUTCOMES.md` — pre-registered primary outcomes
- `STRESS_BENCHMARK_PILOT_REPORT.md` — GO/NO-GO decision
- `EXPERIMENT_B_FINAL_RESULTS.md` — primary results report
- `raw/` — raw per-run data, statistics, environment
- `tables/` — derived tables (validity, runtime, A vs B)
- `statistics/` — paired-test CSVs reachable from the paper
- `figures/` — publication-quality PNG/PDF
- `validation/` — integrity manifest

## Reproducibility

The frozen config hash, the per-run data, and the integrity manifest are mutually cross-checked. See `validation/EXPERIMENT_B_INTEGRITY.md`.
