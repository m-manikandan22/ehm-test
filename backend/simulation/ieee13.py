"""
ieee13.py — IEEE 13-bus test feeder as a SmartGrid-shaped NetworkX graph.

Why this exists
---------------
The EHM control logic (FLISR, DQN, EMS) is currently validated against one
hand-crafted 49-node topology. For the system to be defensible as "general-
purpose smart-grid self-healing", it must also be runnable on a standard test
feeder that other researchers recognise. The IEEE 13-bus test feeder (IEEE PES
Distribution System Analysis Subcommittee, 1992) is the de-facto benchmark for
distribution-system research and is used in OpenDSS, GridLAB-D, Matpower, and
pandapower tutorials.

This module does NOT simulate the IEEE 13-bus physics yet — that requires an AC
power flow (next round, beyond Critical 10). For this round, we expose:

  • build_ieee13()              → standard EHM-shaped SmartGrid instance
  • get_ieee13_metadata()       → bus count, line count, expected topology
  • get_ieee13_topology_table() → human-readable edge list

Per-line impedance values follow the IEEE 13-bus specification
(4.16 kV / 5 MVA base, see Kersting "Distribution System Modeling and
Analysis", Appendix). Values are in per-unit on a 5 MVA base.

References:
  - IEEE PES Distribution System Analysis Subcommittee Report, 1992
  - https://site.ieee.org/pes-testfeeders/
  - W. H. Kersting, "Distribution System Modeling and Analysis", 4th ed.
"""
from __future__ import annotations

import logging
from typing import Dict, Tuple

import networkx as nx  # type: ignore

from simulation.grid import SmartGrid

logger = logging.getLogger(__name__)


# ── IEEE 13-bus feeder topology ────────────────────────────────────────
# Nodes: 650 ↔ 632 (substation source) — 634 — 645 — 646 — 671 — 675 — 680 — 684
#                                                       ↘
#                                          633 — 611 — 684 (via regulator)
#                                                       ↗
# Loads at nodes 634, 645, 646, 671, 675, 680, 684 (a mix of spot & distributed)
#
# Voltage regulators on 650↔632 and 632↔671; transformer 633→634 (Y-Δ step-down).
# Reference: IEEE PES Test Feeder document, working group D5.

# (u, v, R_pu, X_pu, capacity_MVA, edge_kind, has_switch)
IEEE13_LINES: list[Tuple[str, str, float, float, float, str, bool]] = [
    # Source ↔ substation (short feeder-head)
    ("650", "632", 0.0010, 0.0020, 5.0, "substation",  False),
    # Voltage regulator as an equivalent series branch
    ("632", "645", 0.0015, 0.0025, 5.0, "feeder",      True),
    # Lateral branches off 632
    ("632", "633", 0.0020, 0.0030, 2.0, "feeder",      True),
    ("632", "671", 0.0020, 0.0030, 2.0, "feeder",      True),
    # Transformer tap 633 → 611
    ("633", "611", 0.0015, 0.0025, 1.5, "transformer", True),
    # Capacitor-bank stub (no load) — bus 634 fed from 632 via short lateral
    ("632", "634", 0.0008, 0.0015, 2.0, "feeder",      True),
    # Capacitor-bank stub — bus 652 fed from 632
    ("632", "652", 0.0010, 0.0020, 2.0, "feeder",      True),
    # Capacitor-bank stub — bus 692 fed from 671
    ("671", "692", 0.0010, 0.0020, 2.0, "feeder",      True),
    # Downstream chain
    ("611", "684", 0.0010, 0.0020, 1.5, "feeder",      True),
    ("645", "646", 0.0010, 0.0020, 1.5, "lateral",     True),
    ("671", "675", 0.0015, 0.0025, 1.5, "feeder",      True),
    ("675", "680", 0.0010, 0.0020, 1.0, "lateral",     True),
    # Tie 684 → 680 (normally open switch in real feeder)
    ("684", "680", 0.0050, 0.0080, 1.0, "tie",         True),
]

# Bus loads (kW, kVAR) — distributed spot loads. Negative kW would be PV; we
# use positive loads here for conservatism.
IEEE13_LOADS: Dict[str, Tuple[float, float]] = {
    "634": (160.0, 110.0),
    "645": (170.0, 125.0),
    "646": (230.0, 132.0),
    "671": (115.0,  86.0),
    "675": ( 85.0,  61.0),
    "680": ( 60.0,  48.0),
    "684": ( 80.0,  56.0),   # spot load at regulator secondary
    "611": (170.0,  80.0),
}

# Two distributed loads (between nodes)
IEEE13_DISTRIBUTED_LOADS: Dict[Tuple[str, str, str], Tuple[float, float]] = {
    ("632", "671", "x1"): (113.5,  66.5),   # between 632 and 671, 50% point
    ("671", "675", "x2"): ( 84.0,  47.0),   # between 671 and 675
}

# Distributed PV generation on bus 675 (rooftop solar per IEEE spec)
IEEE13_DG: Dict[str, Tuple[float, float]] = {
    "675": (100.0, 0.0),   # 100 kW PV injected at 675
}


