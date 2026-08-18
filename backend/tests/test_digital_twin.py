"""test_digital_twin.py — DigitalTwin + TwinRegistry unit tests."""
from __future__ import annotations

import pytest

from digital_twin.twin import DigitalTwin
from digital_twin.twin_registry import TwinRegistry
from digital_twin.degradation import thermal_ageing_step
from city.city_generator import CityGenerator
from city.city_profile import CityProfile


def _grid():
    return CityGenerator(CityProfile(population=20_000, seed=7)).generate()


def test_degradation_monotonic_for_overload():
    a = thermal_ageing_step(current_health=1.0, loading=1.0)
    assert 0.0 <= a["delta_health"] <= 0.01
    assert a["new_health"] < 1.0


def test_degradation_clamps_health_to_unit_interval():
    a = thermal_ageing_step(current_health=-0.5, loading=1.0)
    assert a["new_health"] == 0.0


def test_degradation_overload_degrades_faster():
    a_idle = thermal_ageing_step(current_health=1.0, loading=0.0)
    a_full = thermal_ageing_step(current_health=1.0, loading=1.5)
    assert a_full["delta_health"] > a_idle["delta_health"]


def test_twin_tick_records_history():
    twin = DigitalTwin(asset_id="T1", asset_type="transformer")
    out = twin.tick(physical_state={"load": 0.5, "generation": 0.0,
                                    "voltage": 1.0, "frequency": 50.0})
    assert out["asset_id"] == "T1"
    assert twin.age_hours == 1.0
    assert len(twin.sensor_history) == 1


def test_twin_predict_failure_zero_horizon_no_samples():
    twin = DigitalTwin(asset_id="T1")
    out = twin.predict_failure(horizon_steps=24)
    assert out["projected_health"] == twin.health
    assert out["will_fail"] is False


def test_twin_predict_failure_after_history():
    twin = DigitalTwin(asset_id="T1")
    # Force a few healthy ticks.
    for _ in range(5):
        twin.tick(physical_state={"load": 0.0, "generation": 0.0})
    out = twin.predict_failure(horizon_steps=24)
    assert out["horizon_steps"] == 24
    # Stage 10 (main.md): heuristic is named `projected_health_risk_score`,
    # NOT `projected_failure_probability` — see EHM-CRIT-001.
    assert 0.0 <= out["projected_health_risk_score"] <= 1.0


def test_twin_health_drives_health_risk_score():
    twin = DigitalTwin(asset_id="T1")
    twin.health = 0.2
    # With health=0.2, the formula gives (0.4-0.2)/0.4 = 0.5.
    # `failure_probability` is the deprecated alias and still works,
    # but the canonical name is `health_risk_score` (EHM-CRIT-001).
    assert twin.health_risk_score >= 0.5


def test_twin_record_maintenance():
    twin = DigitalTwin(asset_id="T1")
    twin.health = 0.1
    twin.record_maintenance({"label": "rewound", "restore_health_to": 1.0})
    assert twin.health == 1.0
    assert len(twin.maintenance_history) == 1


def test_twin_to_dict_keys():
    twin = DigitalTwin(asset_id="T1", asset_type="pole")
    twin.tick(physical_state={"load": 0.2, "generation": 0.0})
    d = twin.to_dict()
    # Stage 10 (main.md) — canonical name is `health_risk_score`,
    # not `failure_probability` (EHM-CRIT-001).
    assert {"asset_id", "asset_type", "health", "age_hours",
            "temperature", "loading", "health_risk_score",
            "sensor_history_size", "maintenance_history_size",
            "predicted_state"} <= set(d.keys())


def test_registry_register_idempotent():
    reg = TwinRegistry()
    g = _grid()
    n0 = len(reg)
    reg.register(g)
    n1 = len(reg)
    reg.register(g)  # second call should be a no-op
    n2 = len(reg)
    assert n1 == len(g.nodes)
    assert n2 == n1


def test_registry_sync_updates_all():
    reg = TwinRegistry()
    g = _grid()
    reg.register(g)
    updated = reg.sync(g, dt_hours=1.0)
    assert updated == len(g.nodes)


def test_registry_summary_shape():
    reg = TwinRegistry()
    g = _grid()
    reg.register(g)
    reg.sync(g, dt_hours=1.0)
    s = reg.summary()
    assert s["count"] == len(g.nodes)
    assert 0.0 <= s["mean_health"] <= 1.0


def test_registry_at_risk_default_threshold():
    reg = TwinRegistry()
    twin = DigitalTwin(asset_id="T_RISK")
    twin.failure_probability = 0.9
    twin.health = 0.1
    twin2 = DigitalTwin(asset_id="T_OK")
    twin2.health = 1.0
    twin2.failure_probability = 0.0
    reg.add(twin)
    reg.add(twin2)
    assert "T_RISK" in reg.at_risk()
    assert "T_OK" not in reg.at_risk()


def test_registry_to_dict_keys():
    reg = TwinRegistry()
    g = _grid()
    reg.register(g)
    d = reg.to_dict()
    assert isinstance(d, dict)
    assert len(d) == len(g.nodes)
