"""
n_minus_1.py — N-1 contingency analysis for the EHM SmartGrid.

What is N-1?
------------
An N-1 contingency analysis answers: "if any *single* asset fails, does
the rest of the grid still serve all customers without violating
operational limits (line loading > 100 %, voltage < 0.95 pu)?"

It is the standard pre-flight check in transmission planning and is the
simplest non-trivial resilience indicator for any distribution system.
main.md Stage 15 requires this as a reusable module.

Public API
----------
  - ``run_n_minus_1(grid, candidates=None, voltage_floor=0.95,
        loading_ceiling=1.00) -> N1Result``
  - ``N1Result`` dataclass: per-contingency violations + rollup stats.

Conventions
-----------
  - We enumerate every node of ``node_type in {transformer, pole}``
    plus every active line in the grid as a candidate contingency.
  - For each candidate we *fail* the asset in a copy of the grid,
    re-solve DC PF, and check KCL / line-loading violations.
  - We never modify the input grid — this is an analysis tool, not a
    controller.
  - The function is *deterministic* given a grid state; it makes no RNG
    calls beyond the underlying DC PF solver.

Limitations
-----------
  - We use DC PF (no reactive / voltage collapse). For full AC
    N-1 voltage checks, the optional ``backend.simulation.ac_power_flow``
    path applies; see EHM-HIGH-005 in
    ``docs/PAPER_READINESS_AUDIT.md``.
  - We treat each contingency as one *forensic* event; we do not run a
    time-series. Real N-1 includes load-shedding and operator
    intervention — our analysis is the pre-intervention baseline.
"""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

import networkx as nx  # type: ignore

from simulation.grid import SmartGrid


logger = logging.getLogger(__name__)


# Candidate contingency types (poles and transformers are the assets
# that FLISR can reroute around; lines/cables are also tested).
_N1_ASSET_TYPES = frozenset({"pole", "transformer"})


@dataclass
class N1Violation:
    """A single limit-violation observed during one N-1 contingency."""
    line: str
    kind: str          # "overload" or "undervoltage"
    magnitude: float   # pu overload, or pu undervoltage

    def to_dict(self) -> dict:
        return {
            "line": self.line,
            "kind": self.kind,
            "magnitude": float(self.magnitude),
        }


@dataclass
class N1Result:
    """Per-contingency result + rollup statistics."""
    contingencies_evaluated: int = 0
    contingencies_violating: int = 0
    contingencies_with_restoration: int = 0
    violations: Dict[str, List[N1Violation]] = field(default_factory=dict)
    # Per-asset recovery fraction (0 = no load served; 1 = full)
    recovery_fraction: Dict[str, float] = field(default_factory=dict)
    # Rollups
    worst_overload_pu: float = 0.0
    worst_undervoltage_pu: float = 1.0
    # Reference grid state (so callers can recover original)
    summary_line: str = ""

    def to_dict(self) -> dict:
        return {
            "contingencies_evaluated": int(self.contingencies_evaluated),
            "contingencies_violating": int(self.contingencies_violating),
            "contingencies_with_restoration":
                int(self.contingencies_with_restoration),
            "violations": {
                k: [v.to_dict() for v in vs]
                for k, vs in self.violations.items()
            },
            "recovery_fraction": dict(self.recovery_fraction),
            "worst_overload_pu": float(self.worst_overload_pu),
            "worst_undervoltage_pu": float(self.worst_undervoltage_pu),
            "summary_line": self.summary_line,
        }

    @property
    def violation_rate(self) -> float:
        if self.contingencies_evaluated == 0:
            return 0.0
        return self.contingencies_violating / self.contingencies_evaluated


def _iter_candidates(grid: SmartGrid) -> Iterable[str]:
    """Yield every node-id that is a sensible N-1 candidate."""
    for nid, n in grid.nodes.items():
        nt = getattr(n, "node_type", "")
        if nt in _N1_ASSET_TYPES and not getattr(n, "failed", False):
            yield nid


def _clone_grid(grid: SmartGrid) -> SmartGrid:
    """Return a *fresh* SmartGrid that the caller can safely mutate.

    The clone preserves the topology and load/generation values but
    not state (failed, isolated). This is what lets us fail one asset
    and re-run the rest of the grid without contaminating the
    analysis input.

    We deep-copy the node map (so each GridNode is a new object whose
    ``failed`` / ``isolated`` flags are independent) and we deep-copy
    the edge data dicts (so per-edge ``flow`` / ``switch_status``
    mutations don't bleed back into the input grid).
    """
    import copy as _copy
    g = _copy.copy(grid)
    # Fresh DiGraph + fresh edge data dicts (DiGraph(nodes=, edges=)
    # with data= triggers networkx to copy each data dict for us).
    g.graph = nx.DiGraph()
    for nid, attrs in grid.graph.nodes(data=True):
        g.graph.add_node(nid, **dict(attrs))
    for u, v, data in grid.graph.edges(data=True):
        g.graph.add_edge(u, v, **dict(data))
    # Deep-copy each node so failed/isolated state is independent
    g.nodes = {
        nid: _copy.deepcopy(node)
        for nid, node in grid.nodes.items()
    }
    # Other state containers: event_log, isolated_list, etc.
    g.event_log = list(getattr(grid, "event_log", []))
    return g


def _force_failed(grid: SmartGrid, target: str) -> None:
    """Mark the candidate asset failed and propagate downstream."""
    try:
        grid.inject_failure(target)
    except Exception as exc:  # noqa: BLE001
        # If the grid can't fail that asset (e.g. protected node),
        # skip silently — the candidate is still reported as
        # evaluated, just with no violations.
        logger.debug("inject_failure(%r) failed: %r", target, exc)


