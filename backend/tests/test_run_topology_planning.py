"""test_run_topology_planning.py — Stage 22 experiment script smoke test."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make sure backend root is on the path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.run_topology_planning import run  # noqa: E402


def test_run_returns_serialisable_dict():
    """Smoke: produce a result dict without raising, with valid schema."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    out = run(max_iterations=4, write_path=tmp_path)
    # Schema
    for k in ("seed", "max_iterations", "n_nodes", "n_actions",
              "kpis_before", "kpis_after", "actions", "summary"):
        assert k in out, f"Missing key {k!r} in run() output"
    # kpis_before should have the four KPIs from topology_kpis.all_kpis
    for k in ("avg_path_length", "mesh_index",
              "redundancy_score", "articulation_count"):
        assert k in out["kpis_before"], f"Missing baseline KPI {k!r}"
    # The result file should now exist
    assert tmp_path.exists()
    with open(tmp_path, "r", encoding="utf-8") as f:
        on_disk = json.load(f)
    assert on_disk["n_nodes"] == out["n_nodes"]
    assert on_disk["actions"] == out["actions"]


def test_run_is_deterministic():
    """Two runs on the *same grid state* must produce identical actions.

    Note: ``SmartGrid()`` itself is non-deterministic (each instance is
    randomly initialised), so we capture one grid and reuse it for both
    planner runs to isolate planner determinism from SmartGrid init.
    """
    import copy
    import tempfile
    from simulation.grid import SmartGrid

    g = SmartGrid()
    # Capture baseline grid state by deep-copying nodes
    snapshot = {
        nid: {k: getattr(n, k, None) for k in
              ("load", "generation", "battery_level", "supercap_level",
               "voltage", "failed", "isolated", "weather", "priority")}
        for nid, n in g.nodes.items()
    }

    def run_with_snapshot():
        # restore node state to baseline
        for nid, n in g.nodes.items():
            for k, v in snapshot[nid].items():
                try:
                    setattr(n, k, v)
                except Exception:
                    pass
        from planning.ai_planner import AIPlanner, PlannerConfig
        cfg = PlannerConfig(max_iterations=4)
        planner = AIPlanner(g, config=cfg, seed=42)
        return [a.to_dict() for a in planner.plan()]

    actions_a = run_with_snapshot()
    actions_b = run_with_snapshot()
    assert actions_a == actions_b, (
        "Topology planner should be deterministic for the same grid state"
    )


def test_run_produces_non_negative_articulation_count():
    """Sanity: articulation_count >= 0 and mesh_index in [0, 2]."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    out = run(max_iterations=2, write_path=tmp_path)
    assert out["kpis_before"]["articulation_count"] >= 0
    assert 0.0 <= out["kpis_before"]["mesh_index"] <= 2.0
    assert 0.0 <= out["kpis_before"]["redundancy_score"] <= 1.0


def test_run_actions_have_expected_delta_key():
    """Each accepted action must record an ``expected_delta``."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    out = run(max_iterations=2, write_path=tmp_path)
    for act in out["actions"]:
        assert "kind" in act
        assert "params" in act
        assert "expected_delta" in act