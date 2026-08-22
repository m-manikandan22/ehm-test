# Stage 45 — Physics Coupling

## Purpose

The Stage-44 metric contract was structurally correct
(ENS = Σ (P_demand − P_served) × Δt) but **physically
disconnected**: the BFS source set included only
generators and substations, so storage actions (action 1
`use_battery`, action 2 `use_supercapacitor`) updated
`node.generation` but the surplus was ignored by the
power-flow distribution.

This document specifies:

1. The full data flow from fault → controller → power
   flow → metric.
2. The Stage-45 source-broadening fix.
3. The DC power-flow limitations.
4. The per-action physical-effect audit.

## 1. Full data flow

```
       ┌────────────────────────────────────────────┐
       │              SCENARIO INPUT                 │
       │  faults_by_step, demand_mult, renew_mult,  │
       │  battery_soc_init, health_override         │
       └────────────────────┬───────────────────────┘
                            │
                            ▼
       ┌────────────────────────────────────────────┐
       │     GRID CONSTRUCTION (deterministic)      │
       │   seed → SmartGrid(nodes, edges, weights)  │
       └────────────────────┬───────────────────────�
                            │
                            ▼
       ┌────────────────────────────────────────────┐
       │          FOR EACH TIMESTEP t               │
       │                                            │
       │  1. inject faults at t                     │
       │  2. controller.choose_action(state)        │
       │  3. dispatch action (see §3)               │
       │  4. grid.step()    — time curves           │
       │  5. grid.update_power_flow()               │
       │       ├─ _simulate_energy_flow (BFS)       │
       │       │     sources = generators ∪         │
       │       │              substations ∪         │
       │       │              STORAGE w/ gen>0      │
       │       │     (Stage-45 broadening)          │
       │       └─ DC power flow overlay             │
       │  6. Stage45MetricCollector.step(grid)     │
       │     record per-load-node                   │
       │     (P_demand, P_served, P_unserved, V)    │
       └────────────────────┬───────────────────────┘
                            │
                            ▼
       ┌────────────────────────────────────────────┐
       │          Stage45ReliabilityMetrics         │
       │  ENS, CMI, critical_load_interruption_     │
       │  steps, voltage_violation_count,           │
       │  restoration_rate, avg_restoration_steps   │
       └────────────────────────────────────────────┘
```

## 2. Stage-45 source-broadening fix

`_simulate_energy_flow` (in `simulation/grid.py`) used
to declare the BFS source set as:

```python
sources = [
    nid for nid, n in self.nodes.items()
    if not n.failed and (
        _is_generator(n.node_type)
        or n.node_type in ("substation", "primary_substation")
    )
]
```

**Stage-45 broadening** — the BFS source set now also
includes any live node whose `generation` field is
positive at this step (house / battery / supercap /
storage_bat / storage_sc). This is the *physical
coupling* that lets `use_battery` /
`use_supercapacitor` injections reach downstream load
nodes.

The fix is documented inline at the broadened source
list. It does NOT change the BFS distribution rule
(power is still split evenly across children); it only
expands the source set so the surplus *reaches* the BFS.

## 3. Per-action physical effect audit

| Action id | Name              | Physical effect (per `_dispatch_action`)        | Coupled to ENS via                              |
|----------:|-------------------|--------------------------------------------------|-------------------------------------------------|
| 0         | `increase_generation` | `target.increase_generation(0.5)` → `generation × 1.5` | Generator source set → BFS → received_power   |
| 1         | `use_battery`     | `node.use_battery(0.2)` → `generation += 0.2`  | House / battery node → broadened source set → BFS |
| 2         | `use_supercapacitor` | `node.use_supercapacitor(0.1)` → `load -= 0.1` | Demand reduction → P_demand reduces → unserved reduces |
| 3         | `shift_load`      | `node.shift_load(0.15)` → `load -= 0.15 * load` | Demand reduction (per-node) → P_demand reduces |
| 4         | `reroute_energy`  | `grid.reroute_energy()` → closes tie-switches | Topology change → next BFS run sees different connectivity |

## 4. DC power-flow limitations

The project uses **DC power flow** for the per-step
feasibility check:

* DC PF computes bus *voltage angles*, not magnitudes.
  The `node.voltage` field is a proxy, not the AC PF
  solution.
* The 0.10 pu voltage-violation band is a heuristic,
  not a regulatory standard (ANSI C84.1 allows
  0.95–1.05 pu).
* DC PF does NOT model reactive power, line losses,
  transformer tap-changers, or voltage regulators.
* DC PF *does* model Kirchhoff's current law
  (`KCL residual`) and per-bus power balance.

These limitations are documented in
`docs/STAGE_43_RUNTIME_CONTROL_FLOW.md`. Stage-45 does
not claim AC power-flow realism; the project has
declared DC power flow as its feasibility model.

## 5. KCL residual and physical-feasibility gate

`dc_power_flow` returns a `KCL residual` field
(squared sum of bus-balance residuals). Stage-43
introduced a feasibility gate: runs with KCL residual
above a threshold are flagged as `valid=False`. Stage-45
preserves this gate unchanged.

## 6. Stage-45 metric-loop integrity

`Stage45MetricCollector.step()` reads the *current* grid
state after `grid.update_power_flow()`. This means the
metric loop is **post-action**: it sees the BFS
distribution *after* the controller action has been
dispatched. There is no separate "metric snapshot"
phase.

## 7. Storage-coupling verification (deterministic test)

```python
# tests/test_stage45_action_sensitivity.py
def test_battery_discharge_changes_received_power():
    g_a = _build_grid()
    m_a = _run(g_a, lambda g, t: -1)   # no action
    g_b = _build_grid()
    m_b = _run(g_b, lambda g, t: 1)    # use_battery
    assert m_b["energy_not_served_mwh"] < m_a["energy_not_served_mwh"]
```

This test fails if the Stage-45 source broadening is
not active. It is the *physical-coupling regression
test* that catches the Stage-44 finding.

## 8. Topology-coupling verification

```python
def test_reroute_changes_received_power():
    g_a = _build_grid()
    m_a = _run(g_a, lambda g, t: -1)
    g_b = _build_grid()
    m_b = _run(g_b, lambda g, t: 4)   # reroute_energy
    # The metric MUST differ if the rerouted topology
    # changes the downstream sub-tree.
    assert (
        m_a["energy_not_served_mwh"] != m_b["energy_not_served_mwh"]
        or m_a["total_customer_minutes_interrupted"]
            != m_b["total_customer_minutes_interrupted"]
    )
```

## 9. Fault-schedule independence

The metric contract does NOT use the fault schedule
directly. The fault schedule is an *input* to the
grid (it triggers `node.failed = True`), but every
metric is derived from the resulting
`node.received_power` / `node.voltage` / `node.failed`
state — not from the fault list itself.

A fault schedule describing `WHEN and WHERE` does not
determine ENS — only the **power-flow consequences** of
that fault schedule do.

## 10. Summary

The Stage-45 metric contract is *physics-coupled*:
every metric is derived from the post-power-flow state
of the grid, with the BFS source set broadened so that
storage actions physically deliver their injections to
downstream load nodes. The metric contract does not
infer controller quality from action distributions
alone; it measures the actual service outcome of each
controller's decisions.