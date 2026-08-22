# Stage 45 — Current Metric Trace

## Purpose

For every reliability metric, trace the exact data source
that produces it. Identify whether the source is the
*physical service state* (post power-flow) or the *fault
schedule* (input).

## 1. `energy_not_served_mwh` — physical, but invariant

**Definition (Stage-44 code):**

```python
# experiments/stage44_validation.py §649–682
for nid, n in grid.nodes.items():
    nt = str(getattr(n, "node_type", ""))
    if nt not in ("house", "industry", "hospital"):
        continue
    received = float(getattr(n, "received_power", 0.0) or 0.0)
    if nt == "house":
        would_be = float(getattr(n, "_base_load", 0.0) or 0.0)
    else:
        would_be = received + 0.0   # ← bug: industry/hospital would_be = received!
    served += received
    baseline += would_be
short = max(0.0, baseline - served)
energy_not_served += short / 60.0
```

**Trace:**

| Source field                       | Set by                                           | Updated per step? |
|------------------------------------|--------------------------------------------------|-------------------|
| `grid.nodes[L].received_power`     | `_simulate_energy_flow` BFS (line 1078+)        | Yes |
| `grid.nodes[L]._base_load`         | `_apply_time_curves` (house only);  constructor | Yes (house only) |
| `grid.nodes[L].load`               | `_apply_time_curves` (industry / hospital)      | Yes (industry / hospital) |

**Diagnosis.** The metric compares `received_power` against
`_base_load` for houses and against `received_power` for
industry / hospital. The `received_power` field is set by
`_simulate_energy_flow` BFS starting from generator /
substation sources and splitting evenly along active
edges. **The BFS does not recognise storage (house /
battery / supercap) nodes as sources**, even though
`use_battery()` correctly increments `node.generation`.
This is the *physical coupling gap* described in
`STAGE_45_IMPLEMENTATION_PLAN.md` §2.2.

**Result for Stage-43 scenarios:**

| Scenario | ENS contribution from houses   | ENS contribution from industry / hospital |
|----------|--------------------------------|------------------------------------------|
| A        | 0 (no fault, BFS delivers all)  | 0 (industry / hospital `would_be = received`) |
| E        | 0 (degraded twin, no physical fault) | 0 |
| G        | 0 (low renewable, no service interruption) | 0 |
| H        | 0 (degraded twin, no service interruption) | 0 |
| J        | Non-zero (heavy faults), but identical across all 12 controllers because all controllers produce the same `received_power = 0` on isolated sub-trees | Non-zero, identical |

## 2. `total_customer_minutes_interrupted` — derived

**Definition (Stage-44 code):**

```python
cmi = float(critical_interruption_steps) * (1.0 / 6.0)
```

where `critical_interruption_steps` is incremented each
step a critical-load (hospital / hospital_icu) node had
`received_power <= 0`.

**Trace.** CMI is derived from
`critical_load_interruption_steps` (see §3). It is a unit
conversion, not an independent measurement. Therefore,
CMI invariance follows from `critical_load_interruption_steps`
invariance.

## 3. `critical_load_interruption_steps` — physical, but invariant

**Definition (Stage-44 code):**

```python
for nid, n in grid.nodes.items():
    nt = str(getattr(n, "node_type", ""))
    if nt not in ("house", "industry", "hospital"):
        continue
    received = float(getattr(n, "received_power", 0.0) or 0.0)
    if nt in CRITICAL_NODE_TYPES and received <= 0:
        crit_int += 1
```

with `CRITICAL_NODE_TYPES = {"hospital", "hospital_icu"}`.

**Trace.** `received_power` for hospitals is the BFS split
from the upstream generator / substation. Hospitals are
critical loads but in the Stage-43 scenario matrix, no
hospital is in a faulted sub-tree — so `received_power > 0`
for every hospital on every step. Result: invariant zero
across all controllers.

## 4. `voltage_violation_count` — physical, but invariant

**Definition (Stage-44 code):**

```python
n_voltage_violations += int(
    any(
        abs(float(getattr(n, "voltage", 1.0) or 1.0) - 1.0) > 0.10
        for n in grid.nodes.values()
    )
)
```

