"""test_xai.py — XAI Report / explainer / route contract tests."""
from __future__ import annotations

import pytest

from rl.explainer import XAIReport, RLExplainer


def test_xai_report_to_dict_has_required_keys():
    report = XAIReport(
        why=[{"feature": "v[0]", "value": 1.0, "importance": 0.05}],
        inputs=["v"],
        expected_benefit=0.42,
        alternatives=[{"action_id": 1, "action_name": "x", "q_value": 0.3}],
        confidence=0.7,
    )
    d = report.to_dict()
    for k in ("why", "inputs", "expected_benefit", "alternatives", "confidence"):
        assert k in d


def test_explainer_voltage_neutral_importance_low():
    """Voltages near 1.0 should have low importance."""
    ex = RLExplainer()
    report = ex.explain(
        features={"voltage": [1.0, 1.0, 1.0]},
        q_values=[0.0],
        chosen_action=0,
        action_names=["x"],
    )
    assert report.why[0]["importance"] == pytest.approx(0.0, abs=1e-9)


def test_explainer_load_deviation_is_high_importance():
    ex = RLExplainer()
    report = ex.explain(
        features={"load": [1.5]},
        q_values=[0.0],
        chosen_action=0,
        action_names=["x"],
    )
    assert report.why[0]["importance"] > 1.0


def test_explainer_confidence_distribution_sums_to_one():
    """With three Q-values and uniform inputs, the softmax should sum to 1."""
    ex = RLExplainer()
    # Use a chosen-action with finite Q.
    q = [0.0, 1.0, 2.0]
    import math
    mx = max(q)
    exps = [math.exp(v - mx) for v in q]
    s = sum(exps)
    expected = exps[0] / s
    report = ex.explain(
        features={"x": [0.0]},
        q_values=q,
        chosen_action=0,
        action_names=["a", "b", "c"],
    )
    assert report.confidence == pytest.approx(expected, rel=1e-9)