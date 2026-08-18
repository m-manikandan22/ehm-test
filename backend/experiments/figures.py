"""figures.py — Publication-quality figures for EHM paper experiments.

Why this module exists
----------------------
The paper tables (``backend/experiments/tables.py``) are text-only. The
figures module produces matplotlib PNG/PDF charts for the most
important quantitative comparisons:

  * Per-policy baseline bar chart for the primary metrics (SAIDI,
    SAIFI, ENS, restoration time, critical-load restored %).
  * Ablation horizontal bar chart of the "cost" of removing each
    component (delta vs ``full_stack``).
  * Predictive-vs-reactive scatter.
  * Storage-policy grouped bar chart (hybrid vs battery-only vs
    supercap-only vs none).
  * Topology resilience comparison (N-1 recoverability as %).

Design principles
-----------------
* No external state. Every function takes a dict or list of dicts and
  returns the figure (or saves it). This keeps the module testable.
* matplotlib-only. No seaborn, no plotly. The paper must render
  identically on any platform with matplotlib.
* Light theme, sensible defaults, readable labels. Colours follow a
  fixed qualitative palette so the same policy always gets the same
  colour across figures.
* Every figure includes error bars / inter-quartile info where the
  caller provides raw paired samples.
* No fabricated data. If a metric is missing, the function raises
  ``ValueError`` with a clear message.

Limitations
-----------
* matplotlib must be installed. The module imports lazily inside each
  function so the rest of the package can run without matplotlib.
* Each figure is a single Axes (no subplot grids). The paper can
  arrange them with ``\\includegraphics`` / SVG.

Usage
-----
::

    from experiments.figures import (
        baseline_bar_chart, ablation_bar_chart, predictive_vs_reactive,
        storage_grouped_bar, topology_resilience_chart,
    )
    fig = baseline_bar_chart(per_policy_summary, metric="saidi_min")
    fig.savefig("figures/saidi.png", dpi=200, bbox_inches="tight")
"""
from __future__ import annotations

import math
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# Qualitative palette used across every figure. Colour-blind safe-ish.
POLICY_COLOURS: Dict[str, str] = {
    "full_stack":      "#1f77b4",  # blue
    "rule_based":      "#2ca02c",  # green
    "dqn_core_only":   "#9467bd",  # purple
    "random":          "#d62728",  # red
    "persistence":     "#8c564b",  # brown
    "no_lstm":         "#1f77b4",
    "no_twin":         "#ff7f0e",
    "no_predictive":   "#2ca02c",
    "no_reward":       "#d62728",
    "hybrid":          "#1f77b4",
    "battery_only":    "#2ca02c",
    "supercap_only":   "#ff7f0e",
    "none":            "#7f7f7f",
    "predictive":      "#1f77b4",
    "reactive":        "#d62728",
}


def _mpl():
    """Lazy import so the rest of the package can run without matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg", force=True)  # non-interactive backend
        import matplotlib.pyplot as plt
        return plt
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "matplotlib is required for figures. Install with "
            "`pip install matplotlib`."
        ) from exc


def _colour_for(policy: str) -> str:
    return POLICY_COLOURS.get(policy, "#7f7f7f")


def _ensure_dir(path: str) -> None:
    out_dir = os.path.dirname(os.path.abspath(path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)


# ── Bar chart primitives ────────────────────────────────────────────

def baseline_bar_chart(
    per_policy: Dict[str, Dict[str, float]],
    *,
    metric: str,
    ylabel: Optional[str] = None,
    title: Optional[str] = None,
    out_path: Optional[str] = None,
) -> Any:
    """Bar chart of a single metric across policies.

    Parameters
    ----------
    per_policy : dict
        ``{policy_name: {metric_name: value, ...}, ...}``. Missing
        metrics raise ``ValueError``.
    metric : str
        Which metric to plot. Must be present in every policy's dict.
    ylabel, title : str, optional
    out_path : str, optional
        Where to save the figure (PNG). If None, the figure is returned
        but not saved.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _mpl()
    labels = list(per_policy.keys())
    if not labels:
        raise ValueError("per_policy is empty")
    for name, row in per_policy.items():
        if metric not in row:
            raise ValueError(f"policy {name!r} is missing metric {metric!r}")
    values = [float(per_policy[name][metric]) for name in labels]
    colours = [_colour_for(name) for name in labels]

    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    bars = ax.bar(labels, values, color=colours, edgecolor="black", linewidth=0.4)
    ax.set_ylabel(ylabel or metric)
    ax.set_title(title or f"{metric} by policy")
    ax.grid(True, axis="y", alpha=0.3)
    # Attach value labels on top of each bar
    ymax = max(values + [0.0])
    pad = max(0.01 * abs(ymax), 1e-9)
    for bar, v in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + pad,
            f"{v:.3f}",
            ha="center", va="bottom", fontsize=8,
        )
    fig.tight_layout()
    if out_path:
        _ensure_dir(out_path)
        fig.savefig(out_path, dpi=200, bbox_inches="tight")
    return fig


