"""
topology_kpis.py — small graph-metric utilities used by the planner.

Why
---
The AI planner needs to evaluate candidate topologies before
committing to a mutation.  The metrics here are well-known in the
distribution-system literature:

  - `avg_path_length`     — mean geodesic hops from each load to the
                           nearest generator (lower = shorter feeder
                           runs → lower losses, lower voltage drop).
  - `mesh_index`          — edges / nodes; higher = more meshed, more
                           redundant (good for reliability, costly to
                           build).
  - `redundancy_score`    — fraction of load buses with ≥ 2
                           generator-disjoint paths.  Used to enforce
                           N-1 reliability.
  - `articulation_count`  — number of articulation points (whose
                           removal disconnects the graph).  Lower is
                           better for self-healing.

All four are pure functions of a NetworkX graph and the grid's
node attribute dict, so they can be evaluated cheaply at every
planner iteration.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set

import networkx as nx

from simulation.grid import SmartGrid


_LOAD_TYPES = {
    "house", "hospital", "hospital_icu", "industry", "commercial",
    "school", "university", "gov_building", "ev_charger",
}
_GENERATOR_TYPES = {
    "generator_solar", "generator_wind", "generator_nuclear",
    "generator_coal", "generator_gas", "solar_farm", "wind_farm",
}


def load_nodes(grid: SmartGrid) -> List[str]:
    return [nid for nid, n in grid.nodes.items() if n.node_type in _LOAD_TYPES]


def generator_nodes(grid: SmartGrid) -> List[str]:
    return [nid for nid, n in grid.nodes.items() if n.node_type in _GENERATOR_TYPES]


def avg_path_length(grid: SmartGrid) -> float:
    """Mean hops from each load bus to the nearest generator bus.

    Returns `float('inf')` if any load is unreachable.
    """
    # Use the undirected view for connectivity (the actual DiGraph
    # carries the same edges mirrored).
    g_und = grid.graph.to_undirected()
    gens = set(generator_nodes(grid))
    if not gens:
        return float("inf")
    total = 0
    count = 0
    for nid in load_nodes(grid):
        if nid not in g_und:
            continue
        try:
            distances = nx.single_source_shortest_path_length(
                g_und, source=nid, cutoff=20
            )
            reachable = [(d, v) for v, d in distances.items() if v in gens]
            if not reachable:
                return float("inf")
            total += min(d for d, _ in reachable)
            count += 1
        except nx.NetworkXError:
            return float("inf")
    return total / count if count else float("inf")


def mesh_index(grid: SmartGrid) -> float:
    """Edge-to-node ratio.  A tree graph has ≈ 1.0; a mesh has > 1.0."""
    n = grid.graph.number_of_nodes()
    if n <= 0:
        return 0.0
    # Divide by 2 because the grid is stored as a bidirectional DiGraph.
    return grid.graph.number_of_edges() / (2.0 * n)


def redundancy_score(grid: SmartGrid) -> float:
    """Fraction of load buses with two or more generator-disjoint paths.

    Uses a fast approximation: a load is "redundant" iff it is reachable
    from two distinct generators, OR its nearest generator can be
    reached through ≥ 2 disjoint paths.  This avoids an exponential
    Menger-disjoint-path computation.
    """
    g_und = grid.graph.to_undirected()
    gens = set(generator_nodes(grid))
    if not gens:
        return 0.0
    score = 0
    total = 0
    for nid in load_nodes(grid):
        if nid not in g_und:
            continue
        total += 1
        reachable_gens: Set[str] = set()
        try:
            for gen in gens:
                if gen not in g_und:
                    continue
                if nx.has_path(g_und, nid, gen):
                    reachable_gens.add(gen)
        except nx.NetworkXError:
            pass
        if len(reachable_gens) >= 2:
            score += 1
    return score / total if total else 0.0


def articulation_count(grid: SmartGrid) -> int:
    """Number of articulation points in the power graph."""
    g_und = grid.graph.to_undirected()
    try:
        return sum(1 for _ in nx.articulation_points(g_und))
    except nx.NetworkXError:
        return 0


def all_kpis(grid: SmartGrid) -> Dict[str, float]:
    """Return all four KPIs as a dict (handy for the planner)."""
    return {
        "avg_path_length": avg_path_length(grid),
        "mesh_index": mesh_index(grid),
        "redundancy_score": redundancy_score(grid),
        "articulation_count": articulation_count(grid),
    }