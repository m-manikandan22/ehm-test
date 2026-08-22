# Stage 43 — Runtime Control Flow

This document maps the actual runtime control path in the Stage-43 harness.
Every arrow corresponds to a real code path; nothing here is aspirational.
Code references are line numbers in the working tree at the time of writing.

Target architecture (per `main.md`):

```
GRID STATE ──> DEMAND FORECAST ──> DECISION STATE ──> DQN CONTROLLER ──> ACTION
   │              (LSTM)              │                  │            │
   │                                 │                  │            │
   │              ASSET HEALTH ───────┘                  │            │
   │              (DIGITAL TWIN)                         │            │
   │                                                    │            │
   │                              EMS ◄─────────────────┤   PREDICTIVE
   │                               │                    │   HEALING ◄─┘
   │                               ▼                    │
   │                          STORAGE STATE             │
   └─────────────────> POWER FLOW ◄─── FLISR ◄──────────┘
                          │
                          ▼
                       METRICS
```

## 1. Per-step sequence inside `run_single()`

`experiments/runner.py::run_single()` is the only path that produces experiment
results. The per-step sequence (line numbers refer to the working tree) is:

| # | Step | Code | Notes |
|---|------|------|-------|
| 1 | Inject faults scheduled for this step | `runner.py:539` (`grid.inject_failure`) | Stage-43 frozen-load accounting is applied at metrics layer (see ENS doc). |
| 2 | Update power flow | `runner.py:562` (`grid.update_power_flow`) | DC-PF + BFS energy flow. |
| 3 | Append `(load, gen, weather)` to LSTM history | `runner.py:568` (`_aggregate_grid_load_and_gen`, `_lstm_history.append`) | `deque(maxlen=10)` — only `t` and earlier enter the LSTM (no future leakage). |
| 4 | Tick twin registry if `enable_twin` | `runner.py:577` (`_tick_twin_registry`) | Each twin's `health_risk_score` advances. |
| 5 | Compute twin feature vector | `runner.py:585` (`_twin_features = {max, mean, high_frac}`) | This is the *only* value that feeds the DQN. Stage-42.5 finding 6 (twin never reaches DQN) is repaired by writing these values into the extended state below. |
| 6 | Predictive preparation if `enable_predictive_healing` | `runner.py:610` (`_predictive_preparation(..., apply_physical=True)`) | For each high-risk asset, pre-close the nearest open tie switch (`info_flow.py:189-219`). |
| 7 | LSTM forecast if `enable_lstm` | `runner.py:622` | History ≤ t, padded to length 10 with the earliest observation. |
| 8 | Controller action selection | `runner.py:652` (`_select_action`) | See §3. |
| 9 | `_dispatch_action(grid, action)` | `runner.py:683` | See §2 (Stage-43 action repair). |
| 10 | `grid.step()` | `runner.py:691` | Physics + `_apply_time_curves` curve write. |
| 11 | EMS dispatch if `enable_ems` | `runner.py:699` (`_run_ems(grid, ..., ems_instance=_ems_instance)`) | Persistent EMS built once per run (see §5). |
| 12 | FLISR every 4 steps if `enable_flisr` | `runner.py:710` | `grid.flisr_9stage()` or `grid.flisr_restore()`. |
| 13 | Re-solve power flow | `runner.py:721` | Settle post-FLISR state. |
| 14 | `collector.record_step(...)` | `runner.py:724` | Includes ENS using `grid.would_be_load(node)` so failed/isolated nodes contribute their baseline. |

## 2. Action space (Stage-43 Repair 3)

`experiments/runner.py::_dispatch_action` (line 130) now applies every action
to a real physical target. Two of five actions were dead code in Stage-42.5:

| ID | Name | Physical effect | Persistence |
|----|------|-----------------|-------------|
| 0 | `increase_generation` | Ramps the first non-failed conventional generator (gas/coal/nuclear) by 0.5 MW (`runner.py:162-174`). Falls back from the fictional `G0` to any live `generator_*` type. | Generation on generator nodes is not rewritten by `_apply_time_curves` (which only touches `_base_load`/`_base_generation` of houses and `generator_solar`/`generator_wind`). Effect persists until `grid.step()` cycle. |
| 1 | `use_battery` | For each energised house or `*storage_bat*` node with `battery_level > 0.2`, calls `node.use_battery(0.2)`. | Battery SOC drain persists; the `_base_load`/`_base_generation` curves do not touch `battery_level`. |
| 2 | `use_supercapacitor` | Same pattern with `node.use_supercapacitor(0.1)` on `*storage_sc*` / house nodes with `supercap_level > 0.1`. | Supercap SOE drain persists. |
| 3 | `shift_load` | For each energised consumer with positive load, calls `node.shift_load(0.15)`. | Effect persists within the step (next `_apply_time_curves` will rewrite it on the *following* step — persistence within the step is the documented scope; see `STAGE_43_ACTION_SPACE.md`). |
| 4 | `reroute_energy` | Calls `grid.reroute_energy()` which closes an open tie switch (`grid.reroute_energy` exists and is documented in `simulation/grid.py`). | Edge activation / `switch_status='closed'` survives power-flow re-solves. |

Additionally, **actions 1–3 now skip failed or isolated nodes**
(`runner.py:157-160`). This is the Stage-43 audit finding that a controller
which discharges a failed house's supercap artificially deflated its ENS.

## 3. Controller action selection

`_select_action()` (`runner.py:207`) chooses the action id for the current
step. Two callers matter:

* `cfg.enable_dqn && agent is not None` — calls
  `agent.select_action(extended_state, predicted_load=predicted_load, grid_state=grid_state)`
  using the **extended state vector** (78-dim; §4).
