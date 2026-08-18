# EXPERIMENT A VS B (CORRECTED) — side-by-side, never pooled

Experiment A loaded: **900** records (nominal condition, no `stress_level` field; loader fixed per Phase-1 TC analysis).
Experiment B: corrected 540-run dataset (moderate / severe).

A and B are different experiments (different disturbance profiles, fault durations, capacity margins, software stack). Their samples are **not pooled**; comparisons are side-by-side and, where seeds overlap, paired descriptive tests on the 30 common seeds (exploratory, cross-experiment).

## Design contrast

| | Experiment A (nominal) | Experiment B moderate | Experiment B severe |
|---|---|---|---|
| seeds | 100 | 30 | 30 |
| fault duration (steps) | 3–8 | 10–20 | 25–50 |
| fault count | 3 | 5 | 8 |
| load multiplier | 1.0 | 1.2 | 1.5 |
| line capacity factor | 1.0 | 0.85 | 0.7 |
| weather | normal | normal | storm |
| software | py 3.11, torch 2.2.2 | py 3.14, torch 2.11.0 | py 3.14, torch 2.11.0 |

## Side-by-side summary (A nominal vs B stress)

CSV: `EXPERIMENT_A_VS_B_CORRECTED.csv` (full). Highlight for `full_stack`:

| metric | A nominal median | B moderate median | B severe median |
|---|---:|---:|---:|
| ens | 30 | 50 | 80 |
| saidi | 0 | 0 | 0 |
| saifi | 0.06122 | 0.102 | 0.1633 |
| restoration_time_seconds | 0 | 0 | 0 |
| critical_load_restored_pct | 100 | 0 | 0 |
| voltage_violation_count | 0 | 2544 | 5864 |
| line_overload_count | 4 | 0 | 96 |
| switching_operations | 0 | 0 | 0 |
| number_of_islands | 1 | 1 | 1 |
| isolated_nodes | 0 | 25 | 38 |
| actions_taken | 200 | 200 | 200 |
| frequency_deviation_count | 9800 | 8158 | 9800 |
| average_voltage_pu | 0.9614 | 0.4756 | 0.222 |
| minimum_voltage_pu | 0.95 | 0 | 0 |
| maximum_voltage_pu | 1 | 1 | 1 |
| successful_restoration_count | 0 | 0 | 0 |
| controller_runtime_s | 0.118 | 0.4118 | 0.3516 |
| runtime_s | 1.558 | 1.297 | 1.127 |

## Paired stress-escalation (common seeds 0–29, descriptive)

CSV: `EXPERIMENT_A_VS_B_PAIRED_ESCALATION.csv`. For `full_stack`:

