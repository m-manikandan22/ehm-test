"""test_validity.py — ValidityReport priority behavior.

Verifies that when multiple invalid signals fire, the more-specific
reason (e.g. CONTROLLER_FAILED) outranks the generic topology check
(TOPOLOGY_INCONSISTENT). See EHM-HIGH-008.
"""
from __future__ import annotations

import pytest

from experiments.validity import (
    InvalidRunReason,
    ValidityReport,
    check_run_validity,
    _INVALID_REASON_PRIORITY,
)


# ── Priority table is well-defined ────────────────────────────────────────────
def test_all_reasons_have_a_priority():
    """Every InvalidRunReason must have a numeric priority."""
    for r in InvalidRunReason:
        assert r in _INVALID_REASON_PRIORITY, f"missing priority for {r.value}"


def test_specific_reasons_outrank_topology():
    """FLISR failures must outrank empty-topology."""
    assert (
        _INVALID_REASON_PRIORITY[InvalidRunReason.CONTROLLER_FAILED]
        > _INVALID_REASON_PRIORITY[InvalidRunReason.TOPOLOGY_INCONSISTENT]
    )
    assert (
        _INVALID_REASON_PRIORITY[InvalidRunReason.UNEXPECTED_EXCEPTION]
        > _INVALID_REASON_PRIORITY[InvalidRunReason.TOPOLOGY_INCONSISTENT]
    )
    assert (
        _INVALID_REASON_PRIORITY[InvalidRunReason.SOLVER_FAILURE]
        > _INVALID_REASON_PRIORITY[InvalidRunReason.TOPOLOGY_INCONSISTENT]
    )


# ── First mark_invalid wins ties ───────────────────────────────────────────
def test_first_mark_invalid_wins_on_tie():
    rep = ValidityReport()
    rep.mark_invalid(InvalidRunReason.NAN_VALUE, step=2)
    # Same priority as NAN_VALUE — earliest wins.
    rep.mark_invalid(InvalidRunReason.INFINITY_VALUE, step=3)
    assert rep.invalid_reason == "NAN_VALUE"
    assert rep.timestamp_step == 2


# ── Higher-priority reason overrides ─────────────────────────────────────────
def test_higher_priority_reason_overrides():
    rep = ValidityReport()
    rep.mark_invalid(InvalidRunReason.TOPOLOGY_INCONSISTENT, step=0)
    rep.mark_invalid(InvalidRunReason.CONTROLLER_FAILED, step=5)
    assert rep.invalid_reason == "CONTROLLER_FAILED"
    assert rep.timestamp_step == 5


# ── Lower-priority reason does NOT override ──────────────────────────────────
def test_lower_priority_reason_does_not_override():
    rep = ValidityReport()
    rep.mark_invalid(InvalidRunReason.CONTROLLER_FAILED, step=5)
    rep.mark_invalid(InvalidRunReason.TOPOLOGY_INCONSISTENT, step=10)
    assert rep.invalid_reason == "CONTROLLER_FAILED"


# ── check_run_validity: empty topology ───────────────────────────────────────
def test_empty_topology_marks_invalid():
    class _Empty:
        nodes = {}
        graph = None
    rep = check_run_validity(_Empty())
    assert rep.valid is False
    assert rep.invalid_reason == "TOPOLOGY_INCONSISTENT"


# ── check_run_validity: impossible voltage ───────────────────────────────────
def test_impossible_voltage_marks_invalid():
    class _BadNode:
        voltage = 5.0   # outside the [-0.5, 2.5] envelope
        failed = False
        isolated = False
    class _G:
        nodes = {"X": _BadNode()}
        graph = None
    rep = check_run_validity(_G())
    assert rep.valid is False
    assert rep.invalid_reason == "IMPOSSIBLE_VOLTAGE"


# ── check_run_validity: NaN voltage ──────────────────────────────────────────
def test_nan_voltage_marks_invalid():
    class _BadNode:
        voltage = float("nan")
        failed = False
        isolated = False
    class _G:
        nodes = {"X": _BadNode()}
        graph = None
    rep = check_run_validity(_G())
    assert rep.valid is False
    assert rep.invalid_reason == "NAN_VALUE"


# ── check_run_validity: healthy grid passes ──────────────────────────────────
def test_healthy_grid_passes():
    class _GoodNode:
        voltage = 1.0
        failed = False
        isolated = False
    class _G:
        nodes = {"X": _GoodNode(), "Y": _GoodNode()}
        graph = None
    rep = check_run_validity(_G())
    assert rep.valid is True
    assert rep.invalid_reason is None