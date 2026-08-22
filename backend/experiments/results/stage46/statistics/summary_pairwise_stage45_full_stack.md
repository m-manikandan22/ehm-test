# Stage 46 — Paired Statistical Audit (stage45_full_stack)

Computed on the PER-SEED runs of the validation set. Every test pairs 10 seeds across the two cells (5+ minimum for Wilcoxon). Cohen's d is paired. Holm correction applied across all per-(cell_a, cell_b, scen, metric) tests.

Total paired tests: 144

## Per-cell means (full_stack only, ENS in MWh)

| Controller | Scenario | n | mean ENS | std | min | max |
|---|---|---:|---:|---:|---:|---:|
| random | A | 10 | 0.5874 | 0.4411 | 0.0938 | 1.6385 |
| random | E | 10 | 1.6184 | 0.8538 | 0.4623 | 3.4556 |
| random | I | 10 | 0.5919 | 0.4447 | 0.0938 | 1.6440 |
| random | J | 10 | 2.0198 | 0.5946 | 1.3496 | 3.3113 |
| rule_based | A | 10 | 4.8733 | 1.5296 | 2.7781 | 8.3590 |
| rule_based | E | 10 | 9.7608 | 1.9041 | 6.6928 | 13.9337 |
| rule_based | I | 10 | 4.8733 | 1.5296 | 2.7781 | 8.3590 |
| rule_based | J | 10 | 44.2272 | 10.4069 | 30.8331 | 59.5803 |
| trained_dqn | A | 10 | 4.8147 | 1.5461 | 2.7781 | 8.3590 |
| trained_dqn | E | 10 | 9.6182 | 1.9452 | 6.6928 | 13.9337 |
| trained_dqn | I | 10 | 4.8422 | 1.5324 | 2.7781 | 8.3590 |
| trained_dqn | J | 10 | 42.6406 | 9.4017 | 30.1601 | 56.7093 |
| untrained_dqn | A | 10 | 2.4983 | 2.1125 | 0.0727 | 5.1205 |
| untrained_dqn | E | 10 | 5.3846 | 4.4773 | 0.2056 | 10.1246 |
| untrained_dqn | I | 10 | 2.5341 | 2.1460 | 0.0727 | 5.1899 |
| untrained_dqn | J | 10 | 26.9532 | 23.6243 | 1.0457 | 59.0108 |

## Paired tests (selected contrasts)

### trained_dqn vs rule_based (full_stack)

