# Stage 46.3 — Q-Value Audit Report

## 1. Experimental Setup

**Checkpoint**: `dqn_stage44.pt` (SHA-256: `eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493`)
- State dim: 78
- Actions: 5
- Mode: `eval_mode()` (greedy, ε=0, no training)
- Network: 2-hidden-layer MLP (78→64→64→5)

**Numerical Tolerance**: ΔQ < 1e-4 considered noise; ||ΔQ||₂ < 1e-3 considered no sensitivity.

---

## 2. Battery SOC Q-Value Sensitivity

### 2.1 Controlled States
| State | Grid Battery SOC | House Battery SOC | Feature 73 |
|-------|------------------|-------------------|------------|
| HIGH  | 0.80             | 1.0               | 1.0        |
| LOW   | 0.20             | 1.0               | 1.0        |

### 2.2 Q-Values
| Action | Name | Q_HIGH | Q_LOW | ΔQ |
|--------|------|--------|-------|-----|
| 0 | increase_generation | -717.8724 | -717.8724 | 0.0 |
| 1 | use_battery | -713.0222 | -713.0222 | 0.0 |
| 2 | use_supercapacitor | -719.8715 | -719.8715 | 0.0 |
| 3 | shift_load | -719.5282 | -719.5282 | 0.0 |
| 4 | reroute_energy | -707.7952 | -707.7952 | 0.0 |

### 2.3 Metrics
- **||ΔQ||₂**: 0.000000
- **Max |ΔQ|**: 0.0
- **Relative change**: 0.0% for all actions
- **Action (argmax)**: 4 → 4 (no change)

**Conclusion**: **NO Q-VALUE SENSITIVITY** to grid battery SOC when house batteries mask at 1.0.

---

## 3. Supercapacitor SOC Q-Value Sensitivity

### 3.1 Controlled States
| State | Grid Supercap SOC | House Supercap SOC | Feature 74 |
|-------|-------------------|--------------------|------------|
| HIGH  | 0.80              | 1.0                | 1.0        |
| LOW   | 0.20              | 1.0                | 1.0        |

### 3.2 Q-Values
| Action | Name | Q_HIGH | Q_LOW | ΔQ |
|--------|------|--------|-------|-----|
| 0 | increase_generation | -717.8724 | -717.8724 | 0.0 |
| 1 | use_battery | -713.0222 | -713.0222 | 0.0 |
| 2 | use_supercapacitor | -719.8715 | -719.8715 | 0.0 |
| 3 | shift_load | -719.5282 | -719.5282 | 0.0 |
| 4 | reroute_energy | -707.7952 | -707.7952 | 0.0 |

### 3.3 Metrics
- **||ΔQ||₂**: 0.000000
- **Max |ΔQ|**: 0.0
- **Relative change**: 0.0% for all actions
- **Action (argmax)**: 4 → 4 (no change)

**Conclusion**: **NO Q-VALUE SENSITIVITY** to grid supercapacitor SOC when house supercaps mask at 1.0.

---

## 4. Multi-State Action Sensitivity Matrix

| State Name | Grid Bat SOC | Grid SC SOC | Feat 73 | Feat 74 | Action | Q[4] (reroute) |
|------------|--------------|-------------|---------|---------|--------|----------------|
| high_bat_high_sc | 0.80 | 0.80 | 1.0 | 1.0 | 4 | -707.80 |
| low_bat_high_sc | 0.20 | 0.80 | 1.0 | 1.0 | 4 | -707.80 |
| high_bat_low_sc | 0.80 | 0.20 | 1.0 | 1.0 | 4 | -707.80 |
| low_bat_low_sc | 0.20 | 0.20 | 1.0 | 1.0 | 4 | -707.80 |
| mid_bat_mid_sc | 0.50 | 0.50 | 1.0 | 1.0 | 4 | -707.80 |
| empty_bat_full_sc | 0.00 | 1.00 | 1.0 | 1.0 | 4 | -707.80 |
| full_bat_empty_sc | 1.00 | 0.00 | 1.0 | 1.0 | 4 | -707.80 |

**All 7 states**: Identical Q-vectors, identical action (4).

---

## 5. Feature Isolation Tests (Single Variable Changes)

| Feature Changed | Base → Test | ΔState Norm | ΔQ Norm | Action Changed? |
|-----------------|-------------|-------------|---------|-----------------|
| Battery SOC (73) | 0.50 → 0.10 | 0.000000 | 0.000000 | No |
| Supercap SOC (74) | 0.50 → 0.10 | 0.000000 | 0.000000 | No |
| LSTM Forecast (72) | 0.5 → 0.9 | 0.400000 | 4.689407 | No |
| Twin Max Risk (75) | 0.0 → 0.8 | 0.800000 | 9.677267 | No |

