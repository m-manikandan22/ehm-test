"""Test the performance module."""
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def test_writes_perf_json(tmp_path):
    """Smoke test: perf.py should write a JSON file with all expected keys."""
    out = tmp_path / "perf.json"
    proc = subprocess.run(
        [sys.executable, "-m", "experiments.performance",
         "--seeds", "1", "--ticks", "5", "--faults", "1",
         "--output", str(out)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text())
    assert "schema_version" in data
    assert "dc_power_flow_avg_s" in data
    assert "flisr_9stage_avg_s" in data
    assert "paper_experiment_total_s" in data
    # dqn and lstm returns either a float (success) or dict with "error"
    for k in ("dqn_act_avg_s", "lstm_forward_avg_s"):
        v = data[k]
        assert isinstance(v, (int, float, dict))
    # dc_power_flow_avg_s should be a positive number
    assert isinstance(data["dc_power_flow_avg_s"], (int, float))
    assert data["dc_power_flow_avg_s"] > 0
