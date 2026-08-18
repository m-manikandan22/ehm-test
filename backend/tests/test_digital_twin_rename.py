"""test_digital_twin_rename.py — Verify the conservative-naming fix.

main.md Stage 10 forbids calling a heuristic ``failure_probability``.
DigitalTwin now exposes the canonical name ``health_risk_score`` and
keeps ``failure_probability`` as a deprecated alias. See
``docs/PAPER_READINESS_AUDIT.md`` EHM-CRIT-001.
"""
from __future__ import annotations

import pytest

from digital_twin.twin import DigitalTwin, _HEALTH_RISK_FORMULA


# ── (1) New canonical name exists ─────────────────────────────────────
def test_health_risk_score_is_disclosed():
    """DigitalTwin has a readable ``health_risk_score`` property."""
    t = DigitalTwin(asset_id="T0")
    assert hasattr(t, "health_risk_score")
    assert hasattr(DigitalTwin, "_HEALTH_RISK_FORMULA") or \
        _HEALTH_RISK_FORMULA
    # Healthy twin → 0 risk.
    assert t.health_risk_score == 0.0


# ── (2) Heuristic risk formula behaves as documented ──────────────────
def test_health_risk_score_clamps_and_is_zero_above_threshold():
    """Risk is 0 at health >= 0.4 and monotonically increases to 1
    at health <= 0. Values are clamped to [0, 1]."""
    t = DigitalTwin(asset_id="T0")
    for h in [1.0, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]:
        t.health = h
        if h >= 0.4:
            assert t.health_risk_score == 0.0, f"h={h}"
        else:
            expected = (0.4 - h) / 0.4
            assert t.health_risk_score == pytest.approx(expected)
    # Strictly defensive: returns 1.0 (clamped) when health is very negative.
    t.health = -5.0
    assert t.health_risk_score == 1.0
    # And 0.0 when health is above the threshold.
    t.health = 2.0
    assert t.health_risk_score == 0.0


# ── (3) Deprecated alias still works but emits a warning ─────────────
def test_failure_probability_is_deprecated_alias():
    """Reading ``failure_probability`` raises DeprecationWarning,
    returns the same value as ``health_risk_score``."""
    t = DigitalTwin(asset_id="T0")
    t.health = 0.2
    expected = t.health_risk_score
    with pytest.warns(DeprecationWarning, match="health_risk_score"):
        alias = t.failure_probability
    assert alias == expected


# ── (4) Setting the score does not desynchronise it from health ──────
def test_setter_is_noop_and_getter_always_derives_from_health():
    """The setter exists for backward compatibility only — the getter
    is always derived from ``self.health`` so external overrides
    cannot desynchronise the two values."""
    t = DigitalTwin(asset_id="T0")
    # Setter is a no-op; the next read still derives from health.
    t.health_risk_score = 1.5
    assert t.health_risk_score == 0.0   # health=1.0 → 0
    t.health_risk_score = -0.5
    assert t.health_risk_score == 0.0
    t.health_risk_score = 0.7
    assert t.health_risk_score == 0.0   # still derived from health=1.0
    # When health drops below the threshold, the derived score dominates.
    t.health = 0.2
    assert t.health_risk_score == pytest.approx(0.5)
    # The setter accepts non-finite / unconvertible inputs without raising.
    t.health_risk_score = "not-a-number"  # type: ignore[assignment]


# ── (5) tick() updates the new name and serialises correctly ───────
def test_tick_writes_health_risk_score():
    t = DigitalTwin(asset_id="T0")
    out = t.tick(physical_state={"load": 0.5, "generation": 0.2,
                                  "voltage": 1.0})
    assert "health_risk_score" in out
    assert out["health_risk_score"] == 0.0   # health is 1.0 by default
    d = t.to_dict()
    assert "health_risk_score" in d
    assert "failure_probability" not in d


# ── (6) predict_failure surfaces the new key ────────────────────────
def test_predict_failure_uses_health_risk_score_key():
    t = DigitalTwin(asset_id="T0")
    # Push a couple of sensor samples so the projection is non-trivial.
    for _ in range(3):
        t.tick(physical_state={"load": 1.0, "generation": 0.0,
                                  "voltage": 1.0})
    pred = t.predict_failure(horizon_steps=12)
    assert "projected_health_risk_score" in pred
    assert "projected_failure_probability" not in pred
