"""test_city_profile.py — expected-derivation formulas for CityProfile."""
from __future__ import annotations

import math

import pytest

from city.city_profile import CityProfile


def test_default_profile_sane():
    p = CityProfile(population=100_000, area_km2=50.0)
    assert p.effective_density == pytest.approx(2000.0, rel=1e-3)
    assert p.expected_load_mw() > 0.0
    assert p.expected_building_count() > 0
    assert p.expected_feeder_count() > 0
    assert p.expected_distribution_substation_count() > 0
    assert p.expected_primary_substation_count() > 0


def test_load_scales_with_population():
    small = CityProfile(population=100_000).expected_load_mw()
    large = CityProfile(population=500_000).expected_load_mw()
    assert large > small
    # Roughly linear (~5x); allow slack for diversity factor margins.
    assert large / small == pytest.approx(5.0, rel=0.2)


def test_renewable_share_drives_renewable_mw():
    p = CityProfile(population=100_000, renewable_share=0.5)
    # Both numbers are rounded to 3 dp in CityProfile — compare with rel
    # tolerance to absorb the small round-off.
    assert p.expected_renewable_mw() == pytest.approx(
        p.expected_load_mw() * 0.5, rel=1e-3
    )


def test_density_override():
    p = CityProfile(population=200_000, area_km2=100.0, density=4000.0)
    assert p.effective_density == 4000.0


def test_from_dict_ignores_unknown_keys():
    p = CityProfile.from_dict({"population": 200_000, "unknown": 99})
    assert p.population == 200_000


def test_from_dict_does_not_mutate_passed_dict():
    """from_dict must not mutate the caller's dictionary."""
    data = {"population": 75_000}
    p = CityProfile.from_dict(data)
    assert p.population == 75_000
    # Original dict untouched.
    assert data == {"population": 75_000}


def test_to_dict_round_trip():
    p = CityProfile(population=123_456, seed=9)
    assert CityProfile.from_dict(p.to_dict()) == p


def test_feeder_count_is_at_least_one():
    p = CityProfile(population=1_000)
    assert p.expected_feeder_count() >= 1


def test_substation_count_is_at_least_one():
    p = CityProfile(population=1_000)
    assert p.expected_distribution_substation_count() >= 1
    assert p.expected_primary_substation_count() >= 1


def test_bess_count_is_at_least_one():
    p = CityProfile(population=1_000)
    assert p.expected_bess_count() >= 1
