# Metrics Reference

## IEEE 1366-2012

All functions live in `backend/metrics/ieee_1366.py`.  They are pure
projections — no global state — so you can call them with synthetic
arrays for unit tests or with real telemetry for benchmark reports.

| Index | Symbol | Units | Definition (IEEE 1366-2012) |
|---|---|---|---|
| SAIFI | System Average Interruption Frequency Index | int/customer | ΣN_i / N_T |
| SAIDI | System Average Interruption Duration Index | min/customer | Σr_i N_i / N_T |
| CAIDI | Customer Average Interruption Duration Index | min | SAIDI / SAIFI |
| MAIFI | Momentary Average Interruption Frequency Index | int/customer | ΣN_MI / N_T |
| ASAI  | Average Service Availability Index | unitless | (ΣN_i × 8760 − Σr_i N_i) / (ΣN_i × 8760) |
| ASIDI | Average System Interruption Duration Index | min | Σ(k_i · r_i) / K_T |
| ASIFI | Average System Interruption Frequency Index | int | Σ(k_i · N_i) / K_T |
| ENS   | Energy Not Served | MWh | ΣP_k · outage_hours_k |
| AENS  | Average ENS per customer | MWh/customer | ENS / N_T |
| ACCI  | Average Customer Curtailment Index | MWh/customer | AENS |

Where:
- `N_i` = number of customers experiencing interruption `i`
- `r_i` = restoration time for interruption `i` (minutes)
- `N_T` = total customers served
- `N_MI` = momentary interruptions
- `k_i` = connected kVA impacted
- `K_T` = total connected kVA

## Grid KPIs (`backend/metrics/grid_kpis.py`)

- `voltage_stability_index(nodes)` ∈ [0, 1] — fraction of buses with
  V ∈ [0.95, 1.05] pu.
- `frequency_stability_index(nodes)` ∈ [0, 1] — fraction with
  f ∈ [49.8, 50.2] Hz.
- `renewable_penetration_pct(nodes)` ∈ [0, 100] — renewable /
  total generation.
- `battery_utilisation_pct(nodes)` ∈ [0, 100] — average SOC across
  storage nodes.
- `system_reliability_index(nodes)` ∈ [0, 1] — composite (V-stab +
  f-stab + not-failed) / 3.

## Forecast metrics (`backend/metrics/forecast_metrics.py`)

- `mae(actual, predicted)` — mean absolute error.
- `rmse(actual, predicted)` — root mean squared error.
- `mape(actual, predicted)` — mean absolute percentage error
  (zero actuals skipped).

## Registry

The decorator `@metric("name")` registers a function in the global
registry.  `compute_all(payload)` runs every registered metric
over the same payload dict and returns `{name: float}`.  Robust to
exceptions — failing metrics return `NaN` instead of breaking the
run.

## Digital twin metrics

- `DigitalTwin.health` ∈ [0, 1] — remaining life; Arrhenius ageing.
- `DigitalTwin.failure_probability` ∈ [0, 1] — derived from health.
- `DigitalTwin.age_hours` — cumulative operating time.
- `DigitalTwin.temperature` (K) — hot-spot estimate.

## IEEE 1366 vs the per-step proxy in `SimulationEvaluator.summary()`

The evaluator produces `ieee_saifi`, `ieee_saidi`, etc. by
treating each failed step as one interruption of 1 minute.  This
is a **coarse proxy** suitable for short benchmark runs
(≤1000 steps).  For larger runs, compute IEEE 1366 over the real
per-customer arrays using the exported functions.
