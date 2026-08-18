"""test_evaluator.py — SimulationEvaluator unit tests."""
from __future__ import annotations

import pytest

from improvement.evaluator import SimulationEvaluator, StepSnapshot


def test_evaluator_summary_zero_snapshots():
    ev = SimulationEvaluator()
    s = ev.summary()
    assert s["steps"] == 0
    # Stable schema even with no snapshots.
    for k in ("forecast_mae", "forecast_rmse", "attack_precision",
              "attack_recall", "ieee_saifi", "ieee_saidi", "ieee_caidi",
              "ieee_maifi", "ieee_asai", "ieee_ens_mwh"):
        assert k in s


def test_evaluator_summary_after_one_step():
    ev = SimulationEvaluator()
    snap = StepSnapshot(
        timestep=1, failed_count=1, restored_count=0,
        total_gen=5.0, total_load=4.0,
        avg_voltage=1.0, avg_frequency=50.0,
        critical_load_available=2, critical_load_total=3,
        battery_discharged_mwh=0.5, renewable_used_mw=1.0,
        switches_toggled=2,
    )
    ev.record_step(snap)
    s = ev.summary()
    assert s["steps"] == 1
    assert s["total_gen"] == 5.0
    assert s["critical_load_availability"] == pytest.approx(2 / 3, rel=1e-3)
    assert s["attack_precision"] == 0.0


def test_evaluator_forecast_metrics():
    ev = SimulationEvaluator()
    ev.record_forecast(1.0, 1.1)
    ev.record_forecast(2.0, 1.9)
    s = ev.summary()
    assert s["forecast_mae"] == pytest.approx(0.1, rel=1e-3)
    assert s["forecast_rmse"] > 0.0


def test_evaluator_attack_metrics():
    ev = SimulationEvaluator()
    # Two true positives, one false positive, one false negative.
    ev.record_attack(True, True)
    ev.record_attack(True, False)
    ev.record_attack(False, True)
    s = ev.summary()
    assert s["attack_tp"] == 1
    assert s["attack_fp"] == 1
    assert s["attack_fn"] == 1
    assert s["attack_tn"] == 0
    assert s["attack_precision"] == pytest.approx(0.5, rel=1e-3)
    assert s["attack_recall"] == pytest.approx(0.5, rel=1e-3)


def test_snapshot_from_grid_minimal():
    """Use SimulationEvaluator.snapshot_from_grid against a stub grid."""

    class _N:
        def __init__(self, ntype, failed, received):
            self.node_type = ntype
            self.failed = failed
            self.received_power = received
            self.generation = 0.0
            self.voltage = 1.0
            self.frequency = 50.0
            self.load = 0.0

    class _G:
        nodes = {"h1": _N("hospital", False, 1.0)}

    snap = SimulationEvaluator.snapshot_from_grid(_G(), timestep=0)
    assert snap.critical_load_total >= 1
    assert snap.critical_load_available == 1