# Stage 43.1 — Controlled State Analysis

## Method

`stage43_1_diag.py::controlled_state_tests` built five deterministic
grid states A–E representing:

- A: generation deficit (balance override = -3, any_load_gt_1_2 True)
- B: short high-power demand (any_load_gt_1_2 True, no balance override)
- C: long-duration deficit (balance override = -5, low battery_soc)
- D: topology fault (any node marked failed)
- E: high demand (balance override = -1, forecast=1.5, any_load_gt_1_2 True)

For each, the *trained* policy net produced Q0..Q4 and the
physical-validity mask was queried; the selected action and the
decomposed reward are recorded.

Artefact: `experiments/results/stage43_1/controlled_states.json`.

## Headline numbers

| Case | Balance      | Failure present | load>1.2 | Selected action | Reward    |
|------|--------------|-----------------|----------|-----------------|-----------|
| A_deficit              | -3.00 | False | True  | 2  use_supercapacitor |  -6.67 |
| B_spike                | 11.58 | False | True  | 2  use_supercapacitor | -40.97 |
| C_sustained_deficit    |  -5.00 | False | True  | 2  use_supercapacitor | -14.67 |
| D_topology_fault       | 13.08 | True  | True  | 2  use_supercapacitor | -57.01 |
| E_high_demand          | -1.00 | False | True  | 2  use_supercapacitor |   1.33 |

(In every case the mask returned `{0,1,2,3,4}`.)

### Q0..Q4 per case

| Case              | Q0       | Q1       | **Q2**    | Q3       | Q4       |
|-------------------|---------:|---------:|----------:|---------:|---------:|
| A_deficit         |  -903.7  |  -894.2  | **-888.5** |  -900.3  |  -903.5  |
| B_spike           |  -868.8  |  -859.7  | **-854.0** |  -865.5  |  -868.6  |
| C_sustained_deficit |  -910.8 |  -901.2  | **-895.5** |  -907.5  |  -910.6  |
| D_topology_fault  |  -909.3  |  -899.7  | **-894.1** |  -906.0  |  -909.1  |
| E_high_demand     |  -864.4  |  -855.4  | **-849.7** |  -861.1  |  -864.2  |

Q2 ranks highest in **5/5** deterministic cases.

## Findings

1. **No state distinguishes the trained policy.** Across balanced,
   spike, sustained-deficit, faulty, and high-demand cases the
   argmax stays at action 2.
2. **Even a faulty grid does not trigger rerouting** (case D):
   - Mask returns `{0,1,2,3,4}` (tie switch satisfies physical
     validity).
   - Q2 > Q4 by 15.0 — the network has not learned to *raise*
     Q4 when `failed=True`.
   - `reroute_bonus = 3.0` would have made this transition
     rewarding, but training never saw a failed node, so the bonus
     never fired and the Q-value gradient never rewarded `+3`.
3. **The +2 supercap bonus fires for every case** — all five
   deterministic states had `any_load_gt_1_2=True`, so action 2
   collected the bonus everywhere. This is *because* the
   `load > 1.2` condition is easy to manufacture in the test grid
   (one node's `load = 1.5` is enough) and the network has learned
   to *expect* the bonus.
4. **The controlled-state probe is more diagnostic than the
   evaluation scenarios.** Scenarios A/E/G/H/J are realistic; they
   consistently trigger the same `use_supercapacitor` action. The
   controlled states go further by *forcing* extreme cases; they
   show the policy is *not state-dependent* in any of the dimensions
   we can craft.

## H5 verdict — state representation distinguishes? **Confirmed: NO.**

The 78-dim extended state vector is *connected* to the network's
output (Q-values change with feature variation), but the *argmax*
does not. The policy has not learned an action-conditional strategy.

## H7 verdict — action effects too weak? **Not the primary cause.**

If action effects were too weak to generate learning signal, all
five actions would have near-zero gradient pressure and we would
expect random-uniform action selection during training. The training
distribution is not uniform: action 2 dominates. So actions *do*
generate differential signal — it just happens to bias toward one
action.

The *persistence* weakness of action 3 (load reductions are
single-step, see `STAGE_43_ACTION_SPACE.md`) is real, but it is
explanatory for why action 3 is rare, *not* why action 2 dominates.

## H8 verdict — implementation bug? **No.**

- Mask returns full set on healthy grid ✓
- Mask respects physical preconditions ✓
- Q-values are sensible numbers (no NaN, no Inf)
- Argmax logic respects the mask
- Reward components add up to the reported scalar
- No environment exception is silently swallowed

No bug detected.

## Files

- `backend/experiments/stage43_1_diag.py::controlled_state_tests`
- `experiments/results/stage43_1/controlled_states.json`
