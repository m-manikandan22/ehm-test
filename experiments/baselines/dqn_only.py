"""dqn_only.py — DQN baseline with LSTM/Twin/Reward-shaping assistance
intentionally *disabled*.

Used as the "DQN-core" arm in the ablation study so we can attribute
gains to LSTM forecasting, Twin aging, and Predictive FLISR separately.
"""
from __future__ import annotations

from typing import Any, Optional


class DQNOnlyBaseline:
    """Wraps the production ``DQNAgent`` with the helpers stripped out.

    We delegate the heavy lifting to the real model so this baseline is
    comparable to a production agent. ``enable_*`` flags let the
    experiment harness toggle assistance on/off externally.
    """

    def __init__(self, state_dim: int = 72):
        try:
            from models.rl_agent import DQNAgent
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "DQNAgent import failed; ensure torch + the EHM RL "
                "module are installed."
            ) from exc
        self.agent = DQNAgent(state_dim=state_dim)
        self.enable_lstm = False
        self.enable_twin = False

    def choose_action(self, state, grid_state: Optional[dict] = None) -> int:
        choice = self.agent.select_action(
            state,
            predicted_load=(0.0 if not self.enable_lstm else 0.5),
            grid_state=grid_state,
        )
        return int(choice.get("action_id", 0))

    def reset(self) -> None:
        # No persistent state to clear; the underlying agent is
        # re-instantiated per-run by the experiment harness.
        pass
