# LIMITATIONS.md — Stage 34

This document is the **honest list of limitations** of the EHM
simulator and the paper that will be built on it. Every item is
graded against three axes:

  * **Severity** — How much does it limit the paper's claims?
    `BLOCKER` (paper must not claim X), `CAUTION` (paper must hedge
    about X), `COSMETIC` (cosmetic; reviewers won't notice).
  * **Scope** — Simulator-only, paper-only, or both.
  * **Workaround** — How the paper handles it.

> **TL;DR:** EHM is a *simulation-validated* framework. It does not
> include real-world validation, full AC PF, hardware in the loop,
> or any of the seven *BLOCKER* items below. The paper must say so
> in every figure caption.

---

## 1. BLOCKER limitations

These are unavoidable in the current repo. The paper must explicitly
acknowledge each one.

### 1.1 DC power flow instead of AC

**Severity:** BLOCKER.
**Scope:** Simulator + paper.

We use DC PF (linear, no reactive, no voltage collapse). The
voltages reported are *linear* duals, not true complex magnitudes.
For full AC-PF comparisons (voltage collapse, reactive limits, line
losses) the paper must rely on the optional
``backend.simulation.ac_power_flow`` path (pandapower-based). See
EHM-HIGH-005 in `docs/PAPER_READINESS_AUDIT.md`.

**Workaround:** when reporting voltage magnitudes, label them
"DC-PF proxy voltage"; when reporting var flows, label them
"not modelled".

### 1.2 No real-world validation

**Severity:** BLOCKER.
**Scope:** Both.

Every metric in the paper is *simulation-validated*, not field-tested.
The 49-node default grid is synthesised; the IEEE 13 / 33 feeders are
from the published standard but our load values are scaled. There is
no SCADA pull, no PMU sync, no IoT telemetry.

**Workaround:** every figure caption and table footnote carries the
"SIMULATION-VALIDATED" or "REPRODUCED" badge.

### 1.3 No hardware-in-the-loop

**Severity:** BLOCKER.
**Scope:** Both.

The simulator does not interface with any real inverter, breaker, or
relay. The "self-healing" loop is a simulation loop, not a real
controller running on a substation RTU.

### 1.4 Random SmartGrid initialisation

**Severity:** BLOCKER for reproducibility.
**Scope:** Simulator.

``SmartGrid()`` randomises node loads / generations at construction
time. This means two ``SmartGrid()`` instances are NOT identical —
they differ in load weights, generation weights, and battery SOCs.
The ablation harness works around this by running *every* policy on
the same seed, but per-claim numbers are still seed-correlated.

**Workaround:** the paper reports metrics averaged over multiple
seeds; the runner pins seed everywhere it can. The
``SmartGrid(seed=...)`` constructor is missing — see EHM-HIGH-009.

### 1.4b Ablation runner never invokes the learned modules (EHM-CRIT-007)

**Severity:** BLOCKER for the ablation claims.
**Scope:** Experiment harness.

``_select_action`` in ``experiments/runner.py`` returns action ``1``
unconditionally for every ``enable_dqn=True`` config; the DQN, LSTM,
digital twin, predictive-healing and reward-shaping modules never run
in any replay. Additionally ``enable_storage`` gates ``grid.step()``,
so the ``dqn_core_only`` config (storage disabled) never advances the
simulation clock and stays at hour 3 — the day's lowest load factor
(``LOAD_CURVE[3] = 0.27``) — while ``full_stack`` / ``rule_based``
advance into peak-load hours. The headline "dqn_core_only beats
rule_based" result is therefore a time-of-day load-scaling artifact,
not a controller effect, and the ablation rows ``full_stack`` /
``no_lstm`` / ``no_twin`` / ``no_predictive`` / ``no_reward`` are
behaviourally identical (their Table IV ENS spread is RNG noise from
section 1.4).

**Workaround:** none for the existing results. The runner must be
corrected (call the DQN in ``eval_mode()``; advance the clock for all
policies) and the Stage 26 experiment re-run before any superiority
claim is made. See EHM-CRIT-007 in the audit.

### 1.5 No round-trip efficiency in the storage model

**Severity:** BLOCKER.
**Scope:** Simulator.

The hybrid storage dispatch (see `docs/HYBRID_STORAGE.md`) treats
energy-in = energy-out per transfer. Real batteries have
round-trip efficiencies of 80–95 %; real supercapacitors have 90–98 %.
The paper's storage claims do not account for these losses.

**Workaround:** the paper caps the storage runtime as "lossless
proxy" and references the more detailed battery model in EHM
extensions.

### 1.6 Single-DQN policy, not multi-agent

**Severity:** BLOCKER.
**Scope:** Both.

The DQN operates per-node (homogeneous action space). There is no
communication between agents, no shared replay buffer, no MARL
coordination. The paper does not claim MARL benefits.

### 1.7 LSTM sees historical data, not exogenous weather

**Severity:** BLOCKER.
**Scope:** Both.

The LSTM input is a 3-channel observation of (load, generation, voltage)
history. There is no weather (temperature, irradiance, wind speed) input.
In real settings, weather drives load and renewables harder than
history.

**Workaround:** the paper describes the LSTM as "history-only" and
lists weather integration as a *future-work* item.

---

## 2. CAUTION limitations

These are known but not paper-critical.

### 2.1 No construction-cost model in the planner

The AI planner proposes tie switches and backup paths without
accounting for the cost of building them. The optimisation is
weighted, not cost-weighted.

### 2.2 No thermal ageing on the digital twin

The twin's `health_risk_score` is a heuristic (load × temperature ×
age). It does not capture Arrhenius chemistry, dendrite growth, or
explosion risk.