| scenario | metric | n | mean_a | mean_b | diff | d | p | class |
|---|---|---:|---:|---:|---:|---:|---:|---|
| A | avg_restoration_steps | 10 | 38.7538 | 39.7610 | -1.0071 | -0.383 | 0.2733 | NON-SIGNIFICANT_IMPROVEMENT |
| A | critical_load_interruption_steps | 10 | 75.7000 | 75.7000 | -0.0000 | -0.000 | 1.0000 | NO_MEANINGFUL_DIFFERENCE |
| A | energy_not_served_mwh | 10 | 4.8147 | 4.8733 | -0.0585 | -0.550 | 0.0679 | NON-SIGNIFICANT_IMPROVEMENT |
| A | restoration_rate | 10 | 0.3851 | 0.3785 | +0.0067 | +0.194 | 0.6547 | NO_MEANINGFUL_DIFFERENCE |
| A | total_customer_minutes_interrupted | 10 | 382.9000 | 394.7000 | -11.8000 | -0.592 | 0.0679 | NON-SIGNIFICANT_IMPROVEMENT |
| E | avg_restoration_steps | 10 | 21.9167 | 21.6000 | +0.3167 | +0.022 | 1.0000 | NO_MEANINGFUL_DIFFERENCE |
| E | critical_load_interruption_steps | 10 | 80.0000 | 80.0000 | -0.0000 | -0.000 | 1.0000 | NO_MEANINGFUL_DIFFERENCE |
| E | energy_not_served_mwh | 10 | 9.6182 | 9.7608 | -0.1425 | -0.649 | 0.0679 | NON-SIGNIFICANT_IMPROVEMENT |
| E | restoration_rate | 10 | 0.2086 | 0.1551 | +0.0536 | +0.616 | 0.1088 | NON-SIGNIFICANT_IMPROVEMENT |
| E | total_customer_minutes_interrupted | 10 | 585.6000 | 595.5000 | -9.9000 | -0.534 | 0.1088 | NON-SIGNIFICANT_IMPROVEMENT |
| I | avg_restoration_steps | 10 | 38.9857 | 39.7610 | -0.7752 | -0.674 | 0.0679 | NON-SIGNIFICANT_IMPROVEMENT |
| I | critical_load_interruption_steps | 10 | 75.7000 | 75.7000 | -0.0000 | -0.000 | 1.0000 | NO_MEANINGFUL_DIFFERENCE |
| I | energy_not_served_mwh | 10 | 4.8422 | 4.8733 | -0.0311 | -0.552 | 0.0679 | NON-SIGNIFICANT_IMPROVEMENT |
| I | restoration_rate | 10 | 0.3785 | 0.3785 | -0.0000 | -0.000 | 1.0000 | NO_MEANINGFUL_DIFFERENCE |
| I | total_customer_minutes_interrupted | 10 | 389.5000 | 394.7000 | -5.2000 | -0.662 | 0.0679 | NON-SIGNIFICANT_IMPROVEMENT |
| J | avg_restoration_steps | 10 | 96.7000 | 156.4667 | -59.7667 | -0.571 | 0.0464 | SIGNIFICANT_IMPROVEMENT |
| J | critical_load_interruption_steps | 10 | 326.5000 | 326.5000 | -0.0000 | -0.000 | 1.0000 | NO_MEANINGFUL_DIFFERENCE |
| J | energy_not_served_mwh | 10 | 42.6406 | 44.2272 | -1.5866 | -0.873 | 0.0051 | SIGNIFICANT_IMPROVEMENT |
| J | restoration_rate | 10 | 0.1239 | 0.0828 | +0.0410 | +0.737 | 0.0679 | NON-SIGNIFICANT_IMPROVEMENT |
| J | total_customer_minutes_interrupted | 10 | 3958.8000 | 4245.9000 | -287.1000 | -0.796 | 0.0077 | SIGNIFICANT_IMPROVEMENT |

### trained_dqn vs untrained_dqn (full_stack)

| scenario | metric | n | mean_a | mean_b | diff | d | p | class |
|---|---|---:|---:|---:|---:|---:|---:|---|
| A | avg_restoration_steps | 10 | 38.7538 | 20.9207 | +17.8331 | +0.714 | 0.0630 | NON-SIGNIFICANT_DEGRADATION |
| A | critical_load_interruption_steps | 10 | 75.7000 | 46.5000 | +29.2000 | +0.882 | 0.0431 | SIGNIFICANT_DEGRADATION |
| A | energy_not_served_mwh | 10 | 4.8147 | 2.4983 | +2.3165 | +0.763 | 0.0280 | SIGNIFICANT_DEGRADATION |
| A | restoration_rate | 10 | 0.3851 | 0.4746 | -0.0895 | -0.443 | 0.2367 | NON-SIGNIFICANT_DEGRADATION |
| A | total_customer_minutes_interrupted | 10 | 382.9000 | 263.4000 | +119.5000 | +0.941 | 0.0180 | SIGNIFICANT_DEGRADATION |
| E | avg_restoration_steps | 10 | 21.9167 | 12.7214 | +9.1952 | +0.962 | 0.0280 | SIGNIFICANT_DEGRADATION |
| E | critical_load_interruption_steps | 10 | 80.0000 | 52.1000 | +27.9000 | +0.774 | 0.0679 | NON-SIGNIFICANT_DEGRADATION |
| E | energy_not_served_mwh | 10 | 9.6182 | 5.3846 | +4.2336 | +0.768 | 0.0499 | SIGNIFICANT_DEGRADATION |
| E | restoration_rate | 10 | 0.2086 | 0.2500 | -0.0414 | -0.333 | 0.2489 | NON-SIGNIFICANT_DEGRADATION |
| E | total_customer_minutes_interrupted | 10 | 585.6000 | 431.2000 | +154.4000 | +0.763 | 0.0630 | NON-SIGNIFICANT_DEGRADATION |
| I | avg_restoration_steps | 10 | 38.9857 | 22.8874 | +16.0983 | +0.653 | 0.1282 | NON-SIGNIFICANT_DEGRADATION |
| I | critical_load_interruption_steps | 10 | 75.7000 | 46.5000 | +29.2000 | +0.882 | 0.0431 | SIGNIFICANT_DEGRADATION |
| I | energy_not_served_mwh | 10 | 4.8422 | 2.5341 | +2.3082 | +0.761 | 0.0280 | SIGNIFICANT_DEGRADATION |
| I | restoration_rate | 10 | 0.3785 | 0.4417 | -0.0633 | -0.353 | 0.2489 | NON-SIGNIFICANT_DEGRADATION |
| I | total_customer_minutes_interrupted | 10 | 389.5000 | 278.3000 | +111.2000 | +0.855 | 0.0180 | SIGNIFICANT_DEGRADATION |
| J | avg_restoration_steps | 10 | 96.7000 | 67.5000 | +29.2000 | +0.184 | 0.4631 | NO_MEANINGFUL_DIFFERENCE |
| J | critical_load_interruption_steps | 10 | 326.5000 | 244.4000 | +82.1000 | +0.532 | 0.0796 | NON-SIGNIFICANT_DEGRADATION |
| J | energy_not_served_mwh | 10 | 42.6406 | 26.9532 | +15.6874 | +0.705 | 0.3743 | NON-SIGNIFICANT_DEGRADATION |
| J | restoration_rate | 10 | 0.1239 | 0.0636 | +0.0602 | +0.772 | 0.0464 | SIGNIFICANT_IMPROVEMENT |
| J | total_customer_minutes_interrupted | 10 | 3958.8000 | 3789.2000 | +169.6000 | +0.230 | 0.5754 | NON-SIGNIFICANT_DEGRADATION |

