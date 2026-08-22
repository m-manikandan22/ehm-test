# Stage 43 — DQN Training (Repair 4)

## Goal

The Stage-42.5 audit verified that the harness DQN had never been trained —
the ablation row measured freshly-seeded random weights behind a hand-coded
mask. Stage-43 Repair 4 makes training an explicit, recorded step that
precedes evaluation, and forbids training during evaluation.

## Training pipeline

`backend/experiments/dqn_training.py::train_dqn`

1. **Seeding.** `set_global_seed(master_seed)` and
   `derive_stream_seeds(master_seed)` produce three independent streams
   (`environment`, `controller`, `training`). `torch.manual_seed` is set
   from the *training* stream so network initialisation depends only on
   that seed (the Stage-42.5 RNG contamination finding is repaired).
2. **Environment.** A new `SmartGrid(seed=..., rng_seed=env_seed)` is built
   per episode. `episodes=8`, `steps_per_episode=200` is the default; the
   scenario is the **clean** (no-fault) training scenario so the policy
   learns basic supply/demand balancing before facing faults at evaluation.
3. **State.** For every step we compute the *same* 78-dim extended
   vector as at evaluation:
   - `state = grid.get_rl_state()` (72-dim)
   - `forecast_feature = max(0.05, min(2.0, _aggregate_load(grid) / 20.0))`
     — varied across steps so the network has gradient pressure on
     feature 72 (a constant forecast would give no signal).
   - `battery_soc = _soc(grid, "battery")`
   - `supercap_soc = _soc(grid, "supercap")`
   - The next-state vector uses the post-step forecast feature to keep
     replay tensors dimensionally consistent.
4. **Action.** `agent.select_action(extended_state, predicted_load, grid_state)`
   chooses via the standard ε-greedy + physical-validity mask.
   `grid._dispatch_action(action)` applies the effect, then `grid.step()`
   and `grid.update_power_flow()` advance physics.
5. **Store.** `agent.store_experience(extended, action_id, reward, next_state, done=False)` pushes a transition and, when the replay buffer has ≥ `BATCH_SIZE=32` entries, runs `_train_step()` (Huber loss + Bellman target + gradient clip + Adam step). Every `TARGET_UPDATE=20` steps the target net is synced.
6. **Checkpoint.** `agent.save_checkpoint(path, seeds=..., git_sha=...)`
   writes `policy_net`, `target_net`, `optimizer`, `steps_done`, `epsilon`,
   `state_dim`, the stream seeds, the repo SHA and a structured `extra`
   block (training seed, episode count, total transitions, mean reward
   per episode, final ε). Default path:
   `backend/experiments/checkpoints/dqn_extended.pt`.

## What is *not* in the checkpoint

The replay buffer is intentionally **not** persisted: it is
training-only scratch, not part of the policy.

## Run-to-run determinism

Same master seed + same episodes/steps ⇒ **byte-identical checkpoint**:

- `set_global_seed(master_seed)` reseeds Python, NumPy and torch.
- The environment stream is per-episode (`stream_seeds["environment"] + ep * 10_007`)
  so each training episode explores a slightly different grid but
  physics noise is reproducible.
- Network initialisation depends only on the training stream because
  the LSTM pretraining (a separate `torch.random.fork_rng(...)` block in
  `run_single()`) does not touch the shared torch RNG.

## Evaluation

`run_single()`:

- Loads the checkpoint with `DQNAgent.load_checkpoint(path, eval_mode=True)`
  ⇒ `_training=False`, ε frozen at 0, replay push is a no-op, no
  gradient step, no target-net sync.
- Without a checkpoint, builds the DQN with the training stream's seed
  and immediately puts it in eval mode ⇒ **untrained_dqn** baseline.
- Never calls `agent.train_mode()`, `agent.store_experience(...)`,
  `agent._train_step()`, `agent.target_net.load_state_dict(...)` during
  an experiment run. The only `_train_step` triggers are in
  `dqn_training.py` (warmup + on-policy updates) and the single
  `smart_warmup(...)` boilerplate; the harness does **not** invoke
  `smart_warmup`.

`test_checkpoint_exists_and_is_loadable`,
`test_trained_dqn_differs_from_untrained`,
`test_eval_never_trains`,
`test_dqn_checkpoint_reload_frozen` in
`tests/test_stage43_integration.py` + `tests/test_dqn_eval_mode.py`
pin this contract.

## What training *does* and *does not* prove

`trained_dqn` is a real frozen policy: weights differ from random
initialisation (training updates persisted to the .pt file); the policy
chooses an action consistently because Q-values are deterministic
given the network. The 10-seed validation (see
`STAGE_43_COMPLETION_REPORT.md`) shows the trained policy collapsed to
a single action (`use_supercapacitor`) — meaning the reward function
(`+2` for supercap during high load) is learnable, but a
single-action deterministic policy is **not** the paper's claim of an
intelligent controller. We report it honestly rather than tuning the
reward to spread actions.

## Files

- `backend/experiments/dqn_training.py` — train + checkpoint.
- `backend/experiments/checkpoints/dqn_extended.pt` — produced checkpoint.
- `backend/models/rl_agent.py` — `DQNAgent.train_mode/eval_mode`,
  `save_checkpoint`, `load_checkpoint`, `store_experience` (eval-mode
  short-circuit at line 589).
- `backend/experiments/runner.py` — checkpoint loading + frozen
  evaluation (lines 487-500).
