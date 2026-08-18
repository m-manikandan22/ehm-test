"""
test_dc_power_flow.py — Validation of the in-house DC power flow solver.

Tests the textbook 5-bus case and the EHM 49-bus grid end-to-end.
"""
import math

import numpy as np

from simulation.grid import SmartGrid
from simulation.power_flow import dc_power_flow, _self_test_5bus


def test_textbook_5bus():
    """Build the canonical 5-bus case inside the solver and verify KCL."""
    assert _self_test_5bus(), "5-bus self-test failed"


def test_ehm_grid_dc_pf():
    g = SmartGrid()
    res = dc_power_flow(g)
    assert res.converged, f"DC PF did not converge: {res.warnings}"
    assert res.kcl_residual_max < 1e-6
    assert res.bus_count == 49
    # Slack bus must have angle 0
    assert abs(res.bus_angle_deg[res.slack_bus_id]) < 1e-6
    # All line flows should be finite
    for k, p in res.line_flow_mw.items():
        assert math.isfinite(p), f"non-finite flow on {k}: {p}"
        assert math.isfinite(res.line_current_a[k]), f"non-finite I on {k}"
        assert math.isfinite(res.line_loss_mw[k]), f"non-finite loss on {k}"
    # Losses non-negative
    for k, l in res.line_loss_mw.items():
        assert l >= 0.0, f"negative loss on {k}: {l}"


def test_dc_pf_handles_islanding():
    """Isolate all of Feeder B and verify the solver skips the island cleanly."""
    g = SmartGrid()
    for nid in ["P_B1", "P_B2", "P_B3", "HOSP"]:
        if nid in g.nodes:
            g.inject_failure(nid)
    g.update_power_flow()
    res = g.get_dc_state()
    assert res, "DC PF did not produce a result with isolated Feeder B"
    # DC PF should still converge (maybe with warnings)
    assert res["kcl_residual_max"] < 1e-6


def test_dc_pf_multi_island_robust():
    """Cut the grid into multiple islands; each component must solve
    independently and KCL must hold on every component. Regression test
    for the bug where the old solver fell back to lstsq and got ~5e-2
    residuals when the global B-matrix was singular."""
    g = SmartGrid()
    # Cut a critical feeder-head to fragment the grid into multiple islands
    for u, v in [("S_MAIN", "T_A"), ("S_MAIN", "T_B"), ("S_MAIN", "T_C")]:
        if g.graph.has_edge(u, v):
            g.graph[u][v]["active"] = False
        if g.graph.has_edge(v, u):
            g.graph[v][u]["active"] = False
    # Now add the source-side generators and S_MAIN should still be solved
    g.update_power_flow()
    res = g.get_dc_state()
    assert res["converged"], f"DC PF did not converge: {res['warnings']}"
    assert res["kcl_residual_max"] < 1e-6, (
        f"KCL residual {res['kcl_residual_max']:.3e} > 1e-6; "
        f"warnings: {res['warnings']}"
    )


def test_dc_pf_each_island_has_angle():
    """After islanding, every powered bus should have an angle. The global
    slack retains angle 0; each new island gets its own local slack."""
    g = SmartGrid()
    for u, v in [("S_MAIN", "T_B"), ("S_MAIN", "T_C")]:
        if g.graph.has_edge(u, v):
            g.graph[u][v]["active"] = False
        if g.graph.has_edge(v, u):
            g.graph[v][u]["active"] = False
    g.update_power_flow()
    res = g.get_dc_state()
    # Active buses = not failed AND not isolated
    active_buses = [nid for nid, n in g.nodes.items()
                    if not n.failed and not n.isolated]
    for nid in active_buses:
        assert nid in res["bus_angle_deg"], (
            f"Active bus {nid} missing from DC PF angles"
        )


def test_dc_pf_overlay_sets_edge_attributes():
    g = SmartGrid()
    g.update_power_flow()
    # At least one edge should have a current_a attribute
    has_i = any("current_a" in d for _, _, d in g.graph.edges(data=True))
    assert has_i, "DC PF did not overlay 'current_a' on any edge"
    has_loss = any("loss_mw" in d for _, _, d in g.graph.edges(data=True))
    assert has_loss, "DC PF did not overlay 'loss_mw' on any edge"


def test_get_dc_state_returns_empty_when_not_run():
    g = SmartGrid.__new__(SmartGrid)   # bypass __init__
    import networkx as nx
    g.graph = nx.DiGraph()
    g.nodes = {}
    g.bus_map = {}
    g.line_impedance = {}
    g.dc_state = None
    assert g.get_dc_state() == {}


def test_per_node_voltage_angle_populated():
    g = SmartGrid()
    g.update_power_flow()
    # At least one bus (the slack) should be exactly 0.0
    slack = g.dc_state.slack_bus_id
    assert abs(g.nodes[slack].voltage_angle) < 1e-9
    # And at least one other bus should have a non-zero angle
    has_nonzero = any(
        abs(n.voltage_angle) > 1e-4
        for nid, n in g.nodes.items()
        if nid != slack
    )
    assert has_nonzero, "No non-trivial angles populated on non-slack buses"