### trained_dqn vs random (full_stack)

| scenario | metric | n | mean_a | mean_b | diff | d | p | class |
|---|---|---:|---:|---:|---:|---:|---:|---|
| A | avg_restoration_steps | 10 | 38.7538 | 17.2667 | +21.4871 | +0.673 | 0.0745 | NON-SIGNIFICANT_DEGRADATION |
| A | critical_load_interruption_steps | 10 | 75.7000 | 31.5000 | +44.2000 | +2.262 | 0.0051 | SIGNIFICANT_DEGRADATION |
| A | energy_not_served_mwh | 10 | 4.8147 | 0.5874 | +4.2273 | +3.378 | 0.0051 | SIGNIFICANT_DEGRADATION |
| A | restoration_rate | 10 | 0.3851 | 0.4917 | -0.1065 | -0.442 | 0.1386 | NON-SIGNIFICANT_DEGRADATION |
| A | total_customer_minutes_interrupted | 10 | 382.9000 | 172.7000 | +210.2000 | +3.113 | 0.0051 | SIGNIFICANT_DEGRADATION |
| E | avg_restoration_steps | 10 | 21.9167 | 32.5067 | -10.5900 | -0.463 | 0.2026 | NON-SIGNIFICANT_IMPROVEMENT |
| E | critical_load_interruption_steps | 10 | 80.0000 | 42.8000 | +37.2000 | +1.878 | 0.0051 | SIGNIFICANT_DEGRADATION |
| E | energy_not_served_mwh | 10 | 9.6182 | 1.6184 | +7.9998 | +5.471 | 0.0051 | SIGNIFICANT_DEGRADATION |
| E | restoration_rate | 10 | 0.2086 | 0.5742 | -0.3656 | -1.888 | 0.0069 | SIGNIFICANT_DEGRADATION |
| E | total_customer_minutes_interrupted | 10 | 585.6000 | 275.2000 | +310.4000 | +2.403 | 0.0051 | SIGNIFICANT_DEGRADATION |
| I | avg_restoration_steps | 10 | 38.9857 | 16.8083 | +22.1774 | +0.729 | 0.0593 | NON-SIGNIFICANT_DEGRADATION |
| I | critical_load_interruption_steps | 10 | 75.7000 | 30.0000 | +45.7000 | +2.595 | 0.0051 | SIGNIFICANT_DEGRADATION |
| I | energy_not_served_mwh | 10 | 4.8422 | 0.5919 | +4.2503 | +3.422 | 0.0051 | SIGNIFICANT_DEGRADATION |
| I | restoration_rate | 10 | 0.3785 | 0.4717 | -0.0932 | -0.498 | 0.0926 | NON-SIGNIFICANT_DEGRADATION |
| I | total_customer_minutes_interrupted | 10 | 389.5000 | 178.5000 | +211.0000 | +2.968 | 0.0051 | SIGNIFICANT_DEGRADATION |
| J | avg_restoration_steps | 10 | 96.7000 | 8.2000 | +88.5000 | +0.772 | 0.0180 | SIGNIFICANT_DEGRADATION |
| J | critical_load_interruption_steps | 10 | 326.5000 | 131.6000 | +194.9000 | +1.429 | 0.0051 | SIGNIFICANT_DEGRADATION |
| J | energy_not_served_mwh | 10 | 42.6406 | 2.0198 | +40.6208 | +4.544 | 0.0051 | SIGNIFICANT_DEGRADATION |
| J | restoration_rate | 10 | 0.1239 | 0.0856 | +0.0383 | +0.379 | 0.3454 | NON-SIGNIFICANT_IMPROVEMENT |
| J | total_customer_minutes_interrupted | 10 | 3958.8000 | 3446.3000 | +512.5000 | +0.752 | 0.0469 | SIGNIFICANT_DEGRADATION |

