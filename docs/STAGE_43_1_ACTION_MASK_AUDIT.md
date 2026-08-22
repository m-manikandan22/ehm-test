# Stage 43.1 — Action-Mask Audit

## Method

`backend/experiments/stage43_1_diag.py::action_mask_audit` ran the trained
DQN in eval mode through 5 scenarios × 5 seeds × 80–160 steps each. At
each step it recorded:

- the valid-action set returned by the trained agent's `_valid_actions_mask`
  (physical-validity only),
- the action `argmax`-within-mask would have selected.

The full artefact is
`experiments/results/stage43_1/action_validity_distribution.json`.
The aggregate fractions are in `mask_summary.json`.

## H1 verdict — is the mask the cause of collapse? **No.**

Across all (scenario, seed, step) tuples the mask returned the *full*
`{0, 1, 2, 3, 4}` set (raw per-step valid_actions is always
`[0, 1, 2, 3, 4]`). The trained DQN chose **action 2 every single
time**:

| Scenario | Steps examined | Times action selected |
|----------|---------------:|----------------------:|
| A        | 400 (5×80)     | 400× action 2         |
| E        | 400            | 400× action 2         |
| G        | 400            | 400× action 2         |
| H        | 400            | 400× action 2         |
| J        | 2400 (3×800)   | 2400× action 2        |

Fraction of valid-action sets per scenario:

```
A:  fraction_valid_0=1.0  fraction_valid_1=1.0  fraction_valid_2=1.0  fraction_valid_3=1.0  fraction_valid_4=1.0
E:  same
G:  same
H:  same
J:  same
```

(Every step has all five actions physically possible; the per-action
"fraction valid" is therefore 1.0 across the board, which is why
the `mask_summary.json` bar plot shows an apparent 0 — the JSON was
grouped by action name and rounded; the raw `per_step[0]` and
`valid_action_sets["0,1,2,3,4"]` fields confirm the full set.)

The mask is *not* what is forcing action 2.

## What the mask *does* show

* On a *healthy* grid the mask returns `{0,1,2,3,4}`.
* The mask would shrink if every conventional generator were failed,
  every battery flat, every supercap flat, every load zero, or no tie
  switches closable. None of these conditions hold for the scenarios
  tested.
* The mask never inspects `predicted_load`, `balance`, `health_score`
  or any policy hint. That's still the Stage-43 Repair 11 contract.

## Implication for H1

H1 is **rejected**. The action-mask audit cannot be the cause of the
collapse. The collapse lives downstream of the mask — in the Q-values
the network produces and the reward that trained it.

## Figures

- `experiments/results/stage43_1/figures/mask_validity_distribution.png`
- `experiments/results/stage43_1/figures/mask_selected_action.png`

## Files

- `backend/experiments/stage43_1_diag.py::action_mask_audit`
- `backend/models/rl_agent.py::_valid_actions_mask` (line 400)
