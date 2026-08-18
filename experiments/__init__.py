"""experiments — Runnable scientific-validation harnesses for the EHM project.

Each module under this package is a self-contained script that:
  1. Builds (or takes) a SmartGrid.
  2. Runs one or more scenarios with controlled seeds.
  3. Aggregates metrics (IEEE 1366 indices, runtime metrics).
  4. Writes a JSON + Markdown report under ``experiments/results/``.

These are *framework only* by design. They support scientific claims
(per-seed reproducibility, paired-t comparisons, drop-one-component
ablation) but do not perform long training runs.
"""