### rule_based vs untrained_dqn (full_stack)

| scenario | metric | n | mean_a | mean_b | diff | d | p | class |
|---|---|---:|---:|---:|---:|---:|---:|---|
| A | avg_restoration_steps | 10 | 39.7610 | 20.9207 | +18.8402 | +0.752 | 0.0357 | SIGNIFICANT_DEGRADATION |
| A | critical_load_interruption_steps | 10 | 75.7000 | 46.5000 | +29.2000 | +0.882 | 0.0431 | SIGNIFICANT_DEGRADATION |
| A | energy_not_served_mwh | 10 | 4.8733 | 2.4983 | +2.3750 | +0.791 | 0.0117 | SIGNIFICANT_DEGRADATION |
| A | restoration_rate | 10 | 0.3785 | 0.4746 | -0.0961 | -0.478 | 0.1763 | NON-SIGNIFICANT_DEGRADATION |
| A | total_customer_minutes_interrupted | 10 | 394.7000 | 263.4000 | +131.3000 | +1.070 | 0.0117 | SIGNIFICANT_DEGRADATION |
| E | avg_restoration_steps | 10 | 21.6000 | 12.7214 | +8.8786 | +0.670 | 0.0747 | NON-SIGNIFICANT_DEGRADATION |
| E | critical_load_interruption_steps | 10 | 80.0000 | 52.1000 | +27.9000 | +0.774 | 0.0679 | NON-SIGNIFICANT_DEGRADATION |
| E | energy_not_served_mwh | 10 | 9.7608 | 5.3846 | +4.3761 | +0.805 | 0.0117 | SIGNIFICANT_DEGRADATION |
| E | restoration_rate | 10 | 0.1551 | 0.2500 | -0.0950 | -0.677 | 0.0464 | SIGNIFICANT_DEGRADATION |
| E | total_customer_minutes_interrupted | 10 | 595.5000 | 431.2000 | +164.3000 | +0.819 | 0.0277 | SIGNIFICANT_DEGRADATION |
| I | avg_restoration_steps | 10 | 39.7610 | 22.8874 | +16.8736 | +0.685 | 0.0687 | NON-SIGNIFICANT_DEGRADATION |
| I | critical_load_interruption_steps | 10 | 75.7000 | 46.5000 | +29.2000 | +0.882 | 0.0431 | SIGNIFICANT_DEGRADATION |
| I | energy_not_served_mwh | 10 | 4.8733 | 2.5341 | +2.3392 | +0.775 | 0.0117 | SIGNIFICANT_DEGRADATION |
| I | restoration_rate | 10 | 0.3785 | 0.4417 | -0.0633 | -0.353 | 0.2489 | NON-SIGNIFICANT_DEGRADATION |
| I | total_customer_minutes_interrupted | 10 | 394.7000 | 278.3000 | +116.4000 | +0.900 | 0.0117 | SIGNIFICANT_DEGRADATION |
| J | avg_restoration_steps | 10 | 156.4667 | 67.5000 | +88.9667 | +0.704 | 0.0679 | NON-SIGNIFICANT_DEGRADATION |
| J | critical_load_interruption_steps | 10 | 326.5000 | 244.4000 | +82.1000 | +0.532 | 0.0796 | NON-SIGNIFICANT_DEGRADATION |
| J | energy_not_served_mwh | 10 | 44.2272 | 26.9532 | +17.2740 | +0.756 | 0.0499 | SIGNIFICANT_DEGRADATION |
| J | restoration_rate | 10 | 0.0828 | 0.0636 | +0.0192 | +0.337 | 0.2850 | NON-SIGNIFICANT_IMPROVEMENT |
| J | total_customer_minutes_interrupted | 10 | 4245.9000 | 3789.2000 | +456.7000 | +0.723 | 0.0180 | SIGNIFICANT_DEGRADATION |

