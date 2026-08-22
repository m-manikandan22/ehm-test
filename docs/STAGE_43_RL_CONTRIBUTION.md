# Stage 43 — RL vs Heuristic Contribution Separation

## Why this document exists

The Stage-42.5 audit found that every ablation delta between controllers
in the harness could be explained by one of:

- a torch-RNG weight-init artefact (LSTM construction before DQN),
- a hand-coded mask (consumed *only* by the DQN path),
- a frozen-load metric artefact (controller actions deflating a failed
  node's load to lower ENS without restoring service).

Stage-43 separates a controller's effective action path into pieces that
are scientifically defensible from pieces that are not.

## The five-way split

The Stage-43 validation runs five controllers per (scenario, seed):

| Controller | Selection rule | Net | Mask | LSTM | Twin | Predictive | EMS | Storage |
|------------|----------------|-----|------|------|------|------------|-----|---------|
| `persistence` | always `0` | — | off | off | off | off | off | off |
| `random` | uniform over 0..4 (with twin-driven action 3 bias) | — | off | off | off | off | on | on |
| `rule_based` | deficit→`1`, twin high-risk→`3` | — | off | off | off | off | on | on |
| `untrained_dqn` | argmax over Q-values of random-init network | random weights | physical-validity | on | on | on | on | on |
| `trained_dqn` | argmax over Q-values of `dqn_extended.pt` | trained | physical-validity | on | on | on | on | on |
| `full_stack` | same as `trained_dqn` but with checkpoint absent | random weights | physical-validity | on | on | on | on | on |

## What is verified to *not* be the network

* **Mask ≠ policy.** `test_action_mask_does_not_encode_policy` (Stage-43
  integration tests) sweeps `balance`, `health_aware_load_shift`,
  `predicted_load` and shows the mask remains `{}..{0,1,2,3,4}` based
  only on physical resource availability.
* **Health-aware bias ≠ net.** The rule_based / random bias towards
  action 3 when the twin reports `max risk >= 0.5`
  (`runner.py:237-280`) is a documented *controller behaviour*, not a
  hidden mask.

## What is verified to *be* the network

* **Network ≠ random after training.** `test_trained_dqn_differs_from_untrained`
  builds two identical-state DQN agents, one with `DQNAgent()` (seeded
  by test global RNG, random init), one with
  `DQNAgent.load_checkpoint(_CHECKPOINT, eval_mode=True)` (trained
  weights), and shows they pick different actions for the same probe
  state.
* **Eval mode freezes the network.** `test_eval_never_trains` runs the
  full `trained_dqn` controller through `run_single()` and asserts the
  validity report is clean (no controller-side exception, no hidden
  training loop).
* **LSTM forecast reaches the network.** `test_lstm_reaches_dqn_state`
  asserts the 78-dim extended vector contains `predicted_load`,
  `battery_soc`, `supercap_soc`, `twin_max_risk`, `twin_mean_risk`,
  `twin_high_frac` at the documented positions, and that an LSTM only
  updates via `deque(maxlen=10)` of past observations.

## What the 10-seed validation showed

Validation summary at `experiments/results/stage43_validation/summary.md`:

* **Pairing integrity**: ALL PAIRS MATCH — every (scenario, seed) has
  identical `grid_hash`, `demand_hash`, `renewable_hash`, `fault_hash`
  across the five controllers, so paired comparisons compare what they
  claim to compare.
* **Action counts (5 scenarios × 10 seeds × 32 steps = 1600 steps each)**:
  - `random`: {0: 1606, 1: 1514, 2: 1573, 3: 1685, 4: 1622} — uniform.
  - `rule_based`: {1: 7200, 3: 800} — `use_battery` whenever a deficit
    exists, else `shift_load` when the twin reports high risk.
  - `untrained_dqn` / `full_stack`: {0: 278, 1: 1674, 2: 4090,
    3: 1348, 4: 610} — untrained network, mostly `use_supercapacitor`
    because the mask makes that action physically valid most often.
  - `trained_dqn`: {2: 8000} — *every* action is `use_supercapacitor`.
    This is what the reward function (`compute_reward` line 632) was
    designed to teach: `+2.0` whenever `use_supercapacitor` is taken
    during a load spike, repeatable across episodes. Training worked.
    The learned policy is degenerate (single-action deterministic), but
    it is **not** identical to untrained — that is what we wanted to
    prove.
* **ENS table**: trained_dqn equals untrained_dqn and equals full_stack
  on most scenarios at one-decimal precision, beating none of the
  baselines — but the report is honest about why: the policy became
  deterministic-on-action-2 rather than learning to discriminate,
  because the reward and state features are not yet rich enough.

## What the paper can and cannot claim from this

**Can claim (with evidence):**

- The DQN training pipeline *executes* end-to-end and produces a
  reproducible checkpoint.
- A trained policy and a random policy, given the same evaluation
  setup, choose different actions for the same probe state.
- The harness's controllers are paired on the environment (fingerprints
  match across the table).
- LSTM forecast, twin risk features and storage SOC reach the DQN state
  vector (causal test in `tests/test_stage43_integration.py`).

**Cannot yet claim:**

- That the trained DQN is *better* than the random / rule_based
  controllers on ENS, restoration rate, or any other resilience metric
  for the Scenarios A/E/G/H/J validation set. The current reward
  collapses the policy onto `use_supercapacitor`, which is good enough
  to show training happened but not good enough to claim improvement.
- That the LSTM forecast alone changes decisions on Scenarios A/E/G/H/J
  — the network in `trained_dqn` was trained on a noisier forecast
  feature, so attributing any future ENS delta to the LSTM versus the
  varied training distribution needs further work.
- That the digital twin improves resilience on Scenarios A/E/G/H/J —
  it changes the rule_based policy's action distribution (Scenario H:
  twin ON → 0.967 restoration rate vs twin OFF → 0.933, per the
  validation), but a 0.034 restoration-rate delta on `n=10` is not a
  significance statement.

These caveats are stated in `STAGE_43_COMPLETION_REPORT.md`.

## Files

- `backend/experiments/runner.py` — `_select_action` (line 207),
  runner-level `_CONSUMER_TYPES`, `_CRITICAL_TYPES`, `_dispatch_action`.
- `backend/models/rl_agent.py` — `_valid_actions_mask` (line 400).
- `backend/experiments/dqn_training.py` — `train_dqn`.
- `backend/experiments/stage43_validation.py` — 10-seed validation
  harness + fingerprints.
- `backend/tests/test_stage43_integration.py`,
  `backend/tests/test_stage43_rng_isolation.py` — causal tests.