def ablation_bar_chart(
    per_config: Dict[str, Dict[str, float]],
    *,
    baseline_label: str,
    metric: str,
    ylabel: Optional[str] = None,
    title: Optional[str] = None,
    out_path: Optional[str] = None,
) -> Any:
    """Horizontal bar chart of ``metric - baseline`` for each ablation.

    Bars to the right mean worse than baseline; bars to the left mean
    better. A dashed vertical line marks zero.
    """
    plt = _mpl()
    if baseline_label not in per_config:
        raise ValueError(f"baseline {baseline_label!r} not in per_config")
    base = float(per_config[baseline_label][metric])
    rows = [
        (label, float(row[metric]) - base)
        for label, row in per_config.items()
        if label != baseline_label
    ]
    rows.sort(key=lambda x: x[1])
    labels = [r[0] for r in rows]
    deltas = [r[1] for r in rows]
    colours = [_colour_for(name) for name in labels]

    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    y_pos = list(range(len(labels)))
    ax.barh(y_pos, deltas, color=colours, edgecolor="black", linewidth=0.4)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.axvline(0.0, color="black", linestyle="--", linewidth=0.6)
    ax.set_xlabel(f"Δ {metric} (config − {baseline_label})")
    ax.set_ylabel("")
    ax.set_title(title or f"Ablation: Δ{metric} vs {baseline_label}")
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    if out_path:
        _ensure_dir(out_path)
        fig.savefig(out_path, dpi=200, bbox_inches="tight")
    return fig


# ── Predictive vs reactive ──────────────────────────────────────────

def predictive_vs_reactive(
    samples: Sequence[Tuple[float, float]],
    *,
    metric_label: str = "ENS [MWh]",
    title: Optional[str] = None,
    out_path: Optional[str] = None,
) -> Any:
    """Paired scatter of (reactive, predictive) for one metric.

    A point below the diagonal means predictive is lower (better, if
    the metric is "lower is better"). The diagonal line is shown.
    """
    plt = _mpl()
    if not samples:
        raise ValueError("samples is empty")
    xs = [float(s[0]) for s in samples]
    ys = [float(s[1]) for s in samples]

    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    ax.scatter(xs, ys, alpha=0.7, color="#1f77b4", edgecolor="black",
               linewidth=0.4, s=30)
    lo = min(xs + ys)
    hi = max(xs + ys)
    pad = 0.05 * (hi - lo) if hi > lo else 1.0
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad],
            color="black", linestyle="--", linewidth=0.6,
            label="y = x")
    ax.set_xlabel(f"Reactive {metric_label}")
    ax.set_ylabel(f"Predictive {metric_label}")
    ax.set_title(title or f"Predictive vs Reactive ({metric_label})")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    if out_path:
        _ensure_dir(out_path)
        fig.savefig(out_path, dpi=200, bbox_inches="tight")
    return fig


# ── Storage grouped bar ─────────────────────────────────────────────

def storage_grouped_bar(
    per_policy: Dict[str, Dict[str, float]],
    *,
    metrics: Sequence[str] = ("energy_not_served_mwh", "customer_minutes_interrupted", "n_recoveries"),
    out_path: Optional[str] = None,
) -> Any:
    """Grouped bar chart of storage policy vs (default) metrics.

    Policies appear on the x-axis, metrics on the colour axis. Each
    metric is normalised to its max across policies so they share an
    axis — raw units are reported in the y-tick label.
    """
    plt = _mpl()
    labels = list(per_policy.keys())
    if not labels:
        raise ValueError("per_policy is empty")
    n_metrics = len(metrics)
    width = 0.8 / max(n_metrics, 1)
    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    for i, metric in enumerate(metrics):
        values = [float(per_policy[p][metric]) for p in labels]
        offset = (i - (n_metrics - 1) / 2.0) * width
        bars = ax.bar(
            [list(range(len(labels)))[k] + offset for k in range(len(labels))],
            values, width=width,
            label=metric, edgecolor="black", linewidth=0.4,
        )
        for bar, v in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height(),
                f"{v:.2f}", ha="center", va="bottom", fontsize=7,
            )
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("value (raw units)")
    ax.set_title("Storage policy comparison")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    if out_path:
        _ensure_dir(out_path)
        fig.savefig(out_path, dpi=200, bbox_inches="tight")
    return fig


