"""test_self_healing.py — unit tests for the predictive self-healing
subsystem and the reliability recorder."""

from __future__ import annotations

import pytest

from self_healing.predictor import (
    PredictiveAction,
    PredictiveSelfHealer,
    RiskAssessment,
)
from self_healing.recorder import ReliabilityRecorder, ReliabilitySample


# ----------------------------------------------------------------------
# PredictiveSelfHealer
# ----------------------------------------------------------------------


class _Twin:
    def __init__(self, asset_id, health=1.0, failure_prob=0.0):
        self.asset_id = asset_id
        self.health = health
        self.failure_probability = failure_prob


class _Registry:
    def __init__(self, twins):
        self._t = {t.asset_id: t for t in twins}

    def get(self, asset_id):
        return self._t.get(asset_id)


@pytest.fixture
def sample_grid():
    from city.city_generator import CityGenerator
    from city.city_profile import CityProfile
    return CityGenerator(CityProfile(population=10_000, seed=3)).generate()


def test_assess_returns_empty_when_no_risks(sample_grid):
    reg = _Registry([
        _Twin(nid, health=1.0, failure_prob=0.0)
        for nid in sample_grid.nodes
    ])
    healer = PredictiveSelfHealer(risk_threshold=0.5)
    risks = healer.assess(sample_grid, reg)
    assert isinstance(risks, list)
    assert risks == []


def test_assess_picks_high_failure_probability(sample_grid):
    nid = next(iter(sample_grid.nodes))
    reg = _Registry([
        _Twin(nid, health=0.2, failure_prob=0.8)
        if other == nid
        else _Twin(other, health=1.0, failure_prob=0.0)
        for other in sample_grid.nodes
    ])
    healer = PredictiveSelfHealer(risk_threshold=0.5)
    risks = healer.assess(sample_grid, reg)
    assert len(risks) >= 1
    assert any(r.node_id == nid for r in risks)
    assert risks[0].severity > 0.0


def test_risk_assessment_to_dict_is_serialisable(sample_grid):
    ra = RiskAssessment(
        node_id="X", failure_probability=0.6,
        isolated_load_mw=1.5, severity=0.7,
        rationale="test",
    )
    d = ra.to_dict()
    assert d["node_id"] == "X"
    assert d["failure_probability"] == 0.6
    assert d["isolated_load_mw"] == 1.5


def test_predictive_action_to_dict(sample_grid):
    pa = PredictiveAction(
        kind="add_tie_switch", params={"u": "A", "v": "B"},
        expected_risk_reduction=0.4, rationale="x", target_node_id="A",
    )
    d = pa.to_dict()
    assert d["kind"] == "add_tie_switch"
    assert d["params"] == {"u": "A", "v": "B"}
    assert d["target_node_id"] == "A"


def test_run_returns_full_envelope(sample_grid):
    reg = _Registry([
        _Twin(nid, health=1.0, failure_prob=0.0)
        for nid in sample_grid.nodes
    ])
    out = PredictiveSelfHealer(risk_threshold=0.5).run(sample_grid, reg)
    assert set(out.keys()) >= {
        "risk_count", "action_count",
        "risks", "actions", "max_severity",
    }


def test_recommend_respects_max_actions(sample_grid):
    # Force several "at risk" nodes so recommend() must respect the cap.
    twins = []
    for nid in sample_grid.nodes:
        twins.append(_Twin(nid, health=0.1, failure_prob=0.9))
    reg = _Registry(twins)
    healer = PredictiveSelfHealer(
        risk_threshold=0.5, max_actions=2,
    )
    risks = healer.assess(sample_grid, reg)
    actions = healer.recommend(sample_grid, risks)
    assert len(actions) <= 2


# ----------------------------------------------------------------------
# ReliabilityRecorder
# ----------------------------------------------------------------------


def test_recorder_empty_summary_has_zero_samples():
    rec = ReliabilityRecorder()
    out = rec.summary()
    assert out["samples"] == 0
    assert out["saifi"] == 0.0
    assert out["history"] == []


def test_recorder_records_from_grid(sample_grid):
    rec = ReliabilityRecorder()
    sample = rec.record_from_grid(sample_grid, timestep=5, load_mw=10.0)
    assert isinstance(sample, ReliabilitySample)
    assert sample.timestep == 5
    assert rec.summary()["samples"] == 1


def test_recorder_summary_includes_history(sample_grid):
    rec = ReliabilityRecorder()
    for t in range(3):
        rec.record_from_grid(sample_grid, timestep=t, load_mw=5.0)
    out = rec.summary()
    assert out["samples"] == 3
    assert len(out["history"]) == 3
    assert "voltage_stability_mean" in out
    assert "frequency_stability_mean" in out


def test_recorder_sample_to_dict_is_serialisable():
    s = ReliabilitySample(
        timestep=1, failed_count=2, critical_failed_count=1,
        cumulative_customer_minutes=60.0, sustained_interruptions=2.0,
        ens_mwh_step=0.5, voltage_stability=0.95,
        frequency_stability=0.99, notes="unit",
    )
    d = s.to_dict()
    assert d["timestep"] == 1
    assert d["ens_mwh_step"] == 0.5
