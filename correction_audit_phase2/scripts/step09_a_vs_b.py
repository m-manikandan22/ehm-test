"""STEP 9 — Experiment A vs B comparison with the corrected loader.

Experiment-A loader correction (from Phase 1 TC analysis): A records have
no `stress_level` field; their condition is `nominal` (weather_mode
`normal`). The historical loader searched for stress_level `'normal'`,
which does not exist, and produced n = 0. We load A by policy + seed and
label the condition `nominal`.

A and B are treated as separate experiments: side-by-side summaries and,
where seeds overlap (0..29), paired descriptive comparisons. Samples are
never pooled.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
from scipy import stats

import fina_common as fc

OUT = fc.ROOT

COMMON_METRICS = [
    "ens", "saidi", "saifi", "restoration_time_seconds",
    "critical_load_restored_pct", "voltage_violation_count",
    "line_overload_count", "switching_operations", "number_of_islands",
    "isolated_nodes", "actions_taken", "frequency_deviation_count",
    "average_voltage_pu", "minimum_voltage_pu", "maximum_voltage_pu",
    "successful_restoration_count", "controller_runtime_s", "runtime_s",
]


def summary_row(vals: np.ndarray) -> dict:
    v = np.asarray(vals, dtype=float)
    if len(v) == 0:
        return dict(n=0, mean=np.nan, sd=np.nan, median=np.nan, iqr=np.nan)
    return dict(
        n=len(v),
        mean=float(np.mean(v)),
        sd=float(np.std(v, ddof=1)) if len(v) > 1 else 0.0,
        median=float(np.median(v)),
        iqr=float(np.subtract(*np.percentile(v, [75, 25]))),
    )


def main() -> None:
    a = fc.load_exp_a()
    b = fc.load_corrected_b()

    # Confirm A loader actually loads.
    a_n = len(a)
    print(f"Experiment A loaded: {a_n} records")
    assert a_n > 0, "Experiment A loader produced n = 0"

    policies = sorted(set(a["policy"]) & set(b["policy"]))

    # ---- Side-by-side summary table ----
    rows = []
    for pol in policies:
        a_sub = a[a["policy"] == pol]
        for m in COMMON_METRICS:
            if m not in a_sub.columns:
                continue
            row = {"policy": pol, "metric": m}
            for cond in ["nominal", "moderate", "severe"]:
                if cond == "nominal":
                    vals = a_sub[m].to_numpy()
                else:
                    vals = b[(b["policy"] == pol) & (b["stress_level"] == cond)][m].to_numpy()
                s = summary_row(vals)
                row[f"{cond}_n"] = s["n"]
                row[f"{cond}_mean"] = s["mean"]
                row[f"{cond}_sd"] = s["sd"]
                row[f"{cond}_median"] = s["median"]
                row[f"{cond}_iqr"] = s["iqr"]
            rows.append(row)
    summary = pd.DataFrame(rows)
    csv_path = os.path.join(OUT, "EXPERIMENT_A_VS_B_CORRECTED.csv")
    summary.to_csv(csv_path, index=False)

    # ---- Paired A->B stress-escalation comparison on common seeds (0..29) ----
    paired_rows = []
    for pol in policies:
        a_sub = a[(a["policy"] == pol)].set_index("seed")
        for m in COMMON_METRICS:
            if m not in a_sub.columns:
                continue
            for lvl in ["moderate", "severe"]:
                b_sub = b[(b["policy"] == pol) & (b["stress_level"] == lvl)].set_index("seed")
                common = sorted(set(a_sub.index) & set(b_sub.index))
                if len(common) < 3:
                    continue
                av = a_sub.loc[common, m].to_numpy(dtype=float)
                bv = b_sub.loc[common, m].to_numpy(dtype=float)
                diffs = bv - av  # B minus A
                zero = np.all(np.abs(diffs) < 1e-12)
                p = 1.0
                W = 0.0
                if not zero:
                    try:
                        res = stats.wilcoxon(av, bv, zero_method="wilcox", method="asymptotic")
                        W, p = float(res.statistic), float(res.pvalue)
                    except Exception:
                        p = 1.0
                if p is None or np.isnan(p):
                    p = 1.0
                rel = np.nan
                den = av[av > 1e-9]
                if len(den) == len(av):
                    rel = float(np.median(diffs[av > 1e-9] / av[av > 1e-9] * 100.0))
                paired_rows.append({
                    "policy": pol,
                    "metric": m,
                    "escalation": f"A_nominal -> B_{lvl}",
                    "n_common_seeds": len(common),
                    "a_median": float(np.median(av)),
                    "b_median": float(np.median(bv)),
                    "median_abs_change": float(np.median(diffs)),
                    "median_rel_change_pct": rel,
                    "wilcoxon_stat": W,
                    "wilcoxon_p": p,
                })
    paired = pd.DataFrame(paired_rows)
    paired_csv = os.path.join(OUT, "EXPERIMENT_A_VS_B_PAIRED_ESCALATION.csv")
    paired.to_csv(paired_csv, index=False)

    # ---- Markdown report ----
    lines = []
    lines.append("# EXPERIMENT A VS B (CORRECTED) — side-by-side, never pooled")
    lines.append("")
    lines.append(f"Experiment A loaded: **{a_n}** records (nominal condition, no `stress_level` field; loader fixed per Phase-1 TC analysis).")
    lines.append("Experiment B: corrected 540-run dataset (moderate / severe).")
    lines.append("")
    lines.append("A and B are different experiments (different disturbance profiles, fault durations, capacity margins, software stack). Their samples are **not pooled**; comparisons are side-by-side and, where seeds overlap, paired descriptive tests on the 30 common seeds (exploratory, cross-experiment).")
    lines.append("")
    lines.append("## Design contrast")
    lines.append("")
    lines.append("| | Experiment A (nominal) | Experiment B moderate | Experiment B severe |")
    lines.append("|---|---|---|---|")
    lines.append("| seeds | 100 | 30 | 30 |")
    lines.append("| fault duration (steps) | 3–8 | 10–20 | 25–50 |")
    lines.append("| fault count | 3 | 5 | 8 |")
    lines.append("| load multiplier | 1.0 | 1.2 | 1.5 |")
    lines.append("| line capacity factor | 1.0 | 0.85 | 0.7 |")
    lines.append("| weather | normal | normal | storm |")
    lines.append("| software | py 3.11, torch 2.2.2 | py 3.14, torch 2.11.0 | py 3.14, torch 2.11.0 |")
    lines.append("")
    lines.append("## Side-by-side summary (A nominal vs B stress)")
    lines.append("")
    lines.append("CSV: `EXPERIMENT_A_VS_B_CORRECTED.csv` (full). Highlight for `full_stack`:")
    lines.append("")
    fs = summary[summary["policy"] == "full_stack"]
    lines.append("| metric | A nominal median | B moderate median | B severe median |")
    lines.append("|---|---:|---:|---:|")
    for _, r in fs.iterrows():
        lines.append(f"| {r['metric']} | {r['nominal_median']:.4g} | {r['moderate_median']:.4g} | {r['severe_median']:.4g} |")
    lines.append("")
    lines.append("## Paired stress-escalation (common seeds 0–29, descriptive)")
    lines.append("")
    lines.append("CSV: `EXPERIMENT_A_VS_B_PAIRED_ESCALATION.csv`. For `full_stack`:")
    lines.append("")
    fs2 = paired[paired["policy"] == "full_stack"]
    lines.append("| metric | escalation | n | A median | B median | median abs change | rel change % | Wilcoxon p |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for _, r in fs2.iterrows():
        rel = "nan" if pd.isna(r["median_rel_change_pct"]) else f"{r['median_rel_change_pct']:.2f}"
        lines.append(f"| {r['metric']} | {r['escalation']} | {r['n_common_seeds']} | {r['a_median']:.4g} | {r['b_median']:.4g} | {r['median_abs_change']:.4g} | {rel} | {r['wilcoxon_p']:.4g} |")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Experiment A's nominal benchmark is saturated (all controllers indistinguishable); Experiment B's stress benchmark discriminates FLISR-enabled from no-action policies on ENS.")
    lines.append("- These are not treated as one homogeneous experiment; the paired tests above are descriptive cross-experiment escalations on shared seeds only.")
    lines.append("")
    path = os.path.join(OUT, "EXPERIMENT_A_VS_B_CORRECTED.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {csv_path}")
    print(f"Wrote {paired_csv}")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
