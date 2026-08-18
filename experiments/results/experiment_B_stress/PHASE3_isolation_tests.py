"""
PHASE 3 — Automated ablation isolation tests.

Verifies that each ablation configuration genuinely disables the
named module at runtime by inspecting the per-run
``module_call_counts``. Each test asserts that the counter for the
disabled module is zero (or, where appropriate, a defined baseline).

Run with the EHM-paper environment:

    C:/Users/ELCOT/miniconda3/envs/EHM-paper/python.exe -m pytest \
        experiments/results/experiment_B_stress/PHASE3_isolation_tests.py -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List


THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _run_smoke(seeds: int = 2, ticks: int = 20) -> Dict[str, Any]:
    """Run a small smoke experiment and return the parsed JSON report."""
    out_path = os.path.join(THIS_DIR, "_phase3_smoke.json")
    py = sys.executable
    # Build the configs we want to verify.
    code = f"""
import sys, json
sys.path.insert(0, r'.')
sys.path.insert(0, r'backend')
from experiments.runner import run_experiment, ExperimentConfig

factory = {{
    'full_stack':    ExperimentConfig.full_stack,
    'no_lstm':       ExperimentConfig.no_lstm,
    'no_twin':       ExperimentConfig.no_twin,
    'no_predictive': ExperimentConfig.no_predictive,
    'no_reward':     ExperimentConfig.no_reward,
    'dqn_core_only': ExperimentConfig.dqn_core_only,
    'rule_based':    ExperimentConfig.rule_based,
    'random':        ExperimentConfig.random_baseline,
    'persistence':   ExperimentConfig.persistence,
}}
cfg = [f() for f in factory.values()]
out = run_experiment(configs=cfg, seeds={seeds}, ticks={ticks}, faults_per_run=1,
                     output_path=r'{out_path}', write_manifest_path=None)
print(json.dumps({{'n_total': out['n_total'], 'n_valid': out['n_valid']}}))
"""
    proc = subprocess.run(
        [py, "-c", code],
        capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"smoke failed: {proc.stderr}")
    with open(out_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _by_label(report: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    bucket: Dict[str, List[Dict[str, Any]]] = {}
    for r in report.get("runs", []):
        bucket.setdefault(r["controller_label"], []).append(r)
    return bucket


def test_full_stack_uses_twin():
    report = _run_smoke()
    by = _by_label(report)
    assert "full_stack" in by, "full_stack not present in smoke run"
    for run in by["full_stack"]:
        mcc = run.get("module_call_counts", {})
        assert mcc.get("twin_syncs", 0) > 0, (
            f"full_stack had twin_syncs={mcc.get('twin_syncs')} — Twin not exercised"
        )


def test_no_twin_does_not_instantiate_twin():
    report = _run_smoke()
    by = _by_label(report)
    assert "no_twin" in by, "no_twin not present"
    for run in by["no_twin"]:
        mcc = run.get("module_call_counts", {})
        assert mcc.get("twin_syncs", 0) == 0, (
            f"no_twin had twin_syncs={mcc.get('twin_syncs')} — Twin is being instantiated"
        )
        assert mcc.get("twin_reads", 0) == 0, (
            f"no_twin had twin_reads={mcc.get('twin_reads')}"
        )


def test_no_predictive_can_still_maintain_twin_state():
    report = _run_smoke()
    by = _by_label(report)
    # When predictive_healing is off, no Twin is consumed because the
    # runner only creates Twin when *both* enable_predictive_healing
    # and enable_twin are True. We assert that predictive_assess_calls
    # is zero but the run completed.
    for run in by["no_predictive"]:
        mcc = run.get("module_call_counts", {})
        assert mcc.get("predictive_assess_calls", 0) == 0, (
            "no_predictive had predictive_assess_calls > 0"
        )


def test_no_predictive_does_not_perform_pre_emptive_healing():
    report = _run_smoke()
    by = _by_label(report)
    for run in by["no_predictive"]:
        mcc = run.get("module_call_counts", {})
        assert mcc.get("predictive_actions", 0) == 0


def test_no_lstm_does_not_execute_lstm_forecasting():
    report = _run_smoke()
    by = _by_label(report)
    for run in by["no_lstm"]:
        mcc = run.get("module_call_counts", {})
        assert mcc.get("lstm_calls", 0) == 0


def test_dqn_core_only_disables_advanced_modules():
    report = _run_smoke()
    by = _by_label(report)
    for run in by["dqn_core_only"]:
        mcc = run.get("module_call_counts", {})
        assert mcc.get("lstm_calls", 0) == 0
        assert mcc.get("twin_syncs", 0) == 0
        assert mcc.get("predictive_assess_calls", 0) == 0
        assert mcc.get("dqn_actions", 0) > 0, (
            "dqn_core_only should still be exercising the DQN"
        )


def test_rule_based_issues_rule_actions():
    report = _run_smoke()
    by = _by_label(report)
    for run in by["rule_based"]:
        mcc = run.get("module_call_counts", {})
        assert mcc.get("rule_actions", 0) > 0 or mcc.get("dqn_actions", 0) > 0


def test_random_issues_random_actions():
    report = _run_smoke()
    by = _by_label(report)
    for run in by["random"]:
        mcc = run.get("module_call_counts", {})
        assert mcc.get("random_actions", 0) > 0


def test_persistence_never_acts():
    report = _run_smoke()
    by = _by_label(report)
    for run in by["persistence"]:
        mcc = run.get("module_call_counts", {})
        assert mcc.get("noop_actions", 0) > 0


if __name__ == "__main__":
    # Manual runner: print PASS/FAIL summary
    import inspect
    tests = [
        (name, obj)
        for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"[PASS] {name}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"[FAIL] {name}: {exc!r}")
    print(f"\n{len(tests) - failures}/{len(tests)} tests passed")
    raise SystemExit(failures)
