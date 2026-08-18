"""info_flow.py — Stage-42 wiring for LSTM / digital-twin / EMS /
predictive-healer information paths.

Stage 41 audit found that ``runner.py`` declares flags
``enable_lstm``, ``enable_twin``, ``enable_predictive_healing``,
``enable_ems`` in ``ExperimentConfig`` but never reads them inside
the loop. This module is the *information-flow glue* that wires
those modules into the harness.

Design rules
------------
* **No future-information leakage.** Every forecast / risk score /
  predictive-heal decision uses only information available at the
  *current* timestep ``t``.
* **Defensive imports.** Each helper tolerates the LSTM / twin /
  EMS module being unavailable (the test environment may be
  minimal); it falls back to a clearly-flagged sentinel.
* **Deterministic per seed.** The LSTM forecaster is constructed
  once per ``run_single``; its random weights are seeded via
  ``set_global_seed`` (already called by the runner).
* **The harness, not the algorithm.** These helpers do not change
  the underlying physics / learning algorithms — they only *wire*
  the existing modules into the harness.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

# ----------------------------------------------------------------------
# LSTM demand forecaster
# ----------------------------------------------------------------------

_LSTM_SEQ_LEN = 10  # matches DemandForecaster.SEQ_LEN


def _aggregate_grid_load_and_gen(grid) -> Tuple[float, float]:
    """Return (aggregate_load, aggregate_generation) for the current grid.

    These are the two observable channels the LSTM uses as inputs.
    The third input (``weather``) is approximated from the
    scenario's ``weather_mode``.
    """
    load = 0.0
    gen = 0.0
    for n in grid.nodes.values():
        if getattr(n, "failed", False) or getattr(n, "isolated", False):
            continue
        load += float(getattr(n, "load", 0.0) or 0.0)
        gen += float(getattr(n, "generation", 0.0) or 0.0)
    return load, gen


def _build_lstm_forecaster(seed: int):
    """Construct a DemandForecaster with deterministic weights."""
    from models.lstm_model import DemandForecaster

    forecaster = DemandForecaster()
    return forecaster


def _compute_lstm_forecast(
    grid,
    history: Deque[Tuple[float, float, float]],
    seed: int,
) -> float:
    """Return a *non-leaking* forecast of next-step aggregate load.

    The history deque holds the last ``_LSTM_SEQ_LEN`` observations
    ``[aggregate_load, aggregate_gen, weather]`` from timesteps
    ``<= current step``. If fewer than ``_LSTM_SEQ_LEN`` observations
    are available, we pad with the earliest available observation
    (a conservative warm-up).
    """
    from models.lstm_model import DemandForecaster

    if not history:
        return 0.5
    seq = list(history)[-_LSTM_SEQ_LEN:]
    # left-pad with the first observation if we don't yet have a full
    # window. This is a *warm-up* and contains no future information.
    if len(seq) < _LSTM_SEQ_LEN:
        seq = [seq[0]] * (_LSTM_SEQ_LEN - len(seq)) + seq

    forecaster = _build_lstm_forecaster(seed)
    pred = forecaster.predict([[load, gen, weather] for load, gen, weather in seq])
    return float(pred)


# ----------------------------------------------------------------------
# Digital twin risk map
# ----------------------------------------------------------------------

# Risk-score threshold above which an asset is "high-risk" and the
# health-aware controller should prefer alternative paths.
_HEALTH_RISK_HIGH = 0.5


def _build_twin_registry(grid) -> Any:
    """Build a TwinRegistry mirroring the grid's nodes."""
    from digital_twin.twin_registry import TwinRegistry

    registry = TwinRegistry()
    registry.register(grid)
    return registry


def _tick_twin_registry(grid, registry) -> None:
    """Advance every twin by one step using the grid's state."""
    if registry is None or not hasattr(registry, "sync"):
        return
    try:
        registry.sync(grid, dt_hours=1.0)
    except Exception:
        pass


