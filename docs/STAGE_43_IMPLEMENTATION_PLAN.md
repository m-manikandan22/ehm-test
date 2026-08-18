# STAGE 43 — Implementation Plan

Status: PLANNING (document written before any code change)
Scope: repair the existing EHM implementation so that the architecture described in `main.md` is *actually* implemented, every claimed information path is a real code path, and each AI component has a causally testable physical effect.

Constraint: we repair and integrate; we do not tune to win, do not cherry-pick seeds, do not modify metric definitions to improve results, and do not replace DQN/LSTM/FLISR/twin/EMS/storage with new AI technology. The Stage-43 gate is a *scientific* gate (evidence of causal wiring), not "tests pass".

---

## 1. Current architecture (as actually implemented)

Modules and their real responsibilities:

| Module | File | Responsibility |
|---|---|---|
| Grid physics | `backend/simulation/grid.py` | node/edge state, `step()`, `update_generation()` + `_apply_time_curves()`, `update_power_flow()` (DC-PF + BFS `_simulate_energy_flow`), `flisr_9stage()`, `get_rl_state()` (72-dim), `get_lstm_input()` |
| Node physics | `backend/simulation/node.py` | per-node `step()`, `use_battery()`, `use_supercapacitor()`, `increase_generation()`, `shift_load()`, SOC levels |
| SCADA | `backend/simulation/scada.py` | `ScadaControlCenter` — telemetry, fault detection (ANN), LSTM forecast, DQN decision, 1-cycle action queue; production control loop |
| LSTM | `backend/models/lstm_model.py` | `DemandForecaster` — synthetic pretrain at startup, `predict(seq)` |
| DQN | `backend/models/rl_agent.py` | `DQNAgent` — 5 actions, MLP 64→64, replay buffer 2000, ε 1.0→0.05, target net every 20 steps, `smart_warmup` (rule-guided bootstrap, 150 steps), `select_action` with mask heuristics |
| Expert policy | `backend/rl/expert_policy.py` | rule ladder `choose_action(state, grid_state)` used for `smart_warmup` |
| Digital twin | `backend/digital_twin/twin.py`, `twin_registry.py` | per-asset health/age/risk (heuristic `health_risk_score`), registry with `sync()` |
| EMS | `backend/simulation/ems.py` | threshold-gated partial dispatch (absorption_ratio 0.5), priority allocation P1/P2/P3, PyPSA optional |
| Experiment harness | `backend/experiments/runner.py` | `run_single()` — the *only* path that produces experiment results |
| Info-flow glue | `backend/experiments/info_flow.py` | Stage-42 wiring: twin registry, predictive healer, EMS invocation, LSTM history |
| Metrics | `backend/experiments/research_metrics.py` | `record_step()` incl. ENS, fault events, restoration, EMS cycles, predictive events |
| Config | `backend/experiments/experiment_config.py` | `ExperimentConfig`, `ABLATION_CONFIGS` |
| Scenarios | `backend/experiments/scenario_matrix.py` | `ScenarioSpec` A–J, `build_scenario()` |

## 2. Runtime control path

Per step inside `run_single()` (runner.py:379–561), in order:

1. inject faults (runner.py:381)
2. `grid.update_power_flow()` (406)
3. append aggregate (load, gen, weather) to LSTM history (412)
4. tick twin registry (418, gated `enable_twin`)
5. predictive healer — advisory only (427)
6. LSTM forecast (438, gated `enable_lstm`)
7. build risk map from twins (459)
8. `_select_action` (467) → controller action id
9. `_dispatch_action(grid, action)` (476) → physical effect
10. `grid.step()` (484) → physics + `_apply_time_curves` wipe
11. `_run_ems(grid)` (490, gated `enable_ems`) → EMS dispatch
12. FLISR every 4 steps (497, gated `enable_flisr`)
13. `grid.update_power_flow()` (508) → settle
14. `collector.record_step(...)` (511) → metrics incl. ENS

## 3. Experiment control path

`run_experiment()` (runner.py:611) iterates (seed, weather_mode, config); for each: `make_scenario(...)` → `run_single(config, scenario, run_seed)` → manifest JSON. `set_global_seed(effective_seed)` (runner.py:264) is called once per run, then grid, rng, collector are built.

## 4. Stage-42.5 defects (13 findings, all verified empirically)

