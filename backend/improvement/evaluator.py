"""
evaluator.py — collect per-run metrics for self-improvement.

Why
---
A self-improvement loop must be measurable.  ``SimulationEvaluator``
records a snapshot of every step's grid state into a buffer and
computes a rollup at the end of the run:

  - restoration_time (mean seconds-to-restore per failure)
  - power_loss_mwh
  - reliability_index (mean)
  - voltage_stability_pct
  - critical_load_availability
  - battery_usage / renewable_usage fractions
  - switching_cost
  - forecast_mae / rmse
  - attack_detection_metrics (false-positive rate)

The evaluator never mutates the grid.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

from metrics.ieee_1366 import saifi, saidi, caidi, maifi, asai, ens_mwh
from metrics.grid_kpis import (
    voltage_stability_index,
    frequency_stability_index,
    renewable_penetration_pct,
    battery_utilisation_pct,
    system_reliability_index,
)
from metrics.forecast_metrics import mae, rmse


@dataclass
class StepSnapshot:
    timestep: int
    failed_count: int
    restored_count: int
    total_gen: float
    total_load: float
    avg_voltage: float
    avg_frequency: float
    critical_load_available: int
    critical_load_total: int
    battery_discharged_mwh: float
    renewable_used_mw: float
    switches_toggled: int
    load_history: List[float] = field(default_factory=list)
    gen_history: List[float] = field(default_factory=list)


@dataclass
class SimulationEvaluator:
    """Collect per-step snapshots and compute summary metrics."""

    max_steps: int = 10000
    snapshots: Deque[StepSnapshot] = field(default_factory=lambda: deque(maxlen=10000))
    failures: Deque[int] = field(default_factory=lambda: deque(maxlen=10000))
    restorations: Deque[int] = field(default_factory=lambda: deque(maxlen=10000))
    forecast_actual: List[float] = field(default_factory=list)
    forecast_pred: List[float] = field(default_factory=list)
    attack_detections: List[bool] = field(default_factory=list)
    attack_ground_truth: List[bool] = field(default_factory=list)

    def record_step(self, snap: StepSnapshot) -> None:
        self.snapshots.append(snap)
        self.failures.append(snap.failed_count)
        self.restorations.append(snap.restored_count)

    def record_forecast(self, actual: float, predicted: float) -> None:
        self.forecast_actual.append(float(actual))
        self.forecast_pred.append(float(predicted))

    def record_attack(self, detected: bool, ground_truth: bool) -> None:
        self.attack_detections.append(bool(detected))
        self.attack_ground_truth.append(bool(ground_truth))

    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        snaps = list(self.snapshots)
        n_steps = len(snaps)
        # Forecast / attack metrics are computed regardless of snapshot count.
        f_mae = mae(self.forecast_actual, self.forecast_pred)
        f_rmse = rmse(self.forecast_actual, self.forecast_pred)
        tp = sum(1 for d, g in zip(self.attack_detections,
                                    self.attack_ground_truth)
                 if d and g)
        fp = sum(1 for d, g in zip(self.attack_detections,
                                    self.attack_ground_truth)
                 if d and not g)
        fn = sum(1 for d, g in zip(self.attack_detections,
                                    self.attack_ground_truth)
                 if not d and g)
        tn = sum(1 for d, g in zip(self.attack_detections,
                                    self.attack_ground_truth)
                 if not d and not g)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        if n_steps == 0:
            # No snapshots yet — still emit zero-forecast / zero-attack
            # keys so callers (and tests) see a stable schema.
            return {
                "steps": 0,
                "mean_voltage": 0.0,
                "mean_frequency": 0.0,
                "critical_load_availability": 0.0,
                "total_gen": 0.0,
                "total_load": 0.0,
                "battery_discharged_mwh": 0.0,
                "renewable_used_mw": 0.0,
                "switching_cost": 0,
                "n_failures": 0,
                "n_restorations": 0,
                "forecast_mae": f_mae,
                "forecast_rmse": f_rmse,
                "attack_precision": precision,
                "attack_recall": recall,
                "attack_tp": tp,
                "attack_fp": fp,
                "attack_fn": fn,
                "attack_tn": tn,
                "ieee_saifi": 0.0,
                "ieee_saidi": 0.0,
                "ieee_caidi": 0.0,
                "ieee_maifi": 0.0,
                "ieee_asai": 1.0,
                "ieee_ens_mwh": 0.0,
            }
        # Reliability across the run.
        n_steps = len(snaps)
        avg_v = sum(s.avg_voltage for s in snaps) / n_steps
        avg_f = sum(s.avg_frequency for s in snaps) / n_steps
        crit_avail = sum(
            s.critical_load_available / max(1, s.critical_load_total)
            for s in snaps
        ) / n_steps
        total_gen = sum(s.total_gen for s in snaps)
        total_load = sum(s.total_load for s in snaps)
        battery_discharged = sum(s.battery_discharged_mwh for s in snaps)
        ren_used = sum(s.renewable_used_mw for s in snaps)
        switches = sum(s.switches_toggled for s in snaps)
        # Failure / restoration.
        n_fails = sum(1 for s in snaps if s.failed_count > 0)
        n_rest = sum(s.restored_count for s in snaps)
        # Forecast / attack metrics were computed above (regardless of snapshot count).
        # IEEE 1366 — interpret each step as one "interruption event" of
        # duration 1 minute for the failed nodes.  This is a coarse
        # proxy so the indices are still meaningful over a short run.
        # For larger runs, callers should pass real per-customer arrays.
        step_minutes = [1.0 if s.failed_count > 0 else 0.0 for s in snaps]
        step_sustained = [float(s.failed_count) for s in snaps]
        step_momentary = [0.0 for _ in snaps]
        crit_total = max(1, snaps[0].critical_load_total)
        customers_served = [crit_total] * n_steps
        customer_minutes = [
            s.failed_count * 60.0 / max(1, s.critical_load_total)
            for s in snaps
        ]
        customer_hours_avail = [
            (s.critical_load_total - s.failed_count)
            * (1.0 / 60.0)
            for s in snaps
        ]
        customer_hours_demanded = [
            s.critical_load_total * (1.0 / 60.0)
            for s in snaps
        ]
        ens = ens_mwh(
            [s.total_load for s in snaps],
            step_minutes,
        )
        return {
            "steps": n_steps,
            "mean_voltage": avg_v,
            "mean_frequency": avg_f,
            "critical_load_availability": crit_avail,
            "total_gen": total_gen,
            "total_load": total_load,
            "battery_discharged_mwh": battery_discharged,
            "renewable_used_mw": ren_used,
            "switching_cost": switches,
            "n_failures": n_fails,
            "n_restorations": n_rest,
            "forecast_mae": f_mae,
            "forecast_rmse": f_rmse,
            "attack_precision": precision,
            "attack_recall": recall,
            "attack_tp": tp,
            "attack_fp": fp,
            "attack_fn": fn,
            "attack_tn": tn,
            # IEEE 1366 (per-step proxy):
            "ieee_saifi": saifi(customers_served, step_sustained),
            "ieee_saidi": saidi(customer_minutes, customers_served),
            "ieee_caidi": caidi(
                saidi(customer_minutes, customers_served),
                saifi(customers_served, step_sustained),
            ),
            "ieee_maifi": maifi(step_momentary, customers_served),
            "ieee_asai": asai(customer_hours_avail, customer_hours_demanded),
            "ieee_ens_mwh": ens,
        }

    # ------------------------------------------------------------------

    @classmethod
    def snapshot_from_grid(cls, grid: Any, timestep: int) -> StepSnapshot:
        """Convenience: build a snapshot from a live grid."""
        nodes = list(grid.nodes.values())
        crit_types = {"hospital", "hospital_icu", "gov_building"}
        crit_total = sum(1 for n in nodes if n.node_type in crit_types)
        crit_avail = sum(
            1 for n in nodes
            if n.node_type in crit_types
            and not getattr(n, "failed", False)
            and float(getattr(n, "received_power", 0.0)) > 0.0
        )
        total_gen = sum(float(getattr(n, "generation", 0.0)) for n in nodes)
        total_load = sum(float(getattr(n, "load", 0.0)) for n in nodes)
        avg_v = sum(float(getattr(n, "voltage", 1.0)) for n in nodes) / max(1, len(nodes))
        avg_f = sum(float(getattr(n, "frequency", 50.0)) for n in nodes) / max(1, len(nodes))
        return StepSnapshot(
            timestep=timestep,
            failed_count=sum(1 for n in nodes if getattr(n, "failed", False)),
            restored_count=0,  # caller can patch
            total_gen=total_gen,
            total_load=total_load,
            avg_voltage=avg_v,
            avg_frequency=avg_f,
            critical_load_available=crit_avail,
            critical_load_total=crit_total,
            battery_discharged_mwh=0.0,
            renewable_used_mw=sum(
                float(getattr(n, "generation", 0.0)) for n in nodes
                if n.node_type in {"solar_farm", "wind_farm",
                                   "generator_solar", "generator_wind"}
            ),
            switches_toggled=0,
        )