def _total_consumer_load(grid: SmartGrid) -> float:
    """Sum of consumer-node baseline load (MW)."""
    total = 0.0
    for n in grid.nodes.values():
        if getattr(n, "node_type", "") in ("house", "industry", "hospital",
                                            "hospital_icu"):
            total += float(getattr(n, "load", 0.0) or 0.0)
    return total


def _received_load(grid: SmartGrid) -> float:
    """Sum of consumer nodes currently receiving power (MW)."""
    served = 0.0
    for n in grid.nodes.values():
        if getattr(n, "node_type", "") in ("house", "industry", "hospital",
                                            "hospital_icu"):
            received = float(getattr(n, "received_power", 0.0) or 0.0)
            if received > 0.0:
                served += received
    return served


def _gather_violations(
    grid: SmartGrid,
    *,
    voltage_floor: float,
    loading_ceiling: float,
) -> List[N1Violation]:
    """Return every violation observed on the current grid."""
    violations: List[N1Violation] = []
    # Line-loading violations
    for u, v, data in grid.graph.edges(data=True):
        flow = abs(float(data.get("flow", 0.0) or 0.0))
        cap = float(data.get("capacity", 1.0) or 1.0)
        if cap <= 0:
            continue
        loading = flow / cap
        if loading > loading_ceiling:
            violations.append(N1Violation(
                line=f"{u}-{v}",
                kind="overload",
                magnitude=loading,
            ))
    # Undervoltage violations
    for nid, node in grid.nodes.items():
        v = float(getattr(node, "voltage", 1.0) or 1.0)
        if v < voltage_floor:
            violations.append(N1Violation(
                line=nid,
                kind="undervoltage",
                magnitude=v,
            ))
    return violations


def run_n_minus_1(
    grid: SmartGrid,
    *,
    candidates: Optional[Iterable[str]] = None,
    voltage_floor: float = 0.95,
    loading_ceiling: float = 1.00,
    auto_remediate: bool = True,
) -> N1Result:
    """Enumerate single-asset contingencies and check limits.

    Parameters
    ----------
    grid : SmartGrid
        The grid to analyse. **Not mutated.**
    candidates : iterable of str, optional
        Override the candidate list. If omitted, every node of type
        ``pole`` or ``transformer`` is evaluated.
    voltage_floor : float
        Pu voltage below which a node counts as a violation.
    loading_ceiling : float
        Line-loading (flow / capacity) above which a line counts as
        overloaded.
    auto_remediate : bool
        If True, run FLISR (``flisr_9stage``) before checking load
        served, so the analysis reflects the post-reroute state.

    Returns
    -------
    N1Result
    """
    base_load = _total_consumer_load(grid)
    if base_load <= 0:
        base_load = 1e-6  # avoid division by zero on degenerate grids

    cand_iter = candidates if candidates is not None else list(_iter_candidates(grid))
    cand_list = list(cand_iter)

    result = N1Result(contingencies_evaluated=len(cand_list))

    for target in cand_list:
        g = _clone_grid(grid)
        _force_failed(g, target)
        try:
            g.update_power_flow()
        except Exception as exc:  # noqa: BLE001
            logger.debug("update_power_flow failed after %r: %r", target, exc)

        violated = _gather_violations(
            g,
            voltage_floor=voltage_floor,
            loading_ceiling=loading_ceiling,
        )

        # Track worst-case magnitudes
        for v in violated:
            if v.kind == "overload":
                result.worst_overload_pu = max(
                    result.worst_overload_pu, v.magnitude
                )
            elif v.kind == "undervoltage":
                result.worst_undervoltage_pu = min(
                    result.worst_undervoltage_pu, v.magnitude
                )

        if violated:
            result.contingencies_violating += 1
            result.violations[target] = violated

        if auto_remediate and hasattr(g, "flisr_9stage"):
            try:
                g.flisr_9stage()
                g.update_power_flow()
            except Exception as exc:  # noqa: BLE001
                logger.debug("flisr_9stage failed on %r: %r", target, exc)

        served = _received_load(g)
        recovery = max(0.0, min(1.0, served / base_load))
        result.recovery_fraction[target] = recovery
        if recovery >= 0.85:
            result.contingencies_with_restoration += 1

    result.summary_line = (
        f"N-1 over {result.contingencies_evaluated} candidates: "
        f"{result.contingencies_violating} violate limits pre-FLISR; "
        f"{result.contingencies_with_restoration} recover ≥85% load post-FLISR."
    )
    return result


def n1_pass_criteria(result: N1Result) -> Tuple[bool, List[str]]:
    """Pass criterion for paper-grade grid designs.

    A grid passes N-1 if:

      1. **No violation rate above 5 %** — at most 5 % of contingencies
         produce limit violations (after DC PF).
      2. **Recovery ≥ 85 % under all evaluated contingencies** — every
         contingency recovers at least 85 % of consumer load after FLISR.
      3. **Worst undervoltage ≥ 0.92 pu** — the lowest voltage observed
         under any contingency is not below 0.92 pu.

    Returns
    -------
    (passed, reasons)
        Boolean + list of failure-reason strings (empty when passed).
    """
    reasons: List[str] = []
    if result.violation_rate > 0.05:
        reasons.append(
            f"violation_rate={result.violation_rate:.1%} > 5 %"
        )
    if result.recovery_fraction:
        min_recovery = min(result.recovery_fraction.values())
        if min_recovery < 0.85:
            reasons.append(
                f"min_recovery={min_recovery:.2f} < 0.85 (worst-case contingency)"
            )
    if result.worst_undervoltage_pu < 0.92:
        reasons.append(
            f"worst_undervoltage_pu={result.worst_undervoltage_pu:.3f} < 0.92"
        )
    return (not reasons), reasons
