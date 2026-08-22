# Stage 44 — Information Ablation

## Purpose

The Stage-43 architecture repair wired three new feature channels
into the DQN's 78-dim state vector:

* **Position 72** — LSTM forecast of next-step aggregate demand
  (`predicted_load`, range `[0.30, 0.49]` at evaluation time).
* **Positions 73–74** — battery / supercapacitor state-of-charge.
* **Positions 75–77** — digital-twin features (`twin_max_risk`,
  `twin_mean_risk`, `twin_high_frac`).

The Stage-43 wiring contract (`docs/STAGE_43_LSTM_INTEGRATION.md`,
`docs/STAGE_43_DIGITAL_TWIN_INTEGRATION.md`) says these channels
*reach* the decision. But reaching is not the same as being
*used*. Stage 44 must demonstrate that the trained DQN *responds*
to these features — and that the response is not just an artifact
of the network's wiring.

The Stage-44 plan (§17 of the mandate) requires three controlled
ablations:

* `FULL_STATE` vs `FORECAST_REMOVED` (zero out position 72)
* `FULL_STATE` vs `TWIN_REMOVED` (zero out positions 75–77)
* `FULL_STATE` vs `STORAGE_REMOVED` (zero out positions 73–74)

## Method

For each ablation pair, on **identical** environment conditions:

1. Build the full extended state vector from the grid's current
   state (`build_extended_state` with the actual LSTM forecast,
   actual battery/supercap SOC, and actual twin features).
2. Build the *ablated* state vector by zeroing the positions
   listed above (everything else identical, byte-for-byte).
3. Run the trained DQN's `policy_net` (in `eval_mode`) on both
   vectors. Record `Q0..Q4`, the physical-validity mask, and the
   selected `argmax`.
4. Report:

   * ΔQ per head — `q_ablated[a] − q_full[a]` for each action
     `a ∈ {0..4}`.
   * Decision change — whether the argmax flips between
     `full` and `ablated`.
   * Confidence change — softmax(max Q_full) vs softmax(max
     Q_ablated).

The ablation is run on the same five controlled probe states used
by the Stage-43.1 controlled-state analysis (`docs/
STAGE_43_1_CONTROLLED_STATE_ANALYSIS.md`):

| Probe | Description                          | num_failed | load>1.2 | forecast |
|-------|--------------------------------------|-----------:|---------:|---------:|
| A     | generation deficit (`balance=-3`)    | 0          | True     | ~0.38    |
| B     | short high-power demand (`balance=+11.58`) | 0    | True     | ~0.38    |
| C     | long-duration deficit (`balance=-5`)| 0          | True     | ~0.38    |
| D     | topology fault (`num_failed>0`)      | 1          | True     | ~0.38    |
| E     | high demand (`balance=-1`, forecast high) | 0   | True     | ~0.49    |

These probes span the four feature axes the ablation targets. If
the DQN uses the features, ablating them must move the Q-values.
If the DQN does *not* use the features, ablating them must leave
the argmax unchanged.

## Expected pattern (hypothesis, not target)

* `FORECAST_REMOVED` should shift `Q4` downward in probes A and C
  (deficit + high forecast favours reroute) and `Q2` upward in
  probe E (high forecast favours supercap).
* `TWIN_REMOVED` should shift `Q4` downward in probe D (fault +
  twin signal triggers reroute) and leave probes A–C, E
  approximately unchanged.
* `STORAGE_REMOVED` should shift `Q1` downward (no SOC → battery
  cannot help) and `Q2` upward in probes A and C (no battery to
  draw from → supercap becomes the only fast-acting option).

If the network is *not* using a feature, the ablation must leave
*every* Q-value within `1e-4` of the full-state value. The
ablation is **invalid** if removing a feature never changes the
output — that means the feature is dead weight in the architecture.

## Decision rule

A feature is *used by the DQN* if and only if:

* At least one of the five probes shows `|ΔQ[a]| > 1.0` for at
  least one action `a`, **and**
* The decision is state-sensitive: at least one probe shows a
  flip in argmax when the feature is removed (or a confidence
  drop > 0.1).

This is the Stage-44 acceptance gate for the architecture: if the
features are not used, they must be reported as such, *not*
patched post-hoc by re-tuning the network.

## Implementation note

The information-ablation experiment is implemented inside the
Stage-44 validation runner
(`backend/experiments/stage44_validation.py`, see
`docs/STAGE_44_VALIDATION_REPORT.md`). The ablation loop loads the
trained policy in `eval_mode`, builds the five probe states,
records Q-values for `FULL_STATE` and each ablation, and writes
the result to
`backend/experiments/results/stage44/information_ablation.json`.

## What this ablation does NOT do

* It does **not** ablate the 72 base-state features (those were
  covered by Stage-42 / Stage-43 integration tests).
* It does **not** ablate the action mask — the mask is a hard
  physical-validity constraint, not a learning input.
* It does **not** ablate the reward — that is a separate audit
  (`STAGE_44_REWARD_DESIGN.md`).

## Files

* `backend/experiments/stage44_validation.py` — ablation runner
  (see `STAGE_44_VALIDATION_REPORT.md` for the surrounding
  validation harness).
* `backend/experiments/results/stage44/information_ablation.json` —
  ΔQ per probe per ablation.
* `backend/experiments/results/stage44/figures/information_ablation.png`
  — bar chart of mean |ΔQ| per ablation.
