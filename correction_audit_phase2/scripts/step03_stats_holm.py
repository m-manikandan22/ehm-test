"""STEP 3 + 4 — Corrected statistical analysis with Holm-Bonferroni.

Primary outcome comparisons:
  stress_level x (full_stack vs each baseline/ablation) x 4 primary outcomes.
Holm family: the four pre-registered primary outcomes within each
controller pair at each stress level (per PRIMARY_OUTCOMES.md).

Outputs: CORRECTED_STATISTICAL_ANALYSIS.csv / .md
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

import fina_common as fc

OUT = fc.ROOT

DIRECTION_LABEL = {"lower": "lower better", "higher": "higher better"}


def build_rows(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for lvl in fc.STRESS_LEVELS:
        for (pol_a, pol_b) in fc.ALL_PAIRS:
            a_all = raw[(raw["policy"] == pol_a) & (raw["stress_level"] == lvl)].set_index("seed")
            b_all = raw[(raw["policy"] == pol_b) & (raw["stress_level"] == lvl)].set_index("seed")
            common = sorted(set(a_all.index) & set(b_all.index))
            # also include an outcome row for each primary outcome
            for po in fc.PRIMARY_OUTCOMES:
                key = po["key"]
                metric = po["metric"]
                a = a_all.loc[common, metric].to_numpy()
                b = b_all.loc[common, metric].to_numpy()
                st = fc.paired_stats(a, b)
                rows.append({
                    "stress_level": lvl,
                    "comparison": f"{pol_a} vs {pol_b}",
                    "controller_a": pol_a,
                    "controller_b": pol_b,
                    "outcome_key": key,
                    "outcome_metric": metric,
                    "outcome_direction": po["direction"],
                    "n_pairs": st["n"],
                    "mean_a": st["mean_a"],
                    "sd_a": st["sd_a"],
                    "median_a": st["median_a"],
                    "iqr_a": st["iqr_a"],
                    "mean_b": st["mean_b"],
                    "sd_b": st["sd_b"],
                    "median_b": st["median_b"],
                    "iqr_b": st["iqr_b"],
                    "ci95_diff_low": st["ci95_diff_low"],
                    "ci95_diff_high": st["ci95_diff_high"],
                    "paired_abs_diff_mean": st["mean_diff"],
                    "paired_abs_diff_median": st["median_diff"],
                    "paired_rel_diff_pct": st["rel_diff_pct"],
                    "wilcoxon_stat": st["wilcoxon_stat"],
                    "wilcoxon_p_raw": st["wilcoxon_p"],
                    "t_stat": st["t_stat"],
                    "t_p_raw": st["t_p"],
                    "cohens_d": st["cohens_d"],
                    "cliffs_delta": st["cliffs_delta"],
                    "zero_diff_all": st["zero_diff_all"],
                    "threshold": po["threshold"],
                    "threshold_kind": po["threshold_kind"],
                    "threshold_value": po["threshold_value"],
                })
    df = pd.DataFrame(rows)
    # Holm correction within (stress_level, comparison) across the 4 outcomes
    adj_map = {}
    for (lvl, comp), g in df.groupby(["stress_level", "comparison"]):
        pvals = g["wilcoxon_p_raw"].tolist()
        adj = fc.holm_adjust(pvals)
        for idx, val in zip(g.index, adj):
            adj_map[idx] = val
    df["wilcoxon_p_holm"] = df.index.map(adj_map)

    # t-test robustness also adjusted within same family
    t_adj_map = {}
    for (lvl, comp), g in df.groupby(["stress_level", "comparison"]):
        pvals = g["t_p_raw"].tolist()
        adj = fc.holm_adjust(pvals)
        for idx, val in zip(g.index, adj):
            t_adj_map[idx] = val
    df["t_p_holm"] = df.index.map(t_adj_map)
    return df


def main() -> None:
    raw = fc.load_corrected_b()
    df = build_rows(raw)

    csv_path = os.path.join(OUT, "CORRECTED_STATISTICAL_ANALYSIS.csv")
    df.to_csv(csv_path, index=False)

    # JSON for downstream reports
    with open(os.path.join(OUT, "CORRECTED_STATISTICAL_ANALYSIS.json"), "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, indent=1)

    lines = []
    lines.append("# CORRECTED STATISTICAL ANALYSIS — Experiment B (540 runs)")
    lines.append("")
    lines.append("Paired by seed (n = 30 per level x policy). Differences defined as **full_stack minus comparator** (a - b).")
    lines.append("")
    lines.append("Primary test: Wilcoxon signed-rank (asymptotic, zero-diffs dropped). Robustness: paired t-test.")
    lines.append("Effect sizes: Cliff's delta (pre-registered, computed alongside Wilcoxon) and paired Cohen's d.")
    lines.append("")
    lines.append("Holm-Bonferroni correction applied across the **four pre-registered primary outcomes within each controller pair** at each stress level (family per PRIMARY_OUTCOMES.md).")
    lines.append("")
    lines.append("## Full comparison table")
    lines.append("")
    for lvl in fc.STRESS_LEVELS:
        for comp in [f"full_stack vs {b}" for _, b in fc.ALL_PAIRS]:
            g = df[(df["stress_level"] == lvl) & (df["comparison"] == comp)]
            if g.empty:
                continue
            lines.append(f"### {lvl}: {comp}")
            lines.append("")
            lines.append("| outcome | metric | n | median A | median B | median diff | rel diff % | Wilcoxon W | p (raw) | p (Holm) | t p (raw) | t p (Holm) | Cliff's d | Cohen's d |")
            lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
            for _, r in g.iterrows():
                rel = "nan" if pd.isna(r["paired_rel_diff_pct"]) else f"{r['paired_rel_diff_pct']:.2f}"
                lines.append(
                    f"| {r['outcome_key']} | {r['outcome_metric']} | {int(r['n_pairs'])} "
                    f"| {r['median_a']:.4g} | {r['median_b']:.4g} | {r['paired_abs_diff_median']:.4g} "
                    f"| {rel} | {r['wilcoxon_stat']:.4g} | {r['wilcoxon_p_raw']:.4g} "
                    f"| {r['wilcoxon_p_holm']:.4g} | {r['t_p_raw']:.4g} | {r['t_p_holm']:.4g} "
                    f"| {r['cliffs_delta']:.3f} | {r['cohens_d']:.3f} |"
                )
            lines.append("")
    lines.append("## Holm family justification")
    lines.append("")
    lines.append("PRIMARY_OUTCOMES.md: \"Multiple-comparison correction: Holm correction across the four primary outcomes for each pair of controllers.\"")
    lines.append("The family is therefore **4 tests per (stress level, controller pair)**, applied to the raw Wilcoxon p-values. Raw and Holm-adjusted p-values are both stored.")
    lines.append("")
    lines.append("_Raw results were not modified._")
    lines.append("")

    md_path = os.path.join(OUT, "CORRECTED_STATISTICAL_ANALYSIS.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    print(f"rows: {len(df)}")


if __name__ == "__main__":
    main()
