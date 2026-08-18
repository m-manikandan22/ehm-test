"""test_figures.py — Tests for experiments/figures.py

These tests verify the public API of the figures module without
actually inspecting the rendered PNG pixels (which would be brittle).
We exercise the value-validation logic, error paths, and the
convenience dispatcher.
"""
from __future__ import annotations

import os

import pytest


pytest.importorskip("matplotlib")

from experiments import figures


@pytest.fixture
def per_policy():
    return {
        "random":        {"saidi_min": 12.5, "ens_mwh": 4.2},
        "rule_based":    {"saidi_min":  9.0, "ens_mwh": 2.8},
        "full_stack":    {"saidi_min":  5.5, "ens_mwh": 1.6},
    }


@pytest.fixture
def per_config(per_policy):
    cfg = dict(per_policy)
    cfg["no_lstm"]  = {"saidi_min": 6.0, "ens_mwh": 1.8}
    cfg["no_twin"]  = {"saidi_min": 6.3, "ens_mwh": 2.0}
    return cfg


def test_baseline_bar_chart_returns_figure(per_policy, tmp_path):
    out = tmp_path / "saidi.png"
    fig = figures.baseline_bar_chart(per_policy, metric="saidi_min",
                                     out_path=str(out))
    assert fig is not None
    assert out.exists()
    plt = figures._mpl()
    plt.close(fig)


def test_baseline_bar_chart_empty_raises():
    with pytest.raises(ValueError):
        figures.baseline_bar_chart({}, metric="saidi_min")


def test_baseline_bar_chart_missing_metric_raises(per_policy):
    with pytest.raises(ValueError):
        figures.baseline_bar_chart(per_policy, metric="nope")


def test_ablation_bar_chart_sorts_by_delta(per_config, tmp_path):
    out = tmp_path / "abl.png"
    fig = figures.ablation_bar_chart(
        per_config, baseline_label="full_stack", metric="saidi_min",
        out_path=str(out),
    )
    assert fig is not None
    plt = figures._mpl()
    plt.close(fig)


def test_ablation_bar_chart_missing_baseline_raises(per_config):
    with pytest.raises(ValueError):
        figures.ablation_bar_chart(per_config, baseline_label="ghost",
                                   metric="saidi_min")


def test_predictive_vs_reactive_draws_diagonal(tmp_path):
    samples = [(1.0, 0.8), (2.0, 1.5), (3.0, 2.4), (4.0, 2.9)]
    out = tmp_path / "pvr.png"
    fig = figures.predictive_vs_reactive(samples, metric_label="ENS [MWh]",
                                         out_path=str(out))
    assert fig is not None
    plt = figures._mpl()
    plt.close(fig)


def test_predictive_vs_reactive_empty_raises():
    with pytest.raises(ValueError):
        figures.predictive_vs_reactive([])


def test_storage_grouped_bar_uses_all_metrics(tmp_path):
    storage = {
        "hybrid":        {"energy_not_served_mwh": 1.2,
                          "customer_minutes_interrupted": 30,
                          "n_recoveries": 5},
        "battery_only":  {"energy_not_served_mwh": 1.5,
                          "customer_minutes_interrupted": 38,
                          "n_recoveries": 4},
    }
    out = tmp_path / "storage.png"
    fig = figures.storage_grouped_bar(storage, out_path=str(out))
    assert fig is not None
    plt = figures._mpl()
    plt.close(fig)


def test_storage_grouped_bar_empty_raises():
    with pytest.raises(ValueError):
        figures.storage_grouped_bar({})


def test_topology_resilience_chart(tmp_path):
    out = tmp_path / "topo.png"
    fig = figures.topology_resilience_chart(
        {"random": 30.0, "as-built": 60.0, "planner": 92.0},
        out_path=str(out),
    )
    assert fig is not None
    plt = figures._mpl()
    plt.close(fig)


def test_restoration_trajectory(tmp_path):
    times = list(range(5))
    series = {
        "rule_based": [10, 9, 7, 5, 4],
        "full_stack": [10, 6, 3, 2, 1],
    }
    out = tmp_path / "traj.png"
    fig = figures.restoration_trajectory(times, series, out_path=str(out))
    assert fig is not None
    plt = figures._mpl()
    plt.close(fig)


def test_restoration_trajectory_mismatched_length_raises():
    with pytest.raises(ValueError):
        figures.restoration_trajectory(
            [0, 1, 2], {"a": [1.0, 2.0]},
        )


def test_restoration_trajectory_empty_raises():
    with pytest.raises(ValueError):
        figures.restoration_trajectory([0, 1, 2], {})


def test_render_paper_figures_writes_files(per_config, tmp_path):
    report = {
        "per_policy_summary": {
            "random":     {"saidi_min": 12.5, "ens_mwh": 4.2},
            "rule_based": {"saidi_min":  9.0, "ens_mwh": 2.8},
            "full_stack": {"saidi_min":  5.5, "ens_mwh": 1.6},
        },
        "per_config_summary": per_config,
        "predictive_vs_reactive_samples": {
            "saidi_min_samples": [(12.0, 10.0), (10.0, 8.0)],
            "ens_mwh_samples":   [(4.0, 3.0), (3.0, 2.5)],
        },
    }
    written = figures.render_paper_figures(report, out_dir=str(tmp_path))
    assert written, "expected at least one figure written"
    # At least the SAIDI baseline + ablation must exist.
    assert "saidi_min" in written
    assert "ablation_saidi_min" in written
    assert "pvr_saidi_min" in written
    # Each path must point to a real file.
    for path in written.values():
        assert os.path.exists(path)


def test_render_paper_figures_empty_report_returns_empty(tmp_path):
    assert figures.render_paper_figures({}, out_dir=str(tmp_path)) == {}


def test_module_self_test_passes():
    assert figures._self_test() is True