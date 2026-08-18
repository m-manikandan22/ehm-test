# CHECKPOINT_3_ABLATION.md — Stage 28

This document is the **post-ablation checkpoint**. It captures what
changed between Checkpoint 2 (CR fixes) and the ablation harness
becoming paper-grade.

> **TL;DR:** the ablation harness (Stage 19) is now deterministic
> given a seed, filters invalid runs, computes paired statistics,
> and writes the canonical outputs (`baseline_results.{json,csv}`,
> `ablation_results.{json,csv}`, `statistics.{json,md}`, plus
> `summary.json` and `manifest.json`). All 9 pre-baked
> configurations in `ABLATION_CONFIGS` produce non-trivial output.

---

## 1. What this checkpoint certifies

After Checkpoint 3, the following are **paper-ready**:

1. **Determinism** — `run_experiment` seeds every component that
   supports it (`make_rng(cfg.seed)` for the random policy; the
   ablation harness uses the same seed across all policies).
2. **Invalid-run exclusion** — `_per_policy(runs, include_invalid=False)`
   filters `validity.valid == False` runs from aggregate statistics.
3. **Paired statistics** — `paired_comparison()` in
   `backend/metrics/statistics.py` returns `n`, `mean_a`, `mean_b`,
   `mean_diff`, `t_stat`, `p_value`, `wilcoxon_p`, `cohens_d`,
   `ci95_low`, `ci95_high`.
4. **Markdown tables** — `render_markdown(tables)` produces a
   per-policy table and a paired-comparison table.
5. **Manifest capture** — every run records
   `seed_id`, `seed`, `weather_mode`, `controller_label`,
   `active_modules`, `disabled_modules`.

---

## 2. Pre-baked ablation configs

The `ABLATION_CONFIGS` dict (`backend/experiments/experiment_config.py`)
defines 9 configurations. Each turns a different capability on/off
in a single `ExperimentConfig`:

| Label | DQN | LSTM | Twin | Predictive | Reward | Storage | FLISR |
|-------|-----|------|------|------------|--------|---------|-------|
| `full_stack` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `no_lstm` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `no_twin` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| `no_predictive` | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| `no_reward` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| `dqn_core_only` | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| `rule_based` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `random` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `persistence` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

`full_stack` is the anchor for paired comparison; the paper reports
it against `rule_based`, `random`, `persistence`.

---

## 3. End-to-end pipeline

The `paper_experiment.py` driver runs the full pipeline:

```bash
python -m experiments.paper_experiment \
    --seeds 5 --ticks 50 --faults 5 --output-dir paper_results
```

Outputs (all written under `paper_results/`):

| File | Content |
|------|---------|
| `scenarios.json` | List of all generated scenarios. |
| `baseline_results.{json,csv}` | rule_based, random, persistence. |
| `baseline_table.md` | Markdown of per-policy baselines. |
| `ablation_results.{json,csv}` | full_stack + 5 ablation variants. |
| `ablation_table.md` | Markdown of the ablation table. |
| `statistics.{json,md}` | Paired t-test, Wilcoxon, Cohen's d, 95 % CI. |
| `manifest.json` | Environment provenance + run ledger. |
| `summary.json` | High-level roll-up. |

---

## 4. Honesty policy

* The ablation harness reports **what the simulator observed**,
  not what would happen in a real grid.
* `rule_based`, `random`, and `persistence` are honest baselines —
  they use the same grid, same scenario, same fault injection.
* `dqn_core_only` exists to isolate the contribution of the LSTM
  and the digital twin.
* ⚠️ **WITHDRAWN (EHM-CRIT-007):** the paper does **not** claim "DQN
  beats LSTM" or "twin beats LSTM"; it *previously* claimed "full_stack
  reduces mean ENS versus rule_based" (see `NOVELTY_MATRIX.md` §1 #11),
  but that claim is invalid — the replay runner never invokes the
  DQN/LSTM/twin modules and `dqn_core_only`'s lower ENS is a
  frozen-clock artifact, not a controller effect. Must be re-run under
  a corrected harness.

---

## 5. Known caveats

* `SmartGrid()` is non-deterministic (see
  `LIMITATIONS.md` §1.4). Per-claim numbers are still seed-correlated.
  Mitigation: report metrics averaged over `seeds=5` by default.
* Hybrid storage results may show ENS=0 on the default 49-node grid
  because the grid is too resilient to expose the difference. The
  paper describes this as "default-grid saturation" and references
  `experiments/run_hybrid_storage.py --seed ... --faults 8` as the
  stress-test variant.
* The `no_reward` ablation still uses a reward function internally
  (because the DQN policy was trained with reward shaping); the
  ablation here disables the *runtime* reward only.

---

## 6. Reproducibility

```bash
cd backend
python -m pytest tests/test_research_readiness.py \
               tests/test_paper_experiment.py \
               tests/test_upgrade.py -v
python -m experiments.paper_experiment \
    --seeds 5 --ticks 50 --faults 5 --output-dir paper_results
```

Both must exit 0 with the pinned seed for the paper to be
reproducible.
