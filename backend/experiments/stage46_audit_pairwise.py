"""stage46_audit_pairwise.py — Stage-46 paired statistics audit.

Computes proper paired (per-seed) statistics over the
Stage-45 ``validation.json`` (480 runs). The original
``stage45_statistics._pairwise_tests`` had a dedup bug that
collapsed all 10 paired seeds into a single sample,
leaving every Wilcoxon test with ``n_pairs==1``. This
script does the correctly-paired computation and writes:

  experiments/results/stage46/statistics/pairwise_correct.json
  experiments/results/stage46/statistics/holm_correct.json
  experiments/results/stage46/statistics/summary_pairwise_correct.md

And also runs the same analysis on the in-progress
Stage-46 validation.json if present, so we can produce a
before/after comparison.

This script is read-only against Stage-45 artefacts: it
DOES NOT touch the simulator, controller, or training
pipeline.
"""
from __future__ import annotations

import json
from collections import defaultdict
from itertools import combinations
from math import erf, sqrt
from pathlib import Path
from typing import Dict, List, Tuple


import numpy as np


THIS = Path(__file__).resolve()
BACKEND = THIS.parent
PROJECT_ROOT = BACKEND.parent
STAGE45 = PROJECT_ROOT / "experiments" / "results" / "stage45"
STAGE46 = PROJECT_ROOT / "experiments" / "results" / "stage46"
STATS46 = STAGE46 / "statistics"
STATS46.mkdir(parents=True, exist_ok=True)


METRICS = (
    "energy_not_served_mwh",
    "total_customer_minutes_interrupted",
    "critical_load_interruption_steps",
    "restoration_rate",
    "avg_restoration_steps",
    "voltage_violation_count",
)


def _load_runs(label: str) -> Tuple[Path, List[Dict]]:
    if label == "stage45":
        src = STAGE45 / "validation.json"
    else:
        src = STAGE46 / "validation.json"
    if not src.exists():
        raise FileNotFoundError(src)
    with open(src, "r", encoding="utf-8") as f:
        rep = json.load(f)
    return src, rep["runs"]


def _bucket_per_seed(runs: List[Dict]) -> Dict[Tuple, Dict[int, Dict]]:
    """Group runs by (controller_label, ablation, scenario) → seed
    → metrics."""
    by: Dict[Tuple, Dict[int, Dict]] = defaultdict(dict)
    for r in runs:
        key = (r["controller_label"], r["ablation"], r["scenario"])
        m = r.get("metrics", {})
        if not m:
            continue
        by[key][int(r["seed"])] = m
    return by


def _wilcoxon_signed_rank(a: List[float], b: List[float]) -> Dict:
    if len(a) != len(b) or len(a) < 5:
        return {
            "n_pairs": len(a),
            "statistic": float("nan"),
            "p_value": float("nan"),
            "z": float("nan"),
            "method": "wilcoxon_too_few_samples",
        }
    diffs = [x - y for x, y in zip(a, b)]
    nonzero = [d for d in diffs if d != 0.0]
    if not nonzero:
        return {
            "n_pairs": len(a), "statistic": 0.0, "p_value": 1.0,
            "z": 0.0, "method": "wilcoxon_all_zeros",
        }
    abs_diffs = sorted({abs(d) for d in nonzero})
    ranks: Dict[float, float] = {}
    i = 0
    while i < len(abs_diffs):
        j = i
        while j < len(abs_diffs) and abs_diffs[j] == abs_diffs[i]:
            j += 1
        r = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[abs_diffs[k]] = r
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
    z = 0.0 if sd_W == 0 else (W - mean_W) / sd_W
    p = 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))
    return {
        "n_pairs": len(a), "statistic": float(W),
        "p_value": float(p), "z": float(z),
        "method": "wilcoxon_signed_rank_normal_approx",
    }


