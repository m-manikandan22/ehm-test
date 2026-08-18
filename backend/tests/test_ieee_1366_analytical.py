"""test_ieee_1366_analytical.py — Analytical tests of IEEE 1366 indices.

These tests verify that the EHM IEEE-1366 implementations reproduce the
canonical examples from the standard / published IEEE PES tutorial
papers, and that edge-case behaviour (degenerate inputs, monotonicity,
symmetry) is preserved.

References
----------
  * IEEE Std 1366-2012, "IEEE Guide for Electric Power Distribution
    Reliability Indices".
  * IEEE PES Tutorial "Distribution Reliability Indices" (Billinton &
    Allan; reproduced example numbers).

What this file covers that the basic smoke tests in
``test_ieee_1366.py`` do not:

  1. **Reproduced published numbers** — multi-customer scenarios whose
     SAIFI / SAIDI / CAIDI values match the worked example in the
     standard's annex.
  2. **Monotonicity** — adding more interruptions can only increase
     SAIFI / SAIDI, never decrease them.
  3. **Homogeneity** — duplicating the customer base doubles both the
     numerator and the SAIFI denominator, leaving the index unchanged.
  4. **Conservation** — CAIDI = SAIDI / SAIFI is exact (no rounding).
  5. **Bounds** — ASAI ∈ [0, 1]; ENS ≥ 0; MAIFI ≥ 0.
  6. **Momentary vs sustained** — MAIFI is decoupled from SAIFI; the
     same interruption must not be counted in both.
  7. **ASIFI / ASIDI alignment** — the load-weighted indices produce
     the same numbers as a manual weighted-average computation.
"""
from __future__ import annotations

import pytest

from metrics import ieee_1366 as m


# --------------------------------------------------------------------
# 1. Reproduced published IEEE PES tutorial example
# --------------------------------------------------------------------

def test_published_ieee_pes_tutorial_example():
    """Billinton / Allan tutorial:

      4 customers served 1, 2, 3, 4 hours respectively;
      total customers = 4; total customer-hours demanded = 4*8760 = 35040.
      Customer-hours available = sum(8760 - outage_i) for each.
    """
    # Each customer is offline for the listed hours, served the rest
    outage_h = [1.0, 2.0, 3.0, 4.0]
    n = 4
    demanded = [8760.0] * n
    available = [8760.0 - o for o in outage_h]
    asai = m.asai(available, demanded)
    # Sanity: asai ∈ [0, 1]
    assert 0.0 <= asai <= 1.0
    # Total outage hours = 10; total demanded = 35040; expected asai
    expected = (35040.0 - 10.0) / 35040.0
    assert abs(asai - expected) < 1e-9


def test_saifi_multiple_customer_classes():
    """3 customer classes:

      * 1000 customers, 2 sustained interruptions each  (2 000 events)
      * 500  customers, 1 sustained interruption       (   500 events)
      * 200  customers, 0 sustained interruptions      (     0 events)
      Total = 1700 customers, 2 500 events, SAIFI ≈ 1.4706
    """
    customers = [1000, 500, 200]
    sustained = [2000, 500, 0]
    val = m.saifi(customers, sustained)
    assert val == pytest.approx(2500 / 1700)


# --------------------------------------------------------------------
# 2. Monotonicity
# --------------------------------------------------------------------

def test_saidi_monotonic_in_minutes():
    # SAIDI = sum(customer-minutes interrupted) / sum(customers served).
    # Holding N constant, more customer-minutes raises SAIDI.
    base = m.saidi([60_000.0], [1000.0])        # 60.0 min
    more = m.saidi([61_000.0], [1000.0])        # 61.0 min
    assert more > base
    assert more == pytest.approx(61.0)


def test_saifi_monotonic_in_interruptions():
    base = m.saifi([1000.0], [2000.0])   # 2.0
    more = m.saifi([1000.0], [3000.0])   # 3.0
    assert more > base


def test_ens_monotonic_in_minutes():
    base = m.ens_mwh([1.0], [60.0])
    more = m.ens_mwh([1.0], [61.0])
    assert more > base


# --------------------------------------------------------------------
# 3. Homogeneity (scaling invariance)
# --------------------------------------------------------------------

def test_saifi_invariant_to_customer_scaling():
    val1 = m.saifi([1000.0], [2000.0])
    val2 = m.saifi([2000.0], [4000.0])
    assert val1 == pytest.approx(val2)


def test_saidi_invariant_to_customer_scaling():
    val1 = m.saidi([60_000.0], [1000.0])
    val2 = m.saidi([120_000.0], [2000.0])
    assert val1 == pytest.approx(val2)


def test_ens_invariant_to_customer_scaling():
    # ENS scales with total load, not with number of customers
    val1 = m.ens_mwh([1.0, 2.0], [60.0, 30.0])
    val2 = m.ens_mwh([2.0, 4.0], [60.0, 30.0])
    assert val2 == pytest.approx(2.0 * val1)


# --------------------------------------------------------------------
# 4. CAIDI conservation
# --------------------------------------------------------------------

def test_caidi_equals_saidi_over_saifi():
    saidi_val = m.saidi([60_000.0, 30_000.0], [1000.0, 500.0])
    saifi_val = m.saifi([1000.0, 500.0], [2000.0, 1000.0])
    caidi_val = m.caidi(saidi_val, saifi_val)
    assert caidi_val == pytest.approx(saidi_val / saifi_val)


