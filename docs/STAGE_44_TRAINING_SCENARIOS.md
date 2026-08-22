# Stage 44 — Training Scenario Generator

## What this document covers

The Stage-44 training scenario generator is implemented in
`backend/experiments/train_scenario_generator.py`. It produces a
deterministic per-master-seed list of `TrainingScenario` records
that the Stage-44 DQN training loop
(`backend/experiments/stage44_dqn_training.py`) consumes — one
record per episode.

The Stage-44 mandate was: *the training distribution must be widened
so the DQN observes faults, high-risk twins, low SOC, and other
operating regimes; evaluation scenarios must remain untouched and
must be sampled independently of training scenarios.*

## Condition taxonomy

Nine engineering conditions are emitted, in this fixed order of
preference so that even short budgets (e.g. 4 episodes in the init
audit) see the rare-but-important states first:

| # | Condition | Demand | Renewable | Battery SOC init | Supercap SOC init | Faults | Pre-aged twin |
|---|---|---:|---:|---:|---:|---|---|
| 1 | `FAULT_AND_DEGRADED` | 1.0 | 1.0 | 0.5 | 0.5 | (45, POLE_PICK) | yes (health 0.2) |
| 2 | `SINGLE_FAULT`       | 1.0 | 1.0 | 0.6 | 0.6 | (40, AUTO_PICK) | — |
| 3 | `TOPOLOGY_FAULT`     | 1.0 | 1.0 | 0.6 | 0.6 | (35, AUTO_PICK) | — |
| 4 | `DEGRADED_ASSET`     | 1.0 | 1.0 | 0.7 | 0.7 | — | yes (health 0.25) |
| 5 | `STORAGE_STRESS`     | 1.2 | 0.8 | 0.05 | 0.05 | — | — |
| 6 | `NORMAL`             | 1.0 | 1.0 | 0.8 | 0.8 | — | — |
| 7 | `HIGH_DEMAND`        | 1.5 | 1.0 | 0.7 | 0.7 | — | — |
| 8 | `LOW_RENEWABLE`      | 1.0 | 0.2 | 0.7 | 0.6 | — | — |
| 9 | `GENERATION_DEFICIT` | 1.3 | 0.5 | 0.3 | 0.5 | — | — |

These are *engineering conditions*, not evaluation scenarios. They
describe a regime the DQN should encounter; the corresponding
evaluation scenarios (A–J) are *separate* and never copied.

## Sampling independence from evaluation

* `sample_training_scenarios(master_seed, n_episodes, ...)` builds an
  independent RNG via `utils.seeds.make_rng(master_seed)`. The
  default mix in `train_scenario_generator.py` weights the nine
  conditions with the *rarer-but-important* conditions appearing
  first; the chosen sequence is deterministic for a given
  `master_seed`.
* Evaluation scenarios are seeded by `0..9` in `scenario_matrix.py`;
  the Stage-44 training runs use `master_seed` in `[10, 11, 12, …]`
  (see `stage44_dqn_training.py::train_stage44_dqn`). Training
  scenarios never collide with evaluation seeds.
* `apply_training_scenario(grid, scenario)` mutates the grid at
  episode start: it sets `grid.demand_multiplier` /
  `grid.renewable_multiplier`, scales `hospital / industry /
  hospital_icu._base_load`, and overrides `battery_level` /
  `supercap_level` for the relevant nodes.
* Fault injection (`(t, AUTO_PICK)` or `(t, POLE_PICK)`) and
  `health_override` application are performed *during* the episode
  by the training loop, **not** baked in at scenario-apply time, so
  they remain observable in the state channel rather than silently
  disappearing before the first state read.

## Training scenario labels

`train_scenario_generator.py` produces labels of the form
`T_{CONDITION}_{ep_seed}` (e.g. `T_FAULT_AND_DEGRADED_11223`).
These are intentionally distinct from the evaluation labels
(`A_..`, `B_..`, `A_simult`, `A|d=1.00|r=1.00|soc=na`) so the two
streams can be distinguished in logs. The test
`test_training_scenarios_independent_of_eval` enforces the
separation.

## What the generator does NOT do

* It does **not** import `experiments/scenario_matrix.py` and never
  reads evaluation scenario specs.
* It does **not** modify `scenario_matrix.py`.
* It does **not** import evaluation fingerprints; training and
  evaluation fingerprints are unrelated.
* It does **not** inject *evaluation* faults — every fault is
  derived from the condition profile + the per-episode seed via
  `make_rng`.
* It does **not** apply post-step load shaping — the engineering
  condition is set once at episode start.

## Test coverage

| Test                                                      | Asserts                                                  |
|-----------------------------------------------------------|----------------------------------------------------------|
| `test_training_includes_faults_and_high_risk_twins`        | At least one SINGLE_FAULT + DEGRADED_ASSET + FAULT_AND_DEGRADED episode in a 24-episode sample. |
| `test_storage_state_training_range`                        | Battery SOC init spans `[0.05, 0.8]`, supercap SOC init spans `[0.05, 0.8]`. |
| `test_training_scenarios_independent_of_eval`             | Training labels never start with `A_`..`J_`; the master-seed stream is independent of evaluation seeds. |
| `test_twin_training_feature_range`                         | At least one health_override scenario produces a non-zero `twin_max_risk` after `_tick_twin_registry`. |

All four tests live in `backend/tests/test_stage44_alignment.py`.

## Files

* `backend/experiments/train_scenario_generator.py` — generator
* `backend/experiments/stage44_dqn_training.py::train_stage44_dqn` — consumer
* `backend/tests/test_stage44_alignment.py` — separation tests
* `docs/STAGE_44_STATE_DISTRIBUTION.md` — empirical training vs
  evaluation distribution comparison.