**Trace.** `node.voltage` is set by
`_simulate_energy_flow` (line 1139: `node.voltage = max(0.95,
u_node.voltage - 0.01)`) and by `update_power_flow` (line
643: `node.voltage = 1.0` for non-failed; line 637:
`node.voltage = 0.0` for failed).

In Stage-43 scenarios, no fault cascades produce
`|V − 1.0| > 0.10` and no faulted hospital sub-tree yields
a non-zero violation count.

**Result:** invariant zero across all controllers.

## 5. `restoration_rate` and `avg_restoration_steps`

**Definition (Stage-44 code):**

```python
for target, base_load in list(fault_baseline_load.items()):
    if target in restored_targets:
        continue
    served = 0.0
    downstream = [target] + list(nx.descendants(grid.graph, target))
    for nid in downstream:
        n = grid.nodes.get(nid)
        ...
        received = float(getattr(n, "received_power", 0.0) or 0.0)
        if received > 0:
            served += float(getattr(n, "_base_load", 0.0) or 0.0)
    if base_load > 0 and served >= 0.85 * base_load:
        restored_targets.add(target)
        n_restored += 1
        ...
        restoration_steps.append(int(t - fault_timesteps[target]))
```

**Trace.** Restoration is measured *per fault target* by
walking the downstream sub-tree and checking if 85 % of
the baseline load is being served. The metric depends on
`received_power` per node, which is **identical across all
controllers** (per §1).

**Result:** `restoration_rate` and
`avg_restoration_steps` are invariant in scenarios where
the fault outcome does not depend on the controller
action (A/E/G/H and J's restoreable parts).

## 6. `battery_discharged_total` and `supercap_discharged_total`

**Definition (Stage-44 code):**

```python
if action_id == 1:
    for nid, n in grid.nodes.items():
        if str(getattr(n, "node_type", "")) == "house":
            battery_discharged += max(
                0.0,
                0.5 - float(getattr(n, "battery_level", 0.0) or 0.0),
            )
```

**Trace.** This is a **side-channel instrumentation**, not
a power-flow measurement. It computes the cumulative
*intended* discharge (= `max(0, 0.5 - current_level)`) per
action-1 step, summed across the run.

**Result:** varies with controller (different controllers
choose action 1 at different rates). This is the ONLY
metric in Stage-44 that varied across controllers.

## 7. Summary

| Metric                              | Source                          | Stage-43 sensitivity to controller |
|-------------------------------------|---------------------------------|-----------------------------------|
| `energy_not_served_mwh`             | post power-flow (BUG: industry/hospital `would_be = received`) | **0 / 12 cells** |
| `total_customer_minutes_interrupted`| derived (CMI = crit_steps × 1/6) | **0 / 12 cells** |
| `critical_load_interruption_steps`  | post power-flow                 | **0 / 12 cells** |
| `voltage_violation_count`           | post power-flow                 | **0 / 12 cells** |
| `restoration_rate`                  | post power-flow                 | 13 / 60 cells (35 / 50 groups) |
| `battery_discharged_total`          | side-channel (instrumentation)  | 15 / 60 cells (35 / 50 groups) |
| `supercap_discharged_total`         | side-channel (instrumentation)  | 50 / 50 groups |

## 8. Root cause (confirmed)

The Stage-44 metric contract is structurally *correct* —
the formulas are right. The *data sources* are not the
fault schedule; they are the post-power-flow state. **The
problem is twofold:**

1. **Scenario-dimension limit.** The Stage-43 scenario
   matrix does not stress the controllers in ways that
   would make the post-power-flow metrics differ.

2. **Physical-coupling gap.** The BFS source set is
   `{generator*, solar_farm, wind_farm, substation,
   primary_substation}`. House nodes with `generation > 0`
   (after `use_battery` / `use_supercapacitor`) are NOT
   added to the source set, so storage discharge is
   computed but never delivered to downstream load
   nodes.

The Stage-45 metric audit does NOT extend the scenario
matrix — that would violate the "do not modify evaluation
scenarios" rule. Instead, it (a) **broadens the BFS source
set** to include any live node with `generation > 0`, and
(b) **fixes the metric loop** so it treats `received_power`
uniformly across house / industry / hospital. After these
fixes, controller-level variation in ENS / CMI /
critical-load interruption becomes observable.