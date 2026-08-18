"""test_microgrid.py — microgrid controller unit tests."""
from __future__ import annotations

import pytest

from microgrid.microgrid_controller import MicrogridController
from city.city_generator import CityGenerator
from city.city_profile import CityProfile


def _grid():
    return CityGenerator(CityProfile(population=20_000, seed=11)).generate()


def test_form_islands_returns_at_least_one():
    c = MicrogridController()
    g = _grid()
    islands = c.form_islands(g, faulted_nodes=[])
    assert len(islands) >= 1
    assert all("generators" in i and "loads" in i for i in islands)


def test_form_islands_marks_has_source():
    c = MicrogridController()
    g = _grid()
    islands = c.form_islands(g, faulted_nodes=[])
    assert all(i["has_source"] for i in islands)


def test_form_islands_excludes_faulted_nodes():
    c = MicrogridController()
    g = _grid()
    islands_before = c.form_islands(g, faulted_nodes=[])
    faulted = ["S_MAIN"]
    g.nodes["S_MAIN"].failed = True
    islands_after = c.form_islands(g, faulted_nodes=faulted)
    # After removing S_MAIN, islands must NOT include S_MAIN.
    for i in islands_after:
        assert "S_MAIN" not in i["nodes"]
    # The total node count across surviving islands is smaller.
    n_before = sum(i["size"] for i in islands_before)
    n_after = sum(i["size"] for i in islands_after)
    assert n_after < n_before


def test_island_health_returns_balance():
    c = MicrogridController()
    g = _grid()
    c.form_islands(g, faulted_nodes=[])
    iid = next(iter(c.islands))
    h = c.island_health(g, iid)
    assert "balance_mw" in h
    assert "total_gen" in h
    assert "total_load" in h


def test_reconnect_returns_int():
    c = MicrogridController()
    g = _grid()
    c.form_islands(g, faulted_nodes=[])
    cleared = c.reconnect(g)
    assert isinstance(cleared, int)
    assert cleared >= 0


def test_island_health_uses_actual_node_attributes():
    c = MicrogridController()
    g = _grid()
    c.form_islands(g, faulted_nodes=[])
    iid = next(iter(c.islands))
    h = c.island_health(g, iid)
    # If the island contains nodes, sums should be non-negative.
    assert h["total_gen"] >= 0.0
    assert h["total_load"] >= 0.0