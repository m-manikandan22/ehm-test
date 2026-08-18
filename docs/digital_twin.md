# IEEE 13-Bus Digital Twin

## Status — what is and isn't validated

The EHM project ships a **construction-time digital twin of the IEEE 13-bus
test feeder** (IEEE PES Distribution System Analysis Subcommittee, 1992).
The twin is wire-compatible with the existing `SmartGrid` Python class, so
any EHM logic that runs on the hand-crafted 49-node topology also runs on
the IEEE 13-bus feeder without code changes.

**Validated:** the network topology, per-line impedance table, and bus
loading values match the IEEE PES reference document. The DC power-flow
overlay on this topology matches a pandapower DC-PF reference run within
1e-3 radians (see `experiments/ieee13_validation.py`).

**Not validated, simulation-based:**
- The failure-risk indicator (`failure_probability`, `failure_risk_indicator`)
  in the per-asset twin is a heuristic function of `health` with a piecewise
  linear step at `health = 0.4`. It is **not** a calibrated probability model;
  the Arrhenius thermal-ageing kernel uses documented engineering constants
  but has not been trained on empirical asset lifetime data. Use it as a
  relative ranking signal ("high vs low risk") rather than a calibrated
  probability statement.
- The "predict_failure" horizon projection is a linear extrapolation of
  the last 8 health samples. It is sensitive to noise and should not be
  read as a forecast.

For a publication-grade validation we would need: (1) a dataset of
recorded transformer outages with known covariates, (2) calibration of
the ageing kernel parameters against that dataset, and (3) out-of-sample
ROC/PR curves. None of these exist in the EHM project today.

## Usage

```python
from simulation.ieee13 import build_ieee13, get_ieee13_metadata

grid = build_ieee13()
print(f"Buses:   {len(grid.nodes)}")
print(f"Lines:   {len(grid.graph.edges)}")
grid.update_power_flow()           # DC power flow overlay
result = grid.update_ac_power_flow()  # AC power flow (requires pandapower)
```

## What's modelled

| Element        | Implementation                                              |
|----------------|-------------------------------------------------------------|
| Buses          | 13 nodes at 4.16 kV, layout mirrors the IEEE reference     |
| Source         | Bus 650 with 1.5 MW dispatchable headroom                   |
| Lines          | 13 segments with per-unit impedance on a 5 MVA base         |
| Loads          | 8 spot loads (kW/kVAR) + 2 distributed, per IEEE spec      |
| DG             | 100 kW PV at bus 675                                        |
| Regulator      | 650↔632 represented as a small series impedance (tap dynamics deferred) |
| Transformer    | 633↔611 step-down                                            |
| Tie switch     | 684↔680 (starts open; closed by FLISR during restoration) |
| Cap banks      | Stubs 634, 652, 692 with zero load (reactive only)         |

## Power-flow regimes

The `SmartGrid` class supports two power-flow regimes over the same
topology:

- **DC power flow** (`update_power_flow`, always available): linear
  approximation. Computes per-bus voltage angle, per-line MW, and KCL
  residuals. Voltage magnitudes are forced to 1.0 pu.
- **AC power flow** (`update_ac_power_flow`, requires `pandapower`):
  Newton-Raphson solve on the Y-bus. Computes per-bus voltage magnitude
  and angle, per-line MW and MVAR, and per-bus reactive injection.

AC PF is added in `simulation/ac_power_flow.py`. See `power_flow.md` for
the document-limitations list.

## What's NOT modelled (deferred)

- **Regulator/transformer tap changer dynamics.** Treated as fixed
  series impedance; auto-tap behaviour would require discrete-control
  logic on top of the AC PF solver.
- **Switching transients.** Tie switch 684↔680 is the only controllable
  switch; close/open actions are simulated atomically.
- **Three-phase unbalanced AC PF.** The current AC solver is a balanced
  positive-sequence model. A full three-phase AC PF would require a
  per-phase Y-bus and a different Newton-Raphson formulation.

## Why the IEEE 13-bus feeder matters

The IEEE 13-bus feeder is the smallest *non-trivial* test feeder: it has
unbalanced loading, voltage regulators, a delta-wye transformer, a normally-
open tie switch, and two capacitor banks. By validating EHM on this feeder
in addition to the 49-node EHM grid, reviewers can compare EHM's FLISR
restoration paths against published OpenDSS / GridLAB-D / Matpower results
without having to map between naming conventions.
