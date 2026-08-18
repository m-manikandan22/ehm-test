"""validity.py — Validity reporting for paper-grade replay runs.

Every replay run produces a ``ValidityReport`` that records whether
the run is *publishable*. A run is invalid if:

  * the grid topology is empty / inconsistent (no nodes, no edges)
  * any node has NaN / infinity voltage
  * any node has voltage outside the physical envelope ( ``[-0.5, 2.5] pu`` )
  * the controller raised an exception
  * the power-flow solver did not converge

When multiple invalid signals fire, the **more specific** reason wins
(see ``_INVALID_REASON_PRIORITY`` below). This avoids the failure
mode where one specific bug is buried under a generic "topology
inconsistent" tag.

Public API
----------
  - ``InvalidRunReason``     : enum of invalid-run reasons
  - ``ValidityReport``       : dataclass returned by ``check_run_validity``
  - ``check_run_validity(grid)`` : one-shot validator
  - ``_INVALID_REASON_PRIORITY`` : ordered mapping (higher = wins)
"""
from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field
from typing import Optional


# ----------------------------------------------------------------------
# Invalid-run reasons
# ----------------------------------------------------------------------

class InvalidRunReason(str, enum.Enum):
    """Enumeration of invalid-run reasons.

    The string value is what shows up in ``ValidityReport.invalid_reason``
    so logs / JSON dumps are human-readable.
    """
    TOPOLOGY_INCONSISTENT   = "TOPOLOGY_INCONSISTENT"
    NAN_VALUE               = "NAN_VALUE"
    INFINITY_VALUE          = "INFINITY_VALUE"
    IMPOSSIBLE_VOLTAGE      = "IMPOSSIBLE_VOLTAGE"
    SOLVER_FAILURE          = "SOLVER_FAILURE"
    CONTROLLER_FAILED       = "CONTROLLER_FAILED"
    UNEXPECTED_EXCEPTION    = "UNEXPECTED_EXCEPTION"
    METRIC_CALCULATION_FAILED = "METRIC_CALCULATION_FAILED"


# Numeric priority: higher wins. The order is important.
#   * CONTROLLER_FAILED and UNEXPECTED_EXCEPTION are the most
#     informative — they tell you *what* crashed.
#   * SOLVER_FAILURE is the next best — it tells you the grid
#     state was unsolvable.
#   * IMPOSSIBLE_VOLTAGE / NAN / INFINITY are mid-level — they
#     point at a specific node but not the cause.
#   * TOPOLOGY_INCONSISTENT is the generic catch-all and has the
#     lowest priority.
_INVALID_REASON_PRIORITY = {
    InvalidRunReason.TOPOLOGY_INCONSISTENT: 10,
    InvalidRunReason.NAN_VALUE:             20,
    InvalidRunReason.INFINITY_VALUE:        20,
    InvalidRunReason.IMPOSSIBLE_VOLTAGE:    30,
    InvalidRunReason.SOLVER_FAILURE:        40,
    InvalidRunReason.CONTROLLER_FAILED:     50,
    InvalidRunReason.UNEXPECTED_EXCEPTION:  60,
    InvalidRunReason.METRIC_CALCULATION_FAILED: 55,
}


# Voltage envelope — outside which a node is physically impossible.
_VOLTAGE_FLOOR = -0.5
_VOLTAGE_CEILING = 2.5


# ----------------------------------------------------------------------
# Validity report
# ----------------------------------------------------------------------

