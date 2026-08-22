# Stage 43 — Scenario Multipliers

## Spec

`STAGE_43_RUNTIME_CONTROL_FLOW.md` demands that **scenario
multipliers** must persist for the whole run instead of being
overwritten by `_apply_time_curves`.

## Mechanism in the runner

`run_single()` (runner.py:401-412) stores the multipliers on the grid:

```python
grid.demand_multiplier = float(_spec_demand_mult)
grid.renewable_multiplier = float(_spec_renew_mult)
```

For the consumer types whose load is **static** (hospital, industry,
hospital_icu) the runner also scales `node._base_load` once
before the loop. This is the persistent effect for those node types.

`_apply_time_curves` (in `backend/simulation/grid.py`, see Stage-43
diagnostics) then reads the multipliers from the grid per step and
applies them when computing the curve-scaled load and renewable output
of every node. (See `STAGE_43_SCENARIO_VALIDATION.md` for the runtime
test.)

## Stage-42.5 finding recap

In Stage-42 the multipliers were applied *once* at the top of the
loop and the resulting `node.load` was overwritten by the curves on the
next `grid.step()`. Therefore scenarios A–J differed in their
**fault schedule** but not in their **demand/renewable profile**.

## Stage-43 fix verification

- `test_high_demand_multiplier_persists` (Stage-42 framework tests +
  Stage-43 `tests/test_scenario.py`): with `demand_multiplier=1.5`,
  an alive house's load is ~1.5× the base profile across all steps
  (within rounding).
- `test_low_renewable_multiplier_persists`: with
  `renewable_multiplier=0.2`, an alive `generator_solar` /
  `generator_wind` is ~0.2× the base profile across all steps.

## Files

- `backend/experiments/runner.py:401-412` — multiplier storage.
- `backend/simulation/grid.py` — `_apply_time_curves` (curve-writer,
  reads multipliers).
- `backend/experiments/scenario_matrix.py` — scenario spec definitions.
