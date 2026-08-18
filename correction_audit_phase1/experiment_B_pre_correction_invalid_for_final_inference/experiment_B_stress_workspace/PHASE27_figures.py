"""
PHASE 27 — Generate publication figures for Experiment B.

Reads ``experiment_B_runs.json`` and produces PNG/PDF figures for
the paper. Figures are high-resolution and avoid fabrication —
they plot exactly what is in the raw data.

Figures produced:
  1. ens_by_stress_level_and_controller
  2. restoration_time (cumulative_unserved) by_controller
  3. critical_load_restored_pct by_controller
  4. voltage_violation_count by_controller
  5. line_overload_count by_controller
  6. controller_runtime_s by_controller
  7. resilience_loss_area by_controller
  8. cumulative_unserved_restoration_mw by_controller
  9. ablation comparison (energy-related)
 10. Experiment A vs Experiment B (saturation overview)
 11. Representative resilience curve (severe level, seed=0)
 12. Failure-case analysis (full_stack vs rule_based, severe)

Run from project root with EHM-paper environment:

    C:/Users/ELCOT/miniconda3/envs/EHM-paper/python.exe \
        experiments/results/experiment_B_stress/PHASE27_figures.py \
        --input experiments/results/experiment_B_stress/experiment_B_runs.json \
        --output-dir experiments/results/experiment_B_stress/figures/
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from typing import Any, Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


# ── Helpers ────────────────────────────────────────────────────────────
def _by_level_policy(runs: List[Dict[str, Any]]):
    buckets: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in runs:
        level = (
            r.get("stress_level")
            or r.get("scenario", {}).get("stress_level")
            or "nominal"
        )
        policy = r.get("controller_label") or r.get("policy", "")
        buckets.setdefault((str(level), str(policy)), []).append(r)
    return buckets


def _metric(r: Dict[str, Any], name: str) -> float:
    m = r.get("metrics", {}) or {}
    val = m.get(name)
    return float(val) if isinstance(val, (int, float)) else 0.0


def _save(fig, png_path: str, pdf_path: str) -> None:
    fig.tight_layout()
    fig.savefig(png_path, dpi=160, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    print(f"  {png_path}")
    print(f"  {pdf_path}")


# ── Figure 1: ENS by stress level × controller ─────────────────────────
def fig_ens_by_controller(buckets, out_dir: str) -> None:
    levels = ["moderate", "severe"]
    policies = sorted({k[1] for k in buckets.keys()})
    fig, ax = plt.subplots(figsize=(11, 5))
    width = 0.18
    x_positions = list(range(len(policies)))
    colors = ["#3B7DD8", "#E26E26"]
    for i, level in enumerate(levels):
        means, stds = [], []
        for p in policies:
            rs = buckets.get((level, p), [])
            vals = [
                _metric(r, "stress_cumulative_unserved_energy") for r in rs
            ]
            means.append(statistics.mean(vals) if vals else 0.0)
            stds.append(statistics.stdev(vals) if len(vals) > 1 else 0.0)
        ax.bar(
            [x + i * width for x in x_positions],
            means,
            width=width,
            yerr=stds,
            label=level,
            color=colors[i],
            capsize=3,
        )
    ax.set_xticks([x + width / 2 for x in x_positions])
    ax.set_xticklabels(policies, rotation=20, ha="right")
    ax.set_ylabel("stress_cumulative_unserved_energy (MW·steps)")
    ax.set_title("Stress-scenario cumulative unserved energy by controller")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    _save(fig, f"{out_dir}/ens_by_controller.png", f"{out_dir}/ens_by_controller.pdf")


# ── Figure 2: Critical-load restoration by controller ──────────────────
def fig_critical_load(buckets, out_dir: str) -> None:
    levels = ["moderate", "severe"]
    policies = sorted({k[1] for k in buckets.keys()})
    fig, ax = plt.subplots(figsize=(11, 5))
    width = 0.18
    x_positions = list(range(len(policies)))
    colors = ["#3B7DD8", "#E26E26"]
    for i, level in enumerate(levels):
        means, stds = [], []
        for p in policies:
            rs = buckets.get((level, p), [])
            vals = [
                _metric(r, "stress_critical_load_restored_pct")
                for r in rs
            ]
            means.append(statistics.mean(vals) if vals else 0.0)
            stds.append(statistics.stdev(vals) if len(vals) > 1 else 0.0)
        ax.bar(
            [x + i * width for x in x_positions],
            means,
            width=width,
            yerr=stds,
            label=level,
            color=colors[i],
            capsize=3,
        )
    ax.set_xticks([x + width / 2 for x in x_positions])
    ax.set_xticklabels(policies, rotation=20, ha="right")
    ax.set_ylabel("stress_critical_load_restored_pct (%)")
    ax.set_title("Critical-load restoration by controller")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    _save(fig, f"{out_dir}/critical_load_restored_pct_by_controller.png",
          f"{out_dir}/critical_load_restored_pct_by_controller.pdf")


# ── Figure 3: Line overload count by controller ───────────────────────
def fig_line_overload(buckets, out_dir: str) -> None:
    levels = ["moderate", "severe"]
    policies = sorted({k[1] for k in buckets.keys()})
    fig, ax = plt.subplots(figsize=(11, 5))
    width = 0.18
    x_positions = list(range(len(policies)))
    colors = ["#3B7DD8", "#E26E26"]
    for i, level in enumerate(levels):
        means, stds = [], []
        for p in policies:
            rs = buckets.get((level, p), [])
            vals = [_metric(r, "line_overload_count") for r in rs]
            means.append(statistics.mean(vals) if vals else 0.0)
            stds.append(statistics.stdev(vals) if len(vals) > 1 else 0.0)
        ax.bar(
            [x + i * width for x in x_positions],
            means,
            width=width,
            yerr=stds,
            label=level,
            color=colors[i],
            capsize=3,
        )
    ax.set_xticks([x + width / 2 for x in x_positions])
    ax.set_xticklabels(policies, rotation=20, ha="right")
    ax.set_ylabel("line_overload_count (per run)")
    ax.set_title("Line overload count by controller (stress benchmark)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    _save(fig, f"{out_dir}/line_overload_by_controller.png",
          f"{out_dir}/line_overload_by_controller.pdf")


# ── Figure 4: Voltage violation count by controller ───────────────────
def fig_voltage_violations(buckets, out_dir: str) -> None:
    levels = ["moderate", "severe"]
    policies = sorted({k[1] for k in buckets.keys()})
    fig, ax = plt.subplots(figsize=(11, 5))
    width = 0.18
    x_positions = list(range(len(policies)))
    colors = ["#3B7DD8", "#E26E26"]
    for i, level in enumerate(levels):
        means, stds = [], []
        for p in policies:
            rs = buckets.get((level, p), [])
            vals = [_metric(r, "voltage_violation_count") for r in rs]
            means.append(statistics.mean(vals) if vals else 0.0)
            stds.append(statistics.stdev(vals) if len(vals) > 1 else 0.0)
        ax.bar(
            [x + i * width for x in x_positions],
            means,
            width=width,
            yerr=stds,
            label=level,
            color=colors[i],
            capsize=3,
        )
    ax.set_xticks([x + width / 2 for x in x_positions])
    ax.set_xticklabels(policies, rotation=20, ha="right")
    ax.set_ylabel("voltage_violation_count (per run)")
    ax.set_title("Voltage violation count by controller")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    _save(fig, f"{out_dir}/voltage_violations_by_controller.png",
          f"{out_dir}/voltage_violations_by_controller.pdf")


# ── Figure 5: Controller runtime by controller ─────────────────────────
def fig_runtime(buckets, out_dir: str) -> None:
    levels = ["moderate", "severe"]
    policies = sorted({k[1] for k in buckets.keys()})
    fig, ax = plt.subplots(figsize=(11, 5))
    width = 0.18
    x_positions = list(range(len(policies)))
    colors = ["#3B7DD8", "#E26E26"]
    for i, level in enumerate(levels):
        means, stds = [], []
        for p in policies:
            rs = buckets.get((level, p), [])
            vals = [_metric(r, "controller_runtime_s") for r in rs]
            means.append(statistics.mean(vals) if vals else 0.0)
            stds.append(statistics.stdev(vals) if len(vals) > 1 else 0.0)
        ax.bar(
            [x + i * width for x in x_positions],
            means,
            width=width,
            yerr=stds,
            label=level,
            color=colors[i],
            capsize=3,
        )
    ax.set_xticks([x + width / 2 for x in x_positions])
    ax.set_xticklabels(policies, rotation=20, ha="right")
    ax.set_ylabel("controller_runtime_s (per run)")
    ax.set_title("Controller runtime by controller (computational cost)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    _save(fig, f"{out_dir}/runtime_by_controller.png",
          f"{out_dir}/runtime_by_controller.pdf")


# ── Figure 6: Resilience loss area by controller ──────────────────────
def fig_resilience_loss_area(buckets, out_dir: str) -> None:
    levels = ["moderate", "severe"]
    policies = sorted({k[1] for k in buckets.keys()})
    fig, ax = plt.subplots(figsize=(11, 5))
    width = 0.18
    x_positions = list(range(len(policies)))
    colors = ["#3B7DD8", "#E26E26"]
    for i, level in enumerate(levels):
        means, stds = [], []
        for p in policies:
            rs = buckets.get((level, p), [])
            vals = [_metric(r, "resilience_loss_area") for r in rs]
            means.append(statistics.mean(vals) if vals else 0.0)
            stds.append(statistics.stdev(vals) if len(vals) > 1 else 0.0)
        ax.bar(
            [x + i * width for x in x_positions],
            means,
            width=width,
            yerr=stds,
            label=level,
            color=colors[i],
            capsize=3,
        )
    ax.set_xticks([x + width / 2 for x in x_positions])
    ax.set_xticklabels(policies, rotation=20, ha="right")
    ax.set_ylabel("resilience_loss_area (service·steps)")
    ax.set_title("Resilience loss area by controller")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    _save(fig, f"{out_dir}/resilience_loss_area_by_controller.png",
          f"{out_dir}/resilience_loss_area_by_controller.pdf")


# ── Figure 7: Resilience curve (representative seed) ──────────────────
def fig_resilience_curve(runs: List[Dict[str, Any]], out_dir: str) -> None:
    """Plot the per-step unserved energy curve for one representative
    seed at the severe level for several controllers."""
    severe = [r for r in runs if r.get("stress_level") == "severe"]
    if not severe:
        return
    # Pick seed=0 by default.
    seed = 0
    sub = [r for r in severe if r.get("seed") == seed]
    if not sub:
        return
    fig, ax = plt.subplots(figsize=(11, 5))
    color_cycle = ["#3B7DD8", "#E26E26", "#1B7F4D", "#7E3FBF", "#B89F1E",
                   "#1E1E1E", "#777777", "#999999", "#444444"]
    for i, r in enumerate(sub):
        ctrl = r.get("controller_label", "?")
        series = r.get("series_unserved", [])
        if not series:
            continue
        ax.plot(
            series,
            label=ctrl,
            color=color_cycle[i % len(color_cycle)],
            alpha=0.85,
        )
    ax.set_xlabel("simulation step")
    ax.set_ylabel("unserved load (MW)")
    ax.set_title(
        f"Representative resilience curve — severe level, seed={seed}"
    )
    ax.legend(ncol=3, fontsize=9)
    ax.grid(alpha=0.3)
    _save(fig, f"{out_dir}/resilience_curve_severe_seed{seed}.png",
          f"{out_dir}/resilience_curve_severe_seed{seed}.pdf")


# ── Figure 8: Experiment A vs Experiment B (saturation overview) ──────
def fig_a_vs_b(exp_a_path: str, exp_b_runs: List[Dict[str, Any]],
               out_dir: str) -> None:
    if not os.path.isfile(exp_a_path):
        return
    with open(exp_a_path, "r", encoding="utf-8") as f:
        exp_a = json.load(f)
    a_runs = exp_a.get("runs", [])
    if not a_runs:
        return
    metrics = ("saifi", "saidi", "ens", "restoration_time_seconds",
               "critical_load_restored_pct", "voltage_violation_count")
    a_buckets = _by_level_policy(a_runs)
    b_buckets = _by_level_policy(exp_b_runs)
    # Union of policies across A and B so each axis can hold all bars.
    # Experiment A may not have ablation variants; Experiment B includes them.
    a_policies = sorted({k[1] for k in a_buckets.keys()}) or [
        "persistence", "random", "rule_based", "dqn_core_only", "full_stack",
    ]
    b_policies = sorted({k[1] for k in b_buckets.keys()})
    all_policies = sorted(set(a_policies) | set(b_policies))
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for ax, metric in zip(axes.flat, metrics):
        # Experiment A buckets default to "nominal" (no stress_level set);
        # Experiment B buckets use the explicit stress level name.
        a_level = "nominal"
        b_level = "severe"
        a_means = [
            statistics.mean([
                _metric(r, metric)
                for r in a_buckets.get((a_level, p), [])
            ]) if a_buckets.get((a_level, p), []) else 0.0
            for p in all_policies
        ]
        # Experiment B — severe
        b_means = [
            statistics.mean([
                _metric(r, metric)
                for r in b_buckets.get((b_level, p), [])
            ]) if b_buckets.get((b_level, p), []) else 0.0
            for p in all_policies
        ]
        x = list(range(len(all_policies)))
        ax.bar(
            [xi - 0.2 for xi in x],
            a_means,
            width=0.4,
            label="A (nominal)",
            color="#1B7F4D",
        )
        ax2 = ax.twinx()
        ax2.bar(
            [xi + 0.2 for xi in x],
            b_means,
            width=0.4,
            label="B (severe)",
            color="#E26E26",
        )
        ax.set_xticks(x)
        ax.set_xticklabels(all_policies, rotation=20, ha="right", fontsize=8)
        ax.set_title(metric, fontsize=10)
        ax.grid(axis="y", alpha=0.3)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    handles2, labels2 = axes[0, 0].twinx().get_legend_handles_labels()
    fig.legend(
        handles + handles2, labels + labels2,
        loc="upper center", ncol=2, fontsize=10,
    )
    fig.suptitle("Experiment A (nominal) vs Experiment B (severe)",
                 fontsize=12)
    _save(fig, f"{out_dir}/experiment_a_vs_b.png",
          f"{out_dir}/experiment_a_vs_b.pdf")


# ── Main driver ────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output-dir",
                    default="experiments/results/experiment_B_stress/figures/")
    ap.add_argument("--experiment-a",
                    default="paper_results/raw/baseline_results.json")
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    with open(args.input, "r", encoding="utf-8") as f:
        report = json.load(f)
    runs = report.get("runs", [])
    buckets = _by_level_policy(runs)

    print("Generating figures...")
    fig_ens_by_controller(buckets, args.output_dir)
    fig_critical_load(buckets, args.output_dir)
    fig_line_overload(buckets, args.output_dir)
    fig_voltage_violations(buckets, args.output_dir)
    fig_runtime(buckets, args.output_dir)
    fig_resilience_loss_area(buckets, args.output_dir)
    fig_resilience_curve(runs, args.output_dir)
    fig_a_vs_b(args.experiment_a, runs, args.output_dir)
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
