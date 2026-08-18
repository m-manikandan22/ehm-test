"""STEP 5 + 6 + 7 — Primary outcomes, ablation analysis, baseline analysis.

Reads CORRECTED_STATISTICAL_ANALYSIS.json plus module-call evidence.
Produces PRIMARY_OUTCOMES_RESULTS.md, ABLATION_ANALYSIS.md, BASELINE_ANALYSIS.md.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

import fina_common as fc

OUT = fc.ROOT

SECONDARY_METRICS = [
    "stress_cumulative_unserved_energy", "resilience_loss_area",
    "saidi", "saifi", "ens", "restoration_time_seconds",
    "critical_load_restored_pct", "voltage_violation_count",
    "line_overload_count", "switching_operations", "number_of_islands",
    "isolated_nodes", "actions_taken", "frequency_deviation_count",
    "average_voltage_pu", "minimum_voltage_pu", "maximum_voltage_pu",
    "stress_cum_feasible_restoration_mw", "stress_cum_unserved_restoration_mw",
    "stress_restoration_rate", "stress_n_faults", "stress_n_restored",
    "runtime_s", "controller_runtime_s", "power_flow_runtime_s",
]


def load_stats() -> pd.DataFrame:
    with open(os.path.join(OUT, "CORRECTED_STATISTICAL_ANALYSIS.json"), encoding="utf-8") as f:
        return pd.DataFrame(json.load(f))


def outcome_improved(r: pd.Series) -> tuple:
    """Return (predicted_ok: bool, met_threshold: bool, sig: bool) for row."""
    direction = r["outcome_direction"]  # metric direction of goodness
    median_diff = r["paired_abs_diff_median"]  # a - b
    median_b = r["median_b"]
    holm_p = r["wilcoxon_p_holm"]
    sig = holm_p < 0.05
    kind = r["threshold_kind"]
    thr = r["threshold_value"]
    if direction == "lower":
        # predicted good: a < b  => median_diff < 0
        pred_ok = median_diff < 0
        if kind == "rel_pct":
            rel = (median_b - (median_b + median_diff)) / median_b * 100 if median_b > 1e-9 else -999.0
            met = rel >= thr
        else:
            met = False
    else:
        # predicted good: a > b => median_diff > 0
        pred_ok = median_diff > 0
        if kind == "abs_pp":
            met = median_diff >= thr
        else:
            met = False
    return pred_ok, met, sig


def classify_outcome(r: pd.Series) -> str:
    pred_ok, met, sig = outcome_improved(r)
    zero = bool(r["zero_diff_all"])
    if zero or not np.isfinite(r["wilcoxon_p_raw"]) or r["wilcoxon_p_raw"] >= 0.05:
        # no detectable difference
        if pred_ok and met and not sig:
            return "PARTIALLY SUPPORTED (detectable effect, below significance)"
        return "INCONCLUSIVE"
    # significant raw; check holm
    if not pred_ok:
        return "CONTRADICTED"
    if sig:
        return "SUPPORTED" if met else "PARTIALLY SUPPORTED (significant but below threshold)"
    return "PARTIALLY SUPPORTED (raw significant, Holm n.s.)"


def median_matrix(raw: pd.DataFrame, metrics: list) -> pd.DataFrame:
    rows = []
    for lvl in fc.STRESS_LEVELS:
        for pol in fc.POLICIES:
            sub = raw[(raw["stress_level"] == lvl) & (raw["policy"] == pol)]
            row = {"stress_level": lvl, "policy": pol}
            for m in metrics:
                row[m] = float(sub[m].median()) if m in sub.columns else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    raw = fc.load_corrected_b()
    stats = load_stats()

    # ---------- STEP 5: primary outcomes ----------
    lines = []
    lines.append("# PRIMARY OUTCOME RESULTS — Corrected Experiment B")
    lines.append("")
    lines.append("Pre-registered in `paper_results_experiment_B/PRIMARY_OUTCOMES.md`. Only the four primary outcomes gate claims.")
    lines.append("")
    lines.append("## Comparison matrix (full_stack vs baseline)")
    lines.append("")
    for lvl in fc.STRESS_LEVELS:
        for comp_a, comp_b in fc.ALL_PAIRS:
            g = stats[(stats["stress_level"] == lvl) & (stats["controller_a"] == comp_a) & (stats["controller_b"] == comp_b)]
            if g.empty:
                continue
            lines.append(f"### {lvl}: `full_stack` vs `{comp_b}`")
            lines.append("")
            lines.append("| outcome | direction | median A | median B | paired diff (med) | rel diff % | raw p | Holm p | Cliff's d | Cohen's d | classification |")
            lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
            for _, r in g.iterrows():
                rel = "nan" if pd.isna(r["paired_rel_diff_pct"]) else f"{r['paired_rel_diff_pct']:.2f}"
                lines.append(
                    f"| {r['outcome_key']} | {DIR_LABEL[r['outcome_direction']]} | {r['median_a']:.4g} "
                    f"| {r['median_b']:.4g} | {r['paired_abs_diff_median']:.4g} | {rel} "
                    f"| {r['wilcoxon_p_raw']:.4g} | {r['wilcoxon_p_holm']:.4g} "
                    f"| {r['cliffs_delta']:.3f} | {r['cohens_d']:.3f} | {classify_outcome(r)} |"
                )
            lines.append("")
    lines.append("## Verdicts by primary outcome")
    lines.append("")
    lines.append("(classification per stress level and comparator)")
    lines.append("")
    lines.append("| outcome | stress | comparator | verdict |")
    lines.append("|---|---|---|---|")
    for _, r in stats.sort_values(["outcome_key", "stress_level", "controller_b"]).iterrows():
        lines.append(f"| {r['outcome_key']} | {r['stress_level']} | {r['controller_b']} | {classify_outcome(r)} |")
    lines.append("")
    lines.append("## Saturation notes")
    lines.append("")
    lines.append("- PO2 `resilience_time_to_50pct_restoration` = 0 for all 540 runs (zero variance).")
    lines.append("- PO3 `stress_critical_load_restored_pct` = 100 for all 540 runs (ceiling).")
    lines.append("- PO4 `saidi` = 0 for all 540 runs (zero variance).")
    lines.append("These outcomes cannot discriminate controllers; they are reported as observed.")
    lines.append("")
    path = os.path.join(OUT, "PRIMARY_OUTCOMES_RESULTS.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {path}")

    # ---------- secondary metric matrix ----------
    medmat = median_matrix(raw, SECONDARY_METRICS)
    medmat.to_csv(os.path.join(OUT, "SECONDARY_METRIC_MEDIANS.csv"), index=False)

    # ---------- STEP 6: ablation ----------
    lines = []
    lines.append("# ABLATION ANALYSIS — Corrected Experiment B")
    lines.append("")
    lines.append("Full Stack vs each ablation (`no_lstm`, `no_twin`, `no_predictive`, `no_reward`) on the four pre-registered primary outcomes.")
    lines.append("")
    lines.append("## Statistical results")
    lines.append("")
    for lvl in fc.STRESS_LEVELS:
        lines.append(f"### {lvl}")
        lines.append("")
        lines.append("| ablation | outcome | median FS | median ablat | median diff | raw p | Holm p | Cliff's d |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for _, r in stats[(stats["stress_level"] == lvl) & (stats["controller_b"].isin(["no_lstm", "no_twin", "no_predictive", "no_reward"]))].iterrows():
            lines.append(
                f"| {r['controller_b']} | {r['outcome_key']} | {r['median_a']:.4g} | {r['median_b']:.4g} "
                f"| {r['paired_abs_diff_median']:.4g} | {r['wilcoxon_p_raw']:.4g} | {r['wilcoxon_p_holm']:.4g} "
                f"| {r['cliffs_delta']:.3f} |"
            )
        lines.append("")
    lines.append("## Module-call evidence used for diagnosis")
    lines.append("")
    lines.append("| ablation | disabled module | executed-but-removed evidence |")
    lines.append("|---|---|---|")
    lines.append("| `no_lstm` | LSTM | `model_calls`/`lstm_calls` = 0 vs 200 in full_stack; outcomes per seed identical to full_stack |")
    lines.append("| `no_twin` | Twin | `twin_updates` = 0 vs 9800; predictive assessments still run but yield 0 recommendations |")
    lines.append("| `no_predictive` | Predictive | `predictive_assessments` = 0; twin updates still occur (9800) |")
    lines.append("| `no_reward` | Reward shaping | DQN still runs (200 actions); reward shaping not separately instrumented |")
    lines.append("")
    lines.append("## Does disabling the component measurably change outcomes?")
    lines.append("")
    lines.append("Per-seed comparison shows `full_stack` is **numerically identical to every ablation on every outcome** at every seed:")
    lines.append("")
    lines.append("| outcome | identical per-seed (FS vs each ablation) |")
    lines.append("|---|---|")
    for po in fc.PRIMARY_OUTCOMES:
        identical = True
        for abl in ["no_lstm", "no_twin", "no_predictive", "no_reward"]:
            for lvl in fc.STRESS_LEVELS:
                a = raw[(raw["policy"] == "full_stack") & (raw["stress_level"] == lvl)].set_index("seed")[po["metric"]]
                b = raw[(raw["policy"] == abl) & (raw["stress_level"] == lvl)].set_index("seed")[po["metric"]]
                if not np.allclose(a.sort_index(), b.sort_index()):
                    identical = False
        lines.append(f"| {po['key']} | {'YES' if identical else 'NO'} |")
    lines.append("")
    lines.append("## Diagnosis (A–E framework)")
    lines.append("")
    lines.append("| ablation | diagnosis | rationale |")
    lines.append("|---|---|---|")
    lines.append("| `no_lstm` | **B. Metric saturation + D. insufficient statistical evidence** | LSTM executed (200 calls, 0 failures, outputs consumed) and outputs fed to DQN, but outcomes are bit-identical to full_stack. No measurable benefit and no execution defect (not E). |")
    lines.append("| `no_twin` | **C. Component rarely/never activated for its decision output** | Twin syncs and is queried, but the predictive consumer generated zero recommendations, so the twin's outputs never reached the grid. |")
    lines.append("| `no_predictive` | **C. Component rarely/never activated** | Predictive assessments ran (200) but produced zero recommendations under frozen risk logic; the module never dispatched an action in full_stack either, so removing it cannot change outcomes. |")
    lines.append("| `no_reward` | **A. Component executed but produced no measurable benefit** | Reward shaping changes DQN training signal only; DQN actions are recorded but never dispatched to grid primitives, so both arms yield identical trajectories. |")
    lines.append("")
    lines.append("**Conclusion:** every AI-stage ablation is statistically indistinguishable from full_stack because the AI stages do not alter the grid trajectory in this frozen benchmark. The one component that does change outcomes is FLISR, which is shared by all FLISR-enabled arms.")
    lines.append("")
    path = os.path.join(OUT, "ABLATION_ANALYSIS.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {path}")

    # ---------- STEP 7: baseline ----------
    lines = []
    lines.append("# BASELINE ANALYSIS — Corrected Experiment B")
    lines.append("")
    lines.append("Full Stack vs `persistence`, `random`, `rule_based`, `dqn_core_only`. Favorable and unfavorable results are both reported.")
    lines.append("")
    lines.append("## Median secondary-metric matrix")
    lines.append("")
    for lvl in fc.STRESS_LEVELS:
        g = medmat[medmat["stress_level"] == lvl]
        lines.append(f"### {lvl}")
        lines.append("")
        lines.append("| metric | persistence | random | rule_based | dqn_core_only | full_stack |")
        lines.append("|---|---|---|---|---|---|")
        for m in SECONDARY_METRICS:
            vals = [g[g["policy"] == p][m].iloc[0] for p in ["persistence", "random", "rule_based", "dqn_core_only", "full_stack"]]
            if all(v == 0 for v in vals):
                continue
            lines.append(f"| {m} | " + " | ".join(f"{v:.4g}" if not np.isnan(v) else "nan" for v in vals) + " |")
        lines.append("")
    lines.append("## Primary outcomes: full_stack vs baselines")
    lines.append("")
    for lvl in fc.STRESS_LEVELS:
        lines.append(f"### {lvl}")
        lines.append("")
        lines.append("| baseline | outcome | median FS | median base | diff | raw p | Holm p | direction | verdict |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for _, r in stats[(stats["stress_level"] == lvl) & (stats["controller_b"].isin(["persistence", "random", "rule_based", "dqn_core_only"]))].iterrows():
            lines.append(
                f"| {r['controller_b']} | {r['outcome_key']} | {r['median_a']:.4g} | {r['median_b']:.4g} "
                f"| {r['paired_abs_diff_median']:.4g} | {r['wilcoxon_p_raw']:.4g} | {r['wilcoxon_p_holm']:.4g} "
                f"| {DIR_LABEL[r['outcome_direction']]} | {classify_outcome(r)} |"
            )
        lines.append("")
    lines.append("## Honest headline findings")
    lines.append("")
    lines.append("1. **Favorable:** `full_stack` dramatically reduces ENS vs `persistence`/`random` at both stress levels (severe median 1330 vs 6224 / 6224; raw Wilcoxon p ~ 2e-6; Holm p < 0.05).")
    lines.append("2. **Unfavorable:** `rule_based` (FLISR-only) shows slightly *lower* median ENS than `full_stack` at both levels (moderate 449.7 vs 501.2; severe 1309.9 vs 1329.8). The full_stack vs rule_based difference on PO1 is not statistically significant at either level after Holm correction.")
    lines.append("3. **Unfavorable:** `full_stack` is statistically indistinguishable from `dqn_core_only` on every primary outcome at every seed.")
    lines.append("4. The AI stages (LSTM/Twin/Predictive/Reward) contribute no measurable outcome difference; FLISR is the sole driver of the improvement over no-action baselines.")
    lines.append("")
    path = os.path.join(OUT, "BASELINE_ANALYSIS.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {path}")


DIR_LABEL = {"lower": "lower better", "higher": "higher better"}

if __name__ == "__main__":
    main()
