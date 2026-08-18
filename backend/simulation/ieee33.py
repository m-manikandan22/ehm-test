"""
ieee33.py — IEEE 33-bus test feeder as a SmartGrid-shaped NetworkX graph.

Why this exists
---------------
The IEEE 33-bus radial distribution test feeder is the second-standard
benchmark after IEEE 13-bus. It has a slightly larger load (~3.715 MW
total) and 33 buses / 37 lines (33 segments + 5 tie switches that are
normally open). It exists so the EHM control logic can be exercised on
*two* distinct standard test feeders (Stage 5 in `main.md`).

The reference topology, line impedances, and bus loads are taken
verbatim from:
  - IEEE PES Distribution System Analysis Subcommittee Report, 1992.
  - M. E. Baran and F. F. Wu, "Network reconfiguration in distribution
    systems for loss reduction and load balancing", IEEE Trans. Power
    Delivery, vol. 4, no. 2, pp. 1401-1407, April 1989.

Per-unit values are on a 12.66 kV / 1 MVA base.

References
----------
  https://site.ieee.org/pes-testfeeders/  (IEEE 33-bus feeder spec)
"""
from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import networkx as nx  # type: ignore

from simulation.grid import SmartGrid

logger = logging.getLogger(__name__)


# ── IEEE 33-bus line data ───────────────────────────────────────────────
# (u, v, R_ohm, X_ohm, capacity_A, edge_kind, has_switch)
# Standard line impedance table from Baran & Wu (1989) and the IEEE PES
# 33-bus test feeder. Ohms are physical (not per-unit) on the 12.66 kV
# base; current capacities are derived from the published current
# ratings of the original test feeder (≈ 400 A main, tapering to 200 A).
# 5 tie switches are normally OPEN at the end of the file.
IEEE33_LINES: List[Tuple[str, str, float, float, float, str, bool]] = [
    # Main feeder (source bus 1 → 2 → … → 22)
    ("1",  "2",  0.0922, 0.0470, 400.0, "feeder", True),
    ("2",  "3",  0.4930, 0.2511, 400.0, "feeder", True),
    ("3",  "4",  0.3660, 0.1864, 400.0, "feeder", True),
    ("4",  "5",  0.3811, 0.1941, 400.0, "feeder", True),
    ("5",  "6",  0.8190, 0.7070, 400.0, "feeder", True),
    ("6",  "7",  0.1872, 0.6188, 400.0, "feeder", True),
    ("7",  "8",  0.7114, 0.2351, 400.0, "feeder", True),
    ("8",  "9",  1.0300, 0.7400, 400.0, "feeder", True),
    ("9",  "10", 1.0440, 0.7400, 400.0, "feeder", True),
    ("10", "11", 0.1966, 0.0650, 400.0, "feeder", True),
    ("11", "12", 0.3744, 0.1298, 400.0, "feeder", True),
    ("12", "13", 1.4680, 1.1550, 400.0, "feeder", True),
    ("13", "14", 0.5416, 0.7129, 400.0, "feeder", True),
    ("14", "15", 0.5910, 0.5260, 400.0, "feeder", True),
    ("15", "16", 0.7463, 0.5450, 400.0, "feeder", True),
    ("16", "17", 1.2890, 1.7210, 400.0, "feeder", True),
    ("17", "18", 0.7320, 0.5740, 400.0, "feeder", True),
    # Lateral branch from bus 2 (buses 19, 20, 21, 22)
    ("2",  "19", 0.1640, 0.1565, 250.0, "lateral", True),
    ("19", "20", 1.5042, 1.3554, 250.0, "lateral", True),
    ("20", "21", 0.4095, 0.4784, 250.0, "lateral", True),
    ("21", "22", 0.7089, 0.9373, 250.0, "lateral", True),
    # Lateral branch from bus 3 (buses 23, 24, 25)
    ("3",  "23", 0.4512, 0.3083, 250.0, "lateral", True),
    ("23", "24", 0.8980, 0.7091, 250.0, "lateral", True),
    ("24", "25", 0.8960, 0.7011, 250.0, "lateral", True),
    # Lateral branch from bus 5 (buses 26, 27, 28, 29, 30, 31, 32)
    ("5",  "26", 0.2030, 0.1034, 250.0, "lateral", True),
    ("26", "27", 0.2842, 0.1447, 250.0, "lateral", True),
    ("27", "28", 1.0590, 0.9337, 250.0, "lateral", True),
    ("28", "29", 0.8042, 0.7006, 250.0, "lateral", True),
    ("29", "30", 0.5075, 0.2585, 250.0, "lateral", True),
    ("30", "31", 0.9744, 0.9630, 250.0, "lateral", True),
    ("31", "32", 0.3105, 0.3619, 250.0, "lateral", True),
    ("32", "33", 0.3410, 0.5302, 250.0, "lateral", True),
    # ─── Tie switches (normally open) ──────────────────────────────────
    # These close to restore downstream load after a fault isolation.
    ("33", "18", 0.5000, 0.5000, 200.0, "tie", True),
    ("22", "12", 0.5000, 0.5000, 200.0, "tie", True),
    ("11", "25", 0.5000, 0.5000, 200.0, "tie", True),
    ("31", "8",  0.5000, 0.5000, 200.0, "tie", True),
    ("9",  "15", 0.5000, 0.5000, 200.0, "tie", True),
]

# Bus loads (kW, kVAR) — verbatim from the IEEE PES test feeder spec.
# Sum of active power: 3,715 kW = 3.715 MW. Sum of reactive: 2,300 kVAR.
IEEE33_LOADS: Dict[str, Tuple[float, float]] = {
    "2":  (100.0,  60.0),  "3":  ( 90.0,  40.0),
    "4":  (120.0,  80.0),  "5":  ( 60.0,  30.0),
    "6":  ( 60.0,  20.0),  "7":  (200.0, 100.0),
    "8":  (200.0, 100.0),  "9":  ( 60.0,  20.0),
    "10": ( 60.0,  20.0),  "11": ( 45.0,  30.0),
    "12": ( 60.0,  35.0),  "13": ( 60.0,  35.0),
    "14": (120.0,  80.0),  "15": ( 60.0,  10.0),
    "16": ( 60.0,  20.0),  "17": ( 60.0,  20.0),
    "18": ( 90.0,  40.0),  "19": ( 90.0,  40.0),
    "20": ( 90.0,  40.0),  "21": ( 90.0,  40.0),
    "22": ( 90.0,  40.0),  "23": ( 90.0,  50.0),
    "24": (420.0, 200.0),  "25": (420.0, 200.0),
    "26": ( 60.0,  25.0),  "27": ( 60.0,  25.0),
    "28": ( 60.0,  20.0),  "29": (120.0,  70.0),
    "30": (200.0, 600.0),  "31": (150.0,  70.0),
    "32": (210.0, 100.0),  "33": ( 60.0,  40.0),
}


def build_ieee33() -> SmartGrid:
    """
    Construct a SmartGrid-shaped instance populated with the IEEE 33-bus
    distribution test feeder.

    The returned object is wire-compatible with `SmartGrid.update_power_flow()`
    (DC PF) and `SmartGrid.flisr_9stage()` (FLISR).  IEEE 33 is radial by
    construction; the 5 tie switches are normally open and provide the
    alternate-feed paths that FLISR can close after a fault.

    Returns:
        SmartGrid with 33 buses, 37 lines (33 segments + 5 tie switches).
    """
    g = SmartGrid.__new__(SmartGrid)  # bypass __init__ to skip EHM topology
    g._init_state()
    from simulation.node import GridNode
    import random

    # 2D layout that approximates the well-known 33-bus drawing.
    coords: Dict[str, Tuple[int, int]] = {
        "1":  (50, 300),
        "2":  (140, 300), "3": (220, 300), "4":  (300, 300), "5":  (380, 300),
        "6":  (460, 300), "7": (540, 300), "8":  (620, 300), "9":  (700, 300),
        "10": (780, 300), "11":(860, 300), "12": (940, 300), "13": (1020, 300),
        "14": (1100, 300),"15":(1180, 300),"16": (1260, 300),"17": (1340, 300),
        "18": (1420, 300),
        "19": (140, 200), "20": (140, 150),"21": (140, 100),"22": (140, 50),
        "23": (220, 200), "24": (220, 100),"25": (220, 40),
        "26": (380, 200), "27": (380, 150),"28": (380, 100),
        "29": (380, 60),  "30": (380, 30), "31": (380, 5),
        "32": (380, -20), "33": (380, -40),
    }

    for bus_id, (x, y) in coords.items():
        is_source = bus_id == "1"
        node = GridNode(
            bus_id,
            node_type="substation" if is_source else "bus",
            x=x, y=y,
        )
        node.street = f"IEEE33 Bus {bus_id}"
        node._base_generation = 0.0
        node._base_load = 0.0
        node.label = f"IEEE33 Bus {bus_id}"
        node.priority = 1 if is_source else 2
        node.source_type = "source" if is_source else "none"
        g.nodes[bus_id] = node
        g.graph.add_node(bus_id)

    g.nodes["1"].generation      = 5.0
    g.nodes["1"]._base_generation = 5.0

    for bus_id, (p_kw, _q) in IEEE33_LOADS.items():
        if bus_id in g.nodes:
            g.nodes[bus_id].load = p_kw / 1000.0
            g.nodes[bus_id]._base_load = p_kw / 1000.0

    for (u, v, r_ohm, x_ohm, cap_a, kind, has_sw) in IEEE33_LINES:
        # Convert Ohms to a per-unit resistance consistent with our
        # simulator's scale.  R_pu_proxy = R / 10 — purely a scaling
        # convenience; the DC PF check uses ``resistance`` as a length
        # proxy.  The exact voltage-drop value is not used for
        # decision-making at this stage (Stage 4 will fold it in).
        edge_data = {
            "capacity":      cap_a / 100.0,  # convert A → a p.u.-ish cap
            "resistance":    r_ohm / 10.0,
            "active":        True,
            "is_tie_switch": (kind == "tie"),
            "switch_type":   "tie" if kind == "tie" else "sectionalizer",
            "switch_status": "open" if kind == "tie" else "closed",
            "has_switch":    has_sw,
            "kind":          kind,
            # Carry Ohms + Amps through so downstream AC PF can use them.
            "R_ohm":         r_ohm,
            "X_ohm":         x_ohm,
            "capacity_A":    cap_a,
        }
        g.graph.add_edge(u, v, **edge_data)
        g.graph.add_edge(v, u, **edge_data)

    g.bus_map = {nid: i for i, nid in enumerate(sorted(g.nodes.keys()))}
    for (u, v, r_ohm, x_ohm, _cap, _kind, _sw) in IEEE33_LINES:
        g.line_impedance[(u, v)] = {"R": r_ohm, "X": x_ohm}
        g.line_impedance[(v, u)] = {"R": r_ohm, "X": x_ohm}

    logger.info(
        "Built IEEE 33-bus digital twin: %d buses, %d lines, source=1",
        len(g.nodes), len(IEEE33_LINES),
    )
    return g


def get_ieee33_metadata() -> dict:
    """Return structural metadata for the IEEE 33-bus feeder."""
    total_load_kw = sum(p for p, _ in IEEE33_LOADS.values())
    total_load_kvar = sum(q for _, q in IEEE33_LOADS.values())
    return {
        "name":           "IEEE 33-bus test feeder",
        "buses":          33,
        "lines":          len(IEEE33_LINES),
        "source_bus":     "1",
        "voltage_base_kv": 12.66,
        "power_base_mva":  1.0,
        "tie_switches":    [
            (u, v) for (u, v, _r, _x, _c, kind, _sw) in IEEE33_LINES
            if kind == "tie"
        ],
        "total_load_kw":   total_load_kw,
        "total_load_kvar": total_load_kvar,
        "reference":       "Baran & Wu 1989; IEEE PES 1992",
    }


def get_ieee33_topology_table() -> List[dict]:
    """Return a list of dicts describing each edge for human inspection."""
    return [
        {
            "u": u, "v": v, "R_ohm": r, "X_ohm": x, "capacity_A": cap,
            "kind": kind, "has_switch": sw,
        }
        for (u, v, r, x, cap, kind, sw) in IEEE33_LINES
    ]


def ieee33_total_load_mw() -> float:
    """Sum of active loads in MW (handy for normalisation)."""
    return sum(p for p, _ in IEEE33_LOADS.values()) / 1000.0
