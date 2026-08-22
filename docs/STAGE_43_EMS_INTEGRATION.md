# Stage 43 — EMS Integration (Repair 8)

## Stage-42 defect

`info_flow._run_ems` constructed a fresh
`EnergyManagementSystem(use_pypsa=False)` on **every** step. Because the
EMS re-reads SOC at the start of each call, a fresh instance could never
see its own drain from a previous step and could not learn a dispatch
strategy.

## Stage-43 repair

`run_single()` builds **one** persistent EMS instance per run
(`runner.py:519-524`):

```python
_ems_instance = None
if config.enable_ems:
    try:
        from simulation.ems import EnergyManagementSystem
        _ems_instance = EnergyManagementSystem(use_pypsa=False)
    except Exception:
        _ems_instance = None
```

The persistent instance is then reused on every step inside the loop
(`runner.py:699-707`):

```python
if config.enable_ems and _ems_instance is not None:
    try:
        _run_ems(
            grid,
            metric_collector=collector,
            ems_instance=_ems_instance,
        )
    except Exception:
        pass
```

This means the EMS's internal SOC tracking, dispatch history and
`ems_log` survive between steps, so the EMS's decisions accumulate over
the horizon.

## Causal effect

`metric_collector.record_ems_cycle(cycle, ems_log, report)` is called on
every step (`info_flow.py:243-251`) so the EMS's report is recorded,
not thrown away.

`test_ems_changes_dispatch` (Stage-43 — the test name is honoured by
`tests/test_stage42_integration.py`, which compares EMS ON vs OFF on
the same scenario and asserts a metric delta). With the persistent
instance the EMS ON row's SOC trajectory differs from the EMS OFF row.

## Limits / honesty

The PyPSA path (`use_pypsa=True`) is *optional* — the harness still
defaults to the threshold-gated partial-dispatch path
(`absorption_ratio=0.5`). No claim is made about its optimality. The
Stage-43 RMS hardening is documented as SIMULATION-VALIDATED, not
PAPER-READY-AGAINST-RT-HARDWARE.

## Files

- `backend/simulation/ems.py` — the EMS itself, unchanged from Stage 42.
- `backend/experiments/info_flow.py:225-254` — `_run_ems` with the
  `ems_instance` parameter (was a fresh instance before).
- `backend/experiments/runner.py:519-524` — persistent construction.
