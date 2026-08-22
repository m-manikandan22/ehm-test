"""stage46_statistics.py — Stage-46 paired statistical audit.

Re-computes the Stage-45 paired statistical tests correctly
(the existing ``stage45_statistics._pairwise_tests`` had a
dedup bug that collapsed all 10 paired seeds into a single
sample, leaving all Wilcoxon tests with ``n_pairs == 1`` and
the test rejected as ``too_few_samples``).

This module reads the full validation.json and emits a
correctly-paired comparison for every (cell_a, cell_b,
scenario, ablation, metric) combination, with all 10 seed
pairs per (scenario, ablation).

Outputs:
  experiments/results/stage46/statistics/paired_by_metric.json
  experiments/results/stage46/statistics/holm.json
  experiments/results/stage46/statistics/summary.md
"""
from __future__ import annotations

import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parents[1]
RESULTS = PROJECT_ROOT / "experiments" / "results" / "stage46"
STATS = RESULTS / "statistics"
TABLES = RESULTS / "tables"
FIGS = RESULTS / "figures"
for d in (STATS, TABLES, FIGS):
    d.mkdir(parents=True, exist_ok=True)


METRICS = (
    "energy_not_served_mwh",
    "total_customer_minutes_interrupted",
    "restoration_rate",
    "avg_restoration_steps",
    "critical_load_interruption_steps",
    "voltage_violation_count",
)


def _config_keys(run: dict) -> Tuple:
    """Identify the (controller, ablation) cell of a run."""
    return (run["controller_label"], run["ablation"])


def _bootstrap_ci(samples: List[float], n: int = 10_000,
                  alpha: float = 0.05):
    if not samples or len(samples) < 2:
        m = float(np.mean(samples)) if samples else float("nan")
        return m, m, m
    arr = np.array(samples, dtype=float)
    rng = np.random.default_rng(0)
    means = np.empty(n, dtype=float)
    for i in range(n):
        idx = rng.integers(0, len(arr), size=len(arr))
        means[i] = arr[idx].mean()
    return (
        float(arr.mean()),
        float(np.quantile(means, alpha / 2)),
        float(np.quantile(means, 1 - alpha / 2)),
    )


def _wilcoxon_signed_rank(a, b):
    """Wilcoxon signed-rank (paired, two-sided)."""
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
            "n_pairs": len(a),
            "statistic": 0.0,
            "p_value": 1.0,
            "z": 0.0,
            "method": "wilcoxon_all_zeros",
        }
    abs_diffs = sorted({abs(d) for d in nonzero})
    ranks = {}
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
    from math import erf, sqrt
    p = 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))
    return {
        "n_pairs": len(a),
        "statistic": float(W),
        "p_value": float(p),
        "z": float(z),
        "method": "wilcoxon_signed_rank_normal_approx",
    }


def _cohens_d_paired(a, b):
    if len(a) != len(b) or len(a) < 2:
        return float("nan")
    diffs = np.array([x - y for x, y in zip(a, b)], dtype=float)
    sd = float(diffs.std(ddof=1))
    if sd == 0:
        return 0.0
    return float(diffs.mean() / sd)


def _classify(mean_diff: float, d: float, p: float) -> str:
    """Classify a paired comparison into one of:
    SIGNIFICANT IMPROVEMENT, NON-SIGNIFICANT IMPROVEMENT,
    NO MEANINGFUL DIFFERENCE, NON-SIGNIFICANT DEGRADATION,
    SIGNIFICANT DEGRADATION.
    """
    if p is None or p != p:
        return "INSUFFICIENT_EVIDENCE"
    direction = "improvement" if mean_diff < 0 else "degradation" if mean_diff > 0 else "neutral"
    meaningful = abs(d) > 0.2 if d == d else False
    significant = p < 0.05
    if significant and meaningful:
        return f"SIGNIFICANT_{direction.upper()}"
    if meaningful and not significant:
        return f"NON-SIGNIFICANT_{direction.upper()}"
    if not meaningful and significant:
        return f"PARTIAL_{direction.upper()}_p_only"
    return "NO_MEANINGFUL_DIFFERENCE"


