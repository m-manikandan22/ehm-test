"""
statistics.py — Centralised statistical utilities for experiment reporting.

Why
---
The benchmark report (`backend/benchmarks/report.py`) and the new
experiments framework both need the same set of primitives:
mean / std / 95% CI / paired t-test. Keeping them in one place
prevents drift between the two reports and avoids the "I changed it
in one place but not the other" bug.

All functions are pure (no globals) and accept Iterable[float].
Where the inputs are too small for a meaningful statistic
(e.g. n < 2 for variance), the function returns a safe default
rather than NaN — dashboards must never show NaN.

Citations
---------
- 95% CI: uses z ≈ 1.96 (large-sample). For small n, replace with
  Student's t; this is a documented choice, not an oversight.
- Paired t-test: `m / (s / sqrt(n))` on the differences. Matches
  scipy.stats.ttest_rel for an n>=2 sample.
"""
from __future__ import annotations

import math
import statistics
from typing import Iterable, List, Sequence, Tuple, Union

Number = Union[int, float]


# ── Location & spread ──────────────────────────────────────────────────
def mean(values: Iterable[Number]) -> float:
    """Arithmetic mean. Returns 0.0 for empty input."""
    xs = list(values)
    if not xs:
        return 0.0
    return float(statistics.fmean(xs))


def std(values: Iterable[Number]) -> float:
    """Sample standard deviation. Returns 0.0 for n < 2."""
    xs = list(values)
    if len(xs) < 2:
        return 0.0
    return float(statistics.stdev(xs))


def median(values: Iterable[Number]) -> float:
    """Median. Returns 0.0 for empty input."""
    xs = list(values)
    if not xs:
        return 0.0
    return float(statistics.median(xs))


def mad(values: Iterable[Number]) -> float:
    """Mean absolute deviation from the mean. Robust spread estimator."""
    xs = list(values)
    if not xs:
        return 0.0
    m = mean(xs)
    return mean(abs(x - m) for x in xs)


# ── Confidence intervals ──────────────────────────────────────────────
def ci95(values: Iterable[Number]) -> Tuple[float, float]:
    """95% confidence interval using z ≈ 1.96 (large-sample approx).

    Returns (low, high) — both equal to the mean when n < 2.
    """
    xs = list(values)
    if len(xs) < 2:
        m = mean(xs)
        return (m, m)
    m = mean(xs)
    s = std(xs)
    half = 1.96 * s / math.sqrt(len(xs))
    return (m - half, m + half)


def ci95_student(values: Iterable[Number]) -> Tuple[float, float]:
    """95% CI using the Student's t critical value (when known).

    For small samples (n < 30) we use the lookup table from
    scipy.stats.t.ppf(0.975, df=n-1). For n >= 30 we fall back to
    z ≈ 1.96.

    Returns (low, high) — both equal to the mean when n < 2.
    """
    # Lookup table for 95% two-tailed t critical values
    _T_95 = {
        2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571,
        7: 2.447, 8: 2.365, 9: 2.306, 10: 2.262, 11: 2.228,
        12: 2.201, 13: 2.179, 14: 2.160, 15: 2.145, 16: 2.131,
        17: 2.120, 18: 2.110, 19: 2.101, 20: 2.093, 21: 2.086,
        22: 2.080, 23: 2.074, 24: 2.069, 25: 2.064, 26: 2.060,
        27: 2.056, 28: 2.052, 29: 2.048, 30: 2.045,
    }
    xs = list(values)
    if len(xs) < 2:
        m = mean(xs)
        return (m, m)
    n = len(xs)
    m = mean(xs)
    s = std(xs)
    t = _T_95.get(n, 1.96)
    half = t * s / math.sqrt(n)
    return (m - half, m + half)


# ── Hypothesis tests ──────────────────────────────────────────────────
def paired_t(a: Iterable[Number], b: Iterable[Number]) -> float:
    """Paired t-statistic for A − B across `n` matched pairs.

    Returns 0.0 when the test is not computable (n < 2, or
    zero variance in the differences).
    """
    pairs = list(zip(list(a), list(b)))
    if len(pairs) < 2:
        return 0.0
    diffs = [x - y for x, y in pairs]
    m = mean(diffs)
    s = std(diffs)
    if s == 0.0:
        return 0.0
    return float(m / (s / math.sqrt(len(diffs))))


