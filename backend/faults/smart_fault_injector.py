"""
smart_fault_injector.py — context-aware fault injection.

Why
---
Random failures aren't realistic.  Realistic fault distributions
depend on weather (storms raise lightning/tree-contact rates), asset
age (aging equipment fails more), and asset type (wind turbines trip
under cyclone winds).  ``SmartFaultInjector`` consumes the current
``WeatherState`` and ``SmartGrid`` state and produces a list of
``FaultEvent`` records whose probabilities are derived from the
catalog and modulated by these contexts.

The injector never *applies* failures — it returns a structured
``FaultEvent`` list.  Applying them is the caller's job (typically
``grid.inject_failure(node_id)``), which preserves the existing
failure-injection API surface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from faults.fault_catalog import Fault, FaultType, catalog_for_type, FAULT_CATALOG
from utils.seeds import make_rng
from weather.weather_engine import WeatherState, WeatherFactors


@dataclass
class FaultEvent:
    """One injected fault event — to be applied by the caller."""
    type: FaultType
    node_id: Optional[str]
    probability: float
    severity: float
    propagation: float
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "node_id": self.node_id,
            "probability": self.probability,
            "severity": self.severity,
            "propagation": self.propagation,
            "description": self.description,
        }


@dataclass
class SmartFaultInjector:
    """Context-aware fault event generator."""

    seed: int = 42
    expected_per_step: float = 0.05
    _rng: Any = None

    def _initialise(self) -> None:
        if self._rng is None:
            self._rng = make_rng(self.seed)

    # ------------------------------------------------------------------

    def inject(
        self,
        weather_state: WeatherState,
        grid: Any,
        *,
        factors: Optional[WeatherFactors] = None,
        max_events: int = 5,
    ) -> List[FaultEvent]:
        """Sample faults using the catalog, weighted by weather + node health.

        Parameters
        ----------
        weather_state : WeatherState
            Current weather state.
        grid : SmartGrid
            The live grid (used to choose candidate node_ids).
        factors : WeatherFactors, optional
            Pre-fetched factors for ``weather_state``.  If ``None``,
            defaults of 1.0 are used (caller didn't bother to
            instantiate ``WeatherEngine``).
        max_events : int
            Upper bound on returned events (clamps the tail).
        """
        self._initialise()
        f = factors or WeatherFactors()
        events: List[FaultEvent] = []
        # Draw a Poisson-ish number of base events per step.
        n_base = int(self._rng.poisson(self.expected_per_step * f.fault_prob_factor))
        n_base = min(max_events, max(0, n_base))
        for _ in range(n_base):
            event = self._sample_one(weather_state, grid, f)
            if event is not None:
                events.append(event)
        return events

    # ------------------------------------------------------------------

    def _sample_one(
        self,
        weather_state: WeatherState,
        grid: Any,
        factors: WeatherFactors,
    ) -> Optional[FaultEvent]:
        """Pick one fault type and one candidate node, weighted."""
        # 1. Pick a candidate node uniformly from the live grid.
        live_ids = [nid for nid, n in grid.nodes.items()
                    if not getattr(n, "failed", False)]
        if not live_ids:
            return None
        target_id = live_ids[int(self._rng.integers(0, len(live_ids)))]
        target = grid.nodes[target_id]
        ntype = getattr(target, "node_type", "generic")

        # 2. Find the candidate faults for this node type.
        candidates = catalog_for_type(ntype)
        if not candidates:
            return None

        # 3. Compute weighted probabilities.
        weights = []
        for fault in candidates:
            w = self._probability_modifier(fault, weather_state, factors, target)
            weights.append(max(0.0, w))
        total = sum(weights)
        if total <= 0.0:
            return None
        probs = [w / total for w in weights]
        idx = int(self._rng.choice(len(candidates), p=probs))
        chosen = candidates[idx]
        return FaultEvent(
            type=chosen.type,
            node_id=target_id,
            probability=weights[idx] / total,
            severity=chosen.severity * factors.fault_prob_factor,
            propagation=chosen.propagation,
            description=chosen.description,
        )

    # ------------------------------------------------------------------

    def _probability_modifier(
        self,
        fault: Fault,
        weather_state: WeatherState,
        factors: WeatherFactors,
        node: Any,
    ) -> float:
        """Combine base probability with weather, node health, and asset type."""
        base = fault.probability
        # Weather modulation.
        weather_mult = 1.0
        if weather_state in (WeatherState.STORM, WeatherState.CYCLONE):
            if fault.type in (FaultType.LIGHTNING, FaultType.TREE_CONTACT,
                              FaultType.WIND_LOSS):
                weather_mult = 2.5
        elif weather_state == WeatherState.HEATWAVE:
            if fault.type in (FaultType.EQUIPMENT_AGING,
                              FaultType.TRANSFORMER_EXPLOSION):
                weather_mult = 2.0
        elif weather_state == WeatherState.RAIN:
            if fault.type == FaultType.CABLE_FAILURE:
                weather_mult = 1.5

        # Health modulation — aged assets are more likely to fault.
        health = getattr(node, "_twin_health", 1.0)
        health_mult = 1.0 + max(0.0, 1.0 - health) * 1.5

        # Type-specific boosts.
        type_mult = 1.0
        if fault.type == FaultType.WIND_LOSS and weather_state == WeatherState.CYCLONE:
            type_mult = 5.0
        if fault.type == FaultType.SOLAR_LOSS and weather_state == WeatherState.CLOUDY:
            type_mult = 3.0

        return base * weather_mult * health_mult * type_mult

    # ------------------------------------------------------------------

    def apply(self, grid: Any, events: List[FaultEvent]) -> List[str]:
        """Apply the events to the grid by calling ``inject_failure`` per event.

        Returns the list of messages produced by the grid's
        ``inject_failure`` (which may legitimately be empty if the
        node was already failed).
        """
        applied: List[str] = []
        for ev in events:
            if ev.node_id is None or ev.node_id not in grid.nodes:
                continue
            msg = grid.inject_failure(ev.node_id)
            applied.append(msg)
        return applied