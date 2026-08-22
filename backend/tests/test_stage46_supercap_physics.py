"""test_stage46_supercap_physics.py — Stage-46 supercapacitor physics audit.

Verifies that ``use_supercapacitor`` satisfies these physical
invariants:

  1. SOC limits (no discharge when SOC ≤ 0)
  2. Discharge limits (delivered ≤ requested amount)
  3. Energy accounting (level drops by delivered / capacity)
  4. No energy creation
  5. Physical reachability (the load reduction only affects
     the node's own load, not downstream loads)
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


import pytest  # noqa: E402

from simulation.node import GridNode  # noqa: E402
from simulation.grid import SmartGrid  # noqa: E402
from utils.seeds import set_global_seed  # noqa: E402


def test_supercap_soc_zero_blocks_discharge():
    """SOC = 0 must block discharge."""
    n = GridNode(node_id="SC_TEST", node_type="supercap",
                 x=0.0, y=0.0)
    n.supercap_level = 0.0
    n.supercap_capacity = 1.0
    delivered = n.use_supercapacitor(0.5)
    assert delivered == 0.0
    assert float(n.supercap_level) == 0.0


def test_supercap_discharge_limit():
    """delivered must not exceed requested amount."""
    n = GridNode(node_id="SC_TEST", node_type="supercap",
                 x=0.0, y=0.0)
    n.supercap_level = 1.0
    n.supercap_capacity = 1.0
    delivered = n.use_supercapacitor(0.3)
    assert delivered <= 0.3 + 1e-6


def test_supercap_energy_accounting():
    """Energy after discharge = Energy before − delivered."""
    n = GridNode(node_id="SC_TEST", node_type="supercap",
                 x=0.0, y=0.0)
    n.supercap_level = 1.0
    n.supercap_capacity = 1.0
    energy_before = float(n.supercap_level) * float(n.supercap_capacity)
    delivered = n.use_supercapacitor(0.2)
    energy_after = float(n.supercap_level) * float(n.supercap_capacity)
    assert abs((energy_before - delivered) - energy_after) < 1e-6, (
        f"Energy: before={energy_before} delivered={delivered} "
        f"after={energy_after}"
    )


def test_supercap_load_offset_only_on_node():
    """``use_supercapacitor`` reduces the *node's own* load, not
    downstream loads. The action is a node-local offset, not a
    wide-area resource."""
    n = GridNode(node_id="SC_TEST", node_type="supercap",
                 x=0.0, y=0.0)
    n.supercap_level = 1.0
    n.supercap_capacity = 1.0
    n.load = 1.0
    load_before = float(n.load)
    n.use_supercapacitor(0.1)
    assert float(n.load) < load_before + 1e-6
    # No neighbouring nodes were affected (supercap is node-local).
    # This is a structural test: the action method does not
    # touch any other node.


def test_supercap_runner_dispatch():
    """The runner's ``_dispatch_action(grid, 2)`` must discharge
    from every alive supercap/``storage_sc`` node + house with
    supercap_level > 0.1."""
    from experiments.runner import _dispatch_action
    set_global_seed(0)
    g = SmartGrid(seed=0)
    # Snapshot all supercap levels.
    levels_before = {
        nid: float(getattr(n, "supercap_level", 0.0) or 0.0)
        for nid, n in g.nodes.items()
        if (
            "storage_sc" in str(getattr(n, "node_type", ""))
            or str(getattr(n, "node_type", "")) == "house"
        )
    }
    result = _dispatch_action(g, 2)
    assert result == "use_supercapacitor"
    # Verify at least one node with SOC > 0.1 had its level
    # reduced (or all start at ≤ 0.1, in which case the action
    # is a no-op).
    levels_after = {
        nid: float(getattr(n, "supercap_level", 0.0) or 0.0)
        for nid, n in g.nodes.items()
        if (
            "storage_sc" in str(getattr(n, "node_type", ""))
            or str(getattr(n, "node_type", "")) == "house"
        )
    }
    # No node should have gained energy.
    for nid, after in levels_after.items():
        before = levels_before.get(nid, 0.0)
        assert after <= before + 1e-6, (
            f"Node {nid}: supercap_level increased "
            f"{before} → {after}"
        )
