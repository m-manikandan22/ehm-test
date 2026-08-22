# Stage 45 — Implementation Plan

## Physics-Coupled Reliability Metric Audit

> **Status:** Drafted after Stage-44 PARTIAL — CONTINUE
> **Mandate:** §1 — Measure the physical consequences of
> controller decisions correctly.

## 1. Current metric architecture (as inherited from Stage-44)

```
┌──────────────────────────────────────────────────────────┐
│  Stage-44 metric loop (in stage44_validation.py §649–   │
│  682)                                                      │
│                                                            │
│  for each timestep:                                         │
│     grid.step()                                             │
│     grid.update_power_flow()                                │
│     for each house / industry / hospital node:             │
│         received = node.received_power                     │
│         baseline = node._base_load   (house only)          │
│                    or received     (industry / hospital)    │
│         served += received                                  │
│         baseline += would_be                                │
│     short = max(0, baseline - served)                       │
│     energy_not_served += short / 60.0   (≈ MWh)            │
│     n_violations += (any |V-1| > 0.10)                      │
│                                                            │
│  → returns {                                                │
│      energy_not_served_mwh, critical_load_interruption_    │
│      steps, total_customer_minutes_interrupted, voltage_   │
│      violation_count, restoration_rate, avg_restoration_    │
│      steps, battery_discharged_total, supercap_discharged  │
│      _total }                                               │
└──────────────────────────────────────────────────────────┘
```

## 2. Root cause of metric invariance (Stage-44 finding)

Stage-44 discovered (via empirical10-seed validation) that
`energy_not_served_mwh`, `total_customer_minutes_interrupted`,
`critical_load_interruption_steps`, and `voltage_violation_count`
are byte-identical across all 12 (controller, ablation) cells
within every (scenario, seed) group.

The root cause is **two-layered**:

### 2.1 Scenario-dimension limit (primary)

The Stage-43 scenario matrix (A, E, G, H, J) does not
include a **generation-deficit** scenario. Scenarios A/E/G/H
have no faults or only digital-twin faults (no physical
service interruption). Scenario J has heavy physical faults,
but the load nodes behind the faulted line are *physically
isolated* from the BFS sources — so the action policy
(reroute / battery / supercap) cannot deliver power across
the faulted line. All controllers receive identical
`received_power = 0` for the isolated sub-tree.

### 2.2 Storage-coupling gap (secondary)

When action 1 (`use_battery`) is dispatched, the runner calls
`node.use_battery(0.2)` on every house node. The method
correctly increases `node.generation = 0.2`. **However,
`_simulate_energy_flow` only treats generator / substation
nodes as BFS sources.** A house node with
`generation = 0.2` is not a source, so the surplus is
ignored by the BFS.

This is the *physical coupling gap*: storage discharge
*is computed*, but it is *not delivered* to downstream
load nodes because the BFS does not recognize house nodes
as sources.

### 2.3 Topology-coupling gap (tertiary)

`reroute_energy` calls `grid.reroute_energy()` which only
closes tie-switches. If the tie is already closed or if
no tie can re-energise the faulted sub-tree (because the
fault is on the only line), the action has no physical
effect. Stage-43 scenarios J / H rarely expose a
*re-enableable* sub-tree, so the action's contribution is
zero in practice.

## 3. Correct physical definition of served load

For each load node `L` (node_type ∈ {house, hospital,
industry, hospital_icu}) at every timestep `t`:

```
P_demand(L, t)  = L.load                    (set by _apply_time_curves)
P_served(L, t)  = min(L.received_power,
                      P_demand(L, t))       (post power-flow clamp)
P_unserved(L, t) = max(0, P_demand(L, t)
                          - P_served(L, t)) (non-negative)
```

**Constraints:**

* A failed node (`L.failed == True`) contributes `0` to
  served and `P_demand` to unserved for the duration it
  remains failed. Once the FLISR restores the node, the
  demand begins contributing again.
* An isolated node (`L.isolated == True`) contributes `0`
  to served (BFS did not reach it) and `P_demand` to
  unserved until the topology restores it.
* The controller **may not** artificially deflate
  `P_demand`. `shift_load` reduces `L.load` by a fraction;
  this is a *legitimate demand-response action* (per
  Stage-43 action catalogue §4). It IS accounted for in
  ENS because `P_unserved` is computed against the
  post-shift `P_demand`.

## 4. Correct physical definition of unserved load

```
P_unserved(t) = Σ_load_nodes L  P_unserved(L, t)
             = Σ_load_nodes L  max(0, P_demand(L, t)
                                       - P_served(L, t))
```

## 5. ENS calculation

```
ENS = Σ_t  P_unserved(t)  ×  Δt_hours
```

with `Δt_hours = 1/60` (1 simulation timestep = 1 minute by
Stage-43 convention).

**Units:** MW × h = MWh. **No double counting** because
P_unserved is computed per node per step and the sum is
across distinct load nodes.