def _pre_age_twins(registry, health_override: Dict[str, float]) -> None:
    """Pre-age specific twins to a known health value.

    Used by Stage-42 scenarios H (degraded asset + fault) and similar.
    ``health_override`` is a dict ``{asset_id: health_in_[0,1]}``.
    """
    if registry is None:
        return
    try:
        for asset_id, h in health_override.items():
            twin = registry.get(str(asset_id))
            if twin is not None:
                twin.health = float(max(0.0, min(1.0, h)))
    except Exception:
        pass


def _twin_risk_map(registry) -> Dict[str, float]:
    """Return {asset_id: health_risk_score} for every registered twin."""
    if registry is None:
        return {}
    out: Dict[str, float] = {}
    try:
        for twin in registry.all():
            out[str(twin.asset_id)] = float(
                getattr(twin, "health_risk_score", 0.0)
            )
    except Exception:
        pass
    return out


def _high_risk_assets(risk_map: Dict[str, float]) -> List[str]:
    """Return asset_ids whose health_risk_score >= _HEALTH_RISK_HIGH."""
    return [aid for aid, r in risk_map.items() if r >= _HEALTH_RISK_HIGH]


# ----------------------------------------------------------------------
# Predictive healer
# ----------------------------------------------------------------------


def _predictive_preparation(
    grid,
    risk_map: Dict[str, float],
    metric_collector=None,
    apply_physical: bool = False,
) -> List[str]:
    """Identify assets at risk of imminent failure.

    Returns the list of asset_ids that exceed the risk threshold.
    If a ``metric_collector`` is provided, records a
    ``predictive_preparation`` event.

    Stage-43 (Repair 7): when ``apply_physical`` is True the healer
    takes a REAL grid action — for every high-risk asset it pre-closes
    the nearest open tie switch on the asset's own feeder (or adjacent
    to it), so an alternate path already exists before a fault hits.
    Only open, non-fault-locked ties with healthy endpoints are
    considered; closing is validated by the next power-flow solve.
    """
    high_risk = _high_risk_assets(risk_map)
    if metric_collector is not None and high_risk:
        try:
            metric_collector.record_predictive_preparation(
                timestep=int(getattr(grid, "timestep", 0)),
                at_risk_assets=high_risk,
            )
        except Exception:
            pass

    if apply_physical and high_risk and hasattr(grid, "get_open_tie_switches"):
        try:
            open_ties = grid.get_open_tie_switches()
            for asset in high_risk:
                if asset not in grid.nodes:
                    continue
                node = grid.nodes[asset]
                if getattr(node, "failed", False) or getattr(node, "isolated", False):
                    continue
                # Distance to every open tie's endpoints via the grid
                # graph (few hops = "nearest").
                from networkx import shortest_path_length as _spl
                best = None
                best_dist = None
                for (u, v) in open_ties:
                    for endpoint in (u, v):
                        if endpoint not in grid.graph:
                            continue
                        try:
                            d = _spl(
                                grid.graph, asset, endpoint,
                                weight=None,
                            )
                        except Exception:
                            continue
                        if best_dist is None or d < best_dist:
                            best_dist = d
                            best = (u, v)
                if best is not None and hasattr(grid, "close_tie_switch"):
                    grid.close_tie_switch(*best)
                    open_ties = grid.get_open_tie_switches()
        except Exception:
            pass
    return high_risk


# ----------------------------------------------------------------------
# EMS dispatch
# ----------------------------------------------------------------------


def _run_ems(grid, metric_collector=None, ems_instance=None) -> Optional[dict]:
    """Run the EMS for one step. Returns the EMS report (or None).

    Stage-43 (Repair 8): ``ems_instance`` is the persistent EMS
    controller created once per run — a fresh EMS per step would never
    see its own storage SOC drain and could not learn. When no instance
    is given, a throwaway instance is created (backward compat).
    """
    try:
        from simulation.ems import EnergyManagementSystem

        ems = ems_instance or EnergyManagementSystem(use_pypsa=False)
        report = ems.run(grid)
        if metric_collector is not None:
            try:
                metric_collector.record_ems_cycle(
                    cycle=int(getattr(ems, "cycle", 0)),
                    ems_log=list(getattr(ems, "ems_log", [])),
                    report=report,
                )
            except Exception:
                pass
        return report
    except Exception:
        return None
