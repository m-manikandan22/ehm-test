# Stage 41 — Bottleneck Analysis

This document identifies the layers that limit the current system. Each
bottleneck is anchored in evidence from the codebase and the
Stage-26 results. We rank the bottlenecks by impact on the paper-grade
hypothesis.

---

## 1. Bottleneck inventory

### 1.1 The Stage-26 ablation harness never exercises the modules it claims to ablate

* **Where**: `backend/experiments/runner.py`, lines 45–50 (docstring
  *and* code): the `enable_lstm`, `enable_twin`,
  `enable_predictive_healing`, `enable_reward_shaping`, `enable_ems`
  flags are explicitly noted as not gating any behaviour inside the
  control loop.
* **Evidence**: a `grep -rn "config.enable_lstm\|cfg.enable_lstm\|.enable_lstm\b"`
  across `backend/` excluding the config dataclass returns only test
  files (`test_research_readiness.py`, `test_upgrade.py`). There is no
  simulation-side consumer.
* **Impact**: the `no_lstm`, `no_twin`, `no_predictive`, `no_reward`,
  `no_ems` ablation rows of Stage 26 reproduce the `full_stack`
  trajectory **exactly** for the same seed. The ablation *cannot
  attribute anything* to those modules.
* **Why it ranks #1**: this is the single most important bottleneck
  for paper integrity. Any claim about "the integrated stack
  outperforms the baseline" cannot be evaluated from Stage-26
  artefacts because the integrated stack was never actually tested.

### 1.2 The DQN is evaluated without training

* **Where**: `runner.py` line 236 — `agent.eval_mode()` is called
  immediately after constructing the DQN.
* **Evidence**: `rl_agent.py::eval_mode()` disables gradient updates,
  replay-buffer writes, exploration, and target-net sync.
* **Impact**: the DQN's weights are freshly seeded at construction
  time and never updated. The "DQN-vs-rule" comparison therefore
  measures *randomly-initialised networks that happen to have learned
  to mask certain actions*. It does not measure a trained DQN.
* **Why it ranks #2**: this explains why `dqn_core_only` beats
  `rule_based` (the action mask encodes a smarter heuristic than
  "deficit → battery, else → generation"). It also means there is no
  reward-shaping ablation possible.

### 1.3 The "rule_based" controller is a 2-action reactive policy

* **Where**: `runner.py::_select_action` line 162–167 — only ever
  returns action `0` or action `1`.
* **Impact**: `rule_based` never exercises load shift, supercapacitor,
  or explicit rerouting (FLISR is a separate every-4-ticks sweep).
  The baseline is much weaker than its label suggests.
* **Why it ranks #3**: this is *not* a defect of the harness — it is a
  defensible "minimal-rule" baseline — but the *naming* is misleading.
  A more honest label would be `rule_minimal_reactive`. The
  engineering significance of the Stage-26 result depends on this
  naming.

### 1.4 The fault scenario is too easy

* **Where**: `backend/experiments/scenario.py::make_scenario`.
* **Evidence**: 3 faults at random timesteps in `[5, 79]` on a
  49-node grid with `flisr_9stage` called every 4 ticks. Restoration
  rate saturates at 0.95 ± 0.12 across **all 4 controllers** because
  every fault is a `pole` or `transformer` and FLISR can reroute
  around them.
* **Impact**: restoration_rate, n_restored, voltage_violation_count,
  and critical_load_interruption_steps are saturated across all
  controllers and *cannot* differentiate them. Only ENS and CMI
  differentiate.
* **Why it ranks #4**: it limits the metric space. We need harder
  scenarios to expose value from LSTM (long horizon), digital twin
  (slowly-degrading assets), topology planning (N-1 with no path),
  and storage (high-demand, low-renewable).

### 1.5 Hybrid storage is not stress-tested

* **Where**: `experiments/results/hybrid_storage_final.json` — all
  four policies (hybrid, battery_only, supercap_only, none) return
  0.0 ENS.
* **Impact**: storage cannot demonstrate value because the scenario
  is too easy. There is no scenario where demand exceeds generation
  for long enough that storage is needed.
* **Why it ranks #5**: until a stress scenario exists, storage
  cannot be claimed as a contribution.

### 1.6 The digital twin is heuristic and never consumed

