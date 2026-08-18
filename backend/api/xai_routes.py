"""
xai_routes.py — explainable-AI endpoints for the RL agent.

Why
---
The publication-grade requirement (Part 11) is that the dashboard
must answer "why did the agent choose this action?"  These routes
expose that answer.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request  # type: ignore
from pydantic import BaseModel  # type: ignore

xai_router = APIRouter(prefix="/explain")


def _agent(request: Request):
    a = getattr(request.app.state, "advanced_agent", None)
    if a is None:
        raise HTTPException(status_code=503, detail="advanced agent not initialised")
    return a


def _grid(request: Request):
    g = getattr(request.app.state, "grid", None)
    if g is None:
        raise HTTPException(status_code=503, detail="grid not initialised")
    return g


class ExplainRequest(BaseModel):
    include_xai: bool = True


@xai_router.post("/decision")
def explain_decision(req: ExplainRequest, request: Request) -> dict:
    """Run the advanced agent on the current grid and return the decision."""
    from simulation.grid import SmartGrid
    grid = _grid(request)
    state = grid.get_state() if isinstance(grid, SmartGrid) else {}
    agent = _agent(request)
    action_id = agent.select_action(grid, state)
    out = {"action_id": action_id}
    if req.include_xai:
        report = agent.explain_last()
        out["xai"] = report.to_dict() if report else {}
    return out


@xai_router.get("/last")
def explain_last(request: Request) -> dict:
    """Return the XAI report from the most recent agent decision."""
    agent = _agent(request)
    report = agent.explain_last()
    if report is None:
        raise HTTPException(status_code=404, detail="no decision has been explained yet")
    return report.to_dict()