# Stage 46.1 — Ablation Audit

Audit of why the Stage-45 trained-DQN ablation table is degenerate, and
what Stage 46.1 establishes about each ablation cell.

## 1. The measured facts (frozen checkpoint)

### 1.1 Single-state experiment (`experiments/results/stage46_1/`)

9 deterministic states across scenarios A, E, I, J, H. For every state,
all five configs were evaluated on **identical** environment snapshots
(deep-copied for the physical probes):

| Ablation       | ‖Δstate‖                | ‖ΔQ‖                 | Δargmax |
|----------------|-------------------------|----------------------|---------|
| `no_lstm`      | 0.112 – 0.143 (feat 72) | 1.31 – 1.67          | never   |
| `no_twin`      | 0.0 (A/E/I/J), 0.5005 (H) | 0.0 (A/E/I/J), 6.38 (H) | never |
| `no_ems`       | 0.0                     | 0.0                  | never   |
| `no_predictive`| 0.0                     | 0.0                  | never   |

### 1.2 Full-episode scan (`stage46_1_scan_argmax_flips.py`)

For scenarios A/E/I/J (80 steps each, seed 0): the masked argmax is
**action 4 in all 320 steps** for `full_stack`, `no_lstm`, and `no_twin`.
Forecast now varies with real history (0.06–0.22 across scenarios) — the
wiring is correct — but the Q-shift it induces (~0.58/head) is below the
action-gap margin of the frozen policy.

### 1.3 40-run diagnostic validation (`validation_40runs.json`)

2 seeds × 4 scenarios × 5 ablations, run on the **repaired** harness:
40/40 runs valid, and **all 8 (scenario, seed) cells are byte-identical
across ablations** in every fingerprint key, action-count histogram,
selected-action sequence, and metric. This reproduces the Stage-45
degeneracy even after the wiring repair — confirming the degeneracy is a
**policy property**, not the harness wiring.

## 2. Attribution of the degeneracy

| Ablation       | Stage-45 degeneracy cause                                                                  |
|----------------|--------------------------------------------------------------------------------------------|
| `no_lstm`      | Wiring bug (constant forecast) **fixed**; residual degeneracy = policy action gap.         |
| `no_twin`      | Wiring correct; scenario set never elevates twin risk (A/E/I/J → zero features).           |
| `no_ems`       | EMS effects land outside the DQN observation (architectural).                              |
| `no_predictive`| Healer is pure in the harness; no state channel exists (architectural).                    |

## 3. What was repaired vs. documented

**Repaired (genuine wiring bug):** the LSTM eval path now consumes the
real per-step aggregate history and the `no_lstm` cell uses the exact 0.5
sentinel — aligning the harness with training and the production runner.

**Documented as architectural/policy (not repaired, not fabricated):**

- Twin risk never rises on the Stage-45 scenario set (scenario coverage).
- EMS and Predictive-healer effects are observationally disjoint from the
  DQN state by design.
- The frozen policy's argmax is pinned at action 4 across the entire
  scanned state space, so no feature perturbation below the gap can change
  behavior.

## 4. Honest statement for the paper

Stage 46.1 demonstrates the information channels at the feature and
Q-value levels (L1–L3) for LSTM and Twin, and proves EMS/Predictive have
no DQN-visible channel by design. Action- and physical-level ablation
differentiation (L4–L5) is **not** attainable with this frozen checkpoint
on the Stage-45 scenario set without retraining — which is out of scope.
Any downstream claim that "the ablations do not matter" must be reworded
to "the ablations do not change the frozen policy's decisions on these
scenarios," which is a statement about the trained policy, not about the
absence of the features.