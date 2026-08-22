# Stage 46 — Implementation Plan

## 1. Stage-45 findings (recap)

The Stage-45 measurement-layer audit (PASS) proved that the
corrected metric contract is now physics-coupled: 40/40
(100%) (scenario, seed) groups show measurable ENS variation
across (controller, ablation) cells; mean std is 5.47 MWh;
480 valid runs with 0 fingerprint-invalid pairs.

However, Stage-45 also surfaced an **action-layer
limitation**: the `reroute_energy` action raises
`NetworkX.NodeNotFound` for an isolated downstream load, and
the runner dispatcher silently swallows the exception
(`runner.py:237-242`). The action becomes a no-op in cases
where it should either:

a. successfully perform a valid reroute, OR
b. explicitly report "no feasible reroute".

This is unacceptable for a paper whose central claim
includes automatic fault isolation and restoration.

## 2. Action-layer architecture

The controller action catalogue (5 actions) is defined in
`runner.py:121-127`:

| ID | Name | Dispatcher | Physical effect |
|---|---|---|---|
| 0 | increase_generation | `runner.py:162-174` | ramp a non-failed conventional generator |
| 1 | use_battery | `runner.py:175-200` | discharge 0.2 MW from every alive battery node |
| 2 | use_supercapacitor | `runner.py:201-209` | discharge 0.1 MW from every alive supercap node |
| 3 | shift_load | `runner.py:210-236` | defer 0.15 MW from every alive consumer node |
| 4 | reroute_energy | `runner.py:237-242` | close the open tie that re-energises the most isolated nodes |

The dispatcher calls into `SmartGrid` (`simulation/grid.py`):

* `use_battery`, `use_supercapacitor`, `shift_load`,
  `increase_generation` → `GridNode` methods (in
  `simulation/node.py`).
* `reroute_energy` → `SmartGrid.reroute_energy` (line 867-955).
* FLISR (run by the simulator itself, not explicitly by the
  controller): `SmartGrid.flisr_restore` (line 1623) and
  `SmartGrid._reroute` (line 1443).

## 3. reroute_energy root cause

### 3.1 The bug

In `simulation/grid.py:867-955`, the function builds a
**candidate graph `tmp`** from `self.graph.edges()` (line 902-908)
**without adding the isolated nodes themselves** to `tmp`:

```python
tmp = _nx.Graph()
for (a, b, d) in self.graph.edges(data=True):
    if not d.get("active", True):
        continue
    if self.nodes[a].failed or self.nodes[b].failed:
        continue
    tmp.add_edge(a, b)   # ← only edges, not nodes
```

Then at line 916-919:

```python
for nid in isolated:   # ← isolated nodes may not be in tmp
    if any(_nx.has_path(tmp, nid, s) for s in subs):
        benefit += 1
```

If `nid` is an isolated downstream node that is connected
to the grid only through a deactivated edge (filtered out
at line 904), `nid` is **not in `tmp` at all**. Calling
`_nx.has_path(tmp, nid, s)` raises
`networkx.NetworkXNodeNotFound`.

### 3.2 Why the runner swallows it

In `runner.py:237-242`:

```python
elif name == "reroute_energy":
    try:
        if hasattr(grid, "reroute_energy"):
            grid.reroute_energy()
    except Exception:
        pass
```

The bare `except Exception: pass` converts ANY error
(including `NodeNotFound`) into a silent no-op. The
action-result contract is implicit: `_dispatch_action`
returns a string (the action name) but does not report
success/failure.

### 3.3 The fix

Two coordinated changes:

1. **`SmartGrid.reroute_energy`** (`simulation/grid.py:867`):
   before calling `_nx.has_path(tmp, nid, s)`, verify that
   `nid` is in `tmp`. If not, skip that node (it is
   disconnected from the live graph even with the tie
   closed). The benefit count then reflects only nodes
   that are CONNECTED to the live graph through the tie.

2. **`runner._dispatch_action`** (`experiments/runner.py:237`):
   catch only the specific `NetworkXNodeNotFound` exception
   (or remove the silent catch entirely once the
   `reroute_energy` method is hardened). Log the action as
   "attempted, no feasible reroute" with a structured result.

## 4. Expected FLISR behavior

The `flisr_restore` / `_reroute` sequence is:

1. **DETECT** — collect failed nodes / open switches.
2. **LOCATE** — locate upstream/downstream of fault.
3. **ISOLATE** — confirm fault-locked switches block path.
4. **IDENTIFY** — list disconnected downstream load nodes.
5. **SEARCH** — enumerate candidate paths to any substation.
6. **FILTER** — check capacity, voltage drop, validity.
7. **SCORE** — pick minimum score.
8. **SWITCH** — close the chosen tie.
9. **VERIFY** — re-run power flow; confirm isolated nodes
   are now connected.

In the 49-node grid, this pipeline is invoked by the
controller via `reroute_energy` (action 4). The current
`flisr_restore` orchestrator handles steps 1-9 internally
when ALL methods run without exception. The Stage-46 audit
will verify that load restoration at step 9 means
**actual served load**, not just a switch closure.

## 5. Action semantics

The Stage-46 mandate requires an explicit action-result
contract. We define (in `runner.py`):

