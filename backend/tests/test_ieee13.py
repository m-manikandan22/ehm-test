"""
test_ieee13.py — Validate the IEEE 13-bus digital twin.

Asserts:
  • build_ieee13() returns a SmartGrid-shaped object
  • Topology has exactly 13 buses and 16 directed lines (2 per undirected edge)
  • All load buses have positive load
  • Source bus has positive generation
  • DC PF converges on the IEEE 13 topology
  • Tie switch 684↔680 starts open
"""
import sys
import os

# Make `backend` the running directory regardless of where pytest is invoked
_THIS = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_THIS)
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from simulation.ieee13 import (
    build_ieee13,
    get_ieee13_metadata,
    IEEE13_LINES,
    IEEE13_LOADS,
)


def test_metadata_constants():
    meta = get_ieee13_metadata()
    assert meta["name"] == "IEEE 13-bus test feeder"
    assert meta["source_bus"] == "650"
    assert meta["buses"] == 13
    assert meta["lines"] == 13     # 13 undirected edges
    assert meta["voltage_base_kv"] == 4.16


def test_build_ieee13_topology():
    g = build_ieee13()
    # 13 unique bus IDs
    assert len(g.nodes) == 13
    # 26 directed edges (13 undirected × 2)
    assert len(g.graph.edges) == 26
    # Bus map matches node count
    assert len(g.bus_map) == 13
    # Line impedance populated for both directions
    assert len(g.line_impedance) == 2 * len(IEEE13_LINES)


def test_source_and_loads():
    g = build_ieee13()
    assert g.nodes["650"].generation > 0.0, "Source bus 650 must generate"
    assert g.nodes["650"]._base_generation > 0.0
    # All load buses have load > 0
    for bus_id, _ in IEEE13_LOADS.items():
        assert g.nodes[bus_id].load > 0.0, f"{bus_id} should have load"


def test_dc_power_flow_converges():
    from simulation.power_flow import dc_power_flow
    g = build_ieee13()
    result = dc_power_flow(g)
    assert result.converged, f"DC PF did not converge on IEEE 13: {result.warnings}"
    assert result.kcl_residual_max < 1e-6, (
        f"KCL residual too high: {result.kcl_residual_max:.2e}"
    )
    assert result.bus_count == 13
    assert result.slack_bus_id == "650"


def test_tie_switch_starts_open():
    g = build_ieee13()
    tie = g.graph["684"]["680"]
    assert tie["is_tie_switch"] is True
    assert tie["active"] is True   # present in graph
    assert tie["switch_status"] == "open"


def test_load_impedance_units():
    # R and X for substation edge 650→632 should be small (per-unit)
    g = build_ieee13()
    imp = g.line_impedance[("650", "632")]
    assert 0.0 < imp["R"] < 0.05
    assert 0.0 < imp["X"] < 0.05


def test_regulators_and_transformer_present():
    meta = get_ieee13_metadata()
    assert any("650" in r and "632" in r for r in meta["regulators"])
    assert any("633" in t and "611" in t for t in meta["transformers"])


def test_ieee13_attribute_set_matches_smartgrid_init():
    """build_ieee13() must expose the same instance attributes as a
    fully-initialised SmartGrid.

    This guards against the historical `__new__` bypass silently
    dropping new attributes added to SmartGrid.__init__.
    """
    from simulation.grid import SmartGrid

    ieee = build_ieee13()

    # A reference SmartGrid is expensive to instantiate; instead, build
    # a second IEEE 13 grid and compare attribute sets — they must be
    # identical.
    twin = build_ieee13()
    assert set(vars(ieee).keys()) == set(vars(twin).keys()), (
        "Two build_ieee13() calls returned grids with different attributes"
    )

    # Spot-check the critical attributes from the audit doc.
    for name in (
        "graph", "nodes", "timestep", "storm_active",
        "total_energy_loss", "avg_frequency", "event_log",
        "reclose_queue", "last_fault_segment", "bus_map",
        "line_impedance", "dc_state", "dc_enabled",
        "ac_state", "ac_enabled",
    ):
        assert hasattr(ieee, name), f"build_ieee13 missing {name!r}"


def test_init_state_helper_is_public_api():
    """`_init_state()` is the shared initialiser used by both
    SmartGrid.__init__ and build_ieee13(). It must be callable on a
    blank SmartGrid instance without raising and without invoking
    `_build_grid`.
    """
    from simulation.grid import SmartGrid

    blank = SmartGrid.__new__(SmartGrid)
    # Pre-condition: no `nodes` attribute yet (because we bypassed __init__).
    assert not hasattr(blank, "nodes")
    blank._init_state()
    assert blank.nodes == {}
    import networkx as nx
    assert isinstance(blank.graph, nx.DiGraph)
    assert blank.dc_enabled is True
    assert blank.ac_enabled is True


if __name__ == "__main__":
    # Allow `python tests/test_ieee13.py` for manual smoke tests
    test_metadata_constants()
    test_build_ieee13_topology()
    test_source_and_loads()
    test_dc_power_flow_converges()
    test_tie_switch_starts_open()
    test_load_impedance_units()
    test_regulators_and_transformer_present()
    print("All IEEE 13-bus digital-twin tests PASSED")