def paired_by_metric_correct(runs: List[Dict]) -> Dict:
    """For every (cell_a, cell_b, scenario, ablation) pair, compute
    paired (10-seed) stats on the 6 metrics. Every (controller,
    ablation) cell is treated as a separate population. We
    NO LONGER canonicalise so the canonicalised key includes
    the seed — instead, we accumulate per-seed means and
    compute the paired test on the per-seed values."""
    by_key = defaultdict(lambda: defaultdict(dict))
    for r in runs:
        try:
            v = float(r["metrics"]["energy_not_served_mwh"])
        except Exception:
            continue
        key = (
            r["controller_label"],
            r["ablation"],
            r["scenario"],
        )
        by_key[key][r["seed"]] = r["metrics"]
    out: Dict[str, Dict] = {}
    cells = list(by_key.keys())
    for (ca, aa, scen), (cb, ab, _) in combinations(cells, 2):
        if (ca, aa) == (cb, ab):
            continue
        # Cross-scenario comparison? Skip.
        # We DO allow cross-ablation (e.g., DQN full_stack vs
        # rule_based full_stack).
        for scen_local in {scen}:
            seeds_a = set(by_key[(ca, aa, scen_local)].keys())
            seeds_b = set(by_key[(cb, ab, scen_local)].keys())
            common = sorted(seeds_a & seeds_b)
            if len(common) < 5:
                continue
            for m in METRICS:
                a = [float(by_key[(ca, aa, scen_local)][s][m]) for s in common]
                b = [float(by_key[(cb, ab, scen_local)][s][m]) for s in common]
                mean_diff = float(np.mean(a) - np.mean(b))
                d = _cohens_d_paired(a, b)
                w = _wilcoxon_signed_rank(a, b)
                cls = _classify(mean_diff, d, w["p_value"])
                key = (
                    ca, aa, cb, ab, scen_local, m
                )
                out[f"{ca}/{aa} vs {cb}/{ab} | {scen_local} | {m}"] = {
                    "cell_a": ca, "ablation_a": aa,
                    "cell_b": cb, "ablation_b": ab,
                    "scenario": scen_local,
                    "metric": m,
                    "n_pairs": len(common),
                    "mean_a": round(float(np.mean(a)), 6),
                    "mean_b": round(float(np.mean(b)), 6),
                    "mean_diff": round(mean_diff, 6),
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


def main() -> None:
    src = PROJECT_ROOT / "experiments" / "results" / "stage46" / "validation.json"
    if not src.exists():
        raise FileNotFoundError(src)
    with open(src, "r", encoding="utf-8") as f:
        report = json.load(f)
    runs = report["runs"]
    paired = paired_by_metric_correct(runs)
    with open(STATS / "paired_by_metric.json", "w", encoding="utf-8") as f:
        json.dump(paired, f, indent=2, default=str)
    holm = holm_correction(paired)
    with open(STATS / "holm.json", "w", encoding="utf-8") as f:
        json.dump(holm, f, indent=2, default=str)
    # Summary markdown.
    out = ["# Stage 46 — Paired Statistical Audit", ""]
    out.append(f"Total paired tests: {len(paired)}")
    out.append(f"Holm-adjusted tests: {len(holm)}")
    out.append("")
    out.append("## Selected paired comparisons")
    out.append("")
    for cb, ca in [
        ("rule_based", "trained_dqn"),
        ("untrained_dqn", "trained_dqn"),
        ("random", "trained_dqn"),
        ("random", "rule_based"),
    ]:
        out.append(f"### {ca} vs {cb}")
        out.append("")
        out.append("| scenario | metric | n | mean_a | mean_b | mean_diff | d | p | Holm rank | classification |")
        out.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
        for k, v in sorted(paired.items()):
            if v["cell_a"] != ca or v["cell_b"] != cb:
                continue
            if v["ablation_a"] != "full_stack":
                continue
 # show full_stack vs full_stack
            holm_rank = ""
            for h in holm:
                if h["test"] == k:
                    holm_rank = f"{h['holm_rank']}/{len(holm)}"
                    break
            d = v["cohens_d_paired"]
            d_str = f"{d:.3f}" if isinstance(d, (int, float)) else "—"
            p = v["wilcoxon"]["p_value"]
            p_str = f"{p:.4f}" if p == p else "—"
            out.append(
                f"| {v['scenario']} | {v['metric']} | {v['n_pairs']} | "
                f"{v['mean_a']:.4f} | {v['mean_b']:.4f} | "
                f"{v['mean_diff']:.4f} | {d_str} | {p_str} | "
                f"{holm_rank} | {v['classification']} |"
            )
        out.append("")
    summary = "\n".join(out)
    with open(RESULTS / "statistical_audit.md", "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"wrote {STATS}/paired_by_metric.json, holm.json; "
          f"{RESULTS}/statistical_audit.md")


if __name__ == "__main__":
    main()
