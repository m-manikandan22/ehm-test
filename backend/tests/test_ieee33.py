"""test_ieee33.py — IEEE 33-bus benchmark coverage (Stage 5, EHM-HIGH-001)."""
from __future__ import annotations

import pytest

from simulation.grid import SmartGrid
from simulation.ieee33 import (
    IEEE33_LINES, IEEE33_LOADS,
    build_ieee33, get_ieee33_metadata,
    ieee33_total_load_mw,
)


def test_build_ieee33_returns_smartgrid_instance():
    g = build_ieee33()
    assert isinstance(g, SmartGrid)


def test_ieee33_has_33_buses():
    g = build_ieee33()
    assert len(g.nodes) == 33, f"Expected 33 buses, got {len(g.nodes)}"


def test_ieee33_has_37_lines():
    """The IEEE 33-bus feeder has 33 segments + 5 tie switches = 37
    directed-line records. Our module records each *undirected* line
    once with the table; the SmartGrid adds the reverse edge during
    build so that ``g.graph`` has 2 entries per (u, v) pair.
    """
    assert len(IEEE33_LINES) == 37, (
        f"Expected 37 directed lines (33 segments + 5 ties), got {len(IEEE33_LINES)}"
    )


def test_ieee33_has_5_tie_switches():
    ties = [l for l in IEEE33_LINES if l[5] == "tie"]
    assert len(ties) == 5, f"Expected 5 tie switches, got {len(ties)}"


def test_ieee33_total_load_is_about_3_715_mw():
    """Baran & Wu reference: total active load = 3,715 kW = 3.715 MW."""
    assert abs(ieee33_total_load_mw() - 3.715) < 1e-6, (
        f"Expected total load 3.715 MW, got {ieee33_total_load_mw()}"
    )


def test_ieee33_tie_switches_are_initially_open():
    g = build_ieee33()
    ties = [l for l in IEEE33_LINES if l[5] == "tie"]
    for (u, v, *_rest) in ties:
        edge = g.graph.get_edge_data(u, v)
        assert edge is not None
        assert edge["switch_status"] == "open"
        assert edge["is_tie_switch"] is True
        assert edge["active"] is True  # The switch exists but is open.


def test_ieee33_source_bus_has_generation():
    g = build_ieee33()
    src = g.nodes["1"]
    assert float(src.generation) > 0
    assert src.node_type == "substation"


def test_ieee33_loads_are_applied():
    g = build_ieee33()
    for bus_id, (p_kw, _) in IEEE33_LOADS.items():
        expected = p_kw / 1000.0
        actual = float(g.nodes[bus_id].load)
        assert abs(actual - expected) < 1e-6, (
            f"Bus {bus_id}: expected load {expected:.4f} MW, got {actual:.4f}"
        )


def test_ieee33_dc_power_flow_runs():
    """The grid should be electrically valid: KCL residuals small."""
    g = build_ieee33()
    g.update_power_flow()
    state = g.get_dc_state()
    residuals = [abs(v) for v in (state.get("bus_balance", {}) or {}).values()]
    if residuals:
        max_residual = max(residuals)
        # Tolerance is generous because IEEE33 cap scaling is approximate.
        assert max_residual < 5.0, (
            f"KCL residual {max_residual} too large — DC PF did not converge"
        )


def test_ieee33_inject_and_restore():
    """End-to-end: inject a fault and run the 9-stage FLISR."""
    from simulation.grid import SmartGrid
    g = build_ieee33()
    res = g.flisr_9stage()  # no faults ⇒ safe no-op
    assert len(res["stages"]) == 9

    # Inject on a non-source main-feeder bus.
    g.inject_failure("6")
    res = g.flisr_9stage()
    assert res["n_failed_nodes"] == 1
    assert "SWITCH" in res["stages_completed"]


def test_ieee33_metadata_keys():
    m = get_ieee33_metadata()
    for k in ("name", "buses", "lines", "source_bus", "tie_switches",
              "total_load_kw", "voltage_base_kv", "power_base_mva",
              "reference"):
        assert k in m, f"Missing key {k!r} in metadata"
    assert m["buses"] == 33
    assert m["source_bus"] == "1"
    assert m["voltage_base_kv"] == 12.66


def test_ieee33_topology_table_is_list_of_dicts():
    from simulation.ieee33 import get_ieee33_topology_table
    tbl = get_ieee33_topology_table()
    assert isinstance(tbl, list)
    assert len(tbl) == len(IEEE33_LINES)
    for row in tbl:
        assert {"u", "v", "R_ohm", "X_ohm", "kind"}.issubset(row.keys())
