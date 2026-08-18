# Experiments — Scientific Validation Reference

This document is the single source of truth for what the `experiments/`
framework does, what it does not do, and how to run it.

## Status

The EHM-simulation project is **demonstrative, not research-grade**.
The numbers it produces are reproducible and self-consistent, but they
are counts of what happened *inside the simulator*, not measurements
against a calibrated physical system. They are suitable for comparing
controllers on the same simulator but should not be quoted as if they
came from field-deployed hardware or a calibrated IEEE 13-bus
distribution feeder.

See `docs/VALIDATION.md` for the per-claim validation status.

## Modules

| File | Purpose |
|------|---------|
| `experiments/experiment_config.py` | `ExperimentConfig` dataclass with 9 boolean module flags. Single source of truth for ablation. |
| `experiments/scenario.py` | `Scenario` + `FaultEvent`. Deterministic per-seed scenario generation + replay. |
| `experiments/validity.py` | `InvalidRunReason` enum + `ValidityReport` + `check_run_validity()`. NaN / Inf / impossible-voltage / topology guards. |
| `experiments/research_metrics.py` | `MetricCollector` + `compute_research_metrics()`. Per-step bookkeeping; final per-run metric dict. |
| `experiments/runner.py` | Top-level driver. Runs `(config, seed, weather)` grid → `runner.json` + `runner.csv` + manifest. |
| `experiments/tables.py` | Consumes `runner.json` → `tables.json` / `tables.csv` / `tables.md` (per-policy + paired comparison). |
| `experiments/ieee13_validation.py` | Compares EHM DC PF vs. pandapower DC PF on the IEEE 13-bus feeder. |

## Reproducibility primitives

Every run begins with `utils.seeds.set_global_seed(s)` which seeds:
- Python `random`
- NumPy global state and default RNG
- PyTorch CPU + CUDA RNGs (if available)
- Records the seed in an env var for downstream tools

The runner additionally seeds the per-run RNG with
`config.seed + scenario.seed` so incidental randomness inside the
controller and the grid are reproducible per (config, scenario) pair.

The `manifest.json` file captures:

- Git commit of the working tree
- Python, NumPy, PyTorch, NetworkX, pandapower versions
- Every config used (with `active_modules` / `disabled_modules`)
- Every scenario used (fault list, weather mode)

This is sufficient to reproduce any single run from scratch.

## Pre-baked ablation configurations

| Label | Active modules | Disabled |
|-------|----------------|----------|
| `full_stack`     | dqn, lstm, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | — |
| `no_lstm`        | dqn, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | lstm |
| `no_twin`        | dqn, lstm, predictive_healing, reward_shaping, flisr, ems, storage, xai | digital_twin |
| `no_predictive`  | dqn, lstm, digital_twin, reward_shaping, flisr, ems, storage, xai | predictive_healing |
| `no_reward`      | dqn, lstm, digital_twin, predictive_healing, flisr, ems, storage, xai | reward_shaping |
| `dqn_core_only`  | dqn, flisr | lstm, digital_twin, predictive_healing, reward_shaping, ems, storage, xai |
| `rule_based`     | flisr | dqn, lstm, digital_twin, predictive_healing, reward_shaping, ems, storage, xai |
| `random`         | — | everything |
| `persistence`    | — | everything (no actions ever issued) |

**These flags genuinely alter runtime behaviour.** The runner checks
each flag before invoking the corresponding module; flipping a flag
*will* bypass the module at runtime, not merely relabel the run.

## Standard run

```bash
python -m experiments.runner \
    --seeds 3 --ticks 50 --faults 2 \
    --weather normal,high_demand,storm \
    --policies random,rule_based,no_lstm,no_twin,no_predictive,no_reward,dqn_core_only,full_stack \
    --output experiments/results/runner.json \
    --manifest experiments/results/runner.manifest.json
```

Outputs:
- `runner.json` — structured per-run report.
- `runner.csv` — flat table, one row per run.
- `runner.manifest.json` — reproducibility manifest.

## One-command paper experiment

For a paper-grade sweep — baseline comparison + ablation + tables +
manifest, all in one command — use:

```bash
python -m experiments.paper_experiment \
    --seeds 100 --ticks 200 --faults 3 \
    --policies random,rule_based,dqn_core_only,full_stack \
    --ablation-policies full_stack,no_lstm,no_twin,no_predictive,no_reward,dqn_core_only \
    --output experiments/results/paper
```

Outputs land in `experiments/results/paper/`:

- `scenarios.json` — every (seed, weather) Scenario.
- `baseline_results.json` / `baseline_results.csv` — the controller
  comparison.
- `ablation_results.json` / `ablation_results.csv` — the ablation
  matrix.
- `baseline_table.md` / `ablation_table.md` — paper-friendly tables.
- `statistics.json` / `statistics.md` — paired tests, CIs, effect
  sizes.
- `manifest.json` — reproducibility record.
- `summary.json` — high-level counts and validity rates.

Smoke version (seconds):

```bash
python -m experiments.paper_experiment \
    --seeds 3 --ticks 20 --faults 1
```

## Generating paper tables

```bash
python -m experiments.tables \
    --input experiments/results/runner.json \
    --output experiments/results/tables.json \
    --csv experiments/results/tables.csv \
    --md experiments/results/tables.md \
    --anchor rule_based
```

The Markdown report contains:

1. **Per-policy summary** — mean ± std of every metric for every
   policy (n=0 means the metric was not produced).
2. **Paired comparison vs. anchor** — for each non-anchor policy and
   each metric, a paired t-test, Wilcoxon signed-rank, Cohen's d,
   and a significance flag at α=0.05.

## IEEE 13-bus validation

```bash
python -m experiments.ieee13_validation \
    --output experiments/results/ieee13_validation.json
```

Compares EHM DC PF against pandapower DC PF on the IEEE 13-bus
balanced positive-sequence equivalent. Reports max |angle_diff_rad|
and max |line_flow_diff_mw|.

**Status:** The IEEE 13-bus model in EHM is a balanced
positive-sequence equivalent. Three-phase unbalanced loads are
collapsed to equivalent positive sequence before the solve. A full
three-phase unbalanced AC PF is deferred — see
`docs/digital_twin.md` and `docs/power_flow.md` for the deferred
features list.

## Honest limitations

- The DQN is not trained to publication-grade convergence. The
  replay-buffer warm-up is rule-guided bootstrapping, **not**
  imitation learning — see `docs/RESEARCH_NOTES.md` for the exact
  definition.
- The digital twin's `failure_probability` / `failure_risk_indicator`
  is a piecewise-linear mapping of `health`, **not** a calibrated
  probability model. Constants are engineering rule-of-thumb values,
  not fitted parameters.
- Carbon, cost, and ENS estimates use the EHM `metrics/carbon_economic`
  module with documented assumed carbon intensities. They are not
  market-clearing prices.
- The advanced "AI planner" is a constrained greedy + local-search
  heuristic, not a deep RL agent.
- Validity guards catch NaN/Inf/impossible voltage. They do **not**
  catch subtle semantic bugs (e.g. silently wrong restoration order).

## Files

```
experiments/
├── __init__.py
├── experiment_config.py
├── scenario.py
├── validity.py
├── research_metrics.py
├── runner.py
├── tables.py
├── ieee13_validation.py
├── baselines/
│   ├── __init__.py
│   ├── rule_based_flisr.py
│   ├── dqn_only.py
│   └── persistence.py
└── results/         (created at runtime)
    ├── runner.json
    ├── runner.csv
    ├── runner.manifest.json
    ├── tables.json
    ├── tables.csv
    ├── tables.md
    └── ieee13_validation.json
```