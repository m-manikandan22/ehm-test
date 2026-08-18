# Stage 41 — Information-Flow Audit

This document traces the actual runtime data flow of every claimed
component, end to end, and asks: *does changing this component change a
controller decision, and therefore change a metric?*

The audit is read-only against the codebase. It does not modify any
existing implementation. All claims below are anchored in source files.

---

## 1. Where the ablation harness lives

The paper-grade experiment harness is `backend/experiments/runner.py`
(`run_single`, lines 195–404). The harness builds a `SmartGrid`, then
loops over `total_steps` ticks. At each tick it:

1. Injects any scheduled fault via `grid.inject_failure(f.target)`.
2. Calls `grid.update_power_flow()`.
3. Calls `_select_action(config, grid, rng, agent=agent)` — a 5-action
   stub that returns one of five action ids (0–4).
4. Calls `_dispatch_action(grid, action)` — applies the physical effect
   of the chosen action (line 100).
5. Calls `grid.step()`.
6. If `enable_flisr` and `step % 4 == 0`, calls `grid.flisr_9stage()` or
   `grid.flisr_restore()`.
7. Calls `grid.update_power_flow()` again.
8. Calls `collector.record_step(...)`.

This harness is **deliberately thin**. The full SCADA control loop
(`backend/simulation/scada.py::ScadaControlCenter.execute_control_loop`)
is *not* called by the harness.

---

## 2. LSTM (Demand Forecasting)

### Where the LSTM lives

`backend/models/lstm_model.py::DemandForecaster` (constructed in
`backend/simulation/scada.py` line 40).

### Where the LSTM input comes from

`grid.get_lstm_input("S_MAIN")` returns the last 10 timesteps of
`[load, generation, weather]` per node.

### Where the LSTM output goes

`scada.py::execute_control_loop` line 119:
```
predicted_load = self.forecaster.predict(telemetry["lstm_sequence"])
```
The predicted load is then used in two places:

* `_predict_overloads(grid, predicted_load)` (line 121) — generates
  warnings but **does not dispatch any control action**.
* Passed to `agent.select_action(state, predicted_load, raw_state)`
  (line 124).

### Where the LSTM *is actually used* by the paper experiments

`backend/experiments/runner.py::run_single` line 154 calls:
```
agent.select_action(state, predicted_load=0.5, grid_state=grid_state)
```
**`predicted_load` is hard-coded to `0.5` and never recomputed from the
LSTM.** The LSTM is therefore not on the critical path of any decision
in the paper experiments.

### Verdict

> **The LSTM does not influence any controller action in the Stage-26
> paper experiments.** Its only consumer is the dashboard's
> `predicted_load` field (returned to the SCADA cycle log) and the
> reasoning string (`_build_reasoning`, line 380–413 of
> `rl_agent.py`), which is dead text from the controller's
> perspective. **The Stage-26 ablation `no_lstm` vs `full_stack` is a
> no-op.**

---

## 3. Digital twin (Asset Health)

### Where the digital twin lives

`backend/digital_twin/twin.py::DigitalTwin` with
`health_risk_score ∈ [0, 1]`.

### Where the twin is consulted

The codebase has **no callsite that reads
`twin.health_risk_score` inside the controller loop**. A
`grep -rn "health_risk_score"` across `backend/` returns the
declaration, the alias, and the getter, but no consumer.

`scada.py` imports the digital twin indirectly only via telemetry, and
the runner never invokes the twin.

### Verdict

> **The digital twin does not influence any controller action in the
> Stage-26 paper experiments.** The `no_twin` ablation is a no-op.

---

## 4. Predictive healing / proactive overload response

### Where predictive healing lives

`scada.py::_predict_overloads` (line 201) — builds an
`overload_warnings` list based on the LSTM's `predicted_load`.

### Where predictive healing is consulted

