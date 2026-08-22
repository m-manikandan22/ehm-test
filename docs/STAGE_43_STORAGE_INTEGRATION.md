# Stage 43 — Hybrid Battery + Supercapacitor Storage

## Division of roles (per `main.md` Stage 8)

- **Battery** = sustained energy, lower power density, higher energy
  density, used for hour-scale balancing and renewable integration.
- **Supercapacitor** = high power density, lower energy density, used
  for short-duration transient support.
- **Hybrid** = coordinated dispatch where the slow resource (battery)
  and the fast resource (supercap) operate on different time-scales
  within the same horizon.

## What the model implements

- Battery + supercap nodes exist as either:
  - `house` nodes that *embed* a small battery and/or supercap, or
  - dedicated `storage_bat_*` / `storage_sc_*` nodes attached to
    transformer feeders.
- Action 1 (`use_battery`) discharges 0.2 MW from each energised
  battery-backed node with `battery_level > 0.2`.
- Action 2 (`use_supercapacitor`) discharges 0.1 MW from each energised
  supercap-backed node with `supercap_level > 0.1`.
- Action 1 and 2 are skipped (Stage-43 physical-validity guard) when a
  node is failed or isolated.

## Limits / honesty

- Power limits (charge / discharge) exist on the node level but are
  *not* explicitly used inside `_dispatch_action` (which selects
  fixed 0.2 / 0.1 MW). This is documented as Stage-43 simplification;
  it does **not** claim dynamic power-limit enforcement.
- Frequency / voltage support is *not* modelled at the level of
  controller-deployed reactive compensation. The EMS path is the only
  place that has voltage-aware dispatch, and even there it is the
  Stage-42 threshold-gated simplification.
- Energy efficiency is implicit (efficiency factor in
  `node.use_battery`/`use_supercapacitor`) but not surfaced in the
  published metric. The metric collector records SOC at every step.

## Causal tests

- `test_action_effect_persists_across_step` — battery drain survives
  `grid.step()`.
- `tests/test_metrics_*` (Stage-42) — battery / supercap SOC are
  observable per node per step.
- `tests/test_run_hybrid_storage.py` — Stage-42 experiment reproduces
  the storage-on-vs-off metric delta.

## Files

- `backend/simulation/node.py` — `use_battery`, `use_supercapacitor`,
  `battery_level`, `supercap_level`.
- `backend/experiments/runner.py::_dispatch_action` line 175-192.
- `backend/simulation/ems.py` — storage-aware dispatch.

## Status

**SIMULATION-VALIDATED.** No claim of physical hardware validation.