1. **Action 0 dead**: `_dispatch_action` targets node `"G0"` which does not exist in `_build_grid`; `increase_generation(0.5)` never executes (runner.py:120).
2. **Action 4 dead**: `reroute_energy` branch is `pass` (runner.py:138–140); FLISR, when enabled, is a separate loop step.
3. **Actions 1–3 not persistent**: `use_battery`/`use_supercapacitor`/`shift_load` only touch `house` nodes; their `generation`/`load` changes are overwritten by `_apply_time_curves` on the next `grid.step()` (grid.py:691,713). Only SOC drains persist.
4. **ENS metric artifact**: failed/isolated node loads are frozen (grid.py:707 skip + node.py `step` zeroing); `record_step` charges `load * (1/60)` even for failed/isolated nodes (research_metrics.py:136–138). Actions that only deflate frozen loads of failed houses (supercap/shift) lower ENS without restoring service → random policy "wins" by load deflation (ENS 0.2374 vs rule_based 0.5444, identical failure sets).
5. **LSTM has no causal path to decisions**: `predicted_load` only appears in the agent's reasoning string; selection is identical for 0.05/0.5/0.95.
6. **Ablation difference is a torch-RNG artifact**: constructing `DemandForecaster` before `DQNAgent` perturbs the shared torch RNG → different DQN weights (max |Δw| = 0.247, argmax flips). `no_lstm` vs `full_stack` difference is not caused by the forecast.
7. **Harness DQN is untrained**: `DQNAgent()` + `eval_mode()` (runner.py:366–369) → replay buffer 0, `steps_done` 0. All DQN rows are random-initialised networks.
8. **Twin never reaches the DQN mask**: the injected `grid_state["system"]["health_aware_load_shift"]` key is not read by the DQN mask (mask checks balance/spike/failed only, rl_agent.py:319–332). Twin affects only rule_based/random via `_select_action` (runner.py:174–207).
9. **Predictive healing advisory-only**: `_predictive_preparation` (info_flow.py:160) only records events; never mutates grid. Events 80 vs 0 but ENS identical.
10. **EMS has zero causal effect**: ENS identical with EMS ON vs OFF (1.6807). `_run_ems` constructs a fresh `EnergyManagementSystem(use_pypsa=False)` every call (info_flow.py:199); dispatch targets only battery/supercap nodes, which `_apply_time_curves` does not restore — but the effect is invisible in aggregate ENS.
11. **Scenario multipliers wiped**: `demand_mult`/`renew_mult` applied once before the loop (runner.py:299–312) then overwritten every step by `_apply_time_curves` from `_base_*`. Scenarios A–J differ only in faults, not profile.
12. **RNG contamination**: DQN eval `select_action` consumes one global `random.random()` per call → grid noise stream differs between controllers; rule_based/random consume none → paired comparisons are not paired on the environment.
13. **Dead flags / no twin path to DQN**: `enable_reward_shaping`, `enable_storage`, `enable_xai` are never read anywhere in `run_single`; twin affects only heuristic controllers (Scenario H: twin ON → all action 3, OFF → all action 1).

## 5. Root causes

- **R1 (architecture/ordering)**: `_apply_time_curves` recomputes house/generator load+generation from `_base_*` every step; controller/EMS effects on those attributes cannot persist by construction.
- **R2 (wiring)**: `predicted_load`, twin risk, predictive-healer, EMS reports are computed and recorded but never consumed by the decision/state chain (or consumed only for strings).
- **R3 (training)**: the experiment harness never invokes `smart_warmup`/`train_step`; there is no train/eval separation, no checkpoint, no learning evidence.
- **R4 (RNG)**: a single global seed is used for grid, controller and (implicitly) torch; controller inference perturbs the environment stream.
- **R5 (metrics)**: ENS is computed against frozen loads of failed/isolated nodes; there is no "would-be load" baseline, so restoration quality is mis-measured.
- **R6 (naming)**: action 0 targets a fictional bus `G0`; action 4 has no implementation in the runner path (it exists in SCADA's `_dispatch_control_signal` for switches, but the runner's FLISR block is the only topology-changing code).

## 6. Minimal corrections (ordered, each independently testable)