@dataclass
class ValidityReport:
    """Outcome of ``check_run_validity``.

    Attributes
    ----------
    valid : bool
        True iff all checks passed.
    invalid_reason : str or None
        The winning ``InvalidRunReason.value`` (string) or ``None``.
    timestamp_step : int or None
        Step at which the invalid signal first fired (0 if unknown).
    notes : dict
        Free-form notes (e.g. ``{"controller_exception": "..."}``).
    """
    valid: bool = True
    invalid_reason: Optional[str] = None
    timestamp_step: Optional[int] = None
    notes: dict = field(default_factory=dict)
    # `details` is the JSON-friendly view of the report. Mirrors
    # `invalid_reason` + `notes` for backward compatibility with
    # test contracts that read `report["details"]["controller"]`.
    details: dict = field(default_factory=dict)

    def mark_invalid(
        self,
        reason: InvalidRunReason,
        *,
        step: int = 0,
        notes: Optional[dict] = None,
        exc: Optional[str] = None,
    ) -> None:
        """Stamp this report as invalid for ``reason``.

        Tie-break rule: if the existing reason has the *same* priority,
        the **earlier** step wins (so the report records the first
        invalid signal). If the new reason has *higher* priority, it
        overrides the existing one.

        ``exc`` is an optional convenience parameter used by the
        legacy root-level runner.py to attach a string repr of the
        exception that caused the failure. It is folded into
        ``notes["exception"]``.
        """
        if exc is not None:
            notes = dict(notes or {})
            notes.setdefault("exception", exc)
        if not self.invalid_reason:
            self.valid = False
            self.invalid_reason = reason.value
            self.timestamp_step = int(step)
            if notes:
                self.notes.update(notes)
            return

        # Compare priorities
        existing_pri = _INVALID_REASON_PRIORITY[
            InvalidRunReason(self.invalid_reason)
        ]
        new_pri = _INVALID_REASON_PRIORITY[reason]
        if new_pri > existing_pri:
            self.invalid_reason = reason.value
            self.timestamp_step = int(step)
            if notes:
                self.notes.update(notes)
        elif new_pri == existing_pri and step < (self.timestamp_step or 0):
            # Same priority, earlier step wins
            self.timestamp_step = int(step)
            if notes:
                self.notes.update(notes)

    def to_dict(self) -> dict:
        return {
            "valid": bool(self.valid),
            "invalid_reason": self.invalid_reason,
            "timestamp_step": self.timestamp_step,
            "notes": dict(self.notes),
            "details": dict(self.details) or dict(self.notes),
        }


# ----------------------------------------------------------------------
# One-shot validator
# ----------------------------------------------------------------------

def check_run_validity(grid) -> ValidityReport:
    """Inspect a grid and return a ValidityReport.

    The validator looks at:

      * **Topology** — empty topology (no nodes, or both nodes and
        graph missing) → TOPOLOGY_INCONSISTENT.
      * **Voltage envelope** — NaN / infinity / out-of-range → the
        corresponding reason.
    """
    rep = ValidityReport()

    # ---- (1) Topology check (catch-all) ----
    nodes = getattr(grid, "nodes", None)
    graph = getattr(grid, "graph", None)
    if not nodes:
        rep.mark_invalid(
            InvalidRunReason.TOPOLOGY_INCONSISTENT, step=0,
            notes={"hint": "no nodes or graph on grid"},
        )
        return rep

    # ---- (2) Voltage checks ----
    for _nid, node in nodes.items():
        v = getattr(node, "voltage", None)
        if v is None:
            continue
        try:
            v_float = float(v)
        except (TypeError, ValueError):
            rep.mark_invalid(
                InvalidRunReason.NAN_VALUE,
                notes={"node_id": getattr(node, "node_id", "?")},
            )
            continue
        if math.isnan(v_float):
            rep.mark_invalid(
                InvalidRunReason.NAN_VALUE,
                notes={"node_id": getattr(node, "node_id", "?")},
            )
        elif math.isinf(v_float):
            rep.mark_invalid(
                InvalidRunReason.INFINITY_VALUE,
                notes={"node_id": getattr(node, "node_id", "?")},
            )
        elif v_float < _VOLTAGE_FLOOR or v_float > _VOLTAGE_CEILING:
            rep.mark_invalid(
                InvalidRunReason.IMPOSSIBLE_VOLTAGE,
                notes={"node_id": getattr(node, "node_id", "?"),
                       "voltage": v_float},
            )

    return rep
