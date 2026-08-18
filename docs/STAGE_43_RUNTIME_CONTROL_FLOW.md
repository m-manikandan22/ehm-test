# STAGE 43 — Runtime Control Flow Map

Every arrow below corresponds to an actual call in the code (file:line). Anything described in `main.md` that has no arrow here is **not implemented** and is a Stage-43 repair target.

Legend: [code path] · (gated by flag) · ✗ = dead/not-implemented path (repair target)

---

## 1. Experiment harness — one `run_single` (runner.py:236)

```
main.md spec
   │
   ▼
run_experiment(configs, seeds, ticks, weather_modes)          runner.py:611
   │
   ├── make_scenario(seed, total_steps, fault_count, weather)  runner.py:647
   │      └── Scenario(seed, faults[])                         experiments/scenario.py
   │
   ├── set_global_seed(effective_seed)                         runner.py:264   [seeds.py]
   │      └── python/random.seed + numpy.random.seed + torch.manual_seed  ← RNG repair 1
   │
   ├── _build_grid(effective_seed)                             runner.py:265
   │      └── SmartGrid()                                      simulation/grid.py
   │
   ├── rng = make_rng(effective_seed)                          runner.py:266   [controller stream today]
   │
   ├── _build_twin_registry(grid)        (enable_twin|enable_predictive_healing)  runner.py:331
   │      └── TwinRegistry.register(grid)                      info_flow.py:99 / twin_registry.py:37
   │
   ├── _lstm_forecaster = DemandForecaster()  (enable_lstm)    runner.py:346
   │      └── pretrain on synthetic data                       lstm_model.py:184
   │
   ├── agent = DQNAgent(); agent.eval_mode()  (enable_dqn)     runner.py:366-369
   │      └── random-initialised network, empty buffer         models/rl_agent.py
   │      ← REPAIR 4: train on training env → checkpoint → load + frozen eval
   │
   └── for step in range(total_steps):                         runner.py:379
```

## 2. One timestep (runner.py:379–561)

```
fault injection: grid.inject_failure(f.target)          runner.py:383
        │
        ▼
grid.update_power_flow()                                 runner.py:406 → grid.py:589
        │        └── DC-PF + BFS _simulate_energy_flow   grid.py:850 (thermal trips grid.py:651)
        │        └── resets isolated=False; failed → voltage 0 + edge deactivate
        ▼
LSTM history: (agg_load, agg_gen, weather) deque       runner.py:412 → info_flow._aggregate_grid_load_and_gen:37
        │
        ▼
twin tick: registry.sync(grid, dt_hours=1.0)            runner.py:420 → info_flow:113 → twin_registry.py:94
        │        └── DigitalTwin.tick(physical_state)   twin.py:141
        ▼
predictive healer: _predictive_preparation(grid, risk_map)   runner.py:429 → info_flow:160
        │        ✗ advisory only — records event, NEVER mutates grid  ← REPAIR 7
        ▼
LSTM forecast: predicted_load = forecaster.predict(seq) runner.py:446 → lstm_model.py:240
        │        ✗ value reaches only the reasoning string  ← REPAIR 5
        ▼
risk map: {asset_id: health_risk_score}                 runner.py:459 → info_flow:135
        │        ✗ consumed by rule_based/random only (runner.py:174-207); never by DQN mask  ← REPAIR 6
        ▼
action = _select_action(config, grid, rng, agent, predicted_load, risk_map)   runner.py:467
        │   ├── DQN: state=grid.get_rl_state()          runner.py:179 → grid.py:1872 (72-dim)
        │   │        ├── select_action(state, predicted_load, grid_state)   rl_agent.py:301
        │   │        │      └── mask heuristics (balance/spike/failed)       rl_agent.py:319-332
        │   │        │            ✗ health_aware_load_shift key never read   ← REPAIR 6
        │   │        │      └── eval draws one global random.random()       ← REPAIR 1
        │   │        └── return {"action_id", "reasoning"} (action ids 0-4)
        │   ├── rule_based: 1 if any deficit else 0      runner.py:199-208
        │   ├── random: uniform 0-4 (rng.integers)       runner.py:193-198
        │   └── persistence: always 0                    runner.py:191-192
        ▼
_dispatch_action(grid, action)                           runner.py:476 → runner.py:110
        │   ├── 0 increase_generation → node "G0"        runner.py:120  ✗ G0 does not exist  ← REPAIR 3
        │   ├── 1 use_battery → house nodes              runner.py:124-128
        │   ├── 2 use_supercapacitor → house nodes       runner.py:129-133
        │   ├── 3 shift_load → house nodes               runner.py:134-137
        │   └── 4 reroute_energy → pass                  runner.py:138-140  ✗ dead  ← REPAIR 3
        ▼
grid.step()                                              runner.py:484 → grid.py:558
        │   └── update_generation()                      grid.py:563
        │         └── _apply_time_curves()               grid.py:691
        │               └── recomputes house load/gen, wind, nuclear, solar, coal
        │                     from _base_* × curves + noise   ← wipes actions 1-3 (REPAIR 3)
        │               └── scenario demand/renew multipliers NOT in curve path  ← REPAIR 2
        │         └── node.step() for non-failed nodes   grid.py:573 → node.py:246
        │               └── failed/isolated: load=gen=0 (frozen)   ← REPAIR 10 (ENS would-be load)
        ▼
_run_ems(grid)  (enable_ems)                             runner.py:492 → info_flow:194
        │   └── EnergyManagementSystem(use_pypsa=False)  ✗ new instance EVERY call  ← REPAIR 8
        │         └── ems.run(grid)                      ems.py:107
        │               ├── charge_storage (excess)      ems.py:168
        │               ├── priority_energy_allocation   ems.py:251
        │               └── peer_sharing                 ems.py:359
        ▼
FLISR (enable_flisr, step % 4 == 0, step > 0)            runner.py:497
        │   └── grid.flisr_9stage()                      grid.py:1488
        │         └── segment isolation + switch toggling + reconnection
        ▼
grid.update_power_flow()  (settle)                       runner.py:508
        ▼
collector.record_step(grid, timestep, controller_action) runner.py:511 → research_metrics.py:98
        │   └── ENS: load * (1/60) per node incl. failed/isolated frozen loads  :136-138
        │         ✗ frozen load ≠ would-be load          ← REPAIR 10
        │   └── voltage/frequency/stress aggregates, fault events, restoration
        ▼
validity = check_run_validity(grid)                      runner.py:563
        ▼
result dict {config, scenario, validity, metrics, seeds, fingerprints…}  runner.py:595
        └── REPAIR 1: record master/env/controller/training seeds + Git SHA
        └── REPAIR 11: record grid_hash/demand_hash/renewable_hash/fault_hash
```

