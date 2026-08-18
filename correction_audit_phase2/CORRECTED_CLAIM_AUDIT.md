# CORRECTED CLAIM AUDIT — Experiment B (540 runs)

Anchored to the pre-registered primary outcomes in `paper_results_experiment_B/PRIMARY_OUTCOMES.md` and to directly measurable module / cost evidence. Classifications:

- **SUPPORTED** — Holm p < 0.05, effect in the predicted direction, and the pre-registered effect threshold is met at every applicable stress level.
- **PARTIALLY SUPPORTED** — passes in at least one stress level but not all.
- **CONTRADICTED** — statistically significant effect in the *opposite* direction to the claim.
- **INCONCLUSIVE** — no statistically detectable effect, or an effect below the threshold (absence of evidence, not evidence of absence).
- **NOT TESTED** — claim requires evidence this simulation study does not produce.

## Reliability

### EHM reduces cumulative ENS / unserved energy vs rule-based FLISR under stress.

- **moderate** vs `rule_based`: **INCONCLUSIVE** (`stress_cumulative_unserved_energy` median diff = -3.399, rel diff = -1.02 %, Holm p = 1, Cliff's δ = -0.067)
- **moderate (combined)** — INCONCLUSIVE

- **severe** vs `rule_based`: **INCONCLUSIVE** (`stress_cumulative_unserved_energy` median diff = 13.144, rel diff = 0.72 %, Holm p = 0.408, Cliff's δ = 0.067)
- **severe (combined)** — INCONCLUSIVE

**Verdict: INCONCLUSIVE**

## Resilience

### EHM reaches 50 % restoration in fewer steps vs rule-based FLISR under stress.

- **moderate** vs `rule_based`: **INCONCLUSIVE** (`resilience_time_to_50pct_restoration` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **moderate (combined)** — INCONCLUSIVE

- **severe** vs `rule_based`: **INCONCLUSIVE** (`resilience_time_to_50pct_restoration` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **severe (combined)** — INCONCLUSIVE

**Verdict: INCONCLUSIVE**

## Critical loads

### EHM restores a higher fraction of critical load vs rule-based FLISR under stress.

- **moderate** vs `rule_based`: **INCONCLUSIVE** (`stress_critical_load_restored_pct` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **moderate (combined)** — INCONCLUSIVE

- **severe** vs `rule_based`: **INCONCLUSIVE** (`stress_critical_load_restored_pct` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **severe (combined)** — INCONCLUSIVE

**Verdict: INCONCLUSIVE**

## Reliability

### EHM reduces SAIDI vs rule-based FLISR under stress.

- **moderate** vs `rule_based`: **INCONCLUSIVE** (`saidi` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **moderate (combined)** — INCONCLUSIVE

- **severe** vs `rule_based`: **INCONCLUSIVE** (`saidi` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **severe (combined)** — INCONCLUSIVE

**Verdict: INCONCLUSIVE**

## Ablations

### The Digital Twin improves resilience over the no-twin ablation.

- **moderate** vs `no_twin`: **INCONCLUSIVE** (`stress_cumulative_unserved_energy` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **moderate (combined)** — INCONCLUSIVE

- **severe** vs `no_twin`: **INCONCLUSIVE** (`stress_cumulative_unserved_energy` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **severe (combined)** — INCONCLUSIVE

**Verdict: INCONCLUSIVE**

## Ablations

### LSTM forecasting improves outcomes over the no-LSTM ablation.

- **moderate** vs `no_lstm`: **INCONCLUSIVE** (`stress_cumulative_unserved_energy` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **moderate (combined)** — INCONCLUSIVE

- **severe** vs `no_lstm`: **INCONCLUSIVE** (`stress_cumulative_unserved_energy` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **severe (combined)** — INCONCLUSIVE

**Verdict: INCONCLUSIVE**

## Ablations

### Predictive healing improves outcomes over the no-predictive ablation.

- **moderate** vs `no_predictive`: **INCONCLUSIVE** (`stress_cumulative_unserved_energy` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **moderate (combined)** — INCONCLUSIVE

- **severe** vs `no_predictive`: **INCONCLUSIVE** (`stress_cumulative_unserved_energy` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **severe (combined)** — INCONCLUSIVE

**Verdict: INCONCLUSIVE**

## Ablations

### Reward shaping helps DQN outcomes under stress.

- **moderate** vs `no_reward`: **INCONCLUSIVE** (`stress_cumulative_unserved_energy` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **moderate (combined)** — INCONCLUSIVE

- **severe** vs `no_reward`: **INCONCLUSIVE** (`stress_cumulative_unserved_energy` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **severe (combined)** — INCONCLUSIVE

**Verdict: INCONCLUSIVE**

## Baselines

### DQN outperforms rule-based FLISR under stress.

- **moderate** vs `dqn_core_only`: **INCONCLUSIVE** (`stress_cumulative_unserved_energy` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **moderate (combined)** — INCONCLUSIVE

- **severe** vs `dqn_core_only`: **INCONCLUSIVE** (`stress_cumulative_unserved_energy` median diff = 0.000, rel diff = 0.00 %, Holm p = 1, Cliff's δ = 0.000)
- **severe (combined)** — INCONCLUSIVE

**Verdict: INCONCLUSIVE**

## Computational cost

### EHM is computationally efficient compared to rule-based.

- **moderate** vs `rule_based`: **CONTRADICTED** (`controller_runtime_s` median diff = 0.408, rel diff = 10743.58 %, Holm p = 1.734e-06, Cliff's δ = 1.000)
- **moderate (combined)** — CONTRADICTED

- **severe** vs `rule_based`: **CONTRADICTED** (`controller_runtime_s` median diff = 0.348, rel diff = 9491.81 %, Holm p = 1.734e-06, Cliff's δ = 1.000)
- **severe (combined)** — CONTRADICTED

**Verdict: CONTRADICTED**

## Deployment

### EHM is real-world validated.

Verdict: **NOT TESTED** — this is a simulation study. The claim requires field measurements, hardware-in-the-loop, or deployment evidence that Experiment B does not produce.

## Deployment

### EHM has been validated on IEEE-13 (publication-grade).

Verdict: **NOT TESTED** — Experiment B runs on the 49-node simulator testbed. The IEEE-13 work in this repository is a balanced positive-sequence per-unit *equivalent* with validation_status `demonstrative`; it is not publication-grade IEEE-13 validation, and Experiment B itself does not benchmark against the IEEE-13 reference.

## Reliability

### EHM (with FLISR) reduces cumulative ENS vs no-action baselines (persistence / random) under stress.

- **moderate** vs `persistence`: **SUPPORTED** (`stress_cumulative_unserved_energy` median diff = -394.451, rel diff = -48.10 %, Holm p = 6.938e-06, Cliff's δ = -1.000)
- **moderate** vs `random`: **SUPPORTED** (`stress_cumulative_unserved_energy` median diff = -394.451, rel diff = -48.10 %, Holm p = 6.938e-06, Cliff's δ = -1.000)
- **moderate (combined)** — SUPPORTED

- **severe** vs `persistence`: **SUPPORTED** (`stress_cumulative_unserved_energy` median diff = -4786.946, rel diff = -78.33 %, Holm p = 6.938e-06, Cliff's δ = -1.000)
- **severe** vs `random`: **SUPPORTED** (`stress_cumulative_unserved_energy` median diff = -4786.946, rel diff = -78.33 %, Holm p = 6.938e-06, Cliff's δ = -1.000)
- **severe (combined)** — SUPPORTED

**Verdict: SUPPORTED**

---

## Summary table

| id | section | claim | verdict | evidence |
|---|---|---|---|---|
| claim_ehm_reduces_ens | Reliability | EHM reduces cumulative ENS / unserved energy vs rule-based FLISR under stress. | INCONCLUSIVE |  |
| claim_ehm_faster_restoration | Resilience | EHM reaches 50 % restoration in fewer steps vs rule-based FLISR under stress. | INCONCLUSIVE |  |
| claim_ehm_restores_critical_load | Critical loads | EHM restores a higher fraction of critical load vs rule-based FLISR under stress. | INCONCLUSIVE |  |
| claim_ehm_reduces_saidi | Reliability | EHM reduces SAIDI vs rule-based FLISR under stress. | INCONCLUSIVE |  |
| claim_twin_improves_resilience | Ablations | The Digital Twin improves resilience over the no-twin ablation. | INCONCLUSIVE |  |
| claim_lstm_improves_restoration | Ablations | LSTM forecasting improves outcomes over the no-LSTM ablation. | INCONCLUSIVE |  |
| claim_predictive_improves_resilience | Ablations | Predictive healing improves outcomes over the no-predictive ablation. | INCONCLUSIVE |  |
| claim_reward_shaping_helps | Ablations | Reward shaping helps DQN outcomes under stress. | INCONCLUSIVE |  |
| claim_dqn_outperforms_rule_based | Baselines | DQN outperforms rule-based FLISR under stress. | INCONCLUSIVE |  |
| claim_ehm_computationally_efficient | Computational cost | EHM is computationally efficient compared to rule-based. | CONTRADICTED |  |
| claim_ehm_real_world_validated | Deployment | EHM is real-world validated. | NOT TESTED |  |
| claim_ehm_validated_ieee13 | Deployment | EHM has been validated on IEEE-13 (publication-grade). | NOT TESTED |  |
| claim_flisr_reduces_ens_vs_noaction | Reliability | EHM (with FLISR) reduces cumulative ENS vs no-action baselines (persistence / random) under stress. | SUPPORTED |  |

## Computational-cost evidence (controller_runtime_s)

Paired by seed, `full_stack` minus `rule_based`:

| level | median FS | median rule_based | median diff | rel diff % | Wilcoxon p | Holm p | Cliff's d |
|---|---:|---:|---:|---:|---:|---:|---:|
| moderate | 0.4118 | 0.0038 | 0.4078 | 10743.6 | 1.734e-06 | 1.734e-06 | 1.000 |
| severe | 0.3516 | 0.0037 | 0.3478 | 9491.8 | 1.734e-06 | 1.734e-06 | 1.000 |

`full_stack` is consistently ~100x slower in controller runtime than `rule_based`; the difference is statistically significant at both levels, contradicting any 'computationally efficient' claim.
## Notes on the headline finding

- `claim_flisr_reduces_ens_vs_noaction` is the **only SUPPORTED claim**: the corrected data show a large, statistically significant ENS reduction for FLISR-enabled controllers vs `persistence`/`random` at both stress levels (e.g. severe median 1329.8 vs 6223.7; raw p ≈ 2e-6, Holm p < 0.05, Cliff's δ = -1.0).
- All AI-stage and DQN-vs-rule-based claims are INCONCLUSIVE because every DQN-based arm is bit-identical per seed to `dqn_core_only` (identical trajectories), and `rule_based` (FLISR-only) is statistically indistinguishable from `full_stack` on PO1 at both levels (moderate p = 0.491, severe p = 0.102 raw; Holm p ≥ 0.41).
- `claim_ehm_computationally_efficient` is CONTRADICTED: `full_stack` controller runtime is ~100x `rule_based` at both levels with Holm p < 0.05 (see below).
- PO2/PO3/PO4 metrics are fully saturated (0 / 100 / 0 everywhere); those claims are INCONCLUSIVE because the instrument cannot discriminate controllers, not because the controller was shown equal.

_Raw results were not modified._