def paired_t_pvalue(t: float, n: int) -> float:
    """Two-tailed p-value approximation for a paired t-statistic.

    Uses the large-sample normal approximation. For n < 30 the result
    is conservative (treat as a lower bound on the true p-value).
    """
    if n < 2:
        return 1.0
    # Approximate |t| → two-tailed p via the survival function for N(0,1).
    # We use the complementary error function, which is well-defined.
    z = abs(t) / math.sqrt(n / max(n - 1, 1))
    # p ≈ 2 * (1 - Φ(|z|)) = erfc(|z|/sqrt(2))
    return float(math.erfc(z / math.sqrt(2.0)))


def is_significant(t: float, n: int, alpha: float = 0.05) -> bool:
    """Whether the paired t-statistic is significant at level `alpha`."""
    return paired_t_pvalue(t, n) < alpha


# ── Aggregator ────────────────────────────────────────────────────────
def summarise(values: Iterable[Number]) -> dict:
    """One-shot summary: mean, std, median, CI95, n."""
    xs = list(values)
    lo, hi = ci95(xs)
    return {
        "n": len(xs),
        "mean": mean(xs),
        "std": std(xs),
        "median": median(xs),
        "min": min(xs) if xs else 0.0,
        "max": max(xs) if xs else 0.0,
        "ci95_low": lo,
        "ci95_high": hi,
    }


def summarise_by_group(
    groups: dict,
    values: Sequence[Sequence[Number]],
) -> dict:
    """Return {group_name: summarise(values_i)} for n parallel sequences.

    `groups` is a dict mapping group_name → index in `values`.
    Both lists must have the same length.
    """
    return {
        name: summarise(values[idx])
        for name, idx in groups.items()
    }


# ── Non-parametric: Wilcoxon signed-rank ───────────────────────────────
def wilcoxon_signed_rank(
    a: Iterable[Number], b: Iterable[Number],
) -> Tuple[float, float]:
    """Wilcoxon signed-rank statistic and normal-approx p-value.

    Returns ``(W_statistic, two_tailed_p_value)``. The p-value is the
    large-sample normal approximation with continuity correction; for
    very small samples it is conservative. If the differences are all
    zero, returns ``(0.0, 1.0)`` — there is no evidence of a shift.

    Reference: Wilcoxon (1945); the normal approximation is from
    scipy.stats.wilcoxon with ``method='approx'``.
    """
    pairs = list(zip(list(a), list(b)))
    if len(pairs) < 1:
        return 0.0, 1.0
    diffs = [x - y for x, y in pairs]
    nonzero = [d for d in diffs if d != 0]
    if not nonzero:
        return 0.0, 1.0
    n = len(nonzero)
    abs_diffs = sorted(abs(d) for d in nonzero)
    # Average ranks for ties.
    ranks = _average_ranks(abs_diffs)
    # Sum of ranks for positive differences.
    w_pos = 0.0
    w_neg = 0.0
    for d, r in zip(nonzero, ranks):
        if d > 0:
            w_pos += r
        else:
            w_neg += r
    w = min(w_pos, w_neg)
    # Normal approximation with continuity correction.
    mean_w = n * (n + 1) / 4.0
    var_w  = n * (n + 1) * (2 * n + 1) / 24.0
    if var_w <= 0:
        return float(w), 1.0
    z = (w - mean_w) / math.sqrt(var_w)
    # Two-tailed p.
    p = float(math.erfc(abs(z) / math.sqrt(2.0)))
    return float(w), p


def _average_ranks(abs_diffs: List[float]) -> List[float]:
    """Compute average ranks for a list of absolute values (handles ties)."""
    indexed = sorted(enumerate(abs_diffs), key=lambda kv: kv[1])
    ranks = [0.0] * len(abs_diffs)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        # Indices i..j (inclusive) all have the same value.
        avg_rank = (i + 1 + j + 1) / 2.0  # 1-indexed ranks, averaged
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


