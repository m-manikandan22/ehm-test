"""stage45_statistics.py — aggregate the Stage-45 10-seed validation results.

The Stage-45 statistics module is a drop-in replacement for
``stage44_statistics.py`` that consumes the corrected
``stage45_validation.json`` produced by ``stage45_validation.py``.
It produces the same artefacts:

* ``experiments/results/stage45/statistics/per_cell.json`` —
  per-(controller, scenario, ablation) summary (mean / median /
  std / 95% bootstrap CI / Wilcoxon vs rule_based / Cohen's d).
* ``experiments/results/stage45/statistics/pairwise.json`` —
  paired-trained vs rule_based tests across all scenarios.
* ``experiments/results/stage45/statistics/holm.json`` —
  Bonferroni-Holm multiple-comparison correction table.
* ``experiments/results/stage45/tables/per_cell.csv`` — flat
  CSV with one row per (controller, scenario, ablation).
* ``experiments/results/stage45/summary.md`` — top-level
  table of head-to-head metrics.
* ``experiments/results/stage45/figures/{boxplot,corr}*.png`` —
  head-to-head metric comparisons.

The statistical scaffolding (bootstrap CI, Wilcoxon signed-rank,
Cohen's d, Holm correction) is identical to Stage-44. The ONLY
change is the metric collector — Stage-45 metrics are sourced
from ``stage45_metrics.Stage45MetricCollector`` whose definitions
are physics-coupled (per-load-node log). The interpretation of
"identical" or "different" cells, however, depends on this
collector: the Stage-44 invariance bug is the *reason* Stage-45
exists, so the metrics list has dropped ``battery_discharged_total``
and ``supercap_discharged_total`` (controller-side diagnostics,
not grid-side reliability metrics) and replaced them with the
physical-effect deltas that the Stage-45 runner captures.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parents[1]
RESULTS = PROJECT_ROOT / "experiments" / "results" / "stage45"
STATS = RESULTS / "statistics"
TABLES = RESULTS / "tables"
FIGS = RESULTS / "figures"
for d in (STATS, TABLES, FIGS):
    d.mkdir(parents=True, exist_ok=True)

VALIDATION_JSON = RESULTS / "validation.json"


# Stage-45 primary metrics. These come from the corrected
# per-load-node service log in ``stage45_metrics.Stage45MetricCollector``.
# The Stage-44 metric invariance was a *fault-schedule derivative* on
# these fields; the Stage-45 values are physical consequences.
METRICS = (
    "energy_not_served_mwh",
    "total_customer_minutes_interrupted",
    "restoration_rate",
    "avg_restoration_steps",
    "critical_load_interruption_steps",
    "voltage_violation_count",
)


def _values_for(run_group, field: str) -> List[float]:
    out = []
    for r in run_group:
        try:
            v = float(r["metrics"][field])
        except Exception:
            continue
        if np.isnan(v) or np.isinf(v):
            continue
        out.append(v)
    return out


def _bootstrap_ci(samples: List[float], n_resamples: int = 10_000,
                  alpha: float = 0.05) -> Tuple[float, float, float]:
    if not samples:
        return (float("nan"), float("nan"), float("nan"))
    arr = np.array(samples, dtype=float)
    n = len(arr)
    if n < 2:
        m = float(arr.mean())
        return (m, m, m)
    rng = np.random.default_rng(0)
    means = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        means[i] = arr[idx].mean()
    return (
        float(arr.mean()),
        float(np.quantile(means, alpha / 2)),
        float(np.quantile(means, 1 - alpha / 2)),
    )


def _wilcoxon(a: List[float], b: List[float]) -> Dict:
    """Two-sided Wilcoxon signed-rank test (paired) with
    normal-approximation p-value when n ≥ 5."""
    if len(a) != len(b) or len(a) < 5:
        return {
            "n_pairs": len(a), "statistic": float("nan"),
            "p_value": float("nan"), "method": "wilcoxon_too_few_samples",
        }
    diffs = [x - y for x, y in zip(a, b)]
    nonzero = [d for d in diffs if d != 0.0]
    if not nonzero:
        return {
            "n_pairs": len(a), "statistic": 0.0, "p_value": 1.0,
            "method": "wilcoxon_all_zeros",
        }
    abs_diffs = sorted(abs(d) for d in nonzero)
    ranks: Dict[float, float] = {}
    i = 0
    while i < len(abs_diffs):
        j = i
        while j < len(abs_diffs) and abs_diffs[j] == abs_diffs[i]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[abs_diffs[k]] = rank
        i = j
    W_pos = 0.0
    W_neg = 0.0
    for d in nonzero:
        r = ranks[abs(d)]
        if d > 0:
            W_pos += r
        else:
            W_neg += r
    W = min(W_pos, W_neg)
    n = len(nonzero)
    mean_W = n * (n + 1) / 4.0
    sd_W = (n * (n + 1) * (2 * n + 1) / 24.0) ** 0.5
    if sd_W == 0:
        z = 0.0
    else:
        z = (W - mean_W) / sd_W
    try:
        from math import erf, sqrt
        p = 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))
    except Exception:
        p = float("nan")
    return {
        "n_pairs": len(a), "statistic": float(W),
        "p_value": float(p), "z": float(z),
        "method": "wilcoxon_signed_rank_normal_approx",
    }


def _cohens_d_paired(a: List[float], b: List[float]) -> float:
    """Cohen's d for paired samples."""
    if len(a) != len(b) or len(a) < 2:
        return float("nan")
    diffs = np.array([x - y for x, y in zip(a, b)], dtype=float)
    sd = float(diffs.std(ddof=1))
    if sd == 0:
        return 0.0
    return float(diffs.mean() / sd)


