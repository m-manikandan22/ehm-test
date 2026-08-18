# REWARD_FORMULATION.md — Stage 12

This document specifies the reward function used to train the DQN agent in
the EHM-simulation framework. It is the master specification the paper
should cite whenever it claims "the agent is trained with reward R".

> **Status:** SIMULATION-VALIDATED — the reward is well-defined and
> deterministic inside the simulator, but no real-world tuning has been
> performed. See `docs/LIMITATIONS.md` (Stage 34) for what this implies.

---

## 1. Mathematical form

The reward at time `t` is a linear weighted sum of named components:

```
R_t = Σ_k  w_k · c_k(state_t, action_t, state_{t+1})
```

Where each `c_k` is a scalar function of the (state, action, next-state)
triple, and `w_k` is the configurable weight (default values in section 4).
The implementation lives in `backend/rl/rewards.py::RewardComposer.compute`.

The legacy `DQNAgent.compute_reward` static method is *not* used for
training by the experiment runner; it remains as a backward-compat shim
for older callers and as a contrasting "legacy reward" in ablation runs.

---

## 2. State and action spaces

### State
The DQN consumes the 72-dimensional vector produced by
`SmartGrid.get_rl_state()`:

```
[voltage, freq/50, load, generation, stress] × 13 priority nodes
   + 7 global system features
   = 65 + 7 = 72 dims
```

The 13 priority nodes are: 5 generators, `S_MAIN`, 2 storage nodes, 3
transformer feeders, `HOSP`, `IND0`. This matches the default targets
used by `SmartGrid.get_rl_state()`.

### Action
There are 5 discrete actions (see `backend/models/rl_agent.py::ACTIONS`):

| id | name                | semantics                                    |
| -- | ------------------- | -------------------------------------------- |
| 0  | increase_generation | boost all substations' output                |
| 1  | use_battery         | discharge battery at highest-deficit node    |
| 2  | use_supercapacitor  | discharge supercap to absorb load spikes     |
| 3  | shift_load          | defer 10% of house-node loads                |
| 4  | reroute_energy      | close alternate tie-switches                 |

`select_action` masks out invalid actions using
`grid_state` observations (e.g. action 1 is suppressed when no battery
is depleted, action 2 is only valid when a load spike is observed).

---

## 3. Reward components

| Component                   | Sign | Default weight `w_k` | Computed from                                                     |
| --------------------------- | ---- | -------------------- | ------------------------------------------------------------------ |
| `critical_load_restored`    | +    | 1.0                  | count of newly energised hospital/ICU/gov nodes                   |
| `outage_penalty`            | −    | 1.0                  | count of newly failed nodes                                        |
| `overload_penalty`          | −    | 0.5                  | count of edges with `|flow| > 0.95 * capacity`                    |
| `switching_cost`            | −    | 0.1                  | 1 per `open_switch`/`close_switch`/`reconfigure_feeder`/`merge_island` action |
| `renewable_usage`           | +    | 0.3                  | fraction of generation from `solar_farm`/`wind_farm`               |
| `reliability_bonus`         | +    | 0.5                  | 1 if `reliability_index > 0.8`, else 0                             |
| `voltage_stability_bonus`   | +    | 0.2                  | 1 if `min(voltage) > 0.92 pu` across all nodes, else 0             |
| `carbon_penalty`            | −    | 0.05                 | `(carbon_kg / 1000) * w_carbon` — read from `carbon_kg` key       |
| `economic_penalty`          | −    | 0.02                 | `(economic_usd / 1000) * w_economic` — read from `economic_usd`    |

The per-component value is computed by the corresponding callable in
`RewardComposer.components` (a `dict[str, Callable]`), so each one can be
replaced, scaled, or zeroed-out for ablation runs.

---

## 4. Default weights

```python
RewardComposer(
    w_critical_restored   =  1.0,
    w_outage_penalty      = -1.0,
    w_overload_penalty    = -0.5,
    w_switching_cost      = -0.1,
    w_renewable_usage     =  0.3,
    w_reliability_bonus   =  0.5,
    w_voltage_bonus       =  0.2,
    w_carbon_penalty      = -0.05,
    w_economic_penalty    = -0.02,
)
```

These are the defaults used by the `full_stack` configuration in
`ExperimentConfig`. They are **not** the result of any tuning campaign;
they were chosen to make the linear sum bounded in [-1, 1] under the
default scenario.

---

## 5. Reward shaping choices — and what they *don't* claim

* **Critical-load first.** Restoring a hospital node yields
  `w_critical_restored = +1.0` per node. That makes critical-load
  restoration the largest positive component in a typical fault cycle.
* **Switching cost is small.** A single switch action costs `−0.1`.
  This intentionally under-penalises switching so the agent is not
  afraid to reroute when it would clearly improve restoration.
* **Carbon & economic components are passive.** They only contribute
  when `carbon_kg` or `economic_usd` keys are populated by the
  external metrics endpoint (`/metrics/carbon`). They contribute
  nothing in the default scenario.
* **No imitation loss.** The rule-based warm-up in
  `DQNAgent.smart_warmup` populates the replay buffer with
  expert-chosen actions, but there is **no behavioural-cloning head**
  on the network. The agent learns from the *reward signal*, not from
  the rule ladder (see `docs/BASELINE_SNAPSHOT.md` note in
  `rl_agent.py::smart_warmup`).

---

## 6. What this reward does NOT capture

| Not captured                             | Why                                                                                  |
| ---------------------------------------- | ------------------------------------------------------------------------------------ |
| Crew dispatch time                       | No field-crew state in the simulator                                                |
| Equipment ageing acceleration           | Captured separately by `DigitalTwin` (Stage 10), not by the per-step reward         |
| Customer interruption cost (CIC)         | A future iteration could map ENS → USD, but no calibrated CIC exists in this paper  |
| Voltage sags / harmonics                  | We track per-node voltage magnitude only — no waveform features                     |
| Cyber-physical attacks                   | Out of scope for this paper                                                         |

These omissions are intentional. They keep the reward linear, bounded,
and interpretable in the XAI panel.

---

## 7. Ablation & reproducibility

* The `no_reward` ablation in `ExperimentConfig` sets every weight to
  zero. That ablation is *not* "no learning" — the agent still learns
  from the replay buffer; it just receives no signal. (Used as a sanity
  check; results should be statistically indistinguishable from random.)
* Every component is a callable that can be swapped without changing
  the optimiser. To ablate a single component, set its weight to 0
  (or remove the key from `RewardComposer.components`).
* Default weights and component set are pinned in
  `backend/rl/rewards.py` and recorded in every run's
  `manifest.json` via the experiment runner.

---

## 8. Citation form (for the paper)

> The DQN is trained against a linear weighted sum of nine named reward
> components (`RewardComposer` in `backend/rl/rewards.py`), each derived
> from the post-action grid state and the dispatched action. Defaults
> `w_*` are listed in `docs/REWARD_FORMULATION.md`. We do **not** apply
> any manual reward shaping outside this composition.

See also `docs/REQUIREMENTS_TRACEABILITY.md` Stage 12 entry.