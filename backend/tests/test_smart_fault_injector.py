"""test_smart_fault_injector.py — fault catalog + injector unit tests."""
from __future__ import annotations

import pytest

from faults.fault_catalog import (
    FAULT_CATALOG,
    FaultType,
    catalog_for_type,
)
from faults.smart_fault_injector import SmartFaultInjector
from weather.weather_engine import WeatherState
from city.city_generator import CityGenerator
from city.city_profile import CityProfile


def _grid():
    return CityGenerator(CityProfile(population=20_000, seed=3)).generate()


def test_catalog_has_all_fault_types():
    expected = set(FaultType)
    assert expected <= set(FAULT_CATALOG.keys())


def test_catalog_for_type_returns_only_matching():
    catalog = catalog_for_type("transformer")
    assert all("transformer" in f.affected_types for f in catalog)


def test_catalog_for_unknown_type_returns_empty():
    assert catalog_for_type("not_a_real_type") == []


def test_injector_zero_expected_returns_empty():
    inj = SmartFaultInjector(seed=42, expected_per_step=0.0)
    g = _grid()
    events = inj.inject(WeatherState.SUNNY, g)
    assert events == []


def test_injector_returns_event_with_real_node_id():
    inj = SmartFaultInjector(seed=42, expected_per_step=2.0)
    g = _grid()
    events = inj.inject(WeatherState.STORM, g)
    assert events
    for ev in events:
        assert ev.node_id in g.nodes
        assert 0.0 <= ev.severity <= 5.0


def test_injector_storm_increases_events_over_sunny():
    inj_a = SmartFaultInjector(seed=42, expected_per_step=1.0)
    inj_b = SmartFaultInjector(seed=42, expected_per_step=1.0)
    g_a = _grid()
    g_b = _grid()
    sunny = inj_a.inject(WeatherState.SUNNY, g_a, max_events=20)
    storm = inj_b.inject(WeatherState.STORM, g_b, max_events=20)
    # Storm base rate is 3x sunny's; expected Poisson draws are larger.
    assert len(storm) >= len(sunny)


def test_injector_apply_calls_grid_inject_failure():
    inj = SmartFaultInjector(seed=42, expected_per_step=2.0)
    g = _grid()
    events = inj.inject(WeatherState.STORM, g)
    applied = inj.apply(g, events)
    assert isinstance(applied, list)
    assert len(applied) == len(events)


def test_injector_apply_skips_unknown_node_ids():
    inj = SmartFaultInjector(seed=42, expected_per_step=1.0)
    g = _grid()
    from faults.smart_fault_injector import FaultEvent
    bogus = [FaultEvent(type=FaultType.LIGHTNING, node_id="DOES_NOT_EXIST",
                        probability=0.1, severity=0.4, propagation=0.2,
                        description="x")]
    assert inj.apply(g, bogus) == []


def test_injector_handles_empty_grid():
    inj = SmartFaultInjector(seed=42, expected_per_step=1.0)
    g = type("Empty", (), {"nodes": {}})()
    assert inj.inject(WeatherState.SUNNY, g) == []


def test_injector_clamps_to_max_events():
    inj = SmartFaultInjector(seed=42, expected_per_step=20.0)
    g = _grid()
    events = inj.inject(WeatherState.CYCLONE, g, max_events=3)
    assert len(events) <= 3