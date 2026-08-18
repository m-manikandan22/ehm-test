"""
di.py — Lightweight dependency-injection container for the EHM backend.

The EHM platform exposes many replaceable modules (grid, EMS, SCADA, AI
models, city generator, weather engine, digital twin registry, XAI
explainer, metrics registry, redesigner).  Each needs to be reachable
from FastAPI route handlers, from the SCADA control loop, and from the
benchmark runner — without creating import cycles or hard-coded module
references.

This `Container` is intentionally minimal: register factories at startup
(`container.register("grid", lambda: SmartGrid())`), look them up later
(`container.get("grid")`).  The container is process-global but
thread-safe under the GIL because we only mutate it at startup, never
during a request.

The container is *additive* to the existing `app.state.*` lookups.  All
existing routes still work via the `get_*` helpers in `api/routes.py`;
new code is encouraged to use the container instead.

Public API
----------
- `Container()`            — empty container.
- `c.register(name, fn)`   — bind a name to a factory `fn() -> object`.
- `c.get(name)`            — return the singleton for `name`.
- `c.has(name)`            — boolean membership test.
- `c.names()`              — sorted list of registered names.
- `c.clear()`              — drop every binding (tests use this).
- `c.describe()`           — JSON-friendly summary (no actual values).

The factory is called *lazily* on first `.get(name)` so an
expensive module (e.g. PyPSA-backed EMS) is only built when something
actually asks for it.
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List


class Container:
    """Tiny thread-safe singleton registry."""

    def __init__(self) -> None:
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._instances: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def register(self, name: str, factory: Callable[[], Any]) -> None:
        """Bind a name to a factory.  Overwrites any prior binding."""
        if not name or not isinstance(name, str):
            raise ValueError("Container.register requires a non-empty string name")
        if not callable(factory):
            raise TypeError(f"Container.register({name!r}): factory must be callable")
        with self._lock:
            self._factories[name] = factory
            # If we already had an instance, drop it so the new factory
            # takes effect on next .get().
            self._instances.pop(name, None)

    def get(self, name: str) -> Any:
        """Return the singleton for `name`, building it on first call."""
        # Read both maps atomically.  We snapshot a list of registered
        # names under the lock to avoid deadlocking on the error path
        # (a `threading.Lock` is not reentrant; calling `.names()`
        # while holding the lock would deadlock).
        with self._lock:
            if name in self._instances:
                return self._instances[name]
            if name not in self._factories:
                registered = sorted(self._factories.keys())
            else:
                registered = None
        if registered is not None:
            raise KeyError(
                f"Container has no binding named {name!r}.  "
                f"Registered: {registered}"
            )
        # Build the instance *outside* the lock so a slow factory can't
        # block other readers — the second `_instances[name]` write is
        # also outside the lock; the second writer wins, which is fine
        # because every successful build produces the same singleton.
        instance = self._factories[name]()
        with self._lock:
            self._instances[name] = instance
        return instance

    def has(self, name: str) -> bool:
        return name in self._factories

    def names(self) -> List[str]:
        with self._lock:
            return sorted(self._factories.keys())

    def clear(self) -> None:
        """Drop every binding.  Used by tests."""
        with self._lock:
            self._factories.clear()
            self._instances.clear()

    def describe(self) -> Dict[str, Any]:
        """JSON-friendly summary — never returns the actual instances."""
        with self._lock:
            return {
                "registered": sorted(self._factories.keys()),
                "instantiated": sorted(self._instances.keys()),
                "count_registered": len(self._factories),
                "count_instantiated": len(self._instances),
            }


# ---------------------------------------------------------------------------
# Process-global container
# ---------------------------------------------------------------------------
#
# The container is process-global so that any module — even one imported
# without a FastAPI app reference (e.g. the benchmark runner) — can
# resolve its dependencies.  The FastAPI `lifespan` handler registers the
# concrete factories; everything else just calls `get_container()`.

_global_container: Container = Container()


def get_container() -> Container:
    """Return the process-global DI container."""
    return _global_container


def reset_container() -> None:
    """Drop every binding.  Test-only convenience."""
    _global_container.clear()
