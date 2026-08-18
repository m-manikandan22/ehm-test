"""
fault_routes.py — FastAPI routes for the smart fault injector.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request  # type: ignore
from pydantic import BaseModel  # type: ignore

from faults.fault_catalog import FAULT_CATALOG, FaultType
from faults.smart_fault_injector import SmartFaultInjector
from weather.weather_engine import WeatherState

fault_router = APIRouter(prefix="/fault")


def _injector(request: Request) -> SmartFaultInjector:
    inj = getattr(request.app.state, "fault_injector", None)
    if inj is None:
        raise HTTPException(status_code=503, detail="fault injector not initialised")
    return inj


def _weather(request: Request):
    return getattr(request.app.state, "weather_engine", None)


@fault_router.get("/catalog")
def fault_catalog() -> dict:
    """Return the full fault catalog."""
    return {ft.value: f.to_dict() for ft, f in FAULT_CATALOG.items()}


class InjectRequest(BaseModel):
    apply: bool = False
    max_events: int = 5
    state: str | None = None  # optional override of the weather state


@fault_router.post("/inject_smart")
def fault_inject_smart(req: InjectRequest, request: Request) -> dict:
    """Sample context-aware faults; optionally apply them."""
    grid = getattr(request.app.state, "grid", None)
    if grid is None:
        raise HTTPException(status_code=503, detail="grid not initialised")
    inj = _injector(request)
    w = _weather(request)
    state = WeatherState(req.state) if req.state else (w.state if w else WeatherState.SUNNY)
    factors = w.get_factors() if w else None
    events = inj.inject(state, grid, factors=factors, max_events=req.max_events)
    applied: list[str] = []
    if req.apply and events:
        applied = inj.apply(grid, events)
    return {
        "weather_state": state.value,
        "events": [e.to_dict() for e in events],
        "applied": applied,
    }