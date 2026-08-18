"""
city_routes.py — FastAPI routes for the procedural city generator and
AI-assisted grid planner.

Mounted by `api/routes.py` via `app.include_router(city_router)`.
All endpoints are additive — none of the existing `/state`,
`/simulate`, `/event`, `/predict`, `/action`, `/reset`, `/health`,
`/fault_analysis`, `/islanding_analysis`, `/dc_state`, `/attack*`,
or `/ai/suggestions` routes are modified.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from city.city_generator import CityGenerator
from city.city_profile import CityProfile
from city.layout import city_layout
from planning.ai_planner import AIPlanner, PlannerConfig


city_router = APIRouter(prefix="/city", tags=["city"])
planner_router = APIRouter(prefix="/planner", tags=["planner"])


class CityRequest(BaseModel):
    population: int = Field(100_000, ge=1_000, le=10_000_000)
    area_km2: float = Field(50.0, gt=0.1, le=10_000.0)
    renewable_share: float = Field(0.30, ge=0.0, le=1.0)
    industrial_pct: float = Field(0.20, ge=0.0, le=1.0)
    commercial_pct: float = Field(0.15, ge=0.0, le=1.0)
    critical_infra_pct: float = Field(0.02, ge=0.0, le=1.0)
    ev_penetration: float = Field(0.05, ge=0.0, le=1.0)
    density: Optional[float] = None
    seed: int = Field(42, ge=0)


class CityResponse(BaseModel):
    profile: Dict[str, Any]
    expected_load_mw: float
    expected_building_count: int
    expected_feeder_count: int
    expected_primary_substation_count: int
    expected_transmission_tower_count: int
    expected_bess_count: int
    expected_renewable_mw: float


# ---------------------------------------------------------------------------
# /city/profile  — pure estimator (no SmartGrid construction)
# ---------------------------------------------------------------------------

@city_router.get("/profile")
def city_profile_defaults() -> dict:
    p = CityProfile()
    return _profile_payload(p)


@city_router.post("/profile")
def city_profile_estimate(req: CityRequest) -> dict:
    try:
        profile = CityProfile.from_dict(req.model_dump())
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _profile_payload(profile)


def _profile_payload(p: CityProfile) -> dict:
    return {
        "profile": p.to_dict(),
        "expected_load_mw": p.expected_load_mw(),
        "expected_building_count": p.expected_building_count(),
        "expected_feeder_count": p.expected_feeder_count(),
        "expected_primary_substation_count": p.expected_primary_substation_count(),
        "expected_transmission_tower_count": p.expected_transmission_tower_count(),
        "expected_bess_count": p.expected_bess_count(),
        "expected_renewable_mw": p.expected_renewable_mw(),
    }


# ---------------------------------------------------------------------------
# /city/generate  — construct a SmartGrid from a profile
# ---------------------------------------------------------------------------

@city_router.post("/generate")
def city_generate(req: CityRequest, request: Request) -> dict:
    """Construct a fresh procedural city and *replace* the live SmartGrid.

    Why replace?  The grid is a singleton in app.state; replacing it is
    the simplest, most explicit way to wire the new topology through
    every other module (SCADA, EMS, RL, twin registry) on the next
    simulation step.  Replacement is wrapped in `grid_lock` to keep the
    CPS pipeline race-free.

    Side effect: the singleton ``TwinRegistry`` (if wired) is rebuilt
    against the new topology. Without this the registry would carry
    stale asset IDs after every regenerate. See
    ``digital_twin.twin_registry.TwinRegistry.rebuild``.
    """
    from api.routes import grid_lock
    profile = CityProfile.from_dict(req.model_dump())
    generator = CityGenerator(profile)
    new_grid = generator.generate()
    with grid_lock:
        request.app.state.grid = new_grid
        # Rebuild the twin registry so it tracks the new topology.
        twin_reg = getattr(request.app.state, "twin_registry", None)
        if twin_reg is not None:
            twin_reg.rebuild(new_grid)
    return {
        "message": "City generated",
        "profile": profile.to_dict(),
        "node_counts": new_grid._city_report.node_counts,
        "edge_count": new_grid._city_report.edge_count,
        "expected_load_mw": new_grid._city_report.expected_load_mw,
        "twin_registry_rebuilt": True,
    }


# ---------------------------------------------------------------------------
# /city/report  — current grid's generation report (if any)
# ---------------------------------------------------------------------------

@city_router.get("/report")
def city_report(request: Request) -> dict:
    grid = request.app.state.grid
    report = getattr(grid, "_city_report", None)
    if report is None:
        return {"has_report": False}
    return {"has_report": True, "report": report.to_dict()}


# ---------------------------------------------------------------------------
# /city/layout  — roads, zones, buildings for the M5 visualiser
# ---------------------------------------------------------------------------

@city_router.get("/layout")
def city_layout_endpoint(request: Request) -> dict:
    """Return roads, zone polygons, and per-node building summaries.

    Backward-compatible: returns ``{"has_layout": False}`` for grids that
    were not produced by ``CityGenerator``.
    """
    grid = request.app.state.grid
    return city_layout(grid)


# ---------------------------------------------------------------------------
# /planner/run  — run the AI planner on the current grid
# ---------------------------------------------------------------------------

class PlannerRequest(BaseModel):
    w_outage: float = 1.0
    w_voltage_drop: float = 1.0
    w_power_loss: float = 1.0
    w_reliability: float = 2.0
    w_restoration: float = 1.0
    max_iterations: int = 8
    eps: float = 1e-3


@planner_router.post("/run")
def planner_run(req: PlannerRequest, request: Request) -> dict:
    grid = request.app.state.grid
    config = PlannerConfig(
        w_outage=req.w_outage,
        w_voltage_drop=req.w_voltage_drop,
        w_power_loss=req.w_power_loss,
        w_reliability=req.w_reliability,
        w_restoration=req.w_restoration,
        max_iterations=req.max_iterations,
        eps=req.eps,
    )
    planner = AIPlanner(grid, config=config)
    actions = planner.plan()
    return {
        "actions": [a.to_dict() for a in actions],
        "count": len(actions),
    }
