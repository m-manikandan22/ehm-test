# Stage 42.5 — Scientific Validity Repair: Completion Report (`STAGE_42_5_COMPLETION_REPORT.md`)

**Date:** 2026-08-18
**Stage:** 42.5 (validity repair). No algorithm was modified during this
stage. All results are from controlled experiments on the existing harness
(≤ 10 seeds per comparison). Temp diagnostic scripts
(`_stage425_diag.py`, `_stage425_controlled.py`, `_stage425_probe.py`) were
removed after this report was written; raw run data is preserved in
`backend/experiments/results/stage425_controlled/controlled_dqn.json` and
all key numbers are quoted in this report and the companion audits.

---

## 1. Why a validity repair was needed

Stage 42 reported: LSTM "changes action selection" (mean ENS diff 0.29,
full_stack vs no_lstm); twin, predictive and reward ablations produced
exactly identical results; random beat every controller. Those results were
reproduced exactly (10-seed Scenario A: random 0.9376, rule_based 1.3761,
dqn_core_only 1.0618, full_stack 1.3527), then dissected to find **why**.
The audits in this stage show the reported numbers are real but their
**causal interpretation was wrong**.

## 2. What the audits established (evidence first)

### 2.1 Action space (`STAGE_42_5_ACTION_AUDIT.md`)
- Action 0 (`increase_generation`) targets a non-existent node `G0` → dead.
- Action 4 (`reroute_energy`) has an empty body → dead.
- Actions 1–3 modify load/generation but `_apply_time_curves` rewrites
  house load/gen from `_base_*` every step → **no persistent effect on
  healthy nodes**; only battery/supercap drains persist.
- Failed/isolated nodes' loads are **frozen** (curves and node.step skip
  them), which is the only channel through which controllers change ENS.

### 2.2 RL vs heuristic (`STAGE_42_5_RL_VS_HEURISTIC.md`)
- `predicted_load` (LSTM) is consumed only in the reasoning string; action
  identical for forecasts 0.05/0.5/0.95 (verified).
- `full_stack` vs `no_lstm` action differences are a **torch-RNG
  weight-init artifact**: `DemandForecaster()` is constructed before
  `DQNAgent()` and consumes torch RNG, changing DQN weights (max |Δw| =
  0.247, argmax flips). Not forecast influence.
- The harness DQN is **untrained**: buffer 0, steps_done 0, eval_mode; no
  `smart_warmup`/`store_experience` in the runner. The "DQN" is a random
  MLP behind a hand-coded mask.
- Twin health key (`health_aware_load_shift`) is **never read** by the DQN
  mask (verified: action identical with/without the key).
- `enable_reward_shaping` is read nowhere in the runner.
- Control: invoking `smart_warmup` does change the policy (shift_load share
  0.785 → 0.905, ENS 1.3704 → 1.0651), i.e. learning works when actually run
  — it just isn't run in the experiments.

### 2.3 Random baseline (`STAGE_42_5_RANDOM_BASELINE_AUDIT.md`)
- Random's ENS advantage is a **metric artifact**: its load-reduction
  actions (`use_supercapacitor`, `shift_load`) persist on failed/isolated
  houses, deflating the frozen-load ENS charge. Probe (seed 0): identical
  failed-node sets/durations for random vs rule_based, but rule_based keeps
  full frozen loads (H7=0.27 for 38 steps) while random's supercap draws
  drive them to 0.00 (28 of 38 steps). ENS 0.2374 vs 0.5444 on the same seed.
- The twin's Scenario-H "benefit" for rule_based (1.0705 vs 1.6807) is the
  same mechanism (switch from battery drain to load shift), not
  health-informed restoration.
- EMS has zero effect (ON vs OFF identical, 1.6807); predictive healing is
  advisory-only (ENS identical, events 80 vs 0); scenario demand/renewable
  multipliers are wiped by the first `grid.step()`.

### 2.4 Fairness
- `random` keeps FLISR+EMS on → fair physical layer for that baseline.
- DQN eval consumes one global-`random` draw per step → DQN rows run on a
  different grid noise realisation than rule_based/random rows at the same
  seed (unfair paired comparison, quantified in the audit).

## 3. Deliverables

| # | Item | Location | Status |
|---|---|---|---|
| 1 | Action-space audit (what each action does, survives or not) | `docs/STAGE_42_5_ACTION_AUDIT.md` | done |
| 2 | RL vs heuristic analysis (where decisions really come from) | `docs/STAGE_42_5_RL_VS_HEURISTIC.md` | done |
| 3 | Random baseline explanation + fairness audit | `docs/STAGE_42_5_RANDOM_BASELINE_AUDIT.md` | done |
| 4 | Controlled DQN experiment (4 variants × 10 seeds × Scenario A) | `experiments/results/stage425_controlled/controlled_dqn.json` + section 2.4 | done |
| 5 | DQN learning verification (untrained vs warmup-trained, 5 seeds) | section 2 | done |
| 6 | Twin controlled test (Scenario H, rule_based, twin ON/OFF, 5 seeds) | section 3 | done |
| 7 | Predictive healing controlled test (ON/OFF, 5 seeds) | section 4 | done |
| 8 | EMS controlled test (ON/OFF, 5 seeds) | section 5 | done |
| 9 | Scenario multiplier audit (direct grid-level wipe check) | section 6 | done |
| 10 | RNG fairness check (rule_based/random vs DQN consumption) | section 7 | done |
| 11 | Test suite audit and repair | `tests/test_stage42_integration.py` (32 tests, all pass) | done |
| 12 | Constraint compliance (≤10 seeds, no 100-seed run, no tuning) | this report | done |
| 13 | This report | `docs/STAGE_42_5_COMPLETION_REPORT.md` | done |
| 14 | Stage-43 gate evaluation | section 4 below | done |
| 15 | Accept conclusion that no AI signal is present; no code changed to force a result | section 5 | done |

