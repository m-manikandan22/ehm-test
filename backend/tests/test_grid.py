"""
test_grid.py — pytest conversion of the legacy smoke tests.

Covers:
  - SmartGrid construction integrity (49 nodes, online = total)
  - DC power flow integration (KCL within tolerance)
  - get_dc_state() exposes the DC result
  - get_rl_state() returns correct length and uses real node names
"""
from simulation.grid import SmartGrid


def test_build_and_clean_state():
    g = SmartGrid()
    assert len(g.nodes) == 49
    failed = [nid for nid, n in g.nodes.items() if n.failed]
    isolated = [nid for nid, n in g.nodes.items() if n.isolated]
    assert not failed, f"unexpected failed nodes at init: {failed}"
    assert not isolated, f"unexpected isolated nodes at init: {isolated}"


def test_dc_power_flow_converges_with_kcl():
    g = SmartGrid()
    res = g.get_dc_state()
    assert res, "dc_state should not be empty after construction"
    assert res["converged"], f"DC PF did not converge: {res.get('warnings')}"
    assert res["kcl_residual_max"] < 1e-6, (
        f"KCL residual too high: {res['kcl_residual_max']:.2e}"
    )
    assert res["bus_count"] == 49
    # 49 nodes, slack bus removed → 48 angles
    assert len(res["bus_angle_deg"]) == 49


def test_rl_state_length_and_real_nodes():
    g = SmartGrid()
    rl = g.get_rl_state()
    # 13 priority nodes × 5 features + 7 globals = 72
    assert len(rl) == 72
    # The historical bug: get_rl_state hard-coded G0/G1/G2/S0-S5 which
    # don't exist; those would have been all-zero. Now they should be alive.
    assert g.nodes["GEN_NUCLEAR"].generation > 0.0
    assert g.nodes["S_MAIN"].voltage > 0.0
    # The first 5 entries are GEN_SOLAR features
    assert rl[0] != 0.0 or rl[1] != 0.0, (
        "First two RL entries should reference real GEN_SOLAR values, not zeros"
    )
