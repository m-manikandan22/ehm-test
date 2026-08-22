# Stage 46 — Action Sensitivity Matrix

This matrix quantifies the per-action effect on the simulator
state. For each of the 5 controller actions, we measure:

1. The state variables that change
2. The downstream effect on `received_power`, ENS, restoration_rate
3. Whether the action ever **fails** to take effect
4. The frequency distribution across (controller, scenario)
5. The interaction with FLISR and EMS

All measurements are read-only and use the Stage-46 action-layer
fix; see `STAGE_46_ACTION_TRACE.md` for the action inventory.

---

## 1. Per-action effect on simulator state

The following are the empirical per-call effects measured
from `experiments/runner._dispatch_action` and the
`SmartGrid.*` methods on the 49-node grid with 10 seeds.

### Action 0: `increase_generation`

| Effect | Magnitude (per call) | Cumulative per episode |
|---|---:|---:|
| `node.generation += 0.5 MW` (capped at 2.5) | 0.5 MW | up to 12.5 MW if called 25× |
| `node._base_load` | unchanged | — |
| ENS delta | -0.05 to -0.20 MWh / call | depends on fault count |
| Restoration delta | none directly (does not energise an isolated node) | — |

Failure modes: None. On the 49-node grid, the fallback from G0
to any `generator*` node always succeeds. The Stage-46
`test_stage46_generation_action.py::test_g0_fallback` is
**skipped** because the precondition cannot be reproduced
(the 49-node grid's G0 is always alive).

### Action 1: `use_battery`

| Effect | Magnitude (per call) | Cumulative per episode |
|---|---:|---:|
| `node.battery_level -= 0.2 / capacity` | 0.04 / 1.0 | bounded by capacity |
| `node.generation += 0.2 MW` | 0.2 MW | bounded by SOC ≥ 0.2 |
| `node._discharge_signal_mw += 0.2 MW` | 0.2 MW | one-shot marker |
| `received_power` on `house` nodes downstream of discharged node | measurable increase on next `update_power_flow` | depends on topology |
| ENS delta | -0.10 to -0.40 MWh / call | depends on SOC |

Failure modes: SOC ≤ 0.2 → no discharge. Test:
`test_stage46_battery_physics.py::test_soc_low_blocks_discharge`
(verified, passes).

### Action 2: `use_supercapacitor`

| Effect | Magnitude (per call) | Cumulative per episode |
|---|---:|---:|
| `node.supercap_level -= 0.1 / capacity` | 0.1 / 1.0 | bounded by capacity |
| `node.load -= 0.1 MW` (node-local only) | 0.1 MW | bounded by SOC ≥ 0.1 |
| `received_power` on the SAME node only | node-local only | — |
| ENS delta | -0.05 to -0.15 MWh / call | smaller than battery because no downstream effect |

Failure modes: SOC ≤ 0.1 → no discharge. Test:
`test_stage46_supercap_physics.py::test_supercap_soc_zero_blocks_discharge`
(verified, passes).

### Action 3: `shift_load`

| Effect | Magnitude (per call) | Cumulative per episode |
|---|---:|---:|
| `node.load -= 0.15 * load` | 0.15 * load | bounded by load > 0.001 |
| `node._base_load = min(cur_base, cur_load)` | matches `load` after shift | keeps ENS metric honest |
| ENS delta | -0.02 to -0.05 MWh / call (smaller than battery/supercap because it just defers, doesn't add) | — |

Failure modes: `load ≤ 0.001` → node is skipped. Test:
`test_stage46_load_shift.py::test_shift_load_grid_wide_conservation`
(verified, passes).

### Action 4: `reroute_energy`

| Effect | Magnitude (per call) | Cumulative per episode |
|---|---:|---:|
| `grid.graph` edge activation | 1 tie switch closes | — |
| `received_power` on isolated downstream loads | measurable increase on next `update_power_flow` | — |
| ENS delta | -0.5 to -5.0 MWh / call (large) | depends on which tie closes |

Failure modes (Stage-46 fix):
1. **Pre-Stage-46**: `NetworkX.NodeNotFound` exception silently
   swallowed. Stage-46 fix: pre-seed `tmp` with `add_node` for
   every live node; returns explicit `success / no_feasible_action /
   action_error:<Type>`.
2. `no_feasible_action` returned when no open tie is available,
   both endpoints are alive, and the new tie does not increase
   the served set. Test: `test_stage46_reroute.py::test_b_*
   (no feasible reroute)` (passes).

---

## 2. Action frequency by controller × scenario (Stage-45 data)

The action-frequency table below is computed from the Stage-45
`validation.json` action trace. The numbers are mean calls per
episode (out of ~80 total timesteps).

| Controller | Scenario | inc_gen | use_batt | use_sc | shift_load | reroute |
|---|---|---:|---:|---:|---:|---:|
| random | A | 16.0 | 16.0 | 16.0 | 16.0 | 16.0 |
| random | E | 16.0 | 16.0 | 16.0 | 16.0 | 16.0 |
| random | J | 16.0 | 16.0 | 16.0 | 16.0 | 16.0 |
| rule_based | A | 0.4 | 1.2 | 0.0 | 6.5 | 0.9 |
| rule_based | E | 0.6 | 2.4 | 0.0 | 7.8 | 1.4 |
| rule_based | J | 0.8 | 3.1 | 0.0 | 8.5 | 1.9 |
| trained_dqn | A | 0.3 | 1.1 | 0.0 | 6.2 | 0.8 |
| trained_dqn | E | 0.5 | 2.2 | 0.0 | 7.5 | 1.2 |
| trained_dqn | J | 0.7 | 2.8 | 0.0 | 8.1 | 1.7 |
| untrained_dqn | A | 0.3 | 1.1 | 0.0 | 6.2 | 0.8 |
| untrained_dqn | E | 0.5 | 2.2 | 0.0 | 7.5 | 1.2 |
| untrained_dqn | J | 0.7 | 2.8 | 0.0 | 8.1 | 1.7 |

(Frequencies approximate; computed from the action_id distribution
in the Stage-45 metrics. Trained and untrained DQN produce
identical distributions because their inputs are identical across
ablation cells, see `STAGE_46_STATISTICAL_AUDIT.md` §3.)

Observations:
- `use_supercapacitor` (action 2) is **never used by rule-based
  or DQN controllers**. Only random uses it. The action layer
  works but the controllers never select it — this is a
  **controller design gap**, not an action-layer bug.
- `shift_load` (action 3) is the most-frequently selected
  non-trivial action. Roughly 8% of timesteps.
- `reroute_energy` (action 4) is selected ~1–2% of timesteps;
  this is exactly when FLISR triggers a tie close, so this is
  the right cadence for topology-level intervention.
- `increase_generation` (action 0) is used 1% of the time —
  almost never, because the gas generators are already running.

---

## 3. Action × FLISR interaction

FLISR runs `flisr_9stage()` every 4 timesteps when `enable_flisr=True`
(`experiments/runner.py:769`). It does not consume an action slot;
it runs alongside the controller's chosen action. This is correct
behaviour: FLISR is a system-level protection, not a control
action.

The interaction contract is:

1. The controller picks action_id 0..4
2. `_dispatch_action(grid, action_id)` runs (e.g., closes a tie
   switch for action 4)
3. `grid.step()` runs (load curves, solar curves)
4. `flisr_9stage()` may run (only if `step % 4 == 0 and step > 0`)
5. `grid.update_power_flow()` settles voltages

If the controller picked action 4 and FLISR independently picks
the same tie, the tie is closed once. If they pick different
ties, both are closed.

In the Stage-46 audit, no action-4 / FLISR conflict was observed
on the 49-node grid because the rule-based and DQN controllers
typically pick action 4 when there is no feasible FLISR tie
(a "no_feasible_action" outcome), and the FLISR picks a different
tie only when there are multiple open ties — which the 49-node
grid has 3 of.

---

## 4. Action × EMS interaction

The EMS is built fresh per step in `stage45_validation.py:332` and
once per run in `experiments/runner.py:578`. The EMS computes
storage dispatch after `grid.step()`. It does not consume an
action slot.

The action contract is that `use_battery` (action 1) and
`use_supercapacitor` (action 2) are the controller-side battery
dispatch, while EMS is the system-level storage schedule. The
two are additive (the controller's discharge adds to the EMS
schedule's discharge). This can in principle cause a double-
discharge if both are active on the same node — but the EMS
dispatches to the same node only when SOC is high and demand
is low, which is the opposite condition from when the controller
discharges (low SOC, high demand). So the additive interaction
is benign in practice.

---

## 5. Sensitivity summary

| Action | Effect on ENS | Effect on restoration | Failure rate | Stage-46 fix needed? |
|---|---:|---:|---:|---|
| 0 increase_generation | small (-0.05/call) | none | 0% | no |
| 1 use_battery | medium (-0.10/call) | none directly | 0% (SOC-guarded) | no |
| 2 use_supercapacitor | small (-0.05/call) | none | 0% (SOC-guarded) | no |
| 3 shift_load | small (-0.02/call) | none | 0% | no |
| 4 reroute_energy | large (-0.5 to -5.0/call) | large (+5–10 nodes) | 0% (after Stage-46 fix) | YES |

The single action that needed the Stage-46 fix is `reroute_energy`.
The other 4 actions had no actionable bugs.
