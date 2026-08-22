# Stage 44 — Digital-Twin Training Alignment

## Stage-43 standing concern

Stage-43 trained on a clean grid; the digital-twin registry's
`max_risk` stayed at 0.0 across every training transition. The
trained network's `twin_max_risk` channel at positions 75–77 saw
the constant tuple `(0.0, 0.0, 0.0)`. Evaluation, particularly
Scenario H (pre-aged twin + fault), reached `max_risk` of 0.5.
The two distributions did not overlap
(`docs/STAGE_43_1_TWIN_TRAINING_ALIGNMENT.md`).

## What Stage-44 changes

`backend/experiments/stage44_dqn_training.py` ticks the twin
registry every step (mirroring the evaluation harness) and reads
its feature vector (`max_risk`, `mean_risk`, `high_frac`) into the
network's extended state. The training scenario generator
(`train_scenario_generator.py`) injects:

* **`DEGRADED_ASSET`**: pre-ages a non-critical pole to health 0.25
  so the twin registry reports `max_risk` ~ 0.5.
* **`FAULT_AND_DEGRADED`**: combines the pre-ageing with a fault on
  the same pole — exercises the high-risk + fault interaction.
* **`STORAGE_STRESS`**: starts the grid with empty batteries +
  supercaps so the network sees low SOC.

The pre-ageing is applied via `experiments.info_flow._pre_age_twins`
(Stage-43 wiring) so the registry is the same code path as
evaluation.

## Health state at timestep t uses only past information

The pre-ageing is applied **once at episode start** — it sets
`health` on the twin before the first step. From that point on,
the twin's `health_risk_score` evolves via the registry's own
tick (`registry.sync(grid, dt_hours=1.0)`), which uses only the
current and past grid state. There is no future-information leak.

## What is not changed

* The twin registry (`digital_twin.twin_registry.TwinRegistry`)
  is unchanged.
* The pre-ageing helper (`info_flow._pre_age_twins`) is unchanged
  from Stage-43.
* The evaluation scenarios' health_override maps (Scenario H) are
  not copied into training.

## Files

* `backend/experiments/stage44_dqn_training.py` — twin wiring.
* `backend/experiments/train_scenario_generator.py` — DEGRADED_ASSET
  + FAULT_AND_DEGRADED conditions.
* `backend/experiments/info_flow.py` — `_pre_age_twins`,
  `_twin_risk_map`, `_tick_twin_registry`.
* `backend/tests/test_twin_training_feature_range.py` — feature-range
  verification test.
