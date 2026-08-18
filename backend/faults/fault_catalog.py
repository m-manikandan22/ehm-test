"""
fault_catalog.py — typed catalog of realistic fault scenarios.

Why
---
A research-grade simulator must produce fault distributions that
match published utility data, not just uniform random failures.  The
catalog here encodes 14 fault types with realistic baseline
probabilities, severity, and propagation behaviour.

The catalog is intentionally small and readable; large studies can
swap in a YAML/JSON catalog loaded from disk via the same API.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set


class FaultType(str, Enum):
    LIGHTNING = "lightning"
    TREE_CONTACT = "tree_contact"
    CABLE_FAILURE = "cable_failure"
    TRANSFORMER_EXPLOSION = "transformer_explosion"
    EQUIPMENT_AGING = "equipment_aging"
    CYBER_ATTACK = "cyber_attack"
    GENERATOR_FAILURE = "generator_failure"
    BATTERY_FAILURE = "battery_failure"
    WIND_LOSS = "wind_loss"
    SOLAR_LOSS = "solar_loss"
    FLOOD = "flood"
    FIRE = "fire"
    EARTHQUAKE = "earthquake"
    ANIMAL_CONTACT = "animal_contact"
    HUMAN_ERROR = "human_error"


@dataclass(frozen=True)
class Fault:
    """Single fault entry in the catalog."""
    type: FaultType
    probability: float
    severity: float           # 0..1, fraction of grid impacted
    propagation: float        # 0..1, chance to spread to a neighbour
    recovery_difficulty: float  # 0..1, time to repair (normalised)
    affected_types: Set[str] = field(default_factory=set)
    description: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "type": self.type.value,
            "probability": self.probability,
            "severity": self.severity,
            "propagation": self.propagation,
            "recovery_difficulty": self.recovery_difficulty,
            "affected_types": sorted(self.affected_types),
            "description": self.description,
        }


_LOAD_TYPES: Set[str] = {
    "house", "hospital", "hospital_icu", "industry", "commercial",
    "school", "university", "gov_building", "ev_charger",
}
_SOURCE_TYPES: Set[str] = {
    "generator", "generator_solar", "generator_wind",
    "generator_nuclear", "generator_coal", "generator_gas",
    "solar_farm", "wind_farm", "substation", "primary_substation",
}
_STORAGE_TYPES: Set[str] = {"battery", "bess", "supercap"}
_LINE_TYPES: Set[str] = {"pole", "transformer", "transmission_tower"}


FAULT_CATALOG: Dict[FaultType, Fault] = {
    FaultType.LIGHTNING: Fault(
        type=FaultType.LIGHTNING,
        probability=0.18, severity=0.40, propagation=0.20,
        recovery_difficulty=0.40,
        affected_types=_LINE_TYPES | _SOURCE_TYPES,
        description="Lightning strike on line or substation bus.",
    ),
    FaultType.TREE_CONTACT: Fault(
        type=FaultType.TREE_CONTACT,
        probability=0.22, severity=0.25, propagation=0.10,
        recovery_difficulty=0.20,
        affected_types=_LINE_TYPES,
        description="Vegetation contact during wind events.",
    ),
    FaultType.CABLE_FAILURE: Fault(
        type=FaultType.CABLE_FAILURE,
        probability=0.08, severity=0.50, propagation=0.05,
        recovery_difficulty=0.60,
        affected_types=_LINE_TYPES | _SOURCE_TYPES,
        description="Underground cable insulation breakdown.",
    ),
    FaultType.TRANSFORMER_EXPLOSION: Fault(
        type=FaultType.TRANSFORMER_EXPLOSION,
        probability=0.04, severity=0.80, propagation=0.40,
        recovery_difficulty=0.85,
        affected_types=_LINE_TYPES,
        description="Catastrophic transformer failure with downstream impact.",
    ),
    FaultType.EQUIPMENT_AGING: Fault(
        type=FaultType.EQUIPMENT_AGING,
        probability=0.12, severity=0.30, propagation=0.00,
        recovery_difficulty=0.70,
        affected_types=_LINE_TYPES | _SOURCE_TYPES | _STORAGE_TYPES,
        description="End-of-life wear-out, esp. under heatwave loading.",
    ),
    FaultType.CYBER_ATTACK: Fault(
        type=FaultType.CYBER_ATTACK,
        probability=0.03, severity=0.60, propagation=0.30,
        recovery_difficulty=0.50,
        affected_types={"substation", "primary_substation", "distribution_substation"},
        description="Coordinated FDIA / replay injection on a substation.",
    ),
    FaultType.GENERATOR_FAILURE: Fault(
        type=FaultType.GENERATOR_FAILURE,
        probability=0.05, severity=0.70, propagation=0.15,
        recovery_difficulty=0.65,
        affected_types=_SOURCE_TYPES,
        description="Trip event at a generator (mechanical / fuel).",
    ),
    FaultType.BATTERY_FAILURE: Fault(
        type=FaultType.BATTERY_FAILURE,
        probability=0.04, severity=0.45, propagation=0.05,
        recovery_difficulty=0.55,
        affected_types=_STORAGE_TYPES,
        description="BMS trip / thermal runaway on a battery cell.",
    ),
    FaultType.WIND_LOSS: Fault(
        type=FaultType.WIND_LOSS,
        probability=0.06, severity=0.50, propagation=0.00,
        recovery_difficulty=0.10,
        affected_types={"wind_farm"},
        description="Wind farm curtailment due to cut-out speed.",
    ),
    FaultType.SOLAR_LOSS: Fault(
        type=FaultType.SOLAR_LOSS,
        probability=0.05, severity=0.40, propagation=0.00,
        recovery_difficulty=0.10,
        affected_types={"solar_farm"},
        description="Cloud cover / inverter outage at a solar farm.",
    ),
    FaultType.FLOOD: Fault(
        type=FaultType.FLOOD,
        probability=0.02, severity=0.65, propagation=0.20,
        recovery_difficulty=0.80,
        affected_types=_SOURCE_TYPES | _STORAGE_TYPES | _LOAD_TYPES,
        description="Flood inundation of low-lying substations.",
    ),
    FaultType.FIRE: Fault(
        type=FaultType.FIRE,
        probability=0.02, severity=0.55, propagation=0.25,
        recovery_difficulty=0.75,
        affected_types=_LINE_TYPES | _SOURCE_TYPES,
        description="Wildfire / substation fire.",
    ),
    FaultType.EARTHQUAKE: Fault(
        type=FaultType.EARTHQUAKE,
        probability=0.01, severity=0.90, propagation=0.50,
        recovery_difficulty=0.95,
        affected_types=_LINE_TYPES | _SOURCE_TYPES | _STORAGE_TYPES,
        description="Seismic event causing multiple simultaneous outages.",
    ),
    FaultType.ANIMAL_CONTACT: Fault(
        type=FaultType.ANIMAL_CONTACT,
        probability=0.07, severity=0.15, propagation=0.00,
        recovery_difficulty=0.10,
        affected_types=_LINE_TYPES,
        description="Squirrel / bird contact on a pole-top insulator.",
    ),
    FaultType.HUMAN_ERROR: Fault(
        type=FaultType.HUMAN_ERROR,
        probability=0.06, severity=0.35, propagation=0.10,
        recovery_difficulty=0.30,
        affected_types=_LINE_TYPES | _SOURCE_TYPES,
        description="Operator mis-coordination during switching.",
    ),
}


def catalog_for_type(ntype: str) -> List[Fault]:
    """Return faults whose ``affected_types`` includes ``ntype``."""
    return [f for f in FAULT_CATALOG.values() if ntype in f.affected_types]