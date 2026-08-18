# EHM-simulation — Paper Results Package

This directory contains the *raw evidence* and *generated artifacts* used
for the final paper experiment. Every file here is the direct output of
a script in `experiments/results/final_paper/` or a verification
script in `backend/`.

## What is in this package

```
paper_results/
    README.md                       ← this file
    experiment_manifest.json        ← full experiment metadata + checksums
    final_experiment_config.json    ← frozen configuration at experiment run

    raw/
        baseline_results.json       ← per-run raw results (5 policies × 100 seeds)
        ablation_results.json       ← per-run raw results (6 policies × 100 seeds)
        manifest.json               ← input manifest (scenarios, configs, seeds)
        scenarios.json              ← pre-generated scenario list
        summary.json                ← summary statistics

    tables/
        baseline_comparison.csv     ← per-policy aggregate + paired tests
        ablation_table.csv          ← per-policy aggregate + paired tests
        statistical_tests.csv       ← one row per (anchor, other, metric) test
        validity_summary.csv        ← per-policy valid / invalid counts
        runtime_summary.csv         ← per-policy runtime statistics

    figures/
        saifi_by_controller.png/.pdf
        saidi_by_controller.png/.pdf
        ens_by_controller.png/.pdf
        restoration_time_seconds_by_controller.png/.pdf
        critical_load_restored_pct_by_controller.png/.pdf
        voltage_violation_count_by_controller.png/.pdf
        number_of_islands_by_controller.png/.pdf
        actions_taken_by_controller.png/.pdf
        runtime_s_by_controller.png/.pdf
        ablation_saidi_bar.png/.pdf
        ablation_ens_bar.png/.pdf
        baseline_runtime_bar.png/.pdf
        validity_summary.png/.pdf

    validation/
        ieee13_validation.json      ← EHM DC PF + pandapower DC PF + AC PF
        environment_report.json     ← Python/package versions
        test_summary.json           ← pytest stats

    reports/
        PRE_FLIGHT_REPORT.md        ← pre-flight go/no-go gate
        FINAL_RESULTS_SUMMARY.md    ← human-readable final results
```

## How each artifact was produced

| Artifact | Script |
|---|---|
| `environment_report.json` | `experiments/results/final_paper/environment/generate_environment_report.py` |
| `test_summary.json` | `python -m pytest backend/tests/ -v` (synthesised from output) |
| `ablation_integrity_report.json` | `experiments/results/final_paper/verify_ablation_integrity.py` |
| `reproducibility_report.json` | `experiments/results/final_paper/verify_reproducibility.py` |
| `validity_guards_report.json` | `experiments/results/final_paper/verify_validity_guards.py` |
| `ieee13_validation.json` | `PYTHONPATH=backend python experiments/ieee13_validation.py --output experiments/results/final_paper/validation/ieee13_validation.json` |
| `*preflight_results*` | `experiments/results/final_paper/preflight_experiment.py` |
| `*baseline_results.json` / `*ablation_results.json` | `experiments/results/final_paper/run_final_experiment.py` |
| `*statistics.json` / `*baseline_comparison.csv` / `*ablation_table.csv` / `*statistical_tests.csv` | `experiments/results/final_paper/compute_statistics.py` |
| `*_by_controller.png` / `*_bar.png` | `experiments/results/final_paper/generate_figures.py` |
| `experiment_manifest.json` | `experiments/results/final_paper/generate_manifest.py` |
| `FINAL_RESULTS_SUMMARY.md` | `experiments/results/final_paper/generate_final_summary.py` |

## What the experiment is

- **Seeds**: 0..99 (deterministic, paired across controllers)
- **Ticks per run**: 200
- **Faults per run**: 3
- **Weather modes**: `normal`
- **Baseline policies**: `random`, `persistence`, `rule_based`, `dqn_core_only`, `full_stack`
- **Ablation policies**: `full_stack`, `no_lstm`, `no_twin`, `no_predictive`, `no_reward`, `dqn_core_only`
- **Total runs**: 1100 (500 baseline + 600 ablation)
- **Valid runs**: 1100 (100.0%)
- **Total wall-clock**: 1595.5 s ≈ 26.6 min

## Sample of headline findings

(Simulation-based counts; not hardware measurements.)

- The 49-node grid in the demonstrated simulator is too forgiving for
  primary reliability indices to differentiate controllers: SAIFI,
  SAIDI, ENS, restoration time, voltage violation count, line
  overload count, switching operations, isolated nodes, load shedding
  events, number of islands, critical-load restored %, outage cost,
  and carbon are **identical across all five baseline controllers**
  within the tested scenario space.
- The DQN-based controllers (`dqn_core_only`, `full_stack`) and the
  ablations with `enable_dqn=True` show measurably higher
  `controller_runtime_s`, `power_flow_runtime_s`, and `runtime_s`
  than the non-DQN controllers.
- Small differences exist in `critical_load_restored_mw`,
  `frequency_deviation_count`, `line_overload_count`, `maifi`, and
  `total_load_mw` between DQN and non-DQN controllers.

## Caveats

- These are **simulation counts**, not empirical measurements.
- The Digital Twin `failure_risk_indicator` is a relative, simulation-
  based risk indicator — not a calibrated probability of failure.
- The IEEE-13 validation is a balanced positive-sequence equivalent,
  not a full three-phase unbalanced model.
- See `FINAL_RESULTS_SUMMARY.md` for the full set of supported
  conclusions, unsupported claims, and limitations.
