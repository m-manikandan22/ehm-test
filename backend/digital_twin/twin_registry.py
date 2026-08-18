"""
twin_registry.py — grid-wide registry of ``DigitalTwin`` instances.

Why
---
The grid has potentially hundreds of assets.  Looking up a twin by
asset_id at every FLISR decision would be wasteful if we re-scanned
a dict.  ``TwinRegistry`` keeps an O(1) dict plus an interface that
mirrors the lifecycle hooks used by ``SmartGrid.update_power_flow``
(see M2 integration in ``simulation/grid.py``).

Design points:
  - ``register(grid)`` walks the grid's nodes and creates a twin for
    every node.  Existing twins are reused (idempotent).
  - ``sync(grid, dt)`` ticks every twin using the latest physical
    state — cheap because each tick is O(1).
  - ``summary()`` returns roll-up statistics (mean health, count of
    high-risk assets).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from digital_twin.twin import DigitalTwin


class TwinRegistry:
    """Maps ``asset_id`` → ``DigitalTwin``."""

    def __init__(self) -> None:
        self._twins: Dict[str, DigitalTwin] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, grid: Any) -> int:
        """Create a twin for every node in ``grid`` that doesn't have one.

        Returns the number of new twins created.
        """
        created = 0
        for nid, node in grid.nodes.items():
            if nid in self._twins:
                continue
            self._twins[nid] = DigitalTwin(
                asset_id=nid,
                asset_type=getattr(node, "node_type", "generic"),
            )
            created += 1
        return created

    def rebuild(self, grid: Any, *, keep_history: bool = False) -> int:
        """Replace every twin in this registry with fresh twins for ``grid``.

        Use this when the underlying grid is swapped wholesale — for
        example after ``POST /city/generate`` creates a new procedural
        city. If ``keep_history`` is False (the default), existing
        twins' sensor/maintenance histories are dropped.

        Returns the number of twins created.
        """
        self._twins = {}
        self.register(grid)
        if not keep_history:
            for twin in self._twins.values():
                twin.sensor_history.clear()
                twin.maintenance_history.clear()
                twin.health = 1.0
                twin.age_hours = 0.0
                twin.failure_probability = 0.0
        return len(self._twins)

    def add(self, twin: DigitalTwin) -> None:
        """Manually register or replace a twin."""
        self._twins[twin.asset_id] = twin

    def get(self, asset_id: str) -> Optional[DigitalTwin]:
        return self._twins.get(asset_id)

    def all(self) -> List[DigitalTwin]:
        return list(self._twins.values())

    def __len__(self) -> int:
        return len(self._twins)

    def __contains__(self, asset_id: str) -> bool:
        return asset_id in self._twins

    # ------------------------------------------------------------------
    # Synchronisation
    # ------------------------------------------------------------------

    def sync(self, grid: Any, dt_hours: float = 1.0) -> int:
        """Tick every registered twin against the current grid state.

        Returns the number of twins updated.
        """
        updated = 0
        for nid, node in grid.nodes.items():
            twin = self._twins.get(nid)
            if twin is None:
                continue
            physical_state = {
                "voltage": getattr(node, "voltage", 1.0),
                "frequency": getattr(node, "frequency", 50.0),
                "load": getattr(node, "load", 0.0),
                "generation": getattr(node, "generation", 0.0),
                "failed": getattr(node, "failed", False),
            }
            twin.tick(physical_state=physical_state, dt_hours=dt_hours)
            updated += 1
        return updated

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Roll-up statistics across all twins."""
        if not self._twins:
            return {
                "count": 0,
                "mean_health": 1.0,
                "high_risk_count": 0,
                "oldest_age_hours": 0.0,
            }
        twins = list(self._twins.values())
        mean_health = sum(t.health for t in twins) / len(twins)
        high_risk = sum(1 for t in twins if t.failure_probability > 0.5)
        return {
            "count": len(twins),
            "mean_health": mean_health,
            "high_risk_count": high_risk,
            "oldest_age_hours": max(t.age_hours for t in twins),
        }

    def at_risk(self, threshold: float = 0.5) -> List[str]:
        """Return asset_ids whose failure probability exceeds the threshold."""
        return [
            t.asset_id for t in self._twins.values()
            if t.failure_probability >= threshold
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            twin.asset_id: twin.to_dict() for twin in self._twins.values()
        }