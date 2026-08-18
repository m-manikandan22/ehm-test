# ABLATION ANALYSIS — Corrected Experiment B

Full Stack vs each ablation (`no_lstm`, `no_twin`, `no_predictive`, `no_reward`) on the four pre-registered primary outcomes.

## Statistical results

### moderate

| ablation | outcome | median FS | median ablat | median diff | raw p | Holm p | Cliff's d |
|---|---|---|---|---|---|---|---|
| no_lstm | PO1_ens | 501.2 | 501.2 | 0 | 1 | 1 | 0.000 |
| no_lstm | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | 0.000 |
| no_lstm | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | 0.000 |
| no_lstm | PO4_saidi | 0 | 0 | 0 | 1 | 1 | 0.000 |
| no_twin | PO1_ens | 501.2 | 501.2 | 0 | 1 | 1 | 0.000 |
| no_twin | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | 0.000 |
| no_twin | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | 0.000 |
| no_twin | PO4_saidi | 0 | 0 | 0 | 1 | 1 | 0.000 |
| no_predictive | PO1_ens | 501.2 | 501.2 | 0 | 1 | 1 | 0.000 |
| no_predictive | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | 0.000 |
| no_predictive | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | 0.000 |
| no_predictive | PO4_saidi | 0 | 0 | 0 | 1 | 1 | 0.000 |
| no_reward | PO1_ens | 501.2 | 501.2 | 0 | 1 | 1 | 0.000 |
| no_reward | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | 0.000 |
| no_reward | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | 0.000 |
| no_reward | PO4_saidi | 0 | 0 | 0 | 1 | 1 | 0.000 |

### severe

| ablation | outcome | median FS | median ablat | median diff | raw p | Holm p | Cliff's d |
|---|---|---|---|---|---|---|---|
| no_lstm | PO1_ens | 1330 | 1330 | 0 | 1 | 1 | 0.000 |
| no_lstm | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | 0.000 |
| no_lstm | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | 0.000 |
| no_lstm | PO4_saidi | 0 | 0 | 0 | 1 | 1 | 0.000 |
| no_twin | PO1_ens | 1330 | 1330 | 0 | 1 | 1 | 0.000 |
| no_twin | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | 0.000 |
| no_twin | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | 0.000 |
| no_twin | PO4_saidi | 0 | 0 | 0 | 1 | 1 | 0.000 |
| no_predictive | PO1_ens | 1330 | 1330 | 0 | 1 | 1 | 0.000 |
| no_predictive | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | 0.000 |
| no_predictive | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | 0.000 |
| no_predictive | PO4_saidi | 0 | 0 | 0 | 1 | 1 | 0.000 |
| no_reward | PO1_ens | 1330 | 1330 | 0 | 1 | 1 | 0.000 |
| no_reward | PO2_restoration_time | 0 | 0 | 0 | 1 | 1 | 0.000 |
| no_reward | PO3_critical_load | 100 | 100 | 0 | 1 | 1 | 0.000 |
| no_reward | PO4_saidi | 0 | 0 | 0 | 1 | 1 | 0.000 |

## Module-call evidence used for diagnosis

| ablation | disabled module | executed-but-removed evidence |
|---|---|---|
| `no_lstm` | LSTM | `model_calls`/`lstm_calls` = 0 vs 200 in full_stack; outcomes per seed identical to full_stack |
| `no_twin` | Twin | `twin_updates` = 0 vs 9800; predictive assessments still run but yield 0 recommendations |
| `no_predictive` | Predictive | `predictive_assessments` = 0; twin updates still occur (9800) |
| `no_reward` | Reward shaping | DQN still runs (200 actions); reward shaping not separately instrumented |

## Does disabling the component measurably change outcomes?

Per-seed comparison shows `full_stack` is **numerically identical to every ablation on every outcome** at every seed:

| outcome | identical per-seed (FS vs each ablation) |
|---|---|
| PO1_ens | YES |
| PO2_restoration_time | YES |
| PO3_critical_load | YES |
| PO4_saidi | YES |

## Diagnosis (A–E framework)

| ablation | diagnosis | rationale |
|---|---|---|
| `no_lstm` | **B. Metric saturation + D. insufficient statistical evidence** | LSTM executed (200 calls, 0 failures, outputs consumed) and outputs fed to DQN, but outcomes are bit-identical to full_stack. No measurable benefit and no execution defect (not E). |
| `no_twin` | **C. Component rarely/never activated for its decision output** | Twin syncs and is queried, but the predictive consumer generated zero recommendations, so the twin's outputs never reached the grid. |
| `no_predictive` | **C. Component rarely/never activated** | Predictive assessments ran (200) but produced zero recommendations under frozen risk logic; the module never dispatched an action in full_stack either, so removing it cannot change outcomes. |
| `no_reward` | **A. Component executed but produced no measurable benefit** | Reward shaping changes DQN training signal only; DQN actions are recorded but never dispatched to grid primitives, so both arms yield identical trajectories. |

**Conclusion:** every AI-stage ablation is statistically indistinguishable from full_stack because the AI stages do not alter the grid trajectory in this frozen benchmark. The one component that does change outcomes is FLISR, which is shared by all FLISR-enabled arms.
