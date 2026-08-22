# Stage 47 — Completion Report

## 1. Objective

Repair the DQN state representation so that features 73 (battery SOC) and 74 (supercapacitor SOC) explicitly observe grid-scale storage state (STORAGE_BAT, STORAGE_SC) instead of being masked by house storage SOC.

## 2. Stage-46.3 Problem Statement

Stage 46.3 proved:
- Feature 73 = `max(house_battery_SOC, STORAGE_BAT_SOC)` = 1.0 constant
- Feature 74 = `max(house_supercap_SOC, STORAGE_SC_SOC)` = 1.0 constant
- All 13 houses initialize at SOC=1.0, masking grid storage
- ||Delta Q||_2 = 0.0 for grid storage perturbations
- Both storage features classified as **LEVEL 1** (represented but constant)

## 3. Exact Root Cause

The `_storage_level()` function in `runner.py`, `stage44_dqn_training.py`, and `stage44_validation.py` used `max()` aggregation over ALL storage nodes (houses + grid storage), causing house SOC=1.0 to mask actual grid storage SOC.

## 4. State Representation Before Repair

```python
# OLD (masked)
def _storage_level(grid, kind):
    best = 0.0
    for n in grid.nodes.values():
        if n.node_type in {"house", "battery"} (or "supercap"):
            best = max(best, n.battery_level)
    return best  # Returns max(13x1.0, grid_SOC) = 1.0
```

**Feature 73:** `max(house_battery, STORAGE_BAT)` = 1.0 (constant)
**Feature 74:** `max(house_supercap, STORAGE_SC)` = 1.0 (constant)

## 5. State Representation After Repair

```python
# NEW (corrected)
def _storage_level(grid, kind):
    if kind == "battery":
        node = grid.nodes.get("STORAGE_BAT")
        return node.battery_level if node and alive else 0.0
    elif kind == "supercap":
        node = grid.nodes.get("STORAGE_SC")
        return node.supercap_level if node and alive else 0.0
```

**Feature 73:** `STORAGE_BAT.battery_level` (direct, range [0.0, 1.0])
**Feature 74:** `STORAGE_SC.supercap_level` (direct, range [0.0, 1.0])

## 6. State Dimension

| Dimension | Value | Changed? |
|-----------|-------|----------|
| STATE_DIM | 72 | No |
| LSTM_FEATURE_DIM | 1 | No |
| STORAGE_FEATURE_DIM | 2 | No (semantics only) |
| TWIN_FEATURE_DIM | 3 | No |
| **EXTENDED_STATE_DIM** | **78** | **No** |

## 7. DQN Architecture

- **Network:** 2-hidden-layer MLP (78 -> 64 -> 64 -> 5)
- **Actions:** 5 discrete (gen, battery, supercap, shift, reroute)
- **Optimizer:** Adam (LR=1e-3)
- **Loss:** Huber (SmoothL1)
- **Gamma:** 0.95
- **Batch Size:** 32
- **Replay Buffer:** 2000
- **Target Update:** Every 20 steps
- **Epsilon:** 1.0 -> 0.05 (exponential decay, 200 steps)

## 8. Training Configuration

- **Master Seed:** 42 (different from Stage-44 seed 0)
- **Episodes:** 20
- **Steps/Episode:** 80
- **Total Transitions:** 1,600
- **Training Scenarios:** 20 (mixed FAULT_AND_DEGRADED, SINGLE_FAULT, TOPOLOGY_FAULT, DEGRADED_ASSET, STORAGE_STRESS, NORMAL, HIGH_DEMAND, LOW_RENEWABLE)
- **LSTM:** Frozen forecaster (RNG-forked)
- **Reward:** Unchanged from Stage-44

## 9. New Checkpoint

- **Path:** `backend/experiments/checkpoints/dqn_stage47_storage_aware.pt`
- **SHA-256:** `316b1a91028ee9143390bc4fba289ffc845a92b94f94ba55015ad52920d029d5`
- **State Dim:** 78
- **Actions:** 5
- **Steps Done:** 1,600
- **Final Epsilon:** 0.0503
- **Extra:** `storage_observation: corrected_grid_only`

## 10. Old Checkpoint Protection

- **Stage-44 Path:** `backend/experiments/checkpoints/dqn_stage44.pt`
- **SHA-256:** `eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493`
- **Status:** **UNCHANGED** (verified before and after Stage 47)

## 11. Observation Sensitivity Results

