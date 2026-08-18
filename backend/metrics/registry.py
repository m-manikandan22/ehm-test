"""
registry.py — decorator-based metric registry.

Why
---
A publication-grade platform registers all metrics in one place
and exposes them through a ``compute_all(payload)`` entry point.
This decouples the API from the implementation: route code asks
for ``compute_all(state_dict)`` and the registry runs every
registered metric without conditional plumbing.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List


class _Registry:
    def __init__(self) -> None:
        self._metrics: Dict[str, Callable[[Dict[str, Any]], float]] = {}

    def register(self, name: str, fn: Callable[[Dict[str, Any]], float]) -> None:
        self._metrics[name] = fn

    def has(self, name: str) -> bool:
        return name in self._metrics

    def names(self) -> List[str]:
        return sorted(self._metrics.keys())

    def run_one(self, name: str, payload: Dict[str, Any]) -> float:
        if name not in self._metrics:
            raise KeyError(f"unknown metric {name!r}")
        return float(self._metrics[name](payload))

    def run_all(self, payload: Dict[str, Any]) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for name, fn in self._metrics.items():
            try:
                out[name] = float(fn(payload))
            except Exception:  # noqa: BLE001 — defensive
                out[name] = float("nan")
        return out

    def clear(self) -> None:
        self._metrics.clear()


registry = _Registry()


def metric(name: str) -> Callable[[Callable[[Dict[str, Any]], float]], Callable[[Dict[str, Any]], float]]:
    """Decorator — register ``fn`` as metric ``name``.

    Usage::

        @metric("saifi.all")
        def saifi_all(payload):
            return saifi(payload["customers"], payload["interruptions"])
    """
    def deco(fn: Callable[[Dict[str, Any]], float]) -> Callable[[Dict[str, Any]], float]:
        registry.register(name, fn)
        return fn
    return deco


def compute_all(payload: Dict[str, Any]) -> Dict[str, float]:
    return registry.run_all(payload)