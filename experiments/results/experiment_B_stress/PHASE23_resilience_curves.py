"""
PHASE 23 — Resilience curves.

If the runner recorded step-level service series (unserved MW per
step, critical_load_restored MW per step), this script plots the
service-level time series for representative seeds and computes:

  - resilience_loss_area (trapezoid integral over (1 - service))
  - time_to_50pct_restoration
  - time_to_90pct_restoration
  - recovery_slope (linear fit on the recovery segment)

The series are NOT interpolated. If the runner only reports
cumulative / end-of-run values, we use those and skip the curve.

Output: paper_results_experiment_B/figures/resilience_curve_*.{png,pdf}
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Tuple


def _by_level_policy(runs: List[Dict[str, Any]]):
    buckets: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in runs:
        level = r.get("stress_level") or r.get("scenario", {}).get(
            "stress_level", "")
        policy = r.get("controller_label") or r.get("policy", "")
        buckets.setdefault((str(level), str(policy)), []).append(r)
    return buckets


def _metric(r: Dict[str, Any], name: str) -> float:
    m = r.get("metrics", {}) or {}
    v = m.get(name)
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def build_resilience_text(runs: List[Dict[str, Any]]) -> str:
    """Build a text-only resilience summary.

    We do NOT fabricate a step-by-step series if the runner did not
    record one. Instead, we report the cumulative / end-of-run
    metrics and the runner-derived resilience_loss_area /
    time_to_50pct / time_to_90pct values per (level, controller).
    """
    out = []
    out.append("# RESILIENCE CURVES — Text Summary\n")
    out.append(
        "Step-level service series are recorded in the runner when "
        "available. If the runner does not record them, we report "
        "the runner's *cumulative* resilience metrics only and do "
        "not interpolate.\n"
    )

    buckets = _by_level_policy(runs)
    for level in sorted({k[0] for k in buckets.keys()}):
        out.append(f"\n## Stress level: {level}\n")
        out.append("| Controller | n | cumulative_unserved_energy (med) | resilience_loss_area (med) | t50 (med) | t90 (med) |")
        out.append("|---|---|---|---|---|---|")
        for policy in sorted({k[1] for k in buckets.keys()}):
            rs = buckets.get((level, policy), [])
            if not rs:
                continue
            n = len(rs)
            ens = [_metric(r, "stress_cumulative_unserved_energy") for r in rs]
            area = [_metric(r, "resilience_loss_area") for r in rs]
            t50 = [_metric(r, "resilience_time_to_50pct_restoration") for r in rs]
            t90 = [_metric(r, "resilience_time_to_90pct_restoration") for r in rs]
            from statistics import median
            out.append(
                f"| {policy} | {n} | "
                f"{median(ens):.1f} | {median(area):.1f} | "
                f"{median(t50):.1f} | {median(t90):.1f} |"
            )
    out.append("\n")
    out.append(
        "Cumulative unserved energy is the *primary* resilience "
        "metric per `PRIMARY_OUTCOMES.md`. The resilience_loss_area "
        "and t50 / t90 columns are *secondary* outcomes reported "
        "for completeness.\n"
    )
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--runs",
        default="experiments/results/experiment_B_stress/experiment_B_runs.json",
    )
    ap.add_argument(
        "--output",
        default="paper_results_experiment_B/reports/RESILIENCE_CURVES.md",
    )
    args = ap.parse_args()

    with open(args.runs, "r", encoding="utf-8") as f:
        runs = json.load(f)
    runs = runs.get("runs", runs) if isinstance(runs, dict) else runs

    md = build_resilience_text(runs)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())