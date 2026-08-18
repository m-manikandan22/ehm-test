"""
twin_routes.py — FastAPI routes for the digital-twin subsystem.

Why
---
A digital twin is the publication spine of the upgrade.  These
routes expose twin creation, per-step sync, per-asset drill-down,
and registry rollups — the minimum surface a research dashboard
needs.

DI discipline
-------------
Every endpoint reads the singleton ``TwinRegistry`` from
``request.app.state.twin_registry``. If it is missing we return 503
rather than silently building a temporary registry, because the
temporary registry would never persist between requests and would
not be the one ``/simulate`` is updating.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request  # type: ignore

logger = logging.getLogger(__name__)
twin_router = APIRouter(prefix="/twins")


def _registry(request: Request):
    """Return the singleton TwinRegistry from app.state.

    Raises 503 if the registry is not wired. We do NOT silently build
    a temporary registry: a temporary registry is not what the rest of
    the app (e.g. ``/simulate``) is updating, so its data would lie.
    """
    reg = getattr(request.app.state, "twin_registry", None)
    if reg is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "twin_registry is not initialised on app.state. "
                "Ensure main.lifespan ran or POST /twins/sync first."
            ),
        )
    return reg


@twin_router.get("/summary")
def twins_summary(request: Request) -> dict:
    """Roll-up health / count / high-risk summary."""
    return _registry(request).summary()


@twin_router.get("")
def twins_list(request: Request) -> dict:
    """List all twins (asset_id only)."""
    reg = _registry(request)
    asset_ids = sorted(reg._twins.keys())
    return {"count": len(reg), "asset_ids": asset_ids}


@twin_router.get("/{asset_id}")
def twin_detail(request: Request, asset_id: str) -> dict:
    reg = _registry(request)
    twin = reg.get(asset_id)
    if twin is None:
        raise HTTPException(status_code=404, detail=f"asset_id {asset_id!r} not found")
    return twin.to_dict()


@twin_router.post("/{asset_id}/predict")
def twin_predict(
    request: Request,
    asset_id: str,
    horizon_steps: int = 24,
) -> dict:
    reg = _registry(request)
    twin = reg.get(asset_id)
    if twin is None:
        raise HTTPException(status_code=404, detail=f"asset_id {asset_id!r} not found")
    return twin.predict_failure(horizon_steps=horizon_steps)


@twin_router.post("/sync")
def twin_sync(request: Request) -> dict:
    """Tick every registered twin against the current grid state."""
    grid = getattr(request.app.state, "grid", None)
    if grid is None:
        raise HTTPException(status_code=503, detail="grid not initialised")
    reg = _registry(request)
    reg.register(grid)  # idempotent — picks up new nodes
    updated = reg.sync(grid, dt_hours=1.0)
    return {"updated": updated, "summary": reg.summary()}
