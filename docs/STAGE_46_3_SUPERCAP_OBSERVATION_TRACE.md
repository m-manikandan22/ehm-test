# Stage 46.3 — Supercapacitor Observation Trace

## 1. Complete Code Path

```
STORAGE_SC.supercap_level (GridNode attribute)
    ↓
runner._storage_level(grid, "supercap")  [runner.py:343–360]
    ↓
max() over nodes where node_type in {"house", "supercap"}
    ↓
feature 74 value (float in [0, 1])
    ↓
build_extended_state()  [rl_agent.py:100–122]
    ↓
extended_state[74] = supercap_soc
    ↓
DQNAgent.select_action()  [rl_agent.py:471–540]
    ↓
policy_net(torch.tensor(state_vec))  [rl_agent.py:129–143]
    ↓
Q-values for 5 actions
```

## 2. Source Object and Variable

| Level | Object | Variable | Type | Initial Value (seed 0) |
|-------|--------|----------|------|------------------------|
| Grid Node | `grid.nodes["STORAGE_SC"]` | `supercap_level` | float | 1.0 |
| Grid Node | `grid.nodes["H0"]`–`grid.nodes["H12"]` | `supercap_level` | float | 1.0 (each) |
| Grid Node | `grid.nodes["STORAGE_SC"]` | `supercap_capacity` | float | 15.0 MWh |
| Grid Node | `grid.nodes["H0"]`–`grid.nodes["H12"]` | `supercap_capacity` | float | 1.0 MWh (each) |

## 3. Aggregation Logic

**Function**: `runner._storage_level(grid, "supercap")` (lines 343–360)

```python
def _storage_level(grid, kind: str) -> float:
    best = 0.0
    attr = "battery_level" if kind == "battery" else "supercap_level"
    for n in grid.nodes.values():
        ntype = str(getattr(n, "node_type", "") or "")
        is_storage = (
            ntype == "house"
            or (kind == "battery" and ntype == "battery")
            or (kind == "supercap" and ntype == "supercap")
        )
        if not is_storage:
            continue
        if getattr(n, "failed", False) or getattr(n, "isolated", False):
            continue
        best = max(best, float(getattr(n, attr, 0.0) or 0.0))
    return best
```

**Included node types for supercap**: `house`, `supercap`

**Aggregation**: `max()` — returns the highest SOC among all non-failed, non-isolated house and supercap nodes.

## 4. Feature Index

| Feature | Index | Value Range | Normalization |
|---------|-------|-------------|---------------|
| Supercapacitor SOC | 74 | [0.0, 1.0] | Raw (no scaling) |

## 5. Normalization

- **Input**: Raw SOC fraction (0.0 = empty, 1.0 = full)
- **Processing**: None — passed directly to `build_extended_state()`
- **Network Input**: Fed as-is to first Linear layer (78→64)
- **Note**: No min-max scaling, no standardization applied

## 6. Final Tensor Value Flow

```
Initial state (seed 0, t=0):
  House supercaps (13 nodes): supercap_level = 1.0 each
  STORAGE_SC: supercap_level = 1.0
  _storage_level() → max(1.0, 1.0, ..., 1.0) = 1.0
  build_extended_state() → extended_state[74] = 1.0
  DQN input[74] = 1.0

After grid supercap drain (e.g., STORAGE_SC.supercap_level = 0.667):
  House supercaps: still 1.0 (unless action 2 dispatched)
  STORAGE_SC: supercap_level = 0.667
  _storage_level() → max(1.0, 1.0, ..., 0.667) = 1.0
  build_extended_state() → extended_state[74] = 1.0
  DQN input[74] = 1.0  ← UNCHANGED
```

## 7. Masking Evidence

**Stage 46.2 storage_state_trace.json** shows:

| Scenario | STORAGE_SC SOC | Feature 74 (corrected) | Changed? |
|----------|----------------|------------------------|----------|
| A, step 34 | 0.667 | 1.0 (before) → 1.0 (after) | ❌ No |
| A, step 4 | 0.667 | 1.0 (before) → 1.0 (after) | ❌ No |

**Conclusion**: The `max()` aggregation over house nodes (fixed at 1.0) **completely masks** the grid-scale supercapacitor SOC. The DQN cannot observe grid supercapacitor state changes.

## 8. Why This Exists

1. **Legacy design**: Original observation only read house nodes (`node_type == "house"`)
2. **Stage 46.2 fix**: Added `supercap` node type to `_storage_level()` but kept `max()` aggregation
3. **House initialization**: All 13 houses start with `supercap_level = 1.0` (full)
4. **No discharge mechanism for houses**: Houses only discharge when action 2 (`use_supercapacitor`) is selected by controller — the frozen policy never selects action 2 (pinned at action 4)
5. **EMS doesn't charge supercap**: `EnergyManagementSystem.run()` only charges battery, not supercapacitor

## 9. What It Hides

| Grid Supercap State | Actual SOC | DQN Feature 74 | Observable? |
|---------------------|------------|----------------|-------------|
| Initial | 1.0 | 1.0 | ❌ (matches by accident) |
| After action 2 drain | 0.987 | 1.0 | ❌ |
| Deep discharge | 0.667 | 1.0 | ❌ |
| Critical low | 0.20 | 1.0 | ❌ |
| Empty | 0.0 | 1.0 | ❌ |

**The DQN receives a constant 1.0 regardless of actual grid supercapacitor state.**

## 10. Physical vs Observed Disconnect

| Physical Reality | DQN Observation |
|------------------|-----------------|
| STORAGE_SC: 15 MWh capacity | Feature 74 = 1.0 (constant) |
| SOC varies 1.0 → 0.987 → 0.667 | No change in feature |
| Action 2 discharges supercap (-0.01333 SOC) | Invisible to DQN |
| Supercap provides load offset (0.2 MWh per node) | DQN cannot correlate |
| Supercap never charged by EMS | Stays at 1.0 until action 2 used |

**Classification**: **PHYSICALLY ACTIVE / OBSERVATION DISCONNECTED**

## 11. Critical Difference from Battery

| Aspect | Battery (STORAGE_BAT) | Supercapacitor (STORAGE_SC) |
|--------|----------------------|----------------------------|
| Initial SOC | 0.75 | 1.0 |
| House SOC | 1.0 | 1.0 |
| Masking | max(1.0, 0.75) = 1.0 | max(1.0, 1.0) = 1.0 |
| EMS charges | Yes (0.75 → 0.839) | No |
| Action that drains | Action 1 (use_battery) | Action 2 (use_supercapacitor) |
| Discharge mechanism | Generation injection | Load offset (local only) |
| Frozen policy selects | Never (action 4) | Never (action 4) |

**Key insight**: For supercapacitor, the initial match (both 1.0) is accidental. Any drain of STORAGE_SC is immediately masked because houses remain at 1.0.