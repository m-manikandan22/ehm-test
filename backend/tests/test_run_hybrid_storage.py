"""test_run_hybrid_storage.py — Stage 21 hybrid-storage smoke test."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.run_hybrid_storage import run, POLICIES   # noqa: E402


def test_all_policies_present_in_results():
    out = run(scenario_seed=0, total_steps=20, fault_count=2)
    labels = {r["policy"] for r in out["results"]}
    assert labels == set(POLICIES)


def test_metrics_are_non_negative():
    out = run(scenario_seed=0, total_steps=20, fault_count=2)
    for r in out["results"]:
        assert r["energy_not_served_mwh"] >= 0.0
        assert r["customer_minutes_interrupted"] >= 0.0
        assert r["n_recoveries"] >= 0
        assert r["n_steps"] >= 0


def test_summary_string_lists_all_policies():
    out = run(scenario_seed=0, total_steps=20, fault_count=2)
    for p in POLICIES:
        assert p in out["summary"]


def test_run_writes_json_when_path_given():
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as t:
        path = Path(t.name)
    try:
        out = run(scenario_seed=0, total_steps=20, fault_count=2,
                  write_path=path)
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert data["scenario_seed"] == 0
        assert len(data["results"]) == len(POLICIES)
    finally:
        if path.exists():
            path.unlink()


def test_different_seed_changes_fault_targets_only_not_policy():
    """Different seeds should NOT change the structure of the output
    (number of policies, schema) — only the per-policy metrics."""
    out_a = run(scenario_seed=0, total_steps=20, fault_count=2)
    out_b = run(scenario_seed=1, total_steps=20, fault_count=2)
    assert len(out_a["results"]) == len(out_b["results"])
    assert {r["policy"] for r in out_a["results"]} == \
           {r["policy"] for r in out_b["results"]}