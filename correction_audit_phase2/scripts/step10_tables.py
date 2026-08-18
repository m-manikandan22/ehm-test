"""STEP 10 — Publication-ready tables from corrected results only."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

import fina_common as fc

OUT = fc.ROOT
TAB = os.path.join(OUT, "tables")


def md_table(df: pd.DataFrame, caption: str) -> str:
    cols = list(df.columns)
    lines = [caption, "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                if pd.isna(v):
                    cells.append("nan")
                else:
                    cells.append(f"{v:.4g}")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    raw = fc.load_corrected_b()
    with open(os.path.join(OUT, "CORRECTED_STATISTICAL_ANALYSIS.json"), encoding="utf-8") as f:
        stats = pd.DataFrame(json.load(f))
    mod = pd.read_csv(os.path.join(OUT, "MODULE_EXECUTION_AUDIT.csv"))
    ab = pd.read_csv(os.path.join(OUT, "EXPERIMENT_A_VS_B_CORRECTED.csv"))

    os.makedirs(TAB, exist_ok=True)

    # ---- Table 1: experimental configuration ----
    t1 = pd.DataFrame([
        ["Experiment", "Experiment B (corrected rerun)", "30 seeds x 2 stress x 9 policies = 540 runs; 540 valid; 0 invalid"],
        ["Dataset", "correction_audit_phase1/experiment_B_corrected_rerun/experiment_B_runs.json", "frozen; not modified"],
        ["Grid topology", "49-node synthetic grid", "constructed from city layout"],
        ["Simulation", "ticks=200; tick_hours=1.0", "quasi-steady AC power flow (positive-sequence)"],
        ["Seeds", "0..29 (30 paired seeds)", "set_global_seed(config.seed + scenario.seed)"],
        ["Stress levels", "moderate, severe", "fault count 5/8; duration 10-20/25-50; load 1.2/1.5; capacity 0.85/0.7"],
        ["Policies", "9", "persistence, random, rule_based, dqn_core_only, full_stack, no_lstm, no_twin, no_predictive, no_reward"],
        ["Primary outcomes", "4", "ENS, time-to-50% restoration, critical-load restoration %, SAIDI"],
        ["Primary test", "Wilcoxon signed-rank (paired by seed)", "asymptotic; paired t robustness"],
        ["Multiple comparisons", "Holm across 4 outcomes per pair", "per PRIMARY_OUTCOMES.md"],
        ["Effect size", "Cliff's delta + paired Cohen's d", "pre-registered"],
        ["Runtime", "672.77 s total", "run manifest elapsed_s"],
        ["Software", "python 3.14.3; numpy 2.4.2; scipy; torch 2.11.0+cpu; networkx 3.6.1", "no CUDA"],
    ], columns=["Item", "Setting", "Detail"])
    t1.to_csv(os.path.join(TAB, "Table1_experimental_configuration.csv"), index=False)
    with open(os.path.join(TAB, "Table1_experimental_configuration.md"), "w", encoding="utf-8") as f:
        f.write(md_table(t1, "# Table 1 — Experimental configuration (corrected Experiment B)"))

    # ---- Table 2: baseline comparison (median + stats) ----
    rows = []
    for lvl in fc.STRESS_LEVELS:
        for _, r in stats[(stats["stress_level"] == lvl) & (stats["controller_b"].isin(["persistence", "random", "rule_based", "dqn_core_only"]))].iterrows():
            rows.append({
                "stress_level": lvl,
                "comparison": f"full_stack vs {r['controller_b']}",
                "outcome": r["outcome_key"],
                "metric": r["outcome_metric"],
                "median_full_stack": r["median_a"],
                "median_baseline": r["median_b"],
                "median_diff": r["paired_abs_diff_median"],
                "rel_diff_pct": r["paired_rel_diff_pct"],
                "wilcoxon_p_raw": r["wilcoxon_p_raw"],
                "wilcoxon_p_holm": r["wilcoxon_p_holm"],
                "cliffs_delta": r["cliffs_delta"],
                "cohens_d": r["cohens_d"],
            })
    t2 = pd.DataFrame(rows)
    t2.to_csv(os.path.join(TAB, "Table2_baseline_comparison.csv"), index=False)
    with open(os.path.join(TAB, "Table2_baseline_comparison.md"), "w", encoding="utf-8") as f:
        f.write(md_table(t2, "# Table 2 — Baseline comparison (full_stack vs baselines, primary outcomes)"))

    # ---- Table 3: primary outcomes ----
    rows = []
    for _, r in stats.iterrows():
        rows.append({
            "stress_level": r["stress_level"],
            "comparison": r["comparison"],
            "outcome": r["outcome_key"],
            "metric": r["outcome_metric"],
            "direction": r["outcome_direction"],
            "median_a": r["median_a"],
            "median_b": r["median_b"],
            "paired_diff_median": r["paired_abs_diff_median"],
            "paired_rel_diff_pct": r["paired_rel_diff_pct"],
            "wilcoxon_stat": r["wilcoxon_stat"],
            "wilcoxon_p_raw": r["wilcoxon_p_raw"],
            "wilcoxon_p_holm": r["wilcoxon_p_holm"],
            "t_p_raw": r["t_p_raw"],
            "t_p_holm": r["t_p_holm"],
            "cliffs_delta": r["cliffs_delta"],
            "cohens_d": r["cohens_d"],
            "n_pairs": r["n_pairs"],
        })
    t3 = pd.DataFrame(rows)
    t3.to_csv(os.path.join(TAB, "Table3_primary_outcomes.csv"), index=False)
    with open(os.path.join(TAB, "Table3_primary_outcomes.md"), "w", encoding="utf-8") as f:
        f.write(md_table(t3, "# Table 3 — Primary outcomes (all comparisons, raw + Holm p)"))

    # ---- Table 4: ablation ----
    rows = []
    for _, r in stats[(stats["controller_b"].isin(["no_lstm", "no_twin", "no_predictive", "no_reward"]))].iterrows():
        rows.append({
            "stress_level": r["stress_level"],
            "ablation": r["controller_b"],
            "outcome": r["outcome_key"],
            "median_full_stack": r["median_a"],
            "median_ablation": r["median_b"],
            "median_diff": r["paired_abs_diff_median"],
            "wilcoxon_p_raw": r["wilcoxon_p_raw"],
            "wilcoxon_p_holm": r["wilcoxon_p_holm"],
            "cliffs_delta": r["cliffs_delta"],
            "per_seed_identical": "yes",
        })
    t4 = pd.DataFrame(rows)
    t4.to_csv(os.path.join(TAB, "Table4_ablation_study.csv"), index=False)
    with open(os.path.join(TAB, "Table4_ablation_study.md"), "w", encoding="utf-8") as f:
        f.write(md_table(t4, "# Table 4 — Ablation study (full_stack vs ablation variants)"))

    # ---- Table 5: statistical significance / effect sizes ----
    rows = []
    for _, r in stats.iterrows():
        if r["controller_b"] not in ["persistence", "random", "rule_based", "dqn_core_only"]:
            continue
        rows.append({
            "stress_level": r["stress_level"],
            "comparison": r["comparison"],
            "outcome": r["outcome_key"],
            "n": r["n_pairs"],
            "mean_diff": r["paired_abs_diff_mean"],
            "ci95_low": r["ci95_diff_low"],
            "ci95_high": r["ci95_diff_high"],
            "wilcoxon_stat": r["wilcoxon_stat"],
            "wilcoxon_p_raw": r["wilcoxon_p_raw"],
            "wilcoxon_p_holm": r["wilcoxon_p_holm"],
            "t_stat": r["t_stat"],
            "t_p_raw": r["t_p_raw"],
            "cliffs_delta": r["cliffs_delta"],
            "cohens_d": r["cohens_d"],
        })
    t5 = pd.DataFrame(rows)
    t5.to_csv(os.path.join(TAB, "Table5_statistical_significance_effect_sizes.csv"), index=False)
    with open(os.path.join(TAB, "Table5_statistical_significance_effect_sizes.md"), "w", encoding="utf-8") as f:
        f.write(md_table(t5, "# Table 5 — Statistical significance and effect sizes"))

    # ---- Table 6: module execution evidence ----
    t6 = mod.copy()
    t6.to_csv(os.path.join(TAB, "Table6_module_execution_evidence.csv"), index=False)
    with open(os.path.join(TAB, "Table6_module_execution_evidence.md"), "w", encoding="utf-8") as f:
        f.write(md_table(t6, "# Table 6 — Module execution evidence (per policy x stress)"))

    # ---- Table 7: Experiment A vs B ----
    t7 = ab.copy()
    t7.to_csv(os.path.join(TAB, "Table7_experiment_A_vs_B.csv"), index=False)
    with open(os.path.join(TAB, "Table7_experiment_A_vs_B.md"), "w", encoding="utf-8") as f:
        f.write(md_table(t7, "# Table 7 — Experiment A (nominal) vs Experiment B (stress) side-by-side"))
    print("Wrote tables 1-7")


if __name__ == "__main__":
    main()