## 4. Test-suite audit (item 11)

Previously vacuous or mislabeled tests, now repaired:

| Old test | Problem | Repair |
|---|---|---|
| `test_twin_registry_built` | ran two configs, asserted nothing | asserts twin ON vs OFF changes rule_based actions on Scenario H (real wiring) |
| `test_health_aware_bias_in_rule_based` | asserted `sum(action_counts) > 0` (trivially true) | asserts action 3 is actually used |
| `test_no_twin_differs_from_full_stack` | `assert True` | asserts a real runtime-path difference on Scenario H |
| `test_lstm_changes_action_selection` | passed for the *wrong* reason (RNG artifact) | replaced by `test_lstm_forecast_value_does_not_change_action` (honest) + `test_lstm_flag_changes_dqn_weights` (documents the artifact) |
| `test_different_seed_different_ens` | asserted `is not None` | asserts fault schedules differ and ENS differs |
| `test_demand_multiplier_applied` / `test_renewable_multiplier_applied` | asserted only spec constants, names over-claim | renamed `*_is_spec_only`; demand test additionally verifies the wipe through `grid.step()` |

Result: **32 passed in ~48 s**.

## 5. Controlled-experiment numbers (Scenario A, 10 seeds)

| Config | ENS mean (sd) | dominant actions |
|---|---|---|
| random | 0.9376 (0.657) | uniform mix (each ≈ 0.19–0.22) |
| rule_based | 1.3761 (0.705) | use_batt 1.00 |
| dqn_core_only | 1.0618 (0.666) | shift_load 0.77 |
| full_stack | 1.3527 (0.781) | use_scap 0.36, reroute 0.37, shift 0.27 |
| dqn_mask (clean, mask on) | 1.0623 (0.669) | shift_load 0.77 |
| dqn_unmasked (mask off) | 1.1461 (0.684) | shift 0.52, use_batt 0.30 |

Reading: `dqn_mask` ≈ `dqn_core_only` (EMS/storage flags are inert).
`full_stack` differs from `dqn_mask` only through the LSTM construction
weight artifact. Mask vs no-mask differs modestly; neither is trained.

## 6. Honest statement of what the architecture does contain

- FLISR performs the actual restoration on a fixed schedule; it is
  controller-independent.
- The rule-based controller reaches the twin's health signal (action 3
  override) — the only verified "twin → decision" path, and it acts through
  the frozen-load artifact, not through any change in restoration.
- EMS, predictive healing, LSTM forecast, reward shaping and the DQN do not
  influence any recorded outcome through their advertised mechanisms.

**The paper's proposed controller (DQN+LSTM+twin) contributes no verified
causal signal to the measured outcomes in the Stage-42 harness.**

## 7. Stage-43 gate evaluation

The task defines the gate as: the stage is acceptable **only if** the
system contains a genuine, verified AI/control contribution, or the
conclusion honestly states there is none.

**Assessment: the gate is NOT met for claiming an AI contribution.**
Per the task's own rule ("all conclusions acceptable; never change the
system to obtain a desired conclusion"), the correct Stage-43 outcome is a
paper/report that states the negative result with the evidence above:

- random beats the proposed controller, and the cause is a metric artifact;
- the DQN was never trained, the LSTM forecast never reaches selection, the
  twin never reaches the DQN;
- no algorithm changes were made in Stage 42.5 to reverse any of this.

**Recommended Stage-43 work items (as written in the paper, not executed
here, per the 100-seed/algorithm-change prohibition):**
1. Decide the paper's claim scope honestly (e.g. "FLISR + rule-based with
   twin bias" rather than "learned controller").
2. If a learned-controller claim is required, the correct path is an
   engineering fix (train the DQN via `smart_warmup` + in-run learning;
   wire `predicted_load` into the mask; fix actions 0/4; apply scenario
   multipliers to `_base_*`) followed by a fresh experiment — this is a
   design decision for the author, not a Stage-42.5 action.
3. No number in this stage was tuned; no 100-seed run was executed.

## 8. Reproducibility

Results JSON: `backend/experiments/results/stage425_controlled/controlled_dqn.json`
(controlled DQN experiment raw + summaries). Seeds: 0–9 (10-seed sections),
0–4 (5-seed sections). Deterministic per `set_global_seed` with the
documented torch-RNG caveat (which the audits quantify rather than hide).
