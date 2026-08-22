# Stage 43 — Digital Twin Integration (Repair 6)

## Module under repair

`backend/digital_twin/twin.py`, `backend/digital_twin/twin_registry.py`.
Stage-42 wiring glue: `backend/experiments/info_flow.py`
(`_build_twin_registry`, `_tick_twin_registry`, `_twin_risk_map`,
`_pre_age_twins`).

## State vector insertion

Every step that has a twin registry (i.e. `cfg.enable_twin=True` or
predictive healing is on) the runner computes:

```python
_risk_vals = list(_twin_risk_map(_twin_registry).values())
_twin_features = {
    "max_risk":   float(max(_risk_vals)),
    "mean_risk":  float(sum(_risk_vals) / len(_risk_vals)),
    "high_frac":  float(sum(r >= 0.5 for r in _risk_vals) / len(_risk_vals)),
}
```

These are then handed to `build_extended_state` at positions 75, 76, 77
(`rl_agent.py:115-122`):

```python
twin_max_risk,
twin_mean_risk,
twin_high_frac,
```

## Conservative terminology

Per `main.md` Stage 10, the value is named `health_risk_score` because
no calibration to real failure data exists. It is *not* a calibrated
failure probability. The Stage-42 assumption (linear extrapolation of
age over `health_age_score`) is unchanged. `health_aware_load_shift` (the
old Stage-42 hand-coded hint flag injected into `grid_state["system"]`)
has been **removed** from the DQN mask and now appears only as a rule-based
controller bias (see `STAGE_43_RUNTIME_CONTROL_FLOW.md` §3).

## Tests

`tests/test_stage43_integration.py`:

- `test_twin_health_reaches_decision_state` — vary `twin_max_risk` and
  verify the policy network's Q-values for the same grid state change
  (Δ > 1e-6). This proves the twin features are real inputs to the
  network, not just metadata.
- `test_twin_health_can_change_decision` — under Scenario H (a
  pre-aged asset + a fault), `rule_based` with `enable_twin=True`
  produces different action counts than `rule_no_twin` (the twin is
  toggled off), proving the twin's risk assessment reaches the rule
  policy.

## What stage-43 proved and did not

Proved:

- Twin risk features reach the DQN decision input (state-vector test).
- The twin risk assessment changes the rule_based controller's
  behaviour in a controlled paired run (Scenario H).

Did not prove:

- That the trained DQN policy (10-seed validation) actually *uses*
  those features to discriminate. The validation shows
  `trained_dqn` collapsing to a single action regardless of twin
  state, so no per-twin discrimination is observed in the validation
  results. This is honestly labelled in `STAGE_43_RL_CONTRIBUTION.md`
  and the Stage-43 completion report.

## Files

- `backend/digital_twin/twin.py`, `backend/digital_twin/twin_registry.py`.
- `backend/experiments/info_flow.py` (twin helpers).
- `backend/experiments/runner.py:585-598` (per-step feature reduction).
- `backend/models/rl_agent.py::build_extended_state` (positions 75-77).
