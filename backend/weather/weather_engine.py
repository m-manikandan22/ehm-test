"""
weather_engine.py — Markov-chain weather engine.

Why
---
Real distribution grids are weather-coupled.  Solar output drops with
cloud cover, wind ramps with weather fronts, and storms dramatically
raise fault probability.  A digital-twin simulator that ignores
weather can't reproduce any published SAIDI/SAIFI scenarios.

This module exposes a tiny state machine with six states:
``sunny``, ``cloudy``, ``rain``, ``storm``, ``heatwave``, ``cyclone``.
Each state carries per-asset multipliers that callers can apply:
``solar_factor``, ``wind_factor``, ``load_factor``, ``fault_prob_factor``,
``battery_discharge_factor``.  Transitions are governed by a 6×6
matrix in ``configs/weather.yaml``.

Design points:
  - Deterministic given a fixed seed (uses ``utils.seeds.make_rng``).
  - Pure-Python (no third-party weather data, no API calls).
  - Replays the last N states so the XAI panel can show "we
    transitioned from sunny → storm 5 steps ago".
"""
from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

import yaml

from utils.seeds import make_rng


class WeatherState(str, Enum):
    SUNNY = "sunny"
    CLOUDY = "cloudy"
    RAIN = "rain"
    STORM = "storm"
    HEATWAVE = "heatwave"
    CYCLONE = "cyclone"


_DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "configs", "weather.yaml"
)


@dataclass(frozen=True)
class WeatherFactors:
    """Per-state multipliers applied to the grid."""
    solar_factor: float = 1.0
    wind_factor: float = 1.0
    load_factor: float = 1.0
    fault_prob_factor: float = 1.0
    battery_discharge_factor: float = 1.0
    temperature_c: float = 25.0


@dataclass
class WeatherEngine:
    """Markov-chain weather state machine."""

    config_path: str = _DEFAULT_CONFIG_PATH
    seed: int = 42
    state: WeatherState = WeatherState.SUNNY
    history: Deque[WeatherState] = field(default_factory=lambda: deque(maxlen=64))

    # Internal state set lazily on first ``step`` or ``set``.
    _factors: Dict[WeatherState, WeatherFactors] = field(default_factory=dict)
    _transitions: Dict[WeatherState, Dict[WeatherState, float]] = field(
        default_factory=dict
    )
    _rng: Any = None
    _initialised: bool = False

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _initialise(self) -> None:
        if self._initialised:
            return
        config = self._load_config()
        self._factors = {
            WeatherState(name): WeatherFactors(**fac)
            for name, fac in config.get("factors", {}).items()
        }
        self._transitions = {
            WeatherState(name): {
                WeatherState(t): float(p) for t, p in row.items()
            }
            for name, row in config.get("transitions", {}).items()
        }
        self._rng = make_rng(self.seed)
        # Backfill any missing factors with sensible defaults.
        for s in WeatherState:
            self._factors.setdefault(s, WeatherFactors())
            self._transitions.setdefault(s, {})
        self._initialised = True

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            return _FALLBACK_CONFIG
        with open(self.config_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return data

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def step(self) -> WeatherState:
        """Advance one Markov step and return the new state."""
        self._initialise()
        row = self._transitions.get(self.state, {})
        next_state = self._sample_transition(row)
        self.set(next_state)
        return self.state

    def set(self, new_state: WeatherState) -> WeatherState:
        """Force-set the weather state (useful for tests / scenario YAML)."""
        self._initialise()
        self.state = WeatherState(new_state)
        self.history.append(self.state)
        return self.state

    def get_factors(self) -> WeatherFactors:
        """Return the multiplier set for the current state."""
        self._initialise()
        return self._factors[self.state]

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the engine state."""
        self._initialise()
        f = self._factors[self.state]
        return {
            "state": self.state.value,
            "factors": {
                "solar_factor": f.solar_factor,
                "wind_factor": f.wind_factor,
                "load_factor": f.load_factor,
                "fault_prob_factor": f.fault_prob_factor,
                "battery_discharge_factor": f.battery_discharge_factor,
                "temperature_c": f.temperature_c,
            },
            "history": [s.value for s in self.history],
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _sample_transition(
        self, row: Dict[WeatherState, float]
    ) -> WeatherState:
        if not row:
            return self.state
        states = list(row.keys())
        probs = [max(0.0, float(row[s])) for s in states]
        total = sum(probs)
        if total <= 0.0:
            return self.state
        probs = [p / total for p in probs]
        choice = self._rng.choice(len(states), p=probs)
        return states[int(choice)]


# Default config used when ``configs/weather.yaml`` is absent.  Row
# sums are approximately 1; small residual mass is treated as "stay".
_FALLBACK_CONFIG: Dict[str, Any] = {
    "factors": {
        "sunny":     {"solar_factor": 1.00, "wind_factor": 0.80, "load_factor": 1.00, "fault_prob_factor": 0.30, "battery_discharge_factor": 0.50, "temperature_c": 28.0},
        "cloudy":    {"solar_factor": 0.55, "wind_factor": 1.00, "load_factor": 1.00, "fault_prob_factor": 0.50, "battery_discharge_factor": 0.70, "temperature_c": 22.0},
        "rain":      {"solar_factor": 0.30, "wind_factor": 1.20, "load_factor": 1.05, "fault_prob_factor": 1.20, "battery_discharge_factor": 1.10, "temperature_c": 18.0},
        "storm":     {"solar_factor": 0.15, "wind_factor": 1.50, "load_factor": 1.15, "fault_prob_factor": 3.00, "battery_discharge_factor": 1.80, "temperature_c": 16.0},
        "heatwave":  {"solar_factor": 1.10, "wind_factor": 0.50, "load_factor": 1.30, "fault_prob_factor": 1.40, "battery_discharge_factor": 1.40, "temperature_c": 42.0},
        "cyclone":   {"solar_factor": 0.05, "wind_factor": 1.80, "load_factor": 1.40, "fault_prob_factor": 5.00, "battery_discharge_factor": 2.50, "temperature_c": 14.0},
    },
    "transitions": {
        "sunny":    {"sunny": 0.70, "cloudy": 0.20, "rain": 0.05, "heatwave": 0.05},
        "cloudy":   {"sunny": 0.30, "cloudy": 0.40, "rain": 0.20, "storm": 0.10},
        "rain":     {"cloudy": 0.30, "rain": 0.40, "storm": 0.20, "sunny": 0.10},
        "storm":    {"rain": 0.40, "storm": 0.30, "cloudy": 0.20, "cyclone": 0.10},
        "heatwave": {"sunny": 0.30, "heatwave": 0.50, "cloudy": 0.15, "storm": 0.05},
        "cyclone":  {"storm": 0.50, "rain": 0.30, "cloudy": 0.15, "cyclone": 0.05},
    },
}