### Key Findings:
1. **Storage features (73, 74)**: Zero ΔState, zero ΔQ — completely masked
2. **LSTM (72)**: Changes state and Q-values (||ΔQ||₂=4.69) but **no action flip**
3. **Twin (75)**: Changes state and Q-values (||ΔQ||₂=9.68) but **no action flip**
4. **Policy pinned at action 4** across all tested states

---

## 6. EMS Observability Q-Value Impact

### 6.1 Physical vs DQN Observation
| Metric | Before EMS | After EMS | Change |
|--------|-----------|-----------|--------|
| STORAGE_BAT SOC | 0.75 | 0.839 | +0.089 |
| Feature 73 | 1.0 | 1.0 | 0.0 (masked) |
| Full state ||Δ|| | — | — | 0.956 |
| ||ΔQ||₂ | — | — | 15.466 |
| Action | 4 | 4 | No |

### 6.2 Interpretation
- **Physical effect real**: Battery charged by EMS (+0.089 SOC, +0.552 MW gen)
- **Storage feature blind**: Feature 73 unchanged (masked by houses)
- **Q-values shift**: ||ΔQ||₂=15.47 due to *other* state changes from `update_power_flow()` (voltage, load, generation redistribution)
- **Action unchanged**: Still action 4

**Classification**: Storage features = PHYSICALLY ACTIVE / DQN-UNOBSERVED; Full state = OBSERVED (via physics side-effects)

---

## 7. Q-Value Sensitivity Classification (5-Level Evidence Chain)

| Feature | L1 Feature | L2 State Δ | L3 Q Δ | L4 Action Δ | L5 Physical Δ | Level |
|---------|------------|------------|--------|-------------|---------------|-------|
| Battery SOC (73) | ✓ | ✗ (0.0) | ✗ (0.0) | ✗ | ✗ | **LEVEL 1** |
| Supercap SOC (74) | ✓ | ✗ (0.0) | ✗ (0.0) | ✗ | ✗ | **LEVEL 1** |
| LSTM Forecast (72) | ✓ | ✓ (0.4) | ✓ (4.69) | ✗ | ✗ | **LEVEL 3** |
| Twin Max Risk (75) | ✓ | ✓ (0.8) | ✓ (9.68) | ✗ | ✗ | **LEVEL 3** |
| Twin Mean Risk (76) | ✓ | (not tested) | — | — | — | UNKNOWN |
| Twin High Frac (77) | ✓ | (not tested) | — | — | — | UNKNOWN |

**Level Definitions:**
- LEVEL 0: Not represented in state vector
- LEVEL 1: Represented but constant (masked)
- LEVEL 2: Changes state vector
- LEVEL 3: Changes Q-values
- LEVEL 4: Changes selected action
- LEVEL 5: Changes physical outcome

---

## 8. Comparison with Stage 46.1 Findings

| Channel | Stage 46.1 L3 (||ΔQ||₂) | Stage 46.3 L3 (||ΔQ||₂) | Consistent? |
|---------|------------------------|------------------------|-------------|
| LSTM | 1.31–1.67 | 4.69 | Yes (same direction) |
| Twin | 0.0 / 6.38 (scenario H) | 9.68 | Yes (stronger in controlled test) |
| Storage (Battery) | ~4.6 per feature pair | 0.0 | **DIFFERENT** — Stage 46.1 varied house SOC; Stage 46.3 varies grid SOC with houses fixed at 1.0 |
| Storage (Supercap) | ~4.6 per feature pair | 0.0 | **DIFFERENT** — same reason |

**Critical Insight**: Stage 46.1 sensitivity came from *house* storage SOC variation. Stage 46.3 proves *grid* storage SOC is invisible when houses are at max SOC.

---

## 9. Numerical Noise Floor

The frozen DQN produces Q-values with magnitude ~700. The observed ΔQ for storage features is **exactly 0.0** (not just small — mathematically identical tensors), confirming the features are truly constant, not merely below a noise threshold.

---

## 10. Summary

| Question | Answer |
|----------|--------|
| Does changing grid battery SOC change Q-values? | **NO** (||ΔQ||₂ = 0.0) |
| Does changing grid supercap SOC change Q-values? | **NO** (||ΔQ||₂ = 0.0) |
| Does changing grid battery SOC change action? | **NO** (action 4 → 4) |
| Does changing grid supercap SOC change action? | **NO** (action 4 → 4) |
| Does LSTM forecast change Q-values? | **YES** (||ΔQ||₂ = 4.69) |
| Does Twin risk change Q-values? | **YES** (||ΔQ||₂ = 9.68) |
| Does EMS change storage observation? | **NO** (features 73/74 constant) |
| Does EMS change Q-values via other physics? | **YES** (||ΔQ||₂ = 15.47) |

**Root Cause**: `max(house_SOC=1.0, grid_SOC)` = 1.0 constant for both battery and supercapacitor.