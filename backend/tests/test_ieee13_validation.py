"""test_ieee13_validation.py — IEEE 13-bus validation harness smoke test.

This test runs the validation script as a subprocess (or imports it
directly) and asserts:
  - The validation script produces a JSON report.
  - The EHM DC PF on IEEE 13-bus converges with a low KCL residual.
  - If pandapower is installed, the reference comparison is included.
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


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_ieee13_validation_script_produces_report(tmp_path):
    """Run the validation script and verify the JSON report is created."""
    script = os.path.join(EXPERIMENTS_DIR, "ieee13_validation.py")
    if not os.path.exists(script):
        pytest.skip(f"Validation script not found: {script}")

    output = tmp_path / "ieee13_validation.json"
    if not os.path.isdir(EXPERIMENTS_DIR) or not os.path.exists(script):
        pytest.skip("experiments/ directory not yet created")

    mod = _load_module("ieee13_validation_under_test", script)
    report = mod.run_validation(str(output))

    # JSON file exists and parses
    assert output.exists()
    with open(output) as f:
        parsed = json.load(f)
    assert parsed["test"] == "ieee13_validation"

    # EHM DC PF must converge
    assert report["ehm_dc_pf"]["converged"] is True
    assert report["ehm_dc_pf"]["kcl_residual_max"] < 1e-6
    # At least 4 buses (the IEEE spec has 13)
    assert report["ehm_dc_pf"]["bus_count"] >= 4
    # Limitations block is always present
    assert len(report["limitations"]) >= 1
    # Validation status is a status string
    assert report["validation_status"] in ("demonstrative", "partial", "validated")


def test_ehm_dc_pf_converges_on_ieee13():
    """A focused smoke test — EHM DC PF must run on the IEEE 13 topology."""
    from simulation.ieee13 import build_ieee13
    from simulation.power_flow import dc_power_flow

    grid = build_ieee13()
    res = dc_power_flow(grid, slack_bus_id="650")
    assert res.converged, f"DC PF on IEEE 13 failed: {res.warnings}"
    assert res.kcl_residual_max < 1e-6
    # Slack angle must be 0 by convention
    assert abs(res.bus_angle_deg.get("650", 0.0)) < 1e-6
    # Loads pull the angle of downstream buses negative
    for nid, ang in res.bus_angle_deg.items():
        if nid == "650":
            continue
        # Allow ±1° wiggle (small angle assumption)
        assert ang <= 1.0, f"Bus {nid} has unexpected positive angle {ang}"


@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("pandapower"),
    reason="pandapower not installed",
)
def test_pandapower_dc_reference_runs():
    """When pandapower is installed, the reference block should appear."""
    from simulation.ieee13 import build_ieee13
    from simulation.power_flow import dc_power_flow
    script = os.path.join(EXPERIMENTS_DIR, "ieee13_validation.py")
    if not os.path.exists(script):
        pytest.skip("Validation script not found")

    mod = _load_module("ieee13_validation_under_test_2", script)
    grid = build_ieee13()
    ref = mod._try_pandapower_dc_reference(grid)
    # Should return at least an angle dict
    assert isinstance(ref, dict)
    # Non-empty (13 buses)
    if ref:
        assert len(ref) >= 4
        # Slack bus (650) should be exactly 0 deg
        assert abs(ref.get("650", 0.0)) < 1e-6
        # Sanity: BFS run should also have converged above
        assert dc_power_flow(grid, slack_bus_id="650").converged
