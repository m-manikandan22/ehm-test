"""test_ac_power_flow.py — Regression tests for the AC PF wrapper.

These tests pin down two contracts:

  1. When pandapower is *not* installed, ``run_ac_power_flow`` returns
     an ``ACPFResult(converged=False)`` with a clear ``error`` reason.
     This keeps the AC PF path failure-tolerant across environments.

  2. When pandapower is installed, the textbook 5-bus solve converges
     and the resulting bus voltages are in a sensible range.
"""
from __future__ import annotations

import pytest


# ── 1. Graceful failure when pandapower is missing ──────────────────────
def test_graceful_when_pandapower_missing(monkeypatch):
    """Force the import guard to fail and assert the result is informative."""
    from simulation import ac_power_flow as acpf

    monkeypatch.setattr(acpf, "PANDAPOWER_AVAILABLE", False)
    monkeypatch.setattr(acpf, "pp", None)

    class _Grid:
        graph = None
        nodes = {}

    res = acpf.run_ac_power_flow(_Grid())
    assert res.converged is False
    assert res.error is not None
    assert "pandapower" in res.error.lower()


# ── 2. Textbook 5-bus solve when pandapower IS installed ────────────────
@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("pandapower"),
    reason="pandapower not installed",
)
def test_5bus_ac_pf_converges():
    import networkx as nx

    from simulation.ac_power_flow import PANDAPOWER_AVAILABLE, run_ac_power_flow

    class _N:
        def __init__(self, nid, gen=0.0, load=0.0, t="bus"):
            self.node_id = nid
            self.node_type = t
            self.generation = gen
            self.load = load
            self.failed = False
            self.isolated = False

    nodes = {
        "B1": _N("B1", t="generator"),
        "B2": _N("B2", load=1.0),
        "B3": _N("B3"),
        "B4": _N("B4", load=0.5),
        "B5": _N("B5", load=1.5),
    }
    edges = [
        ("B1", "B2", 0.01, 0.1),
        ("B1", "B4", 0.01, 0.1),
        ("B2", "B3", 0.01, 0.1),
        ("B3", "B5", 0.01, 0.1),
        ("B4", "B5", 0.01, 0.1),
    ]
    G = nx.DiGraph()
    for nid in nodes:
        G.add_node(nid)
    for u, v, r, x in edges:
        G.add_edge(u, v, resistance=r, reactance=x, active=True)
        G.add_edge(v, u, resistance=r, reactance=x, active=True)

    class _Grid:
        pass

    g = _Grid()
    g.graph = G
    g.nodes = nodes
    g.line_impedance = {(u, v): {"R": r, "X": x} for u, v, r, x in edges}

    assert PANDAPOWER_AVAILABLE, "pandapower must be present for this test"
    res = run_ac_power_flow(g, slack_bus_id="B1")
    assert res.converged, f"AC PF did not converge: {res.error}"
    # Slack is forced to 1.02 by the wrapper
    assert 1.00 <= res.bus_voltage_pu["B1"] <= 1.05
    # Every bus inside a sane window
    for nid, v in res.bus_voltage_pu.items():
        assert 0.85 <= v <= 1.15, f"Bus {nid} voltage {v} out of range"
    # Lines have non-zero flows
    assert any(abs(p) > 1e-6 for p in res.line_flow_mw.values()), \
        "Expected non-zero power flows on lines"


# ── 3. SmartGrid integration test (ac_state + update_ac_power_flow) ─────
def test_smartgrid_ac_state_default_unavailable():
    """A fresh SmartGrid has ``ac_state == None`` and exposes ac_state API."""
    from simulation.grid import SmartGrid
    g = SmartGrid()
    # Default is None (no AC PF run yet)
    assert g.ac_state is None
    out = g.get_ac_state()
    assert out["available"] is False
    assert "reason" in out
