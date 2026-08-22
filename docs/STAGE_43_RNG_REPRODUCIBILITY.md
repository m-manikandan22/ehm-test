# Stage 43 — RNG Reproducibility

## What is recorded

Per-run `run_single()` writes the following into the result dict
(runner.py:813-829):

```python
{
  "seeds": dict(stream_seeds),    # {environment, controller, training}
  "git_sha": _git_sha(),          # repo SHA, "no_git" if unavailable
  "environment_trace": [...],     # list of (load, gen) per step
  "fingerprints": {grid_hash, demand_hash, renewable_hash, fault_hash},
  ...
}
```

`stream_seeds` are derived from `master_seed` via
`utils.seeds.derive_stream_seeds`. `_git_sha()` is a best-effort
`git rev-parse HEAD` in the repo root.

## Reproducing a run

To reproduce a run exactly:

1. `git checkout <git_sha>`.
2. Re-seed with the recorded `seeds["environment"]` for the grid,
   `seeds["controller"]` for the random policy, `seeds["training"]`
   for the torch RNG (the DQN already loads the checkpoint so torch
   is re-seeded post-load).
3. Run the same `cfg` and `scenario` (`scenario.to_dict()` is in
   `result["scenario"]`).

The **scenario fingerprint** (`grid_hash`, `demand_hash`,
`renewable_hash`, `fault_hash`) is sufficient to prove the same
environment inputs across paired controllers; together with `seeds`
it is sufficient to reproduce a run byte-for-byte.

## Tests

- `tests/test_seeds.py::test_*` (Stage-42 framework, unchanged).
- `tests/test_stage43_integration.py::test_checkpoint_*` (Stage-43).
- `tests/test_stage43_rng_isolation.py::test_paired_*`.

## Files

- `backend/experiments/runner.py` — seed recording + fingerprint logic.
- `backend/utils/seeds.py` — seed derivation helpers.
