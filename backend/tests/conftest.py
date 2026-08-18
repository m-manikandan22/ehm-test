"""
conftest.py — pytest fixtures shared across the test suite.

Puts `backend/` on `sys.path` so `import simulation` and `import models`
work regardless of where pytest is invoked from. Also exposes the
most common fixtures (sample grid, twin registry, weather) so tests
can import them by name.

Also puts the project root on `sys.path` so tests that import the
``experiments`` package (which lives at the repo root, not inside
``backend/``) can find it.
"""
import os
import sys

_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_ROOT = os.path.dirname(_BACKEND)
for _p in (_BACKEND, _PROJECT_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402


@pytest.fixture
def rng_seed():
    """Default deterministic seed for unit tests."""
    return 42


@pytest.fixture
def sample_grid():
    """A small SmartGrid for tests that don't need full city generation."""
    from city.city_generator import CityGenerator
    from city.city_profile import CityProfile
    return CityGenerator(CityProfile(population=20_000, seed=7)).generate()


@pytest.fixture
def sample_twin_registry(sample_grid):
    """Twin registry pre-populated with the sample grid's twins."""
    from digital_twin.twin_registry import TwinRegistry
    reg = TwinRegistry()
    reg.register(sample_grid)
    reg.sync(sample_grid, dt_hours=1.0)
    return reg


@pytest.fixture
def sample_weather():
    """A weather engine in a known state."""
    from weather.weather_engine import WeatherEngine, WeatherState
    w = WeatherEngine(seed=42)
    w.set(WeatherState.SUNNY)
    return w
