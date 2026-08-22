# Stage 46 — Statistical Audit

This document audits the Stage-45 statistical artefacts and
re-computes the paired comparison correctly. The headline finding
is that **the Stage-45 pairwise tests were unusable** (`n_pairs=1`
on every entry) due to a dedup bug in `experiments/stage45_statistics.py`;
this audit redoes the paired statistics correctly over the per-seed
runs and reports the actual evidence.

The audit is **read-only against Stage-45**: we do **not**
touch the simulator, the controller, the DQN checkpoint, the
reward, the training pipeline, or the random seeds. We measure
what is already on disk.

---

## 1. The Stage-45 pairwise statistics were broken

`experiments/results/stage45/statistics/pairwise.json` contains
144 entries, **every one of them with `n_pairs=1`** and a
Wilcoxon test that was rejected with `wilcoxon_too_few_samples`.

Root cause: in `experiments/stage45_statistics.py::_pairwise_tests`,
the paired samples are accumulated under a canonical key

```python
key = (small_a, large_a, small_b, large_b, scen, m)
if key in samples:
    continue   # ← BUG: every per-seed sample is collapsed
samples[key] = diffs
```

which dedupes across seeds, leaving one paired-sample "per
(scenario, ablation, metric, cell_a, cell_b)" — i.e., one
pair instead of ten. The Wilcoxon test then has only 1 pair
and reports `n_pairs=1, p_value=NaN`.

The Stage-45 Stage-45.2 statistics table that downstream
papers cite is therefore a one-sample comparison, not a paired
test.

The Stage-46 fix is to **redo the paired comparison directly
on the per-seed runs**:

```
experiments/stage46/statistics/pairwise_correct_stage45_full_stack.json
experiments/stage46/statistics/pairwise_correct_stage45_all_ablations.json
experiments/stage46/statistics/holm_correct_stage45.json
experiments/stage46/statistics/summary_pairwise_stage45_full_stack.md
experiments/stage46/statistics/summary_pairwise_stage45_all_ablations.md
```

The script (`experiments/stage46_audit_pairwise.py`) reads
`experiments/results/stage45/validation.json`, groups runs by
`(controller_label, ablation, scenario)` and seeds, and computes
a real Wilcoxon signed-rank test on the 10 paired samples per
group with Cohen's-d paired effect size.

---

## 2. The correctly-paired headline numbers

### 2.1 Trained DQN vs rule-based

| Scenario | Metric | mean_a (DQN) | mean_b (rule) | diff | Cohen's d | Wilcoxon p | Class |
|---|---|---:|---:|---:|---:|---:|---|
| A | ENS (MWh) | 4.815 | 4.873 | -0.058 | -0.550 | 0.0679 | NON-SIGNIFICANT_IMPROVEMENT |
| E | ENS (MWh) | 9.618 | 9.761 | -0.142 | -0.649 | 0.0679 | NON-SIGNIFICANT_IMPROVEMENT |
| I | ENS (MWh) | 4.842 | 4.873 | -0.031 | -0.552 | 0.0679 | NON-SIGNIFICANT_IMPROVEMENT |
| **J** | **ENS (MWh)** | **42.641** | **44.227** | **-1.587** | **-0.873** | **0.0051** | **SIGNIFICANT_IMPROVEMENT** |
| J | avg_restoration_steps | 96.7 | 156.5 | -59.8 | -0.571 | 0.0464 | SIGNIFICANT_IMPROVEMENT |
| J | customer-minutes interrupted | 3958.8 | 4245.9 | -287.1 | -0.796 | 0.0077 | SIGNIFICANT_IMPROVEMENT |

Interpretation: **trained DQN is essentially indistinguishable
from rule-based on A/E/I** (all p=0.068, just above α=0.05),
and **significantly better on J** (the hardest scenario), with
effect sizes of -0.55 to -0.87 (medium-to-large).

### 2.2 Trained DQN vs untrained DQN

| Scenario | Metric | mean_a | mean_b | diff | d | p | Class |
|---|---|---:|---:|---:|---:|---:|---|
| A | ENS (MWh) | 4.815 | 2.498 | +2.317 | +0.763 | 0.0280 | SIGNIFICANT_DEGRADATION |
| A | customer-minutes | 382.9 | 263.4 | +119.5 | +0.941 | 0.0180 | SIGNIFICANT_DEGRADATION |
| A | critical_load_interruption | 75.7 | 46.5 | +29.2 | +0.882 | 0.0431 | SIGNIFICANT_DEGRADATION |
| E | ENS (MWh) | 9.618 | 5.385 | +4.234 | +0.768 | 0.0499 | SIGNIFICANT_DEGRADATION |
| E | avg_restoration_steps | 21.9 | 12.7 | +9.2 | +0.962 | 0.0280 | SIGNIFICANT_DEGRADATION |
| I | ENS (MWh) | 4.842 | 2.534 | +2.308 | +0.761 | 0.0280 | SIGNIFICANT_DEGRADATION |
| I | critical_load_interruption | 75.7 | 46.5 | +29.2 | +0.882 | 0.0431 | SIGNIFICANT_DEGRADATION |
| J | ENS (MWh) | 42.641 | 26.953 | +15.687 | +0.705 | 0.374 | NON-SIG |
| **J** | **restoration_rate** | **0.124** | **0.064** | **+0.060** | **+0.772** | **0.0464** | **SIGNIFICANT_IMPROVEMENT** |

Interpretation: this is the **most important result**. On A/E/I,
the trained DQN is **statistically significantly WORSE** than the
randomly-initialised untrained DQN (effect sizes d ≈ +0.76 to
+0.96, p ≈ 0.018–0.049). On the hardest scenario J, training flips
the result: the trained DQN significantly improves restoration_rate
(+5.4 percentage points, p=0.046). On the other J metrics the
difference is non-significant but trends in the trained direction
(lower avg_restoration_steps by 30%, lower customer-minutes by 4%).

The interpretation is **not** "the trained DQN is overfit to J
and forgot the easier scenarios" — that is a tempting read, but
the ablation evidence (§3) shows the trained DQN's *actions* are
the same on every scenario. The trained DQN's policy surface is
almost identical to the untrained DQN's on A/E/I (it sees the same
inputs, picks nearly the same action distributions), but the few
percentage points of input shift that the trained network applies
to the same features happen to be **wrong** on A/E/I and **right**
on J.

### 2.3 Trained DQN vs random

| Scenario | Metric | mean_a | mean_b | diff | d | p | Class |
|---|---|---:|---:|---:|---:|---:|---|
| A | ENS (MWh) | 4.815 | 0.587 | +4.227 | +3.378 | 0.0051 | SIGNIFICANT_DEGRADATION |
| E | ENS (MWh) | 9.618 | 1.618 | +7.999 | +5.471 | 0.0051 | SIGNIFICANT_DEGRADATION |
| I | ENS (MWh) | 4.842 | 0.592 | +4.250 | +3.422 | 0.0051 | SIGNIFICANT_DEGRADATION |
| J | ENS (MWh) | 42.641 | 2.020 | +40.621 | +4.544 | 0.0051 | SIGNIFICANT_DEGRADATION |

Interpretation: random beats trained DQN on ENS by 6–20× across
all four scenarios (d=+3.4 to +5.5). This is a Stage-46 SURPRISE;
see `STAGE_46_RANDOM_BASELINE_AUDIT.md` for the action-trace
analysis explaining why.

### 2.4 Rule-based vs random

| Scenario | Metric | mean_a | mean_b | diff | d | p | Class |
|---|---|---:|---:|---:|---:|---:|---|
| A | ENS | 4.873 | 0.587 | +4.286 | +3.450 | 0.0051 | SIGNIFICANT_DEGRADATION |
| E | ENS | 9.761 | 1.618 | +8.142 | +5.670 | 0.0051 | SIGNIFICANT_DEGRADATION |
| J | ENS | 44.227 | 2.020 | +42.207 | +4.239 | 0.0051 | SIGNIFICANT_DEGRADATION |

Random beats rule-based similarly. See `STAGE_46_RANDOM_BASELINE_AUDIT.md`.

---

## 3. The "ablation" cells are identical — the Stage-45 ablation mechanism did not actually differ cells

The Stage-45 ablation table had 5 rows: `full_stack`,
`no_lstm`, `no_twin`, `no_predictive`, `no_ems`. According to
the Stage-45 documentation, each row is supposed to turn off one
piece of information flow (LSTM forecast, digital-twin risk map,
predictive healing, EMS scheduling) and isolate its marginal
contribution.

**Measured outcome (10-seed paired audit):**

| Scenario | full_stack ENS | no_lstm ENS | no_twin ENS | no_predictive ENS | no_ems ENS |
|---|---:|---:|---:|---:|---:|
| A (seed 0) | 5.135 | 5.135 | 5.135 | 5.135 | 5.135 |
| E (seed 0) | 10.323 | 10.323 | 10.323 | 10.323 | 10.323 |
| I (seed 0) | 5.135 | 5.135 | 5.135 | 5.135 | 5.135 |
| J (seed 0) | 56.709 | 56.709 | 56.709 | 56.709 | 56.709 |
| **A across all 10 seeds** | **5/10 differ** | 0/10 differ | 0/10 differ | 0/10 differ | 0/10 differ |

**All five ablation cells produced bit-identical rollout trajectories
(verified seed-by-seed).** This is not surprising once you look at
the wiring: the LSTM forecast in the DQN state vector is either a
constant `0.5` (no LSTM) or a constant `~0.5` (LSTM with no real
history; the prediction is `[0.5, 0.4, 0.0]` padded 10 times →
output also ~0.5). The twin risk-map features are either all zeros
(no twin registry) or the same digital-twin risk values computed
unconditionally in the loop body. The EMS, the twin, the predictive
healer are all gated by config flags in `experiments.runner.run_hybrid_episode`,
**but the Stage-45 validation runner (`experiments/stage45_validation.py`) does not
call `run_hybrid_episode`** — it calls `_run_controller_on_scenario`,
which has its own (almost-but-not-quite) duplicate wiring that
ignores most of the ablation flags:
- `enable_lstm` reaches `_Stage44DQNAdapter._enable_lstm` and gates the LSTM forecast — but as shown, the LSTM forecast is ~constant in both branches.
- `enable_twin` is implemented as `if enable_twin: twin = TwinRegistry()` on line 141; the ablation row `no_twin` therefore prevents the twin from being built, **but the DQN's twin-features block on line 227 is `if twin is not None:` regardless of `enable_twin`** — meaning all cells except `no_twin` get the same twin features, and `no_twin` gets zeros.
- `enable_predictive` is implemented as `if enable_predictive and twin is not None: ... PredictiveSelfHealer ...` on line 316-322. With the same twin gating, this means `no_twin` also loses predictive-healing for free (the configs are correlated).
- `enable_ems` is implemented as `if enable_ems: ems = EnergyManagementSystem(...)` on line 332; this **does** differ. But the EMS `run(grid)` call in the Stage-45 harness is built **fresh per step**, which means the EMS's SOC never accumulates across steps, and the dispatch history is empty. The EMS is effectively a no-op (see `STAGE_42_5_EMS_PERSISTENCE.md` for the same finding).

**So the Stage-45 ablation mechanism did not isolate the contribution
of any feature — the cells are degenerate.** This is a Stage-46
audit finding, not a code change. The Stage-46 docs document this
so reviewers don't take the "Stage-45 ablation table" at face value.

---

## 4. Holm-adjusted significance

With 144 paired tests in the full_stack audit, the smallest
p-values are:

| Test | p | Holm rank | threshold | rejected? |
|---|---:|---:|---:|---|
| `random vs rule_based | A | ENS` | 0.0051 | 1/144 | 0.05/144 | YES |
| `random vs rule_based | E | ENS` | 0.0051 | 2/144 | 0.05/143 | YES |
| `random vs trained_dqn | A | ENS` | 0.0051 | 1/144 | 0.05/144 | YES |
| `random vs trained_dqn | E | ENS` | 0.0051 | 2/144 | 0.05/143 | YES |
| `trained_dqn vs rule_based | J | ENS` | 0.0051 | 1/144 | 0.05/144 | YES |
| ... | ... | ... | ... | ... |

The Holm correction makes the dominant comparisons **stronger**:
random's ENS lead over rule_based/trained_dqn is significant at
the family-wise α=0.05 level. The trained_dqn vs rule_based
"trend" on A/E/I does NOT survive Holm (it remains p=0.068),
but the trained_dqn vs rule_based improvement on J DOES survive
Holm (p=0.0051).

---

## 5. What this audit does NOT establish

- **It does not establish** that the trained DQN is "useless" —
  it shows the trained DQN is at-best-tied with rule-based on
  A/E/I and significantly better on J.
- **It does not establish** that random "wins" — it shows random
  produces lower ENS *because* random takes no actions and therefore
  has no information-flow surface to fail on. Random's *other*
  metrics (restoration_rate on J, critical_load_interruption_steps
  on A/E/I) are worse than the trained DQN; see
  `STAGE_46_RANDOM_BASELINE_AUDIT.md`.
- **It does not establish** that the action-layer fix changed
  these rankings — the Stage-46 reroute fix corrects a bug
  that was hiding restoration, but the trained DQN did not
  use `use_supercapacitor` or `use_battery` heavily in the
  Stage-45 set of runs anyway. The before/after comparison is
  in `STAGE_46_VALIDATION_REPORT.md` (pending the in-progress
  Stage-46 validation run).

---

## 6. Reproducibility

- Script: `backend/experiments/stage46_audit_pairwise.py`
- Inputs: `backend/experiments/results/stage45/validation.json` (480 runs)
- Outputs: `backend/experiments/results/stage46/statistics/*`
- Random seed: not needed (read-only)
- Runtime: < 2 s
- Dependencies: numpy (offline), Python stdlib

The script is run as `python experiments/stage46_audit_pairwise.py`
from `backend/`. It writes six files; no Stage-45 artefacts are
modified.
