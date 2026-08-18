# Stage 41 — Scenario Matrix

This document defines a scientifically justified set of harder scenarios
that the Stage-42 implementation should run. Each scenario is anchored
in measurable characteristics of the existing simulation engine.

> **Important**: We do NOT add new fault kinds, new actions, or new
> grid types in Stage 41. We only define the scenarios. The actual
> extension to `backend/experiments/scenario.py` is Stage-42 work.

---

## 1. Existing model parameters (anchors)

* Grid: 49-node EHM distribution feeder (sources: GEN_SOLAR, GEN_WIND,
  GEN_NUCLEAR, GEN_COAL, GEN_GAS; loads: 24 residential + 1 hospital +
  industries). Tie switches exist; FLISR 9-stage is implemented.
* Renewable curves: `SOLAR_CURVE`, `WIND_CURVE` per
  `backend/simulation/grid.py`.
* Battery and supercapacitor per house node
  (`backend/simulation/node.py`).
* Demand profiles per node type (`house`, `hospital`, `industry`).
* Fault kinds: `pole_failure`, `transformer_overload`, `line_break`,
  `switch_fault` (`backend/experiments/scenario.py::_FAULT_KINDS`).

## 2. Difficulty classification (measurable)

We classify each scenario by four measurable characteristics, each
scored 0/1/2:

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| **Fault severity** | 1 fault | 2–3 faults | ≥ 4 faults or 2 simultaneous |
| **Critical-load exposure** | no hospital/ICU in faulted island | hospital in non-isolated island | hospital in isolated island |
| **Available alternate paths** | ≥ 1 valid tie per island | 0 ties but EMS-eligible | 0 ties, no EMS |
| **Demand / renewable stress** | normal | high demand OR low renewable | both (compound) |

Sum: 0–3 = EASY, 4–5 = MODERATE, 6–7 = HARD, 8 = SEVERE.

This is not arbitrary — every dimension is a property of the existing
model that `backend/simulation/grid.py` can answer.

## 3. Scenario matrix

### Scenario A — Single fault, normal conditions

| Dimension | Score |
|---|---|
| Fault severity | 0 |
| Critical-load exposure | 0 |
| Alternate paths | 0 |
| Demand / renewable | 0 |
| **Total** | **0 → EASY** |

This is the Stage-26 default. All four controllers are saturated
(restoration_rate ≈ 0.95). Useful only as a sanity baseline.

### Scenario B — Single fault, high demand

| Dimension | Score |
|---|---|
| Fault severity | 0 |
| Critical-load exposure | 0 |
| Alternate paths | 0 |
| Demand / renewable | 1 (high demand only) |
| **Total** | **1 → EASY** |

Demand spike: every house load × 1.5 for 10 ticks during a single
fault. **Why**: forces EMS / battery to engage on the unaffected
island. **Hypothesis**: the storage-aware controller should outperform
the 2-action rule-based controller on ENS.

### Scenario C — Single fault, low renewable

| Dimension | Score |
|---|---|
| Fault severity | 0 |
| Critical-load exposure | 0 |
| Alternate paths | 0 |
| Demand / renewable | 1 (low renewable only) |
| **Total** | **1 → EASY** |

Solar output scaled to 0.2 of `SOLAR_CURVE`; wind scaled to 0.3 of
`WIND_CURVE` during a single fault. **Why**: tests whether the
controller can ride out a fault when conventional generation is
limited. **Hypothesis**: EMS / storage awareness should matter.

### Scenario D — Single fault, low battery SOC

| Dimension | Score |
|---|---|
| Fault severity | 0 |
| Critical-load exposure | 0 |
| Alternate paths | 0 |
| Demand / renewable | 0 (but SOC ≈ 0) |
| **Total** | **0 → EASY** (different failure mode) |

Battery SOC forced to 0.05 at fault onset. **Why**: tests whether the
controller conserves the supercapacitor for the high-power transient.
**Hypothesis**: action mask + supercapacitor rule should help.

### Scenario E — Fault + high demand + low renewable

| Dimension | Score |
|---|---|
| Fault severity | 0 |
| Critical-load exposure | 0 |
| Alternate paths | 0 |
| Demand / renewable | 2 (both) |
| **Total** | **2 → EASY** |

The combination of B + C. **Why**: compound stress. **Hypothesis**:
storage + EMS should outperform.

