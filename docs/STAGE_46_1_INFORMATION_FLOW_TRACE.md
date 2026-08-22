# Stage 46.1 — Information-Flow Trace

This document traces, for every Stage-44 decision feature group, the
complete information path from source to Q-function, using the FROZEN
checkpoint `dqn_stage44.pt` (SHA-256
`eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493`,
state_dim=78, n_actions=5).

## 1. Evidence chain definition

For each group we seek the five-level chain:

1. **L1 — Feature present** — the group's features occupy a slot in the
   78-dim state under the relevant flag.
2. **L2 — State changes** — toggling the flag changes the state vector.
3. **L3 — Q changes** — the state change moves the Q-values (norm of the
   per-head delta).
4. **L4 — Action changes** — the masked argmax flips.
5. **L5 — Physical outcome changes** — the flipped action changes ENS /
   served energy / voltage / critical interruption.

## 2. State layout (verified against `build_extended_state`)

| Index | Feature            | Source                                              |
|-------|--------------------|-----------------------------------------------------|
| 0–71  | Legacy 72-dim      | `SmartGrid.get_rl_state()`                           |
| 72    | LSTM forecast      | `DemandForecaster` on past 10 aggregate triples      |
| 73    | battery SOC        | max `battery_level` over `node_type=="house"` nodes  |
| 74    | supercap SOC       | max `supercap_level` over `node_type=="house"` nodes |
| 75    | twin max risk      | max `health_risk_score` over registered twins        |
| 76    | twin mean risk     | mean `health_risk_score` over registered twins       |
| 77    | twin high fraction | fraction of twins with risk ≥ 0.5                    |

## 3. LSTM channel (repaired)

**Bug (before):** `_Stage44DQNAdapter._predicted_load()` fed a hard-coded
`[[0.5, 0.4, 0.0]] * 10` window to the forecaster. Probed forecast on
every scenario was the constant **0.6099**; the real-history values the
training loop and `runner.run_single` compute were never used. The
`lstm_sequence` argument to `choose_action` was silently ignored.

**Repair:** the adapter now reads a real per-run `deque(maxlen=10)` of
`(aggregate_load, aggregate_gen, weather_proxy)` installed by
`set_lstm_history`; both validation loops append the aggregate before each
forecast. `enable_lstm=False` returns the exact `0.5` sentinel.

**Probed forecast ranges over a full 80-step episode (seed 0):**

| Scenario | forecast min | forecast max | old broken constant |
|----------|--------------|--------------|---------------------|
| A        | 0.0636       | 0.1829       | 0.6099              |
| E        | 0.1182       | 0.2185       | 0.6099              |
| I        | 0.0636       | 0.1829       | 0.6099              |
| J        | 0.0645       | 0.1217       | 0.6099              |

The forecast now genuinely varies with the real load history (L1 + L2
for the LSTM channel).

**Single-state sensitivity (9 deterministic states):** toggling
`enable_lstm` changed the state by `‖Δstate‖ = 0.112–0.143` (feature 72
only) and the Q-vector by `‖ΔQ‖ = 1.31–1.67` (≈0.58 per head). **L3
reached.** In no probed state did the masked argmax flip (**L4 not
reached**), and across all 320 scanned episode steps the policy stayed on
action 4 for full, no_lstm, and no_twin alike.

## 4. Twin channel

**L1:** features 75–77 gated by `enable_twin`. **L2:** on scenario H
(health_override `T_A: 0.2`), the pre-aged twin registry yields risk 0.5
and `‖Δstate‖ = 0.5005` when the flag is toggled; on A/E/I/J the twin
risks are all zero so the state is unchanged. **L3:** on H,
`‖ΔQ‖ = 6.38`; on A/E/I/J, `0.0`. **L4/L5:** not reached (argmax pinned at 4).

The twin channel is correctly wired; the Stage-45 scenario set simply
never raises transformer health risk, so the channel carries no signal
there.

## 5. Storage channel

**L1:** features 73–74 always present (state-derived). **L2:** no flag
toggles these; they only change via house-node battery/supercap
physics. **L3:** Q is measurably sensitive to these features (probed
earlier at ≈ +4.6 per feature pair). On the Stage-45 scenarios the
house-node SOC trajectory is identical across ablations, so the channel
does not differentiate cells.

## 6. EMS channel (external / environment-side)

`EMS.run()` mutates the grid (verified: battery 0.75→0.79,
S_MAIN.generation 0→0.552, S_MAIN.deficit 2.5→1.948), but every mutation
lands outside the DQN observation:

- battery SOC features read only `node_type=="house"`; `STORAGE_BAT` is
  `"battery"`;
- substation generation is reset by `node.step()`;
- actions 1/2 target `"house"` / `"storage_bat"` / `"storage_sc"` — none
  match `"battery"` / `"supercap"`.

Hence toggling `enable_ems` cannot change the state, the Q-vector, or the
action. This is an architectural property, documented as such.

## 7. Predictive channel (external / pure)

`PredictiveSelfHealer.run(grid, twin)` never mutates the grid; probed
`risk_count=0`, `action_count=0` on A/E/I/J. The harness invokes the pure
API, so the channel has no observable effect on the DQN. The physical
path (`runner._predictive_preparation(apply_physical=True)`) is exercised
only by the production runner, not the ablation harness.

## 8. Level-5 demonstration where actions differ

Because the frozen policy's masked argmax is **pinned at action 4 for all
320 scanned steps** (and in all 9 single-state probes), no ablation
produces a different action, and therefore no ablation produces a
different physical outcome on the Stage-45 scenario set. The physical
comparison logic is exercised and validated in
`stage46_1_information_flow.py` (identical pre-action snapshots, deep
copies) but records `physical_changed=false` everywhere. This is a policy
property of the frozen checkpoint, explicitly out of scope for repair.