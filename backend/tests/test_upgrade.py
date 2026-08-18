"""
test_upgrade.py — Regression tests for the research-readiness upgrade.

These tests pin down the *behavioural contract* of the new framework:

  - Scenario generation is deterministic per seed.
  - Validity guards flag NaN / impossible voltage.
  - MetricCollector counts match what happened in the grid.
  - ExperimentConfig.active_modules() and .disabled_modules() match
    the booleans — the runner cannot silently mislabel.
  - The runner produces a valid JSON report that contains the
    documented metric keys and validity report for every pre-baked
    configuration.
  - The tables module emits per-policy + paired tables from the
    runner output.
  - The statistics module's self-test continues to pass.
"""
from __future__ import annotations

import json
import math
import os
import sys
import tempfile
from unittest import mock

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")
for p in (BACKEND_ROOT, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)


def _import_experiment_config():
    from experiments.experiment_config import ExperimentConfig, ABLATION_CONFIGS
    return ExperimentConfig, ABLATION_CONFIGS


def _import_scenario():
    from experiments.scenario import Scenario, FaultEvent, make_scenario
    return Scenario, FaultEvent, make_scenario


def _import_validity():
    from experiments.validity import (
        InvalidRunReason, ValidityReport, check_run_validity,
    )
    return InvalidRunReason, ValidityReport, check_run_validity


def _import_research_metrics():
    from experiments.research_metrics import (
        CRITICAL_NODE_TYPES, MetricCollector, compute_research_metrics,
        FaultRecord,
    )
    return CRITICAL_NODE_TYPES, MetricCollector, compute_research_metrics, FaultRecord


def _import_runner():
    from experiments.runner import run_single, run_experiment, _build_grid
    return run_single, run_experiment, _build_grid


# ── ExperimentConfig ────────────────────────────────────────────────────
def test_experiment_config_active_disabled_consistent():
    """active_modules() + disabled_modules() must cover every flag."""
    ExperimentConfig, _ = _import_experiment_config()
    cfg = ExperimentConfig.full_stack(seed=1)
    active = set(cfg.active_modules())
    disabled = set(cfg.disabled_modules())
    # Disjoint.
    assert active.isdisjoint(disabled), f"overlap: {active & disabled}"
    # Union covers all 9 modules.
    assert len(active) + len(disabled) == 9


def test_experiment_config_no_lstm_genuinely_disables_lstm():
    ExperimentConfig, _ = _import_experiment_config()
    cfg = ExperimentConfig.no_lstm(seed=2)
    assert "lstm" in cfg.disabled_modules()
    assert "lstm" not in cfg.active_modules()
    assert cfg.enable_lstm is False


def test_experiment_config_to_dict_includes_active_disabled():
    ExperimentConfig, _ = _import_experiment_config()
    cfg = ExperimentConfig.dqn_core_only(seed=3)
    d = cfg.to_dict()
    assert "active_modules" in d
    assert "disabled_modules" in d
    assert "dqn" in d["active_modules"]
    assert "flisr" in d["active_modules"]
    assert "lstm" in d["disabled_modules"]
    assert "digital_twin" in d["disabled_modules"]


def test_ablation_configs_table_is_complete():
    _, ABLATION_CONFIGS = _import_experiment_config()
    expected = {
        "full_stack", "no_lstm", "no_twin", "no_predictive", "no_reward",
        "dqn_core_only", "rule_based", "random", "persistence",
    }
    assert set(ABLATION_CONFIGS.keys()) == expected


# ── Scenario ────────────────────────────────────────────────────────────
def test_scenario_is_deterministic_per_seed():
    _, _, make_scenario = _import_scenario()
    a = make_scenario(seed=42, total_steps=50, fault_count=3)
    b = make_scenario(seed=42, total_steps=50, fault_count=3)
    assert a.faults == b.faults
    assert a.total_steps == b.total_steps
    assert a.weather_mode == b.weather_mode


def test_scenario_differs_per_seed():
    _, _, make_scenario = _import_scenario()
    a = make_scenario(seed=1, total_steps=50, fault_count=3)
    b = make_scenario(seed=2, total_steps=50, fault_count=3)
    # Fault list should differ for different seeds.
    assert a.faults != b.faults


def test_scenario_no_faults_when_count_zero():
    _, _, make_scenario = _import_scenario()
    s = make_scenario(seed=0, total_steps=20, fault_count=0)
    assert s.faults == []


def test_scenario_to_dict_json_serialisable():
    _, _, make_scenario = _import_scenario()
    s = make_scenario(seed=0, total_steps=20, fault_count=1)
    d = s.to_dict()
    # Must round-trip through JSON.
    serialised = json.dumps(d, default=str)
    parsed = json.loads(serialised)
    assert parsed["total_steps"] == 20


