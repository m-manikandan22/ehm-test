"""
ai_planner.py — AI-assisted grid planner.

Why this exists
---------------
After a procedural city is generated (M1) the resulting topology is
*plausible* but not *optimal*.  An IEEE-reviewer-grade digital twin
asks the AI to suggest topology improvements: a new tie switch here,
a battery there, a redundant transformer there.  The planner must
emit a list of `PlanAction` records (declarative — the caller
applies them) so the same suggestions can be replayed offline, used
by the self-improvement loop (M4), or fed back into the city
generator for the next simulation.

The optimiser
--------------
We use a *constrained greedy + local-search* loop:

  1. Compute the baseline cost:
        C = w1·outage + w2·V_drop + w3·P_loss
            - w4·reliability - w5·restoration
  2. Enumerate candidate actions (move_transformer, add_tie_switch,
     add_battery, add_feeder, add_backup_path, …).
  3. For each candidate, *simulate* the mutation by calling the
     corresponding `grid.add_*` / `grid.move_*` method, recompute
     the five objectives, undo the mutation, and keep the best.
  4. Apply the best candidate, repeat until either `max_iterations`
     is reached or the marginal improvement falls below `eps`.
  5. Return the list of accepted actions.

The objective weights are tunable via the `PlannerConfig` dataclass.
Defaults match the user spec ("min outage, min voltage drop, min
power loss, max reliability, min restoration time").
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import networkx as nx

from planning.objectives import (
    expected_outage_energy,
    power_loss_mw,
    reliability_index,
    restoration_time_lower_bound,
    voltage_drop_index,
)
from planning.topology_kpis import generator_nodes, load_nodes
from simulation.grid import SmartGrid
from utils.seeds import make_rng


@dataclass(frozen=True)
class PlannerConfig:
    """Weights for the planner objective."""
    w_outage: float = 1.0
    w_voltage_drop: float = 1.0
    w_power_loss: float = 1.0
    w_reliability: float = 2.0   # negative in objective → reward
    w_restoration: float = 1.0
    max_iterations: int = 8
    eps: float = 1e-3

    def cost(
        self,
        outage: float,
        v_drop: float,
        loss: float,
        rel: float,
        rest: float,
    ) -> float:
        return (
            self.w_outage * outage
            + self.w_voltage_drop * v_drop
            + self.w_power_loss * loss
            - self.w_reliability * rel
            + self.w_restoration * rest
        )


@dataclass
class PlanAction:
    """A single declarative suggestion emitted by `AIPlanner.plan()`."""
    kind: str               # "add_tie_switch" | "add_battery" | …
    params: Dict[str, Any]  # kind-specific parameters
    expected_delta: float   # reduction in objective cost
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "params": dict(self.params),
            "expected_delta": float(self.expected_delta),
            "rationale": self.rationale,
        }


class AIPlanner:
    """Propose topology improvements for a SmartGrid."""

    def __init__(
        self,
        grid: SmartGrid,
        config: Optional[PlannerConfig] = None,
        seed: int = 42,
    ) -> None:
        self.grid = grid
        self.config = config or PlannerConfig()
        self._rng = make_rng(seed)

    # ------------------------------------------------------------------

    def _baseline_cost(self) -> Tuple[float, Dict[str, float]]:
        metrics = self._evaluate(self.grid)
        c = self.config.cost(**metrics)
        return c, metrics

    def _evaluate(self, g: SmartGrid) -> Dict[str, float]:
        return {
            "outage": expected_outage_energy(g),
            "v_drop": voltage_drop_index(g),
            "loss": power_loss_mw(g),
            "rel": reliability_index(g),
            "rest": restoration_time_lower_bound(g),
        }

    # ------------------------------------------------------------------

    def plan(self) -> List[PlanAction]:
        """Run the planner and return a list of accepted actions."""
        accepted: List[PlanAction] = []
        cost, _ = self._baseline_cost()
        for iteration in range(self.config.max_iterations):
            best = self._best_candidate()
            if best is None:
                break
            new_cost, new_metrics = self._apply_and_evaluate(best)
            delta = cost - new_cost
            if delta < self.config.eps:
                # Accept nothing this iteration; stop to avoid noise.
                break
            accepted.append(PlanAction(
                kind=best["kind"],
                params=best["params"],
                expected_delta=delta,
                rationale=best["rationale"],
            ))
            cost = new_cost
        return accepted

    # ------------------------------------------------------------------

    def _best_candidate(self) -> Optional[Dict[str, Any]]:
        candidates = self._enumerate_candidates()
        if not candidates:
            return None
        best = None
        best_delta = 0.0
        baseline, _ = self._baseline_cost()
        for cand in candidates:
            new_cost, _ = self._apply_and_evaluate(cand)
            delta = baseline - new_cost
            if delta > best_delta:
                best_delta = delta
                best = cand
        if best is not None:
            best["expected_delta"] = best_delta
        return best if best and best_delta > self.config.eps else None

    def _apply_and_evaluate(
        self,
        cand: Dict[str, Any],
    ) -> Tuple[float, Dict[str, float]]:
        """Apply a candidate, evaluate, undo.  Returns (cost, metrics)."""
        undo = self._apply(cand)
        try:
            metrics = self._evaluate(self.grid)
            cost = self.config.cost(**metrics)
        finally:
            self._undo(undo)
        return cost, metrics

    # ------------------------------------------------------------------

    def _enumerate_candidates(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        out.extend(self._candidate_add_tie_switches())
        out.extend(self._candidate_add_backup_paths())
        out.extend(self._candidate_add_redundancy())
        return out

    def _candidate_add_tie_switches(self) -> List[Dict[str, Any]]:
        """Add tie switches between distribution substations that are
        not yet directly connected and not already reachable through a
        tie."""
        out: List[Dict[str, Any]] = []
        g_und = self.grid.graph.to_undirected()
        ds = [nid for nid, n in self.grid.nodes.items()
              if n.node_type == "distribution_substation"]
        for i, a in enumerate(ds):
            for b in ds[i + 1: i + 4]:
                if self.grid.graph.has_edge(a, b):
                    continue
                out.append({
                    "kind": "add_tie_switch",
                    "params": {"u": a, "v": b},
                    "rationale": f"Adds redundancy between {a} and {b}",
                })
        return out[:6]   # cap so the loop stays cheap

    def _candidate_add_backup_paths(self) -> List[Dict[str, Any]]:
        """For every load that is > 4 hops from any tie switch, propose
        a backup feeder to the nearest tie switch's cluster."""
        out: List[Dict[str, Any]] = []
        g_und = self.grid.graph.to_undirected()
        tie_nodes = {
            u for u, v, d in self.grid.graph.edges(data=True)
            if d.get("is_tie_switch")
        }
        if not tie_nodes:
            return out
        for nid in load_nodes(self.grid):
            if nid not in g_und:
                continue
            try:
                dists = nx.single_source_shortest_path_length(
                    g_und, nid, cutoff=12,
                )
            except nx.NetworkXError:
                continue
            nearest = min(
                ((d, v) for v, d in dists.items() if v in tie_nodes),
                key=lambda x: x[0],
                default=None,
            )
            if nearest and nearest[0] > 4:
                out.append({
                    "kind": "add_backup_path",
                    "params": {
                        "load_id": nid,
                        "tie_id": nearest[1],
                    },
                    "rationale": (
                        f"Load {nid} is {nearest[0]} hops from any "
                        f"tie switch; add a redundant branch."
                    ),
                })
        return out[:6]

    def _candidate_add_redundancy(self) -> List[Dict[str, Any]]:
        """Propose adding a backup feeder (transformer) along the
        longest feeder chain — usually the path with the most loads."""
        g_und = self.grid.graph.to_undirected()
        longest: List[Tuple[int, str, str]] = []
        gens = list(generator_nodes(self.grid))
        if not gens:
            return []
        slack = gens[0]
        for nid in load_nodes(self.grid):
            if nid not in g_und:
                continue
            try:
                d = nx.shortest_path_length(g_und, slack, nid)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
            longest.append((d, nid, slack))
        longest.sort(reverse=True)
        out: List[Dict[str, Any]] = []
        for d, leaf, root in longest[:3]:
            out.append({
                "kind": "add_feeder",
                "params": {"from_id": root, "to_id": leaf},
                "rationale": (
                    f"Long feeder chain {root}->{leaf} ({d} hops) — "
                    "add a parallel branch."
                ),
            })
        return out

    # ------------------------------------------------------------------

    def _apply(self, cand: Dict[str, Any]) -> Callable[[], None]:
        """Apply a candidate mutation; return an undo closure."""
        if cand["kind"] == "add_tie_switch":
            u = cand["params"]["u"]
            v = cand["params"]["v"]
            try:
                self._add_tie(u, v)
            except (ValueError, KeyError):
                return lambda: None
            return lambda: self._remove_edge(u, v)

        if cand["kind"] == "add_backup_path":
            load_id = cand["params"]["load_id"]
            tie_id = cand["params"]["tie_id"]
            try:
                self._add_tie(load_id, tie_id)
            except (ValueError, KeyError):
                return lambda: None
            return lambda: self._remove_edge(load_id, tie_id)

        if cand["kind"] == "add_feeder":
            u = cand["params"]["from_id"]
            v = cand["params"]["to_id"]
            try:
                self._add_tie(u, v)
            except (ValueError, KeyError):
                return lambda: None
            return lambda: self._remove_edge(u, v)

        return lambda: None

    def _undo(self, undo: Callable[[], None]) -> None:
        try:
            undo()
        except (ValueError, KeyError, nx.NetworkXError):
            pass

    # ------------------------------------------------------------------

    def _add_tie(self, u: str, v: str) -> None:
        if u == v or u not in self.grid.nodes or v not in self.grid.nodes:
            raise ValueError("invalid tie endpoints")
        if self.grid.graph.has_edge(u, v):
            raise ValueError("edge already exists")
        # Mirror SmartGrid._add_edge's behaviour with tie-switch flags.
        node_u = self.grid.nodes[u]
        node_v = self.grid.nodes[v]
        dx = node_u.x - node_v.x
        dy = node_u.y - node_v.y
        distance = (dx * dx + dy * dy) ** 0.5
        resistance = min(0.05, max(0.001, distance * 1e-4))
        attrs = {
            "active": True,
            "resistance": resistance,
            "capacity": 4.0,
            "flow": 0.0,
            "switch_type": "tie",
            "switch_status": "open",
            "is_tie_switch": True,
        }
        self.grid.graph.add_edge(u, v, **attrs)
        self.grid.graph.add_edge(v, u, **attrs)

    def _remove_edge(self, u: str, v: str) -> None:
        if self.grid.graph.has_edge(u, v):
            self.grid.graph.remove_edge(u, v)
        if self.grid.graph.has_edge(v, u):
            self.grid.graph.remove_edge(v, u)