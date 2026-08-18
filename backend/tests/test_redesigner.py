"""test_redesigner.py — Redesigner unit tests."""
from __future__ import annotations

import pytest

from city.city_generator import CityGenerator
from city.city_profile import CityProfile
from improvement.redesigner import Redesigner


def _grid():
    return CityGenerator(CityProfile(population=20_000, seed=11)).generate()


def test_redesigner_returns_report():
    g = _grid()
    before = {"n_nodes": len(g.nodes), "n_failed": 0}
    r = Redesigner().propose(g, before)
    assert r.actions_proposed >= 0
    assert r.actions_applied >= 0
    assert "n_nodes" in r.before
    assert "n_edges" in r.after


def test_redesigner_does_not_mutate_live_grid():
    g = _grid()
    n_before = len(g.nodes)
    e_before = g.graph.number_of_edges()
    Redesigner().propose(g, {"n_nodes": n_before})
    # AI planner uses try/finally to roll back; the live grid is intact.
    assert len(g.nodes) == n_before
    assert g.graph.number_of_edges() == e_before


def test_redesigner_handles_empty_before_summary():
    g = _grid()
    r = Redesigner().propose(g, {})
    assert isinstance(r.to_dict(), dict)
    assert "delta" in r.to_dict()