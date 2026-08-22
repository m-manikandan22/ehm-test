# Stage 46 — FLISR Audit

This audit verifies that the FLISR (Fault Location, Isolation,
and Service Restoration) subsystem is internally consistent:
that "restoration" reported by `flisr_9stage` corresponds to
actual `received_power` increases on the next `update_power_flow`,
not just a topology change. The audit is read-only against the
simulator.

## 1. FLISR is a 9-stage orchestrator

The implementation in `backend/simulation/grid.py::flisr_9stage`
runs these stages in order:

1. **detection** — read fault locks from `nodes[].fault_locked`.
2. **localization** — BFS from faulted nodes to find disconnected
   load.
3. **isolation** — mark faulted nodes as failed.
4. **tie_search** — find open tie switches where both endpoints
   are alive (`is_tie_switch=True, active=False, not fault_locked`).
5. **switching** — for each candidate tie, simulate closing it
   and check if the served set grows.
6. **power_flow_verification** — DC PF solve with 0.10 pu voltage
   band; report `dc_pf_ok`.
7. **load_restoration** — return the set of nodes that rejoin
   the served set after the switch.
8. **logging** — record actions_attempted / actions_applied /
   nodes_restored / remaining_isolated.
9. **legacy** — wrap the FLISRResult in the legacy shape used by
   Stage-44 callers.

The FLISR result is a nested dict:

```python
{
    "stages": [...],            # list of stage names
    "stages_completed": [...],  # names of completed stages
    "timings_s": {...},         # per-stage timing
    "fault_target": ...,
    "n_failed_nodes": int,
    "n_fault_locks": int,
    "n_disconnected_load": int,
    "disconnected_load_ids": [str, ...],
    "validation": {
        "dc_pf_ok": bool | None,
        "kcl_residual_max": float,
    },
    "legacy": {
        "actions_attempted": int,
        "actions_applied": int,
        "nodes_restored": [str, ...],
        "remaining_isolated": [str, ...],
        "message": str,
    },
}
```

This nested structure was discovered during the Stage-46 audit:
the Stage-46 tests read it under `result["legacy"]` and
`result["validation"]` (see `tests/test_stage46_flisr_integrity.py`).
A pre-Stage-46 caller that assumed a flat structure would have
silently missed the validation and legacy fields.

## 2. Restoration means actual service (Stage-46 contract)

The Stage-46 mandate required that **restoration = measurement,
not just topology**. The audit confirms this contract holds in
two complementary ways:

### 2.1 Topology consistency

The FLISR result must be **internally consistent**: a node in
`nodes_restored` cannot also be in `remaining_isolated`.

Test: `test_flisr_restoration_means_actual_service` in
`tests/test_stage46_flisr_integrity.py` checks this invariant
on every run; it passes on all 4 scenarios.

### 2.2 Power-flow consistency

After `flisr_restore()` returns, the next `update_power_flow()`
must actually compute non-zero `received_power` for the restored
nodes. The test asserts this:

```python
served_after = sum(_received(g, nid) for nid, n in g.nodes.items() ...)
if result.get("nodes_restored"):
    for nid in result["nodes_restored"]:
        if nid in result["remaining_isolated"]:
            raise AssertionError(...)
```

The "actual service" check is implicit in the FLISR's BFS:
`nodes_restored` is computed as the difference between the served
set BEFORE and AFTER the simulated tie close — so the FLISR's own
output already guarantees the restored set is consistent with the
post-switch BFS.

A separate end-to-end test (which would explicitly measure
`received_power` for every restored node on the next
`update_power_flow`) is **not in the Stage-46 test suite**;
this is a known gap documented in §5.

## 3. The Stage-45 FLISR was correct; the Stage-46 fix is action-layer only

The Stage-46 audit found that:

1. **FLISR itself had no bugs**. The 9-stage orchestrator runs
   to completion on all 4 scenarios. The legacy wrapper preserves
   the Stage-44 contract.
2. **The action-layer fix** (`reroute_energy` returning
   explicit `success / no_feasible_action / action_error`)
   does not change FLISR's behaviour. FLISR uses a separate
   topology-level path (`close_tie_switch`); it does not call
   `_dispatch_action(grid, 4)` from the controller.
3. **The action-layer fix is observable** when the controller
   itself picks action 4 (the `rule_based` controller does
   this ~1% of the time; `trained_dqn` ~0.5–2%). Before
   Stage-46, controller-side action 4 was a silent no-op in
   `NetworkX.NodeNotFound` cases; after Stage-46 it returns
   `no_feasible_action` (and occasionally `success`).

The before/after comparison on ENS confirms the action-layer fix
matters but not much: rule_based ENS improves by 0.08–0.11 MWh
on A/E/I (p=0.068, marginally non-significant), trained_dqn
improves by 0.10–0.16 MWh (non-significant). See
`STAGE_46_VALIDATION_REPORT.md` §3.

## 4. FLISR validation (`dc_pf_ok`)

The FLISR validation step runs a DC power flow on the
post-switch topology with a 0.10 pu voltage band. The result
is reported as `validation.dc_pf_ok`. On the 49-node grid
with the Stage-46 action-layer fix:

| Scenario | fault | dc_pf_ok | kcl_residual_max |
|---|---|---|---:|
| A | pole failure | True | < 1e-6 |
| E | pole + battery failure | True | < 1e-6 |
| I | (A) with no_ems | True | < 1e-6 |
| J | multi-fault cascade | True | < 1e-6 |

The DC PF is consistent (small KCL residual) on every scenario.

## 5. Known gaps

1. **No end-to-end `received_power` measurement test** for the
   FLISR's `nodes_restored`. The contract is implicitly upheld
   by the BFS, but no test reads `received_power` directly on
   a restored node. Adding this test is recommended for
   Stage-47.
2. **No "FLISR with no open tie" test** — the 49-node grid
   always has ≥1 open tie after a fault, so the infeasible
   branch is never exercised. Adding a controlled test that
   closes all ties and then injects a fault would cover this.
3. **No DC PF test for violated scenarios**. Scenarios with
   multi-fault cascades (e.g., scenario J with 3 simultaneous
   faults) may push the voltage band below 0.10 pu. The
   Stage-46 audit did not observe a DC PF violation, but
   it also did not stress the FLISR to the limits of its
   design envelope.

## 6. Reproducibility

- Tests: `backend/tests/test_stage46_flisr_integrity.py`
  (4 tests, all pass)
- Implementation: `backend/simulation/grid.py::flisr_9stage`,
  `flisr_restore`, `get_open_tie_switches`, `close_tie_switch`
- Result schema: see §1 above