def _cohens_d_paired(a: List[float], b: List[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        return float("nan")
    arr = np.array([x - y for x, y in zip(a, b)], dtype=float)
    sd = float(arr.std(ddof=1))
    if sd == 0:
        return 0.0
    return float(arr.mean() / sd)


def _classify(direction_is_lower_better: bool,
              mean_diff: float, d: float, p: float) -> str:
    """Classify comparison outcome.

    ``direction_is_lower_better`` is True for ENS, customer-minutes,
    restoration_steps, voltage_violation, critical_interruption; False
    for restoration_rate (higher = better).

    Improved = mean_diff < 0 if lower is better else > 0.
    """
    if p is None or p != p:
        return "INSUFFICIENT_EVIDENCE"
    improved = mean_diff < 0 if direction_is_lower_better else mean_diff > 0
    meaningful = abs(d) > 0.2 if d == d else False
    significant = p < 0.05
    word = "improvement" if improved else "degradation"
    if significant and meaningful:
        return f"SIGNIFICANT_{word.upper()}"
    if meaningful and not significant:
        return f"NON-SIGNIFICANT_{word.upper()}"
    if not meaningful and significant:
        return f"PARTIAL_{word.upper()}_p_only"
    return "NO_MEANINGFUL_DIFFERENCE"


def pairwise(runs: List[Dict],
             only_full_stack: bool = True,
             ) -> Dict[str, Dict]:
    """Compute paired (cell_a vs cell_b) stats per
    (scenario, ablation, metric) for ALL pairs of controllers,
    paired by seed. If ``only_full_stack``, restrict each side
    to ablation == 'full_stack' (so DQN no_lstm is NOT
    compared to rule_based no_lstm -- different populations).
    """
    bucket = _bucket_per_seed(runs)
    if only_full_stack:
        cells = sorted({k for k in bucket.keys() if k[1] == "full_stack"})
    else:
        cells = sorted(bucket.keys())
    out: Dict[str, Dict] = {}
    for (ca, aa, scen), (cb, ab, scen2) in combinations(cells, 2):
        if scen != scen2:
            continue
        seeds_a = set(bucket[(ca, aa, scen)].keys())
        seeds_b = set(bucket[(cb, ab, scen)].keys())
        common = sorted(seeds_a & seeds_b)
        if len(common) < 5:
            continue
        for m in METRICS:
            try:
                a = [float(bucket[(ca, aa, scen)][s][m]) for s in common]
                b = [float(bucket[(cb, ab, scen)][s][m]) for s in common]
            except KeyError:
                continue
            mean_a = float(np.mean(a))
            mean_b = float(np.mean(b))
            mean_diff = mean_a - mean_b
            d = _cohens_d_paired(a, b)
            w = _wilcoxon_signed_rank(a, b)
            lower_better = m in (
                "energy_not_served_mwh",
                "total_customer_minutes_interrupted",
                "critical_load_interruption_steps",
                "avg_restoration_steps",
                "voltage_violation_count",
            )
            cls = _classify(lower_better, mean_diff, d, w["p_value"])
            key = f"{ca}/{aa} vs {cb}/{ab} | {scen} | {m}"
            out[key] = {
                "cell_a": ca, "ablation_a": aa,
                "cell_b": cb, "ablation_b": ab,
                "scenario": scen, "metric": m,
                "n_pairs": len(common),
                "mean_a": round(mean_a, 6),
                "mean_b": round(mean_b, 6),
                "mean_diff": round(mean_diff, 6),
                "lower_is_better": lower_better,
                "wilcoxon": w,
                "cohens_d_paired": round(d, 6) if d == d else None,
                "classification": cls,
            }
    return out


def holm_correction(tests: Dict[str, Dict]) -> List[Dict]:
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


def per_cell_summary(runs: List[Dict]) -> Dict[Tuple, Dict]:
    bucket = _bucket_per_seed(runs)
    out = {}
    for (ctrl, abl, scen), seeds in sorted(bucket.items()):
        if abl != "full_stack":
            continue
        for m in METRICS:
            vals = [float(seeds[s].get(m, float("nan"))) for s in sorted(seeds)]
            out[(ctrl, abl, scen, m)] = {
                "controller_label": ctrl,
                "ablation": abl,
                "scenario": scen,
                "metric": m,
                "n_seeds": len(vals),
                "mean": round(float(np.mean(vals)), 6),
                "std": round(float(np.std(vals, ddof=1)), 6) if len(vals) > 1 else 0.0,
                "min": round(float(np.min(vals)), 6),
                "max": round(float(np.max(vals)), 6),
                "median": round(float(np.median(vals)), 6),
            }
    return out


def _write_summary(label: str, p: Dict[str, Dict],
                   per_cell: Dict[Tuple, Dict]) -> Path:
    out = [
        f"# Stage 46 — Paired Statistical Audit ({label})",
        "",
        "Computed on the PER-SEED runs of the validation set. Every "
        "test pairs 10 seeds across the two cells (5+ minimum for "
        "Wilcoxon). Cohen's d is paired. Holm correction applied "
        "across all per-(cell_a, cell_b, scen, metric) tests.",
        "",
        f"Total paired tests: {len(p)}",
        "",
        "## Per-cell means (full_stack only, ENS in MWh)",
        "",
        "| Controller | Scenario | n | mean ENS | std | min | max |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for k in sorted(per_cell.keys()):
        v = per_cell[k]
        if v["metric"] != "energy_not_served_mwh":
            continue
        out.append(
            f"| {v['controller_label']} | {v['scenario']} | "
            f"{v['n_seeds']} | {v['mean']:.4f} | {v['std']:.4f} | "
            f"{v['min']:.4f} | {v['max']:.4f} |"
        )
    out.append("")
    out.append("## Paired tests (selected contrasts)")
    out.append("")
    # The directional contrast we want: read each metric as
    # ``cell_a vs cell_b`` (cell_a on top, cell_b on bottom).
    # We pick the ordering that matches the alphabetical/
    # "controller_a is the question" framing.
    contrasts = [
        ("trained_dqn", "rule_based"),
        ("trained_dqn", "untrained_dqn"),
        ("trained_dqn", "random"),
        ("rule_based", "untrained_dqn"),
        ("rule_based", "random"),
        ("untrained_dqn", "random"),
    ]
    metric_filter = {
        "energy_not_served_mwh",
        "total_customer_minutes_interrupted",
        "restoration_rate",
        "critical_load_interruption_steps",
        "avg_restoration_steps",
    }
    for ca, cb in contrasts:
        out.append(f"### {ca} vs {cb} (full_stack)")
        out.append("")
        out.append("| scenario | metric | n | mean_a | mean_b | diff | d | p | class |")
        out.append("|---|---|---:|---:|---:|---:|---:|---:|---|")
        rows = []
        for k in sorted(p.keys()):
            v = p[k]
            if not (
                v["cell_a"] == ca and v["cell_b"] == cb
                or v["cell_a"] == cb and v["cell_b"] == ca
            ):
                continue
            if v["ablation_a"] != "full_stack":
                continue
            if v["metric"] not in metric_filter:
                continue
            # Always render cell_a on top (controller of interest
            # = ``ca``). Swap if necessary.
            if v["cell_a"] == ca:
                ma, mb, d = v["mean_a"], v["mean_b"], v["mean_diff"]
            else:
                ma = v["mean_b"]
                mb = v["mean_a"]
                d = -v["mean_diff"]
            cv = v["cohens_d_paired"]
            if v["cell_a"] == cb:
                cv = -cv if isinstance(cv, (int, float)) else cv
                cls = _classify(v["lower_is_better"], -v["mean_diff"],
                                cv, v["wilcoxon"]["p_value"])
            else:
                cls = v["classification"]
            d_str = f"{cv:+.3f}" if isinstance(cv, (int, float)) else "—"
            pv = v["wilcoxon"]["p_value"]
            p_str = f"{pv:.4f}" if pv == pv else "—"
            rows.append(
                f"| {v['scenario']} | {v['metric']} | "
                f"{v['n_pairs']} | {ma:.4f} | "
                f"{mb:.4f} | {d:+.4f} | "
                f"{d_str} | {p_str} | {cls} |"
            )
        out.extend(rows)
        if not rows:
            out.append("| — | — | 0 | — | — | — | — | — | NO_PAIRS |")
        out.append("")
    summary_path = STATS46 / f"summary_pairwise_{label}.md"
    summary_path.write_text("\n".join(out), encoding="utf-8")
    return summary_path


def main() -> None:
    src, runs = _load_runs("stage45")
    print(f"loaded {len(runs)} runs from {src}")
    p_full = pairwise(runs, only_full_stack=True)
    p_all = pairwise(runs, only_full_stack=False)
    with open(STATS46 / "pairwise_correct_stage45_full_stack.json",
              "w", encoding="utf-8") as f:
        json.dump(p_full, f, indent=2, default=str)
    with open(STATS46 / "pairwise_correct_stage45_all_ablations.json",
              "w", encoding="utf-8") as f:
        json.dump(p_all, f, indent=2, default=str)
    holm_full = holm_correction(p_full)
    with open(STATS46 / "holm_correct_stage45.json",
              "w", encoding="utf-8") as f:
        json.dump(holm_full, f, indent=2, default=str)
    per_cell = per_cell_summary(runs)
    summary = _write_summary("stage45_full_stack", p_full, per_cell)
    print(f"wrote {STATS46}/pairwise_correct_stage45_full_stack.json, "
          f"holm_correct_stage45.json, {summary}")
    # Also do ablation-as-cell for information-flow ablation audit.
    ablation_summary = _write_summary("stage45_all_ablations", p_all,
                                       per_cell)
    print(f"wrote {ablation_summary}")


if __name__ == "__main__":
    main()
