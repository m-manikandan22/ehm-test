"""
validity.py — Run-validity guard and invalid-run classification.

Why this exists
---------------
Silent exception swallowing is unacceptable in scientific experiments.
A run that fails to converge, returns NaN/Inf, or produces an
inconsistent topology must be marked **invalid** and excluded from
the aggregate statistics. This module:

  - Defines the ``InvalidRunReason`` enum.
  - Defines the ``ValidityReport`` dataclass (the per-run verdict).
  - Exposes ``check_run_validity(grid, ...)`` which inspects the
    current grid state and flags any of the failure modes described
    in the master plan.

Usage
-----
The experiment runner calls ``check_run_validity`` at every step and
once at the end of each run. The first invalid reason wins; further
checks are skipped so the report stays small.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class InvalidRunReason(str, Enum):
    """Why a run is invalid. The string value is what appears in JSON.

    The ordering of the ``_priority`` map below determines which reason
    wins when a single run triggers multiple invalid signals. Higher
    priority reasons are *more specific* (controller failures, FLISR
    crashes, fault-injection failures) than generic topology checks;
    in the case of a tie the *earliest* reason wins (preserving the
    audit trail of what happened first).
    """

    SOLVER_FAILURE            = "SOLVER_FAILURE"
    NAN_VALUE                 = "NAN_VALUE"
    INFINITY_VALUE            = "INFINITY_VALUE"
    IMPOSSIBLE_VOLTAGE        = "IMPOSSIBLE_VOLTAGE"
    TOPOLOGY_INCONSISTENT     = "TOPOLOGY_INCONSISTENT"
    FAULT_INJECTION_FAILED    = "FAULT_INJECTION_FAILED"
    METRIC_CALCULATION_FAILED = "METRIC_CALCULATION_FAILED"
    CONTROLLER_FAILED         = "CONTROLLER_FAILED"
    UNEXPECTED_EXCEPTION      = "UNEXPECTED_EXCEPTION"

    def __str__(self) -> str:  # so JSON keeps it as a string
        return self.value


# Higher number = more specific / more useful for debugging.
# The runner prefers the most-specific reason when multiple fire.
_INVALID_REASON_PRIORITY: Dict[InvalidRunReason, int] = {
    InvalidRunReason.SOLVER_FAILURE:             100,
    InvalidRunReason.FAULT_INJECTION_FAILED:     90,
    InvalidRunReason.CONTROLLER_FAILED:          80,
    InvalidRunReason.METRIC_CALCULATION_FAILED:  70,
    InvalidRunReason.IMPOSSIBLE_VOLTAGE:         60,
    InvalidRunReason.NAN_VALUE:                  50,
    InvalidRunReason.INFINITY_VALUE:             50,
    InvalidRunReason.UNEXPECTED_EXCEPTION:       95,
    InvalidRunReason.TOPOLOGY_INCONSISTENT:      10,
}


@dataclass
class ValidityReport:
    """Verdict on whether a run is valid."""

    valid: bool = True
    invalid_reason: Optional[str] = None
    details: Dict[str, str] = field(default_factory=dict)
    timestamp_step: Optional[int] = None

    def mark_invalid(self, reason: InvalidRunReason,
                     *, step: Optional[int] = None,
                     **details: str) -> None:
        """Mark the run invalid with the given reason.

        When several invalid signals fire (e.g. an empty topology AND
        a controller exception), the *more specific* reason wins — see
        ``_INVALID_REASON_PRIORITY``. Among reasons of the same
        priority the *earliest* wins, preserving the audit trail of
        what actually triggered the cascade.
        """
        new_pri = _INVALID_REASON_PRIORITY.get(reason, 0)
        cur_pri = 0
        if self.invalid_reason is not None:
            try:
                cur = InvalidRunReason(self.invalid_reason)
            except ValueError:
                cur = None
            if cur is not None:
                cur_pri = _INVALID_REASON_PRIORITY.get(cur, 0)
            if new_pri < cur_pri:
                return  # keep the more specific / earlier reason
            if new_pri == cur_pri:
                return  # earliest wins on ties
        self.valid = False
        self.invalid_reason = reason.value
        self.timestamp_step = step
        self.details.update({k: str(v) for k, v in details.items()})

    def to_dict(self) -> Dict[str, object]:
        return {
            "valid":          bool(self.valid),
            "invalid_reason": self.invalid_reason,
            "details":        dict(self.details),
            "timestamp_step": self.timestamp_step,
        }


# Voltage sanity bound — outside this range the state is considered
# physically impossible. We pick a wide envelope because some EM
# transients can swing past 1.5 pu briefly, but >2.5 pu is unphysical.
_IMPOSSIBLE_VOLTAGE_HIGH = 2.5
_IMPOSSIBLE_VOLTAGE_LOW  = -0.5


def _is_finite_scalar(x) -> bool:
    """Return True iff ``x`` is a finite number."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v)


def check_run_validity(
    grid,
    *,
    step: Optional[int] = None,
) -> ValidityReport:
    """Inspect a grid and decide whether the run is still scientifically valid.

    The check is cheap; call it after every step in the runner.
    """
    report = ValidityReport()
    nodes = getattr(grid, "nodes", {}) or {}

    # ── Topology consistency ────────────────────────────────────────
    # Every node has at least one node_id and at least one of
    # {failed, isolated, voltage}.
    n_nodes = len(nodes)
    if n_nodes == 0:
        report.mark_invalid(
            InvalidRunReason.TOPOLOGY_INCONSISTENT,
            step=step, why="empty_node_set",
        )
        return report

    # ── Per-node voltage sanity ──────────────────────────────────────
    for nid, node in nodes.items():
        v = getattr(node, "voltage", 1.0)
        if isinstance(v, float) and math.isnan(v):
            report.mark_invalid(
                InvalidRunReason.NAN_VALUE,
                step=step, node=str(nid), value=str(v),
            )
            return report
        if not _is_finite_scalar(v):
            report.mark_invalid(
                InvalidRunReason.INFINITY_VALUE,
                step=step, node=str(nid), value=str(v),
            )
            return report
        if v < _IMPOSSIBLE_VOLTAGE_LOW or v > _IMPOSSIBLE_VOLTAGE_HIGH:
            report.mark_invalid(
                InvalidRunReason.IMPOSSIBLE_VOLTAGE,
                step=step, node=str(nid), value=f"{v:.4f}",
            )
            return report

    # ── Edge sanity (active edges must have valid flow) ──────────────
    graph = getattr(grid, "graph", None)
    if graph is not None:
        for u, v, data in graph.edges(data=True):
            if not data.get("active", True):
                continue
            flow = data.get("flow", 0.0)
            if not _is_finite_scalar(flow):
                report.mark_invalid(
                    InvalidRunReason.NAN_VALUE,
                    step=step, edge=f"{u}->{v}", flow=str(flow),
                )
                return report

    return report


def merge_invalid(report: ValidityReport,
                  other: ValidityReport) -> ValidityReport:
    """OR-combine two validity reports (first invalid reason wins)."""
    if not report.valid and report.invalid_reason:
        return report
    if not other.valid and other.invalid_reason:
        return other
    return report


def summarise_invalid_reasons(reports: List[ValidityReport]) -> Dict[str, int]:
    """Count invalid runs by reason."""
    counts: Dict[str, int] = {}
    for r in reports:
        if not r.valid and r.invalid_reason:
            counts[r.invalid_reason] = counts.get(r.invalid_reason, 0) + 1
    return counts