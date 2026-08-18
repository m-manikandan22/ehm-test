# Stage 41 — Action-Space and Reward Audit

This document audits the DQN action space and reward formulation
together, because they co-evolve. The audit is read-only against the
existing implementation.

---

## 1. The 5-action space

| ID | Name | What it does (in the harness) | When the action-mask enables it |
|---:|---|---|---|
| 0 | increase_generation | `node.increase_generation(0.5)` on `G0` (single node) | always enabled if `balance < -0.1` |
| 1 | use_battery | discharges `house` nodes' batteries by 0.2 (only those with `battery_level > 0.2`) | always enabled if `balance < -0.1` |
| 2 | use_supercapacitor | discharges `house` nodes' supercaps by 0.1 (only those with `supercap_level > 0.1`) | enabled if `any(node.load > 1.2)` |
| 3 | shift_load | reduces `house` nodes' load by 15 % via `node.shift_load(0.15)` | **always enabled** |
| 4 | reroute_energy | nothing in the harness (FLISR is called separately every 4 ticks by `runner.py` line 297) | enabled if `any(node.failed or isolated)` |

### 1.1 Each action's reach

| ID | Validity in 49-node grid | Reversible | Conflicts with topology? |
|---:|---|:---:|:---:|
| 0 | always | no (gen setpoint changes) | no |
| 1 | only if SOC > 0.2 | no (depletes battery) | no |
| 2 | only if supercap SOC > 0.1 AND some load > 1.2 MW | no (depletes supercap) | no |
| 3 | always | no (load is shed, not deferred) | no |
| 4 | only when fault/isolation present | n/a (no-op in harness) | n/a |

### 1.2 Action space limitations

* **No explicit "open tie switch" action.** The harness runs FLISR
  every 4 ticks regardless of the DQN's choice. The DQN's action 4
  ("reroute_energy") is a *no-op* in the paper experiments.
* **No "close tie switch" action either.** Tie switches are toggled
  by FLISR's 9-stage algorithm.
* **No "shed load on specific node" action.** `shift_load` sheds 15 %
  on **every** house node simultaneously.
* **No "raise generation on specific generator" action.**
  `increase_generation` always targets `G0` only.
* **No "wait / no-op" action.** Every tick the agent must take one
  of the 5 actions (the harness does not have a do-nothing option).
  This is a design constraint of the harness, not a fundamental
  limitation of the model.

### 1.3 Action that exists but is rarely useful

**Action 2 (use_supercapacitor)** is masked on by the rule
`any(node.load > 1.2)`. In the Stage-26 default scenario, residential
loads are typically < 0.5 MW, so action 2 is **almost never
enabled**. The supercapacitor is therefore effectively unused.

### 1.4 Important engineering decisions not representable

* **Per-node load shedding.** Critical vs non-critical priority
  is encoded in FLISR's tie-candidate scoring
  (`scada.py::_flisr_restore`), but the DQN cannot choose which
  cluster to shed.
* **Per-generator dispatch.** Generation is centralised on `G0`.
* **Battery / supercap reservation policy.** The DQN cannot decide
  to *not* discharge even when SOC is low; the harness always
  discharges 0.2 / 0.1 if the threshold is met.

## 2. Reward audit

See `STAGE_41_REWARD_AUDIT.md` for the full analysis. The headline:

* Reward is positive when voltage ≈ 1.0 pu, frequency ≈ 50 Hz,
  balance ≈ 0, no failed/isolated nodes.
* The reward has a `+5` constant for nominal voltage (reward
  hacking risk).
* The reward includes `+3` for `reroute_energy` when fault/isolated
  — but action 4 is a no-op in the harness.
* The reward is irrelevant to Stage-26 because the DQN is in
  `eval_mode()`.

## 3. Action-space vs. rule-based comparison

The Stage-26 paper compares:

* **rule_based**: 2-action reactive policy (action 0 or 1 only).
* **dqn_core_only**: 5-action DQN with action mask.
* **full_stack**: same as dqn_core_only (the harness does not gate
  the additional modules).

The **only meaningful difference** is that the DQN can choose action
3 (`shift_load`), action 4 (when faults exist, though it's a no-op),
or action 2 (when spikes exist). The rule-based controller cannot.

The **largest behavioural difference** is action 3: the DQN can
**shed 15 % of every house load** as a single-step decision. The
rule-based controller cannot. This is a strong lever — every house
node loses 15 % of its demand instantly.

## 4. Action distribution analysis

The Stage-26 raw data records `actions_taken = 80` for every run
(because every tick takes an action). It does **not** record which
specific action was taken. We have to re-instrument the harness to
record per-action distribution if we want to attribute behaviour to
specific actions.

We do **not** re-instrument in Stage 41.

## 5. Verdict

* The 5-action space is *adequate* for the Stage-26 scenarios but
  cannot represent per-node decisions.
* Action 2 is rarely usable due to the action-mask rule.
* Action 4 is a no-op due to FLISR running separately.
* The reward is reasonable but reward-hackable for voltage.
* The harness-level action-space audit exposes a **paper-writing
  hazard**: claiming "the DQN learns to dispatch a portfolio of
  storage and generation actions" is misleading because the action
  mask is hand-coded and not learned.

## 6. Recommendation for Stage 42

* Record per-action distribution per step per run (one-line change).
* Re-run with harder scenarios (B, E, G, I) and report which actions
  the DQN picks more often than the rule-based.
* Wire the reward into the harness so the `no_reward` ablation
  actually has an effect.
