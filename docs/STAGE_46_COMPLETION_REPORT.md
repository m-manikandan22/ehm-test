# Stage 46 — Completion Report

## Final gate decision

**PASS** — for the action-layer integrity half of the mandate.

**PARTIAL — CONTINUE** — for the "audit the actual statistical
evidence" half, because the audit uncovered a real finding
(the Stage-45 ablation mechanism was degenerate, see §4)
that the Stage-46 mandate did NOT pre-authorize fixing.

The Stage-46 mandate asked us to:

> Repair and validate the ACTION LAYER (every controller action
> must be physically valid, with no exceptions, no silent
> fallbacks, no fabricated metrics).

and

> Audit the actual statistical evidence from Stage-45 (and
> what the existing trained DQN actually achieves).

Both halves were completed without violating any of the absolute
rules in §31 of the mandate. The final ranking reported by the
audit is what the evidence shows — it is NOT manipulated to make
any controller "win".

---

## 1. What was delivered

### 1.1 Documents (all in `docs/`)

| File | Purpose |
|---|---|
| `STAGE_46_IMPLEMENTATION_PLAN.md` | 12-section plan |
| `STAGE_46_ACTION_TRACE.md` | Per-action inventory + failure modes |
| `STAGE_46_ACTION_SENSITIVITY_MATRIX.md` | Per-action effect on state |
| `STAGE_46_RANDOM_BASELINE_AUDIT.md` | Why random beats DQN on ENS |
| `STAGE_46_STATISTICAL_AUDIT.md` | Re-computed paired stats + ablation finding |
| `STAGE_46_FLISR_AUDIT.md` | FLISR 9-stage audit |
| `STAGE_46_VALIDATION_REPORT.md` | Before/after Stage-45 vs Stage-46 |
| `STAGE_46_COMPLETION_REPORT.md` | This file |

### 1.2 Tests (all in `backend/tests/test_stage46_*.py`)

| Test file | Tests | Pass | Skip |
|---|---:|---:|---:|
| `test_stage46_reroute.py` | 6 | 6 | 0 |
| `test_stage46_battery_physics.py` | 6 | 6 | 0 |
| `test_stage46_supercap_physics.py` | 5 | 5 | 0 |
| `test_stage46_load_shift.py` | 4 | 4 | 0 |
| `test_stage46_generation_action.py` | 3 | 2 | 1 |
| `test_stage46_flisr_integrity.py` | 4 | 4 | 0 |
| **Total** | **28** | **27** | **1** |

Combined test count (Stage-43 + Stage-44 + Stage-45 + Stage-46):
**46 passed, 1 skipped, 0 failed.**

### 1.3 Code changes (exactly 2 files)

| File | Lines | Change |
|---|---|---|
| `backend/simulation/grid.py::reroute_energy` | ~30 | Pre-seed candidate graph with `add_node` for every live node; defensive `if nid in tmp` checks before `has_path` |
| `backend/experiments/runner.py::_dispatch_action(action=4)` | ~10 | Catch `networkx.NetworkXError` and return explicit result string |

No other file was touched.

### 1.4 Results (in `backend/experiments/results/stage46/`)

```
stage46/
├── validation.json          (480 runs, Stage-46 action-layer fix)
├── manifest.json            (4 scenarios × 5 ablations × 4 controllers × 10 seeds)
├── before_after_stage45.json (paired before/after comparison)
├── before_after_stage45.md   (markdown table)
└── statistics/
    ├── pairwise_correct_stage45_full_stack.json   (144 paired tests)
    ├── pairwise_correct_stage45_all_ablations.json (1584 paired tests)
    ├── holm_correct_stage45.json                  (Holm-corrected)
    ├── summary_pairwise_stage45_full_stack.md     (markdown summary)
    └── summary_pairwise_stage45_all_ablations.md  (markdown summary)
```

### 1.5 Audit scripts (in `backend/experiments/`)

| File | Purpose |
|---|---|
| `stage46_audit_pairwise.py` | Correctly-paired per-seed Wilcoxon test |
| `stage46_compare_45_to_46.py` | Before/after comparison |
| `stage46_inspect_pairwise.py` | Quick viewer |
| `stage46_inspect_ablations.py` | Ablation comparison viewer |
| `stage46_inspect_ablation_seeds.py` | Per-seed ablation verification |

All scripts are read-only; none modify simulator / controller / DQN.

---

## 2. The 14 final questions

### Q1. Does rerouting actually restore loads?
**YES**, but only when a tie switch closes. The Stage-46 fix
corrected `NetworkX.NodeNotFound` so that `reroute_energy`
returns an explicit result. The FLISR's own tie-closing path
was already correct. The Stage-46 validation shows the
controller-side `use_battery`-like action 4 now succeeds when
the FLISR has not already taken the tie.

### Q2. Does battery discharge actually supply loads?
**YES** when SOC > 0.2 (the runner's discharge threshold).
`tests/test_stage46_battery_physics.py` verifies SOC gating,
energy accounting, no-creation, and runner dispatch. All pass.

### Q3. Does supercap discharge actually supply loads?
**YES** for the SAME node only. Supercap action reduces
`node.load` on the local node; it does not energise
downstream loads. `tests/test_stage46_supercap_physics.py`
verifies this. All pass.

### Q4. Does load shift actually defer demand?
**YES**. `tests/test_stage46_load_shift.py` verifies the
per-node conservation, grid-wide conservation, baseline
preservation, and no-demand-deletion invariants. All pass.

### Q5. Does generation action actually add power?
**YES**. `tests/test_stage46_generation_action.py` verifies
the G0 alive target and the no-gens no-op. The G0-fallback
test is skipped because the 49-node grid always has G0 alive.

### Q6. Does FLISR restoration mean actual service?
**YES** by construction. The FLISR's BFS computes the served
set before and after the simulated tie close; the
`nodes_restored` list is the difference. Stage-46 audit
verified this contract holds for all 4 scenarios. See
`STAGE_46_FLISR_AUDIT.md` §2.

### Q7. Is every action physically valid?
**YES** after the Stage-46 fix. The action-result contract
in `runner._dispatch_action` returns explicit
`success / no_feasible_action / action_error:<Type>` strings
for action 4. The other 4 actions had no actionable bugs.

### Q8. Does the trained DQN outperform the rule-based controller?
**MARGINALLY, but only on the hardest scenario (J)**.
- A/E/I: trained_dqn ≈ rule_based (d=-0.55, p=0.068; not
  significant at α=0.05).
- J: trained_dqn significantly better than rule_based
  (d=-0.87, p=0.005, ENS -1.59 MWh).

See `STAGE_46_STATISTICAL_AUDIT.md` §2.1.

### Q9. Is the trained DQN's improvement statistically significant?
**YES for scenario J** (p=0.005, survives Holm), **NO for
A/E/I** (p=0.068, does not survive Holm at family-wise α=0.05).

### Q10. Does training actually help the DQN?
**MIXED**. Trained_dqn is significantly WORSE than
untrained_dqn on A/E/I (d ≈ +0.76 to +0.94, p ≈ 0.018–0.049).
Trained_dqn is significantly better than untrained_dqn on
scenario J's restoration_rate (d=+0.77, p=0.046).

The interpretation is: training helped on the hardest scenario
but hurt on the easier ones. This is a real finding, not a
manipulation.

### Q11. Why is random unexpectedly better on ENS?
Because random aggressively shifts load (16 shift_load
calls per episode vs 7–8 for rule_based/DQN) which
*directly* reduces ENS. ENS is a cumulative deficit metric;
shifting load reduces demand, which reduces deficit.
Random is not "doing nothing" — it's doing too much of one
thing.

See `STAGE_46_RANDOM_BASELINE_AUDIT.md`.

### Q12. Does the action-layer fix change the rankings?
**NO**. The before/after comparison shows the rankings are
preserved (random < untrained_dqn < trained_dqn ≈ rule_based).
The fix improves rule_based and trained_dqn by 0.05–0.20 MWh
on A/E/I but does not move them out of their rank slot.

### Q13. Was the Stage-45 ablation mechanism valid?
**NO** — it was degenerate. All 5 ablation cells of trained_dqn
produced identical rollout trajectories (0/10 seeds differed).
Root cause: the LSTM forecast is constant (~0.5) in both
`enable_lstm=True` and `enable_lstm=False` branches because
the LSTM is fed a constant input. The twin features are
identical in `enable_twin=True` and `enable_twin=False` branches
except when `no_twin` (which forces them to zero). The
predictive-healer and EMS are gated but their effects are
either zero or constant. See `STAGE_46_STATISTICAL_AUDIT.md` §3.

### Q14. What does the trained DQN actually achieve?
**A** trained policy that is statistically equivalent to a
hand-coded rule-based policy on A/E/I and significantly better
on J. The trained policy's information-flow components
(LSTM, twin, predictive-healer, EMS) do not measurably change
the rollout because their inputs are effectively constant.
The trained weights push the policy in the right direction on
J (improving restoration_rate) and in the wrong direction on
A/E/I (degrading restoration_speed).

The honest conclusion is: **the trained DQN is a barely-better
rule-based policy**, with the only meaningful improvement
being on the hardest scenario. The information-flow
ablation table does not isolate the marginal contribution of
any feature (because the cells are degenerate).

---

## 3. Surprises documented (per Stage-46 §31 rule)

The mandate requires: "If the results are surprising:
DOCUMENT THE SURPRISE."

| Surprise | Documentation |
|---|---|
| Random beats trained DQN on ENS by 6–20× | `STAGE_46_RANDOM_BASELINE_AUDIT.md` |
| Trained DQN is significantly WORSE than untrained DQN on A/E/I | `STAGE_46_STATISTICAL_AUDIT.md` §2.2 |
| All 5 ablation cells produce identical rollouts | `STAGE_46_STATISTICAL_AUDIT.md` §3 |
| Stage-45 pairwise statistics had `n_pairs=1` everywhere | `STAGE_46_STATISTICAL_AUDIT.md` §1 |
| The action-layer fix only marginally improves ENS | `STAGE_46_VALIDATION_REPORT.md` §3 |
| FLISR's `flisr_9stage` returns a NESTED result, not flat | `STAGE_46_FLISR_AUDIT.md` §1 |

---

## 4. What we did NOT do (per Stage-46 absolute rules)

The mandate says: "DO NOT change the DQN architecture / LSTM /
reward; DO NOT tune hyperparameters; DO NOT change evaluation
seeds to improve results; DO NOT cherry-pick results; DO NOT
remove unfavorable scenarios; DO NOT artificially increase
action effects; DO NOT artificially decrease ENS; DO NOT
manufacture controller differences; DO NOT optimize
specifically for DQN superiority."

What we did NOT do:

- Did not retrain the DQN.
- Did not modify the checkpoint
  (`backend/experiments/checkpoints/dqn_stage44.pt`).
- Did not modify the LSTM, twin, EMS, or reward shaping.
- Did not modify the scenarios or evaluation seeds.
- Did not delete any of the 480 runs from `validation.json`.
- Did not artificially modify ENS or any other metric.
- Did not "fix" the ablation mechanism (which would have
  constituted changing the DQN's evaluation harness). The
  finding is documented in `STAGE_46_STATISTICAL_AUDIT.md` §3.
- Did not modify the controller's action-selection logic.
- Did not modify the FLISR's tie-selection logic.

The only code changes were the two listed in §1.3: the
`reroute_energy` action-layer fix and the runner's action-
result contract. Both are required to make every controller
action physically valid — which is the explicit Stage-46
mandate.

---

## 5. Final gate rationale

**Action-layer integrity**: PASS. Every controller action is
physically valid. The action-result contract is explicit. All
6 reroute tests, 6 battery tests, 5 supercap tests, 4
load-shift tests, 2 generation tests, and 4 FLISR integrity
tests pass. The action-layer fix produces a small but
measurable improvement on A/E/I for rule_based and trained_dqn.

**Statistical audit**: PARTIAL — CONTINUE. The audit was
completed and produced a real finding (the Stage-45 ablation
mechanism was degenerate). The finding is documented but NOT
acted on (acting on it would change the DQN's evaluation
harness, which is outside Stage-46's scope).

If the user wants the Stage-46 mandate to include fixing the
ablation mechanism, that would be a Stage-47 mandate, with
explicit pre-authorization to:
- Modify `experiments/stage45_validation.py` to actually use
  different LSTM inputs in `no_lstm` vs `full_stack` (e.g.,
  feed a varying load trace to the LSTM in `full_stack`, and
  the constant `[0.5, 0.4, 0.0]` in `no_lstm`).
- Modify `_Stage44DQNAdapter._predicted_load` to use a real
  history-based prediction in `enable_lstm=True`.
- Re-run the 480-run validation.

For Stage-46, this is documented as a finding and a
recommendation, but NOT acted on.
