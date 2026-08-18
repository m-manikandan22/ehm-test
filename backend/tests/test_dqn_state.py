"""
test_dqn_state.py — Validation of the DQN state vector.

Critical Item 2: the historical implementation referenced node names
("G0", "G1", "G2", "S0"…"S5") that do not exist in the grid; the
agent was effectively training on zeros. This test prevents regressions.
"""
from simulation.grid import SmartGrid
from models.rl_agent import STATE_DIM, DQNAgent


def test_rl_state_shape_matches_dqn_input():
    g = SmartGrid()
    rl = g.get_rl_state()
    assert len(rl) == STATE_DIM, f"state length {len(rl)} != STATE_DIM {STATE_DIM}"


def test_rl_state_uses_live_node_names():
    """The historical bug was passing hard-coded 'G0/G1/G2/S0-S5' that
    didn't exist; this asserts that the priority nodes referenced are
    actually present and live in the grid."""
    g = SmartGrid()
    expected_priority = [
        "GEN_SOLAR", "GEN_WIND", "GEN_NUCLEAR", "GEN_COAL", "GEN_GAS",
        "S_MAIN",
        "STORAGE_BAT", "STORAGE_SC",
        "T_A", "T_B", "T_C",
        "HOSP", "IND0",
    ]
    for nid in expected_priority:
        assert nid in g.nodes, f"priority node {nid} missing"


def test_rl_state_has_signal_not_zeros():
    g = SmartGrid()
    rl = g.get_rl_state()
    non_zero_count = sum(1 for x in rl if abs(x) > 1e-9)
    # Only the 7 globals + a handful of node features may legitimately be
    # zero at midnight; we expect a clear majority of entries to be live.
    assert non_zero_count > len(rl) * 0.5, (
        f"Too many zero entries ({non_zero_count}/{len(rl)}) — DQN likely "
        "training on sparse zeros."
    )


def test_custom_target_node_ids():
    g = SmartGrid()
    rl = g.get_rl_state(target_node_ids=["GEN_NUCLEAR", "HOSP"])
    # 2 nodes × 5 + 7 = 17
    assert len(rl) == 17


def test_dqn_agent_accepts_new_state():
    g = SmartGrid()
    state = g.get_rl_state()
    agent = DQNAgent()
    action = agent.select_action(state, predicted_load=0.5, grid_state=g.get_state())
    assert 0 <= action["action_id"] <= 4
    assert "confidence" in action
