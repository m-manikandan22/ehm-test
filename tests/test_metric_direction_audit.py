"""test_metric_direction_audit.py — Stage 41 metric-direction guard rails.

This test pins the *sign convention* of paired comparisons so future
contributors cannot silently flip it. If anyone changes the convention
of ``paired_comparison`` (e.g. ``mean(other - anchor)`` →
``mean(anchor - other)``), these tests will fail loudly.

Two sign conventions are supported, both pinned:
  1. ``paired_comparison(a, b)`` returns ``mean(a - b)``. This is the
     existing convention in ``backend/metrics/statistics.py``. We pin it
     here so it cannot drift.
  2. The Stage 41 audit artefacts (``paired_full.json``,
     ``paired.md``) currently use **opposite** conventions — this is a
     reporting hazard. We pin the *audit* convention as
     ``delta = other - anchor`` so the audit artefact is consistent.

Run:
    python -m pytest tests/test_metric_direction_audit.py -v
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from metrics.statistics import paired_comparison  # noqa: E402


def test_paired_comparison_sign_is_a_minus_b() -> None:
    """``paired_comparison`` returns ``mean(a - b)`` by contract."""
    # a larger than b → positive diff
    rep = paired_comparison([10, 20, 30, 40], [1, 2, 3, 4])
    assert rep["mean_difference"] > 0, rep
    # a smaller than b → negative diff
    rep = paired_comparison([1, 2, 3, 4], [10, 20, 30, 40])
    assert rep["mean_difference"] < 0, rep
    # identical → zero
    rep = paired_comparison([5, 5, 5], [5, 5, 5])
    assert rep["mean_difference"] == 0.0, rep


def test_lower_is_better_paired_diff_sign() -> None:
    """For a 'lower-is-better' metric, anchor larger means anchor is worse.

    If the anchor is ``rule_based`` and we pair ``(rule_based, dqn)``,
    a positive ``mean_difference`` (rule - dqn) means **DQN is better
    on a lower-is-better metric**.
    """
    rep = paired_comparison([1.355, 1.300, 1.400], [0.741, 0.700, 0.800])
    # rule - dqn = positive → DQN is better
    assert rep["mean_difference"] > 0
    # mean diff should be approximately 0.604 (1.352 - 0.747).
    assert abs(rep["mean_difference"] - 0.604) < 1e-3, rep["mean_difference"]


def test_higher_is_better_paired_diff_sign() -> None:
    """For a 'higher-is-better' metric, anchor smaller means anchor is worse."""
    rep = paired_comparison([0.95, 0.90, 0.85], [0.99, 0.98, 0.97])
    # anchor - other = negative → other is better (higher is better)
    assert rep["mean_difference"] < 0


def test_stage26_paired_full_convention() -> None:
    """Verify the Stage-26 paired_full.json uses (anchor, other) ordering.

    In the Stage-26 artefact, the label is "<other> vs <anchor>" but the
    arguments are passed as ``(a_vals=anchor, b_vals=other)``. This means
    ``mean_difference`` in the JSON equals ``mean(anchor - other)`` and
    therefore a POSITIVE value means the OTHER is better on a lower-is-
    better metric. We pin that here.
    """
    p = PROJECT_ROOT / "experiments/results/paper_final_stage26/statistics/paired_full.json"
    if not p.exists():
        # Stage 26 may have been cleaned. Skip rather than fail.
        import pytest
        pytest.skip(f"paired_full.json missing at {p}")
        return
    data = json.loads(p.read_text())
    ens_comps = [
        c for c in data["comparisons"]
        if c["label"].startswith("energy_not_served_mwh:")
        and "dqn_core_only" in c["label"]
    ]
    assert len(ens_comps) == 1, ens_comps
    comp = ens_comps[0]["report"]
    # mean_difference = anchor - other = rule_based - dqn_core_only > 0
    # means DQN is better on ENS.
    assert comp["mean_difference"] > 0, comp
    assert comp["label_a"] == "A" and comp["label_b"] == "B"
    # We can't easily inspect which is rule_based and which is dqn_core_only
    # without the caller, but the magnitude is what Stage-40 reports.


def test_stage26_audit_convention() -> None:
    """Pin the audit's sign convention as ``delta = other - anchor``."""
    p = PROJECT_ROOT / "experiments/results/stage26_paired_audit.json"
    if not p.exists():
        import pytest
        pytest.skip(f"audit file missing at {p}")
        return
    data = json.loads(p.read_text())
    # dqn_core_only ENS is lower than rule_based; delta should be negative.
    for row in data.get("paired", []):
        if "dqn_core_only" in row["controller_label"]:
            assert row["delta_energy_not_served_mwh_mean"] < 0, row


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
