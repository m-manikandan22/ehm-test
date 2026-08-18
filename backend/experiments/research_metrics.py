"""research_metrics.py — Paper-grade metric collector for replay runs.

The ``MetricCollector`` accumulates everything the paper needs from a
single replay run: fault records, action counts, voltage-violation
counts, energy-not-served, restoration timings, and a list of
"critical" loads (hospital_icu, hospital) so the paper can report a
*critical-load-aware* SAIDI without redefining the standard.

Public API
----------
  - ``CRITICAL_NODE_TYPES``  : tuple of node types with priority 1.
  - ``MetricCollector``      : mutable accumulator.
  - ``compute_research_metrics(collector)`` : roll up to a summary dict.
  - ``FaultRecord``          : dataclass for one injected fault.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# Node types whose outage counts as "critical load interruption".
# Priority 1 means "never shed".
CRITICAL_NODE_TYPES: Tuple[str, ...] = (
    "hospital", "hospital_icu", "water_plant", "transmission_tower",
)


# Voltage envelope — below this counts as an undervoltage violation.
_VOLTAGE_FLOOR = 0.95


@dataclass
class FaultRecord:
    """Bookkeeping for one injected fault."""
    timestep: int
    target: str
    baseline_load_mw: float
    baseline_critical_mw: float = 0.0
    duration_steps: int = 1
    # Restoration outcome (filled when mark_restoration_complete is called)
    successful_restoration: bool = False
    restoration_timestep: Optional[int] = None
    restoration_steps: Optional[int] = None
    restoration_seconds: Optional[float] = None
    # Flags
    voltage_violation_during_fault: bool = False


@dataclass
class MetricCollector:
    """Accumulator for one paper-grade replay run.

    All counts are kept in plain Python integers/floats so the
    collector itself introduces no floating-point noise.
    """
    faults: List[FaultRecord] = field(default_factory=list)
    actions_taken: int = 0
    illegal_actions_attempted: int = 0
    voltage_violation_count: int = 0
    voltage_violation_steps: int = 0
    critical_load_interruption_steps: int = 0
    total_customer_minutes_interrupted: float = 0.0
    energy_not_served_mwh: float = 0.0
    n_steps: int = 0
    n_failed_assets: int = 0
    # Optional: seconds per simulation step (used by legacy root-level
    # runner.py to compute customer-minute interruption).
    simulation_step_duration_s: float = 1.0
    # Stage-42 information-flow bookkeeping
    predictive_preparation_events: int = 0
    predictive_preparation_log: List[Dict[str, Any]] = field(default_factory=list)
    ems_cycles: int = 0
    ems_log: List[str] = field(default_factory=list)
    lstm_forecast_log: List[float] = field(default_factory=list)
    # Per-action count: proves the controller took different decisions
    # under different flags.
    action_counts: Dict[int, int] = field(default_factory=dict)

    # ------------------------------------------------------------------
    def record_fault(
        self,
        *,
        timestep: int,
        target: str,
        baseline_load_mw: float,
        baseline_critical_mw: float = 0.0,
        duration_steps: int = 1,
    ) -> None:
        self.faults.append(FaultRecord(
            timestep=int(timestep),
            target=str(target),
            baseline_load_mw=float(baseline_load_mw),
            baseline_critical_mw=float(baseline_critical_mw),
            duration_steps=int(duration_steps),
        ))

    def record_step(
        self,
        *,
        grid,
        timestep: int,
        controller_action: int,
        action_legal: bool,
    ) -> None:
        """Record one step of the replay run.

        ``grid`` is the SmartGrid at the end of the step (or any
        duck-type with ``nodes`` dict whose items expose ``voltage``,
        ``node_type``, ``failed``, ``isolated``).
        """
        self.n_steps += 1
        self.actions_taken += 1
        if not action_legal:
            self.illegal_actions_attempted += 1
        # Stage-42: per-action counter
        try:
            self.action_counts[int(controller_action)] = (
                self.action_counts.get(int(controller_action), 0) + 1
            )
        except Exception:
            pass

        critical_off = False
        undervoltage = False
        load_served = 0.0
        for nid, node in grid.nodes.items():
            nt = getattr(node, "node_type", "")
            v = float(getattr(node, "voltage", 1.0) or 1.0)
            load = float(getattr(node, "load", 0.0) or 0.0)
            if nt in CRITICAL_NODE_TYPES:
                if getattr(node, "failed", False) or getattr(node, "isolated", False):
                    critical_off = True
            if v < _VOLTAGE_FLOOR:
                undervoltage = True
            if getattr(node, "failed", False) or getattr(node, "isolated", False):
                # Stage-43 (Repair 10): ENS is charged against the
                # *would-be* load — the deterministic demand profile of
                # a healthy node at this timestep — NOT against the
                # node's current load. A failed node's load is frozen
                # (and controller actions 1–3 used to deflate it), so
                # charging current load let a controller 'reduce' ENS by
                # deflating a dead node instead of restoring service
                # (Stage-42.5 random-baseline artifact). Grids exposing
                # ``would_be_load(node)`` use it; stub grids (unit
                # tests) fall back to the current load.
                would_be = load
                if hasattr(grid, "would_be_load"):
                    try:
                        would_be = float(grid.would_be_load(node))
                    except Exception:  # noqa: BLE001
                        would_be = load
                self.total_customer_minutes_interrupted += would_be
                self.energy_not_served_mwh += would_be * (1.0 / 60.0)
            else:
                load_served += load
        if undervoltage:
            self.voltage_violation_count += 1
            self.voltage_violation_steps += 1
        if critical_off:
            self.critical_load_interruption_steps += 1

    def mark_restoration_complete(
        self,
        *,
        fault_target: str,
        timestep: int,
    ) -> None:
        for rec in self.faults:
            if rec.target == fault_target and rec.restoration_timestep is None:
                steps = int(timestep) - rec.timestep
                rec.successful_restoration = True
                rec.restoration_timestep = int(timestep)
                rec.restoration_steps = int(steps)
                # Each timestep in the paper-grade harness is 1 s.
                rec.restoration_seconds = float(steps)
                return

    # ------------------------------------------------------------------
    # Stage-42 information-flow hooks (LSTM / twin / EMS / predictive).
    # These are optional extension points; if a stage-41 style harness
    # doesn't call them the metric summary still works.
    # ------------------------------------------------------------------
    def record_predictive_preparation(
        self,
        *,
        timestep: int,
        at_risk_assets: List[str],
    ) -> None:
        self.predictive_preparation_events += 1
        self.predictive_preparation_log.append({
            "timestep": int(timestep),
            "at_risk_assets": list(at_risk_assets),
        })

    def record_ems_cycle(
        self,
        *,
        cycle: int,
        ems_log: Optional[List[str]] = None,
        report: Optional[dict] = None,
    ) -> None:
        self.ems_cycles += 1
        if ems_log:
            for entry in ems_log:
                self.ems_log.append(str(entry))

    def record_lstm_forecast(self, forecast: float) -> None:
        # Keep at most 256 entries to bound memory in long runs.
        if len(self.lstm_forecast_log) >= 256:
            return
        self.lstm_forecast_log.append(float(forecast))

    # ------------------------------------------------------------------
    def summary(self) -> dict:
        n = len(self.faults)
        restored = [r for r in self.faults if r.successful_restoration]
        restoration_steps = [
            r.restoration_steps for r in restored if r.restoration_steps is not None
        ]
        avg_rest = (
            sum(restoration_steps) / len(restoration_steps)
            if restoration_steps else None
        )
        return {
            "n_faults": n,
            "n_restored": len(restored),
            "restoration_rate": (
                len(restored) / n if n else None
            ),
            "avg_restoration_steps": avg_rest,
            "actions_taken": self.actions_taken,
            "illegal_actions_attempted": self.illegal_actions_attempted,
            "voltage_violation_count": self.voltage_violation_count,
            "critical_load_interruption_steps": (
                self.critical_load_interruption_steps
            ),
            "total_customer_minutes_interrupted": (
                self.total_customer_minutes_interrupted
            ),
            "energy_not_served_mwh": self.energy_not_served_mwh,
            "n_steps": self.n_steps,
            # Stage-42 information-flow counters
            "predictive_preparation_events": self.predictive_preparation_events,
            "ems_cycles": self.ems_cycles,
            "lstm_forecast_samples": len(self.lstm_forecast_log),
            # Stage-43 (Repair 5): the forecast VALUE log (bounded at
            # 256 entries) lets verifiers confirm the forecast carries
            # information (non-constant) — the LSTM channel is real.
            "lstm_forecast_log": list(self.lstm_forecast_log),
            "action_counts": dict(self.action_counts),
        }


def compute_research_metrics(
    collector: Optional["MetricCollector"] = None,
    *,
    grid=None,
    run_started_at: float = 0.0,
) -> dict:
    """Compute paper-grade metrics.

    Two calling conventions:

      * ``compute_research_metrics(collector)``
        Returns the collector's accumulated summary (the typical
        replay-harness call).

      * ``compute_research_metrics(grid=..., collector=collector, ...)``
        Returns a snapshot of the *current* grid state, including the
        critical-load restoration percentage. Used by the
        ``test_critical_load_restoration_calculated`` test.
    """
    if collector is not None and grid is None:
        return collector.summary()

    out: dict = {}
    if collector is not None:
        out.update(collector.summary())

    if grid is not None:
        crit_total = 0.0
        crit_restored = 0.0
        for _nid, node in grid.nodes.items():
            nt = getattr(node, "node_type", "")
            if nt in CRITICAL_NODE_TYPES:
                load = float(getattr(node, "load", 0.0) or 0.0)
                crit_total += load
                if not (
                    getattr(node, "failed", False)
                    or getattr(node, "isolated", False)
                ):
                    crit_restored += load
        out["critical_load_total_mw"] = crit_total
        out["critical_load_restored_mw"] = crit_restored
        out["critical_load_restored_pct"] = (
            (crit_restored / crit_total * 100.0) if crit_total > 0 else 0.0
        )
    return out
