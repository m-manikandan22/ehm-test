# Stage 46.2 — Supercapacitor End-to-End Trace

## Trace Path

```
renewable generation / grid deficit
    → supercapacitor
    → SOC
    → DQN observation (feature 74)
    → use_supercapacitor action (action 2)
    → consumer support
    → voltage / received power
```

## Link-by-Link Evidence

| Stage | Source | Function | Variable | Node | State Feature | Action | Physical Effect |
|-------|--------|----------|----------|------|---------------|--------|-----------------|
| 1 | Grid deficit / voltage dip | `EMS.run()` → `_priority_energy_allocation()` | `supercap_level -= delivered / capacity` | STORAGE_SC (node_type="supercap") | — | — | Supercap discharged for voltage support |
| 2 | Physics | `node.use_supercapacitor()` | `load -= delivered` | STORAGE_SC, houses | — | Action 2 | **Node-local load offset** (not generation injection) |
| 3 | Power Flow | `update_power_flow()` | `received_power` | Consumer nodes | — | — | Reduced load = less power needed |
| 4 | DQN Observation | `runner._storage_level(grid, "supercap")` | `max(supercap_level for house + supercap nodes)` | STORAGE_SC, houses | Feature 74 | — | **NOW INCLUDES STORAGE_SC** (fixed) |
| 5 | DQN Action | `runner._dispatch_action(grid, 2)` → `node.use_supercapacitor()` | `supercap_level -= delivered / capacity` | STORAGE_SC, houses | — | Action 2 | Supercap discharged (SOC -0.01333) |

## Key Findings

### Before Fix (Stage 46.1)
- **Action 2 never reached STORAGE_SC** — dispatch logic checked `"storage_sc" in node_type` but actual type is `"supercap"`
- **Feature 74 excluded STORAGE_SC** — only read `node_type == "house"` nodes
- **Supercap physics is node-local** — `use_supercapacitor()` reduces the node's own `load`, does not inject generation

### After Fix (Stage 46.2)
- **Action 2 discharges STORAGE_SC** — `dSOC_sc = -0.01333` (15 MWh × 0.01333 = 0.2 MWh delivered)
- **Action 2 also discharges house supercaps** — `dhouse_sc = -0.170` to `-0.200` (1 MWh × 0.17 = 0.17 MWh per house)
- **Feature 74 NOW includes STORAGE_SC** — fixed in `_storage_level()` and validation harnesses
- **Consumer effect is indirect** — supercap reduces local load, which reduces power flow demand

## Physical Probe Results (Scenario A, Seed 0)

| Time | Action | STORAGE_SC ΔSOC | House ΔSOC | ΔServed (MWh) | ΔENS (MWh) | ΔReceived Power (MW) |
|------|--------|-----------------|------------|---------------|------------|---------------------|
| t=34 (midday) | use_supercap | **-0.01333** | -0.17041 | -0.0833 | +0.0008 | -5.000 |
| t=4 (night) | use_supercap | **-0.01333** | -0.20000 | +0.0109 | +0.0016 | +0.654 |

**Note:** At midday (t=34), the supercap discharge coincides with solar generation drop (night transition in the step), causing a net negative served. At night (t=4), the supercap provides a small positive effect.

## Supercapacitor vs Battery — Role Distinction

| Aspect | Battery (STORAGE_BAT) | Supercapacitor (STORAGE_SC) |
|--------|----------------------|----------------------------|
| **Capacity** | 150 MWh | 15 MWh |
| **Initial SOC** | 0.75 | 1.0 |
| **Discharge mechanism** | Generation injection (`generation += delivered`) | Load offset (`load -= delivered`) |
| **Power flow effect** | Adds to BFS source set | Reduces demand at node |
| **Action 1 ΔSOC** | -0.00267 (0.4 MWh) | N/A |
| **Action 2 ΔSOC** | N/A | -0.01333 (0.2 MWh) |
| **EMS charging** | Yes (0.75 → 0.839 at t=34) | No (stays at 1.0) |
| **Fast transient role** | NOT demonstrated | NOT demonstrated |

## Critical Finding: Fast Transient Support NOT Demonstrated

The conceptual claim is that supercapacitor handles fast transients while battery handles sustained energy. **This is NOT SUPPORTED by the implementation:**

1. **No voltage-triggered dispatch** — Action 2 is not automatically triggered by voltage dips; it's a DQN action like any other
2. **No time-scale separation** — Both battery and supercap discharge in a single step (0.2 MWh vs 0.1 MWh per node)
3. **Supercap never used by frozen policy** — Policy always selects action 4 (reroute) on scenarios A-E
4. **EMS voltage threshold exists but unused** — `VOLTAGE_DIP_THRESHOLD = 0.97` in EMS but grid voltage never drops below 0.95 in probes

**Verdict:** SUPERCAPACITOR FAST TRANSIENT ROLE = **NOT SUPPORTED**

The supercapacitor is physically simulated and can be discharged, but the control logic does not distinguish its fast-response role from the battery's sustained-energy role.