### Scenario F — Critical-load fault

| Dimension | Score |
|---|---|
| Fault severity | 0 |
| Critical-load exposure | 2 |
| Alternate paths | 0 |
| Demand / renewable | 0 |
| **Total** | **2 → EASY** |

Single fault on the line serving the hospital/ICU. **Why**: tests the
priority-aware FLISR path. **Hypothesis**: priority-aware action
selection should help. The 2-action rule-based controller ignores
priority.

### Scenario G — Multiple faults (2 simultaneous)

| Dimension | Score |
|---|---|
| Fault severity | 1 (2 faults) |
| Critical-load exposure | 0 |
| Alternate paths | 0 |
| Demand / renewable | 0 |
| **Total** | **1 → EASY** |

Two faults injected at the same timestep. **Why**: forces FLISR to
handle multiple islands. **Hypothesis**: the 5-action DQN should
outperform a 2-action rule-based because reroute (action 4) becomes
essential.

### Scenario H — Degraded asset + fault

| Dimension | Score |
|---|---|
| Fault severity | 0 |
| Critical-load exposure | 1 (degraded asset adjacent to critical) |
| Alternate paths | 0 |
| Demand / renewable | 0 |
| **Total** | **1 → EASY** |

One pole / transformer has `health ≈ 0.4` for 30 ticks before the
fault (driven by `digital_twin.twin::thermal_ageing_step`). The fault
is then injected on that node. **Why**: tests whether health-aware
predictive control reroutes around the at-risk component before it
fails. **Hypothesis**: a controller that consumes
`health_risk_score` should outperform one that does not.

### Scenario I — Storage stress

| Dimension | Score |
|---|---|
| Fault severity | 0 |
| Critical-load exposure | 1 (storage depletion → cascade risk) |
| Alternate paths | 0 |
| Demand / renewable | 1 (high demand) |
| **Total** | **2 → EASY** |

All batteries start at SOC = 0.1; demand is 1.5× normal; single fault
at a pole. **Why**: forces the controller to choose between immediate
discharge and conservation. **Hypothesis**: hybrid storage
(battery for sustained, supercapacitor for transient) should
outperform battery-only.

### Scenario J — Topology stress

| Dimension | Score |
|---|---|
| Fault severity | 0 |
| Critical-load exposure | 1 |
| Alternate paths | 1 (no valid tie for this fault's island) |
| Demand / renewable | 0 |
| **Total** | **2 → EASY** |

Single fault on a pole that sits on the *only* valid tie-switch path
to a downstream island. **Why**: forces EMS cluster dispatch + load
shedding rather than reroute. **Hypothesis**: an EMS-aware
controller should serve more critical load than a 2-action reactive
controller.

## 4. Combined stress (Stage 42 candidate)

A single "compound stress" scenario combining E + F + I:

* High demand, low renewable.
* Critical-load exposure.
* Low battery SOC.

This would score 2+2+1 = 5 → MODERATE. It is the most likely
scenario where LSTM, twin, and storage all matter.

## 5. Engineering interpretation

| Scenario | Easiest controller | Hardest controller | Discriminating metric |
|---|---|---|---|
| A (default) | any | any | none — saturated |
| B | rule | full_stack | ENS |
| C | rule | storage-aware | ENS, battery use |
| D | rule | hybrid storage | CMI, supercap use |
| E | rule | full_stack | ENS |
| F | rule | priority-aware | critical_load_interruption |
| G | rule | 5-action DQN | restoration_time, ENS |
| H | any | twin-aware | ENS, predictive_reroute_count |
| I | rule | hybrid storage | battery SOC at end |
| J | rule | EMS-aware | restoration_rate, critical_load_restored |

**This is the diagnostic matrix that Stage 42 must implement** to
determine which controllers — and which modules — actually contribute
under which operating conditions.

## 6. Why not just run harder scenarios in Stage 41

We deliberately did not modify `backend/experiments/scenario.py` in
Stage 41. The user explicitly forbade rebuilding the project and
required that existing infrastructure be preserved. The scenarios
above are a *definition* of what Stage 42 should implement.

If the diagnostic experiments in Stage 42 reveal that **none** of the
harder scenarios differentiate the controllers, that is a *negative
result* and we report it honestly — per the master prompt's
"Possible Outcomes" section F.