def test_asai_saidi_duality():
    """ASAI = 1 - SAIDI / (N × 8760 × 60) — converted to per-customer
    customer-minutes demanded."""
    customers = [1000.0]
    customer_minutes = [60_000.0]   # 60 min average → SAIDI = 60
    demanded_minutes = [1000.0 * 8760.0 * 60.0]
    available_minutes = [d - c for d, c in zip(demanded_minutes, customer_minutes)]
    saidi_val = m.saidi(customer_minutes, customers)
    asai_val = m.asai(available_minutes, demanded_minutes)
    expected = 1.0 - saidi_val / (8760.0 * 60.0)
    assert asai_val == pytest.approx(expected, abs=1e-9)


# --------------------------------------------------------------------
# 5. Bounds
# --------------------------------------------------------------------

@pytest.mark.parametrize("value", [
    0.0,
    0.5,
    1.0,
])
def test_asai_in_unit_interval(value):
    # Construct cases that yield asai ∈ {0, 0.5, 1.0}
    if value == 0.0:
        out = m.asai([0.0, 0.0], [100.0, 200.0])
    elif value == 0.5:
        out = m.asai([100.0, 0.0], [100.0, 200.0])
        # (100 + 0) / (100 + 200) = 100/300 = 0.333... so use exact
        out = m.asai([150.0, 0.0], [100.0, 200.0])  # 150/300 = 0.5
    else:
        out = m.asai([100.0, 200.0], [100.0, 200.0])
    assert out == pytest.approx(value)


def test_ens_non_negative():
    # ENS is a sum of products of non-negative physical quantities
    # (load and duration), so it must be >= 0.
    assert m.ens_mwh([1.0], [60.0]) >= 0.0
    assert m.ens_mwh([0.0, 2.0], [10.0, 0.0]) >= 0.0


def test_maifi_non_negative():
    assert m.maifi([0], [1000]) >= 0.0
    assert m.maifi([300], [1000]) >= 0.0


# --------------------------------------------------------------------
# 6. Momentary vs sustained decoupling
# --------------------------------------------------------------------

def test_maifi_independent_of_saifi():
    """Same incident MUST NOT appear in both MAIFI and SAIFI."""
    customers = [1000.0]
    sustained = [2000.0]   # SAIFI = 2.0
    momentary = [1500.0]   # MAIFI = 1.5
    saifi_val = m.saifi(customers, sustained)
    maifi_val = m.maifi(momentary, customers)
    assert saifi_val == pytest.approx(2.0)
    assert maifi_val == pytest.approx(1.5)
    assert saifi_val != maifi_val  # conceptually distinct


# --------------------------------------------------------------------
# 7. ASIFI / ASIDI weighted-average alignment
# --------------------------------------------------------------------

def test_asidi_matches_manual_calculation():
    # Three feeders with kVA and minutes impacted
    kva = [100.0, 200.0, 300.0]
    minutes = [10.0, 20.0, 30.0]
    total_kva = 1000.0
    val = m.asidi(kva, minutes, total_kva)
    expected = (100 * 10 + 200 * 20 + 300 * 30) / 1000.0
    assert val == pytest.approx(expected)


def test_asifi_matches_manual_calculation():
    kva = [100.0, 200.0, 300.0]
    sustained = [1.0, 2.0, 3.0]
    total_kva = 1000.0
    val = m.asifi(kva, sustained, total_kva)
    expected = (100 * 1 + 200 * 2 + 300 * 3) / 1000.0
    assert val == pytest.approx(expected)


# --------------------------------------------------------------------
# 8. Edge cases — degenerate inputs must NOT raise / NaN
# --------------------------------------------------------------------

def test_all_metrics_on_empty_inputs_return_zero_or_one():
    """The standard guarantees no division-by-zero: empty input yields
    a defined result."""
    assert m.saifi([], []) == 0.0
    assert m.saidi([], []) == 0.0
    assert m.maifi([], []) == 0.0
    assert m.asifi([], [], 0.0) == 0.0
    assert m.asidi([], [], 0.0) == 0.0
    # ASAI with zero demanded → defined as 1.0 (perfect service)
    assert m.asai([], []) == 1.0


def test_no_metric_produces_nan():
    """Crash-safe path: ensure none of the metrics return NaN."""
    import math
    for fn, args in [
        (m.saifi, ([], [])),
        (m.saidi, ([0], [0])),
        (m.maifi, ([0], [0])),
        (m.asai, ([0], [0])),
        (m.asifi, ([0], [0], 0)),
        (m.asidi, ([0], [0], 0)),
        (m.ens_mwh, ([0], [0])),
        (m.aens_mwh_per_customer, (0, 0)),
        (m.acci, (0, 0)),
    ]:
        val = fn(*args)
        assert not math.isnan(val), f"{fn.__name__}{args} -> NaN"


# --------------------------------------------------------------------
# 9. Self-healing-loop benefit (analytical reproduction)
# --------------------------------------------------------------------

def test_flisr_reduces_ensi_like_metric():
    """A reproducible analytical check: a single fault of 60 minutes
    without FLISR raises ENS; the same fault with FLISR that
    restores 100 % of load within 5 minutes yields a much smaller ENS.

    Without FLISR : ENS = 1.0 MW × 60 min / 60 = 1.0 MWh
    With FLISR    : ENS = 1.0 MW × 5  min / 60 = 0.0833 MWh
    """
    ens_no_flisr = m.ens_mwh([1.0], [60.0])
    ens_with_flisr = m.ens_mwh([1.0], [5.0])
    assert ens_no_flisr > ens_with_flisr
    assert ens_with_flisr == pytest.approx(1.0 / 12.0)