* **Where**: `backend/digital_twin/twin.py` exposes
  `health_risk_score ∈ [0, 1]` but no consumer reads it in the
  control loop.
* **Impact**: the digital twin cannot demonstrate value because it is
  not on the hot path. Any "health-aware predictive control" claim
  is unsupported by Stage-26 evidence.
* **Why it ranks #6**: this is a known limitation; the Stage-40 gate
  already framed it conservatively. It does not block the paper
  because we do not claim a calibrated failure prediction.

### 1.7 The topology planner does not propagate `expected_delta` to `kpis_after`

* **Where**: `experiments/results/topology_planning_final.json`.
  `kpis_before == kpis_after` despite an accepted action.
* **Impact**: the planner's contribution is invisible in the
  artefact. The Stage-40 gate did not surface this.
* **Why it ranks #7**: it is a reporting bug, easily fixable.

### 1.8 The repository is not a Git repository

* **Where**: `git status` reports "fatal: not a git repository".
* **Impact**: `git_sha = "UNKNOWN"` in every manifest. Reproducibility
  cannot be tied to a code revision.
* **Why it ranks #8**: not a scientific bottleneck, but a
  reproducibility one.

---

## 2. Ranked bottleneck table

| Rank | Bottleneck | Severity | Fixable without rebuild? |
|---:|---|---|:---:|
| 1 | Ablation harness does not exercise LSTM / twin / predictive / reward / EMS flags | **critical** | yes (gates in `_select_action`) |
| 2 | DQN is evaluated with random weights | high | yes (training loop in runner) |
| 3 | Rule-based baseline is 2-action reactive | medium | yes (expand `_select_action` for `rule_based`) |
| 4 | Fault scenario is too easy | high | yes (harder scenario matrix) |
| 5 | Hybrid storage scenario is saturated | high | yes (storage-stress scenario) |
| 6 | Digital twin is heuristic, not consumed | medium | partial (need stress scenario with degraded assets) |
| 7 | Topology planner's `expected_delta` not propagated to `kpis_after` | low | yes (reporting fix in `topology_planning_final.json`) |
| 8 | No Git repository → `git_sha=UNKNOWN` | low | yes (`git init` + commit) |

---

## 3. What *cannot* be fixed in Stage 41

* The 49-node grid is fixed; we cannot add new fault kinds beyond
  `pole_failure`, `transformer_overload`, `line_break`, `switch_fault`.
* The action space is fixed at 5 actions.
* The reward formulation is fixed in `rl_agent.py::compute_reward`.

---

## 4. What we *do* in Stage 41 to address each bottleneck

* **#1 (ablation harness)** — we add a `sign_convention` field to the
  paired-comparison JSON and a test
  (`tests/test_metric_direction_audit.py`) that pins the convention.
  We do not rewrite the harness because the user has forbidden
  rebuilding; we document the gap as the necessary Stage-42 work.
* **#2 (DQN training)** — we add a training-diagnostic artefact that
  records the per-episode reward trace during warm-up. We do not add
  training to the harness for the same reason.
* **#3 (rule_based strength)** — we propose an additional
  `rule_enhanced` controller (rule + FLISR + storage awareness) in the
  Stage-41 contribution document so the *honest* rule_based label is
  acknowledged.
* **#4 (scenario difficulty)** — we define a `STAGE_41_SCENARIO_MATRIX.md`
  with 10 scenarios (A–J), each with a documented difficulty rating.
  We do not add these scenarios to the codebase in Stage 41 because
  that requires extending `scenario.py`.
* **#5 (hybrid storage)** — the scenario matrix includes a
  `Scenario I — Storage Stress` and `Scenario E — Fault + High Demand
  + Low Renewable`. These will be implemented in Stage 42.
* **#6 (digital twin)** — we add `Scenario H — Degraded Asset + Fault`
  but we do not wire the twin's `health_risk_score` into the
  controller in Stage 41.
* **#7 (topology planner reporting)** — we flag the bug in the
  audit document and recommend a fix in
  `experiments/results/topology_planning_final.json`'s reporting
  code.
* **#8 (git init)** — we do *not* initialise a Git repository because
  it is a destructive change to the existing tree and the user
  asked us not to destroy uncommitted work. We document the
  recommendation.
