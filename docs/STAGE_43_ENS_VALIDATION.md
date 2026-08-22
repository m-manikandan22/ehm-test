# Stage 43 — ENS Validation (Repair 10)

## Stage-42.5 finding

Failed / isolated nodes' loads are frozen (`_apply_time_curves` and
`node.step` skip them). The Stage-42 `MetricCollector.record_step()`
charged ENS as `load * (1/60)` even for failed/isolated nodes.

Consequence: a controller whose action happens to **deflate** a frozen
load could "reduce" ENS without restoring service. That is the
mechanism behind random-baseline outperforming the rule-based
controller on ENS in Stage-42 (ENS 0.2374 vs 0.5444 on the same seed).

## Stage-43 repair

`grid.would_be_load(node)` returns the baseline load the node would
have had at this step **had it not been failed/isolated** — it uses
`node._base_load` and the current grid multipliers (`demand_multiplier`,
the per-step curve factor stored under `grid._curve_*`).

`MetricCollector.record_step()` uses `grid.would_be_load(node)` for the
ENS calculation; the actual `node.load` (which may be deflated by a
controller) is **not** used for ENS charging.

## Tests

`tests/test_stage43_integration.py`:

- `test_ens_counts_unserved_energy_correctly` — failed node's ENS
  contribution equals `would_be_load / 60`, even when the actual
  `node.load` is deflated to 0.0001.
- `test_would_be_load_ignores_controller_deflation` — `would_be_load`
  is invariant to `node.load` mutations.

## What this changes vs Stage-42 numbers

All Stage-43 ENS numbers come from the repaired definition. Stage-42
ENS numbers were an artefact of the old definition; they are not
re-stated here. The Stage-43 10-seed validation
(`experiments/results/stage43_validation/summary.md`) reports ENS
under the repaired definition.

## Files

- `backend/simulation/grid.py` — `would_be_load` accessor.
- `backend/experiments/research_metrics.py` — `record_step` ENS path.
