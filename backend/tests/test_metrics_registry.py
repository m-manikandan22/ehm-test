"""test_metrics_registry.py — forecast + grid KPI + registry tests."""
from __future__ import annotations

import pytest

from metrics.forecast_metrics import mae, rmse, mape
from metrics.grid_kpis import (
    voltage_stability_index,
    frequency_stability_index,
    renewable_penetration_pct,
    battery_utilisation_pct,
    system_reliability_index,
)
from metrics.registry import metric, compute_all, registry


# ----------------------------------------------------------------------
# Forecast
# ----------------------------------------------------------------------

def test_mae_perfect_prediction():
    assert mae([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(0.0)


def test_mae_one_off():
    assert mae([1.0, 2.0], [2.0, 3.0]) == pytest.approx(1.0)


def test_rmse_zero_for_perfect():
    assert rmse([1.0, 2.0], [1.0, 2.0]) == pytest.approx(0.0)


def test_rmse_one_off_is_one():
    assert rmse([1.0, 2.0], [2.0, 3.0]) == pytest.approx(1.0)


def test_mape_perfect_zero():
    assert mape([1.0, 2.0], [1.0, 2.0]) == pytest.approx(0.0)


def test_mape_handles_zero_actual():
    # Zero actuals should be skipped, not produce inf.
    assert mape([0.0, 1.0], [0.0, 1.0]) == pytest.approx(0.0)


# ----------------------------------------------------------------------
# Grid KPIs
# ----------------------------------------------------------------------

class _N:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def test_voltage_stability_all_in_band():
    nodes = [_N(voltage=1.0), _N(voltage=0.97), _N(voltage=1.04)]
    assert voltage_stability_index(nodes) == pytest.approx(1.0)


def test_voltage_stability_two_of_three():
    nodes = [_N(voltage=1.0), _N(voltage=0.5), _N(voltage=1.04)]
    assert voltage_stability_index(nodes) == pytest.approx(2 / 3, rel=1e-3)


def test_frequency_stability():
    nodes = [_N(frequency=50.0), _N(frequency=49.9), _N(frequency=51.0)]
    assert frequency_stability_index(nodes) == pytest.approx(2 / 3, rel=1e-3)


def test_renewable_penetration():
    nodes = [
        _N(node_type="solar_farm", generation=2.0),
        _N(node_type="generator_gas", generation=3.0),
    ]
    assert renewable_penetration_pct(nodes) == pytest.approx(40.0)


def test_battery_utilisation():
    nodes = [
        _N(node_type="battery", battery_level=0.5),
        _N(node_type="battery", battery_level=0.9),
    ]
    assert battery_utilisation_pct(nodes) == pytest.approx(70.0)


def test_system_reliability_in_unit_interval():
    nodes = [
        _N(voltage=1.0, frequency=50.0, failed=False),
        _N(voltage=0.5, frequency=51.0, failed=True),
    ]
    s = system_reliability_index(nodes)
    assert 0.0 <= s <= 1.0


# ----------------------------------------------------------------------
# Registry
# ----------------------------------------------------------------------

def test_metric_decorator_registers_and_returns():
    @metric("test.always_one")
    def always_one(payload):
        return 1.0
    out = compute_all({})
    assert out["test.always_one"] == 1.0
    assert "test.always_one" in registry.names()


def test_compute_all_isolates_failures():
    @metric("test.good")
    def good(payload):
        return 0.5

    @metric("test.bad")
    def bad(payload):
        raise RuntimeError("boom")

    out = compute_all({})
    assert out["test.good"] == 0.5
    # The bad metric returns NaN to signal failure without breaking the run.
    import math
    assert math.isnan(out["test.bad"])


def test_registry_run_one_unknown_raises():
    with pytest.raises(KeyError):
        registry.run_one("nope", {})