* `cfg.label in {persistence, random, rule_based}` — uses an explicit
  policy ladder (deficit-based for rule_based; uniform for random;
  zero for persistence). Health-aware controllers prefer action 3
  (`shift_load`) when the twin registry reports any asset with
  `health_risk_score >= 0.5`.

The Stage-43.1 *action mask* (`rl_agent.py::_valid_actions_mask`, line 400)
filters actions whose physical preconditions are **not** met. It encodes no
policy: with a healthy grid all five actions are valid; with every node
dead it returns `[]`; with `health_aware_load_shift` injected it returns
the same set as without. See `STAGE_43_RL_CONTRIBUTION.md` for the policy
separation audit.

## 4. Extended DQN state (Stage-43 Repair 5+6)

The DQN's decision input is built by `build_extended_state()`
(`rl_agent.py:100`):

```
state_t = [
  # legacy 72-dim grid state (grid.get_rl_state())
  # …, 12 per priority node
  # LSTM forecast  (Repair 5,  position 72)
  predicted_load_t,
  # Storage SOC    (positions 73-74)
  battery_soc_t,
  supercap_soc_t,
  # Digital twin   (Repair 6,  positions 75-77)
  twin_max_risk_t,
  twin_mean_risk_t,
  twin_high_frac_t,
]
```

* `predicted_load_t` is `0.5` if `enable_lstm=False`, otherwise
  `lstm_forecaster.predict(history_≤t)`.
* `battery_soc_t` / `supercap_soc_t` are the highest live SOC of the
  corresponding storage type (`_storage_level`, `runner.py:284`).
* `twin_*` features are computed by `info_flow._twin_risk_map` +
  `_twin_features` reduction (`runner.py:587-598`).

No future data is used: history is `deque(maxlen=10)` of `(load, gen, weather)`
samples built only from `runner.py:567-574`, i.e. from the current step and
earlier. Tests `test_lstm_reaches_dqn_state` and `test_lstm_no_future_leakage`
in `tests/test_stage43_integration.py` pin this contract.

## 5. EMS (Stage-43 Repair 8)

`run_single()` builds **one** `EnergyManagementSystem(use_pypsa=False)` per
run (`runner.py:519-524`), stores it in `_ems_instance`, and reuses it on
every step via `_run_ems(grid, metric_collector=collector, ems_instance=_ems_instance)`
(`runner.py:699`). This is the persistence fix: the Stage-42.5 audit
showed that a fresh EMS instance per step could never see its own SOC
drain.

## 6. Predictive healing (Stage-43 Repair 7)

`_predictive_preparation(grid, risk_map, metric_collector=collector, apply_physical=True)`
(`info_flow.py:160`) does two things:

1. Records a `predictive_preparation` event in the metric collector
   (advisory — present in Stage-42).
2. For every high-risk asset, walks `grid.get_open_tie_switches()` and
   closes the tie that is reachable in the fewest graph hops from the
   asset (graph BFS via `networkx.shortest_path_length`). The next
   `grid.update_power_flow()` validates the topology; a closed tie that
   was previously open mutates `grid.graph.edges[*]['active']` and
   `switch_status`.

`apply_physical=True` is the default whenever `enable_predictive_healing`
is set in the runner (`runner.py:610-619`); setting it to `False` is a
controlled-experiment handle for `predictive OFF`.

## 7. RNG streams (Stage-43 Repair 1)

`run_single()` derives three stream seeds from the master seed
(`utils/seeds.derive_stream_seeds`, `runner.py:360`):

```python
stream_seeds = derive_stream_seeds(effective_seed)
# environment  → grid construction + scene noise
# controller   → random policy draws; never touches DQN policy net
# training     → torch.manual_seed before DQN construction
```

The DQN's torch RNG is reseeded from `stream_seeds["training"]` immediately
before `DQNAgent(...)` (`runner.py:487`), and LSTM pretraining happens
inside `torch.random.fork_rng(...)` so it cannot perturb that stream
(`runner.py:443-454`).

Every run records `seeds`, `git_sha`, `environment_trace` (one
`(load, gen)` per step) and four environment fingerprints
(`grid_hash`, `demand_hash`, `renewable_hash`, `fault_hash`) in the
result dict (`runner.py:813-829`). Tests
`test_controller_rng_does_not_change_environment`,
`test_paired_controllers_share_environment` in
`tests/test_stage43_rng_isolation.py` pin this contract.

## 8. Train / eval split (Stage-43 Repair 4)

* Training happens **only** in `experiments/dqn_training.py::train_dqn`
  (built and saved to `experiments/checkpoints/dqn_extended.pt`).
  The checkpoint contains policy + target nets, optimizer state, training
  bookkeeping, stream seeds, Git SHA.
* `run_single()` **never** trains. When `cfg.checkpoint_path` points at
  a real file, it loads with `DQNAgent.load_checkpoint(path, eval_mode=True)`
  (`rl_agent.py:306`). With no checkpoint the DQN is constructed with the
  training stream's seed and immediately put into eval mode
  (`runner.py:475-500`) — that is the **untrained_dqn** baseline.
* `eval_mode()` (line 242) sets `_training=False`, disabling ε-random
  draws, replay pushes and target-net sync.

## 9. Failures the audit does not paper over

`run_single()` wraps every dispatch step in `try/except` and records the
exception in `controller_exceptions` (line 365). When exceptions
occur, the validity report is flipped to `valid=False` with reason
`CONTROLLER_FAILED` (line 803). This is intentional: **no experiment
silently swallows controller errors**.