### 2.3 No peer-to-peer trading

There is no market layer (LMP, nodal pricing, P2P contracts). The
paper does not claim market benefits.

### 2.4 No HVDC / FACTS

The grid is assumed radial AC. There is no LCC-HVDC link, no VSC
converter, no SSSC, no UPFC.

### 2.5 No three-phase unbalance

The simulator is single-phase. Real distribution feeders are
three-phase and unbalanced. Per-phase reporting is not supported.

### 2.6 No protection coordination

There is no overcurrent relay, distance relay, or recloser. The
"fault" is a node-failure, not a bolted three-phase short.

### 2.7 No timing constraints

The FLISR is instrumented with per-stage timings, but the controller
runs as fast as Python can. There is no real-time deadline.

### 2.8 No failure-propagation model

A failing node takes down its downstream nodes, but the failure
itself is sampled, not derived from physics (mechanical stress,
thermal runaway, etc.).

---

## 3. COSMETIC limitations

These are minor and don't affect the paper.

* **No GUI** — the simulator is CLI-only.
* **No GPU** — DQN training is CPU-only; the LSTM is small enough
  that GPU would not help.
* **No distributed run** — single-process; ablation is
  embarrassingly parallel but not parallelized.
* **SmartGrid RNG dependency** — see 1.4; ablation seed-sweeps
  paper over it but individual runs are not deterministic.

---

## 4. What the paper says about each limitation

Each figure caption / table footnote should include the relevant
"limitation badge" from the table below:

| Badge | Meaning |
|-------|---------|
| `SIM-VALIDATED` | Result is from the simulator, not real-world data. |
| `DC-PF` | Voltage / var numbers are DC-PF proxies. |
| `NO-RT-EFF` | Round-trip efficiency is 100 %. |
| `WEATHER-NONE` | LSTM does not see weather. |
| `RNG-NON-DET` | SmartGrid init is non-deterministic. |
| `LOSS-LESS` | No thermal losses. |
| `NO-FIELD` | No real-world validation. |

---

## 5. Citation form

> The EHM simulator is a simulation-validated framework. It does not
> include real-world validation, hardware-in-the-loop, or full AC-PF.
> All voltages are DC-PF proxies; storage round-trip efficiency is
> 100 %; the LSTM sees no weather; the planner optimises a weighted
> cost without construction costs. The paper's claims are limited to
> what the simulator can demonstrate — see the figure / table footnotes
> for the limitation badge applicable to each result.
