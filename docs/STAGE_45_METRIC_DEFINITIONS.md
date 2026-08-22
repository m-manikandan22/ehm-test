# Stage 45 — Metric Definitions

This document specifies the **corrected** reliability
metric definitions used in Stage-45. Every metric is
derived from the *post-power-flow* grid state — never
from the fault schedule directly.

## Symbols

| Symbol                        | Units       | Definition                                           |
|-------------------------------|-------------|------------------------------------------------------|
| `L`                           | —           | A load node id                                       |
| `t`                           | step        | Simulation timestep (1 step = 1 minute by Stage-43)  |
| `Δt_hours`                    | h           | 1/60 (one minute)                                    |
| `P_demand(L, t)`              | MW          | `_base_load` (house) or `load` (others) at step t   |
| `P_served(L, t)`              | MW          | `min(received_power, P_demand(L, t))`               |
| `P_unserved(L, t)`            | MW          | `max(0, P_demand(L, t) - P_served(L, t))`           |
| `L.failed`, `L.isolated`      | bool        | From the BFS / DC power-flow state                   |
| `V(L, t)`                     | pu          | Per-bus voltage (DC PF proxy; see §Physics coupling) |

## 1. ENS

```
ENS = Σ_t  Σ_L  P_unserved(L, t)  ×  Δt_hours
    = Σ_t  Σ_L  max(0, P_demand(L, t) - P_served(L, t)) × 1/60
```

**Units:** MWh (MW × h).

**Constraints:**

* Sum is over distinct load nodes — no double counting.
* Failed nodes contribute `P_demand` to unserved for the
  duration they remain failed.
* Isolated nodes (BFS did not reach them) contribute
  `P_demand` to unserved until the topology restores them.
* `shift_load` reduces `P_demand` legitimately. ENS is
  computed against the *post-shift* demand — the metric
  does not penalise a controller for a legitimate demand-
  response action.

## 2. CMI (Customer-Minutes Interrupted)

For each load node `L`, define:

```
T_interrupt(L) = first t at which P_unserved(L, t) > 0
T_restore(L)   = first t > T_interrupt at which P_unserved(L, t) == 0
                 AND L.failed == False AND L.isolated == False
```

Then:

```
interruption_minutes(L) = max(0, T_restore(L) - T_interrupt(L))

CMI = Σ_L  interruption_minutes(L)
```

**Units:** customer-minutes.

**Per-customer definition:** one load node = one customer.
CMI does NOT collapse to a single outage duration for a
common-cause event — partial restoration (FLISR closes a
tie at step 5; downstream customers restored at step 5,
upstream customers remain faulted) is captured per-load-
node.

**Continuous service:** if no customer is ever unserved,
every `T_interrupt(L)` is `None` and `CMI = 0`.

## 3. Critical-Load Interruption

```
critical_load_interruption_steps
    = Σ_t  Σ_{L in {hospital, hospital_icu}}  [P_unserved(L, t) > 0]
```

**Units:** critical-load-step (one count per (critical
load, step) where the load was unserved).

**Critical-load set:** `{hospital, hospital_icu}`. The
`house`, `industry`, and `service` node types do NOT
contribute.

## 4. Voltage Violation

For each bus `B` at each step `t`:

```
if |V(B, t) - 1.0| > 0.10:
    record a violation at (B, t)
```

```
voltage_violation_count = Σ_{B, t} [|V(B, t) - 1.0| > 0.10]
```

**Limitations:**

* The project uses **DC power-flow voltage proxy** (see
  `STAGE_45_PHYSICS_COUPLING.md`). The voltage field on
  GridNode is `node.voltage ∈ [0, 1.05]` and is a proxy,
  not the AC PF solution.
* The 0.10 pu band is a heuristic, not a regulatory
  standard (ANSI C84.1 allows 0.95–1.05 pu).
* The Stage-45 metric contract uses the same 0.10 pu
  band as Stage-44; the limitation is documented but
  not removed (DC PF is the project's declared
  feasibility model).

## 5. Restoration Rate

For each load node `L` that experienced unserved service:

```
restored(L) = T_restore(L) is not None
```

```
n_restored = Σ_L  [restored(L)]
n_unserved = Σ_L  [T_interrupt(L) is not None]

restoration_rate = n_restored / max(1, n_unserved)
```

## 6. Average Restoration Time

For each load node `L` that was restored:

```
restoration_time(L) = T_restore(L) - T_interrupt(L)
```

```
avg_restoration_steps = (Σ_L  restoration_time(L)) / max(1, n_restored)
```

## 7. Side-Channel Accumulators (not primary metrics)

The runner also tracks:

* `battery_discharged_total` — cumulative
  `max(0, 0.5 - battery_level)` per action-1 step.
* `supercap_discharged_total` — cumulative
  `max(0, 0.5 - supercap_level)` per action-2 step.

These are *side-channel instrumentation*, not derived
from the post-power-flow state. They remain in the
runner output for the Stage-43 action-distribution
audit, but they are NOT the primary reliability metrics.

## 8. Per-load-node diagnostic record

Every run also records a per-load-node dict:

```
{
  "node_id":                  <str>,
  "node_type":                <str>,
  "is_critical":              <bool>,
  "cumulative_unserved_mwh":  <float>,
  "cumulative_served_mwh":    <float>,
  "cumulative_demand_mwh":    <float>,
  "n_steps_unserved":         <int>,
  "n_steps":                  <int>,
  "first_unserved_step":      <int or null>,
  "restored_step":            <int or null>,
  "min_voltage_seen":         <float>,
  "max_voltage_seen":         <float>,
  "n_voltage_violations":     <int>,
}
```

This record lets the validator trace the physical
service state per load node, per run, without relying on
aggregate metrics alone.