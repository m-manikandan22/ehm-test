# Stage 41 — Research-Contribution Discovery

> **Purpose**: rank the project's possible contributions by evidence,
> effect size, statistical support, engineering relevance,
> reproducibility and novelty. Assign each candidate one of:
>
> * PRIMARY CONTRIBUTION
> * SECONDARY CONTRIBUTION
> * SUPPORTING FEATURE
> * NEGATIVE RESULT
> * FUTURE WORK

This document is the most important output of Stage 41 because it
*commits the paper's narrative* to what the evidence actually shows.

---

## 1. Candidate contributions

### Candidate 1 — "A 5-action DQN with hand-coded action-mask
heuristic beats a 2-action reactive rule-based controller on ENS /
CMI under 3-fault/80-tick scenarios on the EHM 49-node grid"

| Dimension | Evidence |
|---|---|
| Effect size | dqn_core_only vs rule_based: ENS mean diff = -0.614 MWh (large, Cohen's d = 1.37); CMI mean diff = -36.82 min (large, Cohen's d = 1.37) |
| Statistical support | Wilcoxon p = 8.9e-05; BH-corrected p = 0.0 |
| Engineering relevance | DQN-only serves 45 % more demand energy under identical fault schedules. Operationally meaningful. |
| Reproducibility | 20 seeds × 80 ticks × 3 faults. Re-ran in a fresh 5-seed diagnostic and the same pattern held (rule_based worse; dqn_core_only better). |
| Novelty | "DQN beats rule-based on a small power-flow sim" is not new; the novelty is the *specific combination* of action mask + 5-action space + DC-PF proxy. |

**Classification: PRIMARY CONTRIBUTION.**

Caveat: this is *not* a claim about RL *learning*. The DQN's
advantage comes from the hand-coded action-mask heuristic, not from
the Q-network's gradient updates. The Q-network is freshly seeded
per run and never trains in eval mode. **The honest framing is
"action-mask-augmented DQN > reactive rule-based", not "trained DQN
> rule-based".**

### Candidate 2 — "A 9-stage FLISR with priority-aware tie selection
and EMS fallback restores FLISR-healable faults on the EHM 49-node
grid"

| Dimension | Evidence |
|---|---|
| Effect size | Restoration rate = 0.95 ± 0.12 across all controllers (saturated) |
| Statistical support | Saturated metric; no discrimination. |
| Engineering relevance | Restoration *works* — that's the engineering claim. |
| Reproducibility | Validated by `tests/test_flisr_9stage.py` and IEEE 13/33 feeders. |
| Novelty | The 9-stage FLISR with EMS fallback is documented in `docs/HYBRID_STORAGE.md` and the FLISR source. Some novelty in the priority-aware scoring. |

**Classification: SECONDARY CONTRIBUTION.**

Caveat: the restoration metric is saturated by the FLISR-healable
fault set. We cannot claim FLISR is "better than" alternatives
because no alternative exists in the harness.

### Candidate 3 — "A simulation-validated integrated resilience
framework combining FLISR + EMS + storage + forecasting + RL"

| Dimension | Evidence |
|---|---|
| Effect size | full_stack ≈ random ≈ rule_based on ENS / CMI / restoration_rate (Stage-26 result). |
| Statistical support | full_stack vs rule_based ENS p = 0.86, Cohen's d = 0.04 (negligible). |
| Engineering relevance | The full_stack architecture *exists* but the harness does not exercise LSTM / twin / predictive / reward / EMS as code paths. |
| Reproducibility | The artefacts reproduce, but they do not support the contribution. |
| Novelty | The *idea* is novel. The *evidence* is missing. |

**Classification: NEGATIVE RESULT (for the integrated framework
claim) + FUTURE WORK (for the necessary harness wiring).**

This is the most important *honest* finding of Stage 41. The
full_stack architecture does not outperform the 2-action
rule-based controller because the Stage-26 harness never invokes
the LSTM, the digital twin, predictive healing, or reward shaping.
The integrated-stack claim is therefore **not supported by the
Stage-26 evidence**. It is also not falsified — we cannot say
"the integrated stack doesn't help" because we never tested it.

