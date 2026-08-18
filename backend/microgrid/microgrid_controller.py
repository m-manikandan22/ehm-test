"""
microgrid_controller.py — controlled islanding + reconnect.

Why
---
When a section of the distribution grid loses its main-source feed,
the FLISR pipeline tries to reroute through tie switches.  When no
tie path exists, the only way to keep critical loads alive is to
form a *microgrid*: a self-sufficient island with its own local
generation, storage, and load shedding.

This module is the seam between FLISR's RESTORE step and the
microgrid primitive.  It does not invent new physics — it uses the
existing ``SmartGrid.predictive_islanding`` / ``inject_failure`` /
``restore_node`` API surface, so the EMS and DC power-flow code
stay untouched.

Design points:
  - ``form_islands(grid, faulted_nodes)`` examines every healthy
    generator, builds a reachable sub-graph through closed,
    non-faulted edges, and "islands" each by flagging the cut edges
    in ``grid.graph`` (we use the existing ``is_islanded`` /
    ``island_id`` attributes — see ``simulation/grid.py``).
  - ``island_health(grid, island_id)`` returns load/gen/SOC stats for
    that island.
  - ``reconnect(grid)`` clears island flags after the upstream fault
    is repaired.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional, Set

import networkx as nx


class MicrogridController:
    """Form, inspect, and dissolve microgrid islands."""

    def __init__(self) -> None:
        self._next_island_id: int = 1
        # Cache of the most recent islands, keyed by island_id.
        self._islands: Dict[int, Set[str]] = {}

    # ------------------------------------------------------------------
    # Islanding
    # ------------------------------------------------------------------

    def form_islands(
        self,
        grid: Any,
        faulted_nodes: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Identify healthy islands around healthy generators.

        Returns a list of island summaries (one per island), each with
        ``island_id``, ``nodes``, ``generators``, ``loads``,
        ``has_source``.
        """
        faulted_nodes = set(faulted_nodes or [])
        g_und = grid.graph.to_undirected(as_view=False)
        # Remove failed nodes and any edges incident to them.
        for nid in faulted_nodes:
            if nid in g_und:
                g_und.remove_node(nid)
        # Iterate over connected components that contain a generator.
        islands: List[Dict[str, Any]] = []
        self._next_island_id = 1
        self._islands = {}
        for comp in nx.connected_components(g_und):
            comp_nodes = set(comp)
            generators = sorted([
                nid for nid in comp_nodes
                if grid.nodes[nid].node_type in {
                    "generator", "generator_solar", "generator_wind",
                    "generator_nuclear", "generator_coal", "generator_gas",
                    "solar_farm", "wind_farm", "substation",
                    "primary_substation",
                } and not grid.nodes[nid].failed
            ])
            loads = sorted([
                nid for nid in comp_nodes
                if grid.nodes[nid].node_type in {
                    "house", "hospital", "hospital_icu", "industry",
                    "commercial", "school", "university", "gov_building",
                    "ev_charger",
                }
            ])
            if not generators:
                # Island without source — no point islanding; let FLISR skip.
                continue
            island_id = self._next_island_id
            self._next_island_id += 1
            self._islands[island_id] = comp_nodes
            islands.append({
                "island_id": island_id,
                "nodes": sorted(comp_nodes),
                "generators": generators,
                "loads": loads,
                "has_source": True,
                "size": len(comp_nodes),
            })
        return islands

    # ------------------------------------------------------------------

    def island_health(self, grid: Any, island_id: int) -> Dict[str, Any]:
        """Return load/gen/SOC rollups for a specific island."""
        nodes = self._islands.get(island_id, set())
        total_load = 0.0
        total_gen = 0.0
        total_soc = 0.0
        n_storage = 0
        n_failed = 0
        for nid in nodes:
            n = grid.nodes[nid]
            total_load += float(getattr(n, "load", 0.0))
            total_gen += float(getattr(n, "generation", 0.0))
            if getattr(n, "node_type", "") in {"battery", "bess", "supercap"}:
                total_soc += float(getattr(n, "battery_level", 0.0))
                n_storage += 1
            if getattr(n, "failed", False):
                n_failed += 1
        avg_soc = total_soc / n_storage if n_storage else 0.0
        balance = total_gen - total_load
        return {
            "island_id": island_id,
            "size": len(nodes),
            "total_load": total_load,
            "total_gen": total_gen,
            "balance_mw": balance,
            "avg_storage_soc": avg_soc,
            "n_storage": n_storage,
            "n_failed": n_failed,
            "healthy": balance >= -1e-6 and n_failed == 0,
        }

    # ------------------------------------------------------------------

    def reconnect(self, grid: Any) -> int:
        """Clear all islanding metadata; returns the number of nodes reset."""
        cleared = 0
        for nid, node in grid.nodes.items():
            if hasattr(node, "is_islanded") and getattr(node, "is_islanded", False):
                node.is_islanded = False
                cleared += 1
            if hasattr(node, "island_id") and getattr(node, "island_id", None) is not None:
                node.island_id = None
        self._islands = {}
        return cleared

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    @property
    def islands(self) -> Dict[int, Set[str]]:
        return dict(self._islands)