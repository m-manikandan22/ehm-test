"""test_n_minus_1.py — N-1 contingency analysis coverage (Stage 15)."""
from __future__ import annotations

import pytest

from simulation.grid import SmartGrid
from reliability.n_minus_1 import (
    N1Result, run_n_minus_1, n1_pass_criteria,
)


def test_n_minus_1_returns_n1result():
    g = SmartGrid()
    result = run_n_minus_1(g)
    assert isinstance(result, N1Result)


def test_n_minus_1_evaluates_all_poles_and_transformers():
    g = SmartGrid()
    candidates = [
        nid for nid, n in g.nodes.items()
        if getattr(n, "node_type", "") in ("pole", "transformer")
        and not getattr(n, "failed", False)
    ]
    result = run_n_minus_1(g)
    assert result.contingencies_evaluated == len(candidates)


def test_n_minus_1_does_not_mutate_input_grid():
    g = SmartGrid()
    failed_before = [nid for nid, n in g.nodes.items() if n.failed]
    run_n_minus_1(g, auto_remediate=False)
    failed_after = [nid for nid, n in g.nodes.items() if n.failed]
    assert failed_before == failed_after, "run_n_minus_1 mutated the input grid"


def test_n_minus_1_recovery_is_in_unit_interval():
    g = SmartGrid()
    result = run_n_minus_1(g)
    for target, rec in result.recovery_fraction.items():
        assert 0.0 <= rec <= 1.0, f"{target}: recovery {rec} outside [0, 1]"


def test_n_minus_1_worst_overload_tracks_max():
    g = SmartGrid()
    result = run_n_minus_1(g)
    overloads = [
        v.magnitude for vs in result.violations.values() for v in vs
        if v.kind == "overload"
    ]
    if overloads:
        assert result.worst_overload_pu >= max(overloads) - 1e-9


def test_n_minus_1_worst_undervoltage_tracks_min():
    g = SmartGrid()
    result = run_n_minus_1(g)
    undervoltages = [
        v.magnitude for vs in result.violations.values() for v in vs
        if v.kind == "undervoltage"
    ]
    if undervoltages:
        assert result.worst_undervoltage_pu <= min(undervoltages) + 1e-9


def test_n_minus_1_candidate_override():
    g = SmartGrid()
    poles = [
        nid for nid, n in g.nodes.items()
        if getattr(n, "node_type", "") == "pole"
        and not getattr(n, "failed", False)
    ]
    pick = poles[:3]
    result = run_n_minus_1(g, candidates=pick)
    assert result.contingencies_evaluated == len(pick)


def test_n_minus_1_summary_line_non_empty():
    g = SmartGrid()
    result = run_n_minus_1(g)
    assert "N-1 over" in result.summary_line


def test_n_minus_1_to_dict_is_serializable():
    g = SmartGrid()
    result = run_n_minus_1(g)
    d = result.to_dict()
    for k in ("contingencies_evaluated", "contingencies_violating",
              "violations", "recovery_fraction",
              "worst_overload_pu", "worst_undervoltage_pu",
              "summary_line"):
        assert k in d


def test_pass_criteria_returns_bool_and_list():
    g = SmartGrid()
    result = run_n_minus_1(g)
    passed, reasons = n1_pass_criteria(result)
    assert isinstance(passed, bool)
    assert isinstance(reasons, list)


def test_pass_criteria_on_passing_grid_returns_no_reasons():
    """If the default 49-node grid is well-designed, this should pass."""
    g = SmartGrid()
    result = run_n_minus_1(g)
    passed, reasons = n1_pass_criteria(result)
    # We don't *require* this to pass — the default grid may have a
    # overload or undervoltage on a minority of contingencies. We just
    # check the contract: if it passes, the reasons list is empty.
    if passed:
        assert reasons == []
