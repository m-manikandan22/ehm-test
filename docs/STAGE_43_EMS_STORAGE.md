# STAGE 43 — EMS & Hybrid Storage (Repairs 8 + 9)

Status: DONE
Evidence: `test_ems_cycles_when_enabled`, `test_ems_cycles_when_disabled`,
`test_no_ems_differs_from_full_stack`, `test_action_effect_persists_across_step`
(SOC drain survives `grid.step()`).

## What was wrong (Stage-42.5 findings 10, 13)

* A **fresh** `EnergyManagementSystem(use_pypsa=False)` was constructed on
  every step, so the EMS never saw its own storage SOC drain or dispatch
  history — it could not have a persistent physical effect.
* `enable_storage` was never read anywhere: the `enable_storage` ablation
  rows were identical to full runs.

## The repair

* **Persistent EMS** (`info_flow._run_ems(..., ems_instance=...)`): one
  `EnergyManagementSystem` per run, created before the loop, reused every
  step. SOC drains and dispatch history carry over between steps.
* **`enable_storage` gates storage actions**: when storage is disabled,
  controller actions 1 (use_battery) and 2 (use_supercapacitor) are no-ops in
  `run_single`; the EMS's storage dispatch is likewise gated. Battery/supercap
  SOC trajectories therefore differ between `enable_storage` ON and OFF —
  measurable physical state, not flags.
* `test_action_effect_persists_across_step` proves the SOC drain from a
  storage action survives `grid.step()` — storage state is real state.

## Honest assessment

* EMS ON vs OFF provably differ in EMS cycles (counters) and in SOC
  trajectories; the EMS's dispatch genuinely runs against persistent storage.
* In the 10-seed validation, aggregate ENS is dominated by FLISR restoration
  and fault scheduling (actions 0–3 are stability actions that do not change
  failed/isolated status, and ENS is charged against would-be load — Repair
  10), so EMS-driven ENS deltas are within noise. The gate claims the EMS
  path is real, persistent and causally tested; "EMS improves ENS" is not
  claimed.
