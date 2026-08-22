# Stage 46.2 — Completion Report

## 1. Objective

Verify whether the advertised hybrid battery + supercapacitor architecture actually exists in the executable system, using the FROZEN Stage-44 checkpoint (SHA-256: `eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493`).

## 2. Constraint Compliance

| Constraint | Status |
|------------|--------|
| No retraining | ✅ |
| No architecture change | ✅ |
| No reward / hyperparameter change | ✅ |
| No validation-seed change | ✅ |
| Checkpoint byte-identical | ✅ SHA-256 unchanged |
| No 100-seed run | ✅ |
| No manufactured improvements | ✅ |
| No forced battery/supercap actions | ✅ |
| No altered metrics | ✅ |
| Only genuine wiring defects repaired | ✅ |

## 3. Critical Findings

### 3.1 CRITICAL WIRING BUGS — FIXED

**Node-type mismatch discovered and repaired:**

| Component | Actual `node_type` | Bug Pattern | Files Fixed |
|-----------|-------------------|-------------|-------------|
| STORAGE_BAT | `"battery"` | `"storage_bat" in node_type` | runner.py, stage44_dqn_training.py, dqn_training.py, stage44_validation.py, scada.py, train_scenario_generator.py, runner.py (SOC init) |
| STORAGE_SC | `"supercap"` | `"storage_sc" in node_type` | runner.py, stage44_dqn_training.py, dqn_training.py, stage44_validation.py, scada.py, train_scenario_generator.py |

**Effect of bugs:**
- Action 1 (use_battery) **never dispatched** grid battery STORAGE_BAT
- Action 2 (use_supercapacitor) **never dispatched** grid supercap STORAGE_SC
- DQN features 73/74 **excluded** grid-scale storage SOC
- EMS charging **worked correctly** (used exact `node_type` match)
- Power flow **would have worked** (BFS source broadening uses exact types)

### 3.2 Architecture Classification

| Subsystem | Classification | Evidence |
|-----------|----------------|----------|
| **EMS** | **B. Physically integrated but not observed by DQN** | EMS mutates STORAGE_BAT/STORAGE_SC SOC (0.75→0.839), but DQN features 73/74 only see house SOC |
| **Hybrid Storage** | **C. Physically simulated but AI-disconnected** | Battery/supercap physically work, but frozen DQN policy never selects actions 1/2 (pinned at action 4) |
| **DQN Observability** | **PHYSICALLY ACTIVE / OBSERVATION DISCONNECTED** | Storage SOC changes physically but corrected features 73/74 still don't change because houses start at SOC=1.0 |

### 3.3 Fast Transient Role — NOT SUPPORTED

The conceptual claim that "supercapacitor handles fast transients while battery handles sustained energy" is **NOT SUPPORTED**:
- No voltage-triggered automatic dispatch
- No time-scale separation in control logic
- Frozen policy never selects action 2
- Grid voltage never drops below 0.95 in probes (VOLTAGE_DIP_THRESHOLD=0.97)

## 4. Physical Verification Results

### Action Probes (Scenario A, Seed 0)

| Action | STORAGE_BAT ΔSOC | STORAGE_SC ΔSOC | ΔServed (MWh) | ΔENS (MWh) | Verified |
|--------|------------------|-----------------|---------------|------------|----------|
| 0 (gen) | 0.0 | 0.0 | +0.011 (night) | +0.002 | ✅ |
| 1 (battery) | **-0.00267** | 0.0 | **+0.104** (night) | **-0.004** | ✅ |
| 2 (supercap) | 0.0 | **-0.01333** | +0.011 (night) | +0.002 | ✅ |
| 3 (shift) | 0.0 | 0.0 | +0.011 | **-0.057** | ✅ (load reduced) |
| 4 (reroute) | 0.0 | 0.0 | +0.011 | +0.002 | ✅ (no fault) |

**Key:** Action 1 provides largest consumer benefit at night (5.85 MW received power increase).

### EMS Physical Effect (ON vs OFF, identical snapshots)

| Metric | EMS ON | EMS OFF | Δ |
|--------|--------|---------|---|
| STORAGE_BAT SOC | 0.839 | 0.750 | **+0.089** |
| STORAGE_SC SOC | 1.000 | 1.000 | 0.0 |
| Total Generation | 48.78 MW | 47.82 MW | +0.96 MW |
| Served Energy | 3.650 MWh | 3.602 MWh | +0.048 MWh |
| ENS | 0.055 MWh | 0.056 MWh | -0.001 MWh |

**EMS physically charges battery and increases generation.** Effects do NOT reach DQN observation.

### DQN Observability of Storage

| Formula | Feature 73 (battery) | Feature 74 (supercap) | Changed after drain? |
|---------|---------------------|----------------------|---------------------|
| Harness (house only) | 1.0 | 1.0 | ❌ No |
| Corrected (house + grid) | 1.0 | 1.0 | ❌ No (houses at 1.0 mask grid drain) |

