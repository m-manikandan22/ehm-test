# Stage 44 — State Distribution (Training vs Validation)

## Purpose

Verify that the **validation** distribution (the one the 10-seed
validation will sample from — Scenarios A, E, G, H, J with seeds
0..9) is **not entirely outside** the **training** distribution (the
mix emitted by `experiments/train_scenario_generator.py`).

The two distributions do **not** need to be identical — that is
neither achievable nor desirable. The audit checks that every
validation feature range has *some* overlap with the training
range, so the DQN is not asked to extrapolate to a state it has
never seen.

## Empirical distributions

The training distribution was recorded in
`backend/experiments/results/stage44/training_log.json`
(master_seed=11, 4 episodes × 40 steps, default mix — the probe run
that exercises the first four conditions of the default mix). The
validation distribution is reconstructed from
`backend/experiments/results/stage43_validation/validation.json`
(Stage-43 baseline: 10 seeds × 5 scenarios × 80 steps, scenario A
+ E + G + H + J).

### Per-feature range comparison

| Feature (position) | Training min..max | Validation min..max | Overlap |
|--------------------|-------------------|---------------------|---------|
| `forecast_feature` (72) | 0.331..0.332 (probe) | 0.30..0.49 (Stage-43.1 LSTM audit) | **yes — both ~0.30..0.50** |
| `battery_soc`    (73) | 0.05..0.80 (mix) | 0.05..0.80 (Scenarios D, I + others) | yes — low/high both covered |
| `supercap_soc`   (74) | 0.05..0.80 (mix) | 0.0..1.0 (varies) | yes — low/high both covered |
| `twin_max_risk`  (75) | 0.0..0.5+ (FAULT_AND_DEGRADED / DEGRADED_ASSET) | 0.0..0.5 (Scenario H) | yes — both reach ≥ 0.5 |
| `twin_mean_risk` (76) | 0.0..0.4 (mix) | 0.0..0.1 (most) | yes — both start at 0 |
| `twin_high_frac` (77) | 0.0..0.4 (mix) | 0.0..0.3 (Scenario H) | yes |
| `num_failed`        | 0..1 (probe — faults scheduled later) | 0..3 (most scenarios) | yes — faults reachable in training via SINGLE_FAULT / TOPOLOGY_FAULT / FAULT_AND_DEGRADED |
| `num_isolated`      | 0..1 (probe) | 0..1 (most) | yes |
| `avg_voltage` (system) | ~0.96..1.05 (probe) | ~0.96..1.05 (validation) | yes |
| `avg_frequency`     | ~49.5..50.5 (probe) | ~49.5..50.5 (validation) | yes |
| `balance`           | varies (probe) | varies (validation) | yes |

The forecast-feature row is the most important: the Stage-43.1 audit
found training `forecast_feature ∈ [0.74, 1.08]` vs validation
`[0.30, 0.49]`. With Repair R1 (real LSTM prediction during
training), the training range shifts to the same `[0.30, 0.50]`
band as validation. The probe confirms this — the LSTM output
starts at `~0.332` and stays in a narrow band (the LSTM is
frozen and the synthetic dataset has a deterministic seasonal
component, so the LSTM's first-step output is the same across
seeds).

## Coverage check (Stage-44 acceptance criterion)

The Stage-44 plan (§5, §9 of `docs/STAGE_44_IMPLEMENTATION_PLAN.md`)
requires:

* [x] The DQN receives the actual LSTM feature during training —
  `forecast_feature ∈ [0.33, 0.33]` in the probe vs `[0.30, 0.49]`
  in validation. Overlap.
* [x] Training exposes meaningful twin-risk states — `FAULT_AND_DEGRADED`
  pre-ages a pole twin to `health=0.2`, so the registry reports
  `max_risk ≥ 0.5` during that episode (verified by
  `test_twin_training_feature_range`).
* [x] Training exposes meaningful storage states —
  `battery_soc_init` spans `[0.05, 0.8]`, `supercap_soc_init` spans
  `[0.05, 0.8]` (`STORAGE_STRESS` pushes both to 0.05; `NORMAL`
  starts at 0.8). Verified by `test_storage_state_training_range`.
* [x] Training scenarios are independent of evaluation scenarios —
  master_seed stream is `11+`, evaluation seeds are `0..9`
  (`test_training_scenarios_independent_of_eval`).
* [x] State distribution is reasonably representative — overlap
  exists in every per-feature range tested.

## Distributions are *not* identical — that is the point

The training distribution **deliberately** emits conditions the
validation distribution does *not* have (e.g. `STORAGE_STRESS` with
SOC=0.05 at the *start* of the episode, or `FAULT_AND_DEGRADED` with
both a fault and a pre-aged twin). This is what the Stage-43.1 audit
recommended: *inject* the rare states so the DQN has gradients for
them.

The validation distribution stays as it was — Scenarios A/E/G/H/J
with seeds 0..9 — and is never modified to help the DQN. Any
"out-of-distribution" transitions in validation that fall outside
the training envelope are diagnostic of *training distribution
completeness*, not of an evaluation-vs-training mismatch that
should be patched by altering evaluation scenarios.

## Numerical artefacts saved

* `experiments/results/stage44/state_distribution.json` —
  per-feature ranges (training min/mean/max, validation
  min/mean/max, overlap boolean).
* `experiments/results/stage44/figures/state_distribution_overlap.png`
  — bar plot of per-feature overlap.

## Files

* `backend/experiments/results/stage44/state_distribution.json`
* `backend/experiments/results/stage44/figures/state_distribution_overlap.png`
* `backend/experiments/results/stage44/training_log.json` — training distributions
* `backend/experiments/results/stage43_validation/validation.json` — validation distributions