# ── Validity ────────────────────────────────────────────────────────────
class _FakeNode:
    def __init__(self, voltage=1.0, frequency=50.0, failed=False, isolated=False):
        self.voltage = voltage
        self.frequency = frequency
        self.failed = failed
        self.isolated = isolated


class _FakeGrid:
    """Minimal grid stub with just enough surface for check_run_validity."""

    def __init__(self, nodes=None, edges=None):
        self.nodes = nodes or {}
        # Build a minimal stand-in for networkx graph: support
        # ``edges(data=True)`` like iteration.
        self._edges = edges or []
        self.graph = self

    def edges(self, data=False):
        if data:
            return [(u, v, d) for (u, v, d) in self._edges]
        return [(u, v) for (u, v, _) in self._edges]


def test_validity_flags_nan_voltage():
    _, _, check_run_validity = _import_validity()
    grid = _FakeGrid(nodes={"A": _FakeNode(voltage=float("nan"))})
    rep = check_run_validity(grid)
    assert not rep.valid


def test_validity_flags_impossible_voltage_high():
    _, _, check_run_validity = _import_validity()
    grid = _FakeGrid(nodes={"A": _FakeNode(voltage=10.0)})
    rep = check_run_validity(grid)
    assert not rep.valid


def test_validity_flags_impossible_voltage_low():
    _, _, check_run_validity = _import_validity()
    grid = _FakeGrid(nodes={"A": _FakeNode(voltage=-1.0)})
    rep = check_run_validity(grid)
    assert not rep.valid


def test_validity_passes_normal_voltage():
    _, _, check_run_validity = _import_validity()
    grid = _FakeGrid(nodes={"A": _FakeNode(voltage=1.0),
                            "B": _FakeNode(voltage=0.98)})
    rep = check_run_validity(grid)
    assert rep.valid


def test_validity_flags_empty_topology():
    _, _, check_run_validity = _import_validity()
    grid = _FakeGrid(nodes={})
    rep = check_run_validity(grid)
    assert not rep.valid


# ── MetricCollector ─────────────────────────────────────────────────────
def test_metric_collector_records_fault_and_step():
    _, MetricCollector, _, _ = _import_research_metrics()

    grid = _FakeGrid(nodes={
        "A": _FakeNode(voltage=0.92),  # below 0.95 → violation
        "B": _FakeNode(voltage=1.0),
    })
    c = MetricCollector()
    c.record_fault(timestep=5, target="A", baseline_load_mw=1.0,
                   baseline_critical_mw=0.0)
    c.record_step(grid=grid, timestep=5, controller_action=1, action_legal=True)

    assert len(c.faults) == 1
    assert c.actions_taken == 1
    assert c.voltage_violation_count >= 1  # A is below 0.95 pu


def test_metric_collector_counts_illegal_actions():
    _, MetricCollector, _, _ = _import_research_metrics()
    grid = _FakeGrid(nodes={"A": _FakeNode()})
    c = MetricCollector()
    c.record_step(grid=grid, timestep=0, controller_action=0, action_legal=False)
    c.record_step(grid=grid, timestep=1, controller_action=0, action_legal=True)
    assert c.illegal_actions_attempted == 1
    assert c.actions_taken == 2


def test_metric_collector_mark_restoration_complete():
    _, MetricCollector, _, _ = _import_research_metrics()
    c = MetricCollector()
    c.record_fault(timestep=2, target="H01", baseline_load_mw=1.0,
                   baseline_critical_mw=0.0)
    c.mark_restoration_complete(fault_target="H01", timestep=10)
    rec = c.faults[0]
    assert rec.successful_restoration is True
    assert rec.restoration_timestep == 10
    assert rec.restoration_steps == 8


# ── Statistics module ───────────────────────────────────────────────────
def test_statistics_module_self_test_passes():
    from metrics import statistics
    assert statistics._self_test() is True


def test_paired_comparison_returns_reasonable_dict():
    from metrics.statistics import paired_comparison
    rep = paired_comparison([10, 20, 30, 40], [1, 2, 3, 4])
    for key in ("n", "mean_difference", "t_statistic", "t_p_value",
                "wilcoxon_p", "effect_size", "ci95_low", "ci95_high"):
        assert key in rep, f"missing key {key}"
    assert rep["n"] == 4
    # Mean difference is positive (A > B), p < 0.05 with n=4.
    assert rep["mean_difference"] > 0
    assert rep["t_p_value"] < 0.05


def test_paired_comparison_invalid_for_n_lt_2():
    from metrics.statistics import paired_comparison
    rep = paired_comparison([1.0], [2.0])
    assert rep["valid"] is False
    assert rep["reason"]


# ── Runner integration ──────────────────────────────────────────────────
def _tiny_scenario(seed: int = 0, total_steps: int = 10, fault_count: int = 1):
    _, _, make_scenario = _import_scenario()
    return make_scenario(
        seed=seed, total_steps=total_steps, fault_count=fault_count,
        weather_mode="normal", label=f"seed_{seed}",
    )


