# PAPER_OUTLINE.md — Stage 41

This document is the **canonical outline** of the EHM paper. It is
the single source of truth for what each section of the paper
contains, in what order, and what evidence backs each claim.

> **TL;DR:** The paper is a *system integration* paper, not a
> novel-algorithm paper. It has 6 sections + abstract + appendix,
> targets approximately 8 pages + 2 pages of references and 2 pages
> of appendix.
>
> **Honest framing (Stage 41 audit):** the framework is reproducible
> and integration-complete. The Stage-26 ablation harness does not
> exercise the LSTM, digital-twin, predictive-healing,
> reward-shaping, or EMS modules — these flags are *declared* in
> `ExperimentConfig` but never checked inside `runner.run_single`.
> Therefore the Stage-26 result that *the full_stack controller is
> indistinguishable from the rule-based controller on ENS / CMI* is
> **not evidence that the modules don't help** — it is evidence that
> the modules were never exercised. The result that *dqn_core_only
> beats rule_based on ENS* (Wilcoxon p = 8.9e-05, Cohen's d = 1.37)
> *is* real evidence: the DQN's action-mask heuristic
> (deficit → generation/battery; spike → supercapacitor; fault →
> reroute; always → load shift) outperforms the 2-action reactive
> rule-based controller. This is the **PRIMARY CONTRIBUTION** the
> paper can support. All auxiliary components (LSTM, twin, predictive
> healing, reward shaping, hybrid storage, topology planner) are
> presented as **SUPPORTING FEATURES** with an honest "evaluated in
> isolation; integrated evaluation is future work" framing.

---

## 1. Proposed title

> **EHM: A Deterministic, Paper-Grade Self-Healing Smart-Grid
> Simulator with 9-Stage FLISR, Action-Mask-Augmented DQN, and
> Honest Reporting of Negative Results**

---

## 2. Abstract (approximately 200 words)

We present the **EHM** (Energy Management Hub) simulator for
*self-healing* distribution grids. EHM integrates a DC power-flow
solver, an LSTM demand forecaster, a DQN controller with separated
training and evaluation modes, a 9-stage FLISR pipeline, IEEE-1366
reliability indices, a digital twin with Arrhenius ageing, a
hybrid battery + supercapacitor storage model, and a resilience-
aware topology planner into one deterministic Python framework.
Every run is reproducible: scenarios are seeded, invalid runs are
excluded from aggregate statistics, and a manifest records the
environment provenance. We demonstrate the framework on the default
49-node grid and the IEEE 13 / 33 feeders. Across 20 seeds, 80
ticks, and 3 faults, we show that (1) the 9-stage FLISR recovers
at least 95 % of consumer load on FLISR-healable faults; (2) a
5-action DQN with a hand-coded action-mask heuristic outperforms a
2-action reactive rule-based controller on Energy-Not-Served and
Customer-Minutes-Interrupted (Wilcoxon p = 8.9e-05, Cohen's d = 1.37,
n = 20 seeds); (3) adding the LSTM, digital-twin, predictive-
healing, reward-shaping, and EMS modules on top of the DQN core
*does not* measurably improve ENS at the Stage-26 seed budget —
we report this as a **negative result** of the evaluation
methodology, not a defect of the modules (the Stage-26 ablation
harness does not yet invoke these modules as separate code paths);
and (4) every component is end-to-end runnable from a single CLI.
We grade every claim against a *novelty matrix* and document all
limitations (DC-PF proxy, no real-world calibration, no HIL, no
construction-cost constraint in topology planning).

## 3. Section outline

### 3.1 Introduction (1 page)

* The "self-healing grid" concept: detect -> isolate -> restore.
* Why integration is hard: scattered modules, no shared determinism.
* Contribution: an open, reproducible harness with statistical
  ablation evidence (not a novel algorithm).
* Roadmap: section 2 architecture, section 3 components, section 4
  experiments, section 5 discussion, section 6 conclusion, appendix
  with code listings.

### 3.2 Architecture (1 page)

* Figure: high-level diagram (DC PF + LSTM + DQN + FLISR + Twin +
  Storage + Metrics).
* Section references: `docs/ARCHITECTURE.md`, `REWARD_FORMULATION.md`,
  `HYBRID_STORAGE.md`.
* Determinism contract: `utils/seeds.py`, "same seed -> same scenario".

### 3.3 Components (3 pages)

1. **DC power flow** — `simulation/power_flow.py`. KCL residuals.
2. **IEEE 13 / 33 feeders** — `simulation/ieee13.py`,
   `simulation/ieee33.py`.
3. **LSTM forecaster** — `models/lstm_model.py`. Chronological 80/20
   split. No scaler leakage (`tests/test_lstm_no_leakage.py`).
4. **DQN controller** — `models/rl_agent.py`. Replay buffer, target
   network, epsilon-greedy, action masking, `eval_mode()`.
5. **9-stage FLISR** — `simulation/grid.py::flisr_9stage`. Per-stage
   timings. Comparison to legacy `flisr_restore`.
6. **Hybrid storage** — battery + supercap. `docs/HYBRID_STORAGE.md`.
7. **Digital twin** — `digital_twin/`. `health_risk_score` (heuristic).
8. **IEEE-1366 metrics** — `metrics/ieee_1366.py`.
9. **AI planner** — `planning/ai_planner.py`. Greedy + local search.
10. **N-1 contingency** — `reliability/n_minus_one.py`.

### 3.4 Experiments (2 pages)

* **Stage 26 final paper run** (`experiments/stage26_pipeline.py`).
  20 seeds x 80 ticks x 3 faults, four controllers
  (``full_stack``, ``dqn_core_only``, ``rule_based``, ``random``).
  Raw per-seed JSON + aggregated CSV/JSON + 15 paired statistical
  comparisons (5 metrics x 3 controllers vs ``rule_based`` anchor,
  Benjamini-Hochberg corrected). The headline result — that
  ``dqn_core_only`` outperforms ``rule_based`` on ENS (mean diff
  -0.614 MWh, p = 8.9e-05, Cohen's d = 1.37) and CMI (mean diff
  -36.8 min, p = 8.9e-05, Cohen's d = 1.37) — is supported. The
  Stage-41 audit (`docs/STAGE_41_RESULT_AUDIT.md`) confirms the
  sign convention is correct and the effect size is large.
* **Ablation** — `experiments/ablation.py`. Paired comparison of
  ``full_stack`` vs ``no_lstm``, ``no_twin``, ``no_predictive``,
  ``no_reward``. At this seed budget none of these per-module
  removals produces a statistically distinguishable ENS shift.
  **Honest framing (Stage 41)**: this is *not* evidence that the
  modules don't help — it is evidence that the Stage-26 ablation
  harness does not exercise the modules as separate code paths.
  The ``enable_lstm``, ``enable_twin``, ``enable_predictive_healing``,
  ``enable_reward_shaping``, ``enable_ems`` flags are declared in
  ``ExperimentConfig`` but never checked inside the runner. Re-wiring
  the harness is Stage-42 work.
* **Hybrid storage** — `experiments/run_hybrid_storage.py`.
  Hybrid vs battery-only vs supercap-only vs none. The pilot
  fault schedule (40 ticks, 5 faults at ``seed=0``) does not
  discriminate policies (ENS = 0 across all four). Reported as a
  *demonstrative* end-to-end wiring, not a performance ranking.
  The Stage-41 scenario matrix (`docs/STAGE_41_SCENARIO_MATRIX.md`)
  defines harder scenarios (B, C, E, I) that are predicted to
  expose the hybrid-storage contribution.
* **Predictive vs reactive** — `experiments/run_predictive_vs_reactive.py`.
  Mean ENS diff = -7.7e-4 MWh; restoration_rate diff = -2.6e-3.
  Too small to claim superiority; no future-information leakage in
  either strategy. **Stage 41 verdict**: this is a single-seed
  result; we report it as *not-yet-meaningful* rather than as a
  negative result.
* **Topology planning** — `experiments/run_topology_planning.py`.
  AIPlanner accepts 1 action on the 49-node grid
  (``add_feeder(GEN_SOLAR -> H5)``), predicted cost reduction 0.439.
  **Stage 41 finding**: the predicted delta is not propagated to
  ``kpis_after`` (reporting bug). The N-1 evaluation pipeline
  required to demonstrate the planner's value does not exist.
* **N-1 sweep** — `reliability/n_minus_one.py`. 49-node + IEEE 33.
* **Statistical inference** — paired t-test, Wilcoxon, Cohen's d,
  95 % CI, Benjamini-Hochberg. `metrics/statistics.py`. The Stage-41
  metric-direction audit (`docs/STAGE_41_RESULT_AUDIT.md`) documents
  the sign convention and pins it with
  `tests/test_metric_direction_audit.py`.

### 3.5 Discussion (1 page)

* **What works:** integration, determinism, 9-stage FLISR achieves
  at-least-95 % mean restoration, **action-mask-augmented DQN
  outperforms rule-based controller with large effect size** (Cohen's
  d = 1.37), all components end-to-end runnable from one CLI.
* **What doesn't (negative ablation):** the LSTM, digital-twin,
  predictive-healing, and reward-shaping modules in ``full_stack``
  do not measurably improve ENS at this seed budget. **Honest
  framing**: this is a *methodological* negative result, not a
  *module* negative result — the harness never exercised the modules.
  The Stage-41 audit (`docs/STAGE_41_INFORMATION_FLOW.md`) documents
  the missing wiring.
* **What's next (Stage 42):** wire the ablation flags into the
  harness; implement the Stage-41 scenario matrix (A–J); re-run the
  100-seed diagnostic; rebuild the topology-planning N-1 evaluation
  pipeline; calibrate the digital-twin heuristic (REQUIRES EXTERNAL
  DATA).

### 3.6 Conclusion (0.5 page)

* Restate contribution: deterministic, reproducible integration
  harness with statistical ablation evidence and honest reporting
  of negative results.
* Honest framing: the *primary* contribution is the action-mask-
  augmented DQN vs the 2-action rule-based controller. The
  *secondary* contribution is the 9-stage FLISR. The auxiliary
  modules are integration-complete but **not yet evaluated** as
  separate code paths — that is the most important Stage-42 work.
* Open artefacts: code, scenarios, manifest, raw + aggregated
  results, paired statistics.

### 3.7 Appendix (2 pages)

* Code listings (one-liner per module).
* IEEE 33-bus load table.
* Sample ``manifest.json``.
* Sample ``validity.json``.
* Reproducibility command (``stage26_pipeline --stage final``).

---

## 4. Figure / table plan

| # | Type | Title | Source |
|---|------|-------|--------|
| 1 | Figure | Architecture diagram | `docs/ARCHITECTURE.md` |
| 2 | Figure | 9-stage FLISR pipeline | `simulation/grid.py::flisr_9stage` |
| 3 | Figure | Default 49-node grid | `simulation/grid.py` |
| 4 | Figure | IEEE 33-bus feeder | `simulation/ieee33.py` |
| 5 | Figure | LSTM forecast vs ground truth | `experiments/run_lstm_*` |
| 6 | Figure | Hybrid storage SoC over time | `experiments/run_hybrid_storage.py` |
| 7 | Figure | N-1 violation rate per asset | `reliability/n_minus_one.py` |
| 8 | Figure | Ablation ensemble (box-and-whisker) | `experiments/ablation.py` |
| 9 | Figure (Stage 41) | Per-policy ENS distribution (Stage-26 raw) | `experiments/stage41_raw_audit.py` |
| 10 | Figure (Stage 41) | Per-policy CMI distribution (Stage-26 raw) | `experiments/stage41_raw_audit.py` |
| 11 | Figure (Stage 41) | Diagnostic confusion matrix (`full_stack` vs `dqn_core_only`) | `experiments/stage41_diagnostic.py` |
| 12 | Table | Per-policy IEEE-1366 metrics | `experiments/tables.py` |
| 13 | Table | Paired comparison (anchor=rule_based) | `experiments/tables.py` |
| 14 | Table | Stage 41 scenario matrix (A-J, difficulty 0-8) | `docs/STAGE_41_SCENARIO_MATRIX.md` |
| 15 | Table | N-1 pass / fail per contingency | `reliability/n_minus_one.py` |
| 16 | Table | Reproducibility manifest excerpt | `experiments/paper_experiment.py` |
| 17 | Table (Stage 41) | Contribution ranking (10 candidates) | `docs/STAGE_41_RESEARCH_CONTRIBUTION.md` |

---

## 5. Cross-references

| Claim | Backing doc | Backing test |
|-------|-------------|--------------|
| Section 3.1 (intro) | `docs/ARCHITECTURE.md` | — |
| Section 3.2 (architecture) | `docs/REWARD_FORMULATION.md`, `docs/HYBRID_STORAGE.md` | — |
| Section 3.3.1 (DC PF) | `backend/simulation/power_flow.py` | `tests/test_ieee33.py` |
| Section 3.3.3 (LSTM) | `backend/models/lstm_model.py` | `tests/test_lstm_no_leakage.py` |
| Section 3.3.4 (DQN) | `backend/models/rl_agent.py` | `tests/test_dqn_eval_mode.py` |
| Section 3.3.5 (FLISR) | `backend/simulation/grid.py` | `tests/test_flisr_9stage.py` |
| Section 3.3.6 (storage) | `docs/HYBRID_STORAGE.md` | `tests/test_run_hybrid_storage.py` |
| Section 3.3.7 (twin) | `backend/digital_twin/` | `tests/test_digital_twin.py` |
| Section 3.3.8 (IEEE-1366) | `backend/metrics/ieee_1366.py` | `tests/test_ieee_1366_analytical.py` |
| Section 3.3.9 (planner) | `docs/TOPOLOGY_PLANNING.md` | `tests/test_run_topology_planning.py` |
| Section 3.3.10 (N-1) | `backend/reliability/n_minus_one.py` | `tests/test_n_minus_one.py` |
| Section 3.4 (experiments) | `backend/experiments/`, `docs/STAGE_41_RESULT_AUDIT.md`, `docs/STAGE_41_RESEARCH_CONTRIBUTION.md` | `tests/test_research_readiness.py`, `tests/test_metric_direction_audit.py` |
| Section 3.5 (discussion) | `docs/LIMITATIONS.md`, `docs/NOVELTY_MATRIX.md`, `docs/STAGE_41_BOTTLENECK_ANALYSIS.md`, `docs/STAGE_41_INFORMATION_FLOW.md` | — |

---

## 6. Word count budget

| Section | Target |
|---------|--------|
| Abstract | 200 |
| 1. Introduction | 600 |
| 2. Architecture | 700 |
| 3. Components | 1800 |
| 4. Experiments | 1200 |
| 5. Discussion | 600 |
| 6. Conclusion | 250 |
| References | (varies) |
| Appendix | 800 |
| **Total** | **~6100 words** |

---

## 7. How to rebuild the paper from this repo

```bash
cd backend
python -m experiments.stage26_pipeline \
    --stage final \
    --seeds 20 --ticks 80 --faults 3 \
    --output ../experiments/results/paper_final_stage26
python -m experiments.run_hybrid_storage \
    --seed 0 --ticks 40 --faults 5 --out ../experiments/results/hybrid_storage_final.json
python -m experiments.run_predictive_vs_reactive \
    --seed 42 --n-faults 3 --out ../experiments/results/predictive_vs_reactive_final.json
python -m experiments.run_topology_planning \
    --seed 42 --max-iterations 8 --out ../experiments/results/topology_planning_final.json
```

Stage 41 audit commands (do NOT modify the algorithms — these are
diagnostic, paper-grade re-derivations of the Stage-26 numbers):

```bash
cd backend
python -m pytest tests/test_metric_direction_audit.py -v   # pin sign convention
python ../experiments/stage41_raw_audit.py                 # regenerate boxplots / per-policy CI
python ../experiments/stage41_diagnostic.py                # 5-seed x 80-tick diagnostic
```

All artefacts land in `experiments/results/paper_final_stage26/`
(canonical Stage 26 layout: ``raw/aggregated/statistics/tables/figures/logs/manifest.json/summary.md``)
plus the three standalone final-result JSONs. Stage 41 diagnostic
artefacts land in `experiments/results/stage41_diagnostics/`.