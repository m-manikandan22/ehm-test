# Stage 43 — RNG Isolation (Repair 1)

## Spec

`STAGE_43_RUNTIME_CONTROL_FLOW.md` §7 requires three independent
streams: environment, controller, training. Controller inference must
not consume the environment's noise stream.

## Implementation

`utils.seeds.derive_stream_seeds(master_seed)` returns a dict with
`"environment"`, `"controller"`, `"training"` keys.

`run_single()` (`runner.py:355-365`):

```python
set_global_seed(effective_seed)
stream_seeds = derive_stream_seeds(effective_seed)
grid = _build_grid(effective_seed, rng_seed=stream_seeds["environment"])
controller_rng = make_rng(stream_seeds["controller"])
```

`DQNAgent(...)` is constructed after `torch.manual_seed(stream_seeds["training"])`,
so:

- The grid noise stream is owned by `stream_seeds["environment"]`
  inside `SmartGrid(rng_seed=...)`.
- The random policy draws from `controller_rng` (a
  `numpy.random.Generator`).
- The LSTM pretraining is wrapped in `torch.random.fork_rng`, so it
  cannot perturb the training stream.
- The DQN's `policy_net` weights depend only on
  `stream_seeds["training"]`.

`eval_mode()` in `DQNAgent.select_action` (rl_agent.py:486) sets
`self.epsilon = 0.0`, so in eval mode `random.random() < self.epsilon`
is never true and **no global random draw happens at inference**.
This is the second half of the fix: even if the controller stream were
shared with the environment, no controller draw happens at inference.

## Tests

`tests/test_stage43_rng_isolation.py`:

- `test_controller_rng_does_not_change_environment` — running a random
  policy that draws N controller numbers leaves the environment stream
  stream identical.
- `test_paired_controllers_share_environment` — two controllers
  (random, rule_based, untrained_dqn, trained_dqn) on the same
  (scenario, seed) show identical `_environment_trace` and identical
  grid noise stream.

## Files

- `backend/utils/seeds.py` — `derive_stream_seeds`, `make_rng`,
  `set_global_seed`.
- `backend/experiments/runner.py:355-365` — per-run seeding.
- `backend/models/rl_agent.py:486` — epsilon=0 in eval mode.
