# Stage 43 — Scenario Validation

## Five required scenarios (per spec §19)

| Label | Profile | Fault count | Total steps |
|-------|---------|-------------|-------------|
| A | nominal | 3 | 50 |
| E | extended faults | 5 | 60 |
| G | storm + faults | 4 | 60 |
| H | degraded assets + fault | 4 | 50 |
| J | cascading faults | 6 | 80 |

Definitions live in `backend/experiments/scenario_matrix.py`.

## Ten seeds

`runner.py::run_experiment(seeds=10, ticks=..., faults_per_run=...)` —
seeds 0..9. `stage43_validation.py::run_validation` defaults to
`N_SEEDS = 10`.

## Pairing fingerprint contract

`run_single()` emits four fingerprints in the result dict
(`runner.py:778-781`, `_environment_fingerprints`):

- `grid_hash` — topology + per-node `node_type` hash.
- `demand_hash` — per-node base-load × `demand_multiplier`.
- `renewable_hash` — per-node base-generation ×
  `renewable_multiplier` for `generator_solar` / `generator_wind`.
- `fault_hash` — sorted `(target, timestep, duration)` of the scenario's
  fault plan.

Every (scenario, seed) run for any controller must show identical
fingerprints. The Stage-43 10-seed validation summary
(`experiments/results/stage43_validation/summary.md`) confirms
**ALL PAIRS MATCH**.

## Tests

- `test_paired_controllers_share_environment` (Stage-43 RNG isolation
  tests).
- `test_scenario_*_multiplier_*_persists` (Stage-42 framework tests).
- `test_fingerprints_*` (Stage-43 framework tests).

## Files

- `backend/experiments/scenario_matrix.py` (ScenarioSpec).
- `backend/experiments/runner.py::_environment_fingerprints` (line
  832).
- `backend/experiments/stage43_validation.py::summarize` (pairing
  integrity check).
