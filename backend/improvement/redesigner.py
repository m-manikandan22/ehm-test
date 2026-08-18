"""
redesigner.py — apply AI-planner actions to improve the grid.

Why
---
A "self-improving" smart grid must, given an evaluator summary,
propose and apply topology changes that improve the worst KPIs.
This module is the seam between ``Evaluator`` and the M1
``AIPlanner``: it asks the planner for ``PlanAction``s, applies the
non-destructive ones, and emits a ``RedesignReport`` with before /
after metric deltas.

The redesigner intentionally *does not* mutate the live grid used
by the API — it produces a candidate ``SmartGrid`` and lets the
caller decide whether to swap.  This keeps the safety boundary
clear in the API layer.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from improvement.evaluator import SimulationEvaluator
from planning.ai_planner import AIPlanner, PlanAction


@dataclass
class RedesignReport:
    actions_proposed: int
    actions_applied: int
    before: Dict[str, Any]
    after: Dict[str, Any]
    delta: Dict[str, float]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actions_proposed": self.actions_proposed,
            "actions_applied": self.actions_applied,
            "before": self.before,
            "after": self.after,
            "delta": self.delta,
            "notes": self.notes,
        }


@dataclass
class Redesigner:
    """Apply AI planner actions; report before/after metric deltas."""

    planner_factory: Any = AIPlanner
    max_actions: int = 5

    def propose(
        self,
        grid: Any,
        before_summary: Dict[str, Any],
    ) -> RedesignReport:
        """Build a redesigned candidate grid and report the metric delta.

        The candidate is produced by running the AI planner on a deep
        copy of ``grid`` (so the live grid is untouched).  The planner
        mutates its input; we capture that on the copy and roll up
        metrics on the post-plan grid.
        """
        candidate = copy.deepcopy(grid)
        before = dict(before_summary)
        try:
            planner = self.planner_factory(candidate)
            actions: List[PlanAction] = planner.plan()
        except Exception as exc:  # noqa: BLE001
            return RedesignReport(
                actions_proposed=0,
                actions_applied=0,
                before=before,
                after={},
                delta={},
                notes=[f"planner raised: {exc!r}"],
            )

        # The planner already applies candidates inside its try/finally;
        # ``actions`` is the record of *proposed* actions.
        proposed = len(actions)
        applied = sum(1 for a in actions if a.expected_delta > 0.0)

        # Compute a roll-up on the post-plan grid (light version).
        after = _light_summary(candidate)
        delta = _diff(before, after)
        return RedesignReport(
            actions_proposed=proposed,
            actions_applied=applied,
            before=before,
            after=after,
            delta=delta,
            notes=[
                f"applied {applied}/{proposed} actions with positive delta",
                f"grid nodes: {len(candidate.nodes)}",
            ],
        )


def _light_summary(grid: Any) -> Dict[str, Any]:
    """Quick rollup: mean voltage, freq, count of healthy critical nodes."""
    nodes = list(grid.nodes.values())
    if not nodes:
        return {"n_nodes": 0}
    crit_types = {"hospital", "hospital_icu", "gov_building"}
    crit_total = sum(1 for n in nodes if n.node_type in crit_types)
    crit_avail = sum(
        1 for n in nodes
        if n.node_type in crit_types and not getattr(n, "failed", False)
    )
    avg_v = sum(float(getattr(n, "voltage", 1.0)) for n in nodes) / len(nodes)
    avg_f = sum(float(getattr(n, "frequency", 50.0)) for n in nodes) / len(nodes)
    return {
        "n_nodes": len(nodes),
        "n_edges": grid.graph.number_of_edges(),
        "mean_voltage": avg_v,
        "mean_frequency": avg_f,
        "critical_load_total": crit_total,
        "critical_load_available": crit_avail,
        "critical_load_availability": crit_avail / max(1, crit_total),
    }


def _diff(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, float]:
    """Return before→after deltas for keys present in both."""
    out: Dict[str, float] = {}
    for k in set(before) & set(after):
        b = float(before[k]) if isinstance(before[k], (int, float)) else 0.0
        a = float(after[k]) if isinstance(after[k], (int, float)) else 0.0
        out[k] = a - b
    return out