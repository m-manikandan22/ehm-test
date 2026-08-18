"""
improvement_routes.py — self-improvement endpoints (evaluator + redesigner).
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request  # type: ignore
from pydantic import BaseModel  # type: ignore

logger = logging.getLogger(__name__)

from improvement.evaluator import SimulationEvaluator
from improvement.redesigner import Redesigner
from improvement.autonomous import AutonomousImprovementLoop, AutonomousConfig

improvement_router = APIRouter(prefix="/improvement")


# Process-global evaluator + redesign history (simple, not persisted).
_evaluator: Optional[SimulationEvaluator] = None
_history: list = []
_autonomous: Optional[AutonomousImprovementLoop] = None


def _ev() -> SimulationEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = SimulationEvaluator()
    return _evaluator


def _autonomous_loop() -> AutonomousImprovementLoop:
    global _autonomous
    if _autonomous is None:
        _autonomous = AutonomousImprovementLoop()
        _autonomous.attach_evaluator(_ev())
    return _autonomous


@improvement_router.get("/snapshot")
def improvement_snapshot() -> dict:
    return _ev().summary()


class RunRequest(BaseModel):
    steps: int = 50


@improvement_router.post("/run")
def improvement_run(req: RunRequest, request: Request) -> dict:
    """Run a small simulation, then apply the redesigner.

    Returns before/after metrics and the redesign report.
    """
    grid = getattr(request.app.state, "grid", None)
    if grid is None:
        raise HTTPException(status_code=503, detail="grid not initialised")
    ev = _ev()
    # Snapshot each step.
    # Note: solver failures used to be silently swallowed here, which
    # contaminated metrics. We now log and surface the failure count
    # so the caller can decide whether to invalidate the run.
    from improvement.evaluator import SimulationEvaluator
    step_failures = 0
    for t in range(req.steps):
        try:
            grid.update_generation()
            grid.update_power_flow()
        except Exception as exc:  # noqa: BLE001
            step_failures += 1
            logger.warning(
                "improvement_routes: step %s solver failed: %r", t, exc,
            )
        ev.record_step(SimulationEvaluator.snapshot_from_grid(grid, t))
    before = ev.summary()

    # Apply the redesigner.
    redesigner = Redesigner()
    report = redesigner.propose(grid, before)
    _history.append(report.to_dict())
    return {
        "before": before,
        "report": report.to_dict(),
        "history_size": len(_history),
        "step_failures": step_failures,
        "invalid": step_failures > 0,
    }


@improvement_router.get("/history")
def improvement_history() -> dict:
    return {"history": _history, "count": len(_history)}


# ----------------------------------------------------------------------
# Autonomous self-improvement loop (additive)
# ----------------------------------------------------------------------


class AutonomousRequest(BaseModel):
    reliability_threshold: float = 0.85
    ens_step_threshold: float = 0.5
    window: int = 20
    cooldown_steps: int = 50


@improvement_router.get("/autonomous/status")
def autonomous_status() -> dict:
    return _autonomous_loop().status()


@improvement_router.post("/autonomous/run")
def autonomous_step(req: AutonomousRequest, request: Request) -> dict:
    """Run one step of the autonomous loop against the live grid."""
    grid = getattr(request.app.state, "grid", None)
    if grid is None:
        raise HTTPException(status_code=503, detail="grid not initialised")
    loop = _autonomous_loop()
    # Allow the caller to retune the policy in-line.
    loop.config = AutonomousConfig(
        reliability_threshold=req.reliability_threshold,
        ens_step_threshold=req.ens_step_threshold,
        window=req.window,
        cooldown_steps=req.cooldown_steps,
        last_trigger_step=loop.config.last_trigger_step,
    )
    decision = loop.step(grid, getattr(grid, "timestep", 0))
    return decision.to_dict()


@improvement_router.post("/autonomous/reset")
def autonomous_reset() -> dict:
    loop = _autonomous_loop()
    loop.reset()
    return {"reset": True}