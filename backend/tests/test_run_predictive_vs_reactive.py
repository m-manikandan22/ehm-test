"""Test the predictive vs reactive CLI script."""
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def test_runs_without_error_smoke():
    """Smoke test: run the script with --seed and verify it exits 0."""
    proc = subprocess.run(
        [sys.executable, "-m", "experiments.run_predictive_vs_reactive",
         "--seed", "1", "--faults", "1"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert "reactive" in out
    assert "predictive" in out
    assert "delta" in out
    assert out["seed"] == 1


def test_writes_out_file(tmp_path):
    """When --out is passed, file should be written."""
    out_path = tmp_path / "comp.json"
    proc = subprocess.run(
        [sys.executable, "-m", "experiments.run_predictive_vs_reactive",
         "--seed", "2", "--faults", "2", "--out", str(out_path)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert "reactive" in data
    assert "predictive" in data
    assert data["n_faults"] == 2


def test_same_seed_produces_same_targets():
    """Same seed → same fault targets."""
    out1 = subprocess.run(
        [sys.executable, "-m", "experiments.run_predictive_vs_reactive",
         "--seed", "7", "--faults", "3"],
        cwd=str(REPO), capture_output=True, text=True, timeout=60,
    )
    out2 = subprocess.run(
        [sys.executable, "-m", "experiments.run_predictive_vs_reactive",
         "--seed", "7", "--faults", "3"],
        cwd=str(REPO), capture_output=True, text=True, timeout=60,
    )
    j1 = json.loads(out1.stdout)
    j2 = json.loads(out2.stdout)
    assert j1["fault_targets"] == j2["fault_targets"]
