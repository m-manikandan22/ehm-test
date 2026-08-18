"""test_ieee_1366.py — IEEE 1366-2012 reliability indices."""
from __future__ import annotations

import pytest

from metrics.ieee_1366 import (
    saifi,
    saidi,
    caidi,
    maifi,
    asai,
    ens_mwh,
    aens_mwh_per_customer,
    acci,
    asidi,
    asifi,
)


def test_saifi_zero_customers_returns_zero():
    assert saifi([], []) == 0.0


def test_saifi_simple_case():
    # 1000 customers; in total they suffered 2000 interruptions.
    assert saifi([1000], [2000]) == 2.0


def test_saidi_simple_case():
    assert saidi([60_000], [1000]) == 60.0  # 60 min average


def test_caidi_zero_saifi_returns_zero():
    assert caidi(60.0, 0.0) == 0.0


def test_caidi_ratio():
    assert caidi(120.0, 4.0) == 30.0


def test_maifi_simple():
    assert maifi([300], [1000]) == 0.3


def test_asai_perfect_service():
    assert asai([100, 200], [100, 200]) == 1.0


def test_asai_total_outage_is_zero():
    assert asai([0, 0], [100, 200]) == 0.0


def test_ens_basic():
    # 1 MW for 60 min = 1 MWh.
    assert ens_mwh([1.0], [60.0]) == pytest.approx(1.0)


def test_ens_per_minute_conversion():
    # 2 MW for 30 min = 1 MWh.
    assert ens_mwh([2.0], [30.0]) == pytest.approx(1.0)


def test_aens_handles_zero_customers():
    assert aens_mwh_per_customer(10.0, 0) == 0.0


def test_acci_alias_of_aens():
    assert acci(10.0, 5) == aens_mwh_per_customer(10.0, 5)


def test_asifi_simple():
    # 100 kVA impacted × 3 interruptions / 100 kVA total = 3.
    assert asifi([100.0], [3.0], 100.0) == 3.0


def test_asidi_simple():
    assert asidi([100.0], [45.0], 100.0) == 45.0


def test_asifi_zero_total_kva():
    assert asifi([100.0], [3.0], 0.0) == 0.0
