"""test_statistics.py — Unit tests for the centralised statistics utility."""
from __future__ import annotations

import math

import pytest

from metrics.statistics import (
    benjamini_hochberg,
    ci95,
    ci95_student,
    correct_pvalues,
    holm_bonferroni,
    is_significant,
    mad,
    mean,
    median,
    paired_t,
    paired_t_pvalue,
    paired_test_report,
    std,
    summarise,
    summarise_by_group,
)


def test_mean_empty_is_zero():
    assert mean([]) == 0.0


def test_mean_basic():
    assert mean([1, 2, 3, 4, 5]) == 3.0
    assert mean([0]) == 0.0


def test_std_requires_n_ge_2():
    assert std([]) == 0.0
    assert std([5]) == 0.0
    assert std([1, 2, 3, 4, 5]) > 0


def test_std_matches_statistics():
    import statistics
    assert std([1.5, 2.5, 3.5, 4.5]) == pytest.approx(statistics.stdev([1.5, 2.5, 3.5, 4.5]))


def test_median_basic():
    assert median([1, 2, 3, 4, 5]) == 3.0
    assert median([1, 2, 3, 4]) == 2.5
    assert median([]) == 0.0


def test_mad_constant_is_zero():
    assert mad([5, 5, 5, 5]) == 0.0


def test_mad_basic():
    assert mad([1, 2, 3]) == pytest.approx(2.0 / 3.0)


def test_ci95_n_lt_2_returns_mean():
    assert ci95([]) == (0.0, 0.0)
    assert ci95([7]) == (7, 7)


def test_ci95_brackets_mean():
    xs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    lo, hi = ci95(xs)
    assert lo < mean(xs) < hi


def test_ci95_student_wider_for_small_n():
    xs = [1, 2, 3, 4, 5]
    z_lo, z_hi = ci95(xs)
    t_lo, t_hi = ci95_student(xs)
    assert (z_hi - z_lo) < (t_hi - t_lo)  # Student's t = wider for n=5


def test_paired_t_identical_is_zero():
    assert paired_t([5, 5, 5], [5, 5, 5]) == 0.0


def test_paired_t_clear_difference_is_positive():
    assert paired_t([10, 20, 30], [1, 2, 3]) > 0


def test_paired_t_short_returns_zero():
    assert paired_t([1], [2]) == 0.0


def test_paired_t_pvalue_bounds():
    p = paired_t_pvalue(2.0, n=30)
    assert 0.0 <= p <= 1.0
    # Low t → high p
    assert paired_t_pvalue(0.1, n=30) > 0.5


def test_is_significant():
    assert is_significant(2.5, n=10) is True
    assert is_significant(0.5, n=10) is False


def test_summarise_keys():
    s = summarise([1, 2, 3, 4, 5])
    assert {"n", "mean", "std", "median", "min", "max", "ci95_low", "ci95_high"} == set(s.keys())
    assert s["n"] == 5
    assert s["min"] == 1
    assert s["max"] == 5


def test_summarise_by_group():
    values = [[1, 2, 3], [10, 20, 30]]
    groups = {"A": 0, "B": 1}
    out = summarise_by_group(groups, values)
    assert "A" in out and "B" in out
    assert out["A"]["mean"] == 2.0
    assert out["B"]["mean"] == 20.0


def test_self_test_runs():
    """Run the module's own self-test to ensure it passes."""
    from metrics import statistics as s
    assert s._self_test() is True


# ── Multiple-comparison correction (Stage 23 / EHM-MED-003) ────────

def test_bonferroni_correction():
    out = correct_pvalues([0.01, 0.02, 0.5, 0.8], method="bonferroni")
    assert pytest.approx(out[0], abs=1e-12) == 0.04
    assert pytest.approx(out[1], abs=1e-12) == 0.08
    # The cap is 1.0 for p-values that exceed 1.0 after multiplication
    assert out[2] == pytest.approx(1.0)
    assert out[3] == pytest.approx(1.0)


def test_holm_bonferroni_correction_basic():
    # Standard textbook example: 4 p-values
    pvals = [0.01, 0.02, 0.5, 0.8]
    out = holm_bonferroni(pvals)
    # The first (smallest) is multiplied by 4
    assert pytest.approx(out[0], abs=1e-12) == 0.04
    # The second is multiplied by 3, then enforced monotone >= previous
    assert out[1] >= 0.06 - 1e-12
    # The third is multiplied by 2
    assert out[2] >= 1.0 - 1e-9 or out[2] == 1.0
    # The fourth is multiplied by 1
    assert out[3] >= 0.8 - 1e-12


def test_holm_bonferroni_monotone_in_sorted_order():
    pvals = [0.10, 0.02, 0.05, 0.001, 0.30]
    out = holm_bonferroni(pvals)
    # When sorted by raw p, adjusted p must be non-decreasing
    sorted_idx = sorted(range(len(pvals)), key=lambda i: pvals[i])
    sorted_adj = [out[i] for i in sorted_idx]
    for i in range(1, len(sorted_adj)):
        assert sorted_adj[i] >= sorted_adj[i - 1] - 1e-12


def test_benjamini_hochberg_bounds():
    # BH must keep all adjusted p between raw p and 1.0
    pvals = [0.01, 0.04, 0.03, 0.005, 0.30]
    out = benjamini_hochberg(pvals)
    for raw, adj in zip(pvals, out):
        assert adj >= raw - 1e-12
        assert adj <= 1.0 + 1e-12


def test_bh_less_conservative_than_holm():
    # BH always <= Holm for the same p-values
    pvals = [0.001, 0.01, 0.02, 0.05, 0.10]
    bh = benjamini_hochberg(pvals)
    hb = holm_bonferroni(pvals)
    for b, h in zip(bh, hb):
        assert b <= h + 1e-12


def test_correct_pvalues_unknown_method():
    with pytest.raises(ValueError):
        correct_pvalues([0.01, 0.02], method="fdr_bh_xyz")


def test_correct_pvalues_empty():
    assert correct_pvalues([], method="bh") == []
    assert correct_pvalues([], method="holm") == []


def test_paired_test_report_basic():
    out = paired_test_report(
        [
            ([10, 20, 30, 40], [1, 2, 3, 4], "ENS"),
            ([10, 20, 30, 40], [2, 3, 4, 5], "SAIDI"),
        ],
        alpha=0.05,
        correction="bh",
    )
    assert out["n_comparisons"] == 2
    assert out["correction"] == "bh"
    for row in out["comparisons"]:
        assert "p_corrected" in row
        assert "significant_raw" in row
        assert "significant_corrected" in row


def test_paired_test_report_skips_invalid_pairs():
    # One comparison has n<2 → handled gracefully, marked invalid
    out = paired_test_report(
        [
            ([5], [5], "ONE_SAMPLE"),  # n<2, paired_comparison returns valid=False
            ([10, 20, 30], [1, 2, 3], "REAL"),
        ],
        correction="bh",
    )
    assert out["n_comparisons"] == 2
    labels = {row["label"] for row in out["comparisons"]}
    assert labels == {"ONE_SAMPLE", "REAL"}
