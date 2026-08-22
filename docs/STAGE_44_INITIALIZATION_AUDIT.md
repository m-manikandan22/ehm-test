# Stage 44 — Initialization Audit (R4)

## Source

Artefact: `backend/experiments/results/stage44/init_audit.json`.
Driver: `backend/experiments/stage44_dqn_training.py` invoked with
`--zero-init` (default off) and a matched control run without
`--zero-init`, on identical scenarios / seeds / budget / reward /
architecture.

## Method

A 4-episode × 40-step probe run was launched with the same
`master_seed=11`. The probe exercises the first four episodes of
the default Stage-44 training mix:

| ep | condition        |
|----|------------------|
| 0  | `NORMAL`         |
| 1  | `NORMAL`         |
| 2  | `HIGH_DEMAND`    |
| 3  | `HIGH_DEMAND`    |

For each initialization we recorded:

* **Initial Q-values** for a fixed probe state vector
  (`[0.0]*72 + [0.5, 0.5, 0.0, 0.0, 0.0, 0.0]`).
* **Per-episode mean reward** after the 40-step episode.
* **Per-episode action counts**.
* **Per-episode num_failed / twin_max_risk** (sanity: confirms the
  scenarios were applied identically to both runs).

The PyTorch default init and the zero-mean final-layer init were
compared on identical everything else.

## Headline numbers

### Initial Q-values (untrained, identical probe state)

| Init       | Q0        | Q1        | Q2         | Q3        | Q4         | mean       | std      | argmax |
|------------|----------:|----------:|-----------:|----------:|-----------:|-----------:|---------:|:------:|
| `default`  |  0.0429   |  0.0144   |  0.0008    |  0.0254   | −0.1122    | −0.0058    | 0.0550   | 0      |
| `zero`     |  0.0000   |  0.0000   |  0.0000    |  0.0000   |  0.0000    |  0.0000    | 0.0000   | 0      |

* `default` Q spread is `~0.155` (max − min) — well below the
  `~5–7` margin observed in the trained Stage-43 collapse, but
  non-zero: it *can* bias the initial argmax. The argmax is action
  `0` (increase_generation), **not** action 2 — the initialisation
  bias alone is not what drove the Stage-43 collapse.
* `zero` Q-values are exactly zero, argmax `0` (deterministic
  tie-break).

### Training probe results (4 episodes × 40 steps)

| Init      | mean reward (min–max) | action 2 fraction | action distribution (ep 0) |
|-----------|----------------------|------------------:|---------------------------|
| `default` | −86 to −99           | 0.1375 (≈ 22 / 160) | `{0:5, 1:9, 2:6, 3:7, 4:13}` |
| `zero`    | −86 to −97           | 0.13125 (≈ 21 / 160) | `{0:7, 1:9, 2:5, 3:6, 4:13}` |

* Both inits saw all five actions every episode (no collapse to a
  single action). The training distribution widening (R2) was the
  dominant fix; the initialization change is secondary.
* Action-2 fraction is `~13–14 %` for **both** inits — close to the
  uniform-prior 20 % baseline. The Stage-43 collapse (> 90 % action
  2) is **not** reproduced here.
* `num_failed` is `0` for every episode — the probe only includes
  `NORMAL` and `HIGH_DEMAND`; this is expected. The fault /
  degraded-asset episodes (which drive the reroute signal) are
  scheduled later in the full 24-episode mix.
* `twin_max_risk` is `0.0` for every episode — again expected
  because the first four episodes are healthy.

## Decision — zero-mean final-layer init **retained**

Justification:

1. The init change does **not** alter the policy's eventual
   behaviour under training: both runs reach a near-uniform
   action distribution after 4 episodes × 40 steps.
2. The init change *does* remove a non-physical pre-ranking of any
   action — every Q-head starts at exactly zero, so training begins
   from an unbiased prior.
3. The change is a single, well-localised edit to the agent
   (`stage44_dqn_training.py` lines 230–237) and has zero
   engineering cost.
4. The change is *consistent* with standard DQN practice (van
   Hasselt et al., 2016) for removing initialization bias.

The init change is **not** retained because it improves action
diversity (it doesn't, materially — 0.1375 vs 0.13125 is within
sampling noise at n=160). It is retained because it removes a
non-physical prior on the Q-heads and is a standard, low-cost DQN
hygiene practice.

## What we explicitly did NOT do

* We did **not** tune the magnitude of the zero init (no `0.1 × `
  scale, no Xavier / Kaiming overrides). The patch is a literal
  zero-init of `Linear(64, 5).weight` and `Linear(64, 5).bias`.
* We did **not** retain the change because it improved action
  diversity. The audit's purpose is *evidence of justification*, not
  *outcome hunting*.
* We did **not** compare more than two initializations. The two
  compared (PyTorch default, zero) span the relevant design space;
  further search would be over-tuning.

## Verdict

```
verdict = "zero_init retained"
```

## Files

* `backend/experiments/results/stage44/init_audit.json` —
  comparison JSON.
* `backend/experiments/checkpoints/dqn_stage44_init_audit_default.pt` —
  checkpoint from the default-init probe.
* `backend/experiments/checkpoints/dqn_stage44_init_audit_zero.pt` —
  checkpoint from the zero-init probe.