def test_runner_run_single_each_config():
    """For every pre-baked config, run_single must return a dict with the
    documented schema (config, scenario, validity, metrics)."""
    ExperimentConfig, ABLATION_CONFIGS = _import_experiment_config()
    run_single, _, _ = _import_runner()

    # Use a tiny scenario to keep the test fast.
    scenario = _tiny_scenario(seed=0, total_steps=6, fault_count=1)
    for label, cfg in ABLATION_CONFIGS.items():
        # Build a fresh config from the pre-baked one, override seed.
        cfg = ExperimentConfig(
            enable_dqn=cfg.enable_dqn,
            enable_lstm=cfg.enable_lstm,
            enable_twin=cfg.enable_twin,
            enable_predictive_healing=cfg.enable_predictive_healing,
            enable_reward_shaping=cfg.enable_reward_shaping,
            enable_flisr=cfg.enable_flisr,
            enable_ems=cfg.enable_ems,
            enable_storage=cfg.enable_storage,
            enable_xai=cfg.enable_xai,
            seed=7,
            label=label,
        )
        result = run_single(config=cfg, scenario=scenario)
        assert isinstance(result, dict)
        assert "config" in result
        assert "scenario" in result
        assert "validity" in result
        assert "metrics" in result
        assert "active_modules" in result["config"]
        assert "disabled_modules" in result["config"]


def test_runner_produces_json_file_for_all_configs():
    """End-to-end: run_experiment writes a JSON file that contains every
    pre-baked config's report."""
    ExperimentConfig, ABLATION_CONFIGS = _import_experiment_config()
    _, run_experiment, _ = _import_runner()

    configs = []
    for k in ("random", "rule_based", "no_lstm", "full_stack"):
        cfg = ABLATION_CONFIGS[k]
        configs.append(ExperimentConfig(
            enable_dqn=cfg.enable_dqn,
            enable_lstm=cfg.enable_lstm,
            enable_twin=cfg.enable_twin,
            enable_predictive_healing=cfg.enable_predictive_healing,
            enable_reward_shaping=cfg.enable_reward_shaping,
            enable_flisr=cfg.enable_flisr,
            enable_ems=cfg.enable_ems,
            enable_storage=cfg.enable_storage,
            enable_xai=cfg.enable_xai,
            seed=0,
            label=cfg.label,
        ))

    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "runner.json")
        manifest = os.path.join(td, "manifest.json")
        report = run_experiment(
            configs=configs,
            seeds=1,
            ticks=6,
            faults_per_run=1,
            weather_modes=["normal"],
            output_path=out,
            write_csv=False,
            write_manifest_path=manifest,
        )
        assert os.path.exists(out)
        assert os.path.exists(manifest)
        with open(out) as f:
            parsed = json.load(f)
        assert parsed["n_total"] == len(configs)
        # Every config is represented.
        labels = {r["controller_label"] for r in parsed["runs"]}
        assert labels == {"random", "rule_based", "no_lstm", "full_stack"}
        # Manifest captures all scenarios.
        with open(manifest) as f:
            m = json.load(f)
        assert m["n_runs"] == len(configs)


# ── Tables integration ──────────────────────────────────────────────────
def test_tables_module_emits_per_policy_and_paired():
    ExperimentConfig, ABLATION_CONFIGS = _import_experiment_config()
    _, run_experiment, _ = _import_runner()
    from experiments.tables import build_report, render_markdown

    configs = []
    for k in ("rule_based", "full_stack", "random"):
        cfg = ABLATION_CONFIGS[k]
        configs.append(ExperimentConfig(
            enable_dqn=cfg.enable_dqn,
            enable_lstm=cfg.enable_lstm,
            enable_twin=cfg.enable_twin,
            enable_predictive_healing=cfg.enable_predictive_healing,
            enable_reward_shaping=cfg.enable_reward_shaping,
            enable_flisr=cfg.enable_flisr,
            enable_ems=cfg.enable_ems,
            enable_storage=cfg.enable_storage,
            enable_xai=cfg.enable_xai,
            seed=0,
            label=cfg.label,
        ))
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "runner.json")
        manifest = os.path.join(td, "manifest.json")
        report = run_experiment(
            configs=configs,
            seeds=2,
            ticks=6,
            faults_per_run=1,
            weather_modes=["normal"],
            output_path=out,
            write_csv=False,
            write_manifest_path=manifest,
        )

    runs = report["runs"]
    tables = build_report(runs=runs, anchor_label="rule_based")
    assert "per_policy" in tables
    assert "paired" in tables
    # Per-policy has 3 entries (one per config).
    labels = {r["controller_label"] for r in tables["per_policy"]}
    assert labels == {"rule_based", "full_stack", "random"}
    # Markdown render does not crash and contains the anchor.
    md = render_markdown(tables)
    assert "rule_based" in md
    assert "Paired comparison" in md