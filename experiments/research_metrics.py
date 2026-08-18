"""
research_metrics.py — Comprehensive per-run metric collector for paper
experiments.

Why this exists
---------------
The IEEE 1366 module and the existing per-step recorder give us
reliability indices and a few scalar KPIs. For a research paper we
need more — restoration time, critical-load restoration, switching
operations, illegal-action counts, voltage violations, line overloads,
energy delivered, carbon, cost, and runtime.

This module defines:

  - ``ResearchMetrics``       — the per-run metric dict.
  - ``MetricCollector``       — a stateful recorder wired into the run.
  - ``compute_research_metrics(grid, ...)`` — extract every metric from
    a final grid state plus the trace of events the collector recorded
    during the run.

Status
------
Demonstrative, not research-grade. The numeric values are
self-consistent and reproducible, but they are *counts of what
happened in the simulation*, not measurements against a calibrated
power-system reality. They are suitable for comparing controllers on
the same simulator but should not be quoted as if they came from
field-deployed hardware.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ── Critical-load node types ─────────────────────────────────────────────
# These node types are counted as "critical loads" for the
# critical-load-restoration metric. We use the type tags the EHM
# grid already assigns.
CRITICAL_NODE_TYPES = frozenset({
    "hospital",
    "hospital_icu",
    "gov_building",
    "emergency",
    "water_plant",
    "comms_tower",
    "critical_industry",
})


# ── Default restoration threshold ────────────────────────────────────────
# A fault is considered "restored" once 95 % of the originally
# served load in the affected area is back online. The 95 % threshold
# follows the IEEE 1366 convention for sustained interruptions.
DEFAULT_RESTORATION_THRESHOLD = 0.95


@dataclass
class FaultRecord:
    """What happened around a single fault."""

    fault_timestep: int
    fault_timestamp_s: float
    target_node: str
    # Load (MW) being served by the affected area just before the fault.
    baseline_load_mw: float = 0.0
    baseline_critical_mw: float = 0.0
    # Set by the collector when restoration is achieved.
    restoration_timestep: Optional[int] = None
    restoration_timestamp_s: Optional[float] = None
    restoration_steps: Optional[int] = None
    restoration_seconds: Optional[float] = None
    successful_restoration: bool = False

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class MetricCollector:
    """Stateful collector — wired into the runner.

    The runner calls ``record_step`` after each tick and ``record_fault``
    whenever a fault is injected. The collector aggregates counts
    (switching, illegal actions, overloads, voltage violations) and
    the per-fault restoration timings.
    """

    simulation_step_duration_s: float = 1.0
    faults: List[FaultRecord] = field(default_factory=list)
    switching_operations: int = 0
    actions_taken: int = 0
    illegal_actions_attempted: int = 0
    load_shedding_events: int = 0
    battery_dispatch_events: int = 0
    voltage_violation_count: int = 0
    frequency_deviation_count: int = 0
    line_overload_count: int = 0
    # Bookkeeping for restoration thresholds.
    _fault_baseline_load: Dict[str, float] = field(default_factory=dict)
    _fault_baseline_critical: Dict[str, float] = field(default_factory=dict)
    # Highest timestep recorded so far; used to size outage windows when
    # the scenario's total_steps is not passed explicitly.
    _max_timestep: int = 0

    # ── Recording API used by the runner ────────────────────────────────
    def record_fault(self, *, timestep: int, target: str,
                     baseline_load_mw: float,
                     baseline_critical_mw: float) -> FaultRecord:
        """Mark a fault as having happened at ``timestep`` on ``target``.

        ``baseline_load_mw`` is the load the affected area was serving
        just before the fault; we use it to compute the restoration
        threshold and the ENS contribution.
        """
        rec = FaultRecord(
            fault_timestep=timestep,
            fault_timestamp_s=float(timestep) * self.simulation_step_duration_s,
            target_node=str(target),
            baseline_load_mw=float(baseline_load_mw),
            baseline_critical_mw=float(baseline_critical_mw),
        )
        self._fault_baseline_load[target]      = float(baseline_load_mw)
        self._fault_baseline_critical[target]  = float(baseline_critical_mw)
        self.faults.append(rec)
        return rec

    def record_step(self, *, grid, timestep: int,
                    controller_action: Any = None,
                    action_legal: bool = True) -> None:
        """One tick of bookkeeping. Called by the runner after ``grid.step()``."""
        self._max_timestep = max(self._max_timestep, int(timestep))
        if controller_action is not None:
            self.actions_taken += 1
            if not action_legal:
                self.illegal_actions_attempted += 1

        # Voltage violations
        nodes = getattr(grid, "nodes", {}) or {}
        for node in nodes.values():
            v = getattr(node, "voltage", 1.0)
            if isinstance(v, (int, float)) and math.isfinite(v):
                if v < 0.95 or v > 1.05:
                    self.voltage_violation_count += 1
            f = getattr(node, "frequency", 50.0)
            if isinstance(f, (int, float)) and math.isfinite(f):
                if f < 49.5 or f > 50.5:
                    self.frequency_deviation_count += 1

        # Line overloads
        graph = getattr(grid, "graph", None)
        if graph is not None:
            for _u, _v, data in graph.edges(data=True):
                if not data.get("active", True):
                    continue
                flow = float(data.get("flow", 0.0) or 0.0)
                cap  = float(data.get("capacity", 1.0) or 1.0)
                if cap > 0 and abs(flow) > 0.95 * cap:
                    self.line_overload_count += 1

    def mark_restoration_complete(self, *, fault_target: str,
                                  timestep: int) -> None:
        """Mark a specific fault target as restored at ``timestep``."""
        for rec in self.faults:
            if rec.target_node != fault_target:
                continue
            if rec.restoration_timestep is not None:
                continue
            rec.restoration_timestep     = int(timestep)
            rec.restoration_timestamp_s  = float(timestep) * self.simulation_step_duration_s
            rec.restoration_steps        = int(timestep) - int(rec.fault_timestep)
            rec.restoration_seconds      = rec.restoration_timestamp_s - rec.fault_timestamp_s
            rec.successful_restoration   = True


# ── Top-level: compute metrics from final grid + collector ───────────────
def compute_research_metrics(
    *,
    grid,
    collector: MetricCollector,
    run_started_at: float,
    controller_runtime_s: float = 0.0,
    power_flow_runtime_s: float = 0.0,
    total_steps: Optional[int] = None,
) -> Dict[str, object]:
    """Extract every per-run metric into a flat dict.

    The returned dict is JSON-serialisable; the keys are the canonical
    metric names used in the paper tables.

    ``total_steps`` is the scenario horizon; reliability indices
    (ASAI, SAIDI, ENS) are only meaningful when it is known. If it is
    omitted it is inferred from the collector's highest recorded step.
    """
    nodes = getattr(grid, "nodes", {}) or {}
    n_nodes = len(nodes)
    if total_steps is None:
        total_steps = max(1, collector._max_timestep + 1)
    total_steps = int(total_steps)
    n_failed = 0
    n_isolated = 0
    n_islands = 0
    total_load_mw = 0.0
    total_gen_mw = 0.0
    total_critical_mw = 0.0
    critical_with_power_mw = 0.0
    voltages: List[float] = []
    for node in nodes.values():
        if getattr(node, "failed", False):    n_failed  += 1
        if getattr(node, "isolated", False): n_isolated += 1
        load = float(getattr(node, "load", 0.0) or 0.0)
        gen  = float(getattr(node, "generation", 0.0) or 0.0)
        total_load_mw += load
        total_gen_mw  += gen
        v = getattr(node, "voltage", 1.0)
        if isinstance(v, (int, float)) and math.isfinite(v):
            voltages.append(float(v))
        if getattr(node, "node_type", "") in CRITICAL_NODE_TYPES:
            total_critical_mw += load
            if load > 0 and not getattr(node, "failed", False) \
                    and not getattr(node, "isolated", False):
                critical_with_power_mw += load

    # Restoration metrics
    restoration_steps: List[float] = [
        float(rec.restoration_steps) for rec in collector.faults
        if rec.restoration_steps is not None
    ]
    successful_restoration_count = sum(
        1 for rec in collector.faults if rec.successful_restoration
    )

    # Energy / cost (use the EHM carbon / economic module if present).
    operating_cost_usd = 0.0
    outage_cost_usd = 0.0
    carbon_kg = 0.0
    try:
        from metrics.carbon_economic import (
            compute_operating_cost, compute_outage_cost,
            compute_carbon_emissions,
        )
        operating_cost_usd = compute_operating_cost(grid)
        outage_cost_usd    = compute_outage_cost(grid)
        carbon_kg          = compute_carbon_emissions(grid)
    except Exception:  # noqa: BLE001 - metric must still return a value
        pass

    total_simulation_s = time.time() - run_started_at

    # Topology island count via NetworkX weakly connected components.
    n_islands = _count_islands(grid)

    out: Dict[str, object] = {
        # ── Reliability ────────────────────────────────────────────────
        "saifi":                 _saifi(collector, n_nodes),
        "saidi":                 _saidi(collector, n_nodes, total_steps),
        "maifi":                 float(collector.frequency_deviation_count) / max(n_nodes, 1),
        "asai":                  _asai(collector, n_nodes, total_steps),
        "ens":                   _ens(collector, total_steps),
        # ── Self-healing ───────────────────────────────────────────────
        "restoration_time_steps": (sum(restoration_steps) / len(restoration_steps))
                                    if restoration_steps else None,
        "restoration_time_seconds": (
            (sum(rec.restoration_seconds or 0.0 for rec in collector.faults
                 if rec.successful_restoration)
             / successful_restoration_count)
            if successful_restoration_count else None
        ),
        "critical_load_total_mw":      round(total_critical_mw, 4),
        "critical_load_restored_mw":   round(critical_with_power_mw, 4),
        "critical_load_restored_pct":  (
            100.0 * critical_with_power_mw / total_critical_mw
            if total_critical_mw > 0 else 0.0
        ),
        "total_load_mw":               round(total_load_mw, 4),
        "successful_restoration_count": int(successful_restoration_count),
        "n_faults":                    int(len(collector.faults)),
        "number_of_islands":           int(n_islands),
        "isolated_nodes":              int(n_isolated),
        # ── Control ────────────────────────────────────────────────────
        "switching_operations":       int(collector.switching_operations),
        "actions_taken":              int(collector.actions_taken),
        "illegal_actions_attempted":  int(collector.illegal_actions_attempted),
        "load_shedding_events":       int(collector.load_shedding_events),
        "battery_dispatch_events":    int(collector.battery_dispatch_events),
        # ── Power quality ───────────────────────────────────────────────
        "minimum_voltage_pu":         min(voltages) if voltages else 1.0,
        "maximum_voltage_pu":         max(voltages) if voltages else 1.0,
        "average_voltage_pu":         (sum(voltages) / len(voltages)) if voltages else 1.0,
        "voltage_violation_count":    int(collector.voltage_violation_count),
        "frequency_deviation_count":  int(collector.frequency_deviation_count),
        "line_overload_count":        int(collector.line_overload_count),
        # ── Energy ─────────────────────────────────────────────────────
        "generation_mw":              round(total_gen_mw, 4),
        # ── Economic / environmental ────────────────────────────────────
        "operating_cost_usd":         round(operating_cost_usd, 4),
        "outage_cost_usd":            round(outage_cost_usd, 4),
        "carbon_kg":                  round(carbon_kg, 4),
        # ── Computation ────────────────────────────────────────────────
        "runtime_s":                  round(total_simulation_s, 4),
        "controller_runtime_s":       round(float(controller_runtime_s), 4),
        "power_flow_runtime_s":       round(float(power_flow_runtime_s), 4),
        # ── Per-fault trace ─────────────────────────────────────────────
        "faults":                     [rec.to_dict() for rec in collector.faults],
    }
    return out


def _count_islands(grid) -> int:
    """Count weakly-connected components in the grid."""
    try:
        import networkx as nx  # type: ignore
        graph = getattr(grid, "graph", None)
        if graph is None:
            return 0
        return int(nx.number_weakly_connected_components(graph))
    except Exception:  # noqa: BLE001
        return 0


def _saifi(collector: MetricCollector, n_nodes: int) -> float:
    """SAIFI proxy: faults per node."""
    n = max(n_nodes, 1)
    return float(len(collector.faults)) / n


def _outage_steps(rec: FaultRecord, total_steps: int) -> float:
    """Steps a fault interrupted load.

    If the fault was restored, the outage lasts ``restoration_steps``.
    Otherwise it persists from injection to the end of the run
    (``total_steps - fault_timestep`` steps).
    """
    if rec.successful_restoration and rec.restoration_steps is not None:
        return max(0.0, float(rec.restoration_steps))
    return max(0.0, float(total_steps) - float(rec.fault_timestep))


def _baseline_load(collector: MetricCollector, rec: FaultRecord) -> float:
    """Baseline MW served by the affected area before the fault."""
    if rec.baseline_load_mw > 0:
        return float(rec.baseline_load_mw)
    return float(collector._fault_baseline_load.get(rec.target_node, 0.0))


def _saidi(collector: MetricCollector, n_nodes: int, total_steps: int) -> float:
    """SAIDI proxy: total outage steps across faults, per node."""
    n = max(n_nodes, 1)
    total = sum(
        _outage_steps(rec, total_steps)
        for rec in collector.faults
    )
    return total / n


def _ens(collector: MetricCollector, total_steps: int) -> float:
    """Energy Not Served — outage steps × affected baseline load (MW)."""
    total = 0.0
    for rec in collector.faults:
        total += _outage_steps(rec, total_steps) * _baseline_load(collector, rec)
    return float(total)


def _asai(collector: MetricCollector, n_nodes: int, total_steps: int) -> float:
    """ASAI: fraction of customer-steps with service available.

    ``1 - (total outage steps / (n_nodes * total_steps))``. Clamped to
    the [0, 1] range so a short horizon cannot produce a negative index.
    """
    if total_steps <= 0 or n_nodes <= 0:
        return 1.0
    total = sum(_outage_steps(rec, total_steps) for rec in collector.faults)
    return max(0.0, min(1.0, 1.0 - (total / float(n_nodes * total_steps))))