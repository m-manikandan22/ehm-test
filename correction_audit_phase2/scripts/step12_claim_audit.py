"""STEP 12 — Claim audit on corrected Experiment-B data.

Classifies the canonical paper claims against the corrected 540-run
dataset. Each claim is anchored to a pre-registered primary outcome
(PRIMARY_OUTCOMES.md) or to directly measurable module/cost evidence.

Verdict categories:
  SUPPORTED           — Holm p < 0.05, effect in predicted direction,
                        meets the pre-registered effect threshold at
                        every applicable stress level.
  PARTIALLY SUPPORTED — passes in at least one stress level but not all.
  CONTRADICTED        — statistically significant effect in the OPPOSITE
                        direction to the claim.
  INCONCLUSIVE        — no statistically detectable effect, or effect
                        below the threshold.
  NOT TESTED          — claim requires evidence this simulation study
                        does not produce (e.g. field validation).

Output: CORRECTED_CLAIM_AUDIT.md
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fina_common as fc

OUT = fc.ROOT

# Canonical claim list (source of truth: experiments/results/experiment_B_stress/PHASE31_claim_audit.py)
# extended with the FLISR-vs-no-action headline claim that the corrected
# data does support.
CANONICAL_CLAIMS = [
    {
        "id": "claim_ehm_reduces_ens",
        "claim": "EHM reduces cumulative ENS / unserved energy vs rule-based FLISR under stress.",
        "metric": "stress_cumulative_unserved_energy",
        "direction": "lower",
        "threshold_kind": "rel_pct",
        "threshold_value": 5.0,
        "comparator": "rule_based",
        "section": "Reliability",
    },
    {
        "id": "claim_ehm_faster_restoration",
        "claim": "EHM reaches 50 % restoration in fewer steps vs rule-based FLISR under stress.",
        "metric": "resilience_time_to_50pct_restoration",
        "direction": "lower",
        "threshold_kind": "rel_pct",
        "threshold_value": 5.0,
        "comparator": "rule_based",
        "section": "Resilience",
    },
    {
        "id": "claim_ehm_restores_critical_load",
        "claim": "EHM restores a higher fraction of critical load vs rule-based FLISR under stress.",
        "metric": "stress_critical_load_restored_pct",
        "direction": "higher",
        "threshold_kind": "abs_pp",
        "threshold_value": 2.0,
        "comparator": "rule_based",
        "section": "Critical loads",
    },
    {
        "id": "claim_ehm_reduces_saidi",
        "claim": "EHM reduces SAIDI vs rule-based FLISR under stress.",
        "metric": "saidi",
        "direction": "lower",
        "threshold_kind": "rel_pct",
        "threshold_value": 5.0,
        "comparator": "rule_based",
        "section": "Reliability",
    },
    {
        "id": "claim_twin_improves_resilience",
        "claim": "The Digital Twin improves resilience over the no-twin ablation.",
        "metric": "stress_cumulative_unserved_energy",
        "direction": "lower",
        "threshold_kind": "rel_pct",
        "threshold_value": 1.0,
        "comparator": "no_twin",
        "section": "Ablations",
    },
    {
        "id": "claim_lstm_improves_restoration",
        "claim": "LSTM forecasting improves outcomes over the no-LSTM ablation.",
        "metric": "stress_cumulative_unserved_energy",
        "direction": "lower",
        "threshold_kind": "rel_pct",
        "threshold_value": 1.0,
        "comparator": "no_lstm",
        "section": "Ablations",
    },
    {
        "id": "claim_predictive_improves_resilience",
        "claim": "Predictive healing improves outcomes over the no-predictive ablation.",
        "metric": "stress_cumulative_unserved_energy",
        "direction": "lower",
        "threshold_kind": "rel_pct",
        "threshold_value": 1.0,
        "comparator": "no_predictive",
        "section": "Ablations",
    },
    {
        "id": "claim_reward_shaping_helps",
        "claim": "Reward shaping helps DQN outcomes under stress.",
        "metric": "stress_cumulative_unserved_energy",
        "direction": "lower",
        "threshold_kind": "rel_pct",
        "threshold_value": 1.0,
        "comparator": "no_reward",
        "section": "Ablations",
    },
    {
        "id": "claim_dqn_outperforms_rule_based",
        "claim": "DQN outperforms rule-based FLISR under stress.",
        "metric": "stress_cumulative_unserved_energy",
        "direction": "lower",
        "threshold_kind": "rel_pct",
        "threshold_value": 5.0,
        "comparator": "dqn_core_only",
        "section": "Baselines",
    },
    {
        "id": "claim_ehm_computationally_efficient",
        "claim": "EHM is computationally efficient compared to rule-based.",
        "metric": "controller_runtime_s",
        "direction": "lower",
        "threshold_kind": "rel_pct",
        "threshold_value": 0.0,   # any significant *increase* fails this claim
        "comparator": "rule_based",
        "section": "Computational cost",
    },
    {
        "id": "claim_ehm_real_world_validated",
        "claim": "EHM is real-world validated.",
        "metric": None,
        "direction": "n/a",
        "threshold_kind": None,
        "threshold_value": 0.0,
        "comparator": None,
        "section": "Deployment",
    },
    {
        "id": "claim_ehm_validated_ieee13",
        "claim": "EHM has been validated on IEEE-13 (publication-grade).",
        "metric": None,
        "direction": "n/a",
        "threshold_kind": None,
        "threshold_value": 0.0,
        "comparator": None,
        "section": "Deployment",
    },
    {
        "id": "claim_flisr_reduces_ens_vs_noaction",
        "claim": "EHM (with FLISR) reduces cumulative ENS vs no-action baselines (persistence / random) under stress.",
        "metric": "stress_cumulative_unserved_energy",
        "direction": "lower",
        "threshold_kind": "rel_pct",
        "threshold_value": 5.0,
        "comparator": ["persistence", "random"],
        "section": "Reliability",
    },
]


def _find_stat(stats, *, metric: str, comparator: str, level: str):
    for row in stats:
        if (row["stress_level"] == level
                and row["controller_a"] == "full_stack"
                and row["controller_b"] == comparator
                and row["outcome_metric"] == metric):
            return row
    return None


def _runtime_stat(raw, *, comparator: str, level: str) -> dict:
    """Paired runtime stat computed directly from the corrected raw data."""
    a = raw[(raw["policy"] == "full_stack") & (raw["stress_level"] == level)].set_index("seed")["controller_runtime_s"]
    b = raw[(raw["policy"] == comparator) & (raw["stress_level"] == level)].set_index("seed")["controller_runtime_s"]
    common = sorted(set(a.index) & set(b.index))
    st = fc.paired_stats(a.loc[common].to_numpy(), b.loc[common].to_numpy())
    return {
        "median_diff": st["median_diff"],
        "rel_diff": st["rel_diff_pct"],
        "holm_p": fc.holm_adjust([st["wilcoxon_p"]])[0],
        "cliffs_delta": st["cliffs_delta"],
        "zero_diff_all": st["zero_diff_all"],
    }


def _level_verdict(row, direction: str, kind: str, thresh: float) -> str:
    """Return SUPPORTED / CONTRADICTED / INCONCLUSIVE for one (level, claim)."""
    if row is None:
        return "INCONCLUSIVE"
    p = row["holm_p"]
    if p is None or p >= 0.05 or row.get("zero_diff_all"):
        return "INCONCLUSIVE"
    diff = row["median_diff"]
    rel = row["rel_diff"]
    if kind == "abs_pp":
        effect_ok = diff >= thresh if direction == "higher" else diff <= -thresh
    else:  # rel_pct
        effect_ok = (rel <= -thresh) if direction == "lower" else (rel >= thresh)
    if effect_ok:
        return "SUPPORTED"
    wrong_way = (diff > 0) if direction == "lower" else (diff < 0)
    return "CONTRADICTED" if wrong_way else "INCONCLUSIVE"


def _find_row(raw, stats, *, metric: str, comparator: str, level: str):
    """Normalized stat row (median_diff / rel_diff / holm_p / cliffs_delta)."""
    if metric == "controller_runtime_s":
        return _runtime_stat(raw, comparator=comparator, level=level)
    row = _find_stat(stats, metric=metric, comparator=comparator, level=level)
    if row is None:
        return None
    return {
        "median_diff": row["paired_abs_diff_median"],
        "rel_diff": row["paired_rel_diff_pct"],
        "holm_p": row["wilcoxon_p_holm"],
        "cliffs_delta": row["cliffs_delta"],
        "zero_diff_all": row["zero_diff_all"],
    }


def _fmt_rel(row) -> str:
    if row is None or row.get("rel_diff") is None:
        return "nan"
    v = row["rel_diff"]
    return "nan" if v != v else f"{v:.2f}"


def build_audit(raw, stats) -> str:
    lines = []
    lines.append("# CORRECTED CLAIM AUDIT — Experiment B (540 runs)")
    lines.append("")
    lines.append("Anchored to the pre-registered primary outcomes in `paper_results_experiment_B/PRIMARY_OUTCOMES.md` and to directly measurable module / cost evidence. Classifications:")
    lines.append("")
    lines.append("- **SUPPORTED** — Holm p < 0.05, effect in the predicted direction, and the pre-registered effect threshold is met at every applicable stress level.")
    lines.append("- **PARTIALLY SUPPORTED** — passes in at least one stress level but not all.")
    lines.append("- **CONTRADICTED** — statistically significant effect in the *opposite* direction to the claim.")
    lines.append("- **INCONCLUSIVE** — no statistically detectable effect, or an effect below the threshold (absence of evidence, not evidence of absence).")
    lines.append("- **NOT TESTED** — claim requires evidence this simulation study does not produce.")
    lines.append("")

    summary_rows = []
    for claim in CANONICAL_CLAIMS:
        lines.append(f"## {claim['section']}")
        lines.append("")
        lines.append(f"### {claim['claim']}")
        lines.append("")
        if claim["metric"] is None:
            if claim["id"] == "claim_ehm_real_world_validated":
                note = ("Verdict: **NOT TESTED** — this is a simulation study. The claim requires field "
                        "measurements, hardware-in-the-loop, or deployment evidence that Experiment B does not produce.")
            else:
                note = ("Verdict: **NOT TESTED** — Experiment B runs on the 49-node simulator testbed. The IEEE-13 "
                        "work in this repository is a balanced positive-sequence per-unit *equivalent* with "
                        "validation_status `demonstrative`; it is not publication-grade IEEE-13 validation, and "
                        "Experiment B itself does not benchmark against the IEEE-13 reference.")
            lines.append(note)
            lines.append("")
            summary_rows.append([claim["id"], claim["section"], claim["claim"], "NOT TESTED", ""])
            continue

        level_verdicts = []
        comparators = claim["comparator"] if isinstance(claim["comparator"], list) else [claim["comparator"]]
        for level in fc.STRESS_LEVELS:
            sub = []
            for comp in comparators:
                row = _find_row(raw, stats, metric=claim["metric"], comparator=comp, level=level)
                v = _level_verdict(row, claim["direction"], claim["threshold_kind"], claim["threshold_value"])
                sub.append((comp, row, v))
                if row is None:
                    lines.append(f"- **{level}** vs `{comp}`: INCONCLUSIVE (no paired data).")
                    continue
                lines.append(
                    f"- **{level}** vs `{comp}`: **{v}** "
                    f"(`{claim['metric']}` median diff = {row['median_diff']:.3f}, "
                    f"rel diff = {_fmt_rel(row)} %, Holm p = {row['holm_p']:.4g}, "
                    f"Cliff's δ = {row['cliffs_delta']:.3f})"
                )
            # aggregate across comparators for this level: SUPPORTED only if all pass
            lvl_v = "SUPPORTED" if all(v == "SUPPORTED" for _, _, v in sub) else (
                "CONTRADICTED" if any(v == "CONTRADICTED" for _, _, v in sub) else "INCONCLUSIVE")
            level_verdicts.append(lvl_v)
            lines.append(f"- **{level} (combined)** — {lvl_v}")
            lines.append("")

        if any(v == "CONTRADICTED" for v in level_verdicts):
            final = "CONTRADICTED"
        elif all(v == "SUPPORTED" for v in level_verdicts):
            final = "SUPPORTED"
        elif any(v == "SUPPORTED" for v in level_verdicts):
            final = "PARTIALLY SUPPORTED"
        else:
            final = "INCONCLUSIVE"
        lines.append(f"**Verdict: {final}**")
        lines.append("")
        summary_rows.append([claim["id"], claim["section"], claim["claim"], final, ""])

    lines.append("---")
    lines.append("")
    lines.append("## Summary table")
    lines.append("")
    lines.append("| id | section | claim | verdict | evidence |")
    lines.append("|---|---|---|---|---|")
    for row in summary_rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append("## Notes on the headline finding")
    lines.append("")
    lines.append("- `claim_flisr_reduces_ens_vs_noaction` is the **only SUPPORTED claim**: the corrected data show a large, statistically significant ENS reduction for FLISR-enabled controllers vs `persistence`/`random` at both stress levels (e.g. severe median 1329.8 vs 6223.7; raw p ≈ 2e-6, Holm p < 0.05, Cliff's δ = -1.0).")
    lines.append("- All AI-stage and DQN-vs-rule-based claims are INCONCLUSIVE because every DQN-based arm is bit-identical per seed to `dqn_core_only` (identical trajectories), and `rule_based` (FLISR-only) is statistically indistinguishable from `full_stack` on PO1 at both levels (moderate p = 0.491, severe p = 0.102 raw; Holm p ≥ 0.41).")
    lines.append("- `claim_ehm_computationally_efficient` is CONTRADICTED: `full_stack` controller runtime is ~100x `rule_based` at both levels with Holm p < 0.05 (see below).")
    lines.append("- PO2/PO3/PO4 metrics are fully saturated (0 / 100 / 0 everywhere); those claims are INCONCLUSIVE because the instrument cannot discriminate controllers, not because the controller was shown equal.")
    lines.append("")
    lines.append("_Raw results were not modified._")
    lines.append("")
    return "\n".join(lines)


def runtime_evidence(raw) -> str:
    lines = ["## Computational-cost evidence (controller_runtime_s)", "", "Paired by seed, `full_stack` minus `rule_based`:", "", "| level | median FS | median rule_based | median diff | rel diff % | Wilcoxon p | Holm p | Cliff's d |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for level in fc.STRESS_LEVELS:
        a = raw[(raw["policy"] == "full_stack") & (raw["stress_level"] == level)].set_index("seed")["controller_runtime_s"]
        b = raw[(raw["policy"] == "rule_based") & (raw["stress_level"] == level)].set_index("seed")["controller_runtime_s"]
        common = sorted(set(a.index) & set(b.index))
        st = fc.paired_stats(a.loc[common].to_numpy(), b.loc[common].to_numpy())
        rel = "nan" if st["rel_diff_pct"] != st["rel_diff_pct"] else f"{st['rel_diff_pct']:.1f}"
        p4 = fc.esc_p(st["wilcoxon_p"])
        lines.append(
            f"| {level} | {st['median_a']:.4g} | {st['median_b']:.4g} | {st['median_diff']:.4g} "
            f"| {rel} | {p4} | {fc.esc_p(fc.holm_adjust([st['wilcoxon_p']])[0])} | {st['cliffs_delta']:.3f} |"
        )
    lines.append("")
    lines.append("`full_stack` is consistently ~100x slower in controller runtime than `rule_based`; the difference is statistically significant at both levels, contradicting any 'computationally efficient' claim.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    raw = fc.load_corrected_b()
    with open(os.path.join(OUT, "CORRECTED_STATISTICAL_ANALYSIS.json"), encoding="utf-8") as f:
        stats = json.load(f)

    md = build_audit(raw, stats)
    md = md.replace("## Notes on the headline finding",
                    runtime_evidence(raw) + "## Notes on the headline finding")
    path = os.path.join(OUT, "CORRECTED_CLAIM_AUDIT.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
