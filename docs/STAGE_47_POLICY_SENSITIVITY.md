# Stage 47 — Policy Sensitivity Report

## 1. Overview

Tests the Stage-47 trained DQN (checkpoint `dqn_stage47_storage_aware.pt`) on controlled storage SOC perturbations to measure Q-value sensitivity (LEVEL 2) and action sensitivity (LEVEL 3).

**Checkpoint:** `dqn_stage47_storage_aware.pt` (SHA-256: `316b1a91028ee9143390bc4fba289ffc845a92b94f94ba55015ad52920d029d5`)
**Training:** 20 episodes, seed 42, corrected storage observation

## 2. Battery SOC Sensitivity (Feature 73)

### 2.1 Controlled Perturbations

| State | Grid BAT SOC | Feature 73 | ||Delta Q||_2 | Action |
|-------|--------------|------------|--------------|--------|
| very_high_bat | 0.90 | 0.900 | - | 4 |
| high_bat | 0.80 | 0.800 | 1.38 | 4 |
| mid_high_bat | 0.60 | 0.600 | 2.76 | 4 |
| mid_bat | 0.50 | 0.500 | 1.38 | 4 |
| mid_low_bat | 0.40 | 0.400 | 1.38 | 4 |
| low_bat | 0.20 | 0.200 | 2.76 | 4 |
| very_low_bat | 0.10 | 0.100 | 1.38 | 4 |
| critical_bat | 0.05 | 0.050 | 0.69 | 4 |
| empty_bat | 0.00 | 0.000 | 0.69 | 4 |

### 2.2 Q-Value Range

| Action | Min Q | Max Q | Range |
|--------|-------|-------|-------|
| 0 (gen) | -1091.15 | -1085.63 | 5.52 |
| 1 (bat) | -1123.43 | -1117.76 | 5.67 |
| 2 (sc) | -1094.23 | -1088.72 | 5.52 |
| 3 (shift) | -1113.17 | -1107.56 | 5.62 |
| 4 (reroute) | -1085.97 | -1080.50 | 5.47 |

**Max Q-range: 5.67 (Action 1 - use_battery)**

### 2.3 Sensitivity Analysis

- **Linear response:** Q-values shift ~0.61 per 0.1 SOC decrement
- **Larger steps** at 0.2 SOC intervals (2.76 norm)
- **Action 1 (use_battery)** shows highest sensitivity to battery SOC
- **All states select Action 4** (policy still pinned)

## 3. Supercapacitor SOC Sensitivity (Feature 74)

### 3.1 Controlled Perturbations

| State | Grid SC SOC | Feature 74 | ||Delta Q||_2 | Action |
|-------|-------------|------------|--------------|--------|
| very_high_sc | 0.90 | 0.900 | - | 4 |
| high_sc | 0.80 | 0.800 | 0.054 | 4 |
| mid_high_sc | 0.60 | 0.600 | 0.108 | 4 |
| mid_sc | 0.50 | 0.500 | 0.054 | 4 |
| mid_low_sc | 0.40 | 0.400 | 0.054 | 4 |
| low_sc | 0.20 | 0.200 | 0.108 | 4 |
| very_low_sc | 0.10 | 0.100 | 0.054 | 4 |
| critical_sc | 0.05 | 0.050 | 0.027 | 4 |
| empty_sc | 0.00 | 0.000 | 0.027 | 4 |

### 3.2 Q-Value Range

| Action | Min Q | Max Q | Range |
|--------|-------|-------|-------|
| 0 (gen) | -1090.21 | -1089.98 | 0.22 |
| 1 (bat) | -1122.46 | -1122.25 | 0.21 |
| 2 (sc) | -1093.29 | -1093.08 | 0.21 |
| 3 (shift) | -1112.21 | -1111.99 | 0.22 |
| 4 (reroute) | -1085.03 | -1084.82 | 0.21 |

**Max Q-range: 0.22 (Action 0 - increase_generation)**

### 3.3 Sensitivity Analysis

