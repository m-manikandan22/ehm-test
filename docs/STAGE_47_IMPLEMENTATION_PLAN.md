# Stage 47 — Storage Observation Repair Implementation Plan

## 1. Objective

Repair the DQN state representation so that features 73 (battery SOC) and 74 (supercapacitor SOC) explicitly observe grid-scale storage state (STORAGE_BAT, STORAGE_SC) instead of being masked by house storage SOC.

## 2. Stage-46.3 Evidence Summary

| Finding | Evidence |
|---------|----------|
| Feature 73 = max(house_battery_SOC, STORAGE_BAT_SOC) | `runner._storage_level()` uses `max()` over node_type in {"house", "battery"} |
| Feature 74 = max(house_supercap_SOC, STORAGE_SC_SOC) | `runner._storage_level()` uses `max()` over node_type in {"house", "supercap"} |
| All 13 houses initialize at SOC=1.0 | `GridNode.__init__` sets `battery_level=1.0`, `supercap_level=1.0` |
| Grid battery SOC masked: max(1.0, 0.75) = 1.0 | Stage-46.3 controlled experiments |
| Grid supercap SOC masked: max(1.0, 1.0) = 1.0 | Stage-46.3 controlled experiments |
| ||ΔQ||₂ = 0.0 for grid storage perturbations | Stage-46.3 Q-value sensitivity tests |
| LSTM/Twin features DO change Q-values | Stage-46.3 feature isolation tests (||ΔQ||₂ = 4.69, 9.68) |

## 3. Current State Representation (BROKEN)

### Files with the masking bug:

| File | Function | Lines | Issue |
|------|----------|-------|-------|
| `backend/experiments/runner.py` | `_storage_level()` | 343-360 | `max()` over house + grid storage |
| `backend/experiments/stage44_dqn_training.py` | `_highest_storage_soc()` | 96-112 | Same masking logic |
| `backend/experiments/stage44_dqn_training.py` | `_soc()` alias | 146-148 | Delegates to `_highest_storage_soc()` |
| `backend/experiments/stage44_validation.py` | Inline in `_run_controller_on_scenario` | 574-591 | Same `max()` over house + grid storage |

### Current logic (runner.py:343-360):
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

## 4. Proposed Corrected Representation

### Design Principle

Feature 73 and 74 should directly observe grid-scale storage ONLY:
- Feature 73 = `grid.nodes["STORAGE_BAT"].battery_level`
- Feature 74 = `grid.nodes["STORAGE_SC"].supercap_level`

House storage SOC should NOT contribute to these features.

### Rationale

1. **Grid-scale storage is the controllable asset** — the DQN actions 1 (use_battery) and 2 (use_supercapacitor) dispatch to grid storage
2. **House storage is not directly controllable** — houses have their own autonomous charge/discharge logic
3. **State dimension preserved** — still 78 features (72 legacy + 6 extended)
4. **Checkpoint compatibility** — same `EXTENDED_STATE_DIM = 78`, same feature indices (73, 74)

## 5. State Dimension Impact

| Dimension | Current | Proposed | Change |
|-----------|---------|----------|--------|
| STATE_DIM (legacy) | 72 | 72 | None |
| LSTM_FEATURE_DIM | 1 | 1 | None |
| STORAGE_FEATURE_DIM | 2 | 2 | None (semantics change only) |
| TWIN_FEATURE_DIM | 3 | 3 | None |
| **EXTENDED_STATE_DIM** | **78** | **78** | **None** |

**No architecture change needed** — the DQNetwork input layer remains 78→64.

## 6. Architecture Impact

| Component | Impact | Action |
|-----------|--------|--------|
| DQNetwork | None | Same 78→64→64→5 architecture |
| DQNAgent | None | Same interface |
| `build_extended_state()` | None | Same signature, feature 73/74 now mean grid storage |
| Action masking (`_valid_actions_mask`) | None | Checks `battery_level`/`supercap_level` on alive nodes — already works |
| Reward function | None | Uses `supercap_level_pre/post` from grid state — already works |
| Training loop | Minor | Must use corrected `_highest_storage_soc()` |
| Validation loop | Minor | Must use corrected storage SOC computation |

## 7. Training Impact

### Must retrain because:
- Feature semantics change (73/74 now represent different physical quantities)
- The frozen Stage-44 checkpoint was trained on masked observations
- Policy weights encode the old (broken) observation semantics

### Training configuration:
- **New checkpoint**: `dqn_stage47_storage_aware.pt` (NEVER overwrite `dqn_stage44.pt`)
- **Same hyperparameters**: LR=1e-3, GAMMA=0.95, BATCH_SIZE=32, etc.
- **Same network architecture**: 78→64→64→5
- **Same reward function**: No changes to reward design
- **Same action space**: 5 actions
- **New random seed**: To distinguish from Stage-44 training

