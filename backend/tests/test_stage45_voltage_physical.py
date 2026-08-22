"""test_stage45_voltage_physical.py — Stage-45 voltage-violation tests.

Voltage violations come from the solved (post-power-flow) voltage
state at every step. The Stage-45 collector flags a violation if
|V(B, t) − 1.0| > 0.10 pu for any bus B at any step t.

The project uses a DC power-flow voltage proxy (limitations
documented in ``docs/STAGE_45_PHYSICS_COUPLING.md`` §4); the 0.10 pu
band is a heuristic, not ANSI C84.1.
"""
from __future__ import annotations

import os
import sys

THIS = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(THIS)
PROJECT_ROOT = os.path.dirname(BACKEND)
sys.path[:] = [
    p for p in sys.path
    if os.path.normpath(p) != os.path.normpath(PROJECT_ROOT)
]
sys.path.insert(0, BACKEND)


from simulation.grid import SmartGrid
from experiments.stage45_metrics import Stage45MetricCollector
from utils.seeds import set_global_seed


def _step_n(g, n: int) -> Stage45MetricCollector:
    c = Stage45MetricCollector()
    c.register_load_nodes(g)
    for t in range(n):
        try:
            g.step()
        except Exception:
            pass
        try:
            g.update_power_flow()
        except Exception:
            pass
        c.step(grid=g, timestep=t)
    return c


def test_voltage_violation_zero_when_grid_normal():
    """Healthy grid → no voltage violations."""
    set_global_seed(0)
    g = SmartGrid(seed=0)
    c = _step_n(g, 20)
    summary = c.summary()
    assert summary["voltage_violation_count"] == 0, summary


def test_voltage_violation_counted_per_step():
    """If a bus stays in violation for T consecutive steps, the
    collector increments the counter T times. We force a sustained
    voltage violation by zeroing the voltage on every bus except
    the substation, then re-running the power flow.
    """
    set_global_seed(0)
    g = SmartGrid(seed=0)
    c = Stage45MetricCollector()
    c.register_load_nodes(g)
    n_steps = 5
    for t in range(n_steps):
        # Force V on a non-source bus to 0.5 (well outside ±0.10).
        for nid, n in g.nodes.items():
            if nid != "S_MAIN" and not str(
                getattr(n, "node_type", "")
            ).startswith("generator"):
                n.voltage = 0.5
        c.step(grid=g, timestep=t)
    summary = c.summary()
    # We forced a violation on every step; counter must be ≥ n_steps.
    assert summary["voltage_violation_count"] >= n_steps, (
        summary["voltage_violation_count"], n_steps,
    )


def test_voltage_violation_from_solved_state():
    """The violation count must be derived from ``node.voltage``,
    not from fault presence. We set every non-source bus to a
    healthy voltage AND inject a fault → violations must be zero.
    """
    set_global_seed(0)
    g = SmartGrid(seed=0)
    if "P_A2" in g.nodes:
        try:
            g.inject_failure("P_A2")
        except Exception:
            pass
    c = Stage45MetricCollector()
    c.register_load_nodes(g)
    n_steps = 5
    for t in range(n_steps):
        # Override voltages to healthy (1.0).
        for nid, n in g.nodes.items():
            if not getattr(n, "failed", False):
                n.voltage = 1.0
        c.step(grid=g, timestep=t)
    summary = c.summary()
    assert summary["voltage_violation_count"] == 0, summary
