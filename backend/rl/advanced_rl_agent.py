"""
advanced_rl_agent.py — Reward-guided decision agent with action masking
and XAI hooks.

Why
---
This module is **not** a DQN. It picks the legal action whose reward
breakdown is highest under the configured ``RewardComposer``. The
legacy DQN (``DQNAgent`` in ``models/rl_agent.py``) and this
``RewardGuidedDecisionAgent`` are deliberately separate:

  - ``DQNAgent``                       — true neural Q-learning,
                                          replay buffer, target
                                          network, gradient updates.
  - ``RewardGuidedDecisionAgent``      — ``argmax`` over the
                                          ``RewardComposer`` components.

Naming
------
The legacy name ``AdvancedDQNAgent`` was misleading: this class never
trained a Q-network. It is now exported as
``RewardGuidedDecisionAgent`` (and the old name is preserved as an
alias for backward compatibility — old imports keep working). New code
should use the new name.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from rl.action_mask import ActionMask, AdvancedAction
from rl.explainer import RLExplainer, XAIReport
from rl.rewards import RewardComposer
from rl.state_builder import StateBuilder


ACTION_NAMES: Dict[int, str] = {
    int(AdvancedAction.OPEN_SWITCH): "open_switch",
    int(AdvancedAction.CLOSE_SWITCH): "close_switch",
    int(AdvancedAction.RECONFIGURE_FEEDER): "reconfigure_feeder",
    int(AdvancedAction.DISCONNECT_LOAD): "disconnect_load",
    int(AdvancedAction.CHARGE_BATTERY): "charge_battery",
    int(AdvancedAction.DISCHARGE_BATTERY): "discharge_battery",
    int(AdvancedAction.CREATE_ISLAND): "create_island",
    int(AdvancedAction.MERGE_ISLAND): "merge_island",
    int(AdvancedAction.NO_OP): "no_op",
}


@dataclass
class RewardGuidedDecisionAgent:
    """Lightweight decision agent — uses reward components as a Q proxy.

    This class **does not** train a neural network. It scores every
    legal action by computing the ``RewardComposer`` breakdown as if
    the action had been taken, then returns the action with the
    highest total reward. The XAI panel can then attribute the
    decision to specific reward components.

    For a genuine trained DQN, see ``models.rl_agent.DQNAgent``.
    """

    composer: RewardComposer = field(default_factory=RewardComposer)
    builder: StateBuilder = field(default_factory=StateBuilder)
    explainer: RLExplainer = field(default_factory=RLExplainer)
    last_xai: Optional[XAIReport] = None

    # ------------------------------------------------------------------
    # Action selection
    # ------------------------------------------------------------------

    def select_action(
        self,
        grid: Any,
        state: Dict[str, Any],
        next_state: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Pick the best legal action under the current mask.

        Algorithm:
          1. Build the legal-action mask from the current grid + state.
          2. For each legal action, ask the reward composer what the
             total reward would be if we took it. (Stand-in for a Q
             function. We do *not* train a neural network here.)
          3. Return the legal action with the highest reward.
        """
        mask = ActionMask.from_grid(grid, state=state)
        scores: List[float] = []
        action_payloads: List[Dict[str, Any]] = []
        for a in AdvancedAction:
            if not mask.allows(a):
                scores.append(float("-inf"))
                action_payloads.append({"name": "illegal"})
                continue
            payload = {"name": ACTION_NAMES[int(a)], "action_id": int(a)}
            action_payloads.append(payload)
            if next_state is None:
                # No forward step yet; fall back to a static prior that
                # prefers no-op when nothing else is legal.
                scores.append(0.0)
                continue
            bd = self.composer.compute(state, payload, next_state)
            scores.append(bd.total)

        # Best legal action.
        best_idx = max(range(len(scores)), key=lambda i: scores[i])
        # Compute XAI for the chosen action.
        features = self.builder.build_features(grid)
        self.last_xai = self.explainer.explain(
            features=features,
            q_values=scores,
            chosen_action=best_idx,
            action_names=[ACTION_NAMES[int(a)] for a in AdvancedAction],
        )
        return int(best_idx)

    # ------------------------------------------------------------------

    def explain_last(self) -> Optional[XAIReport]:
        return self.last_xai


# Backward-compat alias. The class was previously called
# ``AdvancedDQNAgent``; that name was misleading because the class
# never trained a Q-network. New code must use
# ``RewardGuidedDecisionAgent``; this alias exists so old imports
# (``from rl.advanced_rl_agent import AdvancedDQNAgent``) keep working.
AdvancedDQNAgent = RewardGuidedDecisionAgent