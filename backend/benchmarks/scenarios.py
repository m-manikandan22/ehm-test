"""
scenarios.py — Standard fault scenarios for benchmarking.

Each scenario is a function that takes a SmartGrid and applies a deterministic
sequence of failures, then returns the grid. The runner loops over scenarios
and seeds to gather statistics.
"""
from __future__ import annotations

from typing import Callable, Dict, List

from simulation.grid import SmartGrid


# Each entry is {name: setup_fn(grid) -> dict_with_metadata}
SCENARIOS: Dict[str, Callable[[SmartGrid], dict]] = {}


def _register(name: str):
    def deco(fn):
        SCENARIOS[name] = fn
        return fn
    return deco


@_register("single_pole_fault")
def single_pole_fault(g: SmartGrid) -> dict:
    g.inject_failure("P_A2")
    return {
        "kind":     "single_pole_fault",
        "faulted":  ["P_A2"],
        "expected_isolated": ["H4", "H5", "H6"],
        "severity": "low",
    }


@_register("feeder_head_fault")
def feeder_head_fault(g: SmartGrid) -> dict:
    g.inject_failure("P_B1")
    return {
        "kind":    "feeder_head_fault",
        "faulted": ["P_B1"],
        "expected_isolated": ["P_B2", "P_B3", "HOSP", "H10", "H11"],
        "severity": "medium",
    }


@_register("transformer_fault")
def transformer_fault(g: SmartGrid) -> dict:
    g.inject_failure("T_A")
    return {
        "kind":    "transformer_fault",
        "faulted": ["T_A"],
        "expected_isolated": ["P_A1", "P_A2", "P_A3"],
        "severity": "high",
    }


@_register("generator_loss")
def generator_loss(g: SmartGrid) -> dict:
    g.inject_failure("GEN_NUCLEAR")
    return {
        "kind":    "generator_loss",
        "faulted": ["GEN_NUCLEAR"],
        "expected_isolated": [],
        "severity": "high",
    }


@_register("storage_loss")
def storage_loss(g: SmartGrid) -> dict:
    g.inject_failure("STORAGE_BAT")
    return {
        "kind":    "storage_loss",
        "faulted": ["STORAGE_BAT"],
        "expected_isolated": [],
        "severity": "medium",
    }


@_register("double_fault")
def double_fault(g: SmartGrid) -> dict:
    g.inject_failure("P_A2")
    g.inject_failure("P_C1")
    return {
        "kind":    "double_fault",
        "faulted": ["P_A2", "P_C1"],
        "expected_isolated": ["H4", "H5", "H6"],
        "severity": "high",
    }


@_register("storm_all_feeders")
def storm_all_feeders(g: SmartGrid) -> dict:
    g.storm_active = True
    g.inject_failure("P_B1")
    g.inject_failure("P_C2")
    return {
        "kind":    "storm_all_feeders",
        "faulted": ["P_B1", "P_C2"],
        "expected_isolated": ["P_B2", "P_B3", "HOSP"],
        "severity": "extreme",
    }


@_register("hospital_loss")
def hospital_loss(g: SmartGrid) -> dict:
    g.inject_failure("P_B3")
    return {
        "kind":    "hospital_loss",
        "faulted": ["P_B3"],
        "expected_isolated": ["HOSP"],
        "severity": "critical",
    }


@_register("industry_loss")
def industry_loss(g: SmartGrid) -> dict:
    g.inject_failure("P_C3")
    return {
        "kind":    "industry_loss",
        "faulted": ["P_C3"],
        "expected_isolated": ["IND0"],
        "severity": "high",
    }


@_register("cascade")
def cascade(g: SmartGrid) -> dict:
    g.inject_failure("T_B")
    g.inject_failure("T_C")
    return {
        "kind":    "cascade",
        "faulted": ["T_B", "T_C"],
        "expected_isolated": ["P_B1", "P_B2", "P_B3", "HOSP",
                              "P_C1", "P_C2", "P_C3", "IND0"],
        "severity": "extreme",
    }


# ── 3 weather modes applied on top of the base scenarios ───────────────

WEATHER_MODES = ["clear", "cloudy", "stormy"]


def apply_weather(grid: SmartGrid, mode: str) -> None:
    """Perturb generation/load according to a weather mode."""
    if mode == "clear":
        return
    if mode == "cloudy":
        for nid, n in grid.nodes.items():
            if n.node_type == "generator_solar":
                n.generation *= 0.6
            n.load *= 1.10
    elif mode == "stormy":
        grid.storm_active = True
        for nid, n in grid.nodes.items():
            if n.node_type == "generator_wind":
                n.generation *= 1.3
            elif n.node_type == "generator_solar":
                n.generation *= 0.3
            n.load *= 1.25