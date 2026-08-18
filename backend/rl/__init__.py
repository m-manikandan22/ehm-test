"""rl — Advanced reinforcement-learning + XAI components (M3).

The legacy DQN remains in ``models/rl_agent.py`` and is unchanged.
"""
from rl.rewards import RewardComposer, RewardBreakdown
from rl.action_mask import ActionMask
from rl.state_builder import StateBuilder
from rl.explainer import RLExplainer, XAIReport
from rl.policy_registry import PolicyRegistry
from rl.advanced_rl_agent import AdvancedDQNAgent

__all__ = [
    "RewardComposer",
    "RewardBreakdown",
    "ActionMask",
    "StateBuilder",
    "RLExplainer",
    "XAIReport",
    "PolicyRegistry",
    "AdvancedDQNAgent",
]