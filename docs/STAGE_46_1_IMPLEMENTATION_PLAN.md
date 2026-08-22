# Stage 46.1 — Information-Flow & Ablation Repair (Implementation Plan)

## 1. Scope

Stage 46.1 verifies and, where genuinely broken, repairs the
information-flow plumbing that the Stage-44 trained-DQN ablations
(`full_stack`, `no_lstm`, `no_twin`, `no_ems`, `no_predictive`) depend
on. The Stage-45 ablation table is degenerate: every ablation cell
produces byte-identical fingerprints, which the Stage-46 statistical
audit already documented as a dedup bug in the *statistics* stage. This
stage asks a deeper question: **is the information actually flowing from
each feature group into the DQN state and Q-function at all?**

## 2. Constraints (unchanged from the Stage-46 mandate)

- The DQN checkpoint is **frozen**: `backend/experiments/checkpoints/dqn_stage44.pt`.
  SHA-256 = `eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493`
  (verified before and after all work; unchanged).
- No retraining, no architecture change, no reward change, no seed change,
  no checkpoint change.
- Only **genuine wiring bugs** are repaired. Ablation effects are never
  manufactured; scenario-coverage gaps and policy-property limits are
  documented, not papered over.
- The small diagnostic validation is 2 seeds × 4 scenarios (A, E, I, J) ×
  5 ablations = 40 runs; descriptive statistics only.

## 3. Feature groups and expected information path

| Group       | State features  | Source                                                              | Flag gate            |
|-------------|-----------------|---------------------------------------------------------------------|----------------------|
| LSTM        | `[72]`          | `DemandForecaster` on past 10-step aggregate history                 | `enable_lstm`        |
| Storage     | `[73, 74]`      | max house-node `battery_level` / `supercap_level`                    | n/a (state-derived)  |
| Twin        | `[75, 76, 77]`  | `TwinRegistry` health-risk stats                                     | `enable_twin`        |
| EMS         | — (external)    | `EnergyManagementSystem` (environment-side)                          | `enable_ems`         |
| Predictive  | — (external)    | `PredictiveSelfHealer.run` (never mutates grid)                      | `enable_predictive`  |

## 4. Root-cause investigation

### 4.1 LSTM — GENUINE WIRING BUG (repaired)

The Stage-44/45 validation harnesses fed the LSTM a **hard-coded constant
window** `[[0.5, 0.4, 0.0]] * 10` inside `_Stage44DQNAdapter._predicted_load`
instead of the real per-step aggregate history that training
(`stage44_dqn_training.py::_lstm_predict`) and the production runner
(`runner.run_single`, lines ~625–699) maintain.

Consequences:

- With LSTM enabled, the forecast was a **constant** `0.6099` on every
  scenario (probed empirically), not a function of the actual load.
- The `lstm_sequence` argument passed to `choose_action` was accepted via
  `**kwargs` and **silently ignored** by the adapter.

### 4.2 Twin — correctly wired, but zero signal on the Stage-45 set

The gate `twin is None if not enable_twin` correctly zeroes features
`[75, 76, 77]`. However the twin risk sources (`health_risk_score`) are
all zero on scenarios A/E/I/J because the degradation engine keeps
transformer health ≥ 0.4 over the simulation horizon (only scenario H
carries a `health_override={"T_A": 0.2}`, yielding risk 0.5). This is a
**scenario-coverage property**, not a wiring bug.

### 4.3 EMS / Predictive — external controllers, observationally invisible

- EMS *does* mutate the grid (probed: `STORAGE_BAT.battery_level`
  0.75→0.79, `S_MAIN.generation` 0→0.552, `S_MAIN.deficit` 2.5→1.948), but
  these effects are invisible to the DQN:
  - the storage SOC state features read **house** nodes only
    (`node_type == "house"`); `STORAGE_BAT` is `node_type="battery"`;
  - the S_MAIN generation boost is wiped by `node.step()` (substation
    `else` branch resets `generation=0`);
  - DQN actions 1/2 target `node_type == "house"` or the substrings
    `"storage_bat"`/`"storage_sc"`, which "battery"/"supercap" do not match.
- `PredictiveSelfHealer.run(grid, twin)` is pure — it never mutates the
  grid and reports `risk_count=0` on A/E/I/J. The harness calls the pure
  API; the physical path lives only in `runner._predictive_preparation(apply_physical=True)`.

Both are category-C (environment-side) information paths by design.

## 5. Repair applied (single genuine bug)

**`_Stage44DQNAdapter` now computes its forecast from the real per-run
history deque**, and both validation loops install and maintain that deque:

1. `set_lstm_history(history)` installs the `deque(maxlen=10)` of
   `(aggregate_load, aggregate_gen, weather_proxy)` triples (past-only).
2. `_predicted_load()`: when `enable_lstm=False` returns the exact `0.5`
   sentinel; when enabled, feeds the last ≤10 real observations to the
   forecaster (warm-up pad with the first observation when <10).
3. `_run_controller_on_scenario` (in `stage44_validation.py` **and**
   `stage45_validation.py`) creates the deque, computes the weather proxy
   from the scenario (`normal:0.2, storm:0.85, heatwave:0.5`), appends the
   aggregate `(load, gen)` **before** each forecast call, and wires the
   deque into the adapter.

## 6. Verification plan

1. Wiring check (compile + forecast varies with real history, sentinel
   exact).
2. Single-state experiment (9 deterministic states incl. scenario H) — full
   state vectors, per-feature diffs, Q-values, masked argmax, physical
   outcomes for all 5 configs on identical snapshots.
3. Full-episode argmax-flip scan on A/E/I/J (80 steps each).
4. 40-run diagnostic validation (2 seeds × 4 scenarios × 5 ablations) on
   the repaired harness.
5. Test suite `tests/test_stage46_1_information_flow.py` (8 tests) — all
   pass; existing Stage-43/44/45 tests unaffected.

## 7. Outcome

The LSTM wiring bug is fixed and the feature-level evidence chain
(feature present → state changes → Q changes) is now demonstrated for LSTM
(on all scenarios) and Twin (on scenario H). Action-level and
physical-level differentiation remains **absent on the Stage-45 scenario
set** because the frozen policy's masked argmax is pinned at action 4 for
every one of the 320 scanned steps — a property of the trained policy's
action gap, not of the wiring. This is documented honestly in
`STAGE_46_1_ABLATION_AUDIT.md` and `STAGE_46_1_COMPLETION_REPORT.md`.