1. **RNG isolation** — introduce three explicit RNG streams: `environment_rng` (grid noise), `controller_rng` (random/heuristic controllers), `training_rng` (torch/agent). Record all three seeds + Git SHA in run results. Controller inference must not draw from the environment stream.
2. **Scenario multipliers** — store `_base_load`/`_base_generation` as base profiles and compute `load = base_profile * multiplier * curve` inside `_apply_time_curves` so the modifier persists for the whole run.
3. **Action space repair** — action 0 targets a real generator (e.g. first active `generator` node) with `increase_generation(0.5)`; action 4 performs real topology switching (close available tie switches / re-enable deactivated non-switch edges guarded by physical validity); actions 1–3 persistence follows from (1)+(2) (their load/gen changes persist within a step and remain visible until the next step's curves — this must be documented precisely, not faked).
4. **DQN training pipeline** — train DQN (warmup → replay → Bellman updates → target sync → ε schedule) on a *training* scenario (no fault or separate seed), checkpoint weights to `backend/experiments/checkpoints/<label>_<seed>.pt`; experiment runs load a checkpoint and set `training=False` (frozen eval). Expose `untrained_dqn` and `trained_dqn` controllers.
5. **LSTM → DQN state** — append `predicted_load` (and optionally forecast of critical load) to the DQN state vector (documented `state_t` layout, no future leakage: forecast uses history ≤ t). Causal test `test_lstm_changes_decision()`.
6. **Twin → DQN state** — append twin-derived features (max/mean `health_risk_score`, count of high-risk assets) to the state vector; remove the dead `health_aware_load_shift` mask hack. Controlled test that a health override changes decisions.
7. **Predictive healing physical effect** — implement a physical preparation action (e.g. pre-close tie switches / pre-arm storage for predicted-stressed assets) executed before the fault step; OFF-vs-ON causal experiment on Scenario H-type runs; event counts alone are insufficient.
8. **EMS persistence** — run one persistent `EnergyManagementSystem(use_pypsa=False)` per run (not per step), dispatch battery/supercap nodes with SOC and generation tracked; causal experiment: EMS OFF vs ON measured on SOC trajectory + aggregate metrics.
9. **Hybrid storage causal tests** — battery+supercap dispatch must change physical state and be measurable (SOC trajectory, voltage support) with and without storage-enabled flag.
10. **ENS repair** — ENS must represent would-be energy: compute demand baseline from base profiles (or pre-fault load) and charge ENS for failed/isolated nodes against that baseline; "load becomes zero" must not mean perfect restoration. Analytical tests over frozen-load grids.
11. **Mask policy separation** — the action mask enforces only *physically impossible* actions; learning/behaviour differences live in the network, not the mask.
12. **Dead flags** — remove or genuinely wire `enable_reward_shaping`, `enable_storage`, `enable_xai`; document each in the runtime control-flow doc.

Each repair ships with its own tests (Section 8); full suite must remain green after every repair (regression, ~12.5 min).

## 7. Files to change

| File | Change |
|---|---|
| `backend/experiments/runner.py` | RNG streams, checkpoint loading, persistent EMS, training flag, fingerprints, seed recording |
| `backend/simulation/grid.py` | persistent multipliers in `_apply_time_curves`; (action 4 helpers); frozen-load "would-be load" accessor |
| `backend/models/rl_agent.py` | state-vector extension hooks, train/eval separation, checkpoint save/load, remove dead mask key |
| `backend/experiments/info_flow.py` | persistent EMS, predictive-preparation physical path, state-vector feature plumbing |
| `backend/experiments/research_metrics.py` | ENS would-be-load accounting, EMS/predictive physical-effect metrics, seed/fingerprint fields |
| `backend/experiments/scenario_matrix.py` | multiplier persistence support, fingerprint helpers |
| `backend/simulation/ems.py` | (if needed) persistent-object lifecycle fixes |
| `backend/simulation/scada.py` | (production parity, if needed) action-4 switch toggling |
| `backend/tests/test_stage43_*.py` | new required tests (Section 8) |
| `docs/STAGE_43_*.md` | 12 required docs |

Explicitly unchanged: algorithms of DQN/LSTM/FLISR/twin/EMS/storage; metric *definitions* (except the ENS accounting fix, which is a measurement defect, documented in `STAGE_43_ENS_VALIDATION.md`).

## 8. Tests (required, 15 causal + regression)

Required causal tests (names fixed where given in the Stage-43 spec):

1. `test_controller_rng_does_not_change_environment` — a controller that draws N random numbers leaves the environment stream (grid noise) identical.
2. `test_paired_controllers_share_environment` — two controllers (incl. DQN) produce identical grid noise / fault sequence when compared.
3. `test_lstm_changes_decision()` — two state vectors differing only in `predicted_load` produce different DQN argmax for at least one probe state.
4. `test_high_demand_multiplier_persists` — with `demand_mult=1.5`, house load stays ~1.5× base profile across all steps.
5. `test_low_renewable_multiplier_persists` — with `renew_mult=0.2`, renewable generation stays ~0.2× profile across all steps.
6. `test_action_0_changes_physical_state` — action 0 raises generation of a real generator node.
7. `test_action_4_changes_topology` — action 4 closes a valid tie switch / re-activates a valid deactivated edge on a faulted grid.
8. `test_actions_persist_within_step` — actions 1–3 change load/generation and the change is observable after `update_power_flow()` within the step (documented scope of persistence).
9. `test_dqn_training_changes_policy` — `trained_dqn` (warmup+updates+checkpoint) differs from `untrained_dqn` on held-out states; learning evidence (Q-values / argmax shift).
10. `test_dqn_checkpoint_reload_frozen` — reload from checkpoint with `training=False` gives identical actions across calls (no buffer writes, no learning).
11. `test_twin_changes_dqn_decision` — state with high-risk twin features changes DQN argmax relative to healthy twin state.
12. `test_predictive_healing_changes_physical_state` — predictive preparation mutates grid (switch/storage state) before the predicted fault step; OFF-vs-ON run differ in physical state, not only event counts.
13. `test_ems_changes_physical_state` — EMS ON vs OFF produce different battery SOC trajectories and different total generation on battery nodes.
14. `test_hybrid_storage_causal` — storage dispatch changes an outcome metric (SOC/voltage/ENS) when `enable_storage` differs.
15. `test_ens_counts_would_be_load` — failed/isolated nodes contribute their frozen would-be load to ENS; a run that merely zeroes loads does not reduce ENS.

Plus: analytical ENS tests, seed-recording test (master/env/controller/training seeds + Git SHA in results), fingerprint test (same seed ⇒ same `grid_hash`/`demand_hash`/`renewable_hash`/`fault_hash`; different seed ⇒ different), and a regression run of the full suite after each repair.

## 9. Risks

- **RNG refactor breaks determinism guarantees** (existing tests assert same-seed reproducibility). Mitigation: keep `set_global_seed` semantics for env stream; add `controller_rng`/`training_rng` seeded from derived values; run full suite immediately after repair 1.
- **Multiplier persistence changes all scenario numbers** (load levels move to 1.5×/0.2× etc. per spec). Mitigation: fingerprint hashes + recompute Stage-43 controlled validation with ≤10 seeds; do not re-run Stage-42 400-run matrix.
- **ENS repair invalidates historical ENS numbers** — expected and documented; all Stage-43 numbers are computed with the repaired definition.
- **Training pipeline cost**: warmup + updates must stay ≤ a few minutes per seed on CPU (existing constraint). Mitigation: cap buffer/warmup size, checkpoint early.
- **Action-4 topology switching may destabilise DC-PF** (thermal trips). Mitigation: enforce physical validity guard (only close switches with capacity headroom), wrap in try/except with validity log, test on Scenario A/E/G/H/J.
- **Prevent scope creep** — every change must map to a finding in Section 4 and a test in Section 8.

## 10. Rollback strategy

- One commit/checkpoint per repair step; each step's tests must pass before the next.
- `git stash`-free workflow: record pre-repair numbers in `docs/STAGE_43_RUNTIME_CONTROL_FLOW.md` appendix before each repair (ENS under current definition, Q-magnitude, etc.).
- If a repair fails its causal test after two attempts, revert that step, document the failure in the completion report, and mark the corresponding gate item PARTIAL — CONTINUE.
- No repair is irreversible: changes are confined to the files in Section 7; algorithms and metric *definitions* other than ENS stay untouched.
- Final verdict must be exactly one of: **PASS**, **PARTIAL — CONTINUE**, or **BLOCKED**, with per-item evidence from the 22-item gate checklist in `STAGE_43_COMPLETION_REPORT.md`.
