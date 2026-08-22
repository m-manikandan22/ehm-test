# STAGE 43 — Controlled Validation Report (10 seeds)

Status: DONE
Data: `backend/experiments/results/stage43_validation/validation.json`,
`summary.md`. Harness: `backend/experiments/stage43_validation.py`.

## Design

* Scenarios: **A, E, G, H, J** (spec §21).
* Controllers: **random, rule_based, untrained_dqn, trained_dqn, full_stack**.
* Seeds: 0–9 (10 seeds). 250 runs total.
* Every (scenario, seed) is paired: identical fault schedule, grid seed and
  stream seeds; pairing verified by **environment fingerprints**
  (grid/demand/renewable/fault hashes) — **ALL 50 pairs match**.
* `trained_dqn` = full pipeline + frozen checkpoint
  (`experiments/checkpoints/dqn_extended.pt`, 1600 transitions);
  `untrained_dqn` = same pipeline, random weights (the Stage-42.5 baseline).
  `full_stack` (pre-baked ablation label) carries no checkpoint, so it is
  identical to `untrained_dqn` by construction — expected and noted.

## Mean ENS (MWh) — lower is better (mean ± std over 10 seeds)

| Scenario | random | rule_based | untrained_dqn | trained_dqn |
|---|---|---|---|---|
| A | 1.6079±0.9710 | 1.6263±0.9736 | 1.5984±0.9795 | 1.6263±0.9736 |
| E | 2.5028±2.0437 | 2.5366±2.0436 | 2.4821±2.0585 | 2.5366±2.0436 |
| G | 2.0128±1.1926 | 2.0128±1.1926 | 2.0128±1.1926 | 2.0128±1.1926 |
| H | 1.6079±0.9710 | 1.5617±0.9698 | 1.5617±0.9698 | 1.5617±0.9698 |
| J | 58.0179±15.8821 | 58.0571±15.9139 | 58.0571±15.9139 | 58.0571±15.9139 |

Restoration rate: ≈0.93–1.00 across all cells (FLISR-driven).

## Paired differences `mean(other − trained_dqn)` on ENS (positive ⇒ trained better)

| Scenario | vs rule_based | vs untrained_dqn | vs random |
|---|---|---|---|
| A | +0.0000 (0/10) | +0.0279 (2/10) | +0.0183 (1/10) |
| E | +0.0000 (0/10) | +0.0545 (2/10) | +0.0337 (1/10) |
| G | +0.0000 (0/10) | +0.0000 (0/10) | +0.0000 (0/10) |
| H | +0.0000 (0/10) | +0.0000 (0/10) | −0.0463 (0/10) |
| J | +0.0000 (0/10) | +0.0000 (0/10) | +0.0392 (1/10) |

## Honest reading

1. **All paired environments match** — every controller saw the identical
   grid, profiles and faults; RNG isolation holds in production runs.
2. **The trained policy differs from the untrained one** (action counts,
   ENS deltas), so the training → frozen-eval path is causal — but the
   trained policy **collapsed to a single action** (use_supercapacitor on
   every step; pooled action counts `{2: 8000}`). Its ENS is within noise of
   the baselines and exactly equal to rule_based's in every pair.
3. **ENS in this harness is dominated by FLISR restoration and fault
   scheduling**, not by controller actions 0–3: those are stability actions
   (storage/load) that never change failed/isolated status, and ENS is now
   charged against would-be load (Repair 10). Only topology-changing actions
   (action 4, FLISR) move ENS.
4. **No superiority claim is made for any controller.** These are the numbers
   the paper would report if claims were wanted; the completion report keeps
   the gate verdict limited to wiring evidence, with policy-quality
   improvement as a documented CONTINUE item.
