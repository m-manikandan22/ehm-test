# EHM-simulation — Scientific Validation Status

> **What this document is** — a single source of truth that maps every
> scientific claim about the EHM-simulation project to: (a) the code
> that backs it, (b) the experiment / test that validates it, and (c)
> the honest status (*validated* / *demonstrative* / *out of scope*).

This document exists because reviewers asked pointed questions about
the project ("is this calibrated?", "is this against an industry
reference?", "is this rule-guided or learned?"). The table below is
the answer.

---

## 1. Power-flow physics

| Claim | Code | Validation | Status |
| --- | --- | --- | --- |
| **DC power flow on a general SmartGrid** | `simulation/power_flow.py:dc_power_flow` | `tests/test_dc_power_flow.py` (KCL residual < 1e-6 on textbook cases + IEEE 13-bus) | **validated** |
| **DC PF on IEEE 13-bus** | `simulation/ieee13.build_ieee13` + `power_flow.dc_power_flow` | `tests/test_ieee13.py` + `tests/test_ieee13_validation.py` | **validated** (DC only) |
| **DC PF vs pandapower DC PF reference** | `experiments/ieee13_validation.py` | same | **demonstrative** (balanced π-equivalent) |
| **AC PF (Newton-Raphson) on a SmartGrid** | `simulation/ac_power_flow.py:run_ac_power_flow` (pandapower-backed) | `tests/test_ac_power_flow.py` | **demonstrative** (5-bus converge test + lazy optional import) |
| **AC PF on IEEE 13-bus (per-phase)** | — | — | **out of scope** (full per-phase IEEE 13 with regulators + Y-Δ transformer model is not implemented) |
| **3-phase unbalanced AC PF** | — | — | **out of scope** |

### What is and is not validated

- ✅ DC PF is validated against textbook cases with KCL residual
  `< 1e-6` per-unit. The IEEE 13-bus DC PF runs cleanly and is
  compared against pandapower DC PF on the same builder; both agree
  in sign and small-angle regime.
- ✅ AC PF (Newton-Raphson) is implemented via pandapower; convergence
  is demonstrated on the textbook 5-bus case. The IEEE 13 builder is
  not the full per-phase spec — it is a balanced positive-sequence
  per-unit equivalent. This is sufficient to demonstrate the
  solver API and to compare against pandapower on a real topology,
  but it is **not** publication-grade validation against the IEEE PES
  reference feeder.

### How to run

```bash
# DC PF smoke test
python -m pytest tests/test_dc_power_flow.py -v

# AC PF smoke test (skipped if pandapower is not installed)
python -m pytest tests/test_ac_power_flow.py -v

# IEEE 13-bus validation report
python -m experiments.ieee13_validation \
    --output experiments/results/ieee13_validation.json
```

---

## 2. Reliability indices (IEEE 1366-2012)

| Claim | Code | Validation | Status |
| --- | --- | --- | --- |
| **SAIFI / SAIDI / CAIDI / MAIFI / ASAI / ASIDI / ASIFI / ENS / AENS / ACCI** | `metrics/ieee_1366.py` | `tests/test_ieee_1366.py` (textbook + synthetic cases) | **validated** (against formulas) |
| **Reliability-recorder integration in API** | `api/predictive_routes.py:_RECORDER` | `tests/test_silent_excepts.py:test_routes_simulate_returns_reliability_error` | **validated** (silent excepts removed) |

These indices are formulas from IEEE Std 1366-2012, not learned or
calibrated models. Their numerical values in a given run depend on
the simulation scenario, but the *formulation* is the standard.

---

## 3. Self-healing & RL

| Claim | Code | Validation | Status |
| --- | --- | --- | --- |
| **DQN with replay buffer + target network** | `models/rl_agent.py:DQNAgent` | `tests/test_dqn_state.py`, `tests/test_advanced_rl.py` | **validated** (architecturally; no benchmark numbers) |
| **DQN warm-up uses rule ladder — *not* behavioural cloning** | `rl/expert_policy.py` + `models/rl_agent.py:smart_warmup` | `tests/test_experiments_framework.py` (the smart_warmup docstring states this explicitly) | **validated** (it is documented, not learned) |
| **Action masking** | `models/rl_agent.py:select_action` | `tests/test_dqn_state.py` | **demonstrative** |
| **XAI attribution (signed-importance proxy)** | `rl/xai.py` | `tests/test_xai.py` | **demonstrative** |
| **Predictive self-healing vs reactive FLISR** | `experiments/predictive_vs_reactive.py` | same | **demonstrative** (paired-t framework in place) |

### DQN warm-up — what it is and is **not**

The DQN's `smart_warmup` populates the replay buffer with
transitions whose *actions* come from the rule ladder in
`rl/expert_policy.choose_action`. There is no `state -> action`
regression loss, no behavioural-cloning head, no DAgger. The
network is then trained with standard Bellman regression on this
dataset. See `docs/RESEARCH_NOTES.md` for the citation trail.

---

## 4. Digital twin

| Claim | Code | Validation | Status |
| --- | --- | --- | --- |
| **Arrhenius-style thermal ageing** | `digital_twin/degradation.py` | unit test exists in `tests/test_digital_twin.py` | **validated as a model**, **demonstrative as a probability** |
| **`failure_probability` is a calibrated probability** | — | — | **no** — it is a piecewise-linear mapping of `health`. See `docs/digital_twin.md` and `docs/RESEARCH_NOTES.md`. |

> The README's scientific-validation table marks this as
> *demonstrative* on purpose. To move it to *validated* we would
> need: (1) a recorded transformer-outage dataset, (2) calibration
> of `Ea` and `T_nominal`, (3) out-of-sample ROC/PR curves. None of
> these exist.

---

## 5. Cyber-attack detection

| Claim | Code | Validation | Status |
| --- | --- | --- | --- |
| **Attack injection (FDIA / replay / ramp)** | `api/routes.py:inject_attack` | `tests/test_attack.py` | **validated** (it works) |
| **Detector flags anomalies** | `models/attack_detector.py` | `tests/test_attack.py` | **demonstrative** |
| **Coordinated FDIA detector** | — | — | **out of scope** — explicitly labelled future work in `docs/cyber_attack.md` |

---

## 6. Experiments framework

| Script | What it does | Status |
| --- | --- | --- |
| `experiments/runner.py` | Multi-config × multi-seed × multi-weather runs, JSON output | ⚠️ **real but confounded** (booleans NOT fully honoured: `enable_dqn`/`enable_lstm`/`enable_twin`/`enable_predictive_healing`/`enable_reward_shaping` never affect `_select_action`; `enable_storage` gates the simulation clock — see EHM-CRIT-007) |
| `experiments/aggregate.py` | mean / std / CI / paired-t summary, Markdown report | **real** |
| `experiments/monte_carlo.py` | 100–1000 seed sweep helper | **real** |
| `experiments/ablation.py` | Drop-one-component harness | ⚠️ **invalid as evidence** (each label is a genuine `ExperimentConfig`, but the five module-ablation rows run identical policies and `dqn_core_only` differs only in clock advance — EHM-CRIT-007, EHM-HIGH-009) |
| `experiments/paper_experiment.py` | One-command paper sweep (baseline + ablation + tables + manifest) | **real** (runs, but inherits the confounds above) |
| `experiments/topology_comparison.py` | Random vs rule vs AI-planner | framework only |
| `experiments/predictive_vs_reactive.py` | SAIFI / SAIDI paired comparison | framework only |
| `experiments/ieee13_validation.py` | EHM DC PF vs pandapower DC PF | demonstrative |

All experiments emit a JSON + Markdown pair; the aggregations go
through `metrics/statistics.py` so 95% CIs and paired-t comparisons
are reproducible and testable. The paper experiment script
(`paper_experiment.py`) wires every output together into a single
directory; see `docs/EXPERIMENTS.md` §"One-command paper experiment".

---

## 7. What is intentionally **out of scope**

This project deliberately does *not* claim:

- ❌ 3-phase unbalanced AC power flow
- ❌ Coordinated FDIA detector
- ❌ PMU-based real-time state estimation
- ❌ Empirically-calibrated failure probabilities
- ❌ Hardware-in-the-loop integration
- ❌ Federated-learning or blockchain coordination layers

These are real engineering targets; they require calibration data,
hardware, or protocol agreements that are out of scope for this
simulation. See `docs/ROADMAP_AFTER_CRITICAL_10.md` for the future-work
section.
