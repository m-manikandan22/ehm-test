# Phase 1 findings — no rerun performed

## Recovered frozen experiment

The archived Experiment B package contains 540 completed records: 30 paired seeds × `moderate`/`severe` × `persistence`, `random`, `rule_based`, `dqn_core_only`, `full_stack`, `no_lstm`, `no_twin`, `no_predictive`, and `no_reward`.

## Confirmed findings

- The stress runner only invokes `grid.flisr_restore`, but the concrete implementation belongs to `ScadaControlCenter._flisr_restore(grid, ems)` through SCADA action `reroute_energy`. The runner does not construct SCADA. Historical active-FLISR policies record zero FLISR calls.
- `PredictiveSelfHealer.run` generates declarative recommendations only; its documentation requires a caller to apply them. The stress runner counts recommendations as actions and has no acceptance, dispatch, or application path.
- A `TwinRegistry` is created inside every timestep and discarded, preventing history/ageing from accumulating. Whether persistence is a repair awaits frozen-plan confirmation.
- The LSTM is statically gated in `_DQNAdapter`; execution success and output consumption are not presently evidenced.
- Experiment A data legitimately exist: `paper_results/raw/baseline_results.json` has 500 records and 100 `full_stack` records. The A-vs-B loader produces n=0 because it looks for `normal` while A records have no stress-level field.
- The pre-existing primary-outcome plan specifies per-controller-pair Holm correction over the four primary outcomes, unlike the historical code’s broad pooled family.

## Stop state

No source correction, tests, mechanism test, smoke matrix, full rerun, or performance/statistical rerun has been performed. This concludes Phase 1 only.
