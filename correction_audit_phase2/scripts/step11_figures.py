"""STEP 11 — Publication-quality figures from corrected Experiment-B data only."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import fina_common as fc

OUT = fc.ROOT
FIG = os.path.join(OUT, "figures")

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.bbox": "tight",
})

POLY_ORDER = fc.POLICIES
COLORS = plt.cm.viridis(np.linspace(0.05, 0.95, 9))
COLOR_MAP = {p: COLORS[i] for i, p in enumerate(POLY_ORDER)}


def _save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, f"{name}.{ext}"))
    plt.close(fig)
    print(f"  {name}.png/.pdf")


def _box_panel(ax, data, labels, colors=None, ylabel=""):
    bp = ax.boxplot(data, labels=labels, patch_artist=True, showfliers=True,
                    medianprops=dict(color="black", lw=1.2))
    if colors is None:
        colors = [COLOR_MAP[p] for p in labels]
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.55)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=45)


def fig01_ens(raw):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=False)
    for ax, lvl in zip(axes, fc.STRESS_LEVELS):
        data = [raw[(raw["policy"] == p) & (raw["stress_level"] == lvl)]["stress_cumulative_unserved_energy"].values for p in POLY_ORDER]
        _box_panel(ax, data, POLY_ORDER, ylabel="stress cumulative ENS (MW·steps)")
        ax.set_title(f"Stress level: {lvl}")
    fig.suptitle("Figure 1 — Cumulative unserved energy by policy (corrected Experiment B)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, "fig01_ens_by_policy")


def fig02_saturated_metrics(raw):
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, (lvl, col, title, yl) in zip(
            axes,
            [("moderate", "resilience_time_to_50pct_restoration", "moderate", "steps"),
             ("severe", "resilience_time_to_50pct_restoration", "severe", "steps"),
             ("all", "stress_restoration_rate", "both levels", "restoration rate")]):
        if lvl == "all":
            data = [raw[raw["policy"] == p]["stress_restoration_rate"].values for p in POLY_ORDER]
        else:
            data = [raw[(raw["policy"] == p) & (raw["stress_level"] == lvl)][col].values for p in POLY_ORDER]
        _box_panel(ax, data, POLY_ORDER, ylabel=yl)
        ax.set_title(f"{title}: {col}")
    fig.suptitle("Figure 2 — Saturated restoration metrics (observed values; no variance)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, "fig02_saturated_restoration_metrics")


def fig03_critical_load(raw):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, lvl in zip(axes, fc.STRESS_LEVELS):
        data = [raw[(raw["policy"] == p) & (raw["stress_level"] == lvl)]["stress_critical_load_restored_pct"].values for p in POLY_ORDER]
        _box_panel(ax, data, POLY_ORDER, ylabel="critical-load restored (%)")
        ax.set_title(f"Stress level: {lvl}")
        ax.set_ylim(95, 100.5)
    fig.suptitle("Figure 3 — Critical-load restoration % (saturated at ceiling)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, "fig03_critical_load_restoration")


def fig04_saidi_saifi(raw):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, (col, title) in zip(axes, [("saidi", "SAIDI"), ("saifi", "SAIFI")]):
        data = [raw[(raw["policy"] == p)][col].values for p in POLY_ORDER]
        _box_panel(ax, data, POLY_ORDER, ylabel=title)
        ax.set_title(f"{title} (both stress levels)")
    fig.suptitle("Figure 4 — SAIDI (saturated at 0) and SAIFI", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, "fig04_saidi_saifi")


def fig05_resilience(raw):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, lvl in zip(axes, fc.STRESS_LEVELS):
        data = [raw[(raw["policy"] == p) & (raw["stress_level"] == lvl)]["resilience_loss_area"].values for p in POLY_ORDER]
        _box_panel(ax, data, POLY_ORDER, ylabel="resilience loss area (MW·steps)")
        ax.set_title(f"Stress level: {lvl}")
    fig.suptitle("Figure 5 — Resilience loss area by policy", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, "fig05_resilience_comparison")


def fig06_baseline(raw):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    metrics = [("stress_cumulative_unserved_energy", "ENS (MW·steps)"),
               ("resilience_loss_area", "resilience loss area"),
               ("voltage_violation_count", "voltage violations")]
    for ax, (col, yl) in zip(axes, metrics):
        data = []
        for p in ["persistence", "random", "rule_based", "dqn_core_only", "full_stack"]:
            data.append(raw[raw["policy"] == p][col].values)
        _box_panel(ax, data, ["persistence", "random", "rule_based", "dqn_core_only", "full_stack"], ylabel=yl)
        ax.set_title(yl)
    fig.suptitle("Figure 6 — Baseline comparison (both stress levels pooled)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, "fig06_baseline_comparison")


def fig07_ablation(raw):
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.2))
    for ax, abl in zip(axes, ["no_lstm", "no_twin", "no_predictive", "no_reward"]):
        for lvl, style in zip(fc.STRESS_LEVELS, ["o", "s"]):
            fs = raw[(raw["policy"] == "full_stack") & (raw["stress_level"] == lvl)].set_index("seed")["stress_cumulative_unserved_energy"]
            ab = raw[(raw["policy"] == abl) & (raw["stress_level"] == lvl)].set_index("seed")["stress_cumulative_unserved_energy"]
            common = fs.index
            ax.plot(fs.loc[common].values, ab.loc[common].values, style, ms=4, alpha=0.7, label=lvl)
        lim = [0, ax.get_xlim()[1]]
        ax.plot(lim, lim, "k--", lw=0.8)
        ax.set_xlabel("full_stack ENS")
        ax.set_ylabel(f"{abl} ENS")
        ax.set_title(abl)
        ax.legend()
    fig.suptitle("Figure 7 — Ablation: per-seed ENS identity (all points on the identity line)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, "fig07_ablation_comparison")


def fig08_runtime(raw):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    metrics = [("controller_runtime_s", "controller runtime (s/run)"),
               ("power_flow_runtime_s", "power-flow runtime (s/run)"),
               ("runtime_s", "total runtime (s/run)")]
    for ax, (col, yl) in zip(axes, metrics):
        data = [raw[(raw["policy"] == p)][col].values for p in POLY_ORDER]
        _box_panel(ax, data, POLY_ORDER, ylabel=yl)
        ax.set_title(yl)
    fig.suptitle("Figure 8 — Computational cost by policy (both stress levels)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, "fig08_runtime_computational_cost")


def fig09_a_vs_b(a, b):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
    for ax, lvl in zip(axes, fc.STRESS_LEVELS):
        labels = ["persistence", "random", "rule_based", "dqn_core_only", "full_stack"]
        a_data = [a[a["policy"] == p]["ens"].values for p in labels]
        b_data = [b[(b["policy"] == p) & (b["stress_level"] == lvl)]["ens"].values for p in labels]
        x = np.arange(len(labels))
        w = 0.38
        bp_a = ax.boxplot(a_data, positions=x - w / 2, widths=w, patch_artist=True,
                          medianprops=dict(color="black"))
        bp_b = ax.boxplot(b_data, positions=x + w / 2, widths=w, patch_artist=True,
                          medianprops=dict(color="black"))
        for patch in bp_a["boxes"]:
            patch.set_facecolor("#4C72B0"); patch.set_alpha(0.6)
        for patch in bp_b["boxes"]:
            patch.set_facecolor("#C44E52"); patch.set_alpha(0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30)
        ax.set_ylabel("ENS (MW·steps)")
        ax.set_title(f"B: {lvl}")
        ax.legend([bp_a["boxes"][0], bp_b["boxes"][0]], ["A nominal", f"B {lvl}"], loc="upper left")
    fig.suptitle("Figure 9 — Experiment A (nominal) vs Experiment B (stress): ENS", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, "fig09_experiment_a_vs_b")


def fig10_module_execution(mod):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    groups = [
        ("FLISR", ["flisr_calls", "flisr_successes", "flisr_failures", "restoration_applied"]),
        ("LSTM & Twin", ["lstm/model_calls", "inference_successes", "twin_updates", "twin_queries"]),
        ("Predictive & DQN", ["predictive_assessments", "recommendations_generated", "predictive_applied", "dqn_actions"]),
    ]
    for ax, (title, cols) in zip(axes, groups):
        sev = mod[mod["stress_level"] == "severe"]
        x = np.arange(len(POLY_ORDER))
        width = 0.8 / len(cols)
        for i, c in enumerate(cols):
            vals = [sev[sev["policy"] == p][c].iloc[0] for p in POLY_ORDER]
            ax.bar(x + (i - len(cols) / 2 + 0.5) * width, vals, width, label=c, log=False)
        ax.set_xticks(x)
        ax.set_xticklabels(POLY_ORDER, rotation=45)
        ax.set_title(title)
        ax.legend(fontsize=6.5, loc="upper left")
    fig.suptitle("Figure 10 — Module execution evidence (severe stress, totals over 30 seeds)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, "fig10_module_execution_evidence")


def main() -> None:
    raw = fc.load_corrected_b()
    a = fc.load_exp_a()
    mod = pd.read_csv(os.path.join(OUT, "MODULE_EXECUTION_AUDIT.csv"))
    os.makedirs(FIG, exist_ok=True)
    print("Generating figures...")
    fig01_ens(raw)
    fig02_saturated_metrics(raw)
    fig03_critical_load(raw)
    fig04_saidi_saifi(raw)
    fig05_resilience(raw)
    fig06_baseline(raw)
    fig07_ablation(raw)
    fig08_runtime(raw)
    fig09_a_vs_b(a, raw)
    fig10_module_execution(mod)
    print("Done.")


if __name__ == "__main__":
    main()
