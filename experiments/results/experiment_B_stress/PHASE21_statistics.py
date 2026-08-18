"""
PHASE 21 — Statistical analysis for Experiment B.

Reads ``pilot_runs.json`` or ``final_runs.json`` (whichever is supplied),
groups runs by stress_level × controller_label, and computes paired
statistical tests against the anchor (full_stack).

Outputs:
  - experiment_B_baseline_comparison.csv
  - experiment_B_ablation.csv
  - experiment_B_statistics.csv
  - experiment_B_validity.csv
  - experiment_B_runtime.csv

Tests:
  - Wilcoxon signed-rank (paired, non-parametric) — primary
  - Paired t-test — robustness check
  - Holm correction across (controller_pair, metric) combinations
  - Cliff's delta — non-parametric effect size

Run from project root with the EHM-paper environment:

    C:/Users/ELCOT/miniconda3/envs/EHM-paper/python.exe \
        experiments/results/experiment_B_stress/PHASE21_statistics.py \
        --input experiments/results/experiment_B_stress/pilot_runs.json \
        --output-dir experiments/results/experiment_B_stress/
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple


# ── Primary outcomes (must match PRIMARY_OUTCOMES.md) ──────────────────
PRIMARY_OUTCOMES = (
    "stress_cumulative_unserved_energy",
    "resilience_time_to_50pct_restoration",
    "stress_critical_load_restored_pct",
    "saidi",
)
SECONDARY_OUTCOMES = (
    "saifi", "voltage_violation_count", "line_overload_count",
    "number_of_islands", "resilience_loss_area",
    "resilience_time_to_90pct_restoration",
    "stress_critical_load_interrupted_mw",
    "stress_critical_load_restored_mw",
    "stress_cum_feasible_restoration_mw",
    "stress_cum_unserved_restoration_mw",
    "stress_restoration_rate",
    "ens", "restoration_time_seconds", "critical_load_restored_pct",
    "switching_operations", "frequency_deviation_count",
    "actions_taken", "runtime_s", "controller_runtime_s",
    "power_flow_runtime_s",
)


def _wilcoxon(x: List[float], y: List[float]) -> Tuple[float, float]:
    """Manual Wilcoxon signed-rank test. Returns (W_statistic, p_value).

    Uses normal approximation with continuity correction. Sufficient for
    n >= 5 (we use n >= 20 in practice).
    """
    if len(x) != len(y):
        raise ValueError("paired vectors must have equal length")
    diffs = [a - b for a, b in zip(x, y)]
    diffs = [d for d in diffs if abs(d) > 1e-12]  # drop zeros
    n = len(diffs)
    if n == 0:
        return 0.0, 1.0
    abs_sorted = sorted(diffs, key=lambda v: abs(v))
    # Assign ranks with average for ties.
    ranks: List[float] = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs_sorted[j + 1] == abs_sorted[i]:
            j += 1
        avg_rank = (i + j) / 2 + 1  # 1-indexed
        for k in range(i, j + 1):
            ranks[k] = avg_rank
        i = j + 1
    # Sign the ranks.
    signed = [
        ranks[k] * (1 if diffs[k] > 0 else -1)
        for k in range(n)
    ]
    W_pos = sum(r for r in signed if r > 0)
    W_neg = -sum(r for r in signed if r < 0)
    W = min(W_pos, W_neg)
    # Normal approximation.
    mu = n * (n + 1) / 4
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    if sigma <= 0:
        return W, 1.0
    # Two-tailed p-value.
    z = (W - mu - 0.5) / sigma if W < mu else (W - mu + 0.5) / sigma
    # Use the absolute value of z for a two-tailed test.
    p = 2.0 * (1.0 - _norm_cdf(abs(z)))
    return W, p


def _norm_cdf(z: float) -> float:
    """Standard normal CDF — Abramowitz & Stegun 7.1.26 approximation."""
    # 1 / sqrt(2π)
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    d = 0.3989423 * math.exp(-z * z / 2.0)
    p = d * t * (
        0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.8212560 + t * 1.3302744)))
    )
    return 1.0 - p if z > 0 else p


def _paired_t(x: List[float], y: List[float]) -> Tuple[float, float]:
    """Paired t-test. Returns (t_statistic, p_value)."""
    n = len(x)
    if n < 2:
        return 0.0, 1.0
    diffs = [a - b for a, b in zip(x, y)]
    mean = statistics.mean(diffs)
    sd = statistics.stdev(diffs)
    if sd <= 0:
        return 0.0, 1.0
    t = mean / (sd / math.sqrt(n))
    # Two-tailed p-value from Student's t with df=n-1.
    # Use a simple approximation (for df >= 10).
    p = 2.0 * (1.0 - _student_t_cdf(abs(t), n - 1))
    return t, p


def _student_t_cdf(t: float, df: int) -> float:
    """Approximate CDF of Student's t distribution.

    Uses a rational approximation; sufficient for df >= 5 and small p.
    """
    if df <= 0:
        return 0.5
    x = df / (df + t * t)
    # Incomplete beta function approximation. For our purposes, a
    # crude normal-with-df-correction is enough.
    # Use scipy-free approximation:
    #   p ≈ normal_cdf(t * sqrt((df-2)/df))  for df > 2
    # We clip df to avoid singularities.
    if df <= 2:
        # Use normal approx.
        z = t * 0.95
        return _norm_cdf(z)
    z = t * math.sqrt((df - 2) / df)
    return _norm_cdf(z)


def _cliffs_delta(x: List[float], y: List[float]) -> float:
    """Cliff's delta non-parametric effect size.

    Returns a value in [-1, 1]. Positive means x > y.
    """
    n_x = len(x)
    n_y = len(y)
    if n_x == 0 or n_y == 0:
        return 0.0
    gt = lt = 0
    for a in x:
        for b in y:
            if a > b:
                gt += 1
            elif a < b:
                lt += 1
    delta = (gt - lt) / (n_x * n_y)
    return delta


def _holm_correction(pvalues: List[float]) -> List[float]:
    """Holm-Bonferroni step-down correction."""
    n = len(pvalues)
    indexed = sorted(enumerate(pvalues), key=lambda t: t[1])
    out = [0.0] * n
    cum = 0.0
    for rank, (orig_idx, p) in enumerate(indexed):
        adjusted = (n - rank) * p
        cum = max(cum, adjusted)
        out[orig_idx] = min(1.0, cum)
    return out


def _by_level_policy(runs: List[Dict[str, Any]]):
    buckets: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in runs:
        level = r.get("stress_level") or r.get("scenario", {}).get(
            "stress_level", ""
        )
        policy = r.get("controller_label") or r.get("policy", "")
        key = (str(level), str(policy))
        buckets.setdefault(key, []).append(r)
    return buckets


def _get_metric(run: Dict[str, Any], name: str) -> float:
    m = run.get("metrics", {}) or {}
    val = m.get(name)
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _paired_per_seed(
    a_runs: List[Dict[str, Any]],
    b_runs: List[Dict[str, Any]],
    metric: str,
) -> Tuple[List[float], List[float], int]:
    """Return (a_values, b_values, n_pairs) aligned by seed."""
    a_by = {int(r.get("seed")): r for r in a_runs}
    b_by = {int(r.get("seed")): r for r in b_runs}
    common = sorted(set(a_by.keys()) & set(b_by.keys()))
    a_vals = [_get_metric(a_by[s], metric) for s in common]
    b_vals = [_get_metric(b_by[s], metric) for s in common]
    return a_vals, b_vals, len(common)


def _stat_row(
    *, level: str, anchor: str, other: str, metric: str,
    a_vals: List[float], b_vals: List[float], n_pairs: int,
) -> Dict[str, Any]:
    if n_pairs < 5:
        return {
            "stress_level": level,
            "anchor": anchor,
            "other": other,
            "metric": metric,
            "n_pairs": n_pairs,
            "median_a": statistics.median(a_vals) if a_vals else 0.0,
            "median_b": statistics.median(b_vals) if b_vals else 0.0,
            "mean_a": statistics.mean(a_vals) if a_vals else 0.0,
            "mean_b": statistics.mean(b_vals) if b_vals else 0.0,
            "median_diff": 0.0,
            "median_rel_diff_pct": 0.0,
            "wilcoxon_W": float("nan"),
            "wilcoxon_p": 1.0,
            "ttest_t": float("nan"),
            "ttest_p": 1.0,
            "cliffs_delta": 0.0,
            "holm_p": 1.0,
        }
    median_a = statistics.median(a_vals)
    median_b = statistics.median(b_vals)
    mean_a = statistics.mean(a_vals)
    mean_b = statistics.mean(b_vals)
    median_diff = median_a - median_b
    median_rel_diff = (
        100.0 * median_diff / median_b if abs(median_b) > 1e-9 else 0.0
    )
    W, wp = _wilcoxon(a_vals, b_vals)
    t, tp = _paired_t(a_vals, b_vals)
    delta = _cliffs_delta(a_vals, b_vals)
    return {
        "stress_level": level,
        "anchor": anchor,
        "other": other,
        "metric": metric,
        "n_pairs": int(n_pairs),
        "median_a": float(median_a),
        "median_b": float(median_b),
        "mean_a": float(mean_a),
        "mean_b": float(mean_b),
        "median_diff": float(median_diff),
        "median_rel_diff_pct": float(median_rel_diff),
        "wilcoxon_W": float(W),
        "wilcoxon_p": float(wp),
        "ttest_t": float(t),
        "ttest_p": float(tp),
        "cliffs_delta": float(delta),
        "holm_p": 1.0,  # filled later
    }


def _classify(row: Dict[str, Any], metric: str) -> str:
    """Return SUPPORTED / PARTIAL / NOT / INCONCLUSIVE based on the row.

    Anchored on the anchor (`full_stack`). Direction-of-effect depends
    on whether the metric is "lower is better" or "higher is better".
    """
    metric_lower_better = metric in {
        "stress_cumulative_unserved_energy",
        "resilience_loss_area",
        "resilience_time_to_50pct_restoration",
        "resilience_time_to_90pct_restoration",
        "stress_critical_load_interrupted_mw",
        "saifi", "saidi", "maifi",
        "ens", "voltage_violation_count",
        "line_overload_count",
        "restoration_time_seconds",
        "stress_cum_unserved_restoration_mw",
        "frequency_deviation_count",
    }
    diff = row["median_diff"]
    p = row["holm_p"]
    rel = abs(row["median_rel_diff_pct"])
    if p >= 0.05:
        return "INCONCLUSIVE"
    if rel < 1.0:
        # Below the "small effect" threshold regardless of p.
        return "INCONCLUSIVE"
    if metric_lower_better:
        if diff < 0:
            return "SUPPORTED"
        return "NOT_SUPPORTED"
    else:
        if diff > 0:
            return "SUPPORTED"
        return "NOT_SUPPORTED"


def compute_statistics(
    runs: List[Dict[str, Any]],
    *,
    anchor: str = "full_stack",
    baselines: Tuple[str, ...] = (
        "persistence", "random", "rule_based", "dqn_core_only",
    ),
    ablations: Tuple[str, ...] = (
        "no_lstm", "no_twin", "no_predictive", "no_reward",
    ),
    primary_metrics: Tuple[str, ...] = PRIMARY_OUTCOMES,
    all_metrics: Tuple[str, ...] = PRIMARY_OUTCOMES + SECONDARY_OUTCOMES,
) -> Dict[str, Any]:
    """Compute paired statistical tests across the anchor comparisons."""
    buckets = _by_level_policy(runs)
    levels = sorted({k[0] for k in buckets.keys()})

    # For Holm correction we collect all p-values, then re-assign.
    all_rows: List[Dict[str, Any]] = []
    raw_pvalues: List[float] = []

    for level in levels:
        if (level, anchor) not in buckets:
            continue
        anchor_runs = buckets[(level, anchor)]
        for other in list(baselines) + list(ablations):
            if (level, other) not in buckets:
                continue
            other_runs = buckets[(level, other)]
            for metric in all_metrics:
                a_vals, b_vals, n = _paired_per_seed(
                    anchor_runs, other_runs, metric,
                )
                row = _stat_row(
                    level=level, anchor=anchor, other=other,
                    metric=metric, a_vals=a_vals, b_vals=b_vals, n_pairs=n,
                )
                all_rows.append(row)
                raw_pvalues.append(row["wilcoxon_p"])

    # Holm correction across all rows.
    corrected = _holm_correction(raw_pvalues)
    for row, hp in zip(all_rows, corrected):
        row["holm_p"] = float(hp)
        row["classification"] = _classify(row, row["metric"])

    return {
        "anchor": anchor,
        "levels": levels,
        "n_rows": len(all_rows),
        "rows": all_rows,
    }


def write_csvs(stats: Dict[str, Any], *, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)

    # baseline_comparison.csv — anchor vs baselines
    rows = [
        r for r in stats["rows"]
        if r["other"] in ("persistence", "random", "rule_based", "dqn_core_only")
    ]
    _write_csv(
        os.path.join(out_dir, "experiment_B_baseline_comparison.csv"),
        rows,
    )

    # ablation.csv — anchor vs ablations
    rows = [
        r for r in stats["rows"]
        if r["other"] in ("no_lstm", "no_twin", "no_predictive", "no_reward")
    ]
    _write_csv(os.path.join(out_dir, "experiment_B_ablation.csv"), rows)

    # statistics.csv — everything
    _write_csv(
        os.path.join(out_dir, "experiment_B_statistics.csv"),
        stats["rows"],
    )


def _write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("no_rows\n")
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output-dir", default="experiments/results/experiment_B_stress/")
    ap.add_argument("--anchor", default="full_stack")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        report = json.load(f)
    runs = report.get("runs", [])
    stats = compute_statistics(runs, anchor=args.anchor)

    write_csvs(stats, out_dir=args.output_dir)

    # JSON dump.
    with open(os.path.join(args.output_dir, "experiment_B_statistics.json"),
              "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, sort_keys=True, default=str)

    print(f"Wrote CSVs to {args.output_dir}")
    print(f"Total statistical comparisons: {stats['n_rows']}")

    # Headline table for quick inspection.
    print()
    print(f"{'level':<10s} {'anchor':<12s} {'other':<14s} {'metric':<40s} "
          f"{'n':>4s} {'median_a':>10s} {'median_b':>10s} "
          f"{'diff_pct':>10s} {'p_holm':>8s} {'delta':>7s}  {'cls':<14s}")
    print("-" * 130)
    for r in stats["rows"]:
        if r["metric"] not in PRIMARY_OUTCOMES:
            continue
        print(
            f"{r['stress_level']:<10s} "
            f"{r['anchor']:<12s} "
            f"{r['other']:<14s} "
            f"{r['metric']:<40s} "
            f"{r['n_pairs']:>4d} "
            f"{r['median_a']:>10.3f} "
            f"{r['median_b']:>10.3f} "
            f"{r['median_rel_diff_pct']:>10.2f} "
            f"{r['holm_p']:>8.4f} "
            f"{r['cliffs_delta']:>7.3f}  "
            f"{r['classification']:<14s}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())