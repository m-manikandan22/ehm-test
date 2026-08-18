# Stage 41 — Reward Audit

This document audits the DQN reward formulation in
`backend/models/rl_agent.py::compute_reward`. The audit is read-only.

> The DQN in the Stage-26 paper experiments is run in `eval_mode()`
> (line 236 of `runner.py`), which **disables gradient updates and
> replay-buffer writes**. This means the reward is computed during
> `smart_warmup` (the bootstrap at construction time, lines 234–295
> of `rl_agent.py`), but **not used to update the network during the
> 80-tick paper experiments**.

---

## 1. The reward function (verbatim)

```python
@staticmethod
def compute_reward(grid_state: dict, action_name: str = "") -> float:
    reward = 0.0
    nodes   = grid_state.get("nodes", {})
    system = grid_state.get("system", {})

    avg_voltage       = system.get("avg_voltage", 1.0)
    avg_freq          = system.get("avg_frequency", 50.0)
    balance           = system.get("balance", 0.0)
    total_energy_loss = system.get("total_energy_loss", 0.0)

    num_failed   = sum(1 for n in nodes.values() if n.get("failed"))
    num_isolated = sum(1 for n in nodes.values() if n.get("isolated"))

    # Stability (HIGH priority)
    reward += 5.0 * (1.0 - abs(avg_voltage - 1.0) / 0.1)
    reward += 3.0 * (1.0 - abs(avg_freq - 50.0) / 1.5)

    # Balance (VERY IMPORTANT)
    reward -= 4.0 * abs(balance)

    # Failure penalty (CRITICAL)
    reward -= 10.0 * num_failed
    reward -=  6.0 * num_isolated

    # Efficiency
    reward -= 0.2 * total_energy_loss

    # Smart behavior conditional bonuses
    if action_name == "use_supercapacitor" and any(n.get("load", 0) > 1.2 for n in nodes.values()):
        reward += 2.0
    if action_name == "reroute_energy" and (num_failed > 0 or num_isolated > 0):
        reward += 3.0

    return float(reward)
```

---

## 2. Direction audit

| Term | Direction | Max contribution per step | Notes |
|---|---|---:|---|
| `5.0 * (1 - |ΔV|/0.1)` | **positive** (closer to 1.0 pu is better) | +5.0 | dominates when voltage is nominal |
| `3.0 * (1 - |Δf|/1.5)` | positive (closer to 50 Hz is better) | +3.0 | dominates when frequency is nominal |
| `-4.0 * |balance|` | **negative** (imbalance is bad) | 0 (at balance) | linear penalty |
| `-10.0 * num_failed` | negative | 0 (no failures) | discrete, large magnitude |
| `-6.0 * num_isolated` | negative | 0 (no isolations) | discrete |
| `-0.2 * total_energy_loss` | negative | small | linear, weak |
| `+2.0` for supercap + spike | positive | +2.0 | fires rarely (load > 1.2) |
| `+3.0` for reroute + fault | positive | +3.0 | fires when failed/isolated |

**Max positive reward per step**: ≈ 8.0 + 2.0 + 3.0 = **13.0**.
**Max negative reward per step**: bounded by failure/isolation counts
(which themselves depend on grid state, not the agent).

**Sign convention**: positive reward → better outcome. The Stage-26
paper experiments do not run gradient descent on this reward, so
direction correctness is moot for paper claims, but the reward
itself is directionally correct.

---

## 3. Reward hacking risk

The reward is *partly* hackable. Specifically:

1. The voltage term caps at `5.0` when `avg_voltage == 1.0`. If the
   grid sits at exactly 1.0 pu by construction (which is the case for
   `update_power_flow()`'s default initial state), the agent receives
   `+5.0` per step from voltage alone — regardless of whether the
   action helped.

2. The frequency term caps at `+3.0` per step when `avg_freq == 50.0`.

3. So the *steady-state* reward is `8.0 - 4·|balance| + bonuses`.

4. Because the paper experiments run for 80 steps with no learning,
   the reward has zero influence on the Stage-26 outcomes. **The
   reward is irrelevant for the paper.**

This means the **ablation row `no_reward`** in the Stage-26 artefacts
is not just a no-op because the harness doesn't gate the flag — it
is *also* a no-op because the DQN is run in eval mode.

---

## 4. Reward sensitivity analysis (qualitative)

We did not re-tune the reward in Stage 41 because the user explicitly
forbade it. We do note the following qualitative observations:

* The failure penalty (`-10 * num_failed`) is large enough that an
  agent that prevents failures will dominate one that allows them.
  But **preventing failures in this simulation requires FLISR, which
  runs every 4 ticks regardless of the DQN's action**. So this term
  is effectively constant across actions.
* The balance penalty (`-4 * |balance|`) can be reduced by action
  `0` (increase_generation) when balance is negative, or by action
  `1` (use_battery). The DQN's action-mask enables these actions when
  `balance < -0.1`, so the agent can earn small positive gains from
  reducing balance. This is the **only** lever the agent has in
  eval mode.
* The supercapacitor bonus (`+2`) and the reroute bonus (`+3`) are
  rarely active because they require state conditions that the
  80-tick scenario rarely produces.

---

## 5. Reward formulation issues for Stage 42

For Stage 42 (which the user explicitly excluded from Stage 41), we
would consider:

1. **Adding a critical-load penalty** to incentivise hospital
   priority handling (currently encoded only in FLISR, not in the
   reward).
2. **Adding a switching-cost penalty** to discourage the agent from
   flipping actions every step.
3. **Adding a long-horizon term** so the agent values LSTM-informed
   actions.
4. **Removing the constant `+5.0` voltage term** to avoid reward
   hacking.
5. **Wiring the reward into the harness** so the ablation actually
   has an effect.

We do not implement these in Stage 41.

---

## 6. Verdict

The reward function is **directionally correct but irrelevant to the
Stage-26 paper results** because the DQN is evaluated without learning.
The `no_reward` ablation row of the Stage-26 paper experiments is a
**no-op for two independent reasons**:

1. The harness does not gate `enable_reward_shaping`.
2. The DQN is in `eval_mode()` during the 80-tick run.

Both reasons must be fixed in Stage 42 before any claim about
"reward shaping helps/hurts" can be evaluated.
