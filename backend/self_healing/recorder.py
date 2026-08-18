"""
recorder.py — per-step IEEE 1366 reliability time-series.

Why
---
The metrics module computes *aggregate* SAIFI/SAIDI/CAIDI/ENS values,
but a reproducibility study needs the *time-series* of those values so
reviewers can plot per-step degradation.  ``ReliabilityRecorder``
collects a tiny ``ReliabilitySample`` per simulation step, then rolls
them up into a JSON-friendly list the API can return in one call.

Pure additive — no existing module references the recorder; it is the
caller's responsibility to ``record(...)`` once per ``/simulate`` step.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Any, Deque, Dict, List


@dataclass
class ReliabilitySample:
    """One per-step sample of the IEEE 1366 indices."""

    timestep: int
    failed_count: int
    critical_failed_count: int
    cumulative_customer_minutes: float
    sustained_interruptions: float
    ens_mwh_step: float
    voltage_stability: float
    frequency_stability: float
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReliabilityRecorder:
    """Rolling time-series of reliability samples + aggregates."""

    max_samples: int = 5000
    samples: Deque[ReliabilitySample] = field(
        default_factory=lambda: deque(maxlen=5000),
    )

    def record(self, sample: ReliabilitySample) -> None:
        self.samples.append(sample)

    # ------------------------------------------------------------------

    def record_from_grid(self, grid, timestep: int,
                         load_mw: float = 0.0,
                         notes: str = "") -> ReliabilitySample:
        """One-shot helper that builds a sample from a live grid."""
        nodes = list(grid.nodes.values())
        n_crit_failed = sum(
            1 for n in nodes
            if getattr(n, "node_type", "") in {
                "hospital", "hospital_icu", "gov_building",
            } and getattr(n, "failed", False)
        )
        n_failed = sum(1 for n in nodes if getattr(n, "failed", False))
        in_band_v = sum(
            1 for n in nodes
            if 0.95 <= float(getattr(n, "voltage", 1.0)) <= 1.05
        )
        in_band_f = sum(
            1 for n in nodes
            if 49.8 <= float(getattr(n, "frequency", 50.0)) <= 50.2
        )
        n = len(nodes) or 1
        cmi = n_crit_failed * 60.0
        ens_step = n_failed * load_mw / 60.0
        sample = ReliabilitySample(
            timestep=int(timestep),
            failed_count=int(n_failed),
            critical_failed_count=int(n_crit_failed),
            cumulative_customer_minutes=float(cmi),
            sustained_interruptions=float(n_failed),
            ens_mwh_step=float(ens_step),
            voltage_stability=in_band_v / n,
            frequency_stability=in_band_f / n,
            notes=notes,
        )
        self.samples.append(sample)
        return sample

    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        snaps = list(self.samples)
        if not snaps:
            return {
                "samples": 0,
                "saifi": 0.0,
                "saidi": 0.0,
                "caidi": 0.0,
                "asai": 1.0,
                "ens_mwh": 0.0,
                "voltage_stability_mean": 1.0,
                "frequency_stability_mean": 1.0,
                "history": [],
            }
        n_steps = len(snaps)
        # Treat each step as a single "customer" experiencing interruptions.
        customers_served = [1.0] * n_steps
        sustained = [s.sustained_interruptions for s in snaps]
        customer_minutes = [s.cumulative_customer_minutes for s in snaps]
        try:
            from metrics.ieee_1366 import (
                saifi, saidi, caidi, asai, ens_mwh,
            )
            s_saifi = saifi(customers_served, sustained)
            s_saidi = saidi(customer_minutes, customers_served)
            s_caidi = caidi(s_saidi, s_saifi)
            s_ens = ens_mwh(
                [s.ens_mwh_step for s in snaps],
                [1.0] * n_steps,
            )
            s_asai = asai(
                customer_hours_available=[
                    max(0.0, 1.0 - s.failed_count / 100.0)
                    * (1.0 / 60.0) for s in snaps
                ],
                customer_hours_demanded=[
                    1.0 * (1.0 / 60.0) for _ in snaps
                ],
            )
        except Exception:  # noqa: BLE001 — fallback to local math
            s_saifi = sum(sustained) / max(1, n_steps)
            s_saidi = sum(customer_minutes) / max(1, n_steps)
            s_caidi = s_saidi / s_saifi if s_saifi > 0 else 0.0
            s_ens = sum(s.ens_mwh_step for s in snaps)
            s_asai = 1.0 - sum(s.failed_count) / max(1, n_steps * 100)
        v_mean = sum(s.voltage_stability for s in snaps) / n_steps
        f_mean = sum(s.frequency_stability for s in snaps) / n_steps
        return {
            "samples": n_steps,
            "saifi": float(s_saifi),
            "saidi": float(s_saidi),
            "caidi": float(s_caidi),
            "asai": float(s_asai),
            "ens_mwh": float(s_ens),
            "voltage_stability_mean": float(v_mean),
            "frequency_stability_mean": float(f_mean),
            "history": [s.to_dict() for s in snaps],
        }