### Candidate 4 — "Resilience-aware topology planning (AIPlanner)"

| Dimension | Evidence |
|---|---|
| Effect size | `topology_planning_final.json` shows kpis_before == kpis_after despite an accepted action. `topology_comparison.py` is `framework_only`. |
| Statistical support | None. |
| Engineering relevance | The planner's accepted action does not produce a measurable change in the recorded KPIs. |
| Reproducibility | Single-seed; N-1 analysis not invoked. |
| Novelty | The planner itself is novel; the evaluation is missing. |

**Classification: SUPPORTING FEATURE** (the planner is implemented
and documented) **+ FUTURE WORK** (the N-1 evaluation pipeline is
missing).

### Candidate 5 — "Digital-twin asset-health heuristic with
Arrhenius-style degradation"

| Dimension | Evidence |
|---|---|
| Effect size | None. `health_risk_score` has no consumer. |
| Statistical support | None. |
| Engineering relevance | None demonstrated. |
| Reproducibility | Deterministic per seed. |
| Novelty | Standard Arrhenius model — not novel. |

**Classification: SUPPORTING FEATURE** + **FUTURE WORK.**

### Candidate 6 — "LSTM demand forecaster"

| Dimension | Evidence |
|---|---|
| Effect size | None on the Stage-26 outcomes (predicted_load = 0.5 hard-coded). |
| Statistical support | None. |
| Engineering relevance | The model exists and is trained on synthetic data. |
| Reproducibility | Deterministic; no leakage tests pass. |
| Novelty | A small 2-layer LSTM on synthetic load is not novel. |

**Classification: SUPPORTING FEATURE** + **FUTURE WORK.**

### Candidate 7 — "Hybrid battery + supercapacitor storage model"

| Dimension | Evidence |
|---|---|
| Effect size | None on Stage-26 outcomes (no stress scenario). |
| Statistical support | None. |
| Engineering relevance | The model exists; the scenarios that would expose it don't. |
| Reproducibility | Deterministic. |
| Novelty | Standard. |

**Classification: SUPPORTING FEATURE** + **FUTURE WORK.**

### Candidate 8 — "Predictive healing based on LSTM load forecast"

| Dimension | Evidence |
|---|---|
| Effect size | `predictive_vs_reactive_final.json`: predictive ENS = 0.00484 MWh, reactive ENS = 0.00407 MWh. **Predictive is *worse* by 0.0008 MWh** in a single-seed experiment. |
| Statistical support | None (single seed). |
| Engineering relevance | Negative; this is a *negative result*. |
| Reproducibility | Deterministic. |
| Novelty | The idea is sound. |

**Classification: NEGATIVE RESULT** (in current implementation) +
**FUTURE WORK** (the idea is plausible but the harness doesn't
exercise it; the single-seed test is too small to draw conclusions).

### Candidate 9 — "Statistical testing infrastructure with BH
correction"

| Dimension | Evidence |
|---|---|
| Effect size | n/a — it's tooling. |
| Statistical support | Implements paired t, Wilcoxon, Cohen's d, Holm-Bonferroni, Benjamini-Hochberg. |
| Engineering relevance | Yes — supports paper claims. |
| Reproducibility | Deterministic, tested. |
| Novelty | Standard statistical methodology. |

**Classification: SUPPORTING INFRASTRUCTURE.**

### Candidate 10 — "IEEE 13-bus and IEEE 33-bus standard feeder
validation"

| Dimension | Evidence |
|---|---|
| Effect size | Validation passes (DC-PF converges, KCL residual < 1e-14). |
| Statistical support | n/a — it's a correctness check. |
| Engineering relevance | Yes — establishes the simulation engine is sane. |
| Reproducibility | Deterministic. |
| Novelty | Standard benchmarks. |

**Classification: SUPPORTING INFRASTRUCTURE.**

---

## 2. Final contribution ranking

