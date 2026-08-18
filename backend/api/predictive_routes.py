"""
predictive_routes.py — FastAPI routes for predictive self-healing.

Additive — these endpoints sit alongside the existing ``/fault``,
``/microgrid``, ``/twins`` routes.  None of them mutate the grid; they
return the predictive healer recommendation as JSON so the dashboard
can either display or apply it.

Endpoints
---------
GET  /self_healing/risks
     Returns RiskAssessment list — assets at risk right now.
POST /self_healing/recommend
     Returns the list of PredictiveAction records to take.
POST /self_healing/run
     Convenience: run the full pipeline + emit a JSON envelope.
GET  /reliability/history
     Returns the per-step IEEE 1366 time-series from the recorder.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from self_healing.predictor import PredictiveSelfHealer
from self_healing.recorder import ReliabilityRecorder

predictive_router = APIRouter(prefix="/self_healing")
reliability_router = APIRouter(prefix="/reliability")

# Process-global healer instance (re-created per-call config).
_HEALER: PredictiveSelfHealer = PredictiveSelfHealer()
_RECORDER: ReliabilityRecorder = ReliabilityRecorder()


def _registry(request: Request):
    """Return the singleton TwinRegistry from app.state, or raise 503.

    We do NOT silently build a temporary registry: a temporary registry
    is not updated by ``/simulate``, so its data would lie. The lifespan
    hook in ``main.py`` builds the singleton at startup.
    """
    reg = getattr(request.app.state, "twin_registry", None)
    if reg is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "twin_registry is not initialised on app.state. "
                "Ensure main.lifespan ran before calling this endpoint."
            ),
        )
    return reg


class HealRequest(BaseModel):
    risk_threshold: float = 0.40
    max_actions: int = 5


@predictive_router.get("/risks")
def self_healing_risks(request: Request,
                        risk_threshold: float = 0.40) -> dict:
    grid = getattr(request.app.state, "grid", None)
    if grid is None:
        raise HTTPException(status_code=503, detail="grid not initialised")
    twins = _registry(request)
    healer = PredictiveSelfHealer(risk_threshold=risk_threshold)
    risks = healer.assess(grid, twins)
    return {
        "count": len(risks),
        "risks": [r.to_dict() for r in risks],
    }


@predictive_router.post("/recommend")
def self_healing_recommend(req: HealRequest, request: Request) -> dict:
    grid = getattr(request.app.state, "grid", None)
    if grid is None:
        raise HTTPException(status_code=503, detail="grid not initialised")
    twins = _registry(request)
    healer = PredictiveSelfHealer(
        risk_threshold=req.risk_threshold,
        max_actions=req.max_actions,
    )
    risks = healer.assess(grid, twins)
    actions = healer.recommend(grid, risks)
    return {
        "risk_count": len(risks),
        "action_count": len(actions),
        "actions": [a.to_dict() for a in actions],
    }


@predictive_router.post("/run")
def self_healing_run(req: HealRequest, request: Request) -> dict:
    grid = getattr(request.app.state, "grid", None)
    if grid is None:
        raise HTTPException(status_code=503, detail="grid not initialised")
    twins = _registry(request)
    healer = PredictiveSelfHealer(
        risk_threshold=req.risk_threshold,
        max_actions=req.max_actions,
    )
    return healer.run(grid, twins)


# ----------------------------------------------------------------------
# Reliability time-series endpoints
# ----------------------------------------------------------------------


@reliability_router.get("/history")
def reliability_history() -> dict:
    return _RECORDER.summary()


class ReliabilityStepRequest(BaseModel):
    timestep: int = 0
    load_mw: float = 0.0
    notes: str = ""


@reliability_router.post("/record")
def reliability_record(req: ReliabilityStepRequest, request: Request) -> dict:
    grid = getattr(request.app.state, "grid", None)
    if grid is None:
        raise HTTPException(status_code=503, detail="grid not initialised")
    sample = _RECORDER.record_from_grid(
        grid, timestep=req.timestep,
        load_mw=req.load_mw, notes=req.notes,
    )
    return sample.to_dict()


@reliability_router.post("/reset")
def reliability_reset() -> dict:
    global _RECORDER
    _RECORDER = ReliabilityRecorder()
    return {"reset": True}
