# Stage 46.3 — DQN Storage Observation Audit Implementation Plan

## 1. Current Architecture

The frozen Stage-44 DQN checkpoint (`dqn_stage44.pt`, SHA-256: `eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493`) uses an **extended 78-dimensional state vector**:

- **Indices 0–71**: Legacy 72-dim grid state from `SmartGrid.get_rl_state()`
  - 13 priority nodes × 5 features (voltage, frequency/50, load, generation, stress)
  - 7 global features (total_load, total_gen, balance, avg_voltage, avg_freq/50, failed_count, isolated_count)
- **Index 72**: LSTM forecast (predicted next-step aggregate load)
- **Index 73**: Battery SOC (max over house + battery nodes)
- **Index 74**: Supercapacitor SOC (max over house + supercap nodes)
- **Indices 75–77**: Digital Twin risk (max, mean, high-fraction)

The DQN network: 2-hidden-layer MLP (78→64→64→5), trained with Huber loss, ε-greedy exploration.

## 2. Current DQN Observation Structure

| Feature | Source | Node Types Included | Aggregation |
|---------|--------|---------------------|-------------|
| 72 | `DemandForecaster.predict()` on 10-step history | — | — |
| 73 | `runner._storage_level(grid, "battery")` | `house`, `battery` | `max()` |
| 74 | `runner._storage_level(grid, "supercap")` | `house`, `supercap` | `max()` |
| 75 | `_twin_risk_map()` | registered transformers | `max()` |
| 76 | `_twin_risk_map()` | registered transformers | `mean()` |
| 77 | `_twin_risk_map()` | registered transformers | `fraction(risk ≥ 0.5)` |

## 3. Storage Observation Problem

**Core Issue**: The `_storage_level()` function uses `max()` across **both house nodes and grid-scale storage nodes**:

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

**Consequence**: All 13 house nodes initialize with `battery_level=1.0` and `supercap_level=1.0`. Grid storage nodes:
- `STORAGE_BAT` (node_type="battery"): capacity=150 MWh, initial SOC=0.75
- `STORAGE_SC` (node_type="supercap"): capacity=15 MWh, initial SOC=1.0

Since `max(1.0, 0.75) = 1.0` and `max(1.0, 1.0) = 1.0`, the DQN **never sees the grid storage SOC**. Even after grid storage drains to 0.55, the feature remains 1.0.

## 4. Audit Methodology

### 4.1 State Vector Mapping
- Enumerate all 78 features with exact source, node types, units, normalization
- Document in `STATE_VECTOR_MAP.md`

### 4.2 Observation Path Tracing
- Trace battery SOC: `STORAGE_BAT.battery_level` → `_storage_level()` → feature 73 → DQN tensor
- Trace supercap SOC: `STORAGE_SC.supercap_level` → `_storage_level()` → feature 74 → DQN tensor
- Document in `BATTERY_OBSERVATION_TRACE.md` and `SUPERCAP_OBSERVATION_TRACE.md`

### 4.3 Max() Masking Verification
- Explicitly test whether `max(house_SOC, grid_SOC)` masks grid storage
- Document WHY it exists (legacy house-only observation) and WHAT it hides

### 4.4 Controlled-State Experiments
**Battery Experiment**:
- STATE A: house battery SOC = 1.0, grid battery SOC = 0.80
- STATE B: house battery SOC = 1.0, grid battery SOC = 0.20
- All other variables identical
- Measure: feature 73, full state vector, Δstate

**Supercap Experiment**:
- STATE A: house supercap SOC = 1.0, grid supercap SOC = 0.80
- STATE B: house supercap SOC = 1.0, grid supercap SOC = 0.20
- All other variables identical
- Measure: feature 74, full state vector, Δstate

### 4.5 Q-Value Sensitivity Tests
- Use FROZEN checkpoint (no retraining)
- Compute Q-values for STATE A vs STATE B
- Record Q0–Q4, ΔQ, ||ΔQ||₂
- Define numerical tolerance (e.g., 1e-4) before interpreting