## 8. Checkpoint Strategy

| Checkpoint | Purpose | Protected |
|------------|---------|-----------|
| `dqn_stage44.pt` | Frozen baseline (SHA-256: `eb7bbed...`) | YES — never modify |
| `dqn_stage47_storage_aware.pt` | New trained model | New file |

## 9. Validation Strategy

### Phase 1: State Repair Verification (before training)
- Unit tests: `test_stage47_storage_state.py`
- Controlled observation audit: `stage47_storage_observation_audit.py`
- Verify feature 73/74 track grid storage, not house storage

### Phase 2: Frozen Comparison
- Run Stage-44 DQN vs new observation representation on same states
- Document state/Q-value/action differences

### Phase 3: Training
- Train new DQN with corrected observation
- Log: reward, action distribution, storage SOC, storage action frequency

### Phase 4: Policy Sensitivity
- Controlled state perturbations (battery 0.9→0.1, supercap 0.9→0.1)
- Measure Q-value sensitivity (LEVEL 2) and action sensitivity (LEVEL 3)

### Phase 5: Physical Outcome
- Compare Stage-44 vs Stage-47 on served load, ENS, restoration
- Test hybrid storage scenarios

## 10. Failure Conditions

STOP immediately if:
1. Stage-44 checkpoint SHA-256 changes
2. State dimension != 78
3. Corrected `_storage_level` cannot be constructed reliably
4. Training fails to initialize
5. New checkpoint cannot be saved
6. Features 73/74 still constant after repair
6. Hard-coded storage action logic detected

## 11. Reproducibility Strategy

Record for every experiment:
- Python, PyTorch, NumPy versions
- All seeds (master, torch, numpy, environment)
- Checkpoint SHA-256
- Git SHA
- Timestamp
- Training configuration (hyperparameters, episodes, steps)

## 12. Files Expected to Change

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/experiments/runner.py` | Bug fix | `_storage_level()` → read only grid storage nodes |
| `backend/experiments/stage44_dqn_training.py` | Bug fix | `_highest_storage_soc()` → read only grid storage nodes |
| `backend/experiments/stage44_validation.py` | Bug fix | Inline storage SOC computation → read only grid storage nodes |
| `backend/experiments/stage47_training.py` | New file | Stage-47 training pipeline |
| `backend/experiments/stage47_storage_observation_audit.py` | New file | Observation verification |
| `backend/experiments/stage47_policy_sensitivity.py` | New file | Policy sensitivity tests |
| `backend/tests/test_stage47_storage_state.py` | New file | Unit tests |
| `backend/tests/test_stage47_storage_aware.py` | New file | Integration tests |
| `docs/STAGE_47_STATE_REPAIR_SPEC.md` | New doc | Exact before/after spec |
| `docs/STAGE_47_OBSERVATION_AUDIT.md` | New doc | Observation audit results |
| `docs/STAGE_47_TRAINING_REPORT.md` | New doc | Training log |
| `docs/STAGE_47_POLICY_SENSITIVITY.md` | New doc | Policy sensitivity results |
| `docs/STAGE_47_COMPLETION_REPORT.md` | New doc | Final report |

## 13. Files Explicitly Protected

| File | Reason |
|------|--------|
| `backend/experiments/checkpoints/dqn_stage44.pt` | Historical frozen baseline |
| `backend/models/rl_agent.py` | DQN architecture — no changes needed |
| `backend/simulation/grid.py` | Grid physics — no changes needed |
| `backend/simulation/node.py` | Node definitions — no changes needed |

## 14. Success Criteria

| Criterion | Verification |
|-----------|--------------|
| Feature 73 = STORAGE_BAT.battery_level | Unit test: grid battery 0.8 → feat73=0.8; house SOC=1.0 doesn't mask |
| Feature 74 = STORAGE_SC.supercap_level | Unit test: grid supercap 0.8 → feat74=0.8; house SOC=1.0 doesn't mask |
| State dimension = 78 | Checkpoint `state_dim` = 78 |
| Stage-44 checkpoint unchanged | SHA-256 = `eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493` |
| New checkpoint created | `dqn_stage47_storage_aware.pt` exists |
| Battery Q-value sensitivity | ||ΔQ||₂ > 0.001 for grid battery perturbation |
| Supercap Q-value sensitivity | ||ΔQ||₂ > 0.001 for grid supercap perturbation |
| All tests pass | `pytest backend/tests/test_stage47_*.py -v` → 100% pass |

## 15. Recommended Next Stage (Stage 48)

After Stage 47 completes:
- If storage Q-value sensitivity demonstrated → Stage 48: Large-scale validation (100 seeds)
- If hybrid storage behavior demonstrated → Stage 48: Ablation study (storage vs no-storage)
- If policy still degenerate → Stage 48: Reward function repair (Repair R3 from Stage-44 plan)