# ── Topology resilience ─────────────────────────────────────────────

def topology_resilience_chart(
    per_topology: Dict[str, float],
    *,
    metric_label: str = "N-1 recoverability [%]",
    out_path: Optional[str] = None,
) -> Any:
    """Horizontal bar chart of per-topology resilience scores.

    ``per_topology`` is ``{topology_name: score}``. Higher is better.
    """
    plt = _mpl()
    labels = list(per_topology.keys())
    scores = [float(per_topology[k]) for k in labels]
    colours = ["#2ca02c" if s >= 80 else "#ff7f0e" if s >= 50 else "#d62728" for s in scores]
    y_pos = list(range(len(labels)))

    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    ax.barh(y_pos, scores, color=colours, edgecolor="black", linewidth=0.4)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_xlabel(metric_label)
    ax.set_title("Topology resilience comparison")
    ax.set_xlim(0, 100)
    ax.grid(True, axis="x", alpha=0.3)
    for y, s in zip(y_pos, scores):
        ax.text(s + 1, y, f"{s:.1f}%", va="center", fontsize=8)
    fig.tight_layout()
    if out_path:
        _ensure_dir(out_path)
        fig.savefig(out_path, dpi=200, bbox_inches="tight")
    return fig


# ── Restoration trajectory ──────────────────────────────────────────

def restoration_trajectory(
    times: Sequence[int],
    series: Dict[str, Sequence[float]],
    *,
    ylabel: str = "Energy not served [MWh]",
    title: Optional[str] = None,
    out_path: Optional[str] = None,
) -> Any:
    """Line plot of restoration trajectories per policy.

    ``series`` is ``{policy_name: [v_t0, v_t1, ...]}``. Each policy gets
    a coloured line. Useful for showing how the ENS shrinks as
    restoration proceeds.
    """
    plt = _mpl()
    if not series:
        raise ValueError("series is empty")
    fig, ax = plt.subplots(figsize=(7.0, 3.5))
    for name, vals in series.items():
        if len(vals) != len(times):
            raise ValueError(
                f"policy {name!r} has {len(vals)} values, "
                f"expected {len(times)}"
            )
        ax.plot(list(times), list(vals), label=name,
                color=_colour_for(name), linewidth=1.4, marker="o", markersize=3)
    ax.set_xlabel("timestep")
    ax.set_ylabel(ylabel)
    ax.set_title(title or "Restoration trajectory")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    if out_path:
        _ensure_dir(out_path)
        fig.savefig(out_path, dpi=200, bbox_inches="tight")
    return fig


# ── Convenience: render every standard figure from a paper report ──

