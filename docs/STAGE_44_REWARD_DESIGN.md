# Stage 44 — Reward Audit & Design

## Source

`backend/models/rl_agent.py::compute_reward` (line 632).
Unchanged from Stage-43 in this Stage-44 iteration; this document
records the per-component physical justification (and the parts
that are **not** physically justified and require redesign).

The Stage-43.1 audit (`docs/STAGE_43_1_REWARD_AUDIT.md`) decomposed
the reward into eight components; that decomposition is reproduced
and re-evaluated below against Stage-44 criteria.

## Per-component evaluation

```python
@staticmethod
def compute_reward(grid_state, action_name="") -> float:
    reward  = 0.0
    ...
    reward += 5.0 * (1.0 - abs(avg_voltage - 1.0) / 0.1)        # (A) voltage stability
    reward += 3.0 * (1.0 - abs(avg_freq - 50.0) / 1.5)           # (B) frequency stability
    reward -= 4.0 * abs(balance)                                # (C) generation-load balance
    reward -= 10.0 * num_failed                                 # (D) failed assets
    reward -= 6.0 * num_isolated                                # (E) isolated assets
    reward -= 0.2 * total_energy_loss                           # (F) transmission loss
    if action_name == "use_supercapacitor" and any(n.get("load", 0) > 1.2 for n in nodes.values()):
        reward += 2.0                                           # (G) supercap spike bonus
    if action_name == "reroute_energy" and (num_failed > 0 or num_isolated > 0):
        reward += 3.0                                           # (H) reroute bonus
    return float(reward)
```

| Component | Justification | Keep / redesign |
|-----------|--------------|-----------------|
| (A) `+5 · (1 − |V − 1| / 0.1)` | Standard per-unit-voltage stability proxy; rewards proximity to 1.0 p.u. with a 10% tolerance. Physically meaningful — under-/over-voltage is a real symptom of stress. | **Keep.** |
| (B) `+3 · (1 − |f − 50| / 1.5)` | Standard frequency-deviation proxy; rewards proximity to 50 Hz nominal. Physically meaningful — frequency drift is a real symptom of imbalance. | **Keep.** |
| (C) `−4 · |balance|` | Penalises supply/demand imbalance (signed). Physically meaningful — chronic imbalance leads to undervoltage, load shedding, ENS. | **Keep.** |
| (D) `−10 · num_failed` | Penalises failed assets. Physically meaningful — failed assets are unserved. | **Keep.** |
| (E) `−6 · num_isolated` | Penalises isolated assets (separately from failed). Physically meaningful — isolated assets have no service path even if not physically broken. | **Keep.** |
| (F) `−0.2 · total_energy_loss` | Penalises transmission loss. Physically meaningful proxy for line utilisation cost. | **Keep.** |
| (G) `+2 supercap bonus` (when `load > 1.2`) | Tied to a specific action. The trigger condition (`any node with load > 1.2`) is a *physical* stress signal — but the bonus is paid regardless of whether the supercapacitor *helped*. In the Stage-43 training distribution, this bonus fired on every transition because the training grid's `_base_load` writes load > 1.2 at certain curve phases. | **Conditional redesign.** Stage-44 makes the bonus conditional on the action's *measured effect*: it only fires when the post-step load at the spike node actually drops after the supercap discharge. See the Stage-44 patch below. |
| (H) `+3 reroute bonus` (when `num_failed > 0` or `num_isolated > 0`) | Tied to a specific action. The trigger condition is a *physical* signal (fault). This bonus was the right design intent — it incentivises rerouting when service is impaired — but it never fired during Stage-43 training because training had no faults. Stage-44 training includes faults, so the bonus will now be reachable. | **Keep, but document.** |

## Why component (G) is redesigned

The Stage-43.1 audit found that the `+2 supercap bonus` is *not*
the leading reward signal — the balance penalty dominates the
magnitude. But the bonus is *consistent*: every transition in the
training distribution triggered it, so the network received a
constant `+2.0` delta on Q2 regardless of whether the action helped.
That consistent delta is enough to bias Q-values during training,
especially when other actions (0, 1, 3) are never selected.

The redesign makes the bonus **conditional on the action's measured
effect** — a supercapacitor discharge only earns the bonus when the
post-step load at the spike node is materially lower than the
pre-step load. This preserves the legitimate engineering rationale
("reward supercap when it actually mitigates a spike") without
introducing an arbitrary static preference.

If the redesign makes the bonus too rare to learn from, the bonus
can be removed entirely (Stage-43.1 Repair R3b). The completion
report will state which path was taken and why.

## What Stage-44 does NOT do

* It does **not** silently retune coefficients to make the DQN win.
* It does **not** add or remove reward components based on whether
  they help the network.
* It does **not** introduce a *repeated-action* penalty
  (`STAGE_43_1_REPAIR_RECOMMENDATION.md` §R3c) — that is the most
  aggressive reset and would mask legitimate single-action policies.
* It does **not** modify the reward at evaluation time.
