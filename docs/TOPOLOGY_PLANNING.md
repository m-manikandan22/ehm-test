# TOPOLOGY_PLANNING.md — Stage 14

This document specifies how EHM proposes, evaluates, and applies
topology improvements to a SmartGrid. It pairs with `docs/REWARD_FORMULATION.md`
(what the agents optimise against) and `docs/NOVELTY_MATRIX.md` (where the
planner sits in the contribution stack).

> **Status:** SIMULATION-VALIDATED. The planner runs against the
> in-repo 49-node default grid and the procedurally generated city
> grids. It is **not** validated against a real utility's data.

---

## 1. Why topology planning?

A procedurally generated city grid is *plausible* but not *optimal*:
feeder lengths vary, tie-switch coverage is uneven, and there is no
guarantee that a single contingency can be re-routed. The AI planner
suggests concrete improvements (a new tie switch here, a battery
there) by:

1. Computing five objective metrics on the current grid.
2. Enumerating a small candidate set of *declarative* mutations.
3. For each candidate: apply → recompute metrics → undo.
4. Accept the candidate that reduces the objective the most, repeat.

The result is a **list of `PlanAction` records** — never applied to
the input grid by the planner itself. The caller decides whether to
apply them (real-time, scheduled, or offline).

---

## 2. The five objectives

Defined in `backend/planning/objectives.py`:

| Objective           | Symbol     | Goal | Units      |
| ------------------- | ---------- | ---- | ---------- |
| Expected Outage Energy | outage  | min  | MWh        |
| Voltage Drop Index      | v_drop | min  | pu (scalar)|
| Power Loss              | loss   | min  | MW         |
| Reliability Index       | rel    | max  | unitless   |
| Restoration Time LB     | rest   | min  | s (steps)  |

The combined cost is:

```
C = w_outage · outage
  + w_v_drop · v_drop
  + w_loss   · loss
  - w_rel    · rel
  + w_rest   · rest
```

with defaults `(1.0, 1.0, 1.0, 2.0, 1.0)` (`PlannerConfig`).

The reliability weight is **larger than the others** — the planner
favours configurations that improve redundancy / N-1 readiness even at
a small cost in voltage drop.

---

## 3. Candidate mutations

The planner enumerates three classes of action:

| Kind                | Effect                                                         |
| ------------------- | -------------------------------------------------------------- |
| `add_tie_switch`    | Add a tie switch between two distribution substations that aren't already directly connected. |
| `add_backup_path`   | For a load bus > 4 hops from any tie switch, propose a redundant branch to the nearest tie cluster. |
| `add_redundancy`    | Add a redundant feeder (transformer) along the path with the most loads. |

Each candidate is enumerated, applied to a *copy* of the grid (so the
input grid is never mutated), scored, and then undone. Only the best
candidate per iteration is accepted.

---

## 4. The optimiser

```python
for iteration in range(max_iterations):
    best = best_candidate()
    if best is None:
        break
    cost_after, _ = apply_and_evaluate(best)
    delta = cost_before - cost_after
    if delta < eps:
        break
    accept(best)
    cost_before = cost_after
```

* `max_iterations = 8` by default — the planner stops early if the
  marginal improvement is below `eps = 1e-3`.
* The candidate set is **capped at 6 per class** (18 total per
  iteration) so the loop stays sub-second on a laptop.

This is a constrained local-search, not a global optimisation. The
planner is *directional*: it returns a short list of *likely*
improvements that the caller can sanity-check, not a proof of
optimality.

---

## 5. Public API

| Symbol                  | Location                                   |
| ----------------------- | ------------------------------------------ |
| `PlannerConfig`         | `backend/planning/ai_planner.py`           |
| `PlanAction`            | `backend/planning/ai_planner.py`           |
| `AIPlanner.plan()`      | `backend/planning/ai_planner.py`           |
| `expected_outage_energy`| `backend/planning/objectives.py`           |
| `power_loss_mw`         | `backend/planning/objectives.py`           |
| `reliability_index`     | `backend/planning/objectives.py`           |
| `voltage_drop_index`    | `backend/planning/objectives.py`           |
| `restoration_time_lower_bound` | `backend/planning/objectives.py`     |
| `all_kpis(grid)`        | `backend/planning/topology_kpis.py`        |
| `avg_path_length`       | `backend/planning/topology_kpis.py`        |
| `mesh_index`            | `backend/planning/topology_kpis.py`        |
| `redundancy_score`      | `backend/planning/topology_kpis.py`        |
| `articulation_count`    | `backend/planning/topology_kpis.py`        |

---

## 6. How to reproduce the experiment

```bash
cd backend
python -m experiments.run_topology_planning
```

The script:

1. Loads the default 49-node grid.
2. Runs `AIPlanner().plan()`.
3. Prints before / after KPIs.
4. Writes the action list to `experiments/results/topology_planning.json`.

The script is **deterministic** — `PlannerConfig` is frozen, the
planner uses a fixed seed (`42`), and the underlying power-flow solver
is deterministic given the same grid state.

---

## 7. Limitations

* **Local search, not optimal** — the planner finds *a* local minimum
  near the input. There is no guarantee it finds the *best* plan.
* **No AC PF** — the voltage-drop and power-loss objectives use DC PF
  (matching the rest of the codebase). AC PF would give more accurate
  voltage magnitudes; see EHM-HIGH-005.
* **No construction cost** — `add_tie_switch` is treated as
  zero-cost. Real feeders cost money; adding cost terms would flip
  the optimisation toward *cheaper* plans.
* **No chronological planning** — the planner operates on a static
  snapshot. Real distribution expansion planning is a multi-year
  dynamic problem.

---

## 8. Citation form (for the paper)

> The EHM topology planner is a constrained greedy + local-search
> optimiser that proposes tie-switch additions, backup paths, and
> feeder redundancy. It minimises a weighted sum of expected outage
> energy (MWh), voltage drop index, and power loss while maximising
> a reliability index and minimising the restoration time lower
> bound. The optimiser is deterministic given a frozen `PlannerConfig`
> and a fixed RNG seed, returning a short list of `PlanAction`
> records that the operator can review before enacting.