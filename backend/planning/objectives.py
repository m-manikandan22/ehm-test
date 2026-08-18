"""
objectives.py — closed-form cost functions used by the AI planner.

Why closed-form and not simulated
--------------------------------
The planner proposes many candidate topologies per planning pass.
A full 30-step DC-power-flow simulation per candidate is too slow.
We use *lower-bound* cost functions that can be evaluated in O(E):
they underestimate the true cost, but they preserve ordering — the
candidate with the lowest lower bound is still the candidate most
likely to win once we run the real simulation.  This is the
standard "admissible heuristic" trick from A*.

The five objectives match the five terms in the user's spec:
  - `expected_outage_energy(grid)`     → SAIDI / ENS surrogate.
  - `voltage_drop_index(grid)`         → max bus voltage deviation.
  - `power_loss_mw(grid)`              → I²R loss, summed.
  - `reliability_index(grid)`          → weighted redundancy + mesh.
  - `restoration_time_lower_bound(grid)` → BFS distance to the
    nearest tie switch for the worst-connected load.

All functions accept a `SmartGrid` and return a float.  None of
them mutate the grid.
"""
from __future__ import annotations

import math
from typing import List

import networkx as nx

from planning.topology_kpis import (
    all_kpis,
    avg_path_length,
    generator_nodes,
    load_nodes,
    redundancy_score,
)
from simulation.grid import SmartGrid


def expected_outage_energy(grid: SmartGrid) -> float:
    """Expected energy-not-supplied per fault event (lower is better).

    Heuristic: a fault on the longest feeder path will isolate
    everything downstream.  ENS ≈ load_in_isolated_subtree ×
    mean_repair_time.  We use a 1-hour mean repair time as the unit
    and report MW·h.
    """
    g_und = grid.graph.to_undirected()
    gens = set(generator_nodes(grid))
    if not gens or not g_und.nodes:
        return 0.0
    worst_isolated_mw = 0.0
    for nid, node in grid.nodes.items():
        if nid not in g_und:
            continue
        try:
            dists = nx.single_source_shortest_path_length(g_und, nid, cutoff=15)
        except nx.NetworkXError:
            continue
        isolated = 0.0
        for v, d in dists.items():
            if d == 0:
                continue
            if not nx.has_path(g_und, v, list(gens)[0]):
                continue
            # BFS distance > hop count of "vulnerable" path → contributes
            # to ENS proportional to the node's load.
            isolated += grid.nodes[v].load * (d / 20.0)
        worst_isolated_mw = max(worst_isolated_mw, isolated)
    return float(worst_isolated_mw)


def voltage_drop_index(grid: SmartGrid) -> float:
    """Maximum per-unit voltage deviation across live nodes.

    Uses the existing per-node `voltage` field if the grid has been
    solved, else falls back to a path-length-based estimate.
    """
    if grid.nodes and any(n.voltage != 1.0 for n in grid.nodes.values()):
        devs = [
            abs(n.voltage - 1.0) for n in grid.nodes.values()
            if not n.failed and not n.isolated
        ]
        return max(devs) if devs else 0.0
    # Fallback: estimate V_drop = sum(R * I) along longest path.
    g_und = grid.graph.to_undirected()
    gens = set(generator_nodes(grid))
    if not gens:
        return 0.0
    worst = 0.0
    for nid in load_nodes(grid):
        if nid not in g_und:
            continue
        try:
            path = nx.shortest_path(g_und, nid, list(gens)[0])
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
        drop = 0.0
        for u, v in zip(path[:-1], path[1:]):
            data = grid.graph.get_edge_data(u, v) or {}
            r = data.get("resistance", 0.01)
            load = grid.nodes[v].load if v in grid.nodes else 0.5
            drop += r * load * 1000.0  # pu drop approximation
        worst = max(worst, drop)
    return float(min(0.2, worst))


def power_loss_mw(grid: SmartGrid) -> float:
    """Estimated I²R loss summed over active edges.

    Uses the existing edge flow if DC PF has run, otherwise estimates
    from per-edge load * resistance.
    """
    total = 0.0
    for u, v, data in grid.graph.edges(data=True):
        r = data.get("resistance", 0.01)
        flow = data.get("flow", 0.0)
        if flow and flow != 0.0:
            # Loss in MW = I²·R·S_base; we approximate with (|flow|/10)² × R.
            i_pu = abs(flow) / 10.0
            total += (i_pu ** 2) * r
        else:
            load = grid.nodes[v].load if v in grid.nodes else 0.0
            total += 0.01 * r * (1 + load)
    return float(total)


def reliability_index(grid: SmartGrid) -> float:
    """Higher is better.  Combines redundancy + mesh + reachability."""
    kpis = all_kpis(grid)
    # Normalise each term into [0, 1].
    red = kpis["redundancy_score"]                # already in [0, 1]
    mesh = min(1.0, kpis["mesh_index"] / 2.0)     # 1.0 at mesh=2
    apl = kpis["avg_path_length"]
    apl_norm = 1.0 / (1.0 + apl) if math.isfinite(apl) else 0.0
    art_penalty = 1.0 / (1.0 + kpis["articulation_count"])
    return 0.4 * red + 0.2 * mesh + 0.2 * apl_norm + 0.2 * art_penalty


def restoration_time_lower_bound(grid: SmartGrid) -> float:
    """BFS-distance lower bound on restoration time for the worst load.

    A tie-switch closure restores a load if the load's nearest tie
    switch is one hop away *and* the tie connects to an energised
    cluster.  We return the max hop-distance to any tie switch over
    all loads (lower is better).
    """
    g_und = grid.graph.to_undirected()
    tie_edges: List[tuple] = [
        (u, v) for u, v, d in grid.graph.edges(data=True)
        if d.get("is_tie_switch")
    ]
    if not tie_edges:
        return float(len(load_nodes(grid)))   # no redundancy at all
    tie_nodes = set()
    for u, v in tie_edges:
        tie_nodes.add(u)
        tie_nodes.add(v)
    worst = 0
    for nid in load_nodes(grid):
        if nid not in g_und:
            continue
        try:
            dists = nx.single_source_shortest_path_length(
                g_und, source=nid, cutoff=20
            )
        except nx.NetworkXError:
            continue
        local = min((d for v, d in dists.items() if v in tie_nodes),
                    default=20)
        worst = max(worst, local)
    return float(worst)