def render_paper_figures(
    report: Dict[str, Any],
    *,
    out_dir: str,
) -> Dict[str, str]:
    """Render the standard figure set from a paper-experiment report.

    Reads the keys ``"per_policy_summary"``, ``"per_config_summary"``,
    and ``"predictive_vs_reactive_samples"`` (each optional) and writes
    a PNG to ``out_dir``. Returns ``{figure_name: file_path}``.
    """
    written: Dict[str, str] = {}
    os.makedirs(out_dir, exist_ok=True)

    if "per_policy_summary" in report and report["per_policy_summary"]:
        # Try the canonical primary metrics in order; pick the first
        # that's present for each chart.
        candidates = [
            ("saidi_min", "baseline_saidi.png"),
            ("saifi_int", "baseline_saifi.png"),
            ("ens_mwh",   "baseline_ens.png"),
            ("critical_load_restored_pct", "baseline_critical_restored.png"),
        ]
        for metric, fname in candidates:
            if all(metric in r for r in report["per_policy_summary"].values()):
                f = baseline_bar_chart(
                    report["per_policy_summary"], metric=metric,
                    out_path=os.path.join(out_dir, fname),
                )
                plt = _mpl()
                plt.close(f)
                written[metric] = os.path.join(out_dir, fname)

    if "per_config_summary" in report and report["per_config_summary"]:
        # Ablation charts vs full_stack
        for metric, fname in [
            ("saidi_min", "ablation_saidi.png"),
            ("ens_mwh",   "ablation_ens.png"),
            ("critical_load_restored_pct", "ablation_critical_restored.png"),
        ]:
            if (
                "full_stack" in report["per_config_summary"]
                and metric in report["per_config_summary"]["full_stack"]
            ):
                f = ablation_bar_chart(
                    report["per_config_summary"],
                    baseline_label="full_stack",
                    metric=metric,
                    out_path=os.path.join(out_dir, fname),
                )
                plt = _mpl()
                plt.close(f)
                written[f"ablation_{metric}"] = os.path.join(out_dir, fname)

    if (
        "predictive_vs_reactive_samples" in report
        and report["predictive_vs_reactive_samples"]
    ):
        for metric, fname in [
            ("saidi_min", "predictive_vs_reactive_saidi.png"),
            ("ens_mwh",   "predictive_vs_reactive_ens.png"),
        ]:
            key = f"{metric}_samples"
            samples = report["predictive_vs_reactive_samples"].get(key)
            if samples:
                f = predictive_vs_reactive(
                    samples, metric_label=metric,
                    out_path=os.path.join(out_dir, fname),
                )
                plt = _mpl()
                plt.close(f)
                written[f"pvr_{metric}"] = os.path.join(out_dir, fname)

    return written


# ── Self-test ──────────────────────────────────────────────────────

def _self_test() -> bool:
    """Smoke-test each figure with synthetic data."""
    per_policy = {
        "random":        {"saidi_min": 12.5, "ens_mwh": 4.2},
        "rule_based":    {"saidi_min":  9.0, "ens_mwh": 2.8},
        "dqn_core_only": {"saidi_min":  7.2, "ens_mwh": 2.4},
        "full_stack":    {"saidi_min":  5.5, "ens_mwh": 1.6},
    }
    per_config = dict(per_policy)
    per_config["no_lstm"]      = {"saidi_min":  6.0, "ens_mwh": 1.8}
    per_config["no_twin"]      = {"saidi_min":  6.3, "ens_mwh": 2.0}
    per_config["no_predictive"] = {"saidi_min":  6.6, "ens_mwh": 2.1}
    per_config["no_reward"]     = {"saidi_min":  9.2, "ens_mwh": 3.0}

    f = baseline_bar_chart(per_policy, metric="saidi_min")
    plt = _mpl(); plt.close(f)

    f = ablation_bar_chart(per_config, baseline_label="full_stack", metric="saidi_min")
    plt.close(f)

    f = predictive_vs_reactive([(1.0, 0.8), (2.0, 1.4), (3.0, 2.1)])
    plt.close(f)

    storage = {
        "hybrid":        {"energy_not_served_mwh": 1.2, "customer_minutes_interrupted": 30, "n_recoveries": 5},
        "battery_only":  {"energy_not_served_mwh": 1.5, "customer_minutes_interrupted": 38, "n_recoveries": 4},
        "supercap_only": {"energy_not_served_mwh": 2.0, "customer_minutes_interrupted": 50, "n_recoveries": 3},
        "none":          {"energy_not_served_mwh": 2.5, "customer_minutes_interrupted": 65, "n_recoveries": 1},
    }
    f = storage_grouped_bar(storage)
    plt.close(f)

    f = topology_resilience_chart({"random": 30.0, "as-built": 60.0, "planner": 92.0})
    plt.close(f)

    f = restoration_trajectory(
        list(range(10)),
        {"rule_based": [10, 9, 7, 5, 4, 3, 2, 2, 1, 1],
         "full_stack": [10, 6, 3, 2, 1, 1, 1, 1, 1, 1]},
    )
    plt.close(f)

    # Paper-level convenience
    report = {
        "per_policy_summary": per_policy,
        "per_config_summary": per_config,
        "predictive_vs_reactive_samples": {
            "saidi_min_samples": [(12.0, 10.0), (10.0, 8.0), (9.0, 6.0)],
            "ens_mwh_samples":   [(4.0, 3.0), (3.0, 2.5), (2.8, 2.0)],
        },
    }
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        written = render_paper_figures(report, out_dir=td)
        assert written, "render_paper_figures produced nothing"

    return True


if __name__ == "__main__":
    ok = _self_test()
    print("figures self-test:", "PASS" if ok else "FAIL")
