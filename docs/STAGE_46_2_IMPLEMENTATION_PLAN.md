# Stage 46.2 — Implementation Plan: Physical Storage & EMS Integration Audit

## 1. Objective

Verify whether the advertised hybrid battery + supercapacitor architecture actually exists in the executable system, using the FROZEN Stage-44 checkpoint (SHA-256: `eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493`).

**Research objective pipeline:**
```
renewable generation
    ↓
hybrid battery + supercapacitor storage
    ↓
intelligent energy management
    ↓
DQN / smart-grid controller
    ↓
continuous consumer supply
```

## 2. Critical Finding from Stage 46.1

**Node-type mismatch discovered:**
| Node | Actual `node_type` | DQN Action Logic Targets | Effect |
|------|-------------------|-------------------------|--------|
| STORAGE_BAT | `"battery"` | `"storage_bat"` substring | **CRITICAL WIRING BUG** — action 1 never dispatches grid battery |
| STORAGE_SC | `"supercap"` | `"storage_sc"` substring | **CRITICAL WIRING BUG** — action 2 never dispatches grid supercap |

The DQN observation features (73, 74) read only `node_type == "house"` nodes, while EMS mutates `node_type == "battery"/"supercap"` nodes. This creates a **PHYSICALLY ACTIVE / OBSERVATION DISCONNECTED** architecture.

## 3. Implementation Plan — Repair Only Genuine Wiring Defects

### 3.1 Fix Node-Type Matching in Dispatch Logic (CRITICAL)

**Files to repair:**
- `backend/experiments/runner.py` — `_dispatch_action` (actions 1 & 2)
- `backend/experiments/runner.py` — `_storage_level` (DQN state features)
- `backend/experiments/stage44_dqn_training.py` — `_highest_storage_soc` (training SOC features)
- `backend/experiments/dqn_training.py` — `_soc` (legacy training SOC features)
- `backend/experiments/stage44_validation.py` — validation harness SOC features
- `backend/simulation/scada.py` — `_dispatch_control_signal` (SCADA dispatch)

**Rule:** Match on actual `node_type` values (`"battery"`, `"supercap"`) NOT substrings (`"storage_bat"`, `"storage_sc"`).

**Do NOT:** Rename nodes, change checkpoint, retrain DQN, modify reward.

### 3.2 Fix DQN Observation Features 73/74

**Current:** Features 73/74 = max SOC over `node_type == "house"` only
**Required:** Features 73/74 = max SOC over `node_type in ("house", "battery")` and `("house", "supercap")`

**Files:**
- `backend/experiments/runner.py` — `_storage_level`
- `backend/experiments/stage44_validation.py` — feature extraction
- `backend/experiments/stage45_validation.py` — feature extraction
- `backend/models/rl_agent.py` — `build_extended_state` documentation

### 3.3 Verify All Actions Have Physical Effect

Run deterministic probes for each action (0-4) measuring:
- Δ SOC (battery & supercap, both grid-scale and house)
- Δ generation (before/after step)
- Δ received power (consumer delivery)
- Δ ENS
- Δ voltage

### 3.4 EMS vs DQN Integration Classification

Measure EMS ON vs OFF on identical pre-EMS snapshots. Classify EMS as exactly one:
- A. Fully integrated into DQN decisions
- B. Physically integrated but not observed by DQN
- C. Independent environment-side controller
- D. Broken / disconnected

### 3.5 Energy Accounting & Voltage Feasibility

Document the actual accounting model (no fake conservation equations). Verify storage dispatch does not create invalid voltage states.

## 4. Deliverables

### Documentation (create in `docs/`)
- [ ] `STAGE_46_2_BATTERY_TRACE.md` — End-to-end battery trace
- [ ] `STAGE_46_2_SUPERCAP_TRACE.md` — End-to-end supercapacitor trace
- [ ] `STAGE_46_2_ACTION_AUDIT.md` — All 5 actions physical audit
- [ ] `STAGE_46_2_COMPLETION_REPORT.md` — Final verdict with evidence

### Results (create in `experiments/results/stage46_2/`)
- [ ] `action_physical_effects.json` — All 5 actions × 2 timepoints
- [ ] `storage_state_trace.json` — DQN observability of storage SOC
- [ ] `ems_comparison.json` — EMS ON vs OFF
- [ ] `energy_balance.json` — Accounting model
- [ ] `voltage_effects.json` — Voltage feasibility
- [ ] `checkpoint_hash.json` — SHA-256 before/after
- [ ] `manifest.json` — Provenance

### Tests
- [ ] `tests/test_stage46_2_storage_integration.py` — Verify repairs

## 5. Success Criteria (Completion Gate)

| Criterion | Status |
|-----------|--------|
| Battery action physically verified | ☐ |
| Supercapacitor action physically verified | ☐ |
| Action/node-type mapping correct | ☐ |
| Storage SOC physically valid [0,1] | ☐ |
| Load shifting conserves demand | ☐ |
| Generation action verified | ☐ |
| Rerouting functional | ☐ |
| EMS physical effect quantified | ☐ |
| DQN storage observability quantified | ☐ |
| Energy accounting documented | ☐ |
| Voltage feasibility documented | ☐ |
| Checkpoint unchanged | ☐ |
| No retraining | ☐ |
| No fabricated results | ☐ |

## 6. Prohibited Actions

- ❌ Retrain DQN
- ❌ Modify DQN architecture
- ❌ Modify reward function
- ❌ Change validation seeds
- ❌ Manufacture improvements
- ❌ Force battery/supercap actions to appear
- ❌ Alter metrics to make storage look useful
- ❌ Run 100 seeds
- ❌ Claim storage improves resilience without physical evidence
- ❌ Modify frozen checkpoint (`dqn_stage44.pt`)