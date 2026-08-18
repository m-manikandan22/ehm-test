# Stage 42.5 — Random Baseline Audit (`STAGE_42_5_RANDOM_BASELINE_AUDIT.md`)

**Date:** 2026-08-18
**Status:** Empirical audit complete — mechanism identified and reproduced.

## Question

Why does the `random` controller produce the **lowest ENS** of every
controller in the Stage-42 scenario matrix (Scenario A, 10-seed mean:
random 0.9376 vs rule_based 1.3761, dqn_core_only 1.0618, full_stack
1.3527)? Is this a genuine finding, or an artifact?

## The mechanism

### Step 1 — failed/isolated node loads are frozen

`_apply_time_curves` (grid.py:707) and `node.step()` (grid.py:573) **skip**
failed/isolated nodes. Their `load` is never recomputed while down; it stays
at whatever value it had at the moment of the last write.

### Step 2 — ENS is charged against frozen loads

`record_step` (research_metrics.py:136-138):
`energy_not_served_mwh += load * (1/60)` for every failed/isolated node.

So ENS depends on (a) *which* nodes are down and for how long, and (b) the
*frozen load value* of those nodes while down. Restoration timing is
policy-independent — FLISR runs on a fixed schedule (`step % 4 == 0`,
runner.py:497) for every config with `enable_flisr`.

### Step 3 — only actions that touch frozen loads change ENS

Per the action audit, only `use_supercapacitor` (load −) and `shift_load`
(load × 0.85) modify `node.load`; and because failed nodes are skipped by
the curves, **those reductions persist** on failed houses.

- `random` picks all five actions roughly uniformly (action 2 share ≈ 0.21,
  action 3 ≈ 0.19) → its `use_supercapacitor`/`shift_load` draws repeatedly
  deflate the frozen loads of failed houses → lower ENS.
- `rule_based` picks action 1 (`use_battery`) on **every** step — it never
  touches load — so failed houses keep their full frozen load → highest ENS.
- Masked DQNs pick `shift_load` most (share ≈ 0.77) → some deflation, but
  weaker than `random`'s supercap draws.

### Empirical confirmation (probe, seed 0, Scenario A)

Failed/isolated node sets and down-durations are **identical** between
`random` and `rule_based` (LB0_DN_1 ×38 steps, H7 ×38, LA0_2 ×28, H1 ×28,
LB0_UP_1 ×13, H6 ×13). But the frozen loads differ:

| Node | rule_based frozen load | random frozen load |
|---|---|---|
| H7 (38 steps down) | 0.27 every step | drifts down, 28 of 38 steps at 0.00 |
| H1 (28 steps down) | 0.35 every step | drifts down, 11 of 28 steps at 0.00 |
| H6 (13 steps down) | 0.29 every step | 7 of 13 steps at 0.00 |

ENS: rule_based 0.5444 vs random 0.2374 on the same seed — the entire gap is
the frozen-load deflation, not restoration skill.

## Follow-on artefacts explained

- **Twin's "benefit" on Scenario H** (rule_based, 5 seeds): twin ON 1.0705
  vs twin OFF 1.6807. The health-aware bias switches rule_based from action
  1 (battery drain, no load effect) to action 3 (shift_load, 15% frozen-load
  cut on failed houses). The "improvement" is the same freeze-deflation
  mechanism — not health-informed restoration.
- **EMS has zero effect** (rule_based, 5 seeds, EMS ON vs OFF → ENS identical
  1.6807): EMS dispatches storage but its generation/load writes are
  curve-wiped for healthy nodes and it never touches failed-node loads.
  `dqn_core_only` (EMS/storage off) and `dqn_mask` (EMS/storage on) are
  effectively the same config: 1.0618 vs 1.0623.
- **Predictive healing has zero effect** (Scenario H, 5 seeds): ENS and
  actions identical with `enable_predictive_healing` on/off; only the event
  counter differs (80 vs 0). It is advisory-only.

## Fairness audit

- The `random` config keeps FLISR and EMS enabled (only DQN/LSTM/twin/
  predictive/reward/XAI are disabled) — it is a fair "random controller with
  the physical layer intact" baseline. `dqn_core_only` additionally disables
  EMS/storage, but since those have zero effect (above), the comparison is
  not materially skewed.
- **Cross-controller RNG contamination (unfair):** `select_action` calls
  `random.random() < self.epsilon` in eval mode on **every step** — the draw
  is consumed even though epsilon is 0 (rl_agent.py:357, verified:
  stream diverges after 5 calls). The grid's noise stream (`_apply_time_curves`
  uses the same global `random`) is therefore different for DQN runs than for
  rule_based/random runs at the same seed. DQN and non-DQN runs are **not on
  the same environment trajectory**. rule_based and random consume no global
  RNG (verified), so the rule_based-vs-random comparison is fair, but any
  DQN row is on a different grid realisation.

## Conclusion

`random` beats the other controllers because of a metric artifact: its
load-reduction actions persist on failed/isolated houses (whose loads are
frozen), deflating the ENS charge. The paper result "random outperforms
rule-based and DQN" does not indicate that random behaviour is good
restoration practice; it reflects that ENS is charged against frozen loads
that only load-reduction actions can lower.
