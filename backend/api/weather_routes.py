"""
weather_routes.py — FastAPI routes for the weather engine.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request  # type: ignore
from pydantic import BaseModel  # type: ignore

from weather.weather_engine import WeatherState

weather_router = APIRouter(prefix="/weather")


class WeatherSetRequest(BaseModel):
    state: str


def _engine(request: Request):
    w = getattr(request.app.state, "weather_engine", None)
    if w is None:
        raise HTTPException(status_code=503, detail="weather engine not initialised")
    return w


@weather_router.get("")
def weather_current(request: Request) -> dict:
    return _engine(request).snapshot()


@weather_router.post("/step")
def weather_step(request: Request) -> dict:
    """Advance the Markov chain by one step."""
    w = _engine(request)
    new_state = w.step()
    return {"state": new_state.value, "snapshot": w.snapshot()}


@weather_router.post("/set")
def weather_set(req: WeatherSetRequest, request: Request) -> dict:
    """Force-set the weather state (for scenarios / demos)."""
    try:
        st = WeatherState(req.state.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"unknown state {req.state!r}")
    w = _engine(request)
    w.set(st)
    return {"state": st.value, "snapshot": w.snapshot()}