## 6. CMI calculation

```
CMI = Σ_customers  max(0, T_restore(C) - T_interrupt(C))
            × 1 minute
```

where `T_interrupt(C)` is the first timestep at which
customer `C` had `P_unserved > 0` and `T_restore(C)` is the
first timestep at which `P_unserved(C, T_restore) == 0`.

A customer is one load node (house / industry / hospital /
hospital_icu). CMI is in customer-minutes, consistent with
IEEE 1366.

## 7. Critical-load interruption calculation

```
critical_load_interruption_steps
   = Σ_t  Σ_critical_loads  [P_unserved(C, t) > 0]
```

where `critical_loads = {C | C.node_type == 'hospital'
                               or C.node_type == 'hospital_icu'}`.

This is **not** derived from fault presence. It is derived
from the actual unserved-energy vector at each step.

## 8. Voltage-violation calculation

For each bus at every timestep:

```
if |V - 1.0| > 0.10:
    record a violation
```

**Project uses DC power-flow voltage proxy.** The voltage field
on GridNode is `node.voltage`, a scalar in [0, 1.05]. The
project documents this in `docs/STAGE_43_RUNTIME_CONTROL_
FLOW.md` §"Voltage reporting". **Limitations** of the
voltage proxy:

1. DC power flow computes angles only; the per-bus voltage
   magnitude is a proxy, not the AC PF solution.
2. The 0.10 pu band is a heuristic, not a regulatory
   standard (ANSI C84.1 allows 0.95–1.05 pu).

These limitations are documented in
`docs/STAGE_45_PHYSICS_COUPLING.md` §"DC PF limitations".

## 9. Restoration-time calculation

For each load node that experienced unserved energy:

```
T_restore(L) = first t at which P_unserved(L, t) == 0
             AND P_served(L, t) > 0
             AND L.failed == False
             AND L.isolated == False
```

Restoration time = `T_restore(L) - T_interrupt(L)`,
expressed in simulation timesteps. The Stage-45 metric
collector aggregates restoration time *per-load-node*,
not per-fault.

## 10. Required tests

### tests/test_stage45_ens_physical.py

* `test_ens_zero_when_grid_healthy` — no faults, no ENS.
* `test_ens_matches_unserved_load_sum` — fault a feeder,
  compute ENS from the P_demand − P_served accounting, and
  from the manual baseline; they match.
* `test_ens_storage_action_reduces_ens` — induce a
  generation-deficit scenario; compare ENS between a
  baseline (no action) and an action-1 (`use_battery`)
  policy. ENS must be lower under `use_battery` if
  storage is physically delivered (which the Stage-45
  source-broadening fix ensures).
* `test_ens_no_double_counting` — multi-load scenario,
  ENS equals the sum of per-node unserved energies.
* `test_ens_units_are_mwh` — output is `Σ MW × h = MWh`,
  not `MW × step`.

### tests/test_stage45_cmi_physical.py

* `test_cmi_zero_when_continuous_service` — no faults,
  CMI = 0.
* `test_cmi_matches_restoration_time_x_customers` — a
  feeder fault lasts `T` steps and affects `N` customers.
  CMI = `T × N`.
* `test_cmi_per_customer_independent` — partial restoration
  (FLISR closes the tie at step 5; downstream load is
  restored at step 5, upstream load remains faulted) yields
  CMI equal to the per-load-node sum, not a global scalar.

### tests/test_stage45_critical_load_physical.py

* `test_critical_load_interruption_zero_when_served` —
  hospital served throughout the run; interruption count = 0.
* `test_critical_load_interruption_steps_count` — hospital
  isolated for 5 steps; interruption count = 5.
* `test_critical_load_priority_documented` — the metric
  collector treats `hospital` and `hospital_icu` as critical
  loads; other load types do not contribute.

### tests/test_stage45_voltage_physical.py

* `test_voltage_violation_zero_when_grid_normal` —
  no faults, no violations.
* `test_voltage_violation_counted_per_step` — sustained
  voltage deviation across `T` steps yields `T` violations.
* `test_voltage_violation_from_solved_state` — the
  violation count is derived from `node.voltage`, not from
  fault presence.

### tests/test_stage45_action_sensitivity.py

* `test_battery_discharge_changes_received_power` —
  Controller A = do-nothing, Controller B = use_battery
  on every step. After fixing the Stage-45 source-
  broadening, `P_served` differs and ENS differs.
* `test_reroute_changes_received_power` — Controller A =
  do-nothing, Controller B = reroute_energy. If the
  network has an open tie-switch that can re-energise a
  sub-tree, ENS differs.
* `test_supercap_discharge_changes_received_power` —
  short-duration deficit scenario; supercap action reduces
  unserved energy.
* `test_shift_load_changes_received_power` — peak-demand
  scenario; shift_load reduces ENS by reducing the demand
  being shed.
