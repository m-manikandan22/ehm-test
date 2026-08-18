"""test_experiments_framework.py — Smoke tests for the experiments harness.

These tests do not exercise the heavy RL stack. They only verify:
  - Each experiments/*.py module imports without crashing.
  - The runner / monte-carlo / aggregate write a JSON report.
  - The policy registry returns fresh instances.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys

import pytest


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXPERIMENTS_DIR = os.path.join(REPO_ROOT, "experiments")
sys.path.insert(0, REPO_ROOT)


def _load(name: str, rel_path: str):
    full = os.path.join(EXPERIMENTS_DIR, rel_path)
    spec = importlib.util.spec_from_file_location(name, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_runner_module_importable():
    if not os.path.exists(os.path.join(EXPERIMENTS_DIR, "runner.py")):
        pytest.skip("experiments/runner.py not yet created")
    mod = _load("ehm_runner_under_test", "runner.py")
    assert hasattr(mod, "run_experiment")
    assert hasattr(mod, "_safe_run_one")


def test_runner_smoke_produces_json(tmp_path):
    if not os.path.exists(os.path.join(EXPERIMENTS_DIR, "runner.py")):
        pytest.skip("experiments/runner.py not yet created")
    mod = _load("ehm_runner_under_test_2", "runner.py")
    out = tmp_path / "smoke.json"
    report = mod.run_experiment(
        policies=["random", "rule_based"],
        seeds=1,
        ticks=3,
        faults_per_run=1,
        output_path=str(out),
    )
    assert out.exists()
    with open(out) as f:
        parsed = json.load(f)
    assert parsed["schema_version"] == "1.0"
    assert "summary" in parsed
    # Every policy should have at least one valid run
    for name, s in parsed["summary"].items():
        assert s["n_runs"] >= 1, f"policy {name} produced no runs"


def test_runner_records_pf_diagnostic(tmp_path):
    """EHM-HIGH-005: every run_single output must include a
    `pf_diagnostic` block with DC PF convergence + KCL residual.
    """
    if not os.path.exists(os.path.join(EXPERIMENTS_DIR, "runner.py")):
        pytest.skip("experiments/runner.py not yet created")
    mod = _load("ehm_runner_under_test_pfd", "runner.py")
    from experiments.experiment_config import ExperimentConfig
    from experiments.scenario import make_scenario
    cfg = ExperimentConfig(label="random", seed=0)
    scen = make_scenario(seed=0, total_steps=3, fault_count=1)
    res = mod.run_single(config=cfg, scenario=scen)
    assert "pf_diagnostic" in res, "run_single must record pf_diagnostic"
    pf = res["pf_diagnostic"]
    assert "dc_converged" in pf
    assert "dc_kcl_residual_max" in pf
    assert "dc_bus_count" in pf
    # No NaN values should leak (we use sentinels instead)
    for k, v in pf.items():
        if isinstance(v, float):
            assert v == v, f"pf_diagnostic[{k!r}] is NaN"


def test_aggregate_roundtrip(tmp_path):
    runner = os.path.join(EXPERIMENTS_DIR, "runner.py")
    aggregator = os.path.join(EXPERIMENTS_DIR, "aggregate.py")
    if not (os.path.exists(runner) and os.path.exists(aggregator)):
        pytest.skip("Runner / aggregate not yet created")
    runner_mod = _load("ehm_runner_under_test_3", "runner.py")
    agg_mod = _load("ehm_agg_under_test", "aggregate.py")

    raw_out = tmp_path / "smoke.json"
    runner_mod.run_experiment(
        policies=["random", "rule_based"],
        seeds=2, ticks=3, faults_per_run=1,
        output_path=str(raw_out),
    )
    report_out = tmp_path / "agg.json"
    out = agg_mod.aggregate(str(raw_out), str(report_out))
    assert "per_policy_stats" in out
    assert os.path.exists(report_out)
    # MD sister file is created
    md_path = str(report_out).replace(".json", ".md")
    assert os.path.exists(md_path)


def test_monte_carlo_writes_json(tmp_path):
    mc = os.path.join(EXPERIMENTS_DIR, "monte_carlo.py")
    if not os.path.exists(mc):
        pytest.skip("experiments/monte_carlo.py not yet created")
    mod = _load("ehm_mc_under_test", "monte_carlo.py")
    out = tmp_path / "mc.json"
    res = mod.monte_carlo(
        policies=["random", "rule_based"],
        n_seeds=2,
        ticks=2,
        faults_per_run=1,
        output_path=str(out),
    )
    assert out.exists()
    for name, s in res["policy_stats"].items():
        assert s["n_valid"] >= 0
        for metric, stats in s["metrics"].items():
            assert "mean" in stats and "ci95" in stats


def test_topology_comparison_writes_json(tmp_path):
    script = os.path.join(EXPERIMENTS_DIR, "topology_comparison.py")
    if not os.path.exists(script):
        pytest.skip("topology_comparison.py not yet created")
    mod = _load("ehm_topo_under_test", "topology_comparison.py")
    out = tmp_path / "topo.json"
    res = mod.run_topology_comparison(seeds=1, ticks=2, output_path=str(out))
    assert out.exists()
    assert "random" in res["results"]
    assert "rule" in res["results"]
    assert "ai" in res["results"]


def test_predictive_vs_reactive_writes_json(tmp_path):
    script = os.path.join(EXPERIMENTS_DIR, "predictive_vs_reactive.py")
    if not os.path.exists(script):
        pytest.skip("predictive_vs_reactive.py not yet created")
    mod = _load("ehm_pvr_under_test", "predictive_vs_reactive.py")
    out = tmp_path / "pvr.json"
    res = mod.run_predictive_vs_reactive(
        seeds=2, ticks=3, fault_rate=0.05, output_path=str(out))
    assert out.exists()
    assert "saifi" in res and "saidi_hr" in res


def test_ablation_writes_json(tmp_path):
    script = os.path.join(EXPERIMENTS_DIR, "ablation.py")
    if not os.path.exists(script):
        pytest.skip("ablation.py not yet created")
    mod = _load("ehm_abl_under_test", "ablation.py")
    out = tmp_path / "abl.json"
    res = mod.run_ablation(seeds=2, ticks=2, faults_per_run=1,
                            output_path=str(out))
    assert out.exists()
    # Legacy alias ``ablations`` is still present so older consumers
    # continue to work; the canonical key is ``per_config``.
    assert "ablations" in res
    assert "per_config" in res
    # After PHASE 2, the ablation runner genuinely honours
    # ExperimentConfig booleans, so status must be "real".
    assert res["status"] == "real"


def test_ieee13_validation_via_runner(tmp_path):
    """Confirm the validation module is wired to the runner schema."""
    script = os.path.join(EXPERIMENTS_DIR, "ieee13_validation.py")
    if not os.path.exists(script):
        pytest.skip("ieee13_validation.py not yet created")
    mod = _load("ehm_ieee_under_test", "ieee13_validation.py")
    out = tmp_path / "ieee13.json"
    rep = mod.run_validation(str(out))
    assert out.exists()
    # The JSON has the schema key we want to verify
    with open(out) as f:
        parsed = json.load(f)
    assert "limitations" in parsed
    assert parsed["validation_status"] in ("demonstrative", "partial", "validated")
