# Stage 43 — Action Space (Repair 3)

## Catalogue

| ID | Name | Physical effect (Stage-43) | Persistence scope |
|----|------|-----------------------------|-------------------|
| 0 | `increase_generation` | Ramp the first alive conventional generator (gas/coal/nuclear) by 0.5 MW (`runner.py:162-174`) — previously targeted the fictional `G0` and was silent. | Generation on a non-curved node is *not* overwritten by `_apply_time_curves` (which only writes `_base_load`/`_base_generation` derived fields on houses + `generator_solar`/`generator_wind`). Effect persists until the next `grid.step()` cycle that bumps generation. |
| 1 | `use_battery` | For every alive house or `*storage_bat*` node with `battery_level > 0.2`, `node.use_battery(0.2)` (0.2 MW discharge). | SOC drain persists across `grid.step()` — `battery_level` is not touched by `_apply_time_curves`. |
| 2 | `use_supercapacitor` | For every alive house or `*storage_sc*` node with `supercap_level > 0.1`, `node.use_supercapacitor(0.1)`. | Supercap SOE drain persists. |
| 3 | `shift_load` | For every alive consumer with `load > 0.001`, `node.shift_load(0.15)` (defer 0.15 MW). | Effect persists **within** the step — the next `_apply_time_curves` rewrites `load` from `_base_load` next step, so the persistence window is one step. This is the documented scope; no longer claimed as multi-step persistent. |
| 4 | `reroute_energy` | `grid.reroute_energy()` — closes the open tie that re-energises the most isolated nodes; mutates `grid.graph` edges (`active=True`, `switch_status='closed'`). | Topology change survives subsequent power-flow re-solves. |

## Physical-validity guard (Stage-43 Repair)

`_dispatch_action` (runner.py:157-160) **skips failed or isolated nodes**.
This closes the Stage-42.5 artefact where a controller could lower its
ENS by deflating the frozen load of a dead node:

```python
def _alive(n) -> bool:
    return not (
        getattr(n, "failed", False) or getattr(n, "isolated", False)
    )
```

Tests `test_action_1_skips_failed_and_isolated_nodes` and
`test_action_effect_persists_across_step` in
`tests/test_stage43_integration.py` pin this contract.

## Action mask vs policy (Repair 11)

`_valid_actions_mask` (`rl_agent.py:400`) is a **physical-validity** filter
only:

| Action | Becomes invalid when … |
|--------|------------------------|
| 0 | no non-failed conventional generator exists |
| 1 | no alive node has `battery_level > 0.001` |
| 2 | no alive node has `supercap_level > 0.001` |
| 3 | no alive node has `load > 0.001` |
| 4 | no physically closable tie switch exists (open, not fault-locked, both endpoints alive) |

The mask never inspects `predicted_load`, `balance`, `health_score` or
`health_aware_load_shift`. Tests `test_action_mask_does_not_encode_policy`
asserts the mask is invariant to those hints.

`STAGE_43_RL_CONTRIBUTION.md` separates mask effects (genuine physical
constraints) from policy behaviour (network Q-values + rule ladder).

## Coverage of the required tests

Spec required:

- `test_action_0_has_valid_effect` ✅ (asserts `max(Δgeneration) > 0`).
- `test_action_4_has_valid_effect` ✅ (asserts edge activation changes
  or skipped on trivially closed topology).
- `test_action_effect_persists_across_step` ✅ (battery SOC drain
  survives `grid.step()`).
- `test_action_mask_does_not_encode_policy` ✅ (mask ignores policy
  hints).

## Why action 3 is documented as one-step persistent

`_apply_time_curves` recomputes `node.load` from `node._base_load` every
step for **house / hospital / industry / hospital_icu** nodes. Therefore
action 3's load reduction cannot persist into the next step *for those
node types*, because `_apply_time_curves` is the authoritative writer for
that attribute. The Stage-43 fix is therefore to:

1. Document the one-step persistence scope (above), and
2. Use `grid.would_be_load(node)` in the ENS accounting path so a
   transient load reduction cannot deflate the ENS of a failed node
   (see `STAGE_43_ENS_VALIDATION.md`).
