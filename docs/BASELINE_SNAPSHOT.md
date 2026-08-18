# Stage 0 — Project Baseline Snapshot

Captured before any modifications. This document records the state of the
repository at the moment the master execution prompt began, so that any later
work can be diffed against a known point.

## Git state

- `git rev-parse HEAD` -> **fatal: not a git repository**
- `git status`        -> **fatal: not a git repository**
- `git branch`        -> n/a (no .git directory at repository root)

The repository is **not under version control** in its current state. The
historical correction-audit and `paper_results` directories therefore serve as
the only persistent record of pre-existing experimental work. They must be
treated as read-only evidence and must not be overwritten or deleted without
explicit justification.

## Top-level layout

```
EHM-paper/
├── backend/                # Python simulation, RL, API, tests
├── frontend/               # React/Vite dashboard (node_modules + dist present)
├── docs/                   # Project documentation
├── experiments/            # Experiment scripts, smoke/stress/final results
├── paper_results/          # Final paper artefacts (figures/tables/reports)
├── paper_results_experiment_B/  # Final-paper artefacts, experiment B
├── correction_audit_phase1/     # Pre-correction audit snapshots
├── correction_audit_phase2/     # Post-correction audit snapshots
├── main.md                 # Master specification (this project)
├── README.md
├── requirements.txt
├── docker-compose.yml
├── pyrightconfig.json
├── collect_files.py
├── inference.py            # Legacy standalone inference script
├── test_diag.py            # Legacy diagnostics script
├── test_flisr.py           # Legacy FLISR test
└── test_grid.py            # Legacy grid test
```

## Historical experiment artefacts (preserved, not modified)

- `experiments/results/final_paper/` — final-paper artefacts (ablation,
  baseline, statistics, validation, manifest, logs, preflight, environment).
- `experiments/results/experiment_B_stress/` — stress benchmark pilot
  (PHASE* scripts, smoke runs, claim audit, scientific wording audit).
- `paper_results/` and `paper_results_experiment_B/` — paper-grade tables,
  figures, reports, raw data.
- `correction_audit_phase1/experiment_B_corrected_rerun/` — corrected re-run.

These directories must be treated as historical evidence. Any new experiment
run for the final paper should write to a fresh directory such as
`experiments/results/paper/<RUN_ID>/` to avoid clobbering prior runs.

## First checkpoint commitment

No file in `paper_results/`, `paper_results_experiment_B/`,
`correction_audit_phase1/`, or `correction_audit_phase2/` will be modified or
deleted unless the new master specification explicitly requires it and the
change is documented in `docs/PAPER_READINESS_AUDIT.md`.

## Next actions

1. Run existing test suite and record results.
2. Read core modules to populate `docs/PAPER_READINESS_AUDIT.md`.
3. Build `docs/REQUIREMENTS_TRACEABILITY.md` before any modification.
