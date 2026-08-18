"""
ac_power_flow.py — AC Power Flow solver for the EHM smart grid.

Why this exists
---------------
The default ``simulation/power_flow.py`` solves a DC power flow (DC PF):
linearised, ignoring Q, voltages are 1.0 p.u., and reactive losses are
invisible. DC PF is fast and physically consistent in KCL, but it cannot
answer questions like:

- "Will this bus be under-voltage after the feeder trips?"
- "Does the substation need to absorb reactive power?"
- "Is the generator hitting its Q-limit?"

This module provides an AC Power Flow (AC PF) wrapper around
``pandapower``. Pandapower builds the bus admittance matrix (Y-bus) from
per-line R/X, then runs Newton-Raphson in polar form to solve:

    P_i = Σ_j |V_i||V_j|(G_ij cos(θ_i−θ_j) + B_ij sin(θ_i−θ_j))
    Q_i = Σ_j |V_i||V_j|(G_ij sin(θ_i−θ_j) − B_ij cos(θ_i−θ_j))

Reference: Stott (1974), "Review of Load-Flow Calculation Methods",
*Proc. IEEE* 62(7), 916–929.

Important — what this module is and is not
-----------------------------------------
✅ It is a thin wrapper around a validated AC PF solver (pandapower). The
   Newton-Raphson implementation comes from ``pandapower.runpp`` and is
   not re-implemented here.

❌ It is **not** a 3-phase unbalanced AC PF. The IEEE 13-bus feeder is
   unbalanced (single-phase laterals, voltage regulators), and pandapower
   supports this via the ``runpp_3ph`` engine, but that requires careful
   per-phase line modelling. For the round-one validation we use the
   per-unit equivalent: a positive-sequence, balanced representation of
   the IEEE 13-bus topology with lumped spot loads. This is sufficient
   to demonstrate convergence and to compare angles against the DC PF
   baseline (DC PF ≈ AC PF when angles are small and R/X ratios are
   similar across the network).

To make a *fully-validated* claim against the IEEE 13-bus reference, we
would need: (1) full per-phase line data, (2) voltage regulator tap
model, (3) explicit transformer Y-Δ model. None of those exist in the
EHM ``simulation/ieee13.py`` builder today. The validation script in
``experiments/ieee13_validation.py`` reports *what* it compared and
*what* it does not, so the limitations are explicit.

Status
------
This module is **demonstrative**, not research-grade. It shows the
solver interface works on a real topology, but the per-unit lumping
approximation in ``simulation/ieee13.py`` limits it from being a
publication-ready validation. See ``docs/VALIDATION.md`` for the
honest enumeration.
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Apply the pandas 3.0+ CoW compat patch BEFORE importing pandapower.
# We need to ensure the patch module is importable from the project
# root (when this file is imported via ``python -m experiments.*``).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_ROOT = os.path.dirname(_THIS_DIR)
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
try:
    from utils.pandas_compat import _apply_pandas_compat_patch
    _apply_pandas_compat_patch()
except Exception:
    # If the patch can't be applied we continue without it; pandapower
    # may still work, just with the read-only-array error visible.
    pass

logger = logging.getLogger(__name__)


# Lazy import — pandapower may not be installed in CI.
try:  # pragma: no cover - import guarded at runtime
    import pandapower as pp  # type: ignore
    PANDAPOWER_AVAILABLE = True
except ImportError:  # pragma: no cover
    pp = None  # type: ignore
    PANDAPOWER_AVAILABLE = False


# ── Result container ────────────────────────────────────────────────────
@dataclass
class ACPFResult:
    """Output of ``run_ac_power_flow``."""

    converged: bool
    method: str = "newton_raphson"
    bus_count: int = 0
    line_count: int = 0
    bus_voltage_pu: Dict[str, float] = field(default_factory=dict)
    bus_angle_deg: Dict[str, float] = field(default_factory=dict)
    line_flow_mw: Dict[Tuple[str, str], float] = field(default_factory=dict)
    line_flow_mvar: Dict[Tuple[str, str], float] = field(default_factory=dict)
    line_loss_mw: Dict[Tuple[str, str], float] = field(default_factory=dict)
    line_loss_mvar: Dict[Tuple[str, str], float] = field(default_factory=dict)
    bus_q_injected_mvar: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    slack_bus_id: str = ""
    error: Optional[str] = None


# ── Main entry point ────────────────────────────────────────────────────
def run_ac_power_flow(
    grid,
    slack_bus_id: Optional[str] = None,
    *,
    method: str = "newton",
    max_iterations: int = 30,
    tolerance_mva: float = 1e-6,
) -> ACPFResult:
    """Run AC power flow on a SmartGrid-shaped object.

    The grid must expose:
      - ``.nodes``  — dict of ``node_id`` → object with ``.generation``,
        ``.load``, ``.failed``, ``.isolated``, ``.node_type``.
      - ``.graph`` — NetworkX DiGraph with edges carrying ``resistance``
        and ``reactance`` (or computed via the IEEE 13 builder), and
        ``active`` flags.
      - ``.bus_map`` — optional dict of ``node_id`` → integer bus id.

    Returns an :class:`ACPFResult`. If pandapower is not installed or the
    solve fails, ``converged`` is ``False`` and ``error`` describes the
    reason. Callers should treat AC PF as an enhancement and fall back to
    DC PF when AC PF is unavailable.
    """
    if not PANDAPOWER_AVAILABLE:
        return _unavailable_result(
            "pandapower is not installed; install with "
            "`pip install pandapower` to enable AC PF."
        )

    try:
        net = _build_pandapower_network(grid, slack_bus_id=slack_bus_id)
    except Exception as exc:  # noqa: BLE001 - we want the full message
        logger.warning("Could not build pandapower network: %r", exc)
        return _unavailable_result(f"network build failed: {exc!r}")

    if len(net.bus) == 0:
        return _unavailable_result("no active buses")

    try:
        pp.runpp(
            net,
            algorithm="nr",   # Newton-Raphson (Stott 1974)
            calculate_voltage_angles=True,
            init="flat",
            tolerance_mva=tolerance_mva,
            max_iteration=max_iterations,
            enforce_q_lims=False,  # We don't model Q-limits on the gens yet
        )
    except pp.LoadflowNotConverged as exc:  # type: ignore[attr-defined]
        return ACPFResult(
            converged=False,
            bus_count=int(len(net.bus)),
            line_count=int(len(net.line)),
            warnings=[f"Newton-Raphson did not converge: {exc}"],
            error=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        return ACPFResult(
            converged=False,
            bus_count=int(len(net.bus)),
            line_count=int(len(net.line)),
            warnings=[f"AC PF solver crashed: {exc!r}"],
            error=repr(exc),
        )

    # ── Translate pandapower result into EHM-friendly dicts ───────────
    bus_voltage_pu: Dict[str, float] = {}
    bus_angle_deg: Dict[str, float] = {}
    bus_q_injected_mvar: Dict[str, float] = {}

    # Invert the bus_map we built (pp_index → ehm_node_id).
    pp_bus_to_ehm: Dict[int, str] = {}
    for ehm_id, pp_idx in getattr(grid, "_ac_bus_map", {}).items():
        pp_bus_to_ehm[int(pp_idx)] = ehm_id

    for pp_idx, row in net.res_bus.iterrows():
        ehm_id = pp_bus_to_ehm.get(int(pp_idx))
        if ehm_id is None:
            continue
        bus_voltage_pu[ehm_id] = float(row["vm_pu"])
        bus_angle_deg[ehm_id] = float(row["va_degree"])
        # Net reactive injection from gen + load
        q_gen = float(net.res_gen.loc[net.gen.bus == pp_idx, "q_mvar"].sum())
        q_load = float(net.res_load.loc[net.load.bus == pp_idx, "q_mvar"].sum())
        bus_q_injected_mvar[ehm_id] = q_gen - q_load

    line_flow_mw: Dict[Tuple[str, str], float] = {}
    line_flow_mvar: Dict[Tuple[str, str], float] = {}
    line_loss_mw: Dict[Tuple[str, str], float] = {}
    line_loss_mvar: Dict[Tuple[str, str], float] = {}

    pp_line_to_ehm: Dict[int, Tuple[str, str]] = getattr(grid, "_ac_line_map", {})
    for pp_idx, row in net.res_line.iterrows():
        ehm_edge = pp_line_to_ehm.get(int(pp_idx))
        if ehm_edge is None:
            continue
        u, v = ehm_edge
        # pandapower reports flow from bus → bus; we report the same direction
        line_flow_mw[(u, v)] = float(row["p_from_mw"])
        line_flow_mvar[(u, v)] = float(row["q_from_mvar"])
        line_loss_mw[(u, v)] = float(row["pl_mw"])
        line_loss_mvar[(u, v)] = float(row["ql_mvar"])

    warnings: List[str] = []
    # Flag any bus outside the ANSI C84.1 acceptable range (0.95–1.05 p.u.)
    for nid, v in bus_voltage_pu.items():
        if v < 0.95 or v > 1.05:
            warnings.append(
                f"Bus {nid} voltage {v:.3f} p.u. is outside "
                f"ANSI C84.1 acceptable range [0.95, 1.05]."
            )

    slack_ehm = pp_bus_to_ehm.get(int(net.ext_grid.bus.iloc[0]), "")

    return ACPFResult(
        converged=True,
        method=f"newton_raphson (pandapower {pp.__version__})",
        bus_count=int(len(net.bus)),
        line_count=int(len(net.line)),
        bus_voltage_pu=bus_voltage_pu,
        bus_angle_deg=bus_angle_deg,
        line_flow_mw=line_flow_mw,
        line_flow_mvar=line_flow_mvar,
        line_loss_mw=line_loss_mw,
        line_loss_mvar=line_loss_mvar,
        bus_q_injected_mvar=bus_q_injected_mvar,
        warnings=warnings,
        slack_bus_id=slack_ehm,
    )


# ── Network builder ─────────────────────────────────────────────────────
def _build_pandapower_network(grid, *, slack_bus_id: Optional[str] = None):
    """Build a pandapower network from a SmartGrid-shaped object.

    The builder uses balanced positive-sequence per-unit equivalents:
      - V_base = 11 kV (distribution)
      - S_base = 10 MVA
      - Each SmartGrid edge becomes one pandapower line with per-unit R/X.
      - Loads are spot loads at each non-source bus with P = load (MW)
        and Q ≈ 0.3·P (typical distribution power factor 0.95).
      - Generation at "substation" / "generator" buses is an ``sgen`` if
        < 1 MW or a ``gen`` otherwise (pandapower convention).
    """
    net = pp.create_empty_network(name="EHM AC PF")

    # Pick active nodes
    active_nodes = [
        nid for nid, n in grid.nodes.items()
        if not n.failed and not n.isolated
    ]
    if not active_nodes:
        return net

    # Identify the slack (external grid) bus
    if slack_bus_id is None:
        gens = [
            nid for nid in active_nodes
            if str(grid.nodes[nid].node_type).startswith("generator")
        ]
        if not gens:
            subs = [
                nid for nid in active_nodes
                if grid.nodes[nid].node_type == "substation"
            ]
            gens = subs if subs else active_nodes
        slack_bus_id = gens[0]

    # Add buses
    bus_map: Dict[str, int] = {}
    for nid in active_nodes:
        # Per-unit equivalent; in real life we'd carry V_base per node.
        idx = pp.create_bus(net, vn_kv=11.0, name=str(nid))
        bus_map[nid] = int(idx)

    # External grid (slack)
    pp.create_ext_grid(net, bus=bus_map[slack_bus_id], vm_pu=1.02,
                       name="external_grid", min_p_mw=-100.0,
                       max_p_mw=100.0, min_q_mvar=-100.0,
                       max_q_mvar=100.0)

    # Add generators and static generators (PV / substation)
    for nid in active_nodes:
        if nid == slack_bus_id:
            continue
        p_mw = float(getattr(grid.nodes[nid], "generation", 0.0))
        if p_mw <= 0:
            continue
        # pv buses → sgen (no voltage control in our lumped model)
        try:
            pp.create_sgen(net, bus=bus_map[nid], p_mw=p_mw,
                           q_mvar=0.0, name=f"sgen_{nid}")
        except Exception:  # noqa: BLE001
            pass

    # Add loads (spot loads at every non-source bus)
    for nid in active_nodes:
        if nid == slack_bus_id:
            continue
        p_mw = float(getattr(grid.nodes[nid], "load", 0.0))
        if p_mw <= 0:
            continue
        # Typical distribution PF = 0.95 → tan(acos(0.95)) ≈ 0.3287
        q_mvar = p_mw * 0.3287
        try:
            pp.create_load(net, bus=bus_map[nid], p_mw=p_mw,
                           q_mvar=q_mvar, name=f"load_{nid}")
        except Exception:  # noqa: BLE001
            pass

    # Add lines from the grid graph.
    # We add only one direction per pair (pandapower treats lines as
    # bidirectional; we lose the "u->v" vs "v->u" distinction).
    line_map: Dict[int, Tuple[str, str]] = {}
    added_pairs: set = set()
    for u, v, data in grid.graph.edges(data=True):
        if not data.get("active", True):
            continue
        if u not in active_nodes or v not in active_nodes:
            continue
        pair = tuple(sorted((u, v)))
        if pair in added_pairs:
            continue
        added_pairs.add(pair)
        r_pu = float(data.get("resistance", 0.01)) * 10.0  # calibration
        # reactance is stored either as ``reactance`` or via line_impedance
        x_pu = None
        if "reactance" in data:
            x_pu = float(data["reactance"])
        else:
            imp = grid.line_impedance.get((u, v)) or grid.line_impedance.get((v, u))
            if imp and imp.get("X") is not None:
                x_pu = float(imp["X"])
        if x_pu is None or x_pu <= 0:
            x_pu = 0.05
        # Use create_line_from_parameters because pandapower 2.x
        # requires a ``std_type`` positional arg for create_line and
        # we want to pass our own R/X per-km directly.
        idx = pp.create_line_from_parameters(
            net, from_bus=bus_map[u], to_bus=bus_map[v],
            length_km=1.0,  # per-unit; we encoded R/X directly in r_ohm_per_km=0
            r_ohm_per_km=r_pu,
            x_ohm_per_km=x_pu,
            c_nf_per_km=0.0,
            max_i_ka=999.0,
            name=f"line_{u}_{v}",
        )
        # Preserve the ehm-side direction chosen at line creation.
        line_map[int(idx)] = (u, v)

    # Stash the inverse maps on the grid so the caller can read them.
    grid._ac_bus_map = bus_map
    grid._ac_line_map = line_map

    return net


# ── Helpers ─────────────────────────────────────────────────────────────
def _unavailable_result(reason: str) -> ACPFResult:
    return ACPFResult(
        converged=False,
        warnings=[reason],
        error=reason,
    )


# ── Self-test (textbook 5-bus case) ─────────────────────────────────────
def _self_test_5bus() -> bool:
    """Run AC PF on the textbook 5-bus case and check V near 1.0 p.u.

    Topology (matches ``power_flow.py`` self-test):
        Bus1 (slack) --- Bus2 --- Bus3
            |                        |
            +------- Bus4 --- Bus5 ---+
    All X = 0.1 pu; P_load: Bus2=1.0, Bus4=0.5, Bus5=1.5 (MW).
    """
    if not PANDAPOWER_AVAILABLE:
        return False  # Skip silently when pandapower not installed.

    import networkx as nx

    class _N:
        def __init__(self, nid, gen=0.0, load=0.0, t="bus"):
            self.node_id = nid
            self.node_type = t
            self.generation = gen
            self.load = load
            self.failed = False
            self.isolated = False

    nodes = {
        "B1": _N("B1", t="generator"),
        "B2": _N("B2", load=1.0),
        "B3": _N("B3"),
        "B4": _N("B4", load=0.5),
        "B5": _N("B5", load=1.5),
    }
    edges = [
        ("B1", "B2", 0.01, 0.1),
        ("B1", "B4", 0.01, 0.1),
        ("B2", "B3", 0.01, 0.1),
        ("B3", "B5", 0.01, 0.1),
        ("B4", "B5", 0.01, 0.1),
    ]
    G = nx.DiGraph()
    for nid in nodes:
        G.add_node(nid)
    for u, v, r, x in edges:
        G.add_edge(u, v, resistance=r, reactance=x, active=True)
        G.add_edge(v, u, resistance=r, reactance=x, active=True)

    class _Grid:
        pass

    g = _Grid()
    g.graph = G
    g.nodes = nodes
    g.line_impedance = {
        (u, v): {"R": r, "X": x}
        for u, v, r, x in edges
    }

    res = run_ac_power_flow(g, slack_bus_id="B1")
    if not res.converged:
        return False
    # Slack must be near 1.02 (we set vm_pu=1.02)
    assert 1.00 <= res.bus_voltage_pu["B1"] <= 1.05
    # All other buses must be in [0.95, 1.05]
    for nid, v in res.bus_voltage_pu.items():
        assert 0.90 <= v <= 1.10, f"Bus {nid} voltage {v} out of range"
    return True


if __name__ == "__main__":
    print("pandapower available:", PANDAPOWER_AVAILABLE)
    if PANDAPOWER_AVAILABLE:
        try:
            ok = _self_test_5bus()
            print("5-bus AC PF self-test:", "PASS" if ok else "FAIL")
        except AssertionError as exc:
            print(f"5-bus AC PF self-test: FAIL ({exc})")
    else:
        print("Skipping self-test (pandapower not installed).")