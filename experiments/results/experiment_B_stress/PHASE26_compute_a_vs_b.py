"""
PHASE 26 — Experiment A vs Experiment B comparison.

This script NEVER mixes raw samples from A and B into one
homogeneous dataset. It produces a side-by-side *summary* table
explaining the two experiments' different research questions,
data characteristics, and headline findings.

Output:
  tables/experiment_A_vs_B.csv
  tables/experiment_A_vs_B_overview.md
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
from typing import Any, Dict, List, Tuple


METRICS_FOR_COMPARISON = (
    "saifi", "saidi", "ens", "restoration_time_seconds",
    "critical_load_restored_pct", "voltage_violation_count",
    "line_overload_count", "switching_operations",
    "number_of_islands", "stress_cumulative_unserved_energy",
    "resilience_loss_area",
    "resilience_time_to_50pct_restoration",
    "stress_critical_load_restored_pct",
)


def _metric(r: Dict[str, Any], name: str) -> float:
    m = r.get("metrics", {}) or {}
    v = m.get(name)
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _by_level_policy(runs: List[Dict[str, Any]]):
    buckets: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in runs:
        level = r.get("stress_level") or r.get("scenario", {}).get(
            "stress_level", "")
        policy = r.get("controller_label") or r.get("policy", "")
        buckets.setdefault((str(level), str(policy)), []).append(r)
    return buckets


def build_comparison_csv(
        exp_a_nominal: List[Dict[str, Any]],
        exp_b_severe: List[Dict[str, Any]],
        anchor: str = "full_stack",
) -> List[Dict[str, Any]]:
    a_buckets = _by_level_policy(exp_a_nominal)
    b_buckets = _by_level_policy(exp_b_severe)
    rows = []
    for metric in METRICS_FOR_COMPARISON:
        a_vals = [
            _metric(r, metric)
            for r in a_buckets.get(("normal", anchor), [])
        ]
        b_vals = [
            _metric(r, metric)
            for r in b_buckets.get(("severe", anchor), [])
        ]
        rows.append({
            "metric": metric,
            "experiment_a_nominal_n": len(a_vals),
            "experiment_a_nominal_mean": (
                statistics.mean(a_vals) if a_vals else 0.0
            ),
            "experiment_a_nominal_std": (
                statistics.stdev(a_vals) if len(a_vals) > 1 else 0.0
            ),
            "experiment_b_severe_n": len(b_vals),
            "experiment_b_severe_mean": (
                statistics.mean(b_vals) if b_vals else 0.0
            ),
            "experiment_b_severe_std": (
                statistics.stdev(b_vals) if len(b_vals) > 1 else 0.0
            ),
        })
    return rows


def build_overview_md() -> str:
    """The static textual comparison between the two experiments."""
    out = []
    out.append("# Experiment A vs Experiment B — Overview\n")
    out.append(
        "Experiment A and Experiment B are *independent* "
        "experiments that answer *different* research questions. "
        "Their raw samples are **never** merged into one "
        "homogeneous dataset.\n"
    )
    out.append("\n## Experimental design contrast\n")
    out.append("| Item | Experiment A | Experiment B |")
    out.append("|---|---|---|")
    out.append("| Conditions | Nominal | Stress / constrained |")
    out.append("| Fault severity | 1–3 steps | moderate: 10–20; severe: 25–50 |")
    out.append("| Concurrent faults | 1 (3 sequential) | up to 2 (moderate), up to 3 (severe) |")
    out.append("| Capacity margin | Effectively unlimited | constrained (tie_capacity_mw 5.6 / 3.2) |")
    out.append("| Load level | 1.0× | 1.2× (moderate), 1.5× (severe) |")
    out.append("| Weather | normal | normal / storm |")
    out.append("| Critical-load competition | no | yes (fraction 0.7 / 0.4) |")
    out.append("| Controller variance | saturated | differentiates on secondary metrics |")
    out.append("| Primary findings | saturation | under-reported — see results |")
    out.append("| Research question | does the framework run? | does it help under stress? |")
    out.append("")
    out.append("## Why two experiments?\n")
    out.append(
        "Experiment A's null finding (no measurable controller "
        "differentiation on the standard metrics) is a *legitimate* "
        "scientific result. It is the evidence that motivates the "
        "stress benchmark. Experiment B is what the experiment "
        "looks like when the benchmark is allowed to be "
        "discriminating.\n"
    )
    out.append(
        "Critically, the *nominal* 49-node benchmark's near-flat "
        "tail of metrics is not a defect of the framework; it is "
        "evidence that the benchmark's disturbance profile is too "
        "mild to engage the controller's differentiating mechanisms.\n"
    )
    out.append(
        "Under the stress benchmark, the same FLISR engines and "
        "the same controllers are evaluated under conditions that "
        "demand differentiated decisions. The result is reported "
        "as-is, with no tuning of the benchmark based on the "
        "cross-controller ranking.\n"
    )
    out.append(
        "The two experiments therefore share simulation code but "
        "differ in their *benchmark*. Their raw outputs are "
        "preserved side-by-side so that the contrast can be "
        "audited by a reviewer.\n"
    )
    return "\n".join(out)


def _write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--exp-a",
        default="paper_results/raw/baseline_results.json",
    )
    ap.add_argument(
        "--exp-b",
        default="experiments/results/experiment_B_stress/experiment_B_runs.json",
    )
    ap.add_argument(
        "--output-dir",
        default="paper_results_experiment_B/tables",
    )
    args = ap.parse_args()

    with open(args.exp_a, "r", encoding="utf-8") as f:
        exp_a = json.load(f)
    exp_a = exp_a.get("runs", exp_a) if isinstance(exp_a, dict) else exp_a
    with open(args.exp_b, "r", encoding="utf-8") as f:
        exp_b = json.load(f)
    exp_b = exp_b.get("runs", exp_b) if isinstance(exp_b, dict) else exp_b

    rows = build_comparison_csv(exp_a, exp_b)
    _write_csv(os.path.join(args.output_dir, "experiment_A_vs_B.csv"), rows)
    overview = build_overview_md()
    with open(os.path.join(args.output_dir, "experiment_A_vs_B_overview.md"),
              "w", encoding="utf-8") as f:
        f.write(overview)
    print(f"Wrote {args.output_dir}/experiment_A_vs_B.csv")
    print(f"Wrote {args.output_dir}/experiment_A_vs_B_overview.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