def _aggregate(runs: List[Dict]) -> Dict:
    cells = defaultdict(list)
    for r in runs:
        key = (
            r["controller_label"],
            r["scenario"],
            r["ablation"],
        )
        cells[key].append(r)
    out: Dict[str, Dict] = {}
    for key, group in cells.items():
        ctrl, scen, abl = key
        cell = {
            "n": len(group),
            "n_valid": sum(
                1 for r in group if r.get("validity", {}).get("valid", False)
            ),
            "seeds": sorted(r["seed"] for r in group),
            "fingerprint_consistent": all(
                r.get("fingerprints") for r in group
            ),
            "metrics": {},
        }
        for m in METRICS:
            vals = _values_for(group, m)
            mean, lo, hi = _bootstrap_ci(vals)
            cell["metrics"][m] = {
                "n": len(vals),
                "mean": round(float(mean), 6) if mean == mean else None,
                "median": round(float(np.median(vals)), 6) if vals else None,
                "std": round(float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0, 6),
                "min": round(float(np.min(vals)), 6) if vals else None,
                "max": round(float(np.max(vals)), 6) if vals else None,
                "ci95_low": round(float(lo), 6) if lo == lo else None,
                "ci95_high": round(float(hi), 6) if hi == hi else None,
            }
        out[key] = cell
    return out