| Rank | Candidate | Classification |
|---:|---|---|
| 1 | Candidate 1: action-mask-augmented DQN > reactive rule-based | **PRIMARY** |
| 2 | Candidate 2: 9-stage FLISR with priority-aware tie selection | **SECONDARY** |
| 3 | Candidate 3: integrated framework | **NEGATIVE RESULT + FUTURE WORK** |
| 4 | Candidate 4: topology planning (AIPlanner) | **SUPPORTING + FUTURE WORK** |
| 5 | Candidate 5: digital twin | **SUPPORTING + FUTURE WORK** |
| 6 | Candidate 6: LSTM | **SUPPORTING + FUTURE WORK** |
| 7 | Candidate 7: hybrid storage | **SUPPORTING + FUTURE WORK** |
| 8 | Candidate 8: predictive healing | **NEGATIVE RESULT + FUTURE WORK** |
| 9 | Candidate 9: statistical tooling | **SUPPORTING INFRASTRUCTURE** |
| 10 | Candidate 10: IEEE 13/33 validation | **SUPPORTING INFRASTRUCTURE** |

---

## 3. The paper we *can* write today

> **Title (provisional)**: *Action-Mask-Augmented DQN for Reactive
> Self-Healing on a 49-Node Distribution Feeder: A 5-Action
> Comparison with a 2-Action Rule-Based Controller*
>
> **Claim**: A 5-action DQN with a hand-coded action-mask heuristic
> (deficit → generation/battery; spike → supercapacitor; fault →
> reroute; always → load shift) outperforms a 2-action reactive
> rule-based controller on Energy-Not-Served and Customer-Minutes-
> Interrupted under 3-fault/80-tick scenarios on the EHM 49-node
> distribution test feeder (n=20 seeds, p < 1e-4, Cohen's d = 1.37).
>
> **What we cannot claim** (Stage-41 finding):
> * That LSTM, digital-twin, predictive-healing, or reward-shaping
>   contribute. The Stage-26 ablation harness does not exercise
>   these modules. Any paper claim about the *integrated stack* is
>   not supported by the Stage-26 evidence.
> * That the hybrid-storage model improves outcomes. The scenario
>   saturates the metric.
> * That the topology planner improves N-1 resilience. The N-1
>   evaluation pipeline does not exist.

## 4. The paper we *could* write after Stage 42

> **Title (Stage-42 target)**: *Conditional Resilience: An
> Action-Mask-Augmented DQN with LSTM Forecasting and Storage
> Awareness for Distribution-Feeder Self-Healing*
>
> **Claim**: The action-mask-augmented DQN outperforms a 2-action
> reactive rule-based controller on ENS/CMI under default scenarios
> AND under stress scenarios (high demand, low renewable, critical-
> load exposure, multiple faults). The marginal contribution of
> LSTM forecasting and storage awareness is **scenario-conditional**
> — significant under compound stress (Scenario E) and storage
> stress (Scenario I), negligible under default scenarios.
>
> **Required Stage-42 work**:
> 1. Implement scenarios A–J from `STAGE_41_SCENARIO_MATRIX.md`.
> 2. Wire `enable_lstm`, `enable_twin`, `enable_predictive_healing`,
>    `enable_reward_shaping`, `enable_ems` flags into the harness
>    so the ablation actually has an effect.
> 3. Re-run the diagnostic on the harder scenarios.
> 4. Report the scenario-conditional contributions honestly.

## 5. The honest negative finding

> The Stage-26 paper experiments do **not** support the integrated
> resilience framework claim. The full_stack architecture is
> statistically indistinguishable from a uniform random controller on
> every metric except those dominated by FLISR. This is not a defect
> of the architecture — it is a defect of the evaluation harness,
> which never exercises the architecture's components. **The
> architecture is implemented; the architecture has not been
> evaluated.**

---

## 6. What we present at submission

We present *the truth*:

* The PRIMARY contribution is the action-mask-augmented DQN vs the
  2-action rule-based controller.
* The SECONDARY contribution is the 9-stage FLISR.
* The SUPPORTING contributions are the digital twin, the LSTM, the
  hybrid storage, and the topology planner, **each demonstrated in
  isolation as a working module**, with an honest acknowledgement
  that the integration has not been empirically validated.
* The NEGATIVE results — full_stack ≈ random, predictive >
  reactive (in the single-seed test), topology planner's
  accepted action does not improve kpis_after — are reported as
  *future-work findings*, not hidden.

This is the only honest way to write the paper given Stage-41
evidence.
