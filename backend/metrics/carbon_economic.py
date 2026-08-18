"""
carbon_economic.py — carbon emission + economic cost metrics.

Why
---
The base reward composer tracks voltage stability, outages, and
renewable usage, but a *publication-grade* digital twin must also
report two cost dimensions every utility engineer cares about:

  - Carbon emissions   — kg CO₂-equivalent per step, computed from
                         the per-MWh emission factor of each generator.
  - Economic cost      — $/step, computed from the marginal cost of
                         each generator + load-shedding penalty.

Both metrics are derived from the same per-step snapshot used by the
IEEE 1366 + grid_kpis modules; they never mutate the grid.  Tests in
``tests/test_carbon_economic.py`` verify the formulas.

Backward compatibility
----------------------
The new helpers live in a new module; existing modules are untouched.
The new endpoints register under ``/metrics/carbon`` and
``/metrics/economic`` (see ``metrics_routes.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List


# Carbon intensity (kg CO₂ per MWh).  Reference values from IPCC AR6
# median estimates for the relevant generation mix:
#   coal: 820, gas: 490, oil: 720, nuclear: 12, hydro: 24, biomass: 230,
#   solar: 48, wind: 11, geothermal: 38, battery: 30 (round-trip avg).
# Sources: IPCC AR6 WG III Ch. 6; IEA Electricity Information 2023.
_EMISSION_FACTORS_KG_PER_MWH: Dict[str, float] = {
    "generator_coal": 820.0,
    "generator_gas": 490.0,
    "generator_nuclear": 12.0,
    "generator_solar": 48.0,
    "generator_wind": 11.0,
    "solar_farm": 48.0,
    "wind_farm": 11.0,
    "battery": 30.0,
    "bess": 30.0,
    "substation": 0.0,         # passes through, no direct emission
    "primary_substation": 0.0,
    "distribution_substation": 0.0,
    "microgrid_root": 0.0,
}

# Marginal cost ($/MWh).  Reference values from US EIA AEO 2024:
#   coal: 65, gas: 45, nuclear: 25, solar: 30, wind: 28, battery: 90.
_MARGINAL_COST_USD_PER_MWH: Dict[str, float] = {
    "generator_coal": 65.0,
    "generator_gas": 45.0,
    "generator_nuclear": 25.0,
    "generator_solar": 30.0,
    "generator_wind": 28.0,
    "solar_farm": 30.0,
    "wind_farm": 28.0,
    "battery": 90.0,
    "bess": 90.0,
    "substation": 0.0,
    "primary_substation": 0.0,
    "distribution_substation": 0.0,
    "microgrid_root": 0.0,
}

# Value of Lost Load (VoLL) — what 1 MWh of unsupplied demand costs the
# utility.  Published estimates range from $2 000 (residential) to
# $50 000/MWh (large industrial).  The default reflects the CWE mix.
VOLL_USD_PER_MWH = 8_000.0

# Voltage deviation penalty — a synthetic $ penalty for each bus
# outside the [0.95, 1.05] pu band, scaled by the per-MW load.
VOLTAGE_PENALTY_USD_PER_MW = 50.0


@dataclass
class StepCost:
    """Per-step cost rollup."""

    carbon_kg: float = 0.0
    economic_usd: float = 0.0
    energy_not_served_mwh: float = 0.0
    voltage_penalty_usd: float = 0.0
    components: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "carbon_kg": float(self.carbon_kg),
            "economic_usd": float(self.economic_usd),
            "energy_not_served_mwh": float(self.energy_not_served_mwh),
            "voltage_penalty_usd": float(self.voltage_penalty_usd),
            "components": dict(self.components),
        }


def _gen_mw(node: Any) -> float:
    """Return the current per-unit generation of a node (MW proxy)."""
    return max(0.0, float(getattr(node, "generation", 0.0)))


def _load_mw(node: Any) -> float:
    return max(0.0, float(getattr(node, "load", 0.0)))


def compute_step_cost(grid: Any) -> StepCost:
    """Return the carbon / economic cost rollup for one step of ``grid``."""
    carbon = 0.0
    economic = 0.0
    components: Dict[str, float] = {}
    # 1) Carbon — emissions from each generator.
    for nid, node in grid.nodes.items():
        if getattr(node, "failed", False):
            continue
        gen = _gen_mw(node)
        if gen <= 0.0:
            continue
        factor = _EMISSION_FACTORS_KG_PER_MWH.get(
            getattr(node, "node_type", ""), 0.0,
        )
        contrib = factor * gen
        carbon += contrib
        components[f"carbon:{node.node_type}:{nid}"] = contrib
    # 2) Economic — marginal generation cost + load shedding penalty.
    for nid, node in grid.nodes.items():
        if getattr(node, "failed", False):
            continue
        gen = _gen_mw(node)
        if gen > 0.0:
            cost = _MARGINAL_COST_USD_PER_MWH.get(
                getattr(node, "node_type", ""), 0.0,
            ) * gen
            economic += cost
            components[f"gencost:{node.node_type}:{nid}"] = cost
    # 3) Value of Lost Load — failed nodes lose their load contribution.
    ens_mwh = 0.0
    for nid, node in grid.nodes.items():
        if getattr(node, "failed", False):
            lost = _load_mw(node)
            ens_mwh += lost
            economic += VOLL_USD_PER_MWH * lost
            components[f"voll:{nid}"] = VOLL_USD_PER_MWH * lost
    # 4) Voltage deviation penalty.
    vp = 0.0
    for nid, node in grid.nodes.items():
        if getattr(node, "failed", False):
            continue
        v = float(getattr(node, "voltage", 1.0))
        if 0.95 <= v <= 1.05:
            continue
        dev = abs(v - 1.0)
        contrib = VOLTAGE_PENALTY_USD_PER_MW * _load_mw(node) * dev
        vp += contrib
        components[f"vpenalty:{nid}"] = contrib
    economic += vp
    return StepCost(
        carbon_kg=float(carbon),
        economic_usd=float(economic),
        energy_not_served_mwh=float(ens_mwh),
        voltage_penalty_usd=float(vp),
        components=components,
    )


# ----------------------------------------------------------------------
# Reward composer hook — extend with carbon / economic penalties.
# ----------------------------------------------------------------------


def carbon_penalty(breakdown_state: Dict[str, Any]) -> float:
    """Return a negative reward proportional to the step's carbon.

    Expects ``breakdown_state`` to carry a ``"carbon_kg"`` key.
    """
    return -float(breakdown_state.get("carbon_kg", 0.0)) / 1000.0


def economic_penalty(breakdown_state: Dict[str, Any]) -> float:
    """Return a negative reward proportional to the step's economic cost."""
    return -float(breakdown_state.get("economic_usd", 0.0)) / 1000.0
