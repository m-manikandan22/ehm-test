"""
grid_kpis.py — extended KPI helpers beyond IEEE 1366.

Why
---
IEEE 1366 covers reliability.  A research paper also wants
voltage-stability, frequency-stability, renewable penetration,
battery utilisation, and a composite reliability index.  These
are derived from a "node view" — a list of ``GridNode``-like
objects with the relevant attributes.
"""
from __future__ import annotations

from typing import Any, Iterable, Sequence


def _safe_div(a: float, b: float) -> float:
    return float(a) / float(b) if float(b) > 0 else 0.0


def voltage_stability_index(nodes: Iterable[Any]) -> float:
    """Fraction of buses with voltage in [0.95, 1.05] pu."""
    ns = list(nodes)
    if not ns:
        return 1.0
    in_band = sum(1 for n in ns
                  if 0.95 <= float(getattr(n, "voltage", 1.0)) <= 1.05)
    return in_band / len(ns)


def frequency_stability_index(nodes: Iterable[Any]) -> float:
    """Fraction of buses with frequency in [49.8, 50.2] Hz."""
    ns = list(nodes)
    if not ns:
        return 1.0
    in_band = sum(1 for n in ns
                  if 49.8 <= float(getattr(n, "frequency", 50.0)) <= 50.2)
    return in_band / len(ns)


def renewable_penetration_pct(nodes: Iterable[Any]) -> float:
    """Renewable fraction of total generation, in [0, 100]."""
    ns = list(nodes)
    if not ns:
        return 0.0
    total = 0.0
    ren = 0.0
    for n in ns:
        g = float(getattr(n, "generation", 0.0))
        total += g
        if getattr(n, "node_type", "") in {
            "solar_farm", "wind_farm", "generator_solar", "generator_wind",
        }:
            ren += g
    return _safe_div(ren, total) * 100.0


def battery_utilisation_pct(nodes: Iterable[Any]) -> float:
    """Average SOC across storage nodes."""
    socs = [float(getattr(n, "battery_level", 0.0))
            for n in nodes
            if getattr(n, "node_type", "") in {"battery", "bess", "supercap"}]
    if not socs:
        return 0.0
    return sum(socs) / len(socs) * 100.0


def system_reliability_index(nodes: Iterable[Any]) -> float:
    """Composite reliability in [0, 1] — combines voltage + freq + outage."""
    ns = list(nodes)
    v = voltage_stability_index(ns)
    f = frequency_stability_index(ns)
    not_failed = sum(1 for n in ns if not getattr(n, "failed", False))
    out = not_failed / len(ns) if ns else 1.0
    return max(0.0, min(1.0, (v + f + out) / 3.0))