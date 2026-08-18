# Stage 42.5 — Action-Space Audit (`STAGE_42_5_ACTION_AUDIT.md`)

**Date:** 2026-08-18
**Status:** Empirical audit complete — every claim below was verified by running the actual harness code, not by reading it.

## Scope

The controller action space has five actions. This audit answers one question
for each: **what does the action physically change on the grid, and does that
change survive `grid.step()`?**

Reference: `experiments/runner.py::_dispatch_action` (line 110), `simulation/node.py`
(`use_supercapacitor` 356, `use_battery` 368, `increase_generation` 379,
`shift_load` 383), `simulation/grid.py::_apply_time_curves` (line 691),
`simulation/grid.py::update_generation` (line 563).

## Methodology

`_stage425_diag.py` (section A) built a grid with `_build_grid(7)`, snapshotted
aggregate load / generation / battery / supercapacitor levels, dispatched each
action via the runner's own `_dispatch_action`, and recorded the state again
(a) immediately after dispatch, (b) after one `grid.step()`, (c) after two.

## Results (seed 7, Scenario A grid)

| Action | Immediate effect | After 1× `grid.step()` | Verdict |
|---|---|---|---|
| 0 `increase_generation` | none (Δ=0.0000 everywhere) | none | **Dead** — targets `G0`, which does not exist |
| 1 `use_battery` | gen +2.6000, battery −0.2600 | gen **wiped** (back to curve), battery stays −0.26 | **Battery drain only** |
| 2 `use_supercapacitor` | load −1.0727, supercap −1.3000 | load **wiped**, supercap stays −1.30 | **Supercap drain only** |
| 3 `shift_load` | load −0.1825 | load **wiped** | **No persistent effect** |
| 4 `reroute_energy` | none (Δ=0.0000) | none | **Dead** — function body is `pass` |

### Why effects are wiped

`grid.step()` → `update_generation()` → `_apply_time_curves()` recomputes every
house's load and generation **from `_base_load` / `_base_generation` every
step** (grid.py:713-715). Any load/gen change made by an action is overwritten
on the very next step. Only values that `_apply_time_curves` does not touch —
`battery_level`, `supercap_level` — persist.

### Action 0 details

`_dispatch_action` calls `grid.increase_generation(node_id="G0")`. The grid's
generator nodes are `GEN_SOLAR`, `GEN_WIND`, `GEN_NUCLEAR`, `GEN_COAL`,
`GEN_GAS` — there is no `G0` (`grid.nodes` key check: `'G0' in grid.nodes`
→ **False**). `increase_generation` silently does nothing for a missing node.

### Action 4 details

`_dispatch_action` case 4 has an empty body (`pass`). The docstring claims
"reroute" but no rerouting is implemented. Real reconfiguration is done by
FLISR (`flisr_9stage`, grid.py:1488) on its own schedule (`step % 4 == 0`,
runner.py:497), independent of the controller.

## Interaction with failed/isolated nodes (why ENS varies by controller)

`_apply_time_curves` and `node.step()` **skip** failed/isolated nodes
(grid.py:707, grid.py:573). Consequently the load of a failed/isolated node is
**frozen at its pre-fault value** for as long as the node stays down.

Because of this freeze, the only controller-dependent lever on ENS is whether
the controller's action happens to *reduce* the frozen load of a failed house:

- `use_supercapacitor` (action 2) subtracts from `node.load` — the reduction
  persists because the node is failed (verified: probe shows a failed house's
  load dropping to 0.0 for 28 of 38 down-steps under the `random` policy).
- `shift_load` (action 3) multiplies `node.load` by 0.85 — same persistence on
  failed nodes.
- `use_battery` (action 1) only adds generation, never touches load — failed
  houses keep their full frozen load.
- EMS, running after `grid.step()` but before record, does not change failed
  nodes' loads either (its effects are also curve-wiped; see
  `STAGE_42_5_RANDOM_BASELINE_AUDIT.md`).

## Conclusions

1. **Two of five actions are dead code in the harness** (0 and 4).
2. **The remaining three actions have no persistent effect on healthy-node
   load or generation** — only storage SOC drains survive.
3. **The only mechanism by which any controller changes the ENS metric is
   accidentally deflating the frozen load of failed/isolated houses.**
4. The "restoration" story of the action space (boost, reroute, shift) is not
   realised in the harness as measured.

## Deliverables arising

- `STAGE_42_5_RL_VS_HEURISTIC.md` — why the DQN appears to "change decisions"
  when LSTM is toggled (torch-RNG artifact), and the true state of DQN
  training in the harness.
- `STAGE_42_5_RANDOM_BASELINE_AUDIT.md` — why `random` outperforms every
  other controller, and the ENS freeze mechanism above.
- Test suite repairs (empty/vacuous assertions replaced with honest checks).