### rule_based vs random (full_stack)

| scenario | metric | n | mean_a | mean_b | diff | d | p | class |
|---|---|---:|---:|---:|---:|---:|---:|---|
| A | avg_restoration_steps | 10 | 39.7610 | 17.2667 | +22.4943 | +0.709 | 0.0593 | NON-SIGNIFICANT_DEGRADATION |
| A | critical_load_interruption_steps | 10 | 75.7000 | 31.5000 | +44.2000 | +2.262 | 0.0051 | SIGNIFICANT_DEGRADATION |
| A | energy_not_served_mwh | 10 | 4.8733 | 0.5874 | +4.2859 | +3.450 | 0.0051 | SIGNIFICANT_DEGRADATION |
| A | restoration_rate | 10 | 0.3785 | 0.4917 | -0.1132 | -0.493 | 0.0926 | NON-SIGNIFICANT_DEGRADATION |
| A | total_customer_minutes_interrupted | 10 | 394.7000 | 172.7000 | +222.0000 | +3.131 | 0.0051 | SIGNIFICANT_DEGRADATION |
| E | avg_restoration_steps | 10 | 21.6000 | 32.5067 | -10.9067 | -0.446 | 0.1688 | NON-SIGNIFICANT_IMPROVEMENT |
| E | critical_load_interruption_steps | 10 | 80.0000 | 42.8000 | +37.2000 | +1.878 | 0.0051 | SIGNIFICANT_DEGRADATION |
| E | energy_not_served_mwh | 10 | 9.7608 | 1.6184 | +8.1423 | +5.670 | 0.0051 | SIGNIFICANT_DEGRADATION |
| E | restoration_rate | 10 | 0.1551 | 0.5742 | -0.4191 | -1.869 | 0.0069 | SIGNIFICANT_DEGRADATION |
| E | total_customer_minutes_interrupted | 10 | 595.5000 | 275.2000 | +320.3000 | +2.344 | 0.0051 | SIGNIFICANT_DEGRADATION |
| I | avg_restoration_steps | 10 | 39.7610 | 16.8083 | +22.9526 | +0.755 | 0.0593 | NON-SIGNIFICANT_DEGRADATION |
| I | critical_load_interruption_steps | 10 | 75.7000 | 30.0000 | +45.7000 | +2.595 | 0.0051 | SIGNIFICANT_DEGRADATION |
| I | energy_not_served_mwh | 10 | 4.8733 | 0.5919 | +4.2814 | +3.442 | 0.0051 | SIGNIFICANT_DEGRADATION |
| I | restoration_rate | 10 | 0.3785 | 0.4717 | -0.0932 | -0.498 | 0.0926 | NON-SIGNIFICANT_DEGRADATION |
| I | total_customer_minutes_interrupted | 10 | 394.7000 | 178.5000 | +216.2000 | +2.938 | 0.0051 | SIGNIFICANT_DEGRADATION |
| J | avg_restoration_steps | 10 | 156.4667 | 8.2000 | +148.2667 | +0.842 | 0.0277 | SIGNIFICANT_DEGRADATION |
| J | critical_load_interruption_steps | 10 | 326.5000 | 131.6000 | +194.9000 | +1.429 | 0.0051 | SIGNIFICANT_DEGRADATION |
| J | energy_not_served_mwh | 10 | 44.2272 | 2.0198 | +42.2074 | +4.239 | 0.0051 | SIGNIFICANT_DEGRADATION |
| J | restoration_rate | 10 | 0.0828 | 0.0856 | -0.0028 | -0.046 | 0.6858 | NO_MEANINGFUL_DIFFERENCE |
| J | total_customer_minutes_interrupted | 10 | 4245.9000 | 3446.3000 | +799.6000 | +1.333 | 0.0051 | SIGNIFICANT_DEGRADATION |

