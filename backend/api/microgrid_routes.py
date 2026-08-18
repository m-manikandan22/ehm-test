"""
microgrid_routes.py — FastAPI routes for the microgrid controller.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request  # type: ignore
from pydantic import BaseModel  # type: ignore

microgrid_router = APIRouter(prefix="/microgrid")


def _controller(request: Request):
    c = getattr(request.app.state, "microgrid_controller", None)
    if c is None:
        raise HTTPException(status_code=503, detail="microgrid controller not initialised")
    return c


class FormRequest(BaseModel):
    faulted_nodes: List[str] = []


@microgrid_router.post("/form")
def microgrid_form(req: FormRequest, request: Request) -> dict:
    """Identify healthy microgrid islands around surviving generators."""
    grid = getattr(request.app.state, "grid", None)
    if grid is None:
        raise HTTPException(status_code=503, detail="grid not initialised")
    c = _controller(request)
    islands = c.form_islands(grid, req.faulted_nodes)
    return {"islands": islands, "count": len(islands)}


@microgrid_router.get("/list")
def microgrid_list(request: Request) -> dict:
    """Return summary health for every known island."""
    c = _controller(request)
    grid = getattr(request.app.state, "grid", None)
    if grid is None:
        raise HTTPException(status_code=503, detail="grid not initialised")
    out = []
    for iid in c.islands.keys():
        out.append(c.island_health(grid, iid))
    return {"islands": out}


@microgrid_router.post("/reconnect")
def microgrid_reconnect(request: Request) -> dict:
    grid = getattr(request.app.state, "grid", None)
    if grid is None:
        raise HTTPException(status_code=503, detail="grid not initialised")
    c = _controller(request)
    cleared = c.reconnect(grid)
    return {"cleared": cleared}