`scada.py::execute_control_loop` line 121 — the warnings list is
**returned in the cycle envelope** but **never read by the controller
loop**. The DQN selects an action based on `state`, `predicted_load`,
and `raw_state`, but **not** on `overload_warnings`.

The Stage-26 paper experiment does not run `execute_control_loop`
anyway, so predictive healing is doubly disconnected.

### Verdict

> **Predictive healing does not influence any controller action in the
> Stage-26 paper experiments.** The `no_predictive` ablation is a
> no-op.

---

## 5. Hybrid storage (battery + supercapacitor)

### Where hybrid storage lives

* Battery discharge: `grid.nodes[*].use_battery(0.2)` (line 117 of
  runner).
* Supercapacitor discharge: `grid.nodes[*].use_supercapacitor(0.1)`
  (line 122).

### Where hybrid storage is triggered

These are **only triggered by `_dispatch_action`** when the controller
picks action id `1` (use_battery) or `2` (use_supercapacitor). They
are not triggered autonomously.

### What actually happens

* `rule_based` picks action `1` if any node has `deficit > 0`, else
  action `0`. It never picks `2`.
* `dqn_core_only` action-mask rule: action `2` is enabled only when
  `any(node.load > 1.2)`. Otherwise the supercapacitor is never used.

### Verdict

