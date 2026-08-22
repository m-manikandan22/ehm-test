# Stage 43 — LSTM Integration (Repair 5)

## Spec contract

`STAGE_43_RUNTIME_CONTROL_FLOW.md` says: LSTM forecast at time `t` must
enter the DQN decision state at time `t` only, using information
available at `t`. No future leakage is permitted.

## Implementation

* Module: `backend/models/lstm_model.py` (`DemandForecaster`).
* Wiring: `backend/experiments/info_flow.py` (`_aggregate_grid_load_and_gen`,
  `_compute_lstm_forecast`).
* Runner hook: `backend/experiments/runner.py:567-574` appends the
  post-`update_power_flow()` `(aggregate_load, aggregate_generation,
  weather_proxy)` observation to a `deque(maxlen=10)` once per step.
* Forecast call: `runner.py:622-637` (gated by `cfg.enable_lstm`).
* State insertion: `rl_agent.py::build_extended_state`,
  `state[72] = predicted_load`.

`weather_proxy` is a *scenario*-level constant, not per-step weather.
`runner.py:463-467`:

```python
_weather_proxy = {
    "normal": 0.2, "storm": 0.85, "heatwave": 0.5,
}.get(str(getattr(scenario, "weather_mode", "normal")), 0.2)
```

This is explicitly documented as an honest Stage-42 framing — no per-step
weather input, just a scenario-level scaling — and the value is
repeated for every step within a run, so it does not contaminate the
temporal signal.

## RNG isolation (no more DQN side-effect from LSTM)

The Stage-42.5 audit showed that constructing `DemandForecaster()` before
`DQNAgent()` perturbed the shared torch RNG and changed the DQN's
random-init weights. Repair (runner.py:443-454):

```python
_np_state = _np.random.get_state()
with _torch.random.fork_rng(devices=[]):
    from models.lstm_model import DemandForecaster
    _lstm_forecaster = DemandForecaster()
_np.random.set_state(_np_state)
```

The LSTM pretraining is now isolated to a forked torch RNG, and the
NumPy state is restored after construction. The DQN's torch RNG is
re-seeded from `stream_seeds["training"]` immediately before
`DQNAgent(...)` (runner.py:487), so the network's initial weights depend
only on that seed regardless of whether the LSTM was built.

## Tests

`tests/test_stage43_integration.py`:

- `test_lstm_reaches_dqn_state` — `EXTENDED_STATE_DIM == 78`,
  `state[72]`, `state[73]`, `state[74]`, `state[75]`, `state[76]`,
  `state[77]` carry the documented values.
- `test_lstm_no_future_leakage` — running 30 steps with
  `history.append(load, gen, weather)` keeps the deque at length 10
  and uses only past observations.
- `tests/test_lstm_no_leakage.py` — chronological split, scaler fit on
  past only.

## Causal reach — what stage-43 proved and did not

Proved (by inspection and unit test):

- `predicted_load` is appended to the decision state at position 72.
- A network's Q-values for that decision state would, in principle,
  depend on `predicted_load`. (`test_lstm_reaches_dqn_state` +
  `test_lstm_no_future_leakage` cover the boundary; `test_twin_*` and
  `test_action_*` confirm other features reach selection.)

Did not prove (because the 10-seed validation did not show it):

- That `full_stack - no_lstm` differs on the validation scenarios at the
  controller level. The validation was run with the same `enable_lstm=True`
  ablations as Stage-42, but the Stage-43 reward collapses the network
  onto a single action, so any *quantitative* "LSTM improves ENS"
  comparison would need a non-degenerate learned policy. The Stage-43
  report marks this as **UNSUPPORTED** until the reward is revisited.
