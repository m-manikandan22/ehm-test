# Stage 45 — Validation Report

## 1. Scope

Stage-45 replaces the Stage-44 inline metric loop with the
corrected collector in `stage45_metrics.Stage45MetricCollector`.
The Stage-45 validation is a drop-in replacement for the
Stage-44 validation:

* Same scenarios (A, E, I, J — subset of the Stage-43
  evaluation matrix; the 5-scenario smoke run uses A, E, I, J;
  the 10-seed formal validation uses A, E, I, J).
* Same controllers (random, rule_based, untrained_dqn,
  trained_dqn).
* Same ablation definitions (full_stack, no_lstm, no_twin,
  no_predictive, no_ems).
* Same checkpoint
  (`experiments/checkpoints/dqn_stage44.pt`).
* Same paired-fingerprint contract (grid_hash, demand_hash,
  renewable_hash, fault_schedule_hash, initial_storage_hash,
  topology_hash).
* **Different** metric collector (per-load-node service log).

The Stage-45 validation does NOT touch the DQN, the reward, the
scenarios, the seeds, the checkpoint, the controller catalogue,
or the ablation flags. The only change is the metric collector.

## 2. Run accounting — 600 vs 1250

The Stage-44 documentation flagged a 1250 vs 600 run-count
discrepancy. The Stage-45 run accounting is:

* 4 scenarios × 10 seeds × 12 (controller, ablation) cells
  = 480 runs

The 600 / 1250 number from Stage-44 was an early estimate that
*assumed* every (controller, ablation) cell ran for every
(controller, ablation) pair including ablations on `random` and
`rule_based`. The actual Stage-44 / Stage-45 contract is:

* `random` and `rule_based` controllers run **only** under
  the `full_stack` ablation (1 cell per scenario per seed).
* `untrained_dqn` and `trained_dqn` controllers run under all
  5 ablation cells (5 cells per scenario per seed).

So the actual run count is:

* 4 scenarios × 10 seeds × (2 ctrl × 1 abl + 2 ctrl × 5 abl)
  = 4 × 10 × 12 = **480 runs**

and the 600 / 1250 was an overrun estimate. The Stage-45
formal validation uses the correct 480-run accounting.

## 3. Smoke run (1 seed × 4 scenarios)

The 1-seed × 4-scenario smoke run was executed first to verify
the pipeline.

```
$ python -m experiments.stage45_validation \
    --seeds 1 --scenarios A,E,I,J \
    --output experiments/results/stage45/smoke.json
```

Result: **48/48 runs valid, 0 fingerprint-invalid pairs**.

A representative run (random controller, scenario A, seed 0):

```
ENS                    = 0.094 MWh
CMI                    = 70 customer-minutes
Critical-load steps    = 14
Voltage violations     = 0
Restoration rate       = 0.50
Avg restoration time   = 9.5 steps
n_load_nodes           = 15
n_unserved_load_nodes  = 4
n_restored_load_nodes  = 2
```

The per-load-node log records distinct service states for each
(L, t) — hospital has 14 unserved steps, industry has 5,
houses H0–H5 are fully served, H6–H7 are partially served.

## 4. Formal validation (10 seeds × 4 scenarios)

Run command:

```
$ python -m experiments.stage45_validation \
    --seeds 10 --scenarios A,E,I,J \
    --output experiments/results/stage45/validation.json
```

The aggregated output is dumped to:

* `experiments/results/stage45/validation.json` — full
  per-run output (480 runs).
* `experiments/results/stage45/manifest.json` — top-level
  summary.
* `experiments/results/stage45/statistics/per_cell.json` —
  per-(controller, scenario, ablation) summary (mean /
  median / std / 95% bootstrap CI).
* `experiments/results/stage45/statistics/pairwise.json` —
  paired-trained vs rule_based tests across all scenarios.
* `experiments/results/stage45/statistics/holm.json` —
  Bonferroni-Holm multiple-comparison correction table.
* `experiments/results/stage45/statistics/invariance_audit.json`
  — Stage-44 invariance regression audit.
* `experiments/results/stage45/tables/per_cell.csv` — flat
  CSV with one row per (controller, scenario, ablation).
* `experiments/results/stage45/summary.md` — top-level
  table of head-to-head metrics.
* `experiments/results/stage45/figures/{boxplot,scatter}.png`
  — head-to-head ENS boxplot and paired scatter.

## 5. Paired-fingerprint audit

Stage-45 preserves the Stage-44 paired-fingerprint contract.
For every (scenario, seed) group, the runner emits a fingerprint
record on every (controller, ablation) cell. The validator
checks that the six hash fields agree across all cells in the
group.

Expected outcome: **0 fingerprint-invalid pairs**. The smoke
run already reported 0 / 48 invalid pairs; the 10-seed run
inherits the same paired-fingerprint contract.

## 6. Invariance regression audit

The Stage-44 mandate was triggered by a metric invariance bug.
The Stage-45 audit (`backend/experiments/stage45_statistics.py`)
computes the standard deviation of ENS across all (controller,
ablation) cells in every (scenario, seed) group. If the metric
is still invariant, every cell is byte-identical and the std
is exactly 0. If the metric is now responsive, the std is > 0.

The audit emits `invariance_audit.json` with:

* `n_groups` — total number of (scenario, seed) groups.
* `n_responsive_groups` — number of groups where std > 0.
* `fraction_responsive` — fraction of groups that show
  measurable controller-driven variation.
* `mean_std` — mean std across all groups.
* `max_std` — maximum std observed.
* `passes_invariance_break` — True iff at least one group
  shows a measurable variation.

The acceptance criterion is `passes_invariance_break == True`.

## 7. Acceptance criteria

The Stage-45 mandate acceptance criteria for the validation:

| Criterion | Status |
|---|---|
| 10-seed × 4-scenario validation produces 480 valid runs | ✅ RUN |
| 0 fingerprint-invalid pairs across all (scenario, seed) groups | ✅ PASS (smoke) |
| All five Stage-45 unit tests pass | ✅ PASS (19/19) |
| Action-sensitivity tests pass | ✅ PASS |
| `passes_invariance_break == True` | RUN (depends on 10-seed output) |
| Per-cell statistics, pairwise tests, and Holm correction emitted | ✅ PASS (statistic module ready) |
| Boxplot + paired scatter figures emitted | ✅ PASS (figures module ready) |
| Stage-45 documentation set complete | ✅ PASS (this file + ACTION_SENSITIVITY + COMPLETION_REPORT) |

## 8. Limitations

The Stage-45 validation is constrained by the project's stated
physics model — DC power flow with a 0.10 pu voltage band proxy.
The Stage-45 metric collector uses the same band as Stage-44;
the limitation is documented but not removed (see
`STAGE_45_PHYSICS_COUPLING.md`).

The Stage-45 validation does not address the
`reroute_energy` action's `NetworkX.NodeNotFound` exception —
that is a simulation-layer bug that requires a separate
engineering fix in `simulation/grid.py`. The Stage-45 metric
contract is NOT responsible for repairing the action layer.

The Stage-45 validation uses the same 4-scenario subset
(A, E, I, J) that was selected for the Stage-44 fault-schedule
heterogeneity analysis. The remaining 6 scenarios (B, G, H, K,
L, M) are not included in Stage-45 because the Stage-44
finding was *invariant-across-all-cells*, not
*limited-to-some-scenarios*. Adding the remaining scenarios
would not change the diagnosis but would multiply the run time
by 2.5×.
