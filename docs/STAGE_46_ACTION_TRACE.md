# Stage 46 — Action Trace

Per-action audit: from controller output through to physical
service state. Each row documents the action's source, target,
state variables, physical meaning, expected effect, and
known failure modes.

## Action-result contract

Stage-46 introduces an explicit action-result contract in
`runner._dispatch_action(grid, action_id) -> str`. The returned
string is one of:

| Format | Meaning |
|---|---|
| `<action_name>` | Action was applied; e.g., `use_battery` |
| `<action_name>:<result>` | Structured result (e.g., `reroute_energy:success`, `reroute_energy:no_feasible_action`) |
| `<action_name>:<ERROR>:<ExceptionType>` | Action raised an exception (caught and reported) |

The action-result contract is checked by
`test_stage46_reroute.py::test_f_runner_returns_action_result_for_reroute`
and the Stage-46 validation runner.

## Inventory

| ID | Name | Source | Dispatcher | Target | State vars | Physical meaning | Expected effect | Known failure modes |
|---|---|---|---|---|---|---|---|---|
| 0 | `increase_generation` | `runner.py:130-174` | `_dispatch_action` | First alive conventional generator (G0 → fallback to any non-failed `generator*`) | `node.generation += 0.5` (capped at 2.5) | Spin up extra conventional generation; GAS is not overwritten by `_apply_time_curves` so the effect persists | Increases supply → reduces deficit downstream | None on the 49-node grid (every generator has a valid target); only the "G0 not found" fallback path is exercised |
| 1 | `use_battery` | `runner.py:175-200` | `_dispatch_action` | All alive houses + `storage_bat` nodes with `battery_level > 0.2` | `node.battery_level -= 0.2/capacity`; `node.generation += 0.2`; `node._discharge_signal_mw += 0.2` (Stage-45 marker) | Discharge battery to serve downstream load | Adds live node with `generation > 0` to broadened BFS source set → redistributes downstream | Stage-45 fix: skip auto-recharge when discharge is active |
| 2 | `use_supercapacitor` | `runner.py:201-209` | `_dispatch_action` | All alive houses + `storage_sc` nodes with `supercap_level > 0.1` | `node.supercap_level -= 0.1/capacity`; `node.load -= 0.1` | Short-burst spike mitigation; offsets node-local load | Reduces `P_demand` immediately (load-side, not source-side) | None |
| 3 | `shift_load` | `runner.py:210-236` | `_dispatch_action` | All alive nodes in `_CONSUMER_TYPES` (house/hospital/industry/hospital_icu) with `load > 0.001` | `node.load -= 0.15 * load`; runner also forces `node._base_load = min(cur_base, cur_load)` (Stage-45 baseline patch) | Demand response; defers load | Reduces both `load` and `_base_load` so ENS sees the shift | None |
| 4 | `reroute_energy` | `runner.py:237-279` (post-Stage-46) | `_dispatch_action` calls `grid.reroute_energy` | Open tie switches (`is_tie_switch=True, active=False, not fault_locked, both endpoints alive`) | Closes chosen tie via `close_tie_switch`; no node state change directly | FLISR self-healing: closes tie that re-energises the most isolated load nodes | Topology change → next BFS sees new connectivity | (Stage-46 fix) `NetworkX.NodeNotFound` no longer raised; explicit per-node add_node pre-creates the candidate graph |

## State variables

For every action, the runner mutates the following state:

* `node.generation` (MW) — current power output
* `node.load` (MW) — current demand
* `node.battery_level` (0–1) — battery SOC
* `node.supercap_level` (0–1) — supercap SOC
* `node._base_load` (MW) — baseline demand (used by ENS metric)
* `node._discharge_signal_mw` (MW) — Stage-45 per-step marker
* `node._signal_cleared` (bool) — implicit (zeroed at end of step)
* `grid.graph` edges (`active`, `switch_status`) — topology

Energy accounting invariant (per step):

```
Σ_node.generation_at_live_nodes
  = Σ_pre_step.generation
    + Σ_solar_curve.insertions
    + Σ_wind_curve.insertions
    + Σ_use_battery.discharges
    - Σ_discharge_signal.expires
    + Σ_baseload_recharge_natural
```

The invariant is verified by the Stage-46 battery and
supercap tests.

## Failure modes (and Stage-46 fixes)

| Mode | Where | Stage-46 fix |
|---|---|---|
| `NetworkX.NodeNotFound` from `reroute_energy` on isolated downstream load | `grid.py:918` (pre-Stage-46) | Pre-seed `tmp` with `add_node` for every live node; defensive `if nid in tmp` check |
| Silent exception swallow in `runner._dispatch_action(action=4)` | `runner.py:241-242` (pre-Stage-46) | Catch only `networkx.NetworkXError`; return `reroute_energy:success` / `reroute_energy:no_feasible_action` / `reroute_energy:action_error:<Type>` |
| Auto-recharge defeating deliberate discharge | `node.py:389` (Stage-45 fix) | Recharge branch skipped when `_discharge_active > 0` |
| "G0 not found" on `increase_generation` | `runner.py:163-174` (pre-Stage-43) | Fallback to any non-failed `generator*` node |
| `shift_load` invisible to ENS metric | `runner.py:225-236` (Stage-45 fix) | Force `_base_load = min(cur_base, cur_load)` so formula sees the shift |
| `use_battery` outside daylight window | `node.py:357-360` (Stage-45 fix) | Read `_discharge_signal_mw` as additive generation offset |

## Result verification

The Stage-46 reroute tests verify (test cases A–F):

| Test | Verifies |
|---|---|
| A | Feasible reroute produces non-empty `benefited_nodes` |
| B | Infeasible reroute returns explicit `closed=None` + reason |
| C | No closed tie has a failed endpoint |
| D | Reroute measurably improves served power on benefited nodes |
| E | Idempotent — second call does not corrupt topology |
| F | Runner returns explicit action-result string |

All 6 tests pass. The Stage-46 battery, supercap, load_shift,
generation, and FLISR tests verify the corresponding
invariants for the other actions. Total Stage-46 tests:
27 passed, 1 skipped (G0 fallback test).
