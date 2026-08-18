# HYBRID_STORAGE.md — Stage 8

This document is the master specification for the hybrid
**battery + supercapacitor** storage subsystem used by the EHM control
loop. It defines the state variables, dispatch order, assumptions,
limits, and how the agents interact with the storage.

> **Status:** SIMULATION-VALIDATED — the equations below are the exact
> ones running in `backend/simulation/node.py::GridNode`. No real-world
> tuning has been performed.

---

## 1. Why two storage technologies?

| Storage              | Power density      | Energy density        | Response time | Best for                          |
| -------------------- | ------------------ | --------------------- | ------------- | --------------------------------- |
| **Supercapacitor**   | very high          | low                   | < 1 s         | Short transients (load spikes, voltage sags) |
| **Battery (Li-ion)** | moderate           | high                  | seconds–minutes | Sustained demand / peak shaving   |

A single storage technology forces a compromise: a battery alone is too
slow for spike suppression; a supercap alone has too little energy for
even a few seconds of full demand. **Hybridisation** lets each device
operate in the regime where it dominates. This is a well-established
principle in EV and renewable-integration literature.

---

## 2. State variables (per node)

Each `GridNode` carries:

```python
self.battery_level      # ∈ [0, 1]   — SOC
self.battery_capacity   # MWh (default 10.0)
self.supercap_level     # ∈ [0, 1]   — SOE (state of energy)
self.supercap_capacity  # MWh (default 1.0)
self.generation         # current output (MW)
self.load               # current demand (MW)
```

Capacity defaults are chosen so the supercap can cover ~1 timestep of
demand and the battery can cover ~30 timesteps — i.e. fast and slow
storage roles are physically distinct in the simulator.

---

## 3. Per-step logic

The dispatch lives in `GridNode.step()` (simplified):

```
internal_balance = generation − load       # MW for this node, this step

if internal_balance > 0:
    # 1) Supercap charges FIRST on surplus
    cap_space  = 1.0 − supercap_level
    cap_charge = min(internal_balance · 0.1 · dt, cap_space)
    supercap_level = min(1.0, supercap_level + cap_charge)
    internal_balance -= cap_charge

    # 2) Battery charges on remaining surplus
    bat_space  = 1.0 − battery_level
    bat_charge = min(internal_balance · 0.05 · dt, bat_space)
    battery_level = min(1.0, battery_level + bat_charge)
    internal_balance -= bat_charge

# Deficit is unmet by default; agents (or controllers) may call
# ``use_supercapacitor`` or ``use_battery`` to cover it.

self.excess_energy = max(0, internal_balance)
self.deficit       = max(0, −internal_balance)
```

Net effect: on every step where generation exceeds load, the supercap
charges first (because of the 0.1 vs 0.05 weighting), the battery
charges next, and any leftover is recorded as `excess_energy`. On a
deficit, `deficit` is exposed for downstream controllers to react to.

---

## 4. Actions the agents can take

| Method                                      | Effect                                                                   |
| ------------------------------------------- | ------------------------------------------------------------------------ |
| `node.use_supercapacitor(amount_mwh=0.1)`   | Discharge `supercap` to offset `node.load` by up to `amount_mwh`; returns actual MWh delivered. |
| `node.use_battery(amount_mwh=0.3)`          | Discharge `battery` to offset `node.load`; returns actual MWh delivered.  |
| (implicit) `node.step()`                    | Per-tick charge/discharge as above                                        |
| `node.snapshot()`                           | Records current state for the digital twin (heath, load, generation history) |

Agent policy
------------
The DQN action catalogue (see `docs/REWARD_FORMULATION.md`) uses
`use_battery` and `use_supercapacitor` as **distinct** actions to make
the policy learn which to use when. Action masking disables
`use_supercapacitor` unless a load spike is observed, and disables
`use_battery` when SOC is already empty (and vice-versa).

---

## 5. Dispatch order

For a given node, the *spontaneous* (control-loop) dispatch follows
"supercap first on transients, battery on sustained demand":

| Condition                                | First reaction                         |
| ---------------------------------------- | -------------------------------------- |
| Surplus (gen > load)                     | Supercap charges, then battery charges |
| Transient deficit (spike ≪ battery cap)  | Supercap discharges via `use_supercapacitor` |
| Sustained deficit                        | Battery discharges via `use_battery`   |
| Sustained deficit + supercap low/empty   | Battery discharges (deeper)            |

This is enforced by the action-mask in `DQNAgent.select_action`: action
2 (`use_supercapacitor`) requires a spike (`load > 1.2 pu`), action 1
(`use_battery`) requires a `balance < −0.1` (deficit). The legacy
fallback in `rl_agent.expert_policy` follows the same ordering.

---

## 6. Limits

* `supercap_level ∈ [0, 1]` — clamped at every update
* `battery_level ∈ [0, 1]` — clamped at every update
* `use_supercapacitor(amount)` returns `min(amount, available)` so
  callers cannot over-draw.
* Round-trip efficiency is **not** modelled — energy in equals energy
  out per transfer. This is a deliberate simplification; see
  `docs/LIMITATIONS.md`.
* Thermal limits are **not** modelled — the SOC/SOE caps are sufficient
  for the simulation.

---

## 7. What this subsystem does NOT capture

| Not modelled                               | Why                                                          |
| ------------------------------------------ | ------------------------------------------------------------ |
| Internal resistance / heat                 | Out of scope for control-loop paper                          |
| Cycle-counting / ageing                    | Captured separately by the DigitalTwin (Stage 10)            |
| AC-side inverter dynamics                  | Captured by AC PF (Stage 4 — optional)                       |
| DC-bus dynamics                            | Out of scope                                                 |

---

## 8. Citation form (for the paper)

> The EHM nodes carry both battery (10 MWh default) and supercapacitor
> (1 MWh default) state, with the supercap charged first on surplus
> (`×0.1 per tick` vs. `×0.05 for battery`) so it stays ready for the
> next transient. The DQN action catalogue (action 1 = use_battery,
> action 2 = use_supercapacitor) maps to `node.use_battery()` and
> `node.use_supercapacitor()` respectively, with action masking
> preventing impossible actions.

See also:
- `backend/simulation/node.py::GridNode.step` — the per-step dispatch.
- `backend/simulation/node.py::GridNode.use_supercapacitor`
- `backend/simulation/node.py::GridNode.use_battery`
- `backend/tests/test_grid.py` — implicit coverage in grid step tests.
- `docs/REWARD_FORMULATION.md` — where the actions enter the reward.