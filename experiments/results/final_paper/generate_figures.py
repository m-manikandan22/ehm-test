"""generate_figures.py — Phase 21: Generate paper figures.

Reads:
  - experiments/results/final_paper/raw/paper/baseline_results.json
  - experiments/results/final_paper/raw/paper/ablation_results.json

Writes PNG and PDF figures to:
  - experiments/results/final_paper/figures/

Figures produced:
  1. SAIFI by controller (box plot)
  2. SAIDI by controller (box plot)
  3. ENS by controller (box plot)
  4. Restoration time by controller (box plot)
  5. Critical-load restored % by controller (box plot)
  6. Voltage violation count by controller (box plot)
  7. Ablation impact on SAIDI (bar + CI)
  8. Runtime by controller (bar)
  9. Validity summary (bar)
"""
from __future__ import annotations

import json
import os
import sys
from typing import Dict, List

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(THIS_DIR)))
for p in (os.path.join(PROJECT_ROOT, "backend"), PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

RAW_DIR = os.path.join("experiments", "results", "final_paper", "raw", "paper")
FIG_DIR = os.path.join("experiments", "results", "final_paper", "figures")
os.makedirs(FIG_DIR, exist_ok=True)


def _load_runs(path: str) -> List[Dict[str, object]]:
    with open(path) as f:
        rep = json.load(f)
    return rep.get("runs", [])


def _collect_by_label(runs: List[Dict[str, object]], metric: str
                      ) -> Dict[str, List[float]]:
    out: Dict[str, List[float]] = {}
    for r in runs:
        if not r.get("validity", {}).get("valid"):
            continue
        lbl = r.get("controller_label") or "<unknown>"
        v = (r.get("metrics") or {}).get(metric)
        if isinstance(v, (int, float)):
            out.setdefault(lbl, []).append(float(v))
    return out


def _box_plot(by_label: Dict[str, List[float]], title: str,
              ylabel: str, out_path: str, log: bool = False):
    labels = sorted(by_label.keys())
    data   = [by_label[l] for l in labels]
    fig, ax = plt.subplots(figsize=(9, 5))
    if log:
        # Replace zeros/negatives with 1e-3 for log display
        data = [[max(v, 1e-3) for v in d] for d in data]
        ax.set_yscale("log")
    bp = ax.boxplot(data, patch_artist=True)
    for patch in bp["boxes"]:
        patch.set_facecolor("#90c8e8")
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    fig.savefig(out_path.replace(".png", ".pdf"))
    plt.close(fig)


def _bar_with_ci(by_label: Dict[str, List[float]], title: str,
                 ylabel: str, out_path: str):
    labels = sorted(by_label.keys())
    means, ci_lows, ci_highs = [], [], []
    for lbl in labels:
        v = by_label[lbl]
        if not v:
            means.append(0); ci_lows.append(0); ci_highs.append(0)
            continue
        m = float(np.mean(v))
        s = float(np.std(v, ddof=1)) if len(v) > 1 else 0.0
        h = 1.96 * s / np.sqrt(len(v)) if len(v) > 1 else 0.0
        means.append(m); ci_lows.append(m - h); ci_highs.append(m + h)
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(labels))
    ax.bar(x, means, color="#90c8e8", edgecolor="#345")
    ax.errorbar(x, means,
                yerr=[np.array(means) - np.array(ci_lows),
                      np.array(ci_highs) - np.array(means)],
                fmt="none", color="#345", capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    fig.savefig(out_path.replace(".png", ".pdf"))
    plt.close(fig)


def main() -> int:
    base_runs = _load_runs(os.path.join(RAW_DIR, "baseline_results.json"))
    abl_runs  = _load_runs(os.path.join(RAW_DIR, "ablation_results.json"))
    all_runs  = base_runs + abl_runs

    # 1. Reliability by controller (box plots)
    metrics_to_plot = [
        ("saifi", "SAIFI by controller", "SAIFI (faults/node)"),
        ("saidi", "SAIDI by controller", "SAIDI (steps)"),
        ("ens", "ENS by controller", "ENS (step·count)"),
        ("restoration_time_seconds", "Restoration time by controller",
         "Restoration time (s)"),
        ("critical_load_restored_pct", "Critical-load restored by controller",
         "Critical-load restored (%)"),
        ("voltage_violation_count", "Voltage violation count by controller",
         "Voltage violations"),
        ("number_of_islands", "Number of islands by controller", "Islands"),
        ("actions_taken", "Actions taken by controller", "Actions"),
        ("runtime_s", "Runtime by controller", "Runtime (s)"),
    ]
    for metric, title, ylabel in metrics_to_plot:
        by_label = _collect_by_label(all_runs, metric)
        if not by_label:
            continue
        out = os.path.join(FIG_DIR, f"{metric}_by_controller.png")
        _box_plot(by_label, title, ylabel, out)

    # 2. Ablation impact on SAIDI (bar with CI)
    abl_by_label = _collect_by_label(abl_runs, "saidi")
    out = os.path.join(FIG_DIR, "ablation_saidi_bar.png")
    _bar_with_ci(abl_by_label, "Ablation impact on SAIDI",
                 "SAIDI (steps)", out)

    # 3. Ablation impact on ENS
    abl_ens = _collect_by_label(abl_runs, "ens")
    out = os.path.join(FIG_DIR, "ablation_ens_bar.png")
    _bar_with_ci(abl_ens, "Ablation impact on ENS", "ENS", out)

    # 4. Runtime comparison bar
    base_rt = _collect_by_label(base_runs, "runtime_s")
    out = os.path.join(FIG_DIR, "baseline_runtime_bar.png")
    _bar_with_ci(base_rt, "Runtime by baseline controller",
                 "Runtime (s)", out)

    # 5. Validity summary
    labels = sorted(set(r.get("controller_label") for r in all_runs))
    n_total = {l: 0 for l in labels}
    n_valid = {l: 0 for l in labels}
    for r in all_runs:
        lbl = r.get("controller_label")
        if lbl is None: continue
        n_total[lbl] += 1
        if r.get("validity", {}).get("valid"):
            n_valid[lbl] += 1
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(labels))
    invalid = [n_total[l] - n_valid[l] for l in labels]
    valid   = [n_valid[l] for l in labels]
    ax.bar(x, valid,   color="#2ca02c", label="valid")
    ax.bar(x, invalid, bottom=valid, color="#d62728", label="invalid")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_title("Run validity by controller")
    ax.set_ylabel("Number of runs")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "validity_summary.png")
    fig.savefig(out, dpi=150)
    fig.savefig(out.replace(".png", ".pdf"))
    plt.close(fig)

    print(f"Wrote figures to {FIG_DIR}")
    files = sorted(os.listdir(FIG_DIR))
    for f in files:
        print(f"  {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())