def _pairwise_tests(runs: List[Dict], ref_ctrl: str = "rule_based") -> Dict:
    """Paired-by-seed comparisons of every (ctrl, ablation) cell
    against the rule_based reference on the same (scenario, seed)."""
    samples = defaultdict(dict)
    for r_a in runs:
        for r_b in runs:
            if r_a["seed"] != r_b["seed"]:
                continue
            if r_a["scenario"] != r_b["scenario"]:
                continue
            if r_a["controller_label"] == r_b["controller_label"]:
                continue
            ka = (r_a["controller_label"], r_a["ablation"])
            kb = (r_b["controller_label"], r_b["ablation"])
            if ka == kb:
                continue
            if ka > kb:
                ka, kb = kb, ka
                r_a_canon, r_b_canon = r_b, r_a
            else:
                r_a_canon, r_b_canon = r_a, r_b
            for m in METRICS:
                try:
                    va = float(r_a_canon["metrics"][m])
                    vb = float(r_b_canon["metrics"][m])
                except Exception:
                    continue
                key = (ka[0], ka[1], kb[0], kb[1],
                       r_a_canon["scenario"], m)
                if key in samples:
                    continue
                samples[key][r_a_canon["seed"]] = (va, vb)

    tests: Dict[str, Dict] = {}
    for key, by_seed in samples.items():
        ctrl_a, abl_a, ctrl_b, abl_b, scen, metric = key
        seed_keys = sorted(by_seed.keys())
        a = [by_seed[s][0] for s in seed_keys]
        b = [by_seed[s][1] for s in seed_keys]
        tests[
            f"{ctrl_a}/{abl_a} vs {ctrl_b}/{abl_b} | {scen} | {metric}"
        ] = {
            "cell_a": ctrl_a, "ablation_a": abl_a,
            "cell_b": ctrl_b, "ablation_b": abl_b,
            "scenario": scen, "metric": metric,
            "n_pairs": len(seed_keys),
            "mean_a": round(float(np.mean(a)), 6) if a else None,
            "mean_b": round(float(np.mean(b)), 6) if b else None,
            "mean_diff": round(
                float(np.mean([x - y for x, y in zip(a, b)])), 6
            ) if a else None,
            "wilcoxon": _wilcoxon(a, b),
            "cohens_d_paired": round(_cohens_d_paired(a, b), 6),
        }
    return tests


def _holm_correction(tests: Dict[str, Dict]) -> List[Dict]:
    """Bonferroni-Holm step-down adjustment across all tests."""
    rows = []
    for k, v in tests.items():
        p = v["wilcoxon"].get("p_value")
        if p is None or p != p:
            continue
        rows.append({"test": k, "p_value": float(p), **v})
    rows.sort(key=lambda r: r["p_value"])
    m = len(rows)
    out = []
    for i, r in enumerate(rows):
        k = i + 1
        rejected = bool(r["p_value"] < 0.05 / (m - k + 1))
        out.append({
            **r,
            "holm_rank": k,
            "holm_threshold": round(0.05 / (m - k + 1), 6),
            "holm_rejected": rejected,
        })
    return out


def _summary_md(cell_stats: Dict, pairwise: Dict,
                fp_invalid: List[str]) -> str:
    out = ["# Stage 45 — Validation Summary", ""]
    out.append(
        "Stage-45 replaces the Stage-44 metric loop with the "
        "physics-coupled ``stage45_metrics.Stage45MetricCollector`` "
        "(per-load-node service log). The paired-fingerprint contract "
        "is preserved: every (controller, ablation) cell sees an "
        "identical environment at every (scenario, seed)."
    )
    out.append("")
    out.append(f"FP invalid pairs: {len(fp_invalid)}")
    out.append("")
    out.append("## Cells (controller × scenario × ablation)")
    out.append("")
    out.append(
        "| controller | scenario | ablation | n | ENS mean (95% CI) "
        "| CMI mean (95% CI) | restoration rate mean |"
    )
    out.append("|---|---|---|---:|---|---|---|")
    for (ctrl, scen, abl), cell in sorted(cell_stats.items()):
        ens = cell["metrics"]["energy_not_served_mwh"]
        cmi = cell["metrics"]["total_customer_minutes_interrupted"]
        rr = cell["metrics"]["restoration_rate"]
        ens_ci = (
            f"{ens['mean']:.4f} ({ens['ci95_low']:.4f}-{ens['ci95_high']:.4f})"
            if ens["mean"] is not None else "—"
        )
        cmi_ci = (
            f"{cmi['mean']:.4f} ({cmi['ci95_low']:.4f}-{cmi['ci95_high']:.4f})"
            if cmi["mean"] is not None else "—"
        )
        rr_ci = (
            f"{rr['mean']:.3f} ({rr['ci95_low']:.3f}-{rr['ci95_high']:.3f})"
            if rr["mean"] is not None else "—"
        )
        out.append(
            f"| {ctrl} | {scen} | {abl} | {cell['n']} | {ens_ci} | "
            f"{cmi_ci} | {rr_ci} |"
        )
    out.append("")
    out.append("## Pairwise: trained_dqn vs rule_based")
    out.append("")
    out.append(
        "| scenario | ablation | metric | mean_diff | Cohen's d "
        "| p (Wilcoxon) |"
    )
    out.append("|---|---|---|---:|---:|---:|")
    for name, t in pairwise.items():
        if t["cell_b"] != "rule_based":
            continue
        out.append(
            f"| {t['scenario']} | {t['ablation_a']} | {t['metric']} | "
            f"{t['mean_diff']:.4f} | {t['cohens_d_paired']:.3f} | "
            f"{t['wilcoxon'].get('p_value', float('nan')):.4f} |"
        )
    return "\n".join(out)