## 3. Module-level data flow (who reads what)

```
grid.get_rl_state()  (72-dim: 13 nodes × 5 + 7 globals)   grid.py:1872
   consumed by: DQN select_action (runner.py:179)          ✓
   NOT containing: LSTM forecast, twin health risk         ← REPAIR 5+6

DemandForecaster.predict(seq)                              lstm_model.py:240
   input: 10× [load, gen, weather] from _lstm_history      (history ≤ t — no leakage ✓)
   output: predicted_load → reasoning string only          ← REPAIR 5

TwinRegistry.sync → health_risk_score                       twin.py:93, twin_registry.py:94
   consumed by: _select_action rule_based/random branch    ✓ (runner.py:174-207)
   consumed by: DQN mask?                                  ✗ (dead key)  ← REPAIR 6
   consumed by: predictive healer (event recording only)   ✗  ← REPAIR 7

EMS run(grid)                                               ems.py:107
   physical writes: battery_level/supercap_level on battery/supercap nodes ✓ (persist)
                    house generation/load via use_battery etc.              ✗ wiped by curves
   consumed by: metric_collector.record_ems_cycle (log only)                ← REPAIR 8

DQNAgent.select_action → action_id                         rl_agent.py:301
   → _dispatch_action → node methods                        ✓ (after REPAIR 3)
   → replay buffer writes?                                 none in harness (eval_mode) ← REPAIR 4

FLISR flisr_9stage → edge active/switch_status             grid.py:1488
   consumed by: update_power_flow (BFS over active edges)  ✓
   consumed by: ENS / metrics                               ✓ (via frozen-load state) ← REPAIR 10
```

## 4. Claims in main.md vs implemented arrows (Stage-42.5 findings)

| main.md claim | Implemented? | Where it breaks |
|---|---|---|
| DQN learns / improves grid operations | ✗ untrained random net | runner.py:366-369, REPAIR 4 |
| LSTM forecast informs control | ✗ string only | runner.py:446, REPAIR 5 |
| Digital twin guides restoration | ✗ heuristic controllers only | runner.py:174-207, REPAIR 6 |
| Predictive healing prepares the grid | ✗ advisory only | info_flow.py:160, REPAIR 7 |
| EMS balances / stores energy | △ SOC effects only, ENS-neutral | info_flow.py:199, REPAIR 8 |
| Actions 0–4 change the grid | ✗ 0 and 4 dead; 1–3 wiped | runner.py:110, REPAIR 3 |
| Scenario multipliers shape the run | ✗ wiped after step 1 | grid.py:691, REPAIR 2 |
| Paired comparisons are fair | ✗ DQN draws env RNG | rl_agent.py select_action, REPAIR 1 |
| ENS measures unserved energy | ✗ frozen loads counted | research_metrics.py:136-138, REPAIR 10 |

After the repairs, this document is the source of truth: every arrow must be a real call and every `✗` must be gone or explicitly documented as intentionally advisory.
