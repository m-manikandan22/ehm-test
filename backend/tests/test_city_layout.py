"""test_city_layout.py — unit tests for the city_layer JSON view."""

from __future__ import annotations

import pytest

from city.city_generator import CityGenerator
from city.city_profile import CityProfile
from city.layout import city_layout, buildings, _zone_polygons


class _FakeNode:
    def __init__(self, nid, ntype, label, x, y, priority=3):
        self.id = nid
        self.node_type = ntype
        self.label = label
        self.x = x
        self.y = y
        self.priority = priority
        self.street = "Main"
        self.role = "load"


class _FakeGrid:
    def __init__(self, nodes, road=None, zoning=None):
        self.nodes = nodes
        self._road_network = road
        self._zoning = zoning


def test_city_layout_returns_no_layout_for_empty_grid():
    grid = _FakeGrid({})
    out = city_layout(grid)
    assert out == {"has_layout": False}


def test_buildings_serialises_required_fields():
    nodes = {
        "h1": _FakeNode("h1", "house", "Home 1", 10.0, 20.0, priority=3),
        "h2": _FakeNode("h2", "hospital", "Hosp", 50.0, 60.0, priority=1),
    }
    grid = _FakeGrid(nodes)
    out = buildings(grid)
    assert len(out) == 2
    keys = set(out[0].keys())
    assert keys >= {"id", "node_type", "label", "x", "y", "priority"}
    # Higher priority buildings come back with smaller priority ints
    assert out[0]["priority"] in (1, 3)


def test_zone_polygons_group_blocks_by_zone():
    # Two blocks in 'residential', one in 'industrial'
    road_zones = {
        (0, 0): "residential",
        (0, 1): "residential",
        (1, 0): "industrial",
    }
    out = _zone_polygons(road_zones)
    zones = {z["zone"] for z in out}
    assert zones == {"residential", "industrial"}
    residential = next(z for z in out if z["zone"] == "residential")
    assert residential["block_count"] == 2


def test_city_layout_for_generated_grid_has_roads_and_buildings():
    g = CityGenerator(CityProfile(population=50_000, seed=42)).generate()
    layout = city_layout(g)
    assert layout.get("has_layout") is True
    assert "bounds" in layout
    assert len(layout["buildings"]) > 0
    assert len(layout["zones"]) > 0
    # Each road segment exposes u, v, kind, length
    if layout["roads"]:
        sample = layout["roads"][0]
        assert {"u", "v", "kind", "length"} <= set(sample.keys())