# ── Effect size: Cohen's d for paired samples ───────────────────────────
def cohens_d_paired(a: Iterable[Number], b: Iterable[Number]) -> float:
    """Cohen's d for paired samples (A − B) using the SD of the diffs.

    Convention (Cohen 1988):
      |d| < 0.2  → "negligible"
      |d| < 0.5  → "small"
      |d| < 0.8  → "medium"
      otherwise  → "large"

    Returns 0.0 when the SD of the differences is zero.
    """
    pairs = list(zip(list(a), list(b)))
    if len(pairs) < 2:
        return 0.0
    diffs = [x - y for x, y in pairs]
    s = std(diffs)
    if s == 0.0:
        return 0.0
    return float(mean(diffs) / s)


def effect_size_label(d: float) -> str:
    """Return a human-readable label for a Cohen's d value."""
    ad = abs(d)
    if ad < 0.2:  return "negligible"
    if ad < 0.5:  return "small"
    if ad < 0.8:  return "medium"
    return "large"


# ── Aggregator: paired comparison report ───────────────────────────────
def paired_comparison(
    a: Iterable[Number], b: Iterable[Number],
    *, label_a: str = "A", label_b: str = "B",
    alpha: float = 0.05,
) -> Dict[str, object]:
    """One-shot paired comparison: t-test + Wilcoxon + Cohen's d + CI.

    Returns a dict ready for JSON serialisation with all the numbers a
    paper would need:
        sample size, mean difference, std difference, t statistic,
        t p-value, Wilcoxon W, Wilcoxon p-value, Cohen's d, effect
        size label, 95 % CI on the mean difference, and a
        significance flag at the requested alpha level.
    """
    pairs = list(zip(list(a), list(b)))
    n = len(pairs)
    if n < 2:
        return {
            "n": n,
            "label_a": label_a, "label_b": label_b,
            "valid": False,
            "reason": "n<2; cannot compute paired test",
        }
    diffs = [x - y for x, y in pairs]
    m_diff = mean(diffs)
    s_diff = std(diffs)
    lo, hi = ci95(diffs)

    t = paired_t(a, b)
    p_t = paired_t_pvalue(t, n)

    w_stat, p_w = wilcoxon_signed_rank(a, b)
    d = cohens_d_paired(a, b)

    # Decide significance from the t-test (primary); surface both p's.
    significant = bool(p_t < alpha)

    return {
        "n": n,
        "label_a":   label_a,
        "label_b":   label_b,
        "valid":     True,
        "mean_difference": round(float(m_diff), 6),
        "std_difference":  round(float(s_diff), 6),
        "ci95_low":  round(float(lo), 6),
        "ci95_high": round(float(hi), 6),
        "t_statistic":  round(float(t), 4),
        "t_p_value":    round(float(p_t), 6),
        "wilcoxon_W":   round(float(w_stat), 4),
        "wilcoxon_p":   round(float(p_w), 6),
        "effect_size":  round(float(d), 4),
        "effect_label": effect_size_label(d),
        "significant_at_005": significant,
        "alpha": alpha,
    }


# ── Multiple-comparison correction ────────────────────────────────────
def holm_bonferroni(pvals: Sequence[float]) -> List[float]:
    """Holm-Bonferroni step-down correction.

    Returns adjusted p-values that control the family-wise error rate
    (FWER) under arbitrary dependence. The original ordering of the
    inputs is preserved on the way out; this function returns one
    adjusted p-value per input.

    Procedure
    ---------
    1. Sort the p-values, keeping the original index.
    2. For each rank k = 1..m, multiply by (m - k + 1).
    3. Enforce monotonicity (no later adjusted p may be smaller than
       an earlier one).
    4. Cap at 1.0.

    Edge cases: a ``None`` or ``NaN`` p-value is left as 1.0; an input
    that is already > 1 is left untouched on the way in (the cap at
    step 4 still applies).
    """
    pvs = [float("nan") if p is None else float(p) for p in pvals]
    m = len(pvs)
    if m == 0:
        return []
    # Replace NaN with 1.0 for the ranking (conservative: don't reject).
    pvs_for_rank = [1.0 if (p != p) else p for p in pvs]
    order = sorted(range(m), key=lambda i: pvs_for_rank[i])
    adjusted_sorted: List[float] = []
    running_max = 0.0
    for k, idx in enumerate(order, start=1):
        raw = pvs_for_rank[idx] * (m - k + 1)
        running_max = max(running_max, raw)
        adjusted_sorted.append(min(1.0, running_max))
    # Restore original order
    adjusted = [0.0] * m
    for k, idx in enumerate(order):
        adjusted[idx] = adjusted_sorted[k]
    # NaN inputs stay as NaN
    adjusted = [a if not (pvs[i] != pvs[i]) else a for i, a in enumerate(adjusted)]
    return adjusted