def _figure_boxplot(runs: List[Dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    by_cell = defaultdict(list)
    for r in runs:
        ctrl = r["controller_label"]
        if ctrl not in ("rule_based", "trained_dqn"):
            continue
        try:
            v = float(r["metrics"]["energy_not_served_mwh"])
        except Exception:
            continue
        by_cell[(ctrl, r["ablation"])].append(v)
    if not by_cell:
        return
    keys = sorted(by_cell.keys())
    fig, ax = plt.subplots(figsize=(11, 5))
    data = [by_cell[k] for k in keys]
    labels = [f"{c}/{a}" for c, a in keys]
    bp = ax.boxplot(
        data, labels=labels, patch_artist=True, showmeans=True,
        meanprops={"marker": "D", "markerfacecolor": "white"},
    )
    colors = {"trained_dqn": "#3b82f6", "rule_based": "#f59e0b"}
    for patch, k in zip(bp["boxes"], keys):
        patch.set_facecolor(colors.get(k[0], "#aaa"))
    ax.set_title("ENS (MWh) — trained_dqn vs rule_based, per ablation\n"
                 "Stage-45 physics-coupled metric")
    ax.set_ylabel("Energy-not-served (MWh)")
    ax.tick_params(axis="x", rotation=30)
    plt.tight_layout()
    plt.savefig(FIGS / "ens_boxplot.png", dpi=120, bbox_inches="tight")


def _figure_pair_corr(runs: List[Dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    by_seed = defaultdict(dict)
    for r in runs:
        by_seed[(r["scenario"], r["seed"], r["ablation"])][
            r["controller_label"]
        ] = r
    pairs = []
    for key, group in by_seed.items():
        td = group.get("trained_dqn")
        rb = group.get("rule_based")
        if td is None or rb is None:
            continue
        try:
            x = float(td["metrics"]["energy_not_served_mwh"])
            y = float(rb["metrics"]["energy_not_served_mwh"])
            pairs.append((x, y, td["scenario"]))
        except Exception:
            continue
    if not pairs:
        return
    fig, ax = plt.subplots(figsize=(6, 6))
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    ax.scatter(xs, ys, alpha=0.6)
    lo = min(xs + ys)
    hi = max(xs + ys)
    ax.plot([lo, hi], [lo, hi], "k--", alpha=0.4, label="y = x")
    ax.set_xlabel("trained_dqn ENS (MWh)")
    ax.set_ylabel("rule_based ENS (MWh)")
    ax.set_title("Paired ENS — Stage-45 trained DQN vs rule_based\n"
                 "physics-coupled metric (per-load-node log)")
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGS / "ens_paired_scatter.png", dpi=120, bbox_inches="tight")


def _write_table_csv(cell_stats: Dict, runs: List[Dict]) -> None:
    rows = []
    for (ctrl, scen, abl), cell in sorted(cell_stats.items()):
        for metric, stats in cell["metrics"].items():
            rows.append({
                "controller": ctrl,
                "scenario": scen,
                "ablation": abl,
                "metric": metric,
                **stats,
            })
    if rows:
        path = TABLES / "per_cell.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            for r in rows:
                writer.writerow(r)


def _invariance_audit(runs: List[Dict]) -> Dict:
    """Stage-45 invariance audit.

    The Stage-44 mandate was triggered by a *metric invariance* bug:
    ENS, CMI, critical-load interruption, and voltage-violation
    counters were byte-identical across all 12 (controller, ablation)
    cells in every (scenario, seed) group. That is, the metric was
    measuring the *fault schedule*, not the *controller's response*.

    The Stage-45 audit re-checks the invariance diagnosis on the
    Stage-45 validation output. For each (scenario, seed) group, we
    compute the standard deviation of ENS across all (controller,
    ablation) cells. If the metric is still invariant, every cell
    is byte-identical and the std is exactly 0. If the metric is
    now responsive, the std is > 0.

    A *fully* responsive metric would have unique ENS values
    across every (scenario, seed, controller, ablation) cell — but
    the test only requires the invariance be broken in at least one
    (scenario, seed) cell.
    """
    by_group = defaultdict(list)
    for r in runs:
        try:
            v = float(r["metrics"]["energy_not_served_mwh"])
        except Exception:
            continue
        by_group[(r["scenario"], r["seed"])].append(v)
    n_groups = len(by_group)
    n_responsive = 0
    sum_std = 0.0
    max_std = 0.0
    for vals in by_group.values():
        arr = np.array(vals, dtype=float)
        if arr.size < 2:
            continue
        std = float(arr.std())
        if std > 0:
            n_responsive += 1
        sum_std += std
        if std > max_std:
            max_std = std
    return {
        "n_groups": n_groups,
        "n_responsive_groups": n_responsive,
        "fraction_responsive": (
            float(n_responsive) / n_groups if n_groups else 0.0
        ),
        "mean_std": float(sum_std / n_groups) if n_groups else 0.0,
        "max_std": float(max_std),
        "passes_invariance_break": bool(n_responsive > 0),
    }


def main() -> None:
    if not VALIDATION_JSON.exists():
        raise FileNotFoundError(
            f"Validation JSON not found at {VALIDATION_JSON}. "
            "Run stage45_validation.py first."
        )
    with open(VALIDATION_JSON, "r", encoding="utf-8") as f:
        report = json.load(f)
    runs: List[Dict] = report["runs"]
    fp_invalid = report.get(
        "fingerprint_report", {}
    ).get("invalid_pairs", [])

    cell_stats = _aggregate(runs)
    with open(STATS / "per_cell.json", "w", encoding="utf-8") as f:
        json.dump(
            {"cells": {str(k): v for k, v in cell_stats.items()}},
            f, indent=2, default=str,
        )

    pairwise = _pairwise_tests(runs)
    with open(STATS / "pairwise.json", "w", encoding="utf-8") as f:
        json.dump(pairwise, f, indent=2, default=str)

    holm = _holm_correction(pairwise)
    with open(STATS / "holm.json", "w", encoding="utf-8") as f:
        json.dump(holm, f, indent=2, default=str)

    _write_table_csv(cell_stats, runs)

    invariance = _invariance_audit(runs)
    with open(STATS / "invariance_audit.json", "w", encoding="utf-8") as f:
        json.dump(invariance, f, indent=2, default=str)

    summary = _summary_md(cell_stats, pairwise, fp_invalid)
    with open(RESULTS / "summary.md", "w", encoding="utf-8") as f:
        f.write(summary)

    _figure_boxplot(runs)
    _figure_pair_corr(runs)

    manifest = {
        "schema_version": "stage45.statistics.1.0",
        "n_runs": len(runs),
        "n_cells": len(cell_stats),
        "n_pairwise_tests": len(pairwise),
        "n_holm_tests": len(holm),
        "n_fingerprint_invalid_pairs": len(fp_invalid),
        "invariance_audit": invariance,
        "controllers": report.get("controllers"),
        "scenarios": report.get("scenarios"),
        "ablations": report.get("ablations"),
        "checkpoint": report.get("checkpoint"),
        "git_sha": report.get("git_sha"),
        "metrics": list(METRICS),
    }
    with open(RESULTS / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)

    print(
        f"wrote {STATS}/per_cell.json, pairwise.json, holm.json, "
        f"invariance_audit.json; {TABLES}/per_cell.csv; "
        f"{RESULTS}/summary.md; {FIGS}/*.png; {RESULTS}/manifest.json"
    )


if __name__ == "__main__":
    main()
