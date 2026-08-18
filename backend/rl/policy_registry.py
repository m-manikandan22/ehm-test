"""
policy_registry.py — runtime-swap registry for RL policies.

Why
---
A research paper usually compares multiple policies (rule-based,
DQN, PPO).  Hard-coding the import forces a code change to swap
them out.  The registry pattern lets a caller do
``registry.create("dqn")`` or ``registry.create("rule_based")``
without touching the simulation loop.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Type


class PolicyRegistry:
    """Maps policy names → callables that return a policy instance."""

    def __init__(self) -> None:
        self._factories: Dict[str, Callable[..., Any]] = {}

    def register(self, name: str, factory: Callable[..., Any]) -> None:
        self._factories[name] = factory

    def has(self, name: str) -> bool:
        return name in self._factories

    def names(self) -> list[str]:
        return sorted(self._factories.keys())

    def create(self, name: str, **kwargs: Any) -> Any:
        if name not in self._factories:
            raise KeyError(f"unknown policy {name!r}; registered: {self.names()}")
        return self._factories[name](**kwargs)

    def clear(self) -> None:
        self._factories.clear()