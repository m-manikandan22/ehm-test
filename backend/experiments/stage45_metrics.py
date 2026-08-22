"""stage45_metrics.py — Physics-coupled reliability metric collector.

This module is the Stage-45 replacement for the Stage-44 metric loop
that lived inline inside ``stage44_validation.py``. The Stage-44 metric
contract was structurally correct (ENS = Σ (P_demand − P_served) × Δt)
but its per-timestep loop had two problems documented in
``docs/STAGE_45_CURRENT_METRIC_TRACE.md``:

  1. For ``industry`` / ``hospital`` / ``hospital_icu`` load nodes,
     the loop compared ``received_power`` against itself
     (``would_be = received + 0.0``), so the contribution to ENS was
     always zero — only ``house`` nodes could contribute to ENS.
  2. The metric was computed as ``Σ received`` vs ``Σ would_be`` —
     an aggregate that could not expose per-customer interruption
     minutes or first-interruption-vs-restoration times needed for
     CMI.

The Stage-45 collector fixes both problems:

  * Per-load-node accounting. For every load node we record
    ``P_demand``, ``P_served``, ``P_unserved``, ``V`` at every step
    in a per-node log.
  * The primary metrics are derived from the per-node log, not from
    a single running sum, so the formulas can be inspected
    independently for any (load_node, step).

All five primary metrics (ENS, CMI, critical-load interruption,
voltage violations, restoration rate / time) are derived from this
per-node log.

The collector also captures a per-action ``physical_effect_delta``
that records whether the controller's chosen action *measured*
changed the served-energy vector — this is the diagnostic that
catches the Stage-44 invariance finding.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from experiments.research_metrics import CRITICAL_NODE_TYPES


# Node types that count as "load" for ENS/CMI accounting.
# Stage-43 scenario / fault schedule uses house / industry /
# hospital / hospital_icu. water_plant + transmission_tower exist in
# CRITICAL_NODE_TYPES but only appear in the IEEE-13 / IEEE-33
# benchmarks, not the Stage-43 49-node grid.
_LOAD_NODE_TYPES: Tuple[str, ...] = (
    "house", "industry", "hospital", "hospital_icu",
    "service",
)


# Voltage band — the Stage-44 / Stage-45 0.10 pu band is a heuristic,
# not a regulatory standard. Documented in STAGE_45_PHYSICS_COUPLING.md.
_VOLTAGE_BAND = 0.10

# One simulation step is 1 minute of clock time (per Stage-43
# convention; documented in STAGE_43_RUNTIME_CONTROL_FLOW.md).
_STEP_HOURS = 1.0 / 60.0


@dataclass
class _PerLoadStep:
    """One row of the per-load-node service log."""
    step: int
    p_demand_mw: float
    p_served_mw: float
    p_unserved_mw: float
    voltage_pu: float
    failed: bool
    isolated: bool


@dataclass
class _PerLoadNode:
    """Service log + per-node diagnostics for one load node."""
    node_id: str
    node_type: str
    is_critical: bool
    log: List[_PerLoadStep] = field(default_factory=list)
    cumulative_unserved_mwh: float = 0.0
    cumulative_served_mwh: float = 0.0
    cumulative_demand_mwh: float = 0.0
    n_steps_unserved: int = 0
    first_unserved_step: Optional[int] = None
    restored_step: Optional[int] = None
    min_voltage_pu: float = 1.0
    max_voltage_pu: float = 1.0
    n_voltage_violations: int = 0

    def update(self, step: int, demand: float, served: float,
               voltage: float, failed: bool, isolated: bool) -> None:
        unserved = max(0.0, float(demand) - float(served))
        self.log.append(_PerLoadStep(
            step=int(step),
            p_demand_mw=float(demand),
            p_served_mw=float(served),
            p_unserved_mw=float(unserved),
            voltage_pu=float(voltage),
            failed=bool(failed),
            isolated=bool(isolated),
        ))
        self.cumulative_unserved_mwh += unserved * _STEP_HOURS
        self.cumulative_served_mwh += float(served) * _STEP_HOURS
        self.cumulative_demand_mwh += float(demand) * _STEP_HOURS
        if unserved > 0.0:
            self.n_steps_unserved += 1
            if self.first_unserved_step is None:
                self.first_unserved_step = int(step)
            self.restored_step = None  # re-interrupted, reset
        elif self.first_unserved_step is not None and self.restored_step is None:
            self.restored_step = int(step)
        if voltage < self.min_voltage_pu:
            self.min_voltage_pu = float(voltage)
        if voltage > self.max_voltage_pu:
            self.max_voltage_pu = float(voltage)
        if abs(float(voltage) - 1.0) > _VOLTAGE_BAND:
            self.n_voltage_violations += 1


class Stage45MetricCollector:
    """Per-step reliability-metric collector for a single run.

    Designed to be called from inside the same per-step loop the
    Stage-44 validation uses, but with a corrected data flow: every
    metric is derived from a per-load-node service log, never from a
    single running sum that hides per-customer state.

    The collector is *side-channel free* — it does not consume the
    fault schedule or any controller-side data; everything it
    reports comes from the *post-power-flow* grid state that
    ``grid.update_power_flow()`` produces.
    """

    def __init__(self) -> None:
        self.per_node: Dict[str, _PerLoadNode] = {}
        self._last_action_served_mwh: Dict[int, float] = {}
        # Per-step voltage-violation count (sum across buses that
        # violated). Distinct from per-load-node voltage violations
        # (which count per-load-node-step violations).
        self.voltage_violation_count: int = 0
        self._steps_total: int = 0

    # ------------------------------------------------------------------
    def register_load_nodes(self, grid) -> None:
        """Initialise the per-node book from the current grid topology.

        Called once per run, BEFORE the first ``step()``. After this,
        the collector knows every load node it will track.
        """
        for nid, n in grid.nodes.items():
            nt = str(getattr(n, "node_type", "") or "")
            if nt not in _LOAD_NODE_TYPES:
                continue
            self.per_node[nid] = _PerLoadNode(
                node_id=str(nid),
                node_type=nt,
                is_critical=(nt in CRITICAL_NODE_TYPES),
            )

    def step(self, *, grid, timestep: int) -> None:
        """Record one per-load-node state snapshot.

        ``grid`` is the SmartGrid at the end of the step (after
        ``grid.update_power_flow()``).
        """
        self._steps_total = max(self._steps_total, int(timestep) + 1)
        bus_violations = 0
        for nid, n in grid.nodes.items():
            nt = str(getattr(n, "node_type", "") or "")
            if nt not in _LOAD_NODE_TYPES:
                # Still count voltage violation on the bus — the
                # violation metric is grid-wide, not load-only.
                v = float(getattr(n, "voltage", 1.0) or 1.0)
                if abs(v - 1.0) > _VOLTAGE_BAND:
                    bus_violations += 1
                continue
            # Demand — uses would_be_load if exposed so the metric
            # reflects the *baseline* of a frozen failed node, not
            # the controller-deflated current load (Stage-43 ENS
            # semantics; see STAGE_45_METRIC_DEFINITIONS.md §1).
            try:
                if hasattr(grid, "would_be_load"):
                    demand = float(grid.would_be_load(n))
                else:
                    demand = float(getattr(n, "load", 0.0) or 0.0)
            except Exception:  # noqa: BLE001
                demand = float(getattr(n, "load", 0.0) or 0.0)
            served = float(getattr(n, "received_power", 0.0) or 0.0)
            # Clamp served so we never report "overserved" — a
            # controller can inflate served only by inflating
            # received_power beyond demand, which the BFS clamps in
            # the simulator (children share the parent's received
            # power).
            if served > demand:
                served = demand
            voltage = float(getattr(n, "voltage", 1.0) or 1.0)
            failed = bool(getattr(n, "failed", False))
            isolated = bool(getattr(n, "isolated", False))
            self.per_node[nid].update(
                step=int(timestep), demand=demand, served=served,
                voltage=voltage, failed=failed, isolated=isolated,
            )
            if abs(voltage - 1.0) > _VOLTAGE_BAND:
                bus_violations += 1
        if bus_violations > 0:
            self.voltage_violation_count += 1

    # ------------------------------------------------------------------
    def note_action_effect(self, *, action_id: int,
                            served_mwh_delta: float) -> None:
        """Record an action's physical-effect delta.

        Used by the action-sensitivity regression tests to verify
        that ``use_battery`` / ``use_supercapacitor`` / ``reroute``
        measurably change the served-energy vector. Not a primary
        metric — purely diagnostic.
        """
        self._last_action_served_mwh[int(action_id)] = float(
            served_mwh_delta
        )

    # ------------------------------------------------------------------
    def summary(self) -> Dict[str, Any]:
        """Roll up the per-node log into the Stage-45 metric summary."""
        ens = 0.0
        cmi = 0.0
        critical_interruption_steps = 0
        n_violations = self.voltage_violation_count
        n_unserved_loads = 0
        n_restored_loads = 0
        per_node_diag: Dict[str, Dict[str, Any]] = {}

        for nid, pn in self.per_node.items():
            ens += pn.cumulative_unserved_mwh
            # CMI: for each load node that experienced interruption,
            # interruption_minutes = restored_step − first_unserved_step
            # (in simulation steps = simulation minutes).
            if pn.first_unserved_step is not None:
                n_unserved_loads += 1
                if pn.restored_step is not None:
                    n_restored_loads += 1
                    interruption_min = max(
                        0,
                        int(pn.restored_step) - int(pn.first_unserved_step),
                    )
                else:
                    # Never restored — count the full observed span.
                    interruption_min = max(
                        0,
                        self._steps_total - int(pn.first_unserved_step),
                    )
                cmi += float(interruption_min)
            if pn.is_critical:
                critical_interruption_steps += pn.n_steps_unserved
            per_node_diag[nid] = {
                "node_type": pn.node_type,
                "is_critical": pn.is_critical,
                "cumulative_unserved_mwh": round(
                    pn.cumulative_unserved_mwh, 6
                ),
                "cumulative_served_mwh": round(
                    pn.cumulative_served_mwh, 6
                ),
                "cumulative_demand_mwh": round(
                    pn.cumulative_demand_mwh, 6
                ),
                "n_steps_unserved": int(pn.n_steps_unserved),
                "first_unserved_step": (
                    int(pn.first_unserved_step)
                    if pn.first_unserved_step is not None else None
                ),
                "restored_step": (
                    int(pn.restored_step)
                    if pn.restored_step is not None else None
                ),
                "min_voltage_seen": round(pn.min_voltage_pu, 4),
                "max_voltage_seen": round(pn.max_voltage_pu, 4),
                "n_voltage_violations": int(pn.n_voltage_violations),
            }
        n_unserved = max(1, n_unserved_loads)
        restoration_rate = (
            float(n_restored_loads) / float(n_unserved)
            if n_unserved_loads else 1.0
        )
        avg_restoration_steps = 0.0
        n_restored_with_time = 0
        for pn in self.per_node.values():
            if pn.first_unserved_step is not None and pn.restored_step is not None:
                avg_restoration_steps += float(
                    int(pn.restored_step) - int(pn.first_unserved_step)
                )
                n_restored_with_time += 1
        if n_restored_with_time:
            avg_restoration_steps = (
                avg_restoration_steps / float(n_restored_with_time)
            )
        return {
            "schema_version": "stage45.1.0",
            "energy_not_served_mwh": round(float(ens), 6),
            "total_customer_minutes_interrupted": round(float(cmi), 6),
            "critical_load_interruption_steps": int(
                critical_interruption_steps
            ),
            "voltage_violation_count": int(n_violations),
            "restoration_rate": float(restoration_rate),
            "avg_restoration_steps": float(avg_restoration_steps),
            "n_load_nodes": len(self.per_node),
            "n_unserved_load_nodes": int(n_unserved_loads),
            "n_restored_load_nodes": int(n_restored_loads),
            "per_load_node": per_node_diag,
            "action_effects": dict(self._last_action_served_mwh),
        }


__all__ = [
    "Stage45MetricCollector",
    "CRITICAL_NODE_TYPES",
]