```python
class ActionResult(Enum):
    SUCCESS              = "success"
    NO_FEASIBLE_ACTION   = "no_feasible_action"
    INVALID_TARGET       = "invalid_target"
    PHYSICAL_INFEASIBILITY = "physical_infeasibility"
    ACTION_ERROR         = "action_error"
```

`_dispatch_action` will return both the action name and a
result enum. The runner will record this in the per-step
log so the audit can distinguish "controller chose action X"
from "action X was actually physically performed".

## 6. Physical constraints

* No action may target a failed or isolated node.
* `use_battery` must respect SOC > 0.2 and capacity limits.
* `use_supercapacitor` must respect SOC > 0.1 and capacity.
* `shift_load` must reduce demand without deleting it
  (the deferred load must be visible to the next step).
* `increase_generation` must target a live, conventional
  generator (the historical "G0 not found" bug is fixed by
  falling back to any non-failed generator).
* `reroute_energy` must not introduce failed equipment
  into the live graph.

## 7. Energy-accounting requirements

For every action that moves energy:

```
energy_before = sum of generation at all live nodes
energy_discharged = sum of action.discharge (>= 0)
energy_legitimately_recharged = sum of node.recharge (>= 0)
energy_after = sum of generation at all live nodes after step

invariant: 0 <= energy_after <= energy_before + energy_legitimately_recharged
```

The visible invariant is conservation of energy: the
simulator never creates or destroys energy except at
scheduled times (solar / wind curves).

## 8. Statistical audit

Stage-45 statistical outputs to audit:

* `experiments/results/stage45/statistics/per_cell.json`
* `experiments/results/stage45/statistics/pairwise.json`
* `experiments/results/stage45/statistics/holm.json`
* `experiments/results/stage45/statistics/invariance_audit.json`

For each (trained_dqn vs rule_based, scenario, ablation,
metric) we compute:

* mean_diff, median_diff, std, 95% CI
* Wilcoxon signed-rank p-value
* Holm-adjusted p-value
* Cohen's d
* effect direction (improvement / degradation / no-diff)

We classify each comparison into one of:

* SIGNIFICANT IMPROVEMENT (p < 0.05, d > 0.5)
* NON-SIGNIFICANT IMPROVEMENT (p ≥ 0.05, d > 0.2)
* NO MEANINGFUL DIFFERENCE (|d| ≤ 0.2)
* NON-SIGNIFICANT DEGRADATION
* SIGNIFICANT DEGRADATION

## 9. Validation design

After action-layer fixes:

1. Re-run Stage-45 deterministic test suite (5 files,
   19 tests).
2. Run Stage-46 deterministic test suite (6 files:
   reroute, FLISR, battery, supercap, load_shift,
   generation).
3. Re-run Stage-45 10-seed × 4-scenario validation using
   the **same** seeds, scenarios, controllers, ablations,
   checkpoint.
4. Compute before/after deltas (Stage-45 vs Stage-46) for
   ENS, CMI, restoration rate, critical-load, voltage.
5. Verify paired-fingerprint contract (0 invalid pairs).

## 10. Regression tests

| Test file | What it proves |
|---|---|
| `test_stage46_reroute.py` | TEST A (feasible reroute restores service), TEST B (no feasible reroute returns explicit failure), TEST C (failed equipment not used), TEST D (reroute changes physical service), TEST E (idempotence) |
| `test_stage46_flisr_integrity.py` | FLISR sequence completes; restoration = actual service |
| `test_stage46_battery_physics.py` | Energy accounting; no creation; SOC limits |
| `test_stage46_supercap_physics.py` | SOC limits; reachability |
| `test_stage46_load_shift.py` | Demand conserved; no demand deletion |
| `test_stage46_generation_action.py` | Target exists; fallback works |

## 11. Acceptance criteria

Stage-46 is PASS only if:

* [ ] reroute_energy root cause is fixed
* [ ] reroute does not silently fail
* [ ] feasible reroute restores actual load service
* [ ] infeasible reroute is explicitly reported
* [ ] failed equipment is never used in reroute
* [ ] FLISR restoration = actual service
* [ ] battery energy accounting is valid
* [ ] supercapacitor energy accounting is valid
* [ ] load shifting does not simply delete demand
* [ ] increase_generation has a valid target or is
      explicitly disabled
* [ ] all controller actions have explicit
      success/failure semantics
* [ ] action-sensitivity tests pass
* [ ] Stage-45 regression tests remain passing
* [ ] trained DQN checkpoint remains unchanged
* [ ] Stage-45 statistical results are independently audited
* [ ] Random baseline behavior is explained
* [ ] trained vs untrained DQN is evaluated
* [ ] information-flow ablation is audited
* [ ] corrected 10-seed validation completes
* [ ] fingerprints match
* [ ] no 100-seed experiment is performed
* [ ] no retraining is performed

## 12. Non-goals

Stage-46 does NOT:

* retrain the DQN
* change the DQN architecture
* change the LSTM
* change the reward
* tune hyperparameters
* expand to 100 seeds
* expand to all 10 scenarios
* cherry-pick results
* manufacture controller differences
* force a specific DQN ranking
