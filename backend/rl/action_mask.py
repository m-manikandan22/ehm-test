"""
action_mask.py — mask illegal RL actions.

Why
---
The legacy 5-action DQN doesn't need a mask because every action is
always available.  A research-grade agent with 9 actions (open
switch, close switch, reconfigure feeder, disconnect load, charge
battery, discharge battery, create island, merge island, NO_OP)
must respect the current grid topology — e.g. you can't close a
switch that's already closed, or discharge a battery with SOC = 0.

``ActionMask`` is a small pure-Python helper that inspects the grid
state and returns a boolean array of legal action indices.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, List


class AdvancedAction(IntEnum):
    OPEN_SWITCH = 0
    CLOSE_SWITCH = 1
    RECONFIGURE_FEEDER = 2
    DISCONNECT_LOAD = 3
    CHARGE_BATTERY = 4
    DISCHARGE_BATTERY = 5
    CREATE_ISLAND = 6
    MERGE_ISLAND = 7
    NO_OP = 8


@dataclass
class ActionMask:
    """Boolean mask, indexed by ``AdvancedAction``."""

    legal: Dict[int, bool]

    def __post_init__(self) -> None:
        for a in AdvancedAction:
            self.legal.setdefault(int(a), True)

    def as_array(self) -> List[bool]:
        return [bool(self.legal[int(a)]) for a in AdvancedAction]

    def allows(self, action: AdvancedAction) -> bool:
        return bool(self.legal.get(int(action), True))

    @classmethod
    def from_grid(cls, grid: Any, state: Dict[str, Any] | None = None) -> "ActionMask":
        """Derive a mask from the current grid state.

        Rules:
          - CLOSE_SWITCH requires at least one open switch.
          - OPEN_SWITCH requires at least one closed switch.
          - DISCHARGE_BATTERY requires at least one battery with SOC > 0.1.
          - CHARGE_BATTERY requires at least one battery with SOC < 0.9.
          - DISCONNECT_LOAD requires at least one load that is currently powered.
          - CREATE_ISLAND requires at least one healthy generator.
          - MERGE_ISLAND requires at least one island in the registry.
        """
        legal = {int(a): True for a in AdvancedAction}
        # Switches.
        edges = getattr(grid.graph, "edges", None) or {}
        n_open = 0
        n_closed = 0
        for ed in (edges(data=True) if hasattr(edges, "__call__") else []):
            try:
                _, _, data = ed
            except Exception:
                continue
            if data.get("is_tie_switch"):
                if data.get("switch_status") == "open":
                    n_open += 1
                else:
                    n_closed += 1
        legal[int(AdvancedAction.CLOSE_SWITCH)] = n_open > 0
        legal[int(AdvancedAction.OPEN_SWITCH)] = n_closed > 0
        # Batteries.
        soc_high = 0
        soc_low = 0
        for node in grid.nodes.values():
            if node.node_type in {"battery", "bess", "supercap"}:
                lvl = float(getattr(node, "battery_level", 0.0))
                if lvl > 0.1:
                    soc_high += 1
                if lvl < 0.9:
                    soc_low += 1
        legal[int(AdvancedAction.DISCHARGE_BATTERY)] = soc_high > 0
        legal[int(AdvancedAction.CHARGE_BATTERY)] = soc_low > 0
        # Loads.
        loads = [n for n in grid.nodes.values()
                 if n.node_type in {
                     "house", "hospital", "hospital_icu", "industry",
                     "commercial", "school", "university", "gov_building",
                     "ev_charger",
                 }]
        powered_loads = [n for n in loads
                         if float(getattr(n, "received_power", 0.0)) > 0.0
                         and not getattr(n, "failed", False)]
        legal[int(AdvancedAction.DISCONNECT_LOAD)] = len(powered_loads) > 0
        # Generators.
        gens = [n for n in grid.nodes.values()
                if n.node_type in {
                    "generator", "generator_solar", "generator_wind",
                    "generator_nuclear", "generator_coal", "generator_gas",
                    "solar_farm", "wind_farm", "substation",
                    "primary_substation",
                } and not getattr(n, "failed", False)]
        legal[int(AdvancedAction.CREATE_ISLAND)] = len(gens) > 0
        legal[int(AdvancedAction.MERGE_ISLAND)] = state is not None and bool(
            state.get("islands", [])
        )
        # NO_OP, RECONFIGURE_FEEDER always legal.
        return cls(legal=legal)