* `test_metric_invariance_regression` — the Stage-44
  problem: with the Stage-45 fixes, ENS MUST be capable
  of reflecting different controller decisions. The test
  fails if ENS is byte-identical between two controllers.

## 11. Backward compatibility

The Stage-45 metric collector is a **new module**
(`backend/experiments/stage45_metrics.py`) and the Stage-45
validation runner is a **new file**
(`backend/experiments/stage45_validation.py`). The Stage-44
runner, the existing `benchmarks/metrics.py`, and the
existing `MetricCollector` (used by `runner.run_single`)
are **untouched**. Stage-44 results remain valid as a
*baseline*; Stage-45 results are the *corrected* values.

## 12. Validation design

The Stage-45 validation re-runs the Stage-44 10-seed
contract with the corrected metric contract:

* 10 seeds × 5 scenarios × 4 controllers × 5 ablations.
* Same Stage-43 scenario matrix (A, E, G, H, J).
* Same controllers (random, rule_based, untrained_dqn,
  trained_dqn).
* Same ablations (full_stack, no_lstm, no_twin,
  no_predictive, no_ems).
* Same checkpoint (`experiments/checkpoints/dqn_stage44.pt`).
* Same paired-fingerprint contract.
* Same Wilcoxon + Cohen's d + Holm statistics.

The only difference is the **metric collector**: Stage-45
uses the corrected `_Stage45MetricCollector` (defined in
`backend/experiments/stage45_metrics.py`).

## 13. Acceptance criteria

Stage-45 is **PARTIAL — CONTINUE** until ALL of:

1. ENS, CMI, critical-load interruption, voltage
   violations, restoration time are all derived from
   post-power-flow outcomes — not from the fault schedule.
2. The 5 unit-test files pass deterministically.
3. The action-sensitivity regression test passes
   (storage / topology actions physically change ENS).
4. The 1-seed × 5-scenario × all-controllers smoke run
   shows **at least one metric** with controller-level
   variation.
5. The 10-seed × 5-scenario × 4 controllers × 5 ablations
   full re-run completes with 0 invalid fingerprints.
6. The corrected Stage-45 metrics are reported in
   `docs/STAGE_45_VALIDATION_REPORT.md`.
7. No 100-seed run.
8. No retuning of R1–R4 from Stage-44.
9. No tuning of the new metric collector to make DQN
   look better.
10. Run-count accounting reconciles with Stage-44 (the
    600 vs 1250 discrepancy from Stage-44 is corrected —
    see §22 in the Stage-45 mandate).

## 14. Files to be created

* `backend/experiments/stage45_metrics.py` — corrected
  metric collector (per-timestep service accounting).
* `backend/experiments/stage45_validation.py` — runner
  that uses the corrected metric collector.
* `backend/experiments/stage45_statistics.py` — aggregator
  (mean / median / CI / Wilcoxon / Cohen's d / Holm).
* `docs/STAGE_45_CURRENT_METRIC_TRACE.md`.
* `docs/STAGE_45_METRIC_DEFINITIONS.md`.
* `docs/STAGE_45_PHYSICS_COUPLING.md`.
* `docs/STAGE_45_ACTION_SENSITIVITY.md`.
* `docs/STAGE_45_VALIDATION_REPORT.md`.
* `docs/STAGE_45_COMPLETION_REPORT.md`.
* `tests/test_stage45_ens_physical.py`.
* `tests/test_stage45_cmi_physical.py`.
* `tests/test_stage45_critical_load_physical.py`.
* `tests/test_stage45_voltage_physical.py`.
* `tests/test_stage45_action_sensitivity.py`.
* `experiments/results/stage45/raw/`,
  `experiments/results/stage45/aggregated/`,
  `experiments/results/stage45/statistics/`,
  `experiments/results/stage45/figures/`,
  `experiments/results/stage45/tables/`,
  `experiments/results/stage45/manifest.json`.

## 15. Run-count accounting (resolution of Stage-44 inconsistency)

Stage-44 documentation listed 1250 expected runs (5 scenarios × 10 seeds × 5 controllers × 5 ablations). The Stage-44 *empirical* validation produced **600** runs because `random` and `rule_based` are not ablated (they only run `full_stack`).

The Stage-45 *documented* run count is **600**, computed as:

```
n_runs = (n_controllers_dqn × n_ablations + n_controllers_baseline × 1)
       × n_scenarios × n_seeds
       = (2 × 5 + 2 × 1) × 5 × 10
       = 12 × 5 × 10
       = 600
```

Where:
* `n_controllers_dqn = 2` (untrained_dqn, trained_dqn).
* `n_controllers_baseline = 2` (random, rule_based).
* `n_ablations = 5` (full_stack, no_lstm, no_twin, no_predictive, no_ems).
* `n_scenarios = 5` (A, E, G, H, J).
* `n_seeds = 10`.

This number is reported consistently in the Stage-45
documents, code comments, and statistics manifests.