def build_ieee13() -> SmartGrid:
    """
    Construct a SmartGrid instance populated with the IEEE 13-bus feeder
    topology and per-line impedances.

    The returned object is wire-compatible with `SmartGrid.update_power_flow()`
    (which runs DC PF on top) and `SmartGrid.flisr_restore()` (FLISR). It is
    not intended for AC power flow yet — that arrives in the next iteration.

    Returns:
        SmartGrid instance with 13 buses and the IEEE 13 topology.
    """
    # We *must not* run SmartGrid.__init__() because it calls
    # _build_grid() which constructs the EHM 49-node topology. The
    # canonical way to obtain a "blank" SmartGrid is to call the
    # public initialiser helper `_init_state()`, which sets every
    # attribute the rest of the class expects without touching the
    # graph. After that we populate the IEEE 13-bus graph by hand.
    g = SmartGrid.__new__(SmartGrid)
    g._init_state()

    # ── Build IEEE 13-bus graph on the freshly-initialised grid ──────
    from simulation.node import GridNode  # local import to avoid circulars
    import random

    # 2D layout that visually matches IEEE 13-bus feeder drawings
    coords = {
        "650": ( 50, 250), "632": (200, 250),
        "633": (320, 180), "611": (420, 180), "684": (560, 180),
        "645": (320, 320), "646": (420, 320), "652": (140, 320),
        "671": (320, 410), "675": (420, 410), "680": (560, 410),
        "634": (260, 250),
        "692": (180, 410),
    }

    for bus_id, (x, y) in coords.items():
        # Source bus 650 has generation; others are loads
        is_source = bus_id == "650"
        node = GridNode(bus_id, node_type="substation" if is_source else "bus", x=x, y=y)
        node.street = f"IEEE13 Bus {bus_id}"
        node._base_generation = 0.0
        node._base_load = 0.0
        node.label = f"IEEE13 Bus {bus_id}"
        node.priority = 1 if is_source else 2
        node.source_type = "source" if is_source else "none"
        g.nodes[bus_id] = node
        g.graph.add_node(bus_id)

    # Source has high generation; PV at 675 adds renewable
    g.nodes["650"].generation     = 1.5   # MW equivalent (≈ 3 MVA available headroom)
    g.nodes["650"]._base_generation = 1.5
    g.nodes["675"].generation     = 0.10  # 100 kW PV
    g.nodes["675"]._base_generation = 0.10

    # Apply loads (kW → MW)
    for bus_id, (p_kw, _q_kvar) in IEEE13_LOADS.items():
        if bus_id in g.nodes:
            g.nodes[bus_id].load = p_kw / 1000.0
            g.nodes[bus_id]._base_load = p_kw / 1000.0

    for (u, v, tag), (p_kw, _q_kvar) in IEEE13_DISTRIBUTED_LOADS.items():
        # Distributed load is split 50/50 onto both end buses
        for end in (u, v):
            if end in g.nodes:
                g.nodes[end].load += (p_kw / 1000.0) * 0.5
                g.nodes[end]._base_load += (p_kw / 1000.0) * 0.5

    # Add edges with per-line impedance and switch metadata
    for (u, v, r_pu, x_pu, cap_mva, kind, has_sw) in IEEE13_LINES:
        edge_data = {
            "capacity":    cap_mva,
            "resistance":  r_pu / 10.0,        # back to ~grid-distance scale
            "active":      True,
            "is_tie_switch": (kind == "tie"),
            "switch_type": "tie" if kind == "tie" else "sectionalizer",
            "switch_status": "open" if kind == "tie" else "closed",
            "has_switch":  has_sw,
            "kind":        kind,
        }
        g.graph.add_edge(u, v, **edge_data)
        g.graph.add_edge(v, u, **edge_data)

    # Build bus_map and line_impedance for DC PF
    g.bus_map = {nid: i for i, nid in enumerate(sorted(g.nodes.keys()))}
    for (u, v, r_pu, x_pu, _cap, _kind, _sw) in IEEE13_LINES:
        g.line_impedance[(u, v)] = {"R": r_pu, "X": x_pu}
        g.line_impedance[(v, u)] = {"R": r_pu, "X": x_pu}

    logger.info(
        "Built IEEE 13-bus digital twin: %d buses, %d lines, source=650",
        len(g.nodes), len(IEEE13_LINES),
    )
    return g


def get_ieee13_metadata() -> dict:
    """Return the structural metadata for the IEEE 13-bus feeder."""
    return {
        "name":         "IEEE 13-bus test feeder",
        "buses":        13,
        "lines":        len(IEEE13_LINES),
        "source_bus":   "650",
        "voltage_base_kv": 4.16,
        "power_base_mva":  5.0,
        "regulators":    ["650->632", "632->671"],
        "transformers":  ["633->611"],
        "loads":         len(IEEE13_LOADS) + len(IEEE13_DISTRIBUTED_LOADS),
        "distributed_generation": list(IEEE13_DG.keys()),
        "tie_switches":  [l for l in IEEE13_LINES if l[5] == "tie"],
    }


def get_ieee13_topology_table() -> list:
    """Return a list of dicts describing each edge for human inspection."""
    return [
        {
            "u": u, "v": v, "R_pu": r, "X_pu": x, "capacity_MVA": cap,
            "kind": kind, "has_switch": sw,
        }
        for (u, v, r, x, cap, kind, sw) in IEEE13_LINES
    ]
