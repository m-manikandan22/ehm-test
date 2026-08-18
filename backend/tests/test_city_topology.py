"""test_city_generator.py — procedural city generator end-to-end test."""
from __future__ import annotations

import pytest

from city.city_generator import CityGenerator
from city.city_profile import CityProfile
from city.road_network import RoadNetwork
from city.zoning import Zoning


def test_road_network_deterministic():
    a = RoadNetwork(rows=4, cols=4, seed=42)
    b = RoadNetwork(rows=4, cols=4, seed=42)
    assert sorted(a.graph.nodes) == sorted(b.graph.nodes)
    assert sorted(a.graph.edges) == sorted(b.graph.edges)


def test_road_network_has_avenue_edge():
    rn = RoadNetwork(rows=4, cols=4, seed=42)
    kinds = [d.get("kind") for _, _, d in rn.graph.edges(data=True)]
    assert "avenue" in kinds


def test_zoning_covers_all_blocks():
    rn = RoadNetwork(rows=4, cols=4, seed=42)
    p = CityProfile(population=50_000)
    z = Zoning(rn, p, seed=42)
    assert set(z.zones.keys()) == set(rn.graph.nodes)
    allowed = {"residential", "industrial", "commercial", "critical"}
    assert set(z.zones.values()) <= allowed


def test_generator_returns_smartgrid():
    gen = CityGenerator(CityProfile(population=50_000, seed=42))
    g = gen.generate()
    assert g is not None
    assert len(g.nodes) > 10
    assert g.graph.number_of_edges() > 0
    # A slack bus was added.
    assert "S_MAIN" in g.nodes


def test_generator_deterministic_for_same_seed():
    p = CityProfile(population=50_000, seed=42)
    a = CityGenerator(p).generate()
    b = CityGenerator(p).generate()
    assert sorted(a.nodes.keys()) == sorted(b.nodes.keys())
    assert sorted(a.graph.edges()) == sorted(b.graph.edges())


def test_generator_different_seed_produces_different_topology():
    p1 = CityProfile(population=50_000, seed=1)
    p2 = CityProfile(population=50_000, seed=2)
    a = CityGenerator(p1).generate()
    b = CityGenerator(p2).generate()
    # Node IDs have deterministic prefixes (H_, IND_, etc.) but the
    # embedded coordinates (rounded) may differ.
    sa = set(a.nodes.keys())
    sb = set(b.nodes.keys())
    # We expect at least some difference in IDs.
    assert sa != sb


def test_generator_includes_critical_infrastructure():
    g = CityGenerator(CityProfile(population=200_000, seed=42)).generate()
    assert "HOSP_ICU" in g.nodes
    # Microgrid root is present.
    has_root = any(n.node_type == "microgrid_root" for n in g.nodes.values())
    assert has_root


def test_generator_includes_renewables():
    g = CityGenerator(CityProfile(population=200_000, seed=42)).generate()
    has_solar = any(n.node_type == "solar_farm" for n in g.nodes.values())
    has_wind = any(n.node_type == "wind_farm" for n in g.nodes.values())
    assert has_solar and has_wind


def test_generator_includes_storage():
    g = CityGenerator(CityProfile(population=200_000, seed=42)).generate()
    bess = [nid for nid, n in g.nodes.items() if n.node_type == "bess"]
    assert len(bess) >= 1


def test_generator_has_tie_switches():
    g = CityGenerator(CityProfile(population=200_000, seed=42)).generate()
    ties = [
        (u, v) for u, v, d in g.graph.edges(data=True)
        if d.get("is_tie_switch")
    ]
    assert len(ties) >= 2


def test_generator_report_serialisable():
    g = CityGenerator(CityProfile(population=100_000, seed=42)).generate()
    payload = g._city_report.to_dict()
    assert "profile" in payload
    assert "node_counts" in payload
    assert payload["edge_count"] > 0
    assert payload["expected_load_mw"] > 0


def test_generator_runs_power_flow():
    g = CityGenerator(CityProfile(population=100_000, seed=42)).generate()
    # Power flow ran during warm-up; check at least one node has a
    # non-zero voltage_angle (slack = 0).
    angles = [n.voltage_angle for n in g.nodes.values()]
    assert any(a != 0.0 for a in angles)
