"""Execution-path validation for corrected Experiment B (deterministic)."""
import os
import sys
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from simulation.grid import SmartGrid
from simulation.scada import ScadaControlCenter
from experiments.experiment_config import ABLATION_CONFIGS, ExperimentConfig
from experiments.stress_runner import _dispatch_predictive_action, run_stress_single
from experiments.stress_scenario import make_stress_scenario, validate_scenario_physical


def test_policy_count_is_nine_and_ids_are_unique():
    assert len(ABLATION_CONFIGS) == 9
    fingerprints = {json.dumps(c.to_dict(), sort_keys=True) for c in ABLATION_CONFIGS.values()}
    assert len(fingerprints) == 9


def test_paired_seed_reproducibility_and_targets_are_real():
    a = make_stress_scenario(seed=7, stress_level="moderate", total_steps=40)
    b = make_stress_scenario(seed=7, stress_level="moderate", total_steps=40)
    assert a.to_dict()["faults"] == b.to_dict()["faults"]
    assert validate_scenario_physical(a, list(SmartGrid().nodes))[0]


def test_flisr_is_invoked_and_changes_network_state_when_feasible():
    grid = SmartGrid()
    owner = ScadaControlCenter.__new__(ScadaControlCenter)
    grid.inject_failure("P_A2")
    pre = sum(n.load for n in grid.nodes.values() if n.failed or n.isolated)
    trace = owner._flisr_restore(grid)
    post = sum(n.load for n in grid.nodes.values() if n.failed or n.isolated)
    assert any(e["step"] == "RESTORE" and e["status"] == "ok" for e in trace["flisr_log"])
    assert post < pre


def test_no_flisr_ablation_disables_flisr():
    scenario = make_stress_scenario(seed=2, stress_level="moderate", total_steps=12)
    result = run_stress_single(config=ExperimentConfig.random_baseline(), scenario=scenario)
    counts = result["module_call_counts"]
    assert counts["flisr_calls"] == 0
    assert counts["flisr_requests"] == 0


def test_predictive_action_dispatch_path():
    grid = SmartGrid()
    assert _dispatch_predictive_action(grid, {"kind": "add_tie_switch", "params": {"u": "P_A1", "v": "P_A3"}})
    assert grid.graph["P_A1"]["P_A3"]["active"]


def test_twin_and_lstm_activation_contracts():
    full = ExperimentConfig.full_stack().to_dict()
    no_twin = ExperimentConfig.no_twin().to_dict()
    no_lstm = ExperimentConfig.no_lstm().to_dict()
    assert "digital_twin" in full["active_modules"] and "digital_twin" in no_twin["disabled_modules"]
    assert "lstm" in full["active_modules"] and "lstm" in no_lstm["disabled_modules"]
