# Stage 47.1 — Completion Report

## 1. Objective

Perform a controlled research-integrity and causal-validation audit (Stage 47.1) before any extended training is attempted. Establish whether changing ONLY Feature 73 (battery SOC) or ONLY Feature 74 (supercapacitor SOC) causally changes the trained DQN's Q-values, without any physical simulation side effects.

## 2. Stage-47 Findings Being Validated

Stage 47 repaired the storage observation representation:
- Feature 73 → STORAGE_BAT.battery_level (direct, not masked)
- Feature 74 → STORAGE_SC.supercap_level (direct, not masked)

Stage-47 policy sensitivity test (with physical grid perturbations) reported:
- Battery Q-range ≈ 5.67 (Action 1)
- Supercap Q-range ≈ 0.22 (Action 0)
- Both classified as "LEVEL 3" (incorrect terminology — was Level 2 Q-value sensitivity)
- No action flips observed (all states selected Action 4)

## 3. Stage-44 Provenance Audit

Git history inspected. The repository contains a single commit (`8a3b1d2`). The Stage-47 changes modified:
- `backend/experiments/runner.py` — `_storage_level()` function changed from aggregation over house+grid storage to direct grid-storage access
- `backend/simulation/grid.py` — reroute_energy hardening
- `backend/models/rl_agent.py` — reward decomposition
- `backend/simulation/scada.py` — SCADA dispatch for storage nodes
- `backend/simulation/node.py` — discharge signal persistence

The original Stage-44 behavior (max-aggregation over houses + grid storage) is preserved in Git history. No historical experiment files were silently overwritten.

## 4. Git / Source Changes Identified

Key change in `runner.py:_storage_level()`:

**Before (Stage-44, masked):**
```python
best = 0.0
for n in grid.nodes.values():
    if n.node_type in {"house", "battery"}:  # or "supercap"
        best = max(best, n.battery_level)
return best  # Returns max(13×1.0, grid_SOC) = 1.0 constant
```

**After (Stage-47, corrected):**
```python
if kind == "battery":
    node = grid.nodes.get("STORAGE_BAT")
    return node.battery_level if node and alive else 0.0
elif kind == "supercap":
    node = grid.nodes.get("STORAGE_SC")
    return node.supercap_level if node and alive else 0.0
```

## 5. Checkpoint Integrity

| Checkpoint | Expected SHA-256 | Actual SHA-256 | Status |
|------------|------------------|----------------|--------|
| `dqn_stage44.pt` | eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493 | eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493 | **PASS** |
| `dqn_stage47_storage_aware.pt` | 316b1a91028ee9143390bc4fba289ffc845a92b94f94ba55015ad52920d029d5 | 316b1a91028ee9143390bc4fba289ffc845a92b94f94ba55015ad52920d029d5 | **PASS** |

Both checkpoints remain byte-identical. Neither was modified during Stage 47.1.

## 6. Feature 73 Definition

**Feature 73 (index 73, 0-indexed):**
- Name: `battery_soc`
- Physical meaning: `STORAGE_BAT.battery_level` (grid-scale battery state of charge)
- Range: [0.0, 1.0]
- Level 1 (representation): **DEMONSTRATED** — by construction in corrected `_storage_level()`

## 7. Feature 74 Definition

**Feature 74 (index 74, 0-indexed):**
- Name: `supercap_soc`
- Physical meaning: `STORAGE_SC.supercap_level` (grid-scale supercapacitor state of charge)
- Range: [0.0, 1.0]
- Level 1 (representation): **DEMONSTRATED** — by construction in corrected `_storage_level()`

## 8. Pure-State Experimental Method

**Script:** `backend/experiments/stage47_1_pure_q_sensitivity.py`

**Method:**
1. Load Stage-47 DQN checkpoint (frozen, eval mode)
2. Construct one fixed baseline 78-dim state vector:
   - 72-dim legacy state from `SmartGrid.get_rl_state()` (seed=0, one-time)
   - Feature 72 (predicted_load) = 0.5
   - Feature 73 (battery_soc) = 0.50
   - Feature 74 (supercap_soc) = 0.50
   - Features 75-77 (twin risks) = 0.0
3. For each feature (73, 74), create test states where ONLY that feature changes:
   - SOC values tested: 0.90, 0.80, 0.60, 0.50, 0.40, 0.20, 0.10, 0.05, 0.00
   - All other 77 elements identical to baseline