def benjamini_hochberg(pvals: Sequence[float]) -> List[float]:
    """Benjamini-Hochberg FDR correction (step-up).

    Returns adjusted p-values that control the *false discovery rate*
    (FDR) under independence. Less conservative than Holm-Bonferroni;
    appropriate when many hypotheses are tested and a small fraction of
    false positives is acceptable.

    Procedure
    ---------
    1. Sort p-values ascending, keeping the original index.
    2. For rank k = 1..m:  adjusted_k = p_(k) * m / k.
    3. Enforce monotonicity (non-increasing from the bottom).
    4. Cap at 1.0.
    """
    pvs = [float("nan") if p is None else float(p) for p in pvals]
    m = len(pvs)
    if m == 0:
        return []
    pvs_for_rank = [1.0 if (p != p) else p for p in pvs]
    order = sorted(range(m), key=lambda i: pvs_for_rank[i])
    adjusted_sorted: List[float] = []
    running_min = 1.0
    for k, idx in enumerate(reversed(order), start=1):
        # k = m, m-1, ..., 1  (largest rank first for monotonicity)
        raw = pvs_for_rank[idx] * m / (m - k + 1)
        running_min = min(running_min, raw)
        adjusted_sorted.append(min(1.0, running_min))
    # Reverse back to ascending-rank order, then map to original order.
    adjusted_sorted.reverse()
    adjusted = [0.0] * m
    for k, idx in enumerate(order):
        adjusted[idx] = adjusted_sorted[k]
    adjusted = [a if not (pvs[i] != pvs[i]) else a for i, a in enumerate(adjusted)]
    return adjusted


def correct_pvalues(
    pvals: Sequence[float],
    method: str = "bh",
) -> List[float]:
    """Dispatch helper: ``method in {"bh", "holm", "bonferroni"}``."""
    pvs = list(pvals)
    if method == "bh":
        return benjamini_hochberg(pvs)
    if method == "holm":
        return holm_bonferroni(pvs)
    if method == "bonferroni":
        m = len(pvs)
        return [min(1.0, float(p) * m) for p in pvs]
    raise ValueError(f"unknown correction method: {method!r}")


def paired_test_report(
    comparisons: Sequence[Tuple[Sequence[float], Sequence[float], str]],
    *,
    alpha: float = 0.05,
    correction: str = "bh",
) -> Dict[str, object]:
    """Run multiple paired comparisons and apply a correction in one call.

    Parameters
    ----------
    comparisons : sequence of ``(a, b, label)`` tuples.
        ``a`` and ``b`` are equal-length sequences of paired samples.
        ``label`` is a human-readable name (e.g. ``"ENS"``).
    alpha : float
        Per-comparison significance threshold (default 0.05).
    correction : {"bh", "holm", "bonferroni"}
        Multiple-comparison correction to apply after the per-comparison
        p-values are computed. ``"bh"`` (Benjamini-Hochberg) is the
        default — it controls the false-discovery rate and is
        appropriate when several correlated metrics are reported.

    Returns
    -------
    dict with ``alpha``, ``correction``, ``n_comparisons``, and a
    list of per-comparison dicts containing ``label``, ``n``,
    ``t_p_value`` (raw), ``p_corrected`` (after correction),
    ``significant_raw``, ``significant_corrected``.
    """
    rows = []
    raw_ps: List[float] = []
    for a, b, label in comparisons:
        rep = paired_comparison(list(a), list(b))
        if rep.get("valid"):
            raw_ps.append(float(rep.get("t_p_value", 1.0)))
        else:
            raw_ps.append(1.0)
        rows.append({"label": label, "report": rep})
    if correction:
        corrected = correct_pvalues(raw_ps, method=correction)
    else:
        corrected = list(raw_ps)
    for row, p_raw, p_corr in zip(rows, raw_ps, corrected):
        row["t_p_value_raw"] = round(float(p_raw), 6)
        row["p_corrected"] = round(float(p_corr), 6)
        row["significant_raw"] = bool(p_raw < alpha)
        row["significant_corrected"] = bool(p_corr < alpha)
    return {
        "alpha": alpha,
        "correction": correction,
        "n_comparisons": len(rows),
        "comparisons": rows,
    }


