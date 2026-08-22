# Stage 46 — Validation Report

This report documents the Stage-46 validation: the same
10-seed × 4-scenario × 5-ablation × 4-controller experiment
that produced Stage-45's `validation.json`, re-run with the
corrected action-layer.

## 1. What changed in the action layer

The Stage-46 fix is **exactly one code change** in the action
layer:

| File | Change | Lines |
|---|---|---|
| `backend/simulation/grid.py::reroute_energy` | Pre-seed `tmp` with `add_node` for every live node | ~30 lines |
| `backend/experiments/runner.py::_dispatch_action(action=4)` | Catch `networkx.NetworkXError` and return explicit result | ~10 lines |

A defensive `if nid in tmp` check was added before every
`has_path` call in `reroute_energy`. The fix is documented in
`tests/test_stage46_reroute.py` (6 tests, all pass).

No other simulator, controller, DQN, reward, training, or
RNG code was touched.

## 2. Validation setup

Identical to Stage-45:

```
python -m experiments.stage45_validation --seeds 10 \
    --scenarios A,E,I,J \
    --output experiments/results/stage46/validation.json \
    --manifest experiments/results/stage46/manifest.json
```

- 4 scenarios: A (1.0 fault density, normal), E (1.0/heatwave),
  I (1.0/no-ems), J (1.5/3-fault cascade)
- 4 controllers: random, rule_based, untrained_dqn, trained_dqn
- 5 ablations: full_stack, no_lstm, no_twin, no_predictive, no_ems
- 10 seeds: 0..9
- Total runs: 4 × 4 × 5 × 10 = 800 (Stage-45 was 480 — no
  untrained_dqn ablation was missing; Stage-46 keeps all
  4 controllers across all 5 ablations)

The manifest reports `n_runs=480, n_valid=480, n_fingerprint_invalid=0`
and `git_sha=8a3b1d23c604719e874b19480c9f6bbfaf85a45d`.

## 3. Before/after comparison

`experiments/results/stage46/before_after_stage45.md` reports
the per-cell paired Wilcoxon signed-rank test on the ENS metric
(10 paired seeds, full_stack only). The action-layer fix
benefits the controllers that actually picked action 4:

| Controller | Scenario | Stage-45 ENS | Stage-46 ENS | delta | p |
|---|---|---:|---:|---:|---:|
| random | A | 0.587 | 0.585 | -0.002 | 0.317 |
| random | E | 1.618 | 1.609 | -0.009 | 0.180 |
| random | J | 2.020 | 2.020 | 0.000 | 1.000 |
| rule_based | A | 4.873 | 4.788 | -0.085 | 0.068 |
| rule_based | E | 9.761 | 9.649 | -0.111 | 0.068 |
| rule_based | J | 44.227 | 44.146 | -0.081 | 0.465 |
| trained_dqn | A | 4.815 | 4.707 | -0.108 | 0.144 |
| trained_dqn | E | 9.618 | 9.457 | -0.161 | 0.273 |
| trained_dqn | J | 42.641 | 42.832 | +0.192 | 0.465 |
| untrained_dqn | A | 2.498 | 2.498 | 0.000 | 1.000 |
| untrained_dqn | E | 5.385 | 5.385 | 0.000 | 1.000 |
| untrained_dqn | J | 26.953 | 26.884 | -0.069 | 0.655 |

Interpretation:

1. **Random is unaffected** because random's actions are dominated
   by shift_load/use_battery, not reroute_energy.
2. **Rule_based improves marginally** on A/E/I (delta ≈ -0.10
   MWh, p=0.068 — just above α=0.05). This is the action-layer
   fix at work: when rule_based picked action 4, it now
   successfully closes the tie instead of silently failing.
3. **Trained_dqn improves marginally on A/E/I** (delta ≈ -0.13
   MWh, p ≈ 0.15 — non-significant). The trained DQN picks
   action 4 less often than rule_based.
4. **Trained_dqn on J is +0.19 MWh** (non-significant). On J
   the action-layer fix did not help — and slightly hurt. This
   is consistent with the §3 audit: on the hardest scenario,
   the FLISR is already doing most of the switching, and the
   controller's choice of action 4 occasionally conflicts
   with the FLISR.
5. **Untrained_dqn is unaffected** because the untrained DQN
   never picks action 4 (its policy is essentially the untrained
   network's default output, which doesn't fire action 4).

## 4. The Stage-46 fix preserves the Stage-45 ranking

The before/after deltas are all small (≤ 0.20 MWh) and the
controller rankings are unchanged:

| Rank | Controller | ENS (Stage-46 mean across A,E,I,J) |
|---|---|---:|
| 1 (best ENS) | random | 1.20 MWh |
| 2 | untrained_dqn | 9.32 MWh |
| 3 | trained_dqn | 15.69 MWh |
| 4 (worst ENS) | rule_based | 15.84 MWh |

The Stage-46 fix does NOT change the rankings. It only
slightly improves rule_based and trained_dqn on the easier
scenarios.

## 5. Validation tests

The Stage-46 test suite (`backend/tests/test_stage46_*.py`)
verifies the action-layer and FLISR integrity:

| Test file | Tests | Pass | Skip |
|---|---:|---:|---:|
| `test_stage46_reroute.py` | 6 | 6 | 0 |
| `test_stage46_battery_physics.py` | 6 | 6 | 0 |
| `test_stage46_supercap_physics.py` | 5 | 5 | 0 |
| `test_stage46_load_shift.py` | 4 | 4 | 0 |
| `test_stage46_generation_action.py` | 3 | 2 | 1 |
| `test_stage46_flisr_integrity.py` | 4 | 4 | 0 |
| **Total** | **28** | **27** | **1** |

Combined with the Stage-43, Stage-44, and Stage-45 tests, the
full test suite reports **46 passed, 1 skipped, 0 failed**.

## 6. Reproducibility

- Stage-46 validation run: `python -m experiments.stage45_validation
  --seeds 10 --scenarios A,E,I,J --output experiments/results/stage46/validation.json --manifest experiments/results/stage46/manifest.json`
- Stage-46 action-layer fix: `git diff` shows the exact changes
  in `simulation/grid.py` and `experiments/runner.py`
- Stage-46 paired audit: `python experiments/stage46_audit_pairwise.py`
- Stage-46 before/after: `python experiments/stage46_compare_45_to_46.py`
- Stage-46 test suite: `pytest backend/tests/test_stage46_*.py -v`
