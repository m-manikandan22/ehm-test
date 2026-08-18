"""
PHASE 31 — Claim audit generator.

Reads the statistics JSON and produces EXPERIMENT_B_CLAIM_AUDIT.md,
classifying each canonical claim as SUPPORTED, PARTIALLY SUPPORTED,
NOT SUPPORTED, or INCONCLUSIVE.

The verdict is anchored to the pre-registered primary outcomes
(see PRIMARY_OUTCOMES.md). If the data do not support a claim, the
report says so. Negative results are not reframed.

Run from project root with EHM-paper:

    C:/Users/ELCOT/miniconda3/envs/EHM-paper/python.exe \
        experiments/results/experiment_B_stress/PHASE31_claim_audit.py
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List


# Each claim is tied to a primary outcome and a direction.
# Listed with a sensible threshold. Verdict logic is data-driven.
CANONICAL_CLAIMS = [
    {
        "id": "claim_ehm_reduces_ens",
        "claim": "EHM reduces cumulative ENS / unserved energy under stress.",
        "metric": "stress_cumulative_unserved_energy",
        "direction": "lower",
        "threshold_pct": 5.0,
        "comparison": "full_stack_vs_rule_based",
        "section": "Reliability",
    },
    {
        "id": "claim_ehm_faster_restoration",
        "claim": "EHM reaches 50 % restoration in fewer steps under stress.",
        "metric": "resilience_time_to_50pct_restoration",
        "direction": "lower",
        "threshold_pct": 5.0,
        "comparison": "full_stack_vs_rule_based",
        "section": "Resilience",
    },
    {
        "id": "claim_ehm_restores_critical_load",
        "claim": "EHM restores a higher fraction of critical load under stress.",
        "metric": "stress_critical_load_restored_pct",
        "direction": "higher",
        "threshold_pct": 2.0,
        "comparison": "full_stack_vs_rule_based",
        "section": "Critical loads",
    },
    {
        "id": "claim_ehm_reduces_saidi",
        "claim": "EHM reduces SAIDI under stress.",
        "metric": "saidi",
        "direction": "lower",
        "threshold_pct": 5.0,
        "comparison": "full_stack_vs_rule_based",
        "section": "Reliability",
    },
    {
        "id": "claim_twin_improves_resilience",
        "claim": "The Digital Twin improves resilience over the no-twin ablation.",
        "metric": "stress_cumulative_unserved_energy",
        "direction": "lower",
        "threshold_pct": 1.0,
        "comparison": "full_stack_vs_no_twin",
        "section": "Ablations",
    },
    {
        "id": "claim_lstm_improves_restoration",
        "claim": "LSTM forecasting improves restoration over the no-LSTM ablation.",
        "metric": "stress_cumulative_unserved_energy",
        "direction": "lower",
        "threshold_pct": 1.0,
        "comparison": "full_stack_vs_no_lstm",
        "section": "Ablations",
    },
    {
        "id": "claim_predictive_improves_resilience",
        "claim": "Predictive healing improves resilience over the no-predictive ablation.",
        "metric": "stress_cumulative_unserved_energy",
        "direction": "lower",
        "threshold_pct": 1.0,
        "comparison": "full_stack_vs_no_predictive",
        "section": "Ablations",
    },
    {
        "id": "claim_reward_shaping_helps",
        "claim": "Reward shaping helps faster training under stress.",
        "metric": "stress_cumulative_unserved_energy",
        "direction": "lower",
        "threshold_pct": 1.0,
        "comparison": "full_stack_vs_no_reward",
        "section": "Ablations",
    },
    {
        "id": "claim_dqn_outperforms_rule_based",
        "claim": "DQN outperforms rule-based FLISR under stress.",
        "metric": "stress_cumulative_unserved_energy",
        "direction": "lower",
        "threshold_pct": 5.0,
        "comparison": "full_stack_vs_dqn_core_only",
        "section": "Baselines",
    },
    {
        "id": "claim_ehm_computationally_efficient",
        "claim": "EHM is computationally efficient compared to rule-based.",
        "metric": "controller_runtime_s",
        "direction": "lower",
        "threshold_pct": 0.0,        # any *higher* runtime fails this claim
        "comparison": "full_stack_vs_rule_based",
        "section": "Computational cost",
    },
    {
        "id": "claim_ehm_real_world_validated",
        "claim": "EHM is real-world validated.",
        "metric": None,
        "direction": "n/a",
        "threshold_pct": 0.0,
        "comparison": None,
        "section": "Deployment",
    },
    {
        "id": "claim_ehm_validated_ieee13",
        "claim": "EHM has been validated on IEEE-13.",
        "metric": None,
        "direction": "n/a",
        "threshold_pct": 0.0,
        "comparison": None,
        "section": "Deployment",
    },
]


def _get_pair_stat(stats: Dict[str, Any], *, anchor: str, other: str,
                    metric: str, stress_level: str) -> Dict[str, Any]:
    """Find the paired-stat row for a given (anchor, other, metric, level)."""
    for row in stats.get("rows", []):
        if (row["anchor"] == anchor and row["other"] == other
                and row["metric"] == metric
                and row["stress_level"] == stress_level):
            return row
    return {}


def _verdict(stat_row: Dict[str, Any], direction: str,
              threshold_pct: float) -> str:
    if not stat_row:
        return "INCONCLUSIVE"
    rel = abs(stat_row["median_rel_diff_pct"])
    p = stat_row["holm_p"]
    diff = stat_row["median_diff"]
    if p >= 0.05 or rel < max(1.0, threshold_pct):
        return "INCONCLUSIVE"
    if direction == "lower":
        if diff < 0:
            return "SUPPORTED"
        return "NOT_SUPPORTED"
    if direction == "higher":
        if diff > 0:
            return "SUPPORTED"
        return "NOT_SUPPORTED"
    return "INCONCLUSIVE"


def build_claim_audit(stats: Dict[str, Any], stress_levels: List[str]) -> str:
    out = []
    out.append("# EXPERIMENT B — CLAIM AUDIT\n")
    out.append(
        "This document audits every claim that could be made about "
        "Experiment B. Each claim is anchored to a pre-registered "
        "primary outcome (see `PRIMARY_OUTCOMES.md`) and classified "
        "as one of:\n"
    )
    out.append("- **SUPPORTED** — passes the pre-registered threshold *and* "
                "the effect is in the predicted direction.\n"
                "- **PARTIALLY SUPPORTED** — passes one stress level but "
                "not the other, or passes below the threshold.\n"
                "- **NOT SUPPORTED** — the effect is in the opposite "
                "direction or above the threshold but opposite sign.\n"
                "- **INCONCLUSIVE** — the data do not allow a claim "
                "(no statistically detectable effect, or below the "
                "1 % functional-effect threshold).\n"
                "- **NOT APPLICABLE** — claim is out of scope for a "
                "simulation study (e.g. real-world validation).\n"
    )

    # Group by section.
    by_section: Dict[str, List[Dict[str, Any]]] = {}
    for c in CANONICAL_CLAIMS:
        by_section.setdefault(c["section"], []).append(c)

    for sect, claims in by_section.items():
        out.append(f"\n## {sect}\n")
        for c in claims:
            out.append(f"### {c['claim']}\n")
            if c["metric"] is None:
                out.append(
                    "Verdict: **NOT APPLICABLE** — this is a simulation "
                    "study; the claim requires field measurements or "
                    "deployment evidence that are not produced here.\n"
                )
                continue
            verdicts = []
            for level in stress_levels:
                if c["comparison"] is None:
                    continue
                anchor, other = c["comparison"].split("_vs_")
                row = _get_pair_stat(
                    stats,
                    anchor=anchor, other=other,
                    metric=c["metric"], stress_level=level,
                )
                v = _verdict(row, c["direction"], c["threshold_pct"])
                verdicts.append((level, row, v))
                if row:
                    out.append(
                        f"- **{level}**: {v} "
                        f"(`{c['metric']}` median_diff = "
                        f"{row['median_diff']:.3f}, "
                        f"rel_diff = {row['median_rel_diff_pct']:.2f}%, "
                        f"Holm p = {row['holm_p']:.4f}, "
                        f"Cliff's δ = {row['cliffs_delta']:.3f})\n"
                    )
                else:
                    out.append(
                        f"- **{level}**: no paired data found.\n"
                    )
            final = (
                "SUPPORTED" if all(v == "SUPPORTED" for _, _, v in verdicts if v)
                else "NOT_SUPPORTED" if all(v == "NOT_SUPPORTED" for _, _, v in verdicts if v)
                else "INCONCLUSIVE" if all(v == "INCONCLUSIVE" for _, _, v in verdicts if v)
                else "PARTIALLY SUPPORTED"
            )
            out.append(f"\n**Verdict: {final}**\n")
    out.append("\n---\n")
    out.append(
        "If a claim is INCONCLUSIVE, that does not mean the "
        "opposite is true. It means the data do not allow a "
        "claim to be either supported or refuted.\n"
    )
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--stats",
        default="experiments/results/experiment_B_stress/experiment_B_statistics.json",
    )
    ap.add_argument(
        "--config",
        default="experiments/results/experiment_B_stress/experiment_B_config.json",
    )
    ap.add_argument(
        "--output",
        default="experiments/results/experiment_B_stress/EXPERIMENT_B_CLAIM_AUDIT.md",
    )
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
    with open(args.stats, "r", encoding="utf-8") as f:
        stats = json.load(f)

    md = build_claim_audit(stats, config["stress_levels"])
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