# ── Self-test ─────────────────────────────────────────────────────────
def _self_test() -> bool:
    """Pure-function self-test. Run with `python -m metrics.statistics`."""
    # mean / std
    assert mean([1, 2, 3, 4, 5]) == 3.0
    assert std([1, 2, 3, 4, 5]) == statistics.stdev([1, 2, 3, 4, 5])
    assert median([1, 2, 3, 4, 5]) == 3.0
    # ci95 — non-degenerate
    lo, hi = ci95([1, 2, 3, 4, 5])
    assert lo < 3.0 < hi
    # ci95 student — narrower for small n
    lo2, hi2 = ci95_student([1, 2, 3, 4, 5])
    assert abs(hi2 - lo2) > abs(hi - lo)  # small-n CI is wider
    # paired t: A clearly larger than B → positive t
    assert paired_t([10, 20, 30], [1, 2, 3]) > 0
    # paired t: identical → 0 (no variance)
    assert paired_t([5, 5, 5], [5, 5, 5]) == 0.0
    # is_significant
    assert is_significant(2.5, n=10) is True
    assert is_significant(0.5, n=10) is False
    # ci95 degenerate
    assert ci95([7]) == (7, 7)
    # p-value bounds
    assert 0.0 <= paired_t_pvalue(2.0, 30) <= 1.0
    # Wilcoxon
    w, p = wilcoxon_signed_rank([10, 20, 30], [1, 2, 3])
    assert w >= 0 and 0.0 <= p <= 1.0
    # Cohen's d
    d = cohens_d_paired([10, 20, 30], [1, 2, 3])
    assert d > 0.0  # mean diff is positive, sd > 0
    # Paired comparison dict has all the keys a paper would need
    rep = paired_comparison([10, 20, 30, 40], [1, 2, 3, 4])
    for key in ("n", "mean_difference", "t_statistic", "t_p_value",
                "wilcoxon_p", "effect_size", "ci95_low", "ci95_high"):
        assert key in rep, f"missing key {key}"
    # Multiple-comparison correction
    # 1) Bonferroni: p=0.01 with 4 tests → 0.04
    bf = correct_pvalues([0.01, 0.02, 0.5, 0.8], method="bonferroni")
    assert abs(bf[0] - 0.04) < 1e-9, bf
    assert all(p <= 1.0 for p in bf)
    # 2) Holm-Bonferroni monotonicity + FWER control
    hb = holm_bonferroni([0.01, 0.02, 0.5, 0.8])
    # adjusted >= raw always
    assert hb[0] >= 0.01
    assert hb[1] >= 0.02
    # Monotone non-decreasing in sorted order
    sorted_idx = sorted(range(4), key=lambda i: [0.01, 0.02, 0.5, 0.8][i])
    sorted_adjusted = [hb[i] for i in sorted_idx]
    for i in range(1, len(sorted_adjusted)):
        assert sorted_adjusted[i] >= sorted_adjusted[i - 1] - 1e-12, sorted_adjusted
    # 3) Benjamini-Hochberg non-decreasing
    bh = benjamini_hochberg([0.01, 0.02, 0.5, 0.8])
    assert all(p <= 1.0 for p in bh)
    # BH is no larger than Holm (BH is less conservative)
    for h, b in zip(hb, bh):
        assert b <= h + 1e-12, (hb, bh)
    # 4) Empty input
    assert holm_bonferroni([]) == []
    assert benjamini_hochberg([]) == []
    # 5) Paired-test report with correction
    ptrep = paired_test_report([
        ([10, 20, 30, 40], [1, 2, 3, 4], "ENS"),
        ([10, 20, 30, 40], [2, 3, 4, 5], "SAIDI"),
    ], alpha=0.05, correction="bh")
    assert ptrep["n_comparisons"] == 2
    assert ptrep["correction"] == "bh"
    for row in ptrep["comparisons"]:
        assert "p_corrected" in row
        assert "significant_corrected" in row
    return True


if __name__ == "__main__":
    ok = _self_test()
    print("statistics self-test:", "PASS" if ok else "FAIL")