| metric | escalation | n | A median | B median | median abs change | rel change % | Wilcoxon p |
|---|---|---:|---:|---:|---:|---:|---:|
| ens | A_nominal -> B_moderate | 30 | 30 | 50 | 20 | 66.67 | 4.32e-08 |
| ens | A_nominal -> B_severe | 30 | 30 | 80 | 50 | 166.67 | 6.799e-08 |
| saidi | A_nominal -> B_moderate | 30 | 0 | 0 | 0 | nan | 1 |
| saidi | A_nominal -> B_severe | 30 | 0 | 0 | 0 | nan | 1 |
| saifi | A_nominal -> B_moderate | 30 | 0.06122 | 0.102 | 0.04082 | 66.67 | 4.32e-08 |
| saifi | A_nominal -> B_severe | 30 | 0.06122 | 0.1633 | 0.102 | 166.67 | 6.799e-08 |
| restoration_time_seconds | A_nominal -> B_moderate | 30 | 0 | 0 | 0 | nan | 1 |
| restoration_time_seconds | A_nominal -> B_severe | 30 | 0 | 0 | 0 | nan | 1 |
| critical_load_restored_pct | A_nominal -> B_moderate | 30 | 100 | 0 | -100 | -100.00 | 1.802e-05 |
| critical_load_restored_pct | A_nominal -> B_severe | 30 | 100 | 0 | -100 | -100.00 | 1.976e-07 |
| voltage_violation_count | A_nominal -> B_moderate | 30 | 0 | 2544 | 2544 | nan | 1.734e-06 |
| voltage_violation_count | A_nominal -> B_severe | 30 | 0 | 5864 | 5844 | nan | 1.734e-06 |
| line_overload_count | A_nominal -> B_moderate | 30 | 5 | 0 | -5 | nan | 5.746e-05 |
| line_overload_count | A_nominal -> B_severe | 30 | 5 | 96 | 91.5 | nan | 1.731e-06 |
| switching_operations | A_nominal -> B_moderate | 30 | 0 | 0 | 0 | nan | 1 |
| switching_operations | A_nominal -> B_severe | 30 | 0 | 0 | 0 | nan | 1 |
| number_of_islands | A_nominal -> B_moderate | 30 | 1 | 1 | 0 | 0.00 | 1 |
| number_of_islands | A_nominal -> B_severe | 30 | 1 | 1 | 0 | 0.00 | 1 |
| isolated_nodes | A_nominal -> B_moderate | 30 | 0 | 25 | 25 | nan | 1.704e-06 |
| isolated_nodes | A_nominal -> B_severe | 30 | 0 | 38 | 38 | nan | 1.139e-06 |
| actions_taken | A_nominal -> B_moderate | 30 | 200 | 200 | 0 | 0.00 | 1 |
| actions_taken | A_nominal -> B_severe | 30 | 200 | 200 | 0 | 0.00 | 1 |
| frequency_deviation_count | A_nominal -> B_moderate | 30 | 9800 | 8158 | -1544 | -15.75 | 1.729e-06 |
| frequency_deviation_count | A_nominal -> B_severe | 30 | 9800 | 9800 | 0 | 0.00 | 0.01686 |
| average_voltage_pu | A_nominal -> B_moderate | 30 | 0.9614 | 0.4756 | -0.4761 | -50.02 | 1.73e-06 |
| average_voltage_pu | A_nominal -> B_severe | 30 | 0.9614 | 0.222 | -0.72 | -76.43 | 1.388e-06 |
| minimum_voltage_pu | A_nominal -> B_moderate | 30 | 0.95 | 0 | -0.95 | nan | 9.634e-07 |
| minimum_voltage_pu | A_nominal -> B_severe | 30 | 0.95 | 0 | -0.95 | nan | 9.634e-07 |
| maximum_voltage_pu | A_nominal -> B_moderate | 30 | 1 | 1 | 0 | 0.00 | 1 |
| maximum_voltage_pu | A_nominal -> B_severe | 30 | 1 | 1 | 0 | 0.00 | 1 |
| successful_restoration_count | A_nominal -> B_moderate | 30 | 0 | 0 | 0 | nan | 1 |
| successful_restoration_count | A_nominal -> B_severe | 30 | 0 | 0 | 0 | nan | 1 |
| controller_runtime_s | A_nominal -> B_moderate | 30 | 0.114 | 0.4118 | 0.2941 | 261.24 | 1.734e-06 |
| controller_runtime_s | A_nominal -> B_severe | 30 | 0.114 | 0.3516 | 0.2376 | 215.40 | 1.733e-06 |
| runtime_s | A_nominal -> B_moderate | 30 | 1.594 | 1.297 | -0.2805 | -17.14 | 6.892e-05 |
| runtime_s | A_nominal -> B_severe | 30 | 1.594 | 1.127 | -0.4433 | -28.32 | 2.163e-05 |

## Notes

- Experiment A's nominal benchmark is saturated (all controllers indistinguishable); Experiment B's stress benchmark discriminates FLISR-enabled from no-action policies on ENS.
- These are not treated as one homogeneous experiment; the paired tests above are descriptive cross-experiment escalations on shared seeds only.
