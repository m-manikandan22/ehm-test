"""
state_builder.py — composable RL observation builder.

Why
---
The legacy ``SmartGrid.get_rl_state`` emits a 72-dim numeric vector.
That works for the existing DQN, but research papers usually present
a *decomposition*: voltage features, frequency features, load
forecast, battery SOC, renewable output, congestion, stress,
predicted failure, switch status, transformer health, topology,
weather.  Splitting the features into named extractors makes
ablation studies trivial and gives the XAI panel a per-feature
trace.

The legacy 72-dim path is preserved when ``legacy=True``; new code
uses the modular extractors.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


def voltage_features(grid: Any) -> List[float]:
    vs = [float(getattr(n, "voltage", 1.0)) for n in grid.nodes.values()]
    if not vs:
        return [1.0, 0.0, 0.0, 1.0]
    return [
        sum(vs) / len(vs),
        min(vs),
        max(vs),
        sum(1 for v in vs if v < 0.95) / len(vs),
    ]


def frequency_features(grid: Any) -> List[float]:
    fs = [float(getattr(n, "frequency", 50.0)) for n in grid.nodes.values()]
    if not fs:
        return [50.0, 0.0]
    avg = sum(fs) / len(fs)
    var = sum((f - avg) ** 2 for f in fs) / len(fs)
    return [avg, var]


def load_forecast_features(grid: Any) -> List[float]:
    """Use the mean recent load_history as the load forecast proxy."""
    history_means: List[float] = []
    for n in grid.nodes.values():
        hist = getattr(n, "load_history", None)
        if hist and len(hist) > 0:
            history_means.append(sum(hist) / len(hist))
    if not history_means:
        return [0.0]
    return [sum(history_means) / len(history_means)]


def battery_soc_features(grid: Any) -> List[float]:
    socs = [
        float(getattr(n, "battery_level", 0.0))
        for n in grid.nodes.values()
        if n.node_type in {"battery", "bess", "supercap"}
    ]
    if not socs:
        return [0.0, 0.0]
    return [sum(socs) / len(socs), min(socs)]


def renewable_output_features(grid: Any) -> List[float]:
    gen = 0.0
    ren = 0.0
    for n in grid.nodes.values():
        g = float(getattr(n, "generation", 0.0))
        gen += g
        if n.node_type in {"solar_farm", "wind_farm",
                           "generator_solar", "generator_wind"}:
            ren += g
    return [ren, gen]


def congestion_features(grid: Any) -> List[float]:
    overloaded = 0
    total = 0
    for _, _, d in grid.graph.edges(data=True):
        total += 1
        cap = float(d.get("capacity", 1.0))
        flow = float(d.get("flow", 0.0))
        if cap > 0 and abs(flow) > 0.95 * cap:
            overloaded += 1
    if total == 0:
        return [0.0, 0]
    return [overloaded / total, overloaded]


def node_stress_features(grid: Any) -> List[float]:
    stresses = [float(getattr(n, "stress_level", 0.0))
                for n in grid.nodes.values()]
    if not stresses:
        return [0.0]
    return [sum(stresses) / len(stresses)]


def switch_status_features(grid: Any) -> List[float]:
    ties = 0
    closed = 0
    for _, _, d in grid.graph.edges(data=True):
        if d.get("is_tie_switch"):
            ties += 1
            if d.get("switch_status") == "closed":
                closed += 1
    return [ties, closed]


def weather_features(grid: Any) -> List[float]:
    w = float(getattr(grid, "weather", 0.0))
    return [w]


@dataclass
class StateBuilder:
    """Concatenate named feature extractors into an observation vector."""

    extractors: Dict[str, Callable[[Any], List[float]]] = field(
        default_factory=lambda: {
            "voltage": voltage_features,
            "frequency": frequency_features,
            "load_forecast": load_forecast_features,
            "battery_soc": battery_soc_features,
            "renewable": renewable_output_features,
            "congestion": congestion_features,
            "node_stress": node_stress_features,
            "switches": switch_status_features,
            "weather": weather_features,
        }
    )

    def build(self, grid: Any) -> Dict[str, Any]:
        """Return both the dict-of-features and the flattened vector."""
        features: Dict[str, List[float]] = {}
        for name, fn in self.extractors.items():
            try:
                features[name] = list(fn(grid))
            except Exception:  # noqa: BLE001 — defensive: never crash the agent
                features[name] = [0.0]
        flat: List[float] = []
        for v in features.values():
            flat.extend(v)
        return {"features": features, "vector": flat}

    def build_vector(self, grid: Any) -> List[float]:
        return self.build(grid)["vector"]

    def build_features(self, grid: Any) -> Dict[str, List[float]]:
        return self.build(grid)["features"]