"""test_weather_engine.py — Markov weather engine unit tests."""
from __future__ import annotations

import pytest

from weather.weather_engine import WeatherEngine, WeatherState


def test_default_state_is_sunny():
    w = WeatherEngine(seed=42)
    assert w.state == WeatherState.SUNNY


def test_set_state_appends_to_history():
    w = WeatherEngine(seed=42)
    w.set(WeatherState.STORM)
    w.set(WeatherState.CYCLONE)
    assert list(w.history) == [WeatherState.STORM, WeatherState.CYCLONE]


def test_step_returns_a_known_state():
    w = WeatherEngine(seed=42)
    out = w.step()
    assert isinstance(out, WeatherState)
    assert out in WeatherState


def test_get_factors_returns_finite_numbers():
    w = WeatherEngine(seed=42)
    for st in WeatherState:
        w.set(st)
        f = w.get_factors()
        assert 0.0 <= f.solar_factor <= 5.0
        assert 0.0 <= f.wind_factor <= 5.0
        assert 0.0 <= f.fault_prob_factor <= 10.0


def test_snapshot_keys():
    w = WeatherEngine(seed=42)
    w.set(WeatherState.STORM)
    snap = w.snapshot()
    assert snap["state"] == "storm"
    assert set(snap["factors"].keys()) >= {
        "solar_factor", "wind_factor", "load_factor",
        "fault_prob_factor", "battery_discharge_factor",
        "temperature_c",
    }


def test_step_is_deterministic_with_same_seed():
    a = WeatherEngine(seed=1)
    b = WeatherEngine(seed=1)
    seq_a = [a.step().value for _ in range(10)]
    seq_b = [b.step().value for _ in range(10)]
    assert seq_a == seq_b


def test_step_differs_across_seeds():
    a = WeatherEngine(seed=1)
    b = WeatherEngine(seed=2)
    seq_a = [a.step().value for _ in range(30)]
    seq_b = [b.step().value for _ in range(30)]
    assert seq_a != seq_b


def test_factors_change_with_state():
    w = WeatherEngine(seed=42)
    w.set(WeatherState.SUNNY)
    sunny_solar = w.get_factors().solar_factor
    w.set(WeatherState.CYCLONE)
    cyclone_solar = w.get_factors().solar_factor
    assert sunny_solar > cyclone_solar