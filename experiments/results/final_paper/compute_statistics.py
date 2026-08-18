"""compute_statistics.py — Phase 17: Statistical analysis on the final
100-seed raw results.

Reads:
  - experiments/results/final_paper/raw/paper/baseline_results.json
  - experiments/results/final_paper/raw/paper/ablation_results.json

Produces:
  - experiments/results/final_paper/statistics/statistics.json
  - experiments/results/final_paper/statistics/statistics.md
  - experiments/results/final_paper/statistics/baseline_comparison.csv
  - experiments/results/final_paper/statistics/ablation_table.csv
  - experiments/results/final_paper/statistics/statistical_tests.csv
"""
from __future__ import annotations

import csv
import json
import os
import sys
from typing import Dict, List, Sequence, Tuple

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(THIS_DIR)))
for p in (os.path.join(PROJECT_ROOT, "backend"), PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from experiments.tables import (  # noqa: E402
    TABLE_METRICS, build_report, render_markdown, write_csv_and_markdown,
)


RAW_DIR = os.path.join("experiments", "results", "final_paper", "raw", "paper")
STAT_DIR = os.path.join("experiments", "results", "final_paper", "statistics")
os.makedirs(STAT_DIR, exist_ok=True)


# Table metrics relevant to a paper
KEY_METRICS = [
    "saifi", "saidi", "maifi", "asai", "ens",
    "restoration_time_seconds",
    "critical_load_restored_pct",
    "successful_restoration_count",
    "number_of_islands",
    "isolated_nodes",
    "actions_taken",
    "switching_operations",
    "voltage_violation_count",
    "line_overload_count",
    "minimum_voltage_pu",
    "maximum_voltage_pu",
    "operating_cost_usd",
    "outage_cost_usd",
    "carbon_kg",
    "runtime_s",
]


def _load_runs(path: str) -> List[Dict[str, object]]:
    with open(path) as f:
        rep = json.load(f)
    return rep.get("runs", [])


def _dataset_completeness(runs: List[Dict[str, object]], label: str
                          ) -> Dict[str, object]:
    n_total = len(runs)
    n_valid = sum(1 for r in runs if r.get("validity", {}).get("valid"))
    per_label: Dict[str, Dict[str, int]] = {}
    for r in runs:
        lbl = r.get("controller_label") or "<unknown>"
        b = per_label.setdefault(lbl, {"n_total": 0, "n_valid": 0})
        b["n_total"] += 1
        if r.get("validity", {}).get("valid"):
            b["n_valid"] += 1
    return {
        "label":        label,
        "n_total":      n_total,
        "n_valid":      n_valid,
        "n_invalid":    n_total - n_valid,
        "per_label":    per_label,
    }


def main() -> int:
    # 1. Load raw results
    base_path = os.path.join(RAW_DIR, "baseline_results.json")
    abl_path  = os.path.join(RAW_DIR, "ablation_results.json")
    if not os.path.exists(base_path):
        print(f"ERROR: {base_path} does not exist")
        return 1
    if not os.path.exists(abl_path):
        print(f"ERROR: {abl_path} does not exist")
        return 1

    base_runs = _load_runs(base_path)
    abl_runs  = _load_runs(abl_path)

    # 2. Dataset completeness
    base_complete = _dataset_completeness(base_runs, "baseline")
    abl_complete  = _dataset_completeness(abl_runs, "ablation")
    total_runs    = len(base_runs) + len(abl_runs)
    total_valid   = base_complete["n_valid"] + abl_complete["n_valid"]
    total_invalid = base_complete["n_invalid"] + abl_complete["n_invalid"]

    # 3. Generate reports
    baseline_report = build_report(runs=base_runs, anchor_label="rule_based")
    ablation_report = build_report(runs=abl_runs, anchor_label="full_stack")

    statistics = {
        "schema_version": "1.0",
        "experiment": "compute_statistics",
        "dataset_completeness": {
            "baseline": base_complete,
            "ablation": abl_complete,
            "total": {
                "n_total":      total_runs,
                "n_valid":      total_valid,
                "n_invalid":    total_invalid,
                "valid_rate":   (total_valid / total_runs) if total_runs else 0.0,
            },
        },
        "baseline": baseline_report,
        "ablation": ablation_report,
    }
    with open(os.path.join(STAT_DIR, "statistics.json"), "w") as f:
        json.dump(statistics, f, indent=2, sort_keys=True, default=str)

    # Markdown summary
    md = ["# EHM-simulation — Statistical Analysis",
          "",
          "## Dataset completeness",
          ""]
    md.append(f"- Baseline: {base_complete['n_valid']}/{base_complete['n_total']} valid "
              f"({base_complete['n_invalid']} invalid)")
    md.append(f"- Ablation: {abl_complete['n_valid']}/{abl_complete['n_total']} valid "
              f"({abl_complete['n_invalid']} invalid)")
    md.append(f"- **Total**: {total_valid}/{total_runs} valid "
              f"({total_invalid} invalid)")
    md.append("")
    md.append("## Baseline comparison (anchor: rule_based)")
    md.append("")
    md.append(render_markdown(baseline_report))
    md.append("")
    md.append("## Ablation study (anchor: full_stack)")
    md.append("")
    md.append(render_markdown(ablation_report))
    with open(os.path.join(STAT_DIR, "statistics.md"), "w") as f:
        f.write("\n".join(md))

    # CSV tables
    write_csv_and_markdown(
        baseline_report,
        csv_path=os.path.join(STAT_DIR, "baseline_comparison.csv"),
        md_path=os.path.join(STAT_DIR, "baseline_comparison.md"),
    )
    write_csv_and_markdown(
        ablation_report,
        csv_path=os.path.join(STAT_DIR, "ablation_table.csv"),
        md_path=os.path.join(STAT_DIR, "ablation_table.md"),
    )

    # Statistical tests CSV (only valid rows)
    stat_path = os.path.join(STAT_DIR, "statistical_tests.csv")
    with open(stat_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "anchor", "other", "metric", "n",
            "mean_difference", "std_difference",
            "ci95_low", "ci95_high",
            "t_statistic", "t_p_value",
            "wilcoxon_W", "wilcoxon_p",
            "effect_size", "effect_label", "significant_at_005",
            "valid",
        ])
        # Combine both reports into one big statistical tests file
        for src, rep in [("baseline", baseline_report),
                          ("ablation", ablation_report)]:
            for row in rep["paired"]:
                w.writerow([
                    row.get("anchor", ""),
                    row.get("other", ""),
                    row.get("metric", ""),
                    row.get("n", 0),
                    row.get("mean_difference", ""),
                    row.get("std_difference", ""),
                    row.get("ci95_low", ""),
                    row.get("ci95_high", ""),
                    row.get("t_statistic", ""),
                    row.get("t_p_value", ""),
                    row.get("wilcoxon_W", ""),
                    row.get("wilcoxon_p", ""),
                    row.get("effect_size", ""),
                    row.get("effect_label", ""),
                    row.get("significant_at_005", ""),
                    row.get("valid", False),
                ])

    # Validity summary CSV
    validity_path = os.path.join(STAT_DIR, "validity_summary.csv")
    with open(validity_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["policy", "n_total", "n_valid", "n_invalid", "valid_rate"])
        all_labels = sorted(set(
            list(base_complete["per_label"].keys()) +
            list(abl_complete["per_label"].keys())
        ))
        for lbl in all_labels:
            b = base_complete["per_label"].get(lbl, {"n_total": 0, "n_valid": 0})
            a = abl_complete["per_label"].get(lbl, {"n_total": 0, "n_valid": 0})
            n_total = b["n_total"] + a["n_total"]
            n_valid = b["n_valid"] + a["n_valid"]
            n_invalid = n_total - n_valid
            rate = n_valid / n_total if n_total else 0.0
            w.writerow([lbl, n_total, n_valid, n_invalid, f"{rate:.4f}"])

    # Runtime summary
    runtime_path = os.path.join(STAT_DIR, "runtime_summary.csv")
    with open(runtime_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["policy", "n", "mean_runtime_s",
                    "std_runtime_s", "median_runtime_s"])
        for lbl in all_labels:
            rts = []
            for r in base_runs + abl_runs:
                if r.get("controller_label") != lbl:
                    continue
                if not r.get("validity", {}).get("valid"):
                    continue
                m = r.get("metrics") or {}
                if "runtime_s" in m:
                    rts.append(float(m["runtime_s"]))
            if rts:
                mean_v = sum(rts) / len(rts)
                std_v = (sum((v - mean_v) ** 2 for v in rts) / (len(rts) - 1)) ** 0.5 \
                        if len(rts) > 1 else 0.0
                med = sorted(rts)[len(rts) // 2]
                w.writerow([lbl, len(rts), f"{mean_v:.4f}",
                            f"{std_v:.4f}", f"{med:.4f}"])
            else:
                w.writerow([lbl, 0, "", "", ""])

    print(f"Wrote statistics to {STAT_DIR}")
    print(f"Total runs: {total_runs}, valid: {total_valid}, "
          f"invalid: {total_invalid}")
    print(f"Per-policy:")
    for lbl, b in sorted({**base_complete['per_label'],
                           **abl_complete['per_label']}.items()):
        print(f"  {lbl}: total={b['n_total']} valid={b['n_valid']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())