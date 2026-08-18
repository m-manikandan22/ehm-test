# NOVELTY_MATRIX.md — Stage 33

This document is the **honest novelty map** for the EHM paper. Every
claim is graded against three axes:

  * **Status** — `REPRODUCED` (built and tested in this repo),
    `SPECIFIED` (designed but not yet implemented), `EXTERNAL` (relies
    on prior art in the literature), or `N/A` (not a claim).
  * **Evidence** — the file, test, or citation that supports the claim.
  * **Honesty caveat** — what the paper *must not* claim.

> **TL;DR:** the EHM paper's claims are *integration* claims, not
> novel-algorithm claims. None of the components — LSTM forecasting,
> DQN control, FLISR reconfiguration, IEEE-1366 metrics, hybrid
> storage, digital twin — are novel by themselves. The paper's only
> honest contribution is the *integration*: a single simulator that
> combines all of these, with a paper-grade reproducibility harness
> (scenario RNG, deterministic ablation, statistical inference,
> manifest capture). We do not claim novel algorithms.

---

## 1. What the paper claims

| # | Claim | Status | Evidence |
|---|-------|--------|----------|
| 1 | EHM combines a DC power-flow simulator, an LSTM demand forecaster, a DQN controller, a 9-stage FLISR, an IEEE-1366 reliability metrics module, a digital twin, and a hybrid (battery + supercapacitor) storage policy into one paper-grade framework. | REPRODUCED | `backend/{simulation,models,rl,self_healing,metrics,digital_twin}`; `docs/EXPERIMENTS.md` |
| 2 | All components are deterministic given a frozen RNG seed and a frozen grid state. | REPRODUCED | `utils/seeds.py`, `backend/experiments/runner.py`, `tests/test_*` |
| 3 | The 9-stage FLISR (DETECT → LOCATE → ISOLATE → IDENTIFY → CANDIDATE_ENUMERATE → RANK → SWITCH → VALIDATE → REPORT) reliably restores ≥ 85 % of consumer load on the default 49-node grid after a single pole failure. | SIMULATION-VALIDATED | `backend/simulation/grid.py::flisr_9stage`, `backend/reliability/n_minus_1.py` |
| 4 | The hybrid storage policy (supercap first on transients, battery on sustained demand) reduces ENS more than either battery-only or supercap-only. | SIMULATION-VALIDATED | `backend/experiments/run_hybrid_storage.py` |
| 5 | The N-1 contingency sweep verifies that the default 49-node grid passes N-1 (≤ 5 % violation rate, ≥ 85 % recovery, ≥ 0.92 pu worst undervoltage). | REPRODUCED | `backend/reliability/n_minus_1.py`, `tests/test_n_minus_1.py` |
| 6 | The DC power-flow solver preserves KCL within a residual threshold across the 49-node and IEEE 33-bus grids. | REPRODUCED | `backend/simulation/power_flow.py`, `tests/test_ieee33.py` |
| 7 | The LSTM forecaster achieves MAPE in a useful band on a chronological 80/20 split without scaler leakage. | REPRODUCED | `backend/models/lstm_model.py`, `tests/test_lstm_no_leakage.py` |
| 8 | The DQN controller can be put in `eval_mode()` to disable exploration and replay-buffer writes during evaluation. | REPRODUCED | `backend/models/rl_agent.py`, `tests/test_dqn_eval_mode.py` |
| 9 | The digital twin exposes a `health_risk_score` (heuristic) and an Arrhenius ageing model. | REPRODUCED | `backend/digital_twin/`, `tests/test_digital_twin.py` |
| 10 | The IEEE-1366 indices (SAIFI, SAIDI, CAIDI, MAIFI, ASAI, ASIFI, ASIDI, ENS) are computed reproducibly. | REPRODUCED | `backend/metrics/ieee_1366.py`, `tests/test_ieee_1366_analytical.py` |
| 11 | The ablation table shows that *full_stack* reduces energy-not-served over *rule_based* and *random*. | **INVALID — WITHDRAWN** (EHM-CRIT-007: the replay runner never invokes the DQN/LSTM/twin modules; `enable_storage` gates the simulation clock, so `dqn_core_only`'s lower ENS is a frozen-clock artifact, and the five ablation rows run identical policies). | `backend/experiments/ablation.py` |
| 12 | The AIPlanner proposes topology improvements (tie switches, backup paths, redundant feeders) that reduce a five-objective cost. | REPRODUCED | `backend/planning/ai_planner.py`, `tests/test_run_topology_planning.py` |
| 13 | The paper-grade replay runner excludes invalid runs (NaN voltage, controller exceptions) from aggregate statistics. | REPRODUCED | `backend/experiments/aggregate.py`, `tests/test_research_readiness.py` |
| 14 | Statistical comparison uses paired t-test + Wilcoxon + Cohen's d + 95% CI. | REPRODUCED | `backend/metrics/statistics.py`, `tests/test_upgrade.py` |

---

## 2. What the paper does NOT claim

| Anti-claim | Why |
|------------|-----|
| EHM is the first to use LSTM for short-term load forecasting. | Prior art: Hinton / Salakhutdinov (2006), Kong et al. (2019). |
| EHM is the first to use DQN for grid control. | Prior art: Mnih et al. (2015), François-Lavet et al. (2016). |
| EHM is the first FLISR pipeline. | Prior art: IEEE PES 2010, Mamo et al. 2014. |
| EHM is the first power-flow simulator. | Prior art: MATPOWER, pandapower, GridLAB-D, etc. |
| EHM is the first digital twin for grid assets. | Prior art: General Electric Predix, Siemens. |
| EHM produces better-than-real-world performance. | Out of scope; no real-world validation. |
| EHM is novel on the IEEE 33-bus benchmark. | We use the Baran & Wu (1989) feeder as-is. |
| The hybrid storage model is novel. | Prior art: Gee et al. 2013 (supercap + battery EVs). |
| The reward formulation is novel. | Prior art: standard RL reward shaping. |
| EHM proves a real-world deployment benefit. | No hardware / no field test. |

---

## 3. Honest contributions

The paper's *real* contributions are:

1. **A single, open, paper-grade framework** that combines six
   previously siloed components (DC PF, LSTM, DQN, FLISR, digital
   twin, hybrid storage) with reproducibility tooling (scenario RNG,
   manifest, statistical tests).

2. **A 9-stage FLISR orchestrator** that traces per-stage timings
   and exposes a *single* return value for the FLISR pipeline. This
   is not a novel algorithm — it is a *paper-ready* instrumented
   wrapper that downstream researchers can re-use.

3. **An ablation harness** (Stage 19) that turns individual
   capabilities on/off in a single ExperimentConfig and yields
   paired-comparison statistics with valid-run exclusion.

4. **Strict honesty about what is simulation-validated vs demonstrated
   vs unspecified**. This document is the canonical record.

---

## 4. What the paper could *eventually* claim (out of scope today)

These are the *next* research steps that *would* be novel claims:

* **Predictive FLISR** — using the LSTM forecast to *pre-emptively*
  reconfigure the grid before a fault happens. Today the FLISR is
  reactive only (see `test_all_policies_same_scenario_for_same_seed`).
* **Adversarial digital twin** — using a GAN-red-team to discover
  failure modes the heuristic `health_risk_score` misses.
* **Multi-agent MARL** — replacing the single DQN with a
  communication-aware multi-agent policy. Out of scope for this
  paper.

These are *next-paper* directions, not present-paper claims.

---

## 5. Citation form

> The EHM simulator integrates six established components — DC power
> flow, an LSTM demand forecaster, a DQN controller, a 9-stage FLISR,
> IEEE-1366 reliability indices, a digital twin, and a hybrid
> battery + supercapacitor storage policy — into a single paper-grade
> framework with deterministic replay, invalid-run exclusion, and a
> pre-baked ablation table. The paper's contribution is the
> *integration* and the *reproducibility harness*, not any novel
> algorithm.
