"""
report.py — Aggregate benchmark JSON into a Markdown report.

Computes mean ± std, 95 % CI, and a paired t-test between the rule-based
baseline and random. Writes REPORT.md.

Statistical primitives are delegated to `backend/metrics/statistics.py`
so the experiments framework and the benchmarks framework share one
implementation. See that module for citations and small-sample caveats.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List

from metrics.statistics import (
    ci95,
    is_significant,
    mean as _mean,
    paired_t as _paired_t,
    std as _std,
)


def aggregate(json_path: str, out_md_path: str) -> None:
    with open(json_path, "r") as f:
        data = json.load(f)

    results = data["results"]
    metrics = sorted({m for r in results for m in r["metrics"].keys()})
    policies = sorted({r["policy"] for r in results})

    lines: List[str] = []
    lines.append("# EHM Benchmark Report")
    lines.append("")
    lines.append(
        f"- Generated from: `{os.path.basename(json_path)}`\n"
        f"- Total runs: **{data['total_runs']}** "
        f"(seeds={data['n_seeds']}, "
        f"policies={data['n_policies']}, "
        f"scenarios={data['n_scenarios']}, "
        f"weather modes={data['n_weathers']})\n"
        f"- Wall-clock: {data['wallclock_s']} s"
    )
    lines.append("")
    lines.append("## Per-metric aggregates (mean ± std, 95% CI)")
    lines.append("")

    # Index results by (policy, metric) → list of values
    by_policy: Dict[str, Dict[str, List[float]]] = {
        p: {m: [] for m in metrics} for p in policies
    }
    for r in results:
        for m, v in r["metrics"].items():
            by_policy[r["policy"]][m].append(v)

    lines.append("| Metric | " + " | ".join(policies) + " |")
    lines.append("|---" * (len(policies) + 1) + "|")
    for m in metrics:
        row = [f"`{m}`"]
        for p in policies:
            xs = by_policy[p][m]
            mn = _mean(xs)
            sd = _std(xs)
            lo, hi = _ci95(xs)
            row.append(f"{mn:.3f} ± {sd:.3f}  ({lo:.3f}–{hi:.3f})")
        lines.append("| " + " | ".join(row) + " |")

    # Paired t-test: rule-based vs random (if both present)
    if "random" in policies and "rule_based" in policies:
        lines.append("")
        lines.append("## Paired t-test: rule_based vs random")
        lines.append("")
        lines.append("| Metric | t-statistic | Significant (p < 0.05) |")
        lines.append("|---|---|---|")
        for m in metrics:
            a = by_policy["rule_based"][m]
            b = by_policy["random"][m]
            t = _paired_t(a, b)
            sig = "**YES**" if is_significant(t, n=len(a)) else "no"
            lines.append(f"| `{m}` | {t:+.3f} | {sig} |")

    os.makedirs(os.path.dirname(out_md_path) or ".", exist_ok=True)
    with open(out_md_path, "w") as f:
        f.write("\n".join(lines))
    print(f"[report] Wrote {out_md_path}")


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--input",  default="benchmarks/results/run.json")
    p.add_argument("--output", default="benchmarks/results/REPORT.md")
    args = p.parse_args()
    aggregate(args.input, args.output)


if __name__ == "__main__":
    main()