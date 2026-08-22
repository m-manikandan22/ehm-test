# Stage 47 — State Representation Repair Specification

## 1. Exact Before/After Specification

### Feature 73: Battery SOC

| Aspect | OLD (Stage 44 / 46.3) | NEW (Stage 47) |
|--------|----------------------|----------------|
| **Source** | `runner._storage_level(grid, "battery")` | `grid.nodes["STORAGE_BAT"].battery_level` |
| **Aggregation** | `max()` over node_type in {"house", "battery"} | Direct read from single grid node |
| **Contributing nodes** | 13 houses + STORAGE_BAT | STORAGE_BAT only |
| **House SOC effect** | Masks grid SOC (max(1.0, x) = 1.0) | No effect |
| **Grid battery SOC range visible** | None (constant 1.0) | Full [0.0, 1.0] |
| **Initial value (seed 0)** | 1.0 | 0.75 |

### Feature 74: Supercapacitor SOC

| Aspect | OLD (Stage 44 / 46.3) | NEW (Stage 47) |
|--------|----------------------|----------------|
| **Source** | `runner._storage_level(grid, "supercap")` | `grid.nodes["STORAGE_SC"].supercap_level` |
| **Aggregation** | `max()` over node_type in {"house", "supercap"} | Direct read from single grid node |
| **Contributing nodes** | 13 houses + STORAGE_SC | STORAGE_SC only |
| **House SOC effect** | Masks grid SOC (max(1.0, x) = 1.0) | No effect |
| **Grid supercap SOC range visible** | None (constant 1.0) | Full [0.0, 1.0] |
| **Initial value (seed 0)** | 1.0 | 1.0 |

## 2. Complete State Vector Layout (78 dimensions)

### Indices 0–71: Legacy State (unchanged)
```
13 priority nodes × 5 features = 65 features
7 global features = 7 features
Total = 72 features
```

Priority nodes (from `SmartGrid.get_rl_state()`):
```
0:  GEN_SOLAR        5:  S_MAIN          10: T_C
1:  GEN_WIND         6:  STORAGE_BAT     11: HOSP
2:  GEN_NUCLEAR      7:  STORAGE_SC      12: IND0
3:  GEN_COAL         8:  T_A
4:  GEN_GAS          9:  T_B
```

Per-node features: [voltage, frequency/50, load, generation, stress_level]
Global features: [total_load, total_gen, balance, avg_voltage, avg_freq/50, failed_count, isolated_count]

### Indices 72–77: Extended Features

| Index | Feature | OLD Source | NEW Source |
|-------|---------|------------|------------|
| 72 | LSTM Forecast (predicted_load) | `DemandForecaster.predict()` | Unchanged |
| 73 | Battery SOC | `max(house_battery, STORAGE_BAT)` | `STORAGE_BAT.battery_level` |
| 74 | Supercap SOC | `max(house_supercap, STORAGE_SC)` | `STORAGE_SC.supercap_level` |
| 75 | Twin Max Risk | `max(health_risk_score)` | Unchanged |
| 76 | Twin Mean Risk | `mean(health_risk_score)` | Unchanged |
| 77 | Twin High Fraction | `fraction(risk >= 0.5)` | Unchanged |

## 3. Code Changes Required

### 3.1 `backend/experiments/runner.py` — `_storage_level()` function

**OLD (lines 343-360):**
```python
def _storage_level(grid, kind: str) -> float:
    """Highest SOC fraction of the named storage type across the grid
    (battery or supercap). Used to feed the DQN's decision state."""
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

**NEW:**
```python
def _storage_level(grid, kind: str) -> float:
    """Grid-scale storage SOC for the DQN decision state.
    
    Reads ONLY the dedicated grid storage node (STORAGE_BAT or STORAGE_SC),
    NOT house storage. House storage is autonomous and not directly
    controllable by the DQN.
    """
    if kind == "battery":
        node = grid.nodes.get("STORAGE_BAT")
        if node is not None and not getattr(node, "failed", False) and not getattr(node, "isolated", False):
            return float(getattr(node, "battery_level", 0.0) or 0.0)
        return 0.0
    elif kind == "supercap":
        node = grid.nodes.get("STORAGE_SC")
        if node is not None and not getattr(node, "failed", False) and not getattr(node, "isolated", False):
            return float(getattr(node, "supercap_level", 0.0) or 0.0)
        return 0.0
    return 0.0
```

### 3.2 `backend/experiments/stage44_dqn_training.py` — `_highest_storage_soc()` function

**OLD (lines 96-112):**
```python
def _highest_storage_soc(grid, kind: str) -> float:
    """Return the highest SOC of the named storage across the grid."""
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

**NEW:**
```python
def _highest_storage_soc(grid, kind: str) -> float:
    """Grid-scale storage SOC for the DQN decision state.
    
    Reads ONLY the dedicated grid storage node (STORAGE_BAT or STORAGE_SC),
    NOT house storage. House storage is autonomous and not directly
    controllable by the DQN.
    """
    if kind == "battery":
        node = grid.nodes.get("STORAGE_BAT")
        if node is not None and not getattr(node, "failed", False) and not getattr(node, "isolated", False):
            return float(getattr(node, "battery_level", 0.0) or 0.0)
        return 0.0
    elif kind == "supercap":
        node = grid.nodes.get("STORAGE_SC")
        if node is not None and not getattr(node, "failed", False) and not getattr(node, "isolated", False):
            return float(getattr(node, "supercap_level", 0.0) or 0.0)
        return 0.0
    return 0.0
```

