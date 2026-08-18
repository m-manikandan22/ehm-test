"""
metrics_routes.py — IEEE 1366 + grid KPI + forecast metric endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request  # type: ignore
from pydantic import BaseModel  # type: ignore
from typing import List, Optional

from metrics import (
    saifi, saidi, caidi, maifi, asai, ens_mwh,
    aens_mwh_per_customer, acci, asidi, asifi,
    mae, rmse, mape,
    voltage_stability_index, frequency_stability_index,
    renewable_penetration_pct, battery_utilisation_pct,
    system_reliability_index,
    compute_all,
)
from metrics.carbon_economic import compute_step_cost, VOLL_USD_PER_MWH

metrics_router = APIRouter(prefix="/metrics")


class IEEE1366Request(BaseModel):
    customers_served: List[float]
    sustained_interruptions: List[float]
    customer_minutes_interrupted: Optional[List[float]] = None
    momentary_interruptions: Optional[List[float]] = None
    customer_hours_available: Optional[List[float]] = None
    customer_hours_demanded: Optional[List[float]] = None
    load_mw: Optional[List[float]] = None
    outage_minutes: Optional[List[float]] = None


@metrics_router.get("/full")
def metrics_full(request: Request) -> dict:
    """Return all metrics computed from the current grid."""
    grid = getattr(request.app.state, "grid", None)
    if grid is None:
        raise HTTPException(status_code=503, detail="grid not initialised")
    nodes = list(grid.nodes.values())
    return {
        "voltage_stability": voltage_stability_index(nodes),
        "frequency_stability": frequency_stability_index(nodes),
        "renewable_penetration_pct": renewable_penetration_pct(nodes),
        "battery_utilisation_pct": battery_utilisation_pct(nodes),
        "system_reliability_index": system_reliability_index(nodes),
        "n_nodes": len(nodes),
        "n_failed": sum(1 for n in nodes if getattr(n, "failed", False)),
    }


@metrics_router.post("/ieee1366")
def metrics_ieee1366(req: IEEE1366Request) -> dict:
    """Compute IEEE 1366 indices from the provided arrays."""
    s = saifi(req.customers_served, req.sustained_interruptions)
    out: dict = {"saifi": s}
    if req.customer_minutes_interrupted is not None:
        sd = saidi(req.customer_minutes_interrupted, req.customers_served)
        out["saidi"] = sd
        out["caidi"] = caidi(sd, s)
    if req.momentary_interruptions is not None:
        out["maifi"] = maifi(req.momentary_interruptions, req.customers_served)
    if (req.customer_hours_available is not None
            and req.customer_hours_demanded is not None):
        out["asai"] = asai(req.customer_hours_available, req.customer_hours_demanded)
    if req.load_mw is not None and req.outage_minutes is not None:
        ens = ens_mwh(req.load_mw, req.outage_minutes)
        out["ens_mwh"] = ens
        n = sum(req.customers_served)
        out["aens_mwh_per_customer"] = aens_mwh_per_customer(ens, n)
        out["acci"] = acci(ens, n)
    return out


class ForecastMetricsRequest(BaseModel):
    actual: List[float]
    predicted: List[float]


@metrics_router.post("/forecast")
def metrics_forecast(req: ForecastMetricsRequest) -> dict:
    return {
        "mae": mae(req.actual, req.predicted),
        "rmse": rmse(req.actual, req.predicted),
        "mape": mape(req.actual, req.predicted),
    }


@metrics_router.post("/registry/run")
def metrics_registry_run(payload: dict) -> dict:
    """Run every registered metric over the given payload."""
    return compute_all(payload)


# ----------------------------------------------------------------------
# M5 (EHM upgrade) — carbon emission + economic cost endpoints.
# ----------------------------------------------------------------------


@metrics_router.get("/carbon")
def metrics_carbon(request: Request) -> dict:
    """Carbon emission rollup for the current grid (kg CO₂-equivalent)."""
    grid = getattr(request.app.state, "grid", None)
    if grid is None:
        raise HTTPException(status_code=503, detail="grid not initialised")
    return compute_step_cost(grid).to_dict()


@metrics_router.get("/economic")
def metrics_economic(request: Request) -> dict:
    """Economic cost rollup for the current grid ($ / step)."""
    grid = getattr(request.app.state, "grid", None)
    if grid is None:
        raise HTTPException(status_code=503, detail="grid not initialised")
    cost = compute_step_cost(grid)
    out = cost.to_dict()
    out["voll_usd_per_mwh"] = VOLL_USD_PER_MWH
    return out


class CarbonSeriesEntry(BaseModel):
    carbon_kg: float
    economic_usd: float
    timestep: int


@metrics_router.post("/carbon_series")
def metrics_carbon_series(entries: List[CarbonSeriesEntry]) -> dict:
    """Sum carbon / economic cost across a series of steps."""
    total_carbon = sum(e.carbon_kg for e in entries)
    total_econ = sum(e.economic_usd for e in entries)
    return {
        "total_carbon_kg": float(total_carbon),
        "total_economic_usd": float(total_econ),
        "n_steps": len(entries),
    }