### untrained_dqn vs random (full_stack)

| scenario | metric | n | mean_a | mean_b | diff | d | p | class |
|---|---|---:|---:|---:|---:|---:|---:|---|
| A | avg_restoration_steps | 10 | 20.9207 | 17.2667 | +3.6540 | +0.175 | 0.7989 | NO_MEANINGFUL_DIFFERENCE |
| A | critical_load_interruption_steps | 10 | 46.5000 | 31.5000 | +15.0000 | +0.539 | 0.0745 | NON-SIGNIFICANT_DEGRADATION |
| A | energy_not_served_mwh | 10 | 2.4983 | 0.5874 | +1.9109 | +0.817 | 0.0745 | NON-SIGNIFICANT_DEGRADATION |
| A | restoration_rate | 10 | 0.4746 | 0.4917 | -0.0171 | -0.087 | 0.6784 | NO_MEANINGFUL_DIFFERENCE |
| A | total_customer_minutes_interrupted | 10 | 263.4000 | 172.7000 | +90.7000 | +0.650 | 0.0745 | NON-SIGNIFICANT_DEGRADATION |
| E | avg_restoration_steps | 10 | 12.7214 | 32.5067 | -19.7852 | -1.197 | 0.0166 | SIGNIFICANT_IMPROVEMENT |
| E | critical_load_interruption_steps | 10 | 52.1000 | 42.8000 | +9.3000 | +0.299 | 0.3329 | NON-SIGNIFICANT_DEGRADATION |
| E | energy_not_served_mwh | 10 | 5.3846 | 1.6184 | +3.7662 | +0.775 | 0.0745 | NON-SIGNIFICANT_DEGRADATION |
| E | restoration_rate | 10 | 0.2500 | 0.5742 | -0.3241 | -1.240 | 0.0093 | SIGNIFICANT_DEGRADATION |
| E | total_customer_minutes_interrupted | 10 | 431.2000 | 275.2000 | +156.0000 | +0.538 | 0.1141 | NON-SIGNIFICANT_DEGRADATION |
| I | avg_restoration_steps | 10 | 22.8874 | 16.8083 | +6.0790 | +0.285 | 0.5076 | NON-SIGNIFICANT_DEGRADATION |
| I | critical_load_interruption_steps | 10 | 46.5000 | 30.0000 | +16.5000 | +0.584 | 0.0593 | NON-SIGNIFICANT_DEGRADATION |
| I | energy_not_served_mwh | 10 | 2.5341 | 0.5919 | +1.9421 | +0.813 | 0.0745 | NON-SIGNIFICANT_DEGRADATION |
| I | restoration_rate | 10 | 0.4417 | 0.4717 | -0.0299 | -0.190 | 0.8590 | NO_MEANINGFUL_DIFFERENCE |
| I | total_customer_minutes_interrupted | 10 | 278.3000 | 178.5000 | +99.8000 | +0.628 | 0.0926 | NON-SIGNIFICANT_DEGRADATION |
| J | avg_restoration_steps | 10 | 67.5000 | 8.2000 | +59.3000 | +0.451 | 0.3454 | NON-SIGNIFICANT_DEGRADATION |
| J | critical_load_interruption_steps | 10 | 244.4000 | 131.6000 | +112.8000 | +0.837 | 0.0593 | NON-SIGNIFICANT_DEGRADATION |
| J | energy_not_served_mwh | 10 | 26.9532 | 2.0198 | +24.9334 | +1.069 | 0.0745 | NON-SIGNIFICANT_DEGRADATION |
| J | restoration_rate | 10 | 0.0636 | 0.0856 | -0.0220 | -0.292 | 0.1730 | NON-SIGNIFICANT_DEGRADATION |
| J | total_customer_minutes_interrupted | 10 | 3789.2000 | 3446.3000 | +342.9000 | +0.520 | 0.1097 | NON-SIGNIFICANT_DEGRADATION |
