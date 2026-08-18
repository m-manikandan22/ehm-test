# EXPERIMENT B — CLAIM AUDIT

This document audits every claim that could be made about Experiment B. Each claim is anchored to a pre-registered primary outcome (see `PRIMARY_OUTCOMES.md`) and classified as one of:

- **SUPPORTED** — passes the pre-registered threshold *and* the effect is in the predicted direction.
- **PARTIALLY SUPPORTED** — passes one stress level but not the other, or passes below the threshold.
- **NOT SUPPORTED** — the effect is in the opposite direction or above the threshold but opposite sign.
- **INCONCLUSIVE** — the data do not allow a claim (no statistically detectable effect, or below the 1 % functional-effect threshold).
- **NOT APPLICABLE** — claim is out of scope for a simulation study (e.g. real-world validation).


## Reliability

### EHM reduces cumulative ENS / unserved energy under stress.

- **moderate**: INCONCLUSIVE (`stress_cumulative_unserved_energy` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = -0.001)

- **severe**: INCONCLUSIVE (`stress_cumulative_unserved_energy` median_diff = 125.165, rel_diff = 1.52%, Holm p = 1.0000, Cliff's δ = 0.133)


**Verdict: INCONCLUSIVE**

### EHM reduces SAIDI under stress.

- **moderate**: INCONCLUSIVE (`saidi` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)

- **severe**: INCONCLUSIVE (`saidi` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)


**Verdict: INCONCLUSIVE**


## Resilience

### EHM reaches 50 % restoration in fewer steps under stress.

- **moderate**: INCONCLUSIVE (`resilience_time_to_50pct_restoration` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)

- **severe**: INCONCLUSIVE (`resilience_time_to_50pct_restoration` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)


**Verdict: INCONCLUSIVE**


## Critical loads

### EHM restores a higher fraction of critical load under stress.

- **moderate**: INCONCLUSIVE (`stress_critical_load_restored_pct` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)

- **severe**: INCONCLUSIVE (`stress_critical_load_restored_pct` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)


**Verdict: INCONCLUSIVE**


## Ablations

### The Digital Twin improves resilience over the no-twin ablation.

- **moderate**: INCONCLUSIVE (`stress_cumulative_unserved_energy` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)

- **severe**: INCONCLUSIVE (`stress_cumulative_unserved_energy` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)


**Verdict: INCONCLUSIVE**

### LSTM forecasting improves restoration over the no-LSTM ablation.

- **moderate**: INCONCLUSIVE (`stress_cumulative_unserved_energy` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)

- **severe**: INCONCLUSIVE (`stress_cumulative_unserved_energy` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)


**Verdict: INCONCLUSIVE**

### Predictive healing improves resilience over the no-predictive ablation.

- **moderate**: INCONCLUSIVE (`stress_cumulative_unserved_energy` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)

- **severe**: INCONCLUSIVE (`stress_cumulative_unserved_energy` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)


**Verdict: INCONCLUSIVE**

### Reward shaping helps faster training under stress.

- **moderate**: INCONCLUSIVE (`stress_cumulative_unserved_energy` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)

- **severe**: INCONCLUSIVE (`stress_cumulative_unserved_energy` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)


**Verdict: INCONCLUSIVE**


## Baselines

### DQN outperforms rule-based FLISR under stress.

- **moderate**: INCONCLUSIVE (`stress_cumulative_unserved_energy` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)

- **severe**: INCONCLUSIVE (`stress_cumulative_unserved_energy` median_diff = 0.000, rel_diff = 0.00%, Holm p = 1.0000, Cliff's δ = 0.000)


**Verdict: INCONCLUSIVE**


## Computational cost

### EHM is computationally efficient compared to rule-based.

- **moderate**: NOT_SUPPORTED (`controller_runtime_s` median_diff = 0.123, rel_diff = 3067.50%, Holm p = 0.0006, Cliff's δ = 1.000)

- **severe**: NOT_SUPPORTED (`controller_runtime_s` median_diff = 0.115, rel_diff = 2868.75%, Holm p = 0.0006, Cliff's δ = 1.000)


**Verdict: NOT_SUPPORTED**


## Deployment

### EHM is real-world validated.

Verdict: **NOT APPLICABLE** — this is a simulation study; the claim requires field measurements or deployment evidence that are not produced here.

### EHM has been validated on IEEE-13.

Verdict: **NOT APPLICABLE** — this is a simulation study; the claim requires field measurements or deployment evidence that are not produced here.


---

If a claim is INCONCLUSIVE, that does not mean the opposite is true. It means the data do not allow a claim to be either supported or refuted.
