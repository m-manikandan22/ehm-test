# Stage-43 controlled validation (10 seeds)

Scenarios: A, E, G, H, J | Controllers: random, rule_based, untrained_dqn, trained_dqn, full_stack | Seeds: 10 | Runs: 250
Checkpoint: `C:\Users\ELCOT\Music\EHM-paper\backend\experiments\checkpoints\dqn_extended.pt`

## Pairing integrity (fingerprints)

Every (scenario, seed) must show identical grid/demand/renewable/fault fingerprints across all five controllers:

- ALL PAIRS MATCH

## Mean ENS (MWh) — lower is better

| Scenario | random | rule_based | untrained_dqn | trained_dqn | full_stack |
| --- | --- | --- | --- | --- | --- |
| A | 1.6079±0.9710 | 1.6263±0.9736 | 1.5984±0.9795 | 1.6263±0.9736 | 1.5984±0.9795 |
| E | 2.5028±2.0437 | 2.5366±2.0436 | 2.4821±2.0585 | 2.5366±2.0436 | 2.4821±2.0585 |
| G | 2.0128±1.1926 | 2.0128±1.1926 | 2.0128±1.1926 | 2.0128±1.1926 | 2.0128±1.1926 |
| H | 1.6079±0.9710 | 1.5617±0.9698 | 1.5617±0.9698 | 1.5617±0.9698 | 1.5617±0.9698 |
| J | 58.0179±15.8821 | 58.0571±15.9139 | 58.0571±15.9139 | 58.0571±15.9139 | 58.0571±15.9139 |

## Restoration rate

| Scenario | random | rule_based | untrained_dqn | trained_dqn | full_stack |
| --- | --- | --- | --- | --- | --- |
| A | 0.933 | 0.933 | 0.967 | 0.933 | 0.967 |
| E | 0.933 | 0.933 | 0.967 | 0.933 | 0.967 |
| G | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| H | 0.933 | 0.967 | 0.967 | 0.967 | 0.967 |
| J | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Paired comparisons (trained_dqn vs others)

Reported as `mean(other − trained_dqn)` over the 10 paired seeds; positive = trained_dqn has LESS ENS.

| Scenario | vs rule_based | vs untrained_dqn | vs random |
| --- | --- | --- | --- |
| A | +0.0000 (0/10 pairs) | +0.0279 (2/10 pairs) | +0.0183 (1/10 pairs) |
| E | +0.0000 (0/10 pairs) | +0.0545 (2/10 pairs) | +0.0337 (1/10 pairs) |
| G | +0.0000 (0/10 pairs) | +0.0000 (0/10 pairs) | +0.0000 (0/10 pairs) |
| H | +0.0000 (0/10 pairs) | +0.0000 (0/10 pairs) | -0.0463 (0/10 pairs) |
| J | +0.0000 (0/10 pairs) | +0.0000 (0/10 pairs) | +0.0392 (1/10 pairs) |

## Action counts (all scenarios pooled)

- **random**: {0: 1606, 1: 1514, 2: 1573, 3: 1685, 4: 1622}
- **rule_based**: {1: 7200, 3: 800}
- **untrained_dqn**: {0: 278, 1: 1674, 2: 4090, 3: 1348, 4: 610}
- **trained_dqn**: {2: 8000}
- **full_stack**: {0: 278, 1: 1674, 2: 4090, 3: 1348, 4: 610}
