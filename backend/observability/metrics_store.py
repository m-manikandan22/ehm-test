"""
metrics_store.py — append-only ring buffer for per-step telemetry.

Why a ring buffer (not a database)?
-----------------------------------
For research-grade reproducibility we want a per-step audit trail of
every observability signal the platform produces: power-flow residuals,
RL rewards, fault scores, weather transitions, microgrid formations,
attack detections, redesign deltas, etc.  A persistent database would
add latency and an external dependency.  A ring buffer in-process keeps
everything in memory with O(1) append, predictable retrieval, and the
ability to flush to disk on demand for offline analysis.

The buffer is process-global so the FastAPI app, the SCADA control
loop, the benchmark runner and the frontend's `/metrics/full` endpoint
all see the same view.
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional


_DEFAULT_CAPACITY = 4096
_ENV_CAPACITY = "EHM_METRICS_CAPACITY"


class MetricsStore:
    """Thread-safe append-only ring buffer of named time-series."""

    def __init__(self, capacity: int = _DEFAULT_CAPACITY) -> None:
        if capacity <= 0:
            raise ValueError("MetricsStore capacity must be positive")
        self._capacity = capacity
        self._lock = threading.Lock()
        # Backing structure: dict-of-deques, one deque per series name.
        self._series: Dict[str, Deque[Dict[str, Any]]] = {}

    # ---- mutators -----------------------------------------------------

    def record(self, name: str, value: Any, **extras: Any) -> None:
        """Append a single observation to series `name`.

        `value` can be any JSON-serialisable scalar or dict.  `extras`
        are merged into the record (e.g. timestep=, node_id=).
        """
        if not name:
            raise ValueError("MetricsStore.record requires a non-empty name")
        with self._lock:
            dq = self._series.get(name)
            if dq is None:
                dq = deque(maxlen=self._capacity)
                self._series[name] = dq
            entry: Dict[str, Any] = {
                "t": time.time(),
                "value": value,
            }
            entry.update(extras)
            dq.append(entry)

    # ---- readers ------------------------------------------------------

    def get(self, name: str) -> List[Dict[str, Any]]:
        """Return a snapshot list of all records in series `name`."""
        with self._lock:
            dq = self._series.get(name)
            return list(dq) if dq is not None else []

    def latest(self, name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            dq = self._series.get(name)
            return dq[-1] if dq else None

    def series_names(self) -> List[str]:
        with self._lock:
            return sorted(self._series.keys())

    def summary(self) -> Dict[str, Any]:
        """Per-series counts (no values)."""
        with self._lock:
            return {
                name: {
                    "count": len(dq),
                    "capacity": dq.maxlen,
                    "latest_t": dq[-1]["t"] if dq else None,
                }
                for name, dq in sorted(self._series.items())
            }

    def flush_to_jsonl(self, path: str) -> int:
        """Append every record to `path` as JSON lines.  Returns count."""
        n = 0
        with self._lock:
            with open(path, "a", encoding="utf-8") as fh:
                for name, dq in self._series.items():
                    for entry in dq:
                        fh.write(
                            json.dumps({"series": name, **entry}, separators=(",", ":"))
                            + "\n"
                        )
                        n += 1
        return n

    def clear(self) -> None:
        with self._lock:
            self._series.clear()


# ---------------------------------------------------------------------------
# Process-global instance
# ---------------------------------------------------------------------------

_global: Optional[MetricsStore] = None
_global_lock = threading.Lock()


def get_store() -> MetricsStore:
    """Return the process-global MetricsStore (lazy-init)."""
    global _global
    if _global is None:
        with _global_lock:
            if _global is None:
                cap = int(os.environ.get(_ENV_CAPACITY, _DEFAULT_CAPACITY))
                _global = MetricsStore(capacity=cap)
    return _global


def reset_store() -> None:
    """Drop every series.  Test-only convenience."""
    global _global
    with _global_lock:
        _global = None
