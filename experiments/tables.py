"""
tables.py — Auto-generate research tables from runner JSON.

This is the bridge between ``experiments/runner.py`` (which writes
``runner.json``) and the paper tables. It consumes one or more runner
reports and emits:

  - ``tables.json`` — a structured dict of every table (so consumers
    can render their own formats).
  - ``tables.csv``   — one CSV per table.
  - ``tables.md``    — a single Markdown report aggregating the tables.

What it computes
----------------
For each ``controller_label``, it aggregates every metric over the
(valid) runs that used that label — mean, std, n. Then it computes
the paired comparison of every non-baseline label against the
``rule_based`` label (or any other anchor the caller chooses). The
comparison emits mean difference, 95 % CI, paired t, Wilcoxon W, and
Cohen's d.

Why it exists
-------------
Manual copy-paste from JSON to a paper table is the largest source
of typos in research. This module is the single source of truth that
the runner, the aggregator, and the report all agree on.

Usage
-----
    python -m experiments.tables \
        --input experiments/results/runner.json \
        --output experiments/results/tables.json \
        --csv experiments/results/tables.csv \
        --md experiments/results/tables.md \
        --anchor rule_based
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from collections import defaultdict
from statistics import mean, pstdev
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")
for p in (BACKEND_ROOT, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from metrics.statistics import (  # noqa: E402
    ci95, cohens_d_paired, mean as stats_mean, paired_comparison,
    paired_t, paired_t_pvalue, std as stats_std, summarise,
)


logger = logging.getLogger(__name__)


# ── Metric catalogue ────────────────────────────────────────────────────
# The set of metrics we summarise in the per-policy table, plus a
# human-readable label and whether *lower* is better. This is the
# single source of truth for column ordering in tables.csv.
TABLE_METRICS: Tuple[Tuple[str, str, str], ...] = (
    ("saifi",                        "SAIFI (faults/node)",                 "lower"),
    ("saidi",                        "SAIDI (steps)",                       "lower"),
    ("maifi",                        "MAIFI (events/node)",                 "lower"),
    ("asai",                         "ASAI",                                "higher"),
    ("ens",                          "ENS (step·count)",                    "lower"),
    ("restoration_time_steps",       "Avg restoration (steps)",             "lower"),
    ("critical_load_restored_pct",   "Critical-load restored (%)",         "higher"),
    ("successful_restoration_count", "Successful restorations",             "higher"),
    ("number_of_islands",            "Islands",                             "lower"),
    ("isolated_nodes",               "Isolated nodes",                      "lower"),
    ("actions_taken",                "Actions taken",                       "neutral"),
    ("switching_operations",         "Switching operations",                "neutral"),
    ("illegal_actions_attempted",    "Illegal actions",                     "lower"),
    ("load_shedding_events",         "Load-shedding events",                "lower"),
    ("battery_dispatch_events",      "Battery dispatches",                  "neutral"),
    ("voltage_violation_count",      "Voltage violations",                  "lower"),
    ("frequency_deviation_count",    "Frequency deviations",                "lower"),
    ("line_overload_count",          "Line overloads",                      "lower"),
    ("minimum_voltage_pu",           "Vmin (pu)",                           "higher"),
    ("maximum_voltage_pu",           "Vmax (pu)",                           "lower"),
    ("average_voltage_pu",           "Vavg (pu)",                           "neutral"),
    ("operating_cost_usd",           "Operating cost (USD)",                "lower"),
    ("outage_cost_usd",              "Outage cost (USD)",                   "lower"),
    ("carbon_kg",                    "Carbon (kg)",                         "lower"),
    ("runtime_s",                    "Run time (s)",                        "neutral"),
)


# ── Per-policy aggregate ────────────────────────────────────────────────
def aggregate_by_policy(
    runs: Sequence[Dict[str, object]],
    *,
    metric_keys: Optional[Sequence[str]] = None,
) -> List[Dict[str, object]]:
    """Group valid runs by ``controller_label`` and summarise each metric.

    Returns a list of dicts — one per policy. Each dict contains the
    policy label, the n of valid runs, the active and disabled module
    lists (from the first run of that label), and a ``metrics`` dict
    holding the summarise() result for every metric in
    ``TABLE_METRICS`` (or ``metric_keys``).
    """
    keys = list(metric_keys) if metric_keys else [k for k, *_ in TABLE_METRICS]
    by_policy: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for run in runs:
        if not run.get("validity", {}).get("valid", False):
            continue
        label = run.get("controller_label", "") or "<unknown>"
        by_policy[label].append(run)

    out: List[Dict[str, object]] = []
    for label, group in by_policy.items():
        cfg = group[0].get("config") or {}
        # Per-metric aggregate.
        per_metric: Dict[str, Dict[str, float]] = {}
        for k in keys:
            values: List[float] = []
            for run in group:
                m = run.get("metrics") or {}
                v = m.get(k)
                if isinstance(v, (int, float)):
                    values.append(float(v))
            per_metric[k] = summarise(values) if values else {
                "n": 0, "mean": 0.0, "std": 0.0, "median": 0.0,
                "min": 0.0, "max": 0.0, "ci95_low": 0.0, "ci95_high": 0.0,
            }
        out.append({
            "controller_label":  label,
            "n_valid_runs":      len(group),
            "active_modules":    cfg.get("active_modules", []),
            "disabled_modules":  cfg.get("disabled_modules", []),
            "metrics":           per_metric,
        })
    # Stable order: alphabetical by label.
    out.sort(key=lambda r: r["controller_label"])
    return out


# ── Paired comparison table ─────────────────────────────────────────────
def paired_table(
    runs: Sequence[Dict[str, object]],
    *,
    anchor_label: str = "rule_based",
    metric_keys: Optional[Sequence[str]] = None,
) -> List[Dict[str, object]]:
    """Compare every other policy against ``anchor_label`` per metric.

    For each metric and each non-anchor policy, we run
    ``paired_comparison`` on the matched (seed, weather) pairs of
    valid runs. Returns one row per (metric, policy) pair.
    """
    keys = list(metric_keys) if metric_keys else [k for k, *_ in TABLE_METRICS]

    # Index runs by (label, seed, weather).
    index: Dict[Tuple[str, int, str], Dict[str, object]] = {}
    for run in runs:
        if not run.get("validity", {}).get("valid", False):
            continue
        key = (
            run.get("controller_label", "") or "<unknown>",
            int(run.get("seed", -1)),
            str(run.get("weather_mode", "")),
        )
        index[key] = run

    anchor_runs = [
        run for run in runs
        if run.get("validity", {}).get("valid", False)
        and run.get("controller_label") == anchor_label
    ]
    if not anchor_runs:
        logger.warning(
            "Anchor label %r has no valid runs; skipping paired table.",
            anchor_label,
        )
        return []

    # Collect the set of (label, seed, weather) pairs where the anchor
    # has a match; we only compare on those pairs.
    pairs = [
        (int(r["seed"]), str(r["weather_mode"]))
        for r in anchor_runs
    ]

    # Identify the non-anchor labels that have matched pairs.
    other_labels = sorted({
        lbl for (lbl, s, w) in index.keys()
        if lbl != anchor_label and (s, w) in set(pairs)
    })

    rows: List[Dict[str, object]] = []
    for other in other_labels:
        for k in keys:
            a_vals: List[float] = []
            b_vals: List[float] = []
            for seed, weather in pairs:
                a_run = index.get((anchor_label, seed, weather))
                b_run = index.get((other,        seed, weather))
                if not a_run or not b_run:
                    continue
                a_m = a_run.get("metrics") or {}
                b_m = b_run.get("metrics") or {}
                a = a_m.get(k); b = b_m.get(k)
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    a_vals.append(float(a))
                    b_vals.append(float(b))
            if len(a_vals) < 2:
                # n<2; paired_comparison returns invalid; surface it
                # anyway so the consumer sees we *tried*.
                rows.append({
                    "anchor":       anchor_label,
                    "other":        other,
                    "metric":       k,
                    "n":            len(a_vals),
                    "valid":        False,
                    "reason":       "n<2; cannot compute paired test",
                })
                continue
            comp = paired_comparison(
                a_vals, b_vals,
                label_a=anchor_label, label_b=other,
            )
            rows.append({
                "anchor":       anchor_label,
                "other":        other,
                "metric":       k,
                **comp,
            })
    return rows


# ── Aggregate report ────────────────────────────────────────────────────
def build_report(
    *,
    runs: Sequence[Dict[str, object]],
    anchor_label: str = "rule_based",
) -> Dict[str, object]:
    """Build the full tables dict (per-policy + paired + summary)."""
    by_policy = aggregate_by_policy(runs)
    paired = paired_table(runs, anchor_label=anchor_label)
    n_total   = len(runs)
    n_valid   = sum(1 for r in runs if r["validity"]["valid"])
    return {
        "schema_version":  "1.0",
        "experiment":      "experiments.tables",
        "anchor":          anchor_label,
        "n_total_runs":    n_total,
        "n_valid_runs":    n_valid,
        "valid_rate":      (n_valid / n_total) if n_total else 0.0,
        "per_policy":      by_policy,
        "paired":          paired,
    }


# ── Markdown report ─────────────────────────────────────────────────────
def render_markdown(report: Dict[str, object]) -> str:
    """Render the report dict as a single Markdown document."""
    lines: List[str] = []
    lines.append("# EHM-simulation — Research Tables")
    lines.append("")
    lines.append(
        f"_Generated from `{report.get('experiment', 'experiments.tables')}`._"
    )
    lines.append("")
    lines.append("## Run summary")
    lines.append("")
    lines.append(
        f"- Total runs: **{report['n_total_runs']}**, "
        f"valid: **{report['n_valid_runs']}** "
        f"({report['valid_rate'] * 100:.1f} %)."
    )
    lines.append(f"- Anchor policy for paired comparison: `{report['anchor']}`.")
    lines.append("")

    # ── Per-policy table ──────────────────────────────────────────────
    lines.append("## Per-policy summary")
    lines.append("")
    lines.append(
        "Mean ± std over all valid runs of each configuration. "
        "Cells with `n=0` mean the metric was not produced for that policy."
    )
    lines.append("")
    header = ["Policy", "n", "Active modules", "Disabled modules"] + [
        m[1] for m in TABLE_METRICS
    ]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for row in report["per_policy"]:
        active = ", ".join(row["active_modules"]) or "—"
        disabled = ", ".join(row["disabled_modules"]) or "—"
        cells = [
            f"`{row['controller_label']}`",
            str(row["n_valid_runs"]),
            active,
            disabled,
        ]
        for k, _, direction in TABLE_METRICS:
            m = row["metrics"].get(k) or {}
            n = m.get("n", 0)
            if n == 0:
                cells.append("—")
            else:
                marker = ""
                # Direction is informational; we don't penalise here.
                if direction != "neutral":
                    marker = ""  # direction marker not used in markdown
                cells.append(f"{m.get('mean', 0.0):.3f} ± {m.get('std', 0.0):.3f}")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    # ── Paired comparison table ───────────────────────────────────────
    lines.append(f"## Paired comparison vs `{report['anchor']}`")
    lines.append("")
    lines.append(
        "Each row is a paired test on (anchor, other) matched by "
        "(seed, weather). `d` is Cohen's d (paired); positive "
        "`mean_diff` means anchor > other for that metric."
    )
    lines.append("")
    pheader = ["Other", "Metric", "n", "mean_diff", "t", "p(t)", "Wilcoxon p", "Cohen's d", "Effect", "Sig@0.05"]
    lines.append("| " + " | ".join(pheader) + " |")
    lines.append("|" + "|".join(["---"] * len(pheader)) + "|")
    for row in report["paired"]:
        if not row.get("valid", False):
            lines.append(
                f"| `{row.get('other')}` | `{row.get('metric')}` "
                f"| {row.get('n', 0)} | — | — | — | — | — | — | "
                f"{row.get('reason', 'n<2')} |"
            )
            continue
        cells = [
            f"`{row['other']}`",
            f"`{row['metric']}`",
            str(row["n"]),
            f"{row['mean_difference']:.4f}",
            f"{row['t_statistic']:.3f}",
            f"{row['t_p_value']:.4f}",
            f"{row['wilcoxon_p']:.4f}",
            f"{row['effect_size']:.3f}",
            row["effect_label"],
            "yes" if row["significant_at_005"] else "no",
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    return "\n".join(lines)


# ── CSV writer ──────────────────────────────────────────────────────────
def _write_csv(report: Dict[str, object], path: str) -> None:
    """Write one CSV per table — per-policy and paired."""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        # Per-policy section header.
        w.writerow(["# per_policy_summary"])
        w.writerow(
            ["controller_label", "n_valid_runs", "active_modules",
             "disabled_modules", "metric", "n", "mean", "std",
             "median", "min", "max", "ci95_low", "ci95_high"]
        )
        for row in report["per_policy"]:
            for k, *_ in TABLE_METRICS:
                m = row["metrics"].get(k) or {}
                w.writerow([
                    row["controller_label"],
                    row["n_valid_runs"],
                    ";".join(row["active_modules"]),
                    ";".join(row["disabled_modules"]),
                    k,
                    m.get("n", 0),
                    f"{m.get('mean', 0.0):.6f}",
                    f"{m.get('std', 0.0):.6f}",
                    f"{m.get('median', 0.0):.6f}",
                    f"{m.get('min', 0.0):.6f}",
                    f"{m.get('max', 0.0):.6f}",
                    f"{m.get('ci95_low', 0.0):.6f}",
                    f"{m.get('ci95_high', 0.0):.6f}",
                ])
        w.writerow([])
        # Paired section header.
        w.writerow(["# paired_comparison"])
        w.writerow([
            "anchor", "other", "metric", "n", "valid", "reason",
            "mean_difference", "std_difference", "ci95_low", "ci95_high",
            "t_statistic", "t_p_value", "wilcoxon_W", "wilcoxon_p",
            "effect_size", "effect_label", "significant_at_005",
        ])
        for row in report["paired"]:
            w.writerow([
                row.get("anchor", ""),
                row.get("other", ""),
                row.get("metric", ""),
                row.get("n", 0),
                row.get("valid", False),
                row.get("reason", "") or "",
                f"{row.get('mean_difference', 0.0):.6f}",
                f"{row.get('std_difference', 0.0):.6f}",
                f"{row.get('ci95_low', 0.0):.6f}",
                f"{row.get('ci95_high', 0.0):.6f}",
                f"{row.get('t_statistic', 0.0):.6f}",
                f"{row.get('t_p_value', 1.0):.6f}",
                f"{row.get('wilcoxon_W', 0.0):.6f}",
                f"{row.get('wilcoxon_p', 1.0):.6f}",
                f"{row.get('effect_size', 0.0):.6f}",
                row.get("effect_label", "") or "",
                row.get("significant_at_005", False),
            ])


def write_csv_and_markdown(
    report: Dict[str, object],
    *,
    csv_path: str,
    md_path: str,
) -> None:
    """Write the report to both CSV and Markdown.

    Convenience wrapper used by :mod:`experiments.paper_experiment`.
    Creates the parent directories if needed.
    """
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(md_path) or ".", exist_ok=True)
    _write_csv(report, csv_path)
    with open(md_path, "w") as f:
        f.write(render_markdown(report))


# ── CLI ─────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", required=True,
        help="Path to runner.json (the output of experiments.runner).",
    )
    parser.add_argument(
        "--output", default="experiments/results/tables.json",
        help="Path to write the structured tables JSON.",
    )
    parser.add_argument(
        "--csv", default="experiments/results/tables.csv",
        help="Path to write the tables CSV.",
    )
    parser.add_argument(
        "--md", default="experiments/results/tables.md",
        help="Path to write the tables Markdown report.",
    )
    parser.add_argument(
        "--anchor", default="rule_based",
        help="Policy label to use as the anchor for paired comparison.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    with open(args.input) as f:
        report = json.load(f)
    runs = report.get("runs", []) or []

    tables = build_report(runs=runs, anchor_label=args.anchor)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(tables, f, indent=2, sort_keys=True, default=str)

    _write_csv(tables, args.csv)
    md = render_markdown(tables)
    with open(args.md, "w") as f:
        f.write(md)

    print(f"Wrote {args.output}")
    print(f"Wrote {args.csv}")
    print(f"Wrote {args.md}")
    print(f"per-policy rows: {len(tables['per_policy'])}, "
          f"paired rows: {len(tables['paired'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())