> **The supercapacitor is essentially never used** because action `2`
> is only enabled by an action-mask rule that almost never fires
> (load > 1.2 MW on a residential node is rare). The battery is
> occasionally used by both `rule_based` and `dqn_core_only` when a
> deficit is detected. The Stage-26 ablation `no_storage` is *also* a
> no-op because the runner does not gate the simulation clock on
> `enable_storage` (line 51 of the runner: *"The simulation clock is
> decoupled from storage"*).

---

## 6. Topology planner (Resilience-Aware Network Reconfiguration)

### Where the planner lives

`backend/planning/ai_planner.py::AIPlanner.plan()`.

### Where the planner is invoked

`topology_planning_final.json` shows one invocation on a deterministic
49-node grid. The planner's `expected_delta` is recorded but the
"after" KPIs are identical to the "before" KPIs — meaning **the
planner's accepted action did not produce a measurable change in the
metrics the harness records**.

### Verdict

> **The topology planner is not on the runtime hot path of any
> Stage-26 paper experiment.** It is a one-shot offline optimisation
> evaluated once. The Stage-26 ablation does not exercise it.

---

## 7. Reward shaping

### Where the reward shaping lives

`backend/models/rl_agent.py::compute_reward`. The Stage-26 paper
experiments run the DQN in `eval_mode()`, which disables exploration
and **disables gradient updates**. Reward shaping influences training,
not evaluation.

### Verdict

> **Reward shaping cannot influence Stage-26 evaluation results
> because the DQN is run in eval mode** (`runner.py` line 236 calls
> `agent.eval_mode()` immediately after constructing the agent). The
> `no_reward` ablation is therefore a no-op.

---

## 8. Rule-based controller

### What the rule-based controller actually does

`runner.py::_select_action`, line 162–167:
```python
if label == "rule_based" or not cfg.enable_dqn:
    for n in grid.nodes.values():
        deficit = float(getattr(n, "deficit", 0.0) or 0.0)
        if deficit > 0.0:
            return 1
    return 0
```

The rule-based controller picks action `1` (use_battery) if any node
reports a deficit, else action `0` (increase_generation). It **never**
picks action `2` (use_supercapacitor), `3` (shift_load) or `4`
(reroute_energy). Reroute is performed separately by the FLISR every
4 ticks, **regardless of the controller's choice**.

### Verdict

> The rule-based controller is a **2-action reactive policy** (deficit
> → battery, else → generation). It does *not* exercise the action
> space, the LSTM, the digital twin, the predictive healing, or the
> hybrid storage supercapacitor. The Stage-26 paper experiments
> therefore compare a 2-action reactive rule-based controller against a
> 5-action DQN that uses an action-mask heuristic. **This is not a
> full-stack vs. rule-based comparison in any meaningful sense.**

---

## 9. DQN controller (dqn_core_only)

### What the DQN actually does

`runner.py::_select_action` line 150–156 calls:
```python
state = grid.get_rl_state()
grid_state = grid.get_state() if hasattr(grid, "get_state") else None
decision = agent.select_action(
    state, predicted_load=0.5, grid_state=grid_state,
)
return int(decision["action_id"])
```

The DQN is run in `eval_mode()` (line 236), so it does greedy action
selection based on its freshly-seeded network weights and the
action-mask logic in `rl_agent.py::select_action` (lines 319–337).

The action mask is the most important piece of information flow:

* If `system.balance < -0.1`, action set = {0 (increase_generation),
  1 (use_battery)}.
* If `any(node.load > 1.2)`, action set += 2 (use_supercapacitor).
* If `any(node.failed or isolated)`, action set += 4 (reroute_energy).
* Action 3 (shift_load) is always allowed.

This mask is **the only place** where information other than the
state vector influences the DQN's choice. The LSTM is not used.
Digital twin is not used. Reward shaping is irrelevant in eval mode.

### Verdict

> **The DQN's only meaningful information channel in the Stage-26
> experiments is its action mask**, which encodes "deficit →
> generation/battery", "spike → supercapacitor", "fault →
> reroute_energy", "always → load shift". This is itself a small,
> hand-coded policy — but it has access to a 5-action space and
> learns a 64-unit Q-network on top.

---

## 10. Summary table

| Component | In production SCADA? | In Stage-26 paper harness? | Influences action in Stage-26? |
|---|:---:|:---:|:---:|
| LSTM forecast | yes | yes (but `predicted_load=0.5` hard-coded) | **NO** |
| Digital twin (`health_risk_score`) | yes (SCADA telemetry) | not invoked | **NO** |
| Predictive overload warnings | yes | not invoked | **NO** |
| Battery (action 1) | yes | yes | **YES** — via `_dispatch_action` |
| Supercapacitor (action 2) | yes | yes (mask) | rarely — mask rarely fires |
| EMS / cluster dispatch | yes (FLISR fallback) | yes (FLISR every 4 ticks) | YES |
| Topology planner | yes (one-shot) | not invoked | **NO** |
| Reward shaping | yes (training) | disabled (`eval_mode`) | **NO** |
| DQN network weights | yes | yes (`eval_mode`) | YES |
| Action-mask heuristic | yes | yes | YES |

---

## 11. Consequences for the Stage-40 result

The Stage-26 result — "DQN-only beats rule-based on ENS; full_stack
does not" — is therefore **not** evidence that LSTM / twin / predictive
healing add nothing. It is evidence that **the ablation harness never
exercised those components** in the first place. The Stage-26 harness
is a 5-action controller with FLISR-every-4-ticks, regardless of which
ablation flag is set.

The strongest claim the Stage-26 evidence supports is:

> **A 5-action DQN with a hand-coded action mask, evaluated greedily
> with freshly-seeded weights, beats a 2-action reactive rule-based
> controller on ENS** under 3-fault/80-tick scenarios on the EHM
> 49-node grid.

This is a small, defensible claim. It is **not** a claim about
integrated resilience frameworks, predictive healing, LSTM, or the
digital twin.

---

## 12. Recommendation

To test the *real* claim — that LSTM, twin, predictive healing and
hybrid storage add value — we need a harness that:

1. Invokes the real `ScadaControlCenter.execute_control_loop` for the
   full_stack config.
2. Invokes the same loop *with the relevant module disabled* for the
   no_* ablation rows.
3. Reports a per-controller metric trace so a difference (or absence
   thereof) is interpretable.

We do not implement this in Stage 41 because the user has explicitly
forbidden rebuilding the project. Instead, we document it as the
**necessary Stage-42 prerequisite** for any paper claim about the
integrated stack.
