# Stage 46.3 — Battery Observation Trace

## 1. Complete Code Path

```
STORAGE_BAT.battery_level (GridNode attribute)
    ↓
runner._storage_level(grid, "battery")  [runner.py:343–360]
    ↓
max() over nodes where node_type in {"house", "battery"}
    ↓
feature 73 value (float in [0, 1])
    ↓
build_extended_state()  [rl_agent.py:100–122]
    ↓
extended_state[73] = battery_soc
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
| Grid Node | `grid.nodes["STORAGE_BAT"]` | `battery_level` | float | 0.75 |
| Grid Node | `grid.nodes["H0"]`–`grid.nodes["H12"]` | `battery_level` | float | 1.0 (each) |
| Grid Node | `grid.nodes["STORAGE_BAT"]` | `battery_capacity` | float | 150.0 MWh |
| Grid Node | `grid.nodes["H0"]`–`grid.nodes["H12"]` | `battery_capacity` | float | 10.0 MWh (each) |

## 3. Aggregation Logic

**Function**: `runner._storage_level(grid, "battery")` (lines 343–360)

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

**Included node types for battery**: `house`, `battery`

**Aggregation**: `max()` — returns the highest SOC among all non-failed, non-isolated house and battery nodes.

## 4. Feature Index

| Feature | Index | Value Range | Normalization |
|---------|-------|-------------|---------------|
| Battery SOC | 73 | [0.0, 1.0] | Raw (no scaling) |

## 5. Normalization

- **Input**: Raw SOC fraction (0.0 = empty, 1.0 = full)
- **Processing**: None — passed directly to `build_extended_state()`
- **Network Input**: Fed as-is to first Linear layer (78→64)
- **Note**: No min-max scaling, no standardization applied

## 6. Final Tensor Value Flow

```
Initial state (seed 0, t=0):
  House batteries (13 nodes): battery_level = 1.0 each
  STORAGE_BAT: battery_level = 0.75
  _storage_level() → max(1.0, 1.0, ..., 0.75) = 1.0
  build_extended_state() → extended_state[73] = 1.0
  DQN input[73] = 1.0

After grid battery drain (e.g., STORAGE_BAT.battery_level = 0.55):
  House batteries: still 1.0 (unless action 1 dispatched)
  STORAGE_BAT: battery_level = 0.55
  _storage_level() → max(1.0, 1.0, ..., 0.55) = 1.0
  build_extended_state() → extended_state[73] = 1.0
  DQN input[73] = 1.0  ← UNCHANGED
```

## 7. Masking Evidence

**Stage 46.2 storage_state_trace.json** shows:

| Scenario | STORAGE_BAT SOC | Feature 73 (corrected) | Changed? |
|----------|-----------------|------------------------|----------|
| A, step 34 | 0.55 | 1.0 (before) → 1.0 (after) | ❌ No |
| A, step 4 | 0.55 | 1.0 (before) → 1.0 (after) | ❌ No |

**Conclusion**: The `max()` aggregation over house nodes (fixed at 1.0) **completely masks** the grid-scale battery SOC. The DQN cannot observe grid battery state changes.

## 8. Why This Exists

1. **Legacy design**: Original observation only read house nodes (`node_type == "house"`)
2. **Stage 46.2 fix**: Added `battery` node type to `_storage_level()` but kept `max()` aggregation
3. **House initialization**: All 13 houses start with `battery_level = 1.0` (full)
4. **No discharge mechanism for houses**: Houses only discharge when action 1 (`use_battery`) is selected by controller — the frozen policy never selects action 1 (pinned at action 4)

## 9. What It Hides

| Grid Battery State | Actual SOC | DQN Feature 73 | Observable? |
|-------------------|------------|----------------|-------------|
| Initial | 0.75 | 1.0 | ❌ |
| After EMS charge | 0.839 | 1.0 | ❌ |
| After action 1 drain | 0.747 | 1.0 | ❌ |
| Deep discharge | 0.55 | 1.0 | ❌ |
| Critical low | 0.20 | 1.0 | ❌ |
| Empty | 0.0 | 1.0 | ❌ |

**The DQN receives a constant 1.0 regardless of actual grid battery state.**

## 10. Physical vs Observed Disconnect

| Physical Reality | DQN Observation |
|------------------|-----------------|
| STORAGE_BAT: 150 MWh capacity | Feature 73 = 1.0 (constant) |
| SOC varies 0.75 → 0.55 → 0.20 | No change in feature |
| EMS charges battery (+0.089 SOC) | Invisible to DQN |
| Action 1 discharges battery (-0.00267 SOC) | Invisible to DQN |
| Battery provides 5.85 MW received power at night | DQN cannot correlate |

**Classification**: **PHYSICALLY ACTIVE / OBSERVATION DISCONNECTED**