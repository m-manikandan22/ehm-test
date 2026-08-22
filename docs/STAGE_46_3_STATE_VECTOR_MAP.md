# Stage 46.3 — Complete DQN State Vector Map

## 1. Overview

| Dimension | Description |
|-----------|-------------|
| Legacy state (indices 0–71) | 72 features from `SmartGrid.get_rl_state()` |
| Extended features (indices 72–77) | 6 features appended by `build_extended_state()` |
| **Total** | **78** (matches frozen checkpoint `state_dim=78`) |

Checkpoint: `backend/experiments/checkpoints/dqn_stage44.pt` (SHA-256: `eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493`)

---

## 2. Legacy State (Indices 0–71)

### 2.1 Per-Node Features (13 nodes × 5 = 65 features)

Node order (fixed in `get_rl_state` default `target_node_ids`):

| Block | Node ID | Node Type | Indices | Features |
|-------|---------|-----------|---------|----------|
| 0 | GEN_SOLAR | generator_solar | 0–4 | [voltage, freq/50, load, generation, stress] |
| 1 | GEN_WIND | generator_wind | 5–9 | [voltage, freq/50, load, generation, stress] |
| 2 | GEN_NUCLEAR | generator_nuclear | 10–14 | [voltage, freq/50, load, generation, stress] |
| 3 | GEN_COAL | generator_coal | 15–19 | [voltage, freq/50, load, generation, stress] |
| 4 | GEN_GAS | generator_gas | 20–24 | [voltage, freq/50, load, generation, stress] |
| 5 | S_MAIN | substation | 25–29 | [voltage, freq/50, load, generation, stress] |
| 6 | STORAGE_BAT | battery | 30–34 | [voltage, freq/50, load, generation, stress] |
| 7 | STORAGE_SC | supercap | 35–39 | [voltage, freq/50, load, generation, stress] |
| 8 | T_A | transformer | 40–44 | [voltage, freq/50, load, generation, stress] |
| 9 | T_B | transformer | 45–49 | [voltage, freq/50, load, generation, stress] |
| 10 | T_C | transformer | 50–54 | [voltage, freq/50, load, generation, stress] |
| 11 | HOSP | hospital | 55–59 | [voltage, freq/50, load, generation, stress] |
| 12 | IND0 | industry | 60–64 | [voltage, freq/50, load, generation, stress] |

**Per-node feature definitions (in order within each block):**

| Offset | Feature | Unit / Range | Normalization | Source |
|--------|---------|--------------|---------------|--------|
| 0 | voltage | p.u. [0.9, 1.1] | Raw (nominal=1.0) | `n.voltage` |
| 1 | frequency | p.u. [0.94, 1.04] | Divided by 50.0 | `n.frequency / 50.0` |
| 2 | load | MW [0, ~5] | Raw | `n.load` |
| 3 | generation | MW [0, ~15] | Raw | `n.generation` |
| 4 | stress_level | [0, 1] | Raw | `n.stress_level` |

### 2.2 Global Features (7 features, indices 65–71)

| Index | Feature | Unit / Range | Normalization | Source |
|-------|---------|--------------|---------------|--------|
| 65 | total_load | MW [0, ~100] | Raw | `sum(n.load for active nodes)` |
| 66 | total_gen | MW [0, ~100] | Raw | `sum(n.generation for active nodes)` |
| 67 | balance | MW [-100, +100] | Raw | `total_gen - total_load` |
| 68 | avg_voltage | p.u. [0.9, 1.1] | Raw | `mean(n.voltage for active nodes)` |
| 69 | avg_freq | p.u. [0.94, 1.04] | Divided by 50.0 | `mean(n.frequency for active nodes) / 50.0` |
| 70 | failed_count | integer [0, N] | Raw | `sum(1 for n if n.failed)` |
| 71 | isolated_count | integer [0, N] | Raw | `sum(1 for n if n.isolated and not n.failed)` |

---

## 3. Extended Features (Indices 72–77)

Added by `build_extended_state()` in `models/rl_agent.py:100–122`:

| Index | Feature | Unit / Range | Normalization | Source |
|-------|---------|--------------|---------------|--------|
| 72 | LSTM forecast (predicted_load) | MW [0, ~50] | Raw (sentinel=0.5 when disabled) | `DemandForecaster.predict()` on 10-step aggregate history |
| 73 | Battery SOC | Fraction [0, 1] | Raw | `_storage_level(grid, "battery")` = `max(battery_level over house + battery nodes)` |
| 74 | Supercapacitor SOC | Fraction [0, 1] | Raw | `_storage_level(grid, "supercap")` = `max(supercap_level over house + supercap nodes)` |
| 75 | Twin max risk | Fraction [0, 1] | Raw | `max(health_risk_score over twin registry)` |
| 76 | Twin mean risk | Fraction [0, 1] | Raw | `mean(health_risk_score over twin registry)` |
| 77 | Twin high fraction | Fraction [0, 1] | Raw | `fraction(risk ≥ 0.5 over twin registry)` |

---

## 4. Storage Feature Detail (Indices 73–74)

### Feature 73 — Battery SOC

**Source function**: `runner._storage_level(grid, "battery")` (line 343–360 in `runner.py`)

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

**Contributing nodes (seed 0, initial state):**
| Node ID | node_type | battery_level | Included? |
|---------|-----------|---------------|-----------|
| H0–H12 | house | 1.0 (all 13) | ✅ |
| STORAGE_BAT | battery | 0.75 | ✅ |
| Others | various | 0.0 or N/A | ❌ |

**Result**: `max(1.0, 1.0, ..., 0.75) = 1.0` → **Grid battery SOC (0.75) is MASKED**

### Feature 74 — Supercapacitor SOC

**Source function**: Same `_storage_level(grid, "supercap")`

**Contributing nodes (seed 0, initial state):**
| Node ID | node_type | supercap_level | Included? |
|---------|-----------|----------------|-----------|
| H0–H12 | house | 1.0 (all 13) | ✅ |
| STORAGE_SC | supercap | 1.0 | ✅ |
| Others | various | 0.0 or N/A | ❌ |

**Result**: `max(1.0, 1.0, ..., 1.0) = 1.0` → Grid supercap SOC (1.0) matches but **no headroom to observe drain**

---

## 5. Verification of Dimensions

| Check | Value |
|-------|-------|
| Legacy `get_rl_state()` length | 72 |
| `STATE_DIM` constant | 72 |
| `LSTM_FEATURE_DIM` | 1 |
| `STORAGE_FEATURE_DIM` | 2 |
| `TWIN_FEATURE_DIM` | 3 |
| `EXTENDED_STATE_DIM` | 78 |
| Checkpoint `state_dim` | 78 ✅ |
| Checkpoint `n_actions` | 5 ✅ |

---

## 6. Unknown / Uncertain Features

| Index | Feature | Status |
|-------|---------|--------|
| 0–4 | GEN_SOLAR block | VERIFIED |
| 5–9 | GEN_WIND block | VERIFIED |
| 10–14 | GEN_NUCLEAR block | VERIFIED |
| 15–19 | GEN_COAL block | VERIFIED |
| 20–24 | GEN_GAS block | VERIFIED |
| 25–29 | S_MAIN block | VERIFIED |
| 30–34 | STORAGE_BAT block | VERIFIED (but note: generation=0 always, load=small parasitic) |
| 35–39 | STORAGE_SC block | VERIFIED (generation=0 always) |
| 40–44 | T_A block | VERIFIED |
| 45–49 | T_B block | VERIFIED |
| 50–54 | T_C block | VERIFIED |
| 55–59 | HOSP block | VERIFIED |
| 60–64 | IND0 block | VERIFIED |
| 65–71 | Global features | VERIFIED |
| 72 | LSTM forecast | VERIFIED (repaired in Stage 46.1) |
| 73 | Battery SOC | VERIFIED (uses max over house+battery) |
| 74 | Supercap SOC | VERIFIED (uses max over house+supercap) |
| 75 | Twin max risk | VERIFIED |
| 76 | Twin mean risk | VERIFIED |
| 77 | Twin high fraction | VERIFIED |

**No UNKNOWN features remain — all 78 mapped to source code.**