### 3.3 `backend/experiments/stage44_validation.py` — Inline storage SOC computation

**OLD (lines 574-591):**
```python
battery_soc = 0.0
supercap_soc = 0.0
for nid, n in grid.nodes.items():
    ntype = str(getattr(n, "node_type", ""))
    if ntype == "house" or ntype == "battery":
        try:
            battery_soc = max(
                battery_soc,
                float(getattr(n, "battery_level", 0.0) or 0.0),
            )
        except Exception:
            pass
    if ntype == "house" or ntype == "supercap":
        try:
            supercap_soc = max(
                supercap_soc,
                float(getattr(n, "supercap_level", 0.0) or 0.0),
            )
        except Exception:
            pass
```

**NEW:**
```python
battery_soc = 0.0
supercap_soc = 0.0
# Grid-scale battery (STORAGE_BAT)
bat_node = grid.nodes.get("STORAGE_BAT")
if bat_node is not None and not getattr(bat_node, "failed", False) and not getattr(bat_node, "isolated", False):
    battery_soc = float(getattr(bat_node, "battery_level", 0.0) or 0.0)

# Grid-scale supercapacitor (STORAGE_SC)
sc_node = grid.nodes.get("STORAGE_SC")
if sc_node is not None and not getattr(sc_node, "failed", False) and not getattr(sc_node, "isolated", False):
    supercap_soc = float(getattr(sc_node, "supercap_level", 0.0) or 0.0)
```

## 4. Verification Tests

### Test 1: Grid Battery SOC Changes Feature 73
```python
grid = SmartGrid(seed=0)
grid.nodes["STORAGE_BAT"].battery_level = 0.80
feat73 = _storage_level(grid, "battery")
assert feat73 == 0.80
```

### Test 2: House Battery SOC Does NOT Change Feature 73
```python
grid = SmartGrid(seed=0)
grid.nodes["STORAGE_BAT"].battery_level = 0.50
for n in grid.nodes.values():
    if n.node_type == "house":
        n.battery_level = 1.0
feat73 = _storage_level(grid, "battery")
assert feat73 == 0.50  # Not 1.0!
```

### Test 3: Grid Supercap SOC Changes Feature 74
```python
grid = SmartGrid(seed=0)
grid.nodes["STORAGE_SC"].supercap_level = 0.80
feat74 = _storage_level(grid, "supercap")
assert feat74 == 0.80
```

### Test 4: House Supercap SOC Does NOT Change Feature 74
```python
grid = SmartGrid(seed=0)
grid.nodes["STORAGE_SC"].supercap_level = 0.50
for n in grid.nodes.values():
    if n.node_type == "house":
        n.supercap_level = 1.0
feat74 = _storage_level(grid, "supercap")
assert feat74 == 0.50  # Not 1.0!
```

### Test 5: Specific Values
```python
# Battery
for soc in [0.8, 0.6, 0.4, 0.2, 0.1, 0.05, 0.0]:
    grid = SmartGrid(seed=0)
    grid.nodes["STORAGE_BAT"].battery_level = soc
    assert _storage_level(grid, "battery") == soc

# Supercap
for soc in [0.8, 0.6, 0.4, 0.2, 0.1, 0.05, 0.0]:
    grid = SmartGrid(seed=0)
    grid.nodes["STORAGE_SC"].supercap_level = soc
    assert _storage_level(grid, "supercap") == soc
```

### Test 6: State Dimension
```python
from models.rl_agent import EXTENDED_STATE_DIM
assert EXTENDED_STATE_DIM == 78
```

### Test 7: Failed/Isolated Handling
```python
grid = SmartGrid(seed=0)
grid.nodes["STORAGE_BAT"].failed = True
assert _storage_level(grid, "battery") == 0.0

grid = SmartGrid(seed=0)
grid.nodes["STORAGE_BAT"].isolated = True
assert _storage_level(grid, "battery") == 0.0
```

## 5. What MUST NOT Change

| Component | Must Remain |
|-----------|-------------|
| `STATE_DIM` | 72 |
| `LSTM_FEATURE_DIM` | 1 |
| `STORAGE_FEATURE_DIM` | 2 |
| `TWIN_FEATURE_DIM` | 3 |
| `EXTENDED_STATE_DIM` | 78 |
| `N_ACTIONS` | 5 |
| `DQNetwork` architecture | 78→64→64→5 |
| `build_extended_state()` signature | Same 6 appended features |
| Action space | 5 actions (0-4) |
| Reward function | Unchanged |
| Stage-44 checkpoint | Byte-identical |

## 6. Implementation Checklist

- [ ] Fix `runner._storage_level()`
- [ ] Fix `stage44_dqn_training._highest_storage_soc()`
- [ ] Fix `stage44_validation.py` inline storage SOC computation
- [ ] Create `test_stage47_storage_state.py` unit tests
- [ ] Run unit tests → verify all pass
- [ ] Create `stage47_storage_observation_audit.py` — controlled experiments
- [ ] Run observation audit → verify features track grid storage
- [ ] Create `stage47_training.py` — new training pipeline
- [ ] Train new DQN → `dqn_stage47_storage_aware.pt`
- [ ] Create `stage47_policy_sensitivity.py` — policy tests
- [ ] Run policy sensitivity → document Q-value/action sensitivity
- [ ] Create all documentation files
- [ ] Run full test suite → verify no regressions