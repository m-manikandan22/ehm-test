"""Test the results_sanity module."""
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def test_passes_on_valid_summary(tmp_path):
    """A summary.json with valid_rate=1.0 should pass sanity."""
    summary = {"n_total_runs": 10, "n_valid_runs": 10, "valid_rate": 1.0}
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps(summary))
    out_path = tmp_path / "sanity.json"
    proc = subprocess.run(
        [sys.executable, "-m", "experiments.results_sanity",
         "--input", str(summary_path), "--output", str(out_path)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out_path.read_text())
    assert data["overall_pass"] is True
    assert any(c["metric"] == "valid_rate" for c in data["checks"])


def test_valid_rate_out_of_bounds_fails(tmp_path):
    """A valid_rate > 1.0 should fail."""
    summary = {"n_total_runs": 10, "n_valid_runs": 10, "valid_rate": 1.5}
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps(summary))
    out_path = tmp_path / "sanity.json"
    proc = subprocess.run(
        [sys.executable, "-m", "experiments.results_sanity",
         "--input", str(summary_path), "--output", str(out_path)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 1
    data = json.loads(out_path.read_text())
    assert data["overall_pass"] is False


def test_no_output_flag_prints_to_stdout(tmp_path):
    """Without --output, JSON should be printed to stdout."""
    summary = {"n_total_runs": 1, "n_valid_runs": 1, "valid_rate": 1.0}
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps(summary))
    proc = subprocess.run(
        [sys.executable, "-m", "experiments.results_sanity",
         "--input", str(summary_path)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert "overall_pass" in data
    assert "checks" in data
