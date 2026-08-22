"""stage46_compare_45_to_46.py — before/after comparison.

Reads ``experiments/results/stage45/validation.json`` and
``experiments/results/stage46/validation.json``, computes the
per-(controller, scenario) means on both, and emits:

  experiments/results/stage46/before_after_stage45.json
  experiments/results/stage46/before_after_stage45.md

The "before" set is the Stage-45 result with the broken
``reroute_energy`` action; the "after" set is the Stage-46
result with the corrected action-layer. The comparison
quantifies the action-layer fix.
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict
from itertools import combinations
from math import erf, sqrt

import numpy as np


THIS = Path(__file__).resolve()
BACKEND = THIS.parent
PROJECT_ROOT = BACKEND.parent
STAGE45 = PROJECT_ROOT / "experiments" / "results" / "stage45" / "validation.json"
STAGE46 = PROJECT_ROOT / "experiments" / "results" / "stage46" / "validation.json"
OUT_DIR = PROJECT_ROOT / "experiments" / "results" / "stage46"


METRICS = (
    "energy_not_served_mwh",
    "total_customer_minutes_interrupted",
    "critical_load_interruption_steps",
    "restoration_rate",
    "avg_restoration_steps",
)


def _bucket_per_seed(runs):
    by = defaultdict(dict)
    for r in runs:
        key = (r["controller_label"], r["ablation"], r["scenario"])
        if not r.get("metrics"):
            continue
        by[key][int(r["seed"])] = r["metrics"]
    return by


def _wilcoxon_signed_rank(a, b):
    if len(a) != len(b) or len(a) < 5:
        return {"n_pairs": len(a), "p_value": float("nan"),
                "method": "wilcoxon_too_few_samples"}
    diffs = [x - y for x, y in zip(a, b)]
    nz = [d for d in diffs if d != 0.0]
    if not nz:
        return {"n_pairs": len(a), "p_value": 1.0,
                "method": "wilcoxon_all_zeros"}
    abs_d = sorted({abs(d) for d in nz})
    ranks = {}
    i = 0
    while i < len(abs_d):
        j = i
        while j < len(abs_d) and abs_d[j] == abs_d[i]:
            j += 1
        r = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[abs_d[k]] = r
        i = j
    W_pos = 0.0
    W_neg = 0.0
    for d in nz:
        r = ranks[abs(d)]
        if d > 0:
            W_pos += r
        else:
            W_neg += r
    W = min(W_pos, W_neg)
    n = len(nz)
    mean_W = n * (n + 1) / 4.0
    sd_W = (n * (n + 1) * (2 * n + 1) / 24.0) ** 0.5
    z = 0.0 if sd_W == 0 else (W - mean_W) / sd_W
    p = 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))
    return {"n_pairs": len(a), "p_value": float(p), "z": float(z),
            "method": "wilcoxon_signed_rank_normal_approx"}


def main():
    if not STAGE46.exists():
        raise SystemExit(f"missing {STAGE46}")
    rep45 = json.loads(STAGE45.read_text())
    rep46 = json.loads(STAGE46.read_text())
    runs45 = _bucket_per_seed(rep45["runs"])
    runs46 = _bucket_per_seed(rep46["runs"])
    cells45 = set(runs45.keys())
    cells46 = set(runs46.keys())
    if cells45 != cells46:
        print(f"NOTE: cell-set differs. only in 45: {cells45 - cells46}, "
              f"only in 46: {cells46 - cells45}")
    out = {"schema_version": "stage46.compare.1.0",
           "stage45_path": str(STAGE45),
           "stage46_path": str(STAGE46),
           "n_cells_common": len(cells45 & cells46),
           "per_cell": {},
           "paired": {}}
    rows_md = [
        "# Stage 46 — Before/After Stage-45 vs Stage-46",
        "",
        "Per-cell means (full_stack only) on the 6 metrics, "
        "paired Wilcoxon signed-rank test (10 seeds).",
        "",
        "## Per-cell means (ENS, MWh)",
        "",
        "| Controller | Scenario | n_45 | mean_45 | n_46 | mean_46 | delta | p (paired) |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for cell in sorted(cells45 & cells46):
        ctrl, abl, scen = cell
        if abl != "full_stack":
            continue
        per_cell = {"cell": cell}
        for side, bucket in (("stage45", runs45), ("stage46", runs46)):
            seeds = sorted(bucket[cell].keys())
            for m in METRICS:
                vals = [float(bucket[cell][s][m]) for s in seeds]
                per_cell[f"{side}_{m}"] = {
                    "n": len(vals),
                    "mean": round(float(np.mean(vals)), 6),
                    "std": round(float(np.std(vals, ddof=1)), 6) if len(vals) > 1 else 0.0,
                }
        out["per_cell"][f"{ctrl}/{abl}/{scen}"] = per_cell
        n45 = per_cell["stage45_energy_not_served_mwh"]["n"]
        m45 = per_cell["stage45_energy_not_served_mwh"]["mean"]
        n46 = per_cell["stage46_energy_not_served_mwh"]["n"]
        m46 = per_cell["stage46_energy_not_served_mwh"]["mean"]
        seeds45 = sorted(runs45[cell].keys())
        seeds46 = sorted(runs46[cell].keys())
        common = sorted(set(seeds45) & set(seeds46))
        if len(common) >= 5:
            a = [float(runs45[cell][s]["energy_not_served_mwh"]) for s in common]
            b = [float(runs46[cell][s]["energy_not_served_mwh"]) for s in common]
            d = float(np.mean(b) - np.mean(a))
            w = _wilcoxon_signed_rank(b, a)  # b=46, a=45; positive diff = improvement
            p = w["p_value"]
            p_str = f"{p:.4f}" if p == p else "—"
        else:
            d = float("nan")
            p_str = "—"
        rows_md.append(
            f"| {ctrl} | {scen} | {n45} | {m45:.4f} | {n46} | "
            f"{m46:.4f} | {d:+.4f} | {p_str} |"
        )
    # Paired cell-vs-cell (e.g. trained_dqn vs rule_based) on each side.
    cells_full = sorted({k for k in cells45 & cells46 if k[1] == "full_stack"})
    for (ca, aa, sa), (cb, ab, sb) in combinations(cells_full, 2):
        if sa != sb:
            continue
        for ctrl_side in ("stage45", "stage46"):
            bucket = runs45 if ctrl_side == "stage45" else runs46
            seeds_a = set(bucket[(ca, aa, sa)].keys())
            seeds_b = set(bucket[(cb, ab, sa)].keys())
            common = sorted(seeds_a & seeds_b)
            if len(common) < 5:
                continue
            for m in METRICS:
                a = [float(bucket[(ca, aa, sa)][s][m]) for s in common]
                b = [float(bucket[(cb, ab, sa)][s][m]) for s in common]
                if np.std([x - y for x, y in zip(a, b)]) == 0:
                    continue
                w = _wilcoxon_signed_rank(a, b)
                key = f"{ca} vs {cb} | {sa} | {m} | {ctrl_side}"
                out["paired"][key] = {
                    "cell_a": ca, "cell_b": cb, "scenario": sa,
                    "metric": m, "side": ctrl_side,
                    "n_pairs": len(common),
                    "mean_a": round(float(np.mean(a)), 6),
                    "mean_b": round(float(np.mean(b)), 6),
                    "mean_diff": round(float(np.mean(a) - np.mean(b)), 6),
                    "wilcoxon": w,
                }
    # Paired before/after (same controller, same seed).
    for cell in sorted(cells45 & cells46):
        ctrl, abl, scen = cell
        if abl != "full_stack":
            continue
        common = sorted(set(runs45[cell].keys()) & set(runs46[cell].keys()))
        if len(common) < 5:
            continue
        for m in METRICS:
            a = [float(runs45[cell][s][m]) for s in common]
            b = [float(runs46[cell][s][m]) for s in common]
            w = _wilcoxon_signed_rank(b, a)  # 46 vs 45; negative diff = improvement
            key = f"{ctrl}/{scen} | {m} | 46 vs 45"
            out["paired"][key] = {
                "cell": ctrl, "scenario": scen, "metric": m,
                "side": "stage46_vs_stage45",
                "n_pairs": len(common),
                "mean_45": round(float(np.mean(a)), 6),
                "mean_46": round(float(np.mean(b)), 6),
                "mean_diff": round(float(np.mean(b) - np.mean(a)), 6),
                "wilcoxon": w,
            }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "before_after_stage45.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    rows_md += ["", "## Paired before/after (Stage-46 vs Stage-45)"]
    rows_md += ["", "| cell | scen | metric | mean_45 | mean_46 | diff | p |"]
    rows_md += ["|---|---|---|---:|---:|---:|---:|"]
    for k, v in sorted(out["paired"].items()):
        if v.get("side") != "stage46_vs_stage45":
            continue
        if v["metric"] != "energy_not_served_mwh":
            continue
        p = v["wilcoxon"]["p_value"]
        p_str = f"{p:.4f}" if p == p else "—"
        rows_md.append(
            f"| {v['cell']} | {v['scenario']} | {v['metric']} | "
            f"{v['mean_45']:.4f} | {v['mean_46']:.4f} | "
            f"{v['mean_diff']:+.4f} | {p_str} |"
        )
    (OUT_DIR / "before_after_stage45.md").write_text(
        "\n".join(rows_md), encoding="utf-8"
    )
    print(f"wrote {OUT_DIR}/before_after_stage45.json + .md")


if __name__ == "__main__":
    main()
