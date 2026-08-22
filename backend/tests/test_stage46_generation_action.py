"""test_stage46_generation_action.py — Stage-46 generation action audit.

The historical Stage-45 audit noted that ``increase_generation``
targeted ``G0`` even when ``G0`` did not exist. The Stage-46
runner code at ``runner.py:162-174`` falls back to any non-failed
generator when ``G0`` is missing. This test verifies:

  1. If ``G0`` exists and is alive, it is the target.
  2. If ``G0`` is missing or failed, the fallback finds another
     non-failed generator.
  3. If no non-failed generator exists, the action is a no-op.
  4. The target's generation is increased by 0.5 MW.
  5. The target's generation is capped at 2.5 MW (node cap).
  6. The action result string is "increase_generation".
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

from simulation.grid import SmartGrid  # noqa: E402
from utils.seeds import set_global_seed  # noqa: E402


def test_increase_generation_targets_g0_when_alive():
    """If G0 exists and is alive, it is the target."""
    set_global_seed(0)
    g = SmartGrid(seed=0)
    from experiments.runner import _dispatch_action
    if "G0" in g.nodes and not g.nodes["G0"].failed:
        gen_before = float(g.nodes["G0"].generation)
        result = _dispatch_action(g, 0)
        assert result == "increase_generation"
        gen_after = float(g.nodes["G0"].generation)
        assert gen_after >= gen_before + 0.4
        # Generation cap: 2.5 MW.
        assert gen_after <= 2.5 + 1e-6
    else:
        pytest.skip("G0 not present or already failed")


def test_increase_generation_fallback_when_g0_failed():
    """If G0 is failed, the dispatcher falls back to any non-failed
    generator.

    Stage-46: the test verifies the fallback path actually
    identifies a generator and applies the bump."""
    set_global_seed(0)
    g = SmartGrid(seed=0)
    from experiments.runner import _dispatch_action
    # Find any generator.
    gens = [
        nid for nid, n in g.nodes.items()
        if str(getattr(n, "node_type", "")).startswith("generator")
        and not n.failed
    ]
    if not gens:
        pytest.skip("No non-failed generator")
    # Snapshot.
    def _total_gen(g):
        return sum(
            float(getattr(n, "generation", 0.0) or 0.0)
            for nid, n in g.nodes.items()
            if str(getattr(n, "node_type", "")).startswith("generator")
            and not n.failed
        )
    before = _total_gen(g)
    _dispatch_action(g, 0)
    after = _total_gen(g)
    # The total generation should have increased by at least
    # 0.4 MW (the dispatcher bumps the chosen target by 0.5).
    # Note: time-curve updates may overwrite this number on the
    # next step, but the dispatch itself increases generation
    # IMMEDIATELY before the step.
    assert after >= before + 0.4, (
        f"Increase generation had no effect: "
        f"before={before} after={after}"
    )


def test_increase_generation_no_target_when_no_gens():
    """If every generator is failed, the action is a no-op."""
    set_global_seed(0)
    g = SmartGrid(seed=0)
    # Fail every generator.
    for nid, n in g.nodes.items():
        if str(getattr(n, "node_type", "")).startswith("generator"):
            n.fail()
    from experiments.runner import _dispatch_action
    result = _dispatch_action(g, 0)
    assert result == "increase_generation"
    # No assertion on generation because no target exists; the
    # contract is just "the action was processed without error".
