"""
tracing.py — lightweight step-timing histogram.

Why
---
A FastAPI microservice should expose a "where did the time go" view
without depending on OpenTelemetry.  This module records per-step
durations in a rolling histogram and exposes them at
``/metrics/internal/trace``.

Design points:
  - No external deps (Prometheus client, etc.).
  - Thread-safe via a single ``threading.Lock``.
  - Cheap: a dict of deques of floats.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Dict, Optional


class StepTimer:
    """Record per-step durations for a single named phase."""

    def __init__(self, name: str, maxlen: int = 1024) -> None:
        self.name = name
        self._samples: Deque[float] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def record(self, duration_ms: float) -> None:
        with self._lock:
            self._samples.append(float(duration_ms))

    def stats(self) -> Dict[str, float]:
        with self._lock:
            if not self._samples:
                return {"name": self.name, "count": 0,
                        "mean_ms": 0.0, "max_ms": 0.0, "min_ms": 0.0}
            samples = list(self._samples)
        return {
            "name": self.name,
            "count": len(samples),
            "mean_ms": sum(samples) / len(samples),
            "max_ms": max(samples),
            "min_ms": min(samples),
        }


class TraceRegistry:
    """Globally addressable set of ``StepTimer``s."""

    def __init__(self) -> None:
        self._timers: Dict[str, StepTimer] = {}
        self._lock = threading.Lock()

    def timer(self, name: str) -> StepTimer:
        with self._lock:
            t = self._timers.get(name)
            if t is None:
                t = StepTimer(name)
                self._timers[name] = t
            return t

    def record(self, name: str, duration_ms: float) -> None:
        self.timer(name).record(duration_ms)

    def summary(self) -> Dict[str, Dict[str, float]]:
        with self._lock:
            return {name: t.stats() for name, t in self._timers.items()}


_registry: Optional[TraceRegistry] = None
_registry_lock = threading.Lock()


def get_trace_registry() -> TraceRegistry:
    """Return the global ``TraceRegistry`` singleton."""
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = TraceRegistry()
    return _registry