### Battery SOC (Feature 73)
- Grid BAT varied 0.90 -> 0.00
- Feature 73: 0.900 -> 0.000 (exact match)
- House SOC at 1.0 does NOT mask (verified)
- **All 7 test values PASS**

### Supercapacitor SOC (Feature 74)
- Grid SC varied 0.90 -> 0.00
- Feature 74: 0.900 -> 0.000 (exact match)
- House SOC at 1.0 does NOT mask (verified)
- **All 7 test values PASS**

### Multi-State Verification
- 7 joint states tested
- **All 7 PASS**

### House SOC Independence
- 5 tests with varying house SOC
- **All 5 PASS** (house SOC never affects grid features)

## 12. Battery Q-Value Sensitivity

| Metric | Value |
|--------|-------|
| Max Q-range | 5.6732 (Action 1 - use_battery) |
| Q-range per 0.1 SOC | ~0.61 (linear) |
| Classification | **LEVEL 3** (Q-value sensitivity demonstrated) |

## 13. Supercapacitor Q-Value Sensitivity

| Metric | Value |
|--------|-------|
| Max Q-range | 0.2231 (Action 0 - increase_generation) |
| Q-range per 0.1 SOC | ~0.025 (linear) |
| Classification | **LEVEL 3** (Q-value sensitivity demonstrated) |

## 14. Action Sensitivity

| Test | Action Flips? |
|------|---------------|
| Battery SOC (9 states) | NO |
| Supercap SOC (9 states) | NO |
| Joint states (7 states) | NO |
| Feature isolation (4 features) | NO |

**All 25 controlled states select Action 4 (reroute_energy).**

## 15. Hybrid Storage Scenario Results

- **7 corner/center states tested**
- **All select Action 4**
- **No battery/supercap differentiation observed**
- Training action distribution shows some storage use (Actions 1, 2) but evaluation policy favors reroute

## 16. Physical Outcome Results

Not yet measured (requires Stage 48 validation with multi-seed experiments).

## 17. Stage-44 vs Stage-47 Comparison

| Aspect | Stage-44 (Frozen) | Stage-47 (New) |
|--------|-------------------|----------------|
| Battery observable | NO (masked) | YES (direct) |
| Supercap observable | NO (masked) | YES (direct) |
| Battery Q-range | 0.0 | 5.67 |
| Supercap Q-range | 0.0 | 0.22 |
| Observation repair | N/A | COMPLETE |
| Policy action (eval) | 4 (pinned) | 4 (pinned) |
| Storage actions in training | 0 | Yes (1, 2 used) |

## 18. Tests Executed

| Test File | Tests | Passed |
|-----------|-------|--------|
| `test_stage47_storage_state.py` | 19 | 19 |
| `stage47_storage_observation_audit.py` | N/A (audit) | All PASS |
| `stage47_frozen_comparison.py` | N/A (audit) | Verified |
| `stage47_policy_sensitivity.py` | N/A (audit) | Complete |
| `test_stage46_3_observation_audit.py` | 22 | 22 (regression) |

## 19. Limitations

1. **Only 20 training episodes** - likely insufficient for policy to fully exploit storage observability
2. **No action flips in evaluation** - policy still pinned at reroute (Action 4)
3. **Supercap sensitivity 25x weaker** than battery - may need voltage-dip scenarios
4. **No physical outcome comparison** - Stage 48 needed for ENS/served load metrics
5. **No ablation study** - storage vs no-storage not yet tested

## 20. What Has NOT Yet Been Proven

- [ ] Stage-47 statistically outperforms Stage-44 on ENS/served load
- [ ] DQN learns hybrid storage differentiation (battery vs supercap roles)
- [ ] Storage actions (1, 2) are selected appropriately in evaluation
- [ ] Action flips occur for storage SOC perturbations
- [ ] 100-seed statistical validation

## 21. Recommendation for Stage 48

**Stage 48: Controlled Retraining & Validation**

1. **Train longer:** 100+ episodes with corrected observation (seed 42)
2. **Add voltage-dip scenarios:** To trigger supercapacitor value proposition
3. **Physical outcome comparison:** Stage-44 vs Stage-47 on:
   - Energy Not Served (ENS)
   - Served Load
   - Restoration Time
   - Storage Utilization
4. **Ablation study:** 
   - Stage-47 full
   - Stage-47 no-battery (mask feature 73)
   - Stage-47 no-supercap (mask feature 74)
   - Stage-47 no-storage (mask both)
5. **Statistical validation:** 10-20 seeds per scenario

**Do NOT proceed to 100-seed paper experiment yet.**