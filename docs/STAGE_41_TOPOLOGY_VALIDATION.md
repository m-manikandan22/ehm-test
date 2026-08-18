# Stage 41 — Topology-Planning Validation

This document validates the resilience-aware topology planner against
the on-disk artefacts and source code. We do NOT run a new
topology-planning experiment in Stage 41 — we evaluate the existing
artefacts honestly.

---

## 1. Where the planner lives

`backend/planning/ai_planner.py::AIPlanner.plan()` is a constrained
greedy + local-search loop with five objectives:

```
C = w_outage * outage
  + w_v_drop   * v_drop
  + w_loss     * power_loss
  - w_rel      * reliability_index
  + w_rest     * restoration_time_lower_bound
```

The defaults (`PlannerConfig`) are `w_outage = w_v_drop = w_loss =
w_rest = 1.0` and `w_rel = 2.0`.

The candidate actions are:

* `move_transformer`
* `add_tie_switch`
* `add_battery`
* `add_feeder`
* `add_backup_path`

For each candidate the planner simulates the mutation, recomputes the
five objectives, undoes the mutation, and keeps the best.

## 2. The on-disk artefact

`experiments/results/topology_planning_final.json`:

```json
{
  "seed": 42,
  "max_iterations": 8,
  "n_nodes": 49,
  "n_actions": 1,
  "kpis_before": {
    "avg_path_length":   6.2,
    "mesh_index":        0.5510204081632653,
    "redundancy_score":  1.0,
    "articulation_count": 23
  },
  "kpis_after": {
    "avg_path_length":   6.2,
    "mesh_index":        0.5510204081632653,
    "redundancy_score":  1.0,
    "articulation_count": 23
  },
  "actions": [
    {
      "kind": "add_feeder",
      "params": {"from_id": "GEN_SOLAR", "to_id": "H5"},
      "expected_delta": 0.43938364997030455,
      "rationale": "Long feeder chain GEN_SOLAR->H5 (8 hops) — add a parallel branch."
    }
  ]
}
```

### 2.1 Reported `expected_delta` is not propagated to `kpis_after`

The planner accepts one action with `expected_delta = 0.4394` but
`kpis_after == kpis_before`. This is a **reporting bug**: the
topology planner computes an expected delta but does not actually
re-evaluate `kpis_after` after applying the mutation, or it
overwrites `kpis_after` with the cached `kpis_before` snapshot.

### 2.2 The planner does not demonstrate value

* The action's `expected_delta = 0.4394` is not realised in the
  reported `kpis_after`. So we cannot say the planner improved the
  grid.
* The planner is run **once**, deterministically, with seed 42.
  There is no statistical comparison.
* There is no N-1 resilience validation in this artefact.

---

## 3. The N-1 resilience path

`backend/reliability/n_minus_one.py` is mentioned in `main.md` and
the Stage-40 gate as the N-1 analyser. It is NOT called by
`topology_planning_final.json`'s driver.

A scientifically defensible topology-planning claim requires:

1. Run the planner once → `topology_proposed`.
2. Run N-1 analysis on the *original* topology → `recovery_rate_orig`.
3. Apply planner mutations to the grid → `topology_planned`.
4. Run N-1 analysis on the *planned* topology → `recovery_rate_planned`.
5. Report `(recovery_rate_planned − recovery_rate_orig)` with a
   paired statistical test.

This pipeline does not exist in the current artefacts. The existing
`topology_planning_final.json` records `kpis_before/after` (structural
KPIs only) and `expected_delta` (the planner's self-prediction), but
not the N-1 outcome.

---

## 4. Topology comparison experiment

`experiments/topology_comparison.py` is `framework_only`:

```
"notes": [
  "'random' and 'rule' currently share the same builder "
  "(the default 49-node SmartGrid). The distinction becomes "
  "meaningful once a procedural-random builder is added.",
  "'ai' reuses the default builder and records the planner "
  "metadata; it is not a fully-resolved AI-generated grid.",
]
```

So this artefact compares three identical topologies and reports no
distinguishable metrics. **It cannot support any topology-planning
claim.**

---

## 5. Honest framing

The Stage-40 gate does *not* claim topology planning is a
demonstrated contribution. The gate text says:

> *"AIPlanner.plan()" — checked as implemented but not as
> empirically demonstrated.*

We confirm this framing.

## 6. Recommendations for Stage 42 (NOT implemented in Stage 41)

To make topology planning a defensible contribution, Stage 42 should:

1. Add a procedural-random builder (different from the default
   builder) so `random`, `rule`, and `ai` are distinguishable.
2. Add the N-1 evaluation pipeline described in §3.
3. Add a paired comparison of `kpis_before` vs `kpis_after` with the
   planner's *actual* `expected_delta` (recomputed, not the cached
   self-prediction).
4. Add a `cost_of_infrastructure` term to the objective so the
   planner's suggestion has a budget. The current objective is
   unbounded: the planner can keep accepting actions until the
   objective saturates. A real planning problem has a cost
   constraint.

## 7. Verdict

> **The topology planner is implemented and produces an output, but
> the on-disk artefacts do not demonstrate that it improves N-1
> resilience. It is a *negative result* in the sense that we cannot
> show it works; it is a *future work* item in the sense that the
> evaluation pipeline needs to be built before any claim can be
> made.**