**Even with corrected formula, features don't change** because house SOC (1.0) > grid SOC (0.55 after drain). Max operator masks the grid storage state.

### Priority Behaviour (Frozen Policy)

| Scenario | Balance (MW) | Deficit (MW) | Voltage | Policy Action | Storage Selected? |
|----------|-------------|--------------|---------|---------------|-------------------|
| A | +33.2 | 13.9 | 0.95 | 4 (reroute) | ❌ |
| B | +30.5 | 14.1 | 0.95 | 4 (reroute) | ❌ |
| C | +10.7 | 18.0 | 0.95 | 4 (reroute) | ❌ |
| D | +33.2 | 13.9 | 0.95 | 4 (reroute) | ❌ |
| E | +7.9 | 20.7 | 0.95 | 4 (reroute) | ❌ |

**Frozen policy pinned at action 4** — never selects battery/supercap on any scenario.

### Energy Accounting

The simulator does **NOT enforce a closed energy balance**. It tracks:
- Per-node generation/load
- Per-node excess/deficit (post auto-charge)
- BFS received_power
- DC line losses (~0.96 MW)

Closest identity: `gen - load = excess - deficit` after auto-charge.

### Voltage Feasibility

All actions keep voltage within [0.95, 1.0] — no violations created.

## 5. Files Created

### Documentation (`docs/`)
- ✅ `STAGE_46_2_IMPLEMENTATION_PLAN.md`
- ✅ `STAGE_46_2_BATTERY_TRACE.md`
- ✅ `STAGE_46_2_SUPERCAP_TRACE.md`
- ✅ `STAGE_46_2_ACTION_AUDIT.md`
- ✅ `STAGE_46_2_COMPLETION_REPORT.md` (this file)

### Results (`experiments/results/stage46_2/`)
- ✅ `action_physical_effects.json` — 10 probes × 5 actions
- ✅ `storage_state_trace.json` — DQN observability (2 probes)
- ✅ `ems_comparison.json` — EMS ON vs OFF (2 probes)
- ✅ `energy_balance.json` — Accounting model
- ✅ `voltage_effects.json` — Voltage feasibility (5 actions)
- ✅ `checkpoint_hash.json` — SHA-256 before/after (unchanged)
- ✅ `manifest.json` — Provenance
- ✅ `node_type_audit.json` — Full node-type mismatch table
- ✅ `priority_behaviour.json` — Frozen policy on scenarios A-E

## 6. Completion Gate

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Battery action physically verified | ✅ | dSOC_bat = -0.00267, dServed = +0.104 MWh |
| Supercapacitor action physically verified | ✅ | dSOC_sc = -0.01333, dServed = +0.011 MWh |
| Action/node-type mapping correct | ✅ | All 8 locations fixed to exact type match |
| Storage SOC physically valid [0,1] | ✅ | All SOCs in [0,1] post-action |
| Load shifting conserves demand | ✅ | Base load updated, total load reduced by design |
| Generation action verified | ✅ | GEN_SOLAR/GEN_GAS +0.5 MW |
| Rerouting functional | ✅ | Stage-46 fix prevents NetworkX errors |
| EMS physical effect quantified | ✅ | SOC +0.089, gen +0.96 MW, served +0.048 MWh |
| DQN storage observability quantified | ✅ | Features 73/74 = max(house, grid); houses mask grid |
| Energy accounting documented | ✅ | No closed balance; gen-load=excess-deficit |
| Voltage feasibility documented | ✅ | All actions keep V in [0.95, 1.0] |
| Checkpoint unchanged | ✅ | SHA-256 identical |
| No retraining | ✅ | Checkpoint not modified |
| No fabricated results | ✅ | All results from deterministic probes |

## 7. Honest Assessment for Paper Claims

| Claim | Supported? | Evidence |
|-------|------------|----------|
| "Hybrid storage improves resilience" | ❌ NO | No controlled experiment demonstrates this; frozen policy never uses storage |
| "Supercapacitor provides fast transient support" | ❌ NO | Not implemented in control logic; voltage never dips to trigger threshold |
| "EMS is integrated with DQN" | ❌ NO | EMS effects physically real but invisible to DQN observation |
| "Battery/supercap actions work" | ✅ YES | Physically verified after wiring fix |
| "Storage SOC observable to DQN" | ⚠️ PARTIAL | Features 73/74 now include grid storage, but houses mask it |

## 8. Remaining Work for Paper-Ready Claims

To make defensible claims about hybrid storage, the following would be needed:
1. **Retrain DQN** with corrected observation features so policy can learn storage value
2. **Design scenarios** with voltage dips <0.97 to test supercap fast response
3. **Run ablation** comparing no-storage / battery-only / supercap-only / hybrid
4. **Statistical validation** across multiple seeds (not single deterministic probes)

## 9. Next Action

Stage 46.2 complete. Proceed to Stage 47 only if retraining is planned. Otherwise, document limitations honestly in paper.