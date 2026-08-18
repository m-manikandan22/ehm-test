"""
predictor.py — predictive self-healing subsystem.

Why this module exists
----------------------
The legacy FLISR pipeline is *reactive*: a fault happens, we reroute
around it.  An IEEE-grade digital twin should predict failures *before*
they occur and reconfigure the grid proactively — turning self-healing
into "anticipatory" self-healing.  This module is the seam between the
``TwinRegistry`` (failure probabilities) and the grid's reconfiguration
primitives (``add_tie_switch``, ``inject_failure`` etc.) and emits a
declarative list of ``PredictiveAction`` records the caller can apply.

Algorithm
---------
For every node whose digital twin has ``failure_probability`` > a given
threshold (default 0.40), we:

  1. Compute the *worst-case isolated load* if the node fails — using a
     short single-source BFS over the undirected graph (O(V + E)).
  2. For every candidate reconfiguration action (add tie switch,
     redirect via a microgrid root, shift load to a parallel feeder),
     call the candidate's evaluator to estimate the expected reduction
     in isolated load.
  3. Rank actions by expected reduction / cost and return the top N.

The module is *pure* — it never mutates ``grid``; the caller decides
whether to apply the actions.  This makes it easy to benchmark against
the reactive baseline.

Backward compatibility
-----------------------
All new endpoints register under a new ``/self_healing`` prefix
(see ``api/predictive_routes.py``); the legacy ``/event`` and
``/islanding_analysis`` endpoints are untouched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

import networkx as nx


@dataclass(frozen=True)
class RiskAssessment:
    """Per-node risk roll-up used by the predictive healer."""

    node_id: str
    failure_probability: float
    isolated_load_mw: float
    severity: float        # 0..1, combination of load + criticality
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "failure_probability": float(self.failure_probability),
            "isolated_load_mw": float(self.isolated_load_mw),
            "severity": float(self.severity),
            "rationale": self.rationale,
        }


@dataclass
class PredictiveAction:
    """A declarative reconfiguration the predictive healer recommends.

    The caller is expected to dispatch the action through the existing
    grid primitives (``grid.add_user_edge`` / ``cut_user_edge`` /
    ``inject_failure``).  This module does not mutate the grid.
    """

    kind: str
    params: Dict[str, Any]
    expected_risk_reduction: float
    rationale: str
    # Optional: the asset the action protects.
    target_node_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "params": dict(self.params),
            "expected_risk_reduction": float(self.expected_risk_reduction),
            "rationale": self.rationale,
            "target_node_id": self.target_node_id,
        }


# Critical node types whose outage we want to avoid at (almost) any cost.
_CRITICAL_TYPES = {
    "hospital", "hospital_icu", "gov_building",
    "microgrid_root", "primary_substation", "solar_farm", "wind_farm",
}


@dataclass
class PredictiveSelfHealer:
    """Recommend proactive reconfiguration before faults occur."""

    risk_threshold: float = 0.40
    cost_per_tie_switch: float = 0.05     # switching cost penalty
    cost_per_load_shift: float = 0.02
    max_actions: int = 5

    # ------------------------------------------------------------------

    def assess(
        self,
        grid: Any,
        twin_registry: Any,
    ) -> List[RiskAssessment]:
        """Return one RiskAssessment per node above ``risk_threshold``.

        Parameters
        ----------
        grid : SmartGrid
        twin_registry : TwinRegistry
            Used to read per-asset ``failure_probability``.  Any object
            exposing ``.get(asset_id) -> DigitalTwin`` works.
        """
        assessments: List[RiskAssessment] = []
        for nid, node in grid.nodes.items():
            twin = twin_registry.get(nid) if twin_registry is not None else None
            if twin is None:
                continue
            p = float(getattr(twin, "failure_probability", 0.0))
            if p < self.risk_threshold:
                continue
            iso_load = self._isolated_load_if_fail(grid, nid)
            severity = self._severity(node, p)
            rationale = (
                f"twin health={getattr(twin, 'health', 1.0):.2f} p_fail={p:.2f}"
                f" iso_load={iso_load:.2f}MW"
            )
            assessments.append(RiskAssessment(
                node_id=nid,
                failure_probability=p,
                isolated_load_mw=iso_load,
                severity=severity,
                rationale=rationale,
            ))
        assessments.sort(key=lambda r: r.severity, reverse=True)
        return assessments

    # ------------------------------------------------------------------

    def recommend(
        self,
        grid: Any,
        assessments: List[RiskAssessment],
    ) -> List[PredictiveAction]:
        """Convert the highest-severity assessments into actions.

        Only assessments whose ``isolated_load_mw`` is non-trivial
        (>0.05 MW) get an action — sub-load noise is not worth a
        switching operation.
        """
        actions: List[PredictiveAction] = []
        for a in assessments:
            if a.isolated_load_mw < 0.05:
                continue
            # Strategy 1 — open a tie switch if a parallel feeder exists.
            tie = self._candidate_tie(grid, a.node_id)
            if tie is not None:
                actions.append(PredictiveAction(
                    kind="add_tie_switch",
                    params={"u": tie[0], "v": tie[1]},
                    expected_risk_reduction=min(
                        a.isolated_load_mw, 1.0
                    ) * (1.0 - self.cost_per_tie_switch),
                    rationale=(
                        f"asset {a.node_id} at risk p={a.failure_probability:.2f}; "
                        f"tie switch {tie[0]}<->{tie[1]} bypasses its load"
                    ),
                    target_node_id=a.node_id,
                ))
            # Strategy 2 — flag a load-shift suggestion for non-critical
            # loads downstream of the at-risk asset.
            elif self._has_critical(grid, a.node_id):
                actions.append(PredictiveAction(
                    kind="shift_load",
                    params={"from_node_id": a.node_id,
                            "category": "non_critical"},
                    expected_risk_reduction=a.isolated_load_mw * 0.3,
                    rationale=(
                        f"critical-load protection around {a.node_id}"
                    ),
                    target_node_id=a.node_id,
                ))
            if len(actions) >= self.max_actions:
                break
        return actions

    # ------------------------------------------------------------------
    # Convenience wrapper combining assess + recommend.
    # ------------------------------------------------------------------

    def run(self, grid: Any, twin_registry: Any) -> Dict[str, Any]:
        risks = self.assess(grid, twin_registry)
        actions = self.recommend(grid, risks)
        return {
            "risk_count": len(risks),
            "action_count": len(actions),
            "risks": [r.to_dict() for r in risks],
            "actions": [a.to_dict() for a in actions],
            "max_severity": risks[0].severity if risks else 0.0,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _isolated_load_if_fail(self, grid: Any, node_id: str) -> float:
        """Return the sum of load that would become unreachable if
        ``node_id`` failed (approximated via connected components).
        """
        g_und = grid.graph.to_undirected(as_view=False)
        if node_id not in g_und:
            return 0.0
        try:
            g_minus = g_und.copy()
            g_minus.remove_node(node_id)
        except Exception:  # noqa: BLE001
            return 0.0
        gens: Set[str] = {
            nid for nid, n in grid.nodes.items()
            if getattr(n, "node_type", "") in {
                "generator", "generator_solar", "generator_wind",
                "generator_nuclear", "generator_coal", "generator_gas",
                "solar_farm", "wind_farm", "substation",
                "primary_substation",
            } and not getattr(n, "failed", False) and nid != node_id
        }
        # Sum load over components that contain no healthy generator.
        total = 0.0
        for comp in nx.connected_components(g_minus):
            if comp & gens:
                continue
            for nid in comp:
                n = grid.nodes.get(nid)
                if n is None:
                    continue
                total += float(getattr(n, "load", 0.0))
        return float(total)

    def _severity(self, node: Any, p: float) -> float:
        """Combine failure probability with criticality."""
        crit = 1.0 if getattr(node, "node_type", "") in _CRITICAL_TYPES else 0.0
        load = min(1.0, float(getattr(node, "load", 0.0)))
        return min(1.0, 0.5 * p + 0.3 * crit + 0.2 * load)

    def _candidate_tie(
        self, grid: Any, node_id: str
    ) -> Optional[tuple]:
        """If the node has a parallel neighbour within 2 hops that does
        not currently share an edge, suggest connecting them.
        """
        try:
            g_und = grid.graph.to_undirected(as_view=False)
            if node_id not in g_und:
                return None
            neighbours = list(g_und.neighbors(node_id))
            for n in neighbours:
                for hop2 in g_und.neighbors(n):
                    if hop2 == node_id or hop2 in neighbours:
                        continue
                    # Already connected? skip.
                    if grid.graph.has_edge(node_id, hop2):
                        continue
                    return (node_id, hop2)
        except (nx.NetworkXError, AttributeError):
            return None
        return None

    def _has_critical(self, grid: Any, node_id: str) -> bool:
        g_und = grid.graph.to_undirected(as_view=False)
        if node_id not in g_und:
            return False
        try:
            reachable = nx.single_source_shortest_path_length(
                g_und, source=node_id, cutoff=4,
            )
        except nx.NetworkXError:
            return False
        for nid in reachable:
            n = grid.nodes.get(nid)
            if n is None:
                continue
            if getattr(n, "node_type", "") in _CRITICAL_TYPES:
                if not getattr(n, "failed", False):
                    return True
        return False
