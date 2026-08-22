# Stage 46.2 — Battery End-to-End Trace

## Trace Path

```
renewable generation
    → excess energy
    → EMS
    → STORAGE_BAT (node_type="battery", node_id="STORAGE_BAT")
    → battery SOC
    → DQN observation (feature 73)
    → use_battery action (action 1)
    → consumer load
    → received power
```

## Link-by-Link Evidence

| Stage | Source | Function | Variable | Node | State Feature | Action | Physical Effect |
|-------|--------|----------|----------|------|---------------|--------|-----------------|
| 1 | Solar/Wind | `node.step()` / `_apply_time_curves()` | `generation` | GEN_SOLAR, GEN_WIND | — | — | Generation produced |
| 2 | Grid | `update_generation()` → `node.step()` | `excess_energy = max(0, generation - load)` | All nodes | — | — | Excess computed post-storage-charge |
| 3 | EMS | `EnergyManagementSystem.run()` → `_charge_storage()` | `battery_level += absorbed / capacity` | STORAGE_BAT (node_type="battery") | — | — | Battery charged (0.75 → 0.839 at t=34) |
| 4 | Physics | `node.step()` (battery branch) | `generation = discharge_signal` | STORAGE_BAT | — | — | Discharge appears as generation injection |
| 5 | Power Flow | `update_power_flow()` → `dc_power_flow()` / `_simulate_energy_flow()` | `received_power` | Downstream houses | — | — | Power delivered to consumers |
| 6 | DQN Observation | `runner._storage_level(grid, "battery")` | `max(battery_level for house + battery nodes)` | STORAGE_BAT, houses | Feature 73 | — | **NOW INCLUDES STORAGE_BAT** (fixed) |
| 7 | DQN Action | `runner._dispatch_action(grid, 1)` → `node.use_battery()` | `battery_level -= delivered / capacity` | STORAGE_BAT, houses | — | Action 1 | Battery discharged (SOC -0.00267) |
| 8 | Physics | `node.step()` | `_discharge_signal_mw` preserved | Houses + STORAGE_BAT | — | — | Discharge persists through step |
| 9 | Power Flow | `update_power_flow()` | `received_power` | Consumer nodes | — | — | **Measured: dServed=+0.010 MWh at t=4** |

## Key Findings

### Before Fix (Stage 46.1)
- **Action 1 never reached STORAGE_BAT** — dispatch logic checked `"storage_bat" in node_type` but actual type is `"battery"`
- **Feature 73 excluded STORAGE_BAT** — only read `node_type == "house"` nodes

### After Fix (Stage 46.2)
- **Action 1 discharges STORAGE_BAT** — `dSOC_bat = -0.00267` (150 MWh × 0.00267 = 0.4 MWh delivered)
- **Action 1 also discharges house batteries** — `dhouse_bat = -0.04` (10 MWh × 0.04 = 0.4 MWh per house)
- **Feature 73 NOW includes STORAGE_BAT** — fixed in `_storage_level()` and validation harnesses
- **Measurable consumer benefit** — `dServed = +0.010 MWh` at night (t=4), `+0.010 MWh` at midday (t=34)

## Physical Probe Results (Scenario A, Seed 0)

| Time | Action | STORAGE_BAT ΔSOC | House ΔSOC | ΔServed (MWh) | ΔENS (MWh) | ΔReceived Power (MW) |
|------|--------|------------------|------------|---------------|------------|---------------------|
| t=34 (midday) | use_battery | **-0.00267** | -0.04000 | +0.0100 | +0.0008 | +0.200 |
| t=4 (night) | use_battery | **-0.00267** | -0.04000 | +0.1042 | -0.0042 | +5.854 |

**Conclusion:** Battery action is PHYSICALLY VERIFIED. The grid-scale battery (STORAGE_BAT) now participates in discharge and the effect reaches consumers via power flow.