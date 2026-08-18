# Stage 42 — Implementation Plan

## 1. Current Architecture

The EHM project implements a self-healing smart-grid framework with:

- **49-node EHM grid** (`backend/simulation/grid.py`): 5 generators, 3 feeders (residential, hospital, industrial), poles, transformers, house nodes, grid-scale battery + supercapacitor
- **DQN controller** (`backend/models/rl_agent.py`): 5-action space (increase_generation, use_battery, use_supercapacitor, shift_load, reroute_energy) with action-mask heuristic
- **Rule-based controller**: 2-action reactive (deficit→battery, else→generation)
- **LSTM forecaster** (`backend/models/lstm_model.py`): 2-layer LSTM, 10-step input window, synthetic training data
- **Digital twin** (`backend/digital_twin/twin.py`): Arrhenius-style health degradation, `health_risk_score ∈ [0,1]`
- **EMS** (`backend/simulation/ems.py`): Energy management with PyPSA integration
- **FLISR 9-stage** (`backend/simulation/grid.py::flisr_9stage`): Fault detection→isolation→restoration
- **Hybrid storage**: Battery (long-duration) + Supercapacitor (fast-transient)
- **Topology planner** (`backend/planning/ai_planner.py`): Resilience-aware network reconfiguration
- **N-1 analysis** (`backend/reliability/n_minus_one.py`)
- **Power flow** (`backend/simulation/power_flow.py`): DC power flow with KCL validation

## 2. Current Experimental Architecture

- **Runner**: `backend/experiments/runner.py` (`run_single`) — the main harness
- **Pipeline**: `backend/experiments/stage26_pipeline.py` — batch orchestration, statistics, tables
- **Config**: `backend/experiments/experiment_config.py` — ablation flag definitions
- **Scenarios**: `backend/experiments/scenario.py` — deterministic fault injection
- **Scenario Matrix**: `backend/experiments/scenario_matrix.py` — A-J scenario definitions
- **Ablation**: `backend/experiments/ablation.py` — ablation study driver
- **Metrics**: `backend/experiments/research_metrics.py` — metric collection

### Stage-42 Partial Wiring (Already Implemented)

The runner.py already has:
1. **LSTM integration** (lines 338-456): `_lstm_history` deque, `_lstm_forecaster` construction, LSTM prediction call with no-future-leakage, fallback to 0.5
2. **Digital twin integration** (lines 327-337, 417-422): `_twin_registry` construction, `_tick_twin_registry` per step, `_twin_risk_map` computation
3. **Predictive healing** (lines 427-435): `_predictive_preparation` advisory calls
4. **EMS dispatch** (lines 490-494): `_run_ems` after grid.step()
5. **Health-aware action bias** (lines 174-208): `_health_aware_bias` in `_select_action`
6. **Scenario matrix decoding** (lines 272-296): Demand/renewable multipliers, battery SOC override, health override

## 3. Missing Information-Flow Connections

Based on Stage-41 audit and current code inspection:

| Component | Status | Gap |
|-----------|--------|-----|
| LSTM → controller | **Wired** | LSTM forecast reaches `_select_action` via `predicted_load` parameter |
| Digital twin → controller | **Wired** | `risk_map` reaches `_select_action`; health-aware bias forces action 3 when risk≥0.5 |
| Predictive healing | **Wired (advisory only)** | Records preparation events; does not mutate grid |
| EMS | **Wired** | `_run_ems` called after grid.step() when `enable_ems=True` |
| Battery dispatch | **Wired** | Action 1 dispatches battery; action 2 dispatches supercap |
| Action distribution | **Wired** | `action_counts` dict recorded per step |
| Scenario matrix | **Wired** | A-J scenarios encoded in label, decoded by runner |

### Remaining Gaps to Verify

1. **LSTM forecast actually changes decisions**: Need to verify that predicted_load ≠ 0.5 reaches the DQN and changes action selection
2. **Digital twin health changes decisions**: Need to verify that health_risk_score ≥ 0.5 actually triggers action 3 in practice
3. **EMS changes dispatch**: Need to verify EMS runs and affects grid state
4. **Scenario multipliers work**: Need to verify demand/renewable multipliers actually scale loads
5. **Battery SOC override works**: Need to verify battery_level is set correctly
6. **Action masking is isolated from learning**: DQN is in eval_mode(); action mask is hand-coded

## 4. Required Changes

### 4.1 Verification Changes (No Algorithm Modification)

These are diagnostic/test changes only:

1. **Add integration tests** proving information flows end-to-end
2. **Run 10-seed validation** across all scenario classes × all controllers
3. **Verify ablation flags change runtime paths** by checking action_counts differ
4. **Verify time advancement equality** across controllers

### 4.2 Test Additions

Required tests (from Stage-42 spec):
- `test_lstm_reaches_controller`
- `test_lstm_no_future_leakage`
- `test_twin_health_changes_decision`
- `test_predictive_healing_changes_preparation`
- `test_ems_changes_dispatch`
- `test_battery_limits`
- `test_supercapacitor_limits`
- `test_hybrid_dispatch`
- `test_ablation_flags_change_runtime_path`
- `test_all_controllers_advance_clock_equally`
- `test_seed_reproducibility`
- `test_paired_scenarios_identical`
- `test_topology_changes_n1_result`
- `test_all_actions_have_effect_or_are_explicitly_invalid`

## 5. Files Affected

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/experiments/runner.py` | Verify | Already has Stage-42 wiring; verify end-to-end |
| `backend/experiments/info_flow.py` | Verify | Already has helper functions; verify correctness |
| `backend/experiments/scenario_matrix.py` | Verify | Already has A-J; verify multipliers work |
| `backend/experiments/research_metrics.py` | Verify | Already has hooks; verify summary includes new fields |
| `backend/experiments/stage26_pipeline.py` | Verify | Already has ablation support; verify pipeline works |
| `tests/test_stage42_integration.py` | **Create** | New integration tests |
| `tests/test_scenario_matrix.py` | **Create** | Scenario matrix validation |
| `tests/test_information_flow.py` | **Create** | End-to-end information flow tests |
| `docs/STAGE_42_COMPLETION_REPORT.md` | **Create** | Stage-42 completion report |

## 6. Tests Required

### 6.1 Information Flow Tests
- LSTM output reaches controller (predicted_load ≠ 0.5 when enable_lstm=True)
- LSTM uses only past data (no future leakage)
- Digital twin risk score reaches action selection
- Health-aware bias triggers action 3 when risk ≥ 0.5
- EMS runs when enable_ems=True
- Action counts differ between ablation rows

### 6.2 Scenario Matrix Tests
- Demand multiplier scales loads correctly
- Renewable multiplier scales generation correctly
- Battery SOC override sets battery_level
- Health override sets twin health
- Simultaneous faults share same timestep
- Scenario encoding/decoding round-trips correctly

### 6.3 Reproducibility Tests
- Same seed → identical grid
- Same seed → identical scenario
- Same seed → identical results for same controller
- Different seeds → different results

### 6.4 Fairness Tests
- All controllers advance clock equally (same n_steps)
- All controllers see same grid for same seed
- All controllers see same fault schedule

## 7. Validation Experiments

### 7.1 10-Seed Diagnostic Run

```
10 seeds × {A,B,C,D,E,F,G,H,I,J} × {random, rule_based, dqn_core_only, full_stack}
= 10 × 10 × 4 = 400 runs
```

Metrics to collect:
- ENS, CMI, restoration_rate, critical_load_interruption_steps
- action_counts per controller
- predictive_preparation_events per controller
- ems_cycles per controller
- lstm_forecast_samples per controller

### 7.2 Ablation Validation

```
10 seeds × Scenario A × {full_stack, no_lstm, no_twin, no_predictive, no_reward, dqn_core_only}
= 10 × 6 = 60 runs
```

Verify: action_counts or ENS differ between rows (proving flags work).

## 8. Risks

| Risk | Mitigation |
|------|------------|
| LSTM forecaster returns constant | Check predicted_load varies across timesteps |
| Digital twin never reaches high risk | Check Scenario H specifically |
| EMS has no effect | Check ems_cycles > 0 in metric summary |
| Scenario multipliers don't work | Check node.load changes after construction |
| Action masking still dominates | This is acceptable; document it |

## 9. Rollback Strategy

All changes are additive (new tests, new docs). No existing algorithms are modified. If the 10-seed diagnostic reveals:
- Modules don't help → report honestly as negative results
- Modules help under specific scenarios → report as conditional contributions
- Something breaks → revert test files only; no algorithm changes

The existing Stage-26 results remain the baseline reference.

## 10. Success Criteria

1. All existing tests pass
2. New integration tests pass
3. 10-seed diagnostic completes without crashes
4. Ablation rows show different action_counts (proving flags work)
5. Scenario multipliers produce measurable grid state changes
6. LSTM predictions vary across timesteps
7. Digital twin risk scores are non-zero for Scenario H
8. Documentation is complete and honest