- **Smaller response** than battery (~25x smaller Q-range)
- **Linear response:** ~0.025 per 0.1 SOC decrement
- **No action dominates sensitivity** - all actions shift similarly
- **All states select Action 4**

## 4. Joint Storage Sensitivity

| State | Grid BAT | Grid SC | Action | Notes |
|-------|----------|---------|--------|-------|
| both_high | 0.90 | 0.90 | 4 | |
| high_bat_low_sc | 0.90 | 0.10 | 4 | |
| low_bat_high_sc | 0.10 | 0.90 | 4 | |
| both_low | 0.10 | 0.10 | 4 | |
| both_mid | 0.50 | 0.50 | 4 | |
| high_bat_midlow_sc | 0.80 | 0.20 | 4 | |
| midlow_bat_high_sc | 0.20 | 0.80 | 4 | |

**All 7 joint states select Action 4.** No hybrid storage differentiation observed.

## 5. Feature Isolation (Single Variable Changes)

| Feature Changed | Delta Q Norm | Action Changed? |
|-----------------|--------------|-----------------|
| Battery SOC (0.50 -> 0.10) | 5.52 | No |
| Supercap SOC (0.50 -> 0.10) | 0.22 | No |
| LSTM Forecast (0.5 -> 0.9) | 1.48 | No |
| Twin Max Risk (0.0 -> 0.8) | 2.28 | No |

**Ranking by Q-sensitivity:**
1. Battery SOC (5.52) - STRONGEST
2. Twin Max Risk (2.28)
3. LSTM Forecast (1.48)
4. Supercap SOC (0.22) - WEAKEST

## 6. 5-Level Evidence Chain Classification

| Feature | L1 Feature | L2 State Delta | L3 Q Delta | L4 Action Delta | L5 Physical | Level |
|---------|------------|----------------|------------|-----------------|-------------|-------|
| Battery SOC | PASS | PASS | PASS (5.67) | FAIL | UNTESTED | **LEVEL 3** |
| Supercap SOC | PASS | PASS | PASS (0.22) | FAIL | UNTESTED | **LEVEL 3** |
| LSTM Forecast | PASS | PASS | PASS (1.48) | FAIL | UNTESTED | LEVEL 3 |
| Twin Max Risk | PASS | PASS | PASS (2.28) | FAIL | UNTESTED | LEVEL 3 |

**Both storage features reach LEVEL 3 (Q-value sensitivity demonstrated).**

## 7. Action Distribution

| Action | Count | Percentage |
|--------|-------|------------|
| 4 (reroute) | 25 | 100% |
| 0 (gen) | 0 | 0% |
| 1 (bat) | 0 | 0% |
| 2 (sc) | 0 | 0% |
| 3 (shift) | 0 | 0% |

**Policy remains pinned at Action 4 (reroute_energy) across all tested states.**

## 8. Comparison: Stage-44 vs Stage-47

| Metric | Stage-44 (Frozen) | Stage-47 (Trained) |
|--------|-------------------|---------------------|
| Battery SOC observable | NO (masked) | YES |
| Supercap SOC observable | NO (masked) | YES |
| Battery Q-range | 0.0 | 5.67 |
| Supercap Q-range | 0.0 | 0.22 |
| Policy action | 4 (pinned) | 4 (pinned) |
| Storage actions used in training | 0 | Yes (1, 2) |

## 9. Interpretation

**POSITIVE:**
- Battery SOC now produces STRONG Q-value sensitivity (LEVEL 3)
- Supercap SOC produces measurable Q-value sensitivity (LEVEL 3)
- Observation repair successful - features track grid storage
- DQN trained with corrected observation uses storage actions during training

**NEGATIVE:**
- Policy still pinned at Action 4 in evaluation
- No action flips observed in controlled tests
- Supercap sensitivity 25x weaker than battery
- Only 20 episodes of training (likely insufficient)

## 10. Recommendation

**Stage 48 should:**
1. Train for 100+ episodes with corrected observation
2. Test on scenarios with voltage dips (to trigger supercap value)
3. Compare physical outcomes (ENS, served load) between Stage-44 and Stage-47
4. Run ablation: storage vs no-storage to measure contribution