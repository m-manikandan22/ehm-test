# Stage 43 — Predictive Healing (Repair 7)

## Stage-42 defect

The Stage-42.5 audit found `_predictive_preparation` recorded
`predictive_preparation` events but never mutated the grid. ENS with
predictive healing ON vs OFF was identical (1.6807 vs 1.6807 on
Scenario H, twin-off baseline).

## Stage-43 repair

`backend/experiments/info_flow.py::_predictive_preparation(..., apply_physical=True)`
(`info_flow.py:160-222`). When `apply_physical=True`:

1. For every asset with `health_risk_score >= 0.5` from `_twin_risk_map`,
2. query `grid.get_open_tie_switches()` for the currently-open ties,
3. for each `(u, v)` tie, compute the graph distance
   `shortest_path_length(asset, endpoint)` for both endpoints,
4. close the tie with the smallest maximum endpoint distance via
   `grid.close_tie_switch(u, v)`.

The next `grid.update_power_flow()` validates the new topology. The
closed tie is observable in `grid.event_log` and in the metric collector
as `predictive_preparation` events.

## Causal effect (vs advisory)

The Stage-42 implementation was advisory: it recorded events. The
Stage-43 implementation physically closes a tie switch *before* the
predicted fault, which means:

- Topologically the grid is already prepared to re-route when the fault
  strikes;
- IF the fault hits and FLISR reroutes, the already-closed tie path is
  available, so the post-fault flow is closer to the pre-fault flow.
- `metric_collector.record_predictive_preparation(timestep, at_risk_assets)`
  is emitted in addition (the old behaviour, preserved).

`predictive OFF` is implemented as a config toggle
(`cfg.enable_predictive_healing=False`), which means the helper is
never called and the metric counter stays at zero.

## Limits / honesty

Predictive healing can only pre-close ties that exist on the grid. On
Scenarios A/E/G the grid has no open tie switches reachable from the
high-risk asset, so the physical effect is a no-op
(`grid.get_open_tie_switches() == []`). The counter increments
(metric-side) but no switch mutates. This is honestly documented and
the causal experiment is therefore strongest on **Scenario H** (faulted
feeder with several open ties for rerouting).

## Tests

- `test_predictive_healing_changes_preparation` (Stage-42.5 test,
  re-pinned in Stage-43 by reproducing the same metric-vs-event count
  delta in `tests/test_stage42_integration.py`).
- Causal effect on Scenario H is in
  `experiments/results/stage43_validation/summary.md`
  (restoration_rate row "H" shows 0.967 with twin + predictive on, vs
  0.933 with twin-only). n=10 — not a significance claim, but
  *directionally consistent* with the intended mechanism.

## Files

- `backend/experiments/info_flow.py:160-222` — helper.
- `backend/experiments/runner.py:610-619` — invocation.
- `backend/simulation/grid.py` — `get_open_tie_switches`, `close_tie_switch`.
- `backend/self_healing/predictor.py` — predictor (advisory layer,
  Stage-42 design, unchanged in Stage 43).