4. NO `update_power_flow()`, NO grid rebuild, NO physical simulation
5. For each test state: forward pass → record 5 Q-values, argmax action
6. Verify state isolation: exactly one index changed (or zero when test=baseline)

**Numerical tolerances (defined BEFORE experiment):**
- State isolation tolerance: `1e-10`
- Q-value sensitivity tolerance: `1e-6`

## 9. State-Isolation Verification

| Test | Feature | Test Values | Isolation Checks | Result |
|------|---------|-------------|------------------|--------|
| Battery | 73 | 9 values | 9/9 PASS | **PASS** |
| Supercap | 74 | 9 values | 9/9 PASS | **PASS** |

All perturbations changed ONLY the intended feature index. When test value = baseline (0.50), zero indices changed (correct).

## 10. Battery Q-Value Sensitivity (Feature 73)

| SOC Range | Max Q-Range | Max ‖ΔQ‖₂ | Max |ΔQ| | Level 2 |
|-----------|-------------|-----------|-----------|---------|
| 0.00 → 0.90 | **5.6731** (Action 1) | 6.906 | 3.152 | **PASS** |

- Q-range per action: [5.518, 5.673, 5.518, 5.618, 5.465]
- Q-range > 1e-6 tolerance: **YES**
- Classification: **Level 2 Q-value sensitivity DEMONSTRATED**

## 11. Supercapacitor Q-Value Sensitivity (Feature 74)

| SOC Range | Max Q-Range | Max ‖ΔQ‖₂ | Max |ΔQ| | Level 2 |
|-----------|-------------|-----------|-----------|---------|
| 0.00 → 0.90 | **0.2231** (Action 0) | 0.269 | 0.124 | **PASS** |

- Q-range per action: [0.223, 0.214, 0.213, 0.222, 0.209]
- Q-range > 1e-6 tolerance: **YES**
- Classification: **Level 2 Q-value sensitivity DEMONSTRATED**

## 12. Action Sensitivity (Level 3)

| Feature | Actions Observed | Action Flips | Level 3 |
|---------|------------------|--------------|---------|
| Battery (73) | {4} only | NO | **NOT DEMONSTRATED** |
| Supercap (74) | {4} only | NO | **NOT DEMONSTRATED** |

All 18 controlled states (9 battery + 9 supercap) selected Action 4 (reroute_energy). No action flip occurred.

## 13. Comparison With Stage 47

| Metric | Stage-47 (Physical Perturbation) | Stage-47.1 (Pure State Isolation) |
|--------|----------------------------------|-----------------------------------|
| Battery Q-range | ~5.6732 (Action 1) | **5.6731** (Action 1) |
| Supercap Q-range | ~0.2231 (Action 0) | **0.2231** (Action 0) |
| Battery classification | "LEVEL 3" (incorrect) | **Level 2** (correct) |
| Supercap classification | "LEVEL 3" (incorrect) | **Level 2** (correct) |
| Action flips | NO | NO |
| Side effects | Possible (power-flow recomputation) | **NONE (verified)** |

The pure state-isolation test reproduces the Stage-47 Q-range magnitudes almost exactly, confirming that the earlier sensitivity was primarily driven by the storage features themselves, not by correlated physical-state changes. However, the terminology is corrected: **Level 2 = Q-value sensitivity**, **Level 3 = action sensitivity**.

## 14. Limitations

1. **Only 20 training episodes** (Stage-47) — likely insufficient for policy to fully exploit storage observability
2. **No action flips in evaluation** — policy still pinned at reroute (Action 4)
3. **Supercap sensitivity ~25× weaker** than battery — may need voltage-dip scenarios
4. **Single baseline state** — results may vary with different legacy state contexts
5. **No physical outcome comparison** — requires Stage 48 for ENS/served load metrics

## 15. Scientific Conclusion

**The Stage-47 storage observation repair is causally validated at the representation and Q-value levels.**

- Feature 73 (battery SOC) and Feature 74 (supercapacitor SOC) independently affect DQN Q-values when perturbed in isolation, with no physical simulation side effects.
- Battery Q-range: 5.67 (strong), Supercap Q-range: 0.22 (weak but significant).
- Both exceed the pre-defined numerical tolerance (1e-6) for Level 2 Q-value sensitivity.

**However, no corresponding action flip was observed; therefore Level 3 action sensitivity remains unproven.**

The DQN has learned to modulate Q-values based on storage SOC, but the current policy (20 episodes) still selects Action 4 (reroute_energy) for all tested states. This is a valid scientific result — not a failure of the experiment.

## 16. Recommendation for Stage 48

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