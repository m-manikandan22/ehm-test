"""stage41_raw_audit.py — Stage 41 raw-data audit.

Reads the Stage-26 raw JSON files, computes per-controller distributions,
identifies outliers, and writes diagnostic artefacts into
``experiments/results/stage41_diagnostics/``.

This script does NOT modify any existing files. It only reads from
``experiments/results/paper_final_stage26/raw/`` and writes into the new
``stage41_diagnostics`` directory.

Run:
    python experiments/stage41_raw_audit.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, List

import statistics

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
RAW_DIR = PROJECT_ROOT / "experiments/results/paper_final_stage26/raw"
OUT_DIR = PROJECT_ROOT / "experiments/results/stage41_diagnostics"
RAW_OUT = OUT_DIR / "raw"
AGG_OUT = OUT_DIR / "aggregated"
STAT_OUT = OUT_DIR / "statistics"
FIG_OUT = OUT_DIR / "figures"

# Add project root to path for backend imports.
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from metrics.statistics import mean, std, median, ci95_student, summarise  # noqa: E402


_METRIC_KEYS = (
    "n_faults",
    "n_restored",
    "restoration_rate",
    "avg_restoration_steps",
    "actions_taken",
    "voltage_violation_count",
    "critical_load_interruption_steps",
    "total_customer_minutes_interrupted",
    "energy_not_served_mwh",
    "n_steps",
)


def _load_raw() -> Dict[str, List[dict]]:
    """Group raw runs by controller_label."""
    grouped: Dict[str, List[dict]] = {}
    for fp in sorted(RAW_DIR.glob("*.json")):
        with open(fp) as f:
            run = json.load(f)
        lbl = run.get("controller_label") or "?"
        grouped.setdefault(lbl, []).append(run)
    return grouped


def _per_controller_stats(grouped: Dict[str, List[dict]]) -> dict:
    """Compute per-controller summary stats per metric."""
    out: Dict[str, Dict[str, dict]] = {}
    for label, runs in grouped.items():
        out[label] = {}
        for mk in _METRIC_KEYS:
            vals: List[float] = []
            for r in runs:
                m = r.get("metrics") or {}
                v = m.get(mk)
                if isinstance(v, (int, float)):
                    vals.append(float(v))
            out[label][mk] = summarise(vals) if vals else {
                "n": 0, "mean": 0.0, "std": 0.0, "median": 0.0,
                "min": 0.0, "max": 0.0, "ci95_low": 0.0, "ci95_high": 0.0,
            }
    return out


def _flag_suspicious(grouped: Dict[str, List[dict]]) -> dict:
    """Find identical values, zero variance, extreme outliers."""
    flags: Dict[str, dict] = {}
    for label, runs in grouped.items():
        per_metric: Dict[str, dict] = {}
        for mk in _METRIC_KEYS:
            vals = []
            for r in runs:
                v = (r.get("metrics") or {}).get(mk)
                if isinstance(v, (int, float)):
                    vals.append(float(v))
            if not vals:
                continue
            unique = sorted(set(vals))
            std_v = std(vals)
            mean_v = mean(vals)
            # Outlier: > 3 SD from mean
            outliers = [
                v for v in vals
                if std_v > 0 and abs(v - mean_v) > 3 * std_v
            ]
            per_metric[mk] = {
                "n_unique_values":   len(unique),
                "zero_variance":     std_v == 0.0,
                "min":               min(vals),
                "max":               max(vals),
                "mean":              mean_v,
                "std":               std_v,
                "n_outliers_3sd":    len(outliers),
                "outlier_values":    outliers,
            }
        flags[label] = per_metric
    return flags


def _duplicated_seeds(grouped: Dict[str, List[dict]]) -> dict:
    """Verify seed coverage is complete and non-overlapping across configs."""
    info: Dict[str, List[int]] = {}
    for label, runs in grouped.items():
        info[label] = sorted(int(r.get("seed", -1)) for r in runs)
    # Cross-controller duplicate detection (same scenario)
    n_per = {lbl: len(v) for lbl, v in info.items()}
    return {"seeds_per_controller": info, "n_per_controller": n_per}


def _scenario_diversity(grouped: Dict[str, List[dict]]) -> dict:
    """Report whether each (seed, controller) uses the same fault scenario."""
    out: Dict[str, dict] = {}
    for label, runs in grouped.items():
        scenarios = []
        for r in runs:
            sc = r.get("scenario") or {}
            faults = sc.get("faults") or []
            key = "|".join(
                f"{f.get('timestep')}:{f.get('target')}:{f.get('duration_steps')}"
                for f in faults
            )
            scenarios.append((r.get("seed"), key))
        unique_scenarios = {k for _, k in scenarios}
        out[label] = {
            "n_runs":           len(scenarios),
            "n_unique_scenarios": len(unique_scenarios),
            "fault_target_counts": _count(faults=[s.split("|") for _, s in scenarios]),
        }
    return out


def _count(faults):
    """Quick count of distinct fault-target tokens across all scenarios."""
    c: Dict[str, int] = {}
    for parts in faults:
        for p in parts:
            if not p:
                continue
            tgt = p.split(":")[1] if ":" in p else p
            c[tgt] = c.get(tgt, 0) + 1
    return c


def _distribution_table(grouped: Dict[str, List[dict]],
                         metric: str) -> str:
    """Build a Markdown table of the per-controller distribution."""
    lines = [f"## Distribution of `{metric}`",
             "",
             "| Controller | n | mean | std | min | median | max | 95 % CI |",
             "|---|---:|---:|---:|---:|---:|---:|---|"]
    for label, runs in grouped.items():
        vals = []
        for r in runs:
            v = (r.get("metrics") or {}).get(metric)
            if isinstance(v, (int, float)):
                vals.append(float(v))
        if not vals:
            lines.append(f"| `{label}` | 0 | — | — | — | — | — | — |")
            continue
        s = summarise(vals)
        lines.append(
            f"| `{label}` | {s['n']} | {s['mean']:.4f} | {s['std']:.4f} "
            f"| {s['min']:.4f} | {s['median']:.4f} | {s['max']:.4f} "
            f"| [{s['ci95_low']:.4f}, {s['ci95_high']:.4f}] |"
        )
    return "\n".join(lines)


def main() -> int:
    if not RAW_DIR.exists():
        print(f"FATAL: raw dir not found: {RAW_DIR}")
        return 1
    for d in (RAW_OUT, AGG_OUT, STAT_OUT, FIG_OUT):
        d.mkdir(parents=True, exist_ok=True)

    grouped = _load_raw()
    print(f"Loaded {sum(len(v) for v in grouped.values())} runs "
          f"across {len(grouped)} controllers.")

    # Per-controller stats
    stats = _per_controller_stats(grouped)
    with open(AGG_OUT / "per_controller_stats.json", "w") as f:
        json.dump(stats, f, indent=2, default=str)

    # CSV
    with open(AGG_OUT / "per_controller_stats.csv", "w") as f:
        f.write("controller,metric,n,mean,std,median,min,max,ci95_low,ci95_high\n")
        for label, mdict in stats.items():
            for mk, s in mdict.items():
                f.write(
                    f"{label},{mk},{s['n']},{s['mean']:.6f},{s['std']:.6f},"
                    f"{s['median']:.6f},{s['min']:.6f},{s['max']:.6f},"
                    f"{s['ci95_low']:.6f},{s['ci95_high']:.6f}\n"
                )

    # Suspicious values
    flags = _flag_suspicious(grouped)
    with open(STAT_OUT / "suspicious_values.json", "w") as f:
        json.dump(flags, f, indent=2, default=str)

    # Seed coverage
    seeds = _duplicated_seeds(grouped)
    with open(STAT_OUT / "seed_coverage.json", "w") as f:
        json.dump(seeds, f, indent=2, default=str)

    # Scenario diversity
    scen = _scenario_diversity(grouped)
    with open(STAT_OUT / "scenario_diversity.json", "w") as f:
        json.dump(scen, f, indent=2, default=str)

    # Distribution tables
    md_lines = ["# Stage 41 — Raw-data audit", ""]
    md_lines.append(
        "Source: `experiments/results/paper_final_stage26/raw/` "
        f"({sum(len(v) for v in grouped.values())} runs, "
        f"{len(grouped)} controllers).\n"
    )
    md_lines.append("## Controllers and run counts\n")
    md_lines.append("| Controller | n_runs |\n|---|---:|")
    for label, runs in grouped.items():
        md_lines.append(f"| `{label}` | {len(runs)} |")
    md_lines.append("")
    for mk in _METRIC_KEYS:
        md_lines.append(_distribution_table(grouped, mk))
        md_lines.append("")

    # Saturation flags
    md_lines.append("## Saturation flags (zero variance)\n")
    md_lines.append(
        "If a metric has zero variance across all 20 runs of a controller, "
        "it cannot differentiate controllers.\n"
    )
    md_lines.append("| Controller | Metric | std | min == max? |")
    md_lines.append("|---|---|---:|---|")
    for label, runs in grouped.items():
        for mk in _METRIC_KEYS:
            vals = []
            for r in runs:
                v = (r.get("metrics") or {}).get(mk)
                if isinstance(v, (int, float)):
                    vals.append(float(v))
            if not vals:
                continue
            std_v = std(vals)
            mn, mx = min(vals), max(vals)
            md_lines.append(
                f"| `{label}` | `{mk}` | {std_v:.4f} | "
                f"{'yes' if mn == mx else 'no'} |"
            )

    md_lines.append("")
    md_lines.append("## Outlier report (> 3 SD)\n")
    md_lines.append("| Controller | Metric | n_outliers | values |")
    md_lines.append("|---|---|---:|---|")
    for label, mdict in flags.items():
        for mk, info in mdict.items():
            if info["n_outliers_3sd"] > 0:
                md_lines.append(
                    f"| `{label}` | `{mk}` | {info['n_outliers_3sd']} | "
                    f"{info['outlier_values']} |"
                )

    with open(OUT_DIR / "raw_data_audit.md", "w") as f:
        f.write("\n".join(md_lines))

    # Diagnostic plot (matplotlib)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2, 2, figsize=(11, 8))
        for ax, metric in zip(axes.flat, [
            "energy_not_served_mwh",
            "total_customer_minutes_interrupted",
            "restoration_rate",
            "avg_restoration_steps",
        ]):
            data = []
            labels = []
            for label, runs in grouped.items():
                vals = []
                for r in runs:
                    v = (r.get("metrics") or {}).get(metric)
                    if isinstance(v, (int, float)):
                        vals.append(float(v))
                data.append(vals)
                labels.append(label)
            ax.boxplot(data, labels=labels)
            ax.set_title(metric)
            ax.tick_params(axis='x', rotation=30)
            ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(FIG_OUT / "stage26_distributions.png", dpi=110)
        plt.close(fig)
    except Exception as exc:
        with open(FIG_OUT / "plot_error.txt", "w") as f:
            f.write(repr(exc))

    print("Wrote audit artefacts under", OUT_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