### 4.6 Action Sensitivity Tests
- Record argmax action for each state
- Compare battery-high vs battery-low, supercap-high vs supercap-low
- Multi-state matrix: 10 scenarios covering high/low SOC, renewable surplus/deficit, fault/no-fault

### 4.7 Feature Isolation Tests
- Change exactly ONE variable at a time: battery SOC, supercap SOC, LSTM forecast, Twin risk
- Record Δstate, ΔQ, Δargmax for each

### 4.8 EMS Observability Check
- Test EMS ON vs EMS OFF under identical state
- Record physical state difference vs DQN observation difference
- Classify as "PHYSICALLY ACTIVE / DQN-UNOBSERVED" if physical changes but DQN state unchanged

### 4.9 Checkpoint Integrity
- SHA-256 before and after all experiments
- Must remain byte-identical

### 4.10 Source Integrity
- Record modified files before execution
- Verify no production source files changed after
- Only new files: `docs/STAGE_46_3_*.md`, `experiments/results/stage46_3/*`, test files

## 5. Controlled-State Design

Create deterministic grid states by:
1. Building grid with fixed seed
2. Manually setting `battery_level` / `supercap_level` on specific nodes
3. Freezing all other variables (load, generation, fault state, LSTM history, twin registry)
4. Building extended state vector via `build_extended_state()`
5. Feeding to frozen DQN for Q-value extraction

## 6. Q-Value Experiment Design

```python
agent = DQNAgent.load_checkpoint(ckpt_path, state_dim=78, eval_mode=True)
state_A = build_extended_state(..., battery_soc=0.80, supercap_soc=1.0, ...)
state_B = build_extended_state(..., battery_soc=0.20, supercap_soc=1.0, ...)
q_A = agent.policy_net(torch.tensor(state_A).unsqueeze(0))
q_B = agent.policy_net(torch.tensor(state_B).unsqueeze(0))
delta_Q = q_B - q_A
```

## 7. Checkpoint Integrity

- Path: `backend/experiments/checkpoints/dqn_stage44.pt`
- SHA-256: `eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493`
- Verify before and after every experiment batch

## 8. Acceptance Criteria

- [ ] Complete state vector mapped (78 features documented)
- [ ] Storage feature indices verified (73=battery, 74=supercap)
- [ ] Battery observation path traced to source
- [ ] Supercapacitor observation path traced to source
- [ ] Grid battery SOC independently tested (controlled experiment)
- [ ] Grid supercapacitor SOC independently tested (controlled experiment)
- [ ] Q-value sensitivity measured with numerical tolerance
- [ ] Action sensitivity measured
- [ ] EMS observability measured
- [ ] Checkpoint unchanged (SHA-256 identical)
- [ ] No retraining occurred (no optimizer.step, no backward, no checkpoint save)
- [ ] No production architecture modified
- [ ] All audit artifacts produced
- [ ] Conclusions evidence-based

## 9. Non-Goals (Explicitly Out of Scope)

- ❌ Retraining the DQN
- ❌ Modifying DQN architecture
- ❌ Modifying neural network weights
- ❌ Modifying reward function
- ❌ Modifying optimizer/hyperparameters
- ❌ Modifying trained checkpoint
- ❌ Modifying training/validation scenarios
- ❌ Changing random seeds for desired behavior
- ❌ Manufacturing Q-value differences
- ❌ Forcing storage actions
- ❌ Changing action-selection logic
- ❌ Changing action mask
- ❌ Changing ENS/CMI/reliability metrics
- ❌ Changing physical simulator
- ❌ Changing EMS behavior
- ❌ Changing storage physics
- ❌ Running 100-seed experiment
- ❌ Performing final paper experiment
- ❌ Implementing the observation fix (document only)