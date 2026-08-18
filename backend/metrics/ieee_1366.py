"""
ieee_1366.py — IEEE Std 1366-2012 reliability indices.

Why
---
A research-grade simulator must produce the same numbers a utility
reliability engineer reports to the regulator.  IEEE Std 1366-2012
defines the canonical reliability indices: SAIFI, SAIDI, CAIDI,
MAIFI, ASAI, ASIDI, ASIFI, plus auxiliary ENS / AENS / ACCI.
Each function below returns a float; arrays are accepted where the
underlying definition sums (e.g. per-customer interruption counts).

Every function is a pure scalar projection — no global state, no
hidden references.  Tested against published IEEE examples; the
common-sense edge cases (zero customers, zero interruptions) are
defined as ``0.0`` so dashboards never display ``NaN``.
"""
from __future__ import annotations

from typing import Iterable, Sequence


def _sum_or_zero(values: Iterable[float]) -> float:
    return float(sum(values))


# ----------------------------------------------------------------------
# Sustained interruption indices
# ----------------------------------------------------------------------

def saifi(
    customers_served: Sequence[float],
    sustained_interruptions: Sequence[float],
) -> float:
    """System Average Interruption Frequency Index.

    SAIDI = sum(C_i) / N_served, where C_i is the count of sustained
    interruptions (>5 min) experienced by customer i.  Vectorised over
    N total customers.
    """
    n = _sum_or_zero(customers_served)
    if n <= 0:
        return 0.0
    return _sum_or_zero(sustained_interruptions) / n


def saidi(
    customer_minutes_interrupted: Sequence[float],
    customers_served: Sequence[float],
) -> float:
    """System Average Interruption Duration Index (minutes)."""
    n = _sum_or_zero(customers_served)
    if n <= 0:
        return 0.0
    return _sum_or_zero(customer_minutes_interrupted) / n


def caidi(saidi_val: float, saifi_val: float) -> float:
    """Customer Average Interruption Duration Index (minutes)."""
    if saifi_val <= 0:
        return 0.0
    return saidi_val / saifi_val


def asai(
    customer_hours_available: Sequence[float],
    customer_hours_demanded: Sequence[float],
) -> float:
    """Average Service Availability Index (unitless, in [0, 1])."""
    demanded = _sum_or_zero(customer_hours_demanded)
    if demanded <= 0:
        return 1.0
    return max(0.0, min(1.0, _sum_or_zero(customer_hours_available) / demanded))


def asifi(
    load_connected_kva_impacted: Sequence[float],
    sustained_interruptions: Sequence[float],
    total_connected_kva: float,
) -> float:
    """Average System Interruption Frequency Index."""
    if total_connected_kva <= 0:
        return 0.0
    # Sum_k(k_impacted * N_interruptions_k) / Total_kVA
    total = 0.0
    for k, n in zip(load_connected_kva_impacted, sustained_interruptions):
        total += float(k) * float(n)
    return total / total_connected_kva


def asidi(
    load_connected_kva_impacted: Sequence[float],
    minutes_impacted: Sequence[float],
    total_connected_kva: float,
) -> float:
    """Average System Interruption Duration Index (minutes)."""
    if total_connected_kva <= 0:
        return 0.0
    total = 0.0
    for k, m in zip(load_connected_kva_impacted, minutes_impacted):
        total += float(k) * float(m)
    return total / total_connected_kva


# ----------------------------------------------------------------------
# Momentary interruption indices
# ----------------------------------------------------------------------

def maifi(
    momentary_interruptions: Sequence[float],
    customers_served: Sequence[float],
) -> float:
    """Momentary Average Interruption Frequency Index.

    MAIFI counts *momentary* (<5 min) events, excluded from SAIFI.
    Many utilities report this separately.
    """
    n = _sum_or_zero(customers_served)
    if n <= 0:
        return 0.0
    return _sum_or_zero(momentary_interruptions) / n


# ----------------------------------------------------------------------
# Energy-not-served and curtailment indices
# ----------------------------------------------------------------------

def ens_mwh(load_mw: Sequence[float], outage_minutes: Sequence[float]) -> float:
    """Energy Not Served in MWh — true time-integrated outage cost.

    ENS = sum(load_kw * outage_hours) / 1000
    """
    total = 0.0
    for p, m in zip(load_mw, outage_minutes):
        total += float(p) * float(m) / 60.0
    return total


def aens_mwh_per_customer(ens_val: float, customers_served: float) -> float:
    """Average ENS per customer served."""
    if customers_served <= 0:
        return 0.0
    return ens_val / customers_served


def acci(ens_val: float, customers_served: float) -> float:
    """Average Customer Curtailment Index (matches ACCI = ENS / customers)."""
    return aens_mwh_per_customer(ens_val, customers_served)