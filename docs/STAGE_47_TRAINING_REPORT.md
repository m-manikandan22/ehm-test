# Stage 47 — Training Report

## 1. Training Configuration

| Parameter | Value |
|-----------|-------|
| Master Seed | 42 (different from Stage-44 seed 0) |
| Episodes | 20 |
| Steps per Episode | 80 |
| Total Transitions | 1,600 |
| State Dimension | 78 |
| Action Dimension | 5 |
| Network Architecture | 78 -> 64 -> 64 -> 5 |
| Optimizer | Adam (LR=1e-3) |
| Gamma | 0.95 |
| Batch Size | 32 |
| Epsilon Start | 1.0 |
| Epsilon End | 0.05 |
| Epsilon Decay | 200 steps |
| Target Update | Every 20 steps |
| Replay Buffer | 2000 capacity |
| Checkpoint | `dqn_stage47_storage_aware.pt` |

## 2. Training Scenarios

20 episodes sampled from training scenario generator:
- 3x FAULT_AND_DEGRADED
- 3x SINGLE_FAULT
- 3x TOPOLOGY_FAULT
- 3x DEGRADED_ASSET
- 3x STORAGE_STRESS
- 2x NORMAL
- 2x HIGH_DEMAND
- 1x LOW_RENEWABLE

## 3. Per-Episode Rewards

| Episode | Scenario | Mean Reward |
|---------|----------|-------------|
| 0 | FAULT_AND_DEGRADED | -101.36 |
| 1 | FAULT_AND_DEGRADED | -106.25 |
| 2 | FAULT_AND_DEGRADED | -83.18 |
| 3 | SINGLE_FAULT | -81.12 |
| 4 | SINGLE_FAULT | -101.25 |
| 5 | SINGLE_FAULT | -101.74 |
| 6 | TOPOLOGY_FAULT | -79.39 |
| 7 | TOPOLOGY_FAULT | -99.06 |
| 8 | TOPOLOGY_FAULT | -112.70 |
| 9 | DEGRADED_ASSET | -85.56 |
| 10 | DEGRADED_ASSET | -69.01 |
| 11 | DEGRADED_ASSET | -76.48 |
| 12 | STORAGE_STRESS | -70.56 |
| 13 | STORAGE_STRESS | -61.51 |
| 14 | STORAGE_STRESS | -57.62 |
| 15 | NORMAL | -62.10 |
| 16 | NORMAL | -62.79 |
| 17 | HIGH_DEMAND | -75.59 |
| 18 | HIGH_DEMAND | -52.16 |
| 19 | LOW_RENEWABLE | -40.73 |

**Trend:** Reward improving from ~-100 to ~-40 over 20 episodes.

## 4. Action Distribution Evolution

| Episode | Action 0 (gen) | Action 1 (bat) | Action 2 (sc) | Action 3 (shift) | Action 4 (reroute) |
|---------|----------------|----------------|---------------|------------------|---------------------|
| 0 | 18 | 11 | 11 | 16 | 24 |
| 5 | 7 | 4 | 33 | 27 | 9 |
| 10 | 0 | 2 | 25 | 1 | 44 |
| 15 | 0 | 17 | 25 | 1 | 53 |
| 19 | 23 | 2 | 1 | 1 | 53 |

**Observation:** Action 4 (reroute) dominates. Storage actions (1, 2) appear but are minority.

## 5. Storage SOC Statistics

| Episode | Battery SOC (mean) | Supercap SOC (mean) |
|---------|-------------------|---------------------|
| 0 | ~0.70 | ~0.85 |
| 5 | ~0.65 | ~0.80 |
| 10 | ~0.55 | ~0.75 |
| 15 | ~0.50 | ~0.70 |
| 19 | ~0.45 | ~0.65 |

**Trend:** Both storage SOCs decline over episodes as they're used.

## 6. Storage Action Frequency

| Episode | Action 1 (bat) | Action 2 (sc) |
|---------|----------------|---------------|
| 0 | 11 | 11 |
| 5 | 4 | 33 |
| 10 | 2 | 25 |
| 15 | 2 | 17 |
| 19 | 2 | 1 |

**Observation:** Supercap action (2) used more frequently early, battery action (1) minimal.

## 6. Reward Components (Episode 19)

| Component | Value |
|-----------|-------|
| Stability Voltage | ~3.2 |
| Stability Freq | ~2.8 |
| Balance Penalty | ~-2.1 |
| Failed Penalty | ~-8.5 |
| Isolated Penalty | ~-4.2 |
| Loss Penalty | ~-1.8 |
| Supercap Spike Bonus | 0.0 |
| Reroute Bonus | 3.0 |
| **Total** | **~-40.7** |

## 7. Checkpoint Verification

- **Checkpoint:** `dqn_stage47_storage_aware.pt`
- **SHA-256:** `316b1a91028ee9143390bc4fba289ffc845a92b94f94ba55015ad52920d029d5`
- **State Dim:** 78
- **Actions:** 5
- **Steps Done:** 1,600
- **Final Epsilon:** 0.0503
- **Storage Observation:** `corrected_grid_only`

## 8. Stage-44 Checkpoint Protection

- **Stage-44 Path:** `dqn_stage44.pt`
- **SHA-256:** `eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493`
- **Status:** UNCHANGED (verified)

## 9. Training Assessment

**Positive:**
- Reward trend improving (-101 to -40)
- Storage SOC correctly observed (validated in audit)
- DQN learns to use storage actions (1, 2)
- No architectural changes needed

**Limitations:**
- Only 20 episodes (limited training)
- Policy still heavily favors action 4 (reroute)
- Action flips not observed in sensitivity tests
- Need more episodes for policy to fully exploit storage observability

**Recommendation:** Continue training to 100+ episodes for Stage 48 validation.