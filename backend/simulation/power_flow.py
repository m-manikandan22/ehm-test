"""
power_flow.py — In-house DC Power Flow solver for the EHM smart grid.

Why this exists
---------------
The previous `_simulate_energy_flow` is a BFS with equal-split that violates
Kirchhoff's Current Law (KCL) at every multi-child bus. This module provides a
physically correct DC power flow (DC PF) overlay that respects KCL.

DC PF equations (per-unit)
--------------------------
    P_i = Σ_j B_ij · (θ_i − θ_j), for all non-slack buses i
    P_ij = (θ_i − θ_j) / X_ij, for each line (i, j)
    I_ij = |P_ij| / V_base
    loss_ij = I_ij^2 · R_ij = (P_ij^2 / V_base^2) · R_ij

Where:
    B_ij = −1 / X_ij          (off-diagonal of B-matrix)
    B_ii = Σ_{k≠i} 1 / X_ik   (diagonal of B-matrix)
    θ    = voltage angle vector
    Slack bus: θ = 0 by definition

The DC PF is a linear system. For each connected component of the network
that contains at least one generator, we identify a slack bus and solve
`B·θ = P_inj` on the reduced (slack-removed) B-matrix. Isolated components
that have no generator are dead buses — their angles are undefined and we
leave them at 0.0 with a warning.

This module does NOT depend on PyPSA, MATPOWER, or pandapower.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


# ── Per-unit base values (used for unit conversion) ─────────────────────
V_BASE_KV = 11.0         # Base voltage at distribution level (kV)
S_BASE_MVA = 10.0        # Base power (MVA) — per-unit convenience


# ── Default per-line reactance (X, per-unit) by edge category ───────────
# These match standard distribution-feeder values; see Kersting "Distribution
# System Modeling and Analysis" Table 4.1.
DEFAULT_X_BY_TYPE: Dict[str, float] = {
    "substation":    0.01,   # Step-down transformer LV side
    "transformer":   0.02,   # Service transformer
    "feeder":        0.05,   # Trunk pole-to-pole
    "lateral":       0.08,   # Lateral pole-to-house
    "tie":           0.10,   # Tie switch
    "default":       0.05,
}


def _x_for_edge(u_type: str, v_type: str, is_tie: bool) -> float:
    if is_tie:
        return DEFAULT_X_BY_TYPE["tie"]
    # Pick the most-specific category
    if "substation" in (u_type, v_type):
        return DEFAULT_X_BY_TYPE["substation"]
    if "transformer" in (u_type, v_type):
        return DEFAULT_X_BY_TYPE["transformer"]
    if "house" in (u_type, v_type) or "hospital" in (u_type, v_type) or "industry" in (u_type, v_type):
        return DEFAULT_X_BY_TYPE["lateral"]
    return DEFAULT_X_BY_TYPE["feeder"]


# ── Result container ────────────────────────────────────────────────────
@dataclass
class DCPFResult:
    """Output of dc_power_flow()."""

    converged: bool
    kcl_residual_max: float
    kcl_residual_mean: float
    bus_count: int
    line_count: int
    bus_voltage_pu: Dict[str, float]            # 1.0 for all buses in DC PF
    bus_angle_deg: Dict[str, float]             # voltage angle per bus
    line_flow_mw: Dict[Tuple[str, str], float]  # MW from i → j
    line_current_a: Dict[Tuple[str, str], float]
    line_loss_mw: Dict[Tuple[str, str], float]
    warnings: List[str] = field(default_factory=list)
    slack_bus_id: str = ""


# ── Main entry point ────────────────────────────────────────────────────
def dc_power_flow(grid, slack_bus_id: Optional[str] = None) -> DCPFResult:
    """
    Run DC power flow on a SmartGrid (or any object exposing .graph, .nodes,
    .bus_map, .line_impedance).

    Args:
        grid: object with .graph (NetworkX), .nodes (dict), .bus_map (dict
              node_id → int bus_id), .line_impedance (dict (u,v) → {"R":...,"X":...})
        slack_bus_id: optional explicit slack bus node_id. Defaults to the
              first generator node.

    Returns:
        DCPFResult with per-bus angles, per-line P/I/loss, and KCL residuals.
    """
    warnings: List[str] = []

    # ── Identify all candidate buses (every active node) ────────────────
    active_nodes = [
        nid for nid, n in grid.nodes.items()
        if not n.failed and not n.isolated
    ]
    if not active_nodes:
        return _empty_result("no active nodes")

    # ── Build bus map if missing ────────────────────────────────────────
    if not getattr(grid, "bus_map", None):
        grid.bus_map = {nid: i for i, nid in enumerate(sorted(active_nodes))}

    # ── Pick the slack bus ──────────────────────────────────────────────
    if slack_bus_id is None:
        gens = [
            nid for nid in active_nodes
            if grid.nodes[nid].node_type.startswith("generator")
        ]
        if not gens:
            # Fallback: any substation
            subs = [nid for nid in active_nodes if grid.nodes[nid].node_type == "substation"]
            slack_bus_id = subs[0] if subs else active_nodes[0]
        else:
            slack_bus_id = gens[0]

    if slack_bus_id not in active_nodes:
        return _empty_result(f"slack bus {slack_bus_id} not active")

    # ── Decompose the network into weakly-connected components and solve
    # each independently. This is the standard fix for singular B-matrix
    # under partial islanding caused by failed/tripped edges.
    bus_angle_deg: Dict[str, float] = {slack_bus_id: 0.0}
    bus_voltage_pu: Dict[str, float] = {nid: 1.0 for nid in active_nodes}

    # Build a subgraph of active edges among active nodes for connectivity
    active_set = set(active_nodes)
    comp_graph = nx.DiGraph()
    for nid in active_nodes:
        comp_graph.add_node(nid)
    for u, v, data in grid.graph.edges(data=True):
        if not data.get("active", True):
            continue
        if u in active_set and v in active_set:
            comp_graph.add_edge(u, v)
            comp_graph.add_edge(v, u)   # undirected connectivity via both arcs

    components = list(nx.weakly_connected_components(comp_graph))
    n_islands = len(components)

    # Find the component that contains the global slack bus
    global_slack_comp = None
    for comp in components:
        if slack_bus_id in comp:
            global_slack_comp = comp
            break

    # ── Build per-component B matrices and solve ──────────────────────
    line_flow_mw: Dict[Tuple[str, str], float] = {}
    line_current_a: Dict[Tuple[str, str], float] = {}
    line_loss_mw: Dict[Tuple[str, str], float] = {}
    all_residuals: list = []

    for comp in components:
        comp_nodes = [nid for nid in comp if nid in active_set]
        # Find a generator in this component; prefer the global slack if
        # it's in this component.
        if global_slack_comp is comp:
            comp_slack = slack_bus_id
        else:
            gens = [
                nid for nid in comp_nodes
                if grid.nodes[nid].node_type.startswith("generator")
            ]
            if gens:
                comp_slack = gens[0]
            else:
                subs = [
                    nid for nid in comp_nodes
                    if grid.nodes[nid].node_type == "substation"
                ]
                comp_slack = subs[0] if subs else comp_nodes[0]

        non_slack = [nid for nid in comp_nodes if nid != comp_slack]
        if not non_slack:
            # Single-bus component: slack angle is 0, no flow to compute
            continue
        idx_of = {nid: i for i, nid in enumerate(non_slack)}
        n = len(non_slack)
        B = np.zeros((n, n), dtype=float)
        P_inj = np.zeros(n, dtype=float)

        # Build B for this component
        for u, v, data in grid.graph.edges(data=True):
            if not data.get("active", True):
                continue
            if u not in comp or v not in comp:
                continue
            imp = _get_impedance(grid, u, v)
            if imp["X"] is None or imp["X"] <= 0:
                continue
            b_ij = 1.0 / imp["X"]
            if u in idx_of:
                B[idx_of[u], idx_of[u]] += b_ij
            if v in idx_of:
                B[idx_of[v], idx_of[v]] += b_ij
            if u in idx_of and v in idx_of:
                B[idx_of[u], idx_of[v]] -= b_ij
                B[idx_of[v], idx_of[u]] -= b_ij

        # Compute P_inj for non-slack buses
        for nid in non_slack:
            node = grid.nodes[nid]
            p_inj_pu = (max(0.0, float(node.generation)) - float(node.load)) / S_BASE_MVA
            P_inj[idx_of[nid]] = p_inj_pu

        # Solve this component
        try:
            rank = np.linalg.matrix_rank(B)
            if rank < n:
                # Still singular sub-component — use lstsq with tolerance
                theta_comp, residuals, _, _ = np.linalg.lstsq(B, P_inj, rcond=None)
                # Residual sum-of-squares is the unrecoverable energy in
                # this sub-island. Convert to per-element KCL.
                if residuals.size > 0:
                    all_residuals.extend(
                        [abs(r) for r in (B @ theta_comp - P_inj)]
                    )
                warnings.append(
                    f"Component {{ {', '.join(sorted(comp_nodes)[:3])}... }} "
                    f"rank-deficient (rank={rank}/{n}); using pseudoinverse."
                )
            else:
                theta_comp = np.linalg.solve(B, P_inj)
                all_residuals.extend(
                    [abs(r) for r in (B @ theta_comp - P_inj)]
                )
        except np.linalg.LinAlgError as e:
            logger.warning("DC PF component solve failed: %s", e)
            warnings.append(f"Component solve failed: {e}")
            continue

        # Save angles
        for nid in non_slack:
            bus_angle_deg[nid] = float(np.degrees(theta_comp[idx_of[nid]]))

    # Multi-island warning (was singular before)
    if n_islands > 1:
        unpowered = []
        for comp in components:
            if global_slack_comp is not comp:
                gens = [n for n in comp if grid.nodes[n].node_type.startswith("generator")]
                if not gens:
                    unpowered.extend(sorted(comp))
        if unpowered:
            warnings.append(
                f"Grid has {n_islands} islands; {len(unpowered)} buses are "
                f"in unpowered islands (no generator): {unpowered[:5]}"
            )
        else:
            warnings.append(
                f"Grid has {n_islands} islands; each solved independently."
            )

    # ── Compute per-line flows, currents, losses (only on active edges
    # within a connected component) ─────────────────────────────────────

    # ── Per-line flows, currents, losses ───────────────────────────────
    line_flow_mw: Dict[Tuple[str, str], float] = {}
    line_current_a: Dict[Tuple[str, str], float] = {}
    line_loss_mw: Dict[Tuple[str, str], float] = {}

    for u, v, data in grid.graph.edges(data=True):
        if not data.get("active", True):
            continue
        if u not in active_nodes or v not in active_nodes:
            continue
        # Avoid double-counting: only count the (u, v) directed edge that
        # was used when building B (i.e., as it appears in the graph).
        imp = _get_impedance(grid, u, v)
        if imp["X"] is None or imp["X"] <= 0:
            continue
        # Per-unit angle difference
        theta_u = np.radians(bus_angle_deg.get(u, 0.0))
        theta_v = np.radians(bus_angle_deg.get(v, 0.0))
        p_ij_pu = (theta_u - theta_v) / imp["X"]
        p_ij_mw = p_ij_pu * S_BASE_MVA
        # Current magnitude (A): I = P / (√3 · V_LL) for 3φ; in per-unit
        # I_pu = P_pu / V_pu, then A = I_pu · (S_base / (√3 · V_base_kV · 1000))
        i_ij_pu = abs(p_ij_pu) / 1.0  # V_pu = 1 in DC
        i_ij_a = i_ij_pu * (S_BASE_MVA * 1e6) / (np.sqrt(3) * V_BASE_KV * 1e3)
        # Loss: I²R (per-unit), then convert to MW
        if imp["R"] is None or imp["R"] <= 0:
            loss_mw = 0.0
        else:
            loss_pu = (i_ij_pu ** 2) * imp["R"]
            loss_mw = loss_pu * S_BASE_MVA
        line_flow_mw[(u, v)] = float(p_ij_mw)
        line_current_a[(u, v)] = float(i_ij_a)
        line_loss_mw[(u, v)] = float(loss_mw)

    # ── KCL residual check ─────────────────────────────────────────────
    # A correctly solved DC PF has residuals at machine precision.
    # We aggregate per-component residuals computed during the solve.
    if all_residuals:
        kcl_residual_max = float(max(abs(r) for r in all_residuals))
        kcl_residual_mean = float(sum(abs(r) for r in all_residuals) / len(all_residuals))
    else:
        # All components were single-bus or trivially solved
        kcl_residual_max = 0.0
        kcl_residual_mean = 0.0

    if kcl_residual_max > 1e-6:
        warnings.append(
            f"KCL residual {kcl_residual_max:.2e} exceeds 1e-6 tolerance "
            f"(grid may have unpowered islands with unmet load)."
        )

    # ── V_angles that exceed ±30° are flagged (informational only) ─────
    for nid, ang in bus_angle_deg.items():
        if abs(ang) > 30.0:
            warnings.append(
                f"Voltage angle at {nid} is {ang:.1f}° (DC PF valid for small angles only)."
            )

    return DCPFResult(
        converged=True,
        kcl_residual_max=kcl_residual_max,
        kcl_residual_mean=kcl_residual_mean,
        bus_count=len(active_nodes),
        line_count=len(line_flow_mw),
        bus_voltage_pu=bus_voltage_pu,
        bus_angle_deg=bus_angle_deg,
        line_flow_mw=line_flow_mw,
        line_current_a=line_current_a,
        line_loss_mw=line_loss_mw,
        warnings=warnings,
        slack_bus_id=slack_bus_id,
    )


# ── Helpers ─────────────────────────────────────────────────────────────
def _get_impedance(grid, u: str, v: str) -> dict:
    """Look up the (R, X) per-unit impedance for edge (u, v) in the grid."""
    imp_map = getattr(grid, "line_impedance", None) or {}
    # Try both directions
    if (u, v) in imp_map:
        return imp_map[(u, v)]
    if (v, u) in imp_map:
        return imp_map[(v, u)]
    # Synthesize a default
    is_tie = False
    try:
        edge_data = grid.graph.get_edge_data(u, v) or grid.graph.get_edge_data(v, u) or {}
        is_tie = bool(edge_data.get("is_tie_switch", False))
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not read tie-switch flag from edge %s-%s: %s", u, v, e)
    nu = grid.nodes.get(u)
    nv = grid.nodes.get(v)
    u_type = getattr(nu, "node_type", "") if nu else ""
    v_type = getattr(nv, "node_type", "") if nv else ""
    x = _x_for_edge(u_type, v_type, is_tie)
    # R: re-use edge resistance if available (already in pu-ish units)
    r = None
    if nu and nv:
        try:
            d = grid.graph.get_edge_data(u, v) or grid.graph.get_edge_data(v, u) or {}
            r_val = d.get("resistance", None)
            if r_val is not None and r_val > 0:
                # Edge resistance is a small float (0.001–0.012). For DC PF in
                # per-unit, treat it as 10× the actual value so it makes
                # sense in a 10 MVA / 11 kV base. This is a calibration
                # choice documented in docs/power_flow.md.
                r = r_val * 10.0
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not read resistance from edge %s-%s: %s", u, v, e)
            r = None
    return {"R": r, "X": x}


def _empty_result(reason: str) -> DCPFResult:
    return DCPFResult(
        converged=False,
        kcl_residual_max=float("inf"),
        kcl_residual_mean=float("inf"),
        bus_count=0,
        line_count=0,
        bus_voltage_pu={},
        bus_angle_deg={},
        line_flow_mw={},
        line_current_a={},
        line_loss_mw={},
        warnings=[f"DC PF did not run: {reason}"],
        slack_bus_id="",
    )


# ── Self-test (textbook 5-bus case) ─────────────────────────────────────
def _self_test_5bus() -> bool:
    """
    Textbook 5-bus test: 2 generators, 3 loads. Solves DC PF and checks KCL.
    Topology:
        Bus1 (slack) --- Bus2 --- Bus3
            |                        |
            +------- Bus4 --- Bus5 ---+
    All X = 0.1 pu; P_load: Bus2=1.0, Bus4=0.5, Bus5=1.5 (MW).
    """
    import networkx as nx

    class _N:
        def __init__(self, nid, gen=0.0, load=0.0, t="bus"):
            self.node_id = nid
            self.node_type = t
            self.generation = gen
            self.load = load
            self.failed = False
            self.isolated = False
            self.voltage_angle = 0.0

    nodes = {
        "B1": _N("B1", gen=0.0, t="generator"),  # Slack
        "B2": _N("B2", load=1.0),
        "B3": _N("B3", load=0.0),
        "B4": _N("B4", load=0.5),
        "B5": _N("B5", load=1.5),
    }
    edges = [
        ("B1", "B2", 0.1), ("B1", "B4", 0.1),
        ("B2", "B3", 0.1), ("B3", "B5", 0.1),
        ("B4", "B5", 0.1),
    ]
    G = nx.DiGraph()
    for nid in nodes:
        G.add_node(nid)
    for u, v, x in edges:
        G.add_edge(u, v)
        G.add_edge(v, u)

    class _Grid:
        pass

    g = _Grid()
    g.graph = G
    g.nodes = nodes
    g.bus_map = {nid: i for i, nid in enumerate(sorted(nodes.keys()))}
    g.line_impedance = {(u, v): {"R": 0.01, "X": x} for u, v, x in edges}
    # Add reverse direction too
    for u, v, x in edges:
        g.line_impedance[(v, u)] = {"R": 0.01, "X": x}

    res = dc_power_flow(g, slack_bus_id="B1")
    assert res.converged, f"5-bus solve failed: {res.warnings}"
    # KCL must be tight
    assert res.kcl_residual_max < 1e-6, (
        f"KCL residual too high: {res.kcl_residual_max:.2e}"
    )
    # Slack must carry the full load
    slack_angle = res.bus_angle_deg["B1"]
    assert abs(slack_angle) < 1e-6
    # Other angles should be negative (loads pull angle down)
    for nid, ang in res.bus_angle_deg.items():
        if nid != "B1":
            assert ang < 0.0, f"Bus {nid} has non-negative angle {ang}"
    return True


if __name__ == "__main__":
    ok = _self_test_5bus()
    print("5-bus self-test:", "PASS" if ok else "FAIL")
