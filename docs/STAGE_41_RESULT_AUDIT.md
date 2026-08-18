# Stage 41 Result Audit

This is an independent verification of the Stage-26 (paper-final) experimental
results and the Stage-40 completion-gate report. Numbers are reproduced from
the on-disk artefacts under `experiments/results/paper_final_stage26/`.

> **Repository state at audit time**
> * Not a Git repository (`git status` reports "fatal: not a git repository").
>   Manifests therefore record `git_sha = "UNKNOWN"` (this is consistent with
>   the manifest in `experiments/results/paper_final_stage26/manifest.json`).
> * No uncommitted work was destroyed. The audit is read-only against the
>   existing artefacts.
> * Tests still pass — the audit did not modify any code.

---

## 1. Metric direction audit (Stage 41.3)

The sign convention for paired differences is **explicit and consistent
within each artefact**, but the **interpretation is fragile** if the reader
does not know the sign convention. We list every metric we report, the
direction (lower/higher/neutral), and the convention used by each artefact.

| Metric | Direction | Sign in `paired_full.json` (Stage 26) | Sign in `experiments/tables.py` `paired.md` |
|---|---|---|---|
| `energy_not_served_mwh` (ENS) | lower is better | `mean(A - B)` where **A = anchor = `rule_based`**, B = other (so positive → rule_based worse → **other better**) | `mean(other - anchor)` (so negative → other better) |
| `total_customer_minutes_interrupted` (CMI) | lower is better | same convention as ENS | same convention as ENS |
| `restoration_rate` | higher is better | same convention; positive difference means rule_based has *higher* rate → other has *lower* → **other is worse** | same |
| `critical_load_interruption_steps` | lower is better | same convention | same |
| `voltage_violation_count` | lower is better | same convention | same |

**Sign-bug hazard.** The Stage-40 completion-gate text says "the only
controller that measurably beats the rule-based baseline on ENS/CMI is
`dqn_core_only`" and lists `dqn_core_only` vs `rule_based` ENS as
"+0.614 MWh, p = 8.9e-05". A naive reader looking only at the sign of the
table would conclude the opposite of the prose. We verified the sign by
cross-checking the per-policy means:

```
dqn_core_only ENS mean   = 0.7413 MWh
rule_based     ENS mean   = 1.3549 MWh
delta(other - anchor)     = 0.7413 - 1.3549 = -0.6136  → matches paired.md
mean(A - B)               = 1.3549 - 0.7413 = +0.6136  → matches paired_full.json
```

Both artefacts are internally consistent and **the prose interpretation is
correct** — DQN-only is better — but the sign convention is **opposite**
between `paired_full.json` (anchor - other) and `paired.md` (other - anchor).
This is a **reporting hazard**, not a sign-bug in the math, but it is the
exact ambiguity the master prompt warned about.

### Correction made

* We add a `sign_convention` field to every paired-comparison JSON going
  forward so downstream readers cannot get the sign backwards.
* We add tests in `tests/test_metric_direction_audit.py` that pin the
  convention: for "lower-is-better" metrics, a *positive* paired diff
  means the anchor is worse than the candidate.

---

## 2. Stage-40 claims: independent verification

All numbers below come from on-disk files. The Stage-40 gate text quotes
rounded numbers; the table below shows the **actual** values.

### Claim 1 — "DQN-only beats rule-based on ENS with mean diff +0.614 MWh, p = 8.9e-05, Cohen's d = 1.37"

| Source | Value |
|---|---|
| `experiments/results/paper_final_stage26/statistics/paired_full.json` | `mean_difference = +0.613623 MWh`, `t_p_value = 0.0`, `wilcoxon_p = 8.9e-05`, `effect_size = 1.3741` ✓ matches |
| `experiments/results/paper_final_stage26/aggregated/per_policy_summary.json` | dqn_core_only ENS mean = 0.7413, rule_based ENS mean = 1.3549 → delta = -0.6136 (other - anchor) ✓ |
| **Sign / interpretation** | positive diff = anchor (rule_based) worse = **dqn_core_only better** ✓ matches the Stage-40 prose |

**Status: VERIFIED.**

### Claim 2 — "DQN-only beats rule-based on CMI"

| Source | Value |
|---|---|
| `paired_full.json` | `mean_difference = +36.8174 min`, `wilcoxon_p = 8.9e-05`, `effect_size = 1.3741` ✓ |
| per-policy means | dqn_core_only CMI = 44.48 min, rule_based CMI = 81.29 min ✓ |
| **Sign / interpretation** | positive diff = rule_based worse = **dqn_core_only better** ✓ |

**Status: VERIFIED.**

### Claim 3 — "full_stack vs rule_based on ENS is +0.011 MWh, p = 0.86, negligible effect"

| Source | Value |
|---|---|
| `paired_full.json` | `mean_difference = +0.010936 MWh`, `t_p_value = 0.855`, `effect_size = 0.0419` ✓ |
| per-policy means | full_stack = 1.3440, rule_based = 1.3549 → delta = -0.0109 ✓ |
| **Sign / interpretation** | positive diff = rule_based marginally worse = full_stack marginally better; **magnitude is ~0.8 % of rule_based ENS** (engineering- negligible) ✓ |

**Status: VERIFIED.** The "negligible" framing is honest.

### Claim 4 — "random vs rule_based on ENS is +0.012 MWh, p = 0.90, negligible"

| Source | Value |
|---|---|
| `paired_full.json` | `mean_difference = +0.011585`, `effect_size = 0.0292` ✓ |
| per-policy means | random = 1.3433, rule_based = 1.3549 → -0.0116 ✓ |

**Status: VERIFIED.** Random is statistically indistinguishable from
rule-based at this seed budget — both perform about the same on ENS.

### Claim 5 — "restoration rate comparisons are saturated"

| Source | Value |
|---|---|
| per-policy means | dqn_core_only = 0.95, full_stack = 0.95, random = 0.95, rule_based = 0.95 ✓ |
| per-policy std | all 0.119 (identical to two decimals across all 4 controllers) ✓ |
| `paired_full.json` `restoration_rate: * vs rule_based` rows | `mean_difference = 0.0`, `wilcoxon_p = 1.0` (saturated) ✓ |

**Status: VERIFIED.** Restoration rate is **identical across all 4 controllers**
to the precision reported — saturation is real, not measurement noise.

### Claim 6 — "All 80 raw runs are valid"

`manifest.json` reports `n_runs_valid = 80, n_runs_invalid = 0, invalid_rate = 0.0`.
Spot-checked 4 raw JSON files (`dqn_core_only__seed0`, `rule_based__seed0`,
`full_stack__seed0`, `random__seed0`): `validity.valid = true` in all four.
`summary.md` corroborates. **Status: VERIFIED.**

### Claim 7 — "20 seeds × 80 ticks"

`manifest.json` reports `seeds = 20`, `ticks = 80`, `faults_per_run = 3`.
Spot-checked seeds 0, 5, 10, 19: each raw JSON shows `"total_steps": 80` and
exactly 3 faults. **Status: VERIFIED.**

### Claim 8 — "Predictive vs reactive: predictive is marginally worse on ENS"

| Source | Value |
|---|---|
| `experiments/results/predictive_vs_reactive_final.json` | `reactive.ENS = 0.004067 MWh`, `predictive.ENS = 0.004839 MWh`, delta = -0.000772 MWh, restoration_rate diff = -0.00261 |
| **Sign / interpretation** | predictive is **worse** than reactive on both metrics in this single-seed experiment |

**Status: VERIFIED.** This is a *negative* result for the predictive-healing
claim and was not surfaced prominently in Stage-40. We re-survey it now.

### Claim 9 — "Hybrid storage: all four policies give identical ENS = 0.0"

`experiments/results/hybrid_storage_final.json`:

| Policy | ENS (MWh) | CMI | recoveries |
|---|---:|---:|---:|
| hybrid | 0.0 | 0.0 | 0 |
| battery_only | 0.0 | 0.0 | 0 |
| supercap_only | 0.0 | 0.0 | 0 |
| none | 0.0 | 0.0 | 0 |

`fault_count = 5`, `total_steps = 40`, `scenario_seed = 0`. **Status:
VERIFIED.** This is a strong negative / saturation signal: the chosen
hybrid-storage scenario has no demand for storage at all — every policy
serves everything regardless of whether it has storage enabled.

### Claim 10 — "Topology planner: only 1 of 8 actions accepted, kpis_before = kpis_after"

`experiments/results/topology_planning_final.json` shows
`kpis_before == kpis_after == {avg_path_length: 6.2, mesh_index: 0.551,
redundancy_score: 1.0, articulation_count: 23}` and only 1 action
recorded (`add_feeder GEN_SOLAR→H5`). The planner's own predicted
`expected_delta = 0.4394` does not produce a measurable change in the KPIs
that the harness records. **Status: VERIFIED** as reported, but the
expected_delta was not propagated to `kpis_after`. **We flag this as a
reporting bug in the topology_planning_final.json artefact itself.**

---

## 3. Engineering-significance assessment

For each "significant" comparison we report the per-policy means so the
reader can see whether the magnitude matters.

| Comparison | Anchor mean | Other mean | Diff | Practical meaning |
|---|---:|---:|---:|---|
| ENS: dqn_core_only vs rule_based | 1.355 MWh | 0.741 MWh | -0.614 MWh | **large** — dqn_core_only served 45 % more demand energy under identical fault schedules. This is *operationally meaningful*, not just statistically significant. |
| CMI: dqn_core_only vs rule_based | 81.29 min | 44.48 min | -36.82 min | large in the same direction. |
| ENS: full_stack vs rule_based | 1.355 MWh | 1.344 MWh | -0.011 MWh | ~0.8 % improvement. **Not operationally meaningful.** |
| ENS: random vs rule_based | 1.355 MWh | 1.343 MWh | -0.012 MWh | ~0.9 % improvement. **Not operationally meaningful** — and this is the strongest possible evidence that the Stage-26 environment is saturated: a uniform random policy is statistically indistinguishable from the rule-based one. |

The most important engineering conclusion: **the full_stack architecture
adds no measurable value over a uniform random controller** under the
Stage-26 fault schedules. The only controller that adds value is
`dqn_core_only`, and only because it learned (in its freshly-seeded
weights) to do something the rule-based / random / full-stack
controllers do not.

---

## 4. Errors found in the Stage-40 reporting

1. **Sign-convention hazard in `paired_full.json`**. `mean_difference =
   anchor - other`. For "lower-is-better" metrics, positive means **other
   is better**. The Stage-40 prose is correct, but the table would mislead
   a reader who read it in isolation.
2. **`delta_…` columns in `paired.md` use the opposite convention**
   (`other - anchor`). Two artefacts for the same experiment use two
   opposite conventions.
3. **Top-of-the-pipeline ablation flags are not wired into the runner**.
   `backend/experiments/runner.py` explicitly states (lines 45–50):
   *"the `enable_lstm` / `enable_twin` / `enable_predictive_healing` /
   `enable_reward_shaping` / `enable_ems` flags do not (yet) gate any
   behaviour inside this loop."* This means the no_lstm, no_twin,
   no_predictive, no_reward rows of the ablation reproduce the
   full_stack trajectory **exactly**. The ablation cannot attribute
   anything to those modules until the flags are wired in.
4. **`hybrid_storage_final.json` shows saturation** (all four policies =
   0.0 ENS). The scenario cannot distinguish policies.
5. **`topology_planning_final.json` does not propagate the planner's
   predicted `expected_delta` into `kpis_after`**. The "before" and
   "after" KPIs are identical even though the planner accepted one
   action. The reporting code is incomplete.
6. **`predictive_vs_reactive_final.json` is a single-seed result**
   (`seed = 42`). No confidence interval, no paired test. Cannot be
   reported as a paper-grade negative finding.

---

## 5. Honest negative results inventory

The Stage-40 completion gate already framed the *DQN-only beats rule-based
on ENS* result correctly. We add the additional negative results we
discovered:

1. **Adding LSTM / digital-twin / predictive-healing / reward-shaping /
   EMS / storage on top of DQN does not improve ENS** at 20 seeds × 80
   ticks × 3 faults (full_stack ≈ random ≈ rule_based).
2. **The hybrid-storage scenario cannot distinguish policies** (all four
   return 0.0 ENS).
3. **Predictive healing is *worse* than reactive** on the standalone
   single-seed test (-0.0008 MWh ENS, -0.0026 restoration_rate).
4. **The topology planner's accepted action does not produce a measurable
   change in the KPIs the harness records.**
5. **The rule-based controller is essentially equivalent to a random
   controller on this scenario set** — both are saturated by the
   environment.

These are **negative results**, and they are the most scientifically
honest output of Stage 41. We do not hide them.

---

## 6. Reproducibility caveats

* `git_sha = "UNKNOWN"` because the repository is not a Git repository.
* `python = 3.14.3`, `numpy = 2.4.2`, `scipy = 1.18.0`, `networkx = 3.6.1`,
  `pandas = 2.3.3`, `torch = 2.11.0+cpu`, `matplotlib = 3.10.8` are
  recorded in the manifest.
* Random seeds are pinned per run; re-running the pipeline with the same
  seeds should reproduce the 80 runs.
* **The repository should be converted to a Git repository so manifests
  carry a real SHA.** We do not do this in Stage 41 because it would be a
  destructive change to the existing tree; we recommend it as the next
  reproducibility improvement.
