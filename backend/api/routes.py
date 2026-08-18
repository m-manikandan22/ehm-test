"""
routes.py — FastAPI route definitions for the Smart Grid API.

Uses FastAPI dependency injection (Request → app.state) instead of
mutable module-level globals, which eliminates NoneType type errors.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional, TYPE_CHECKING
from fastapi import APIRouter, HTTPException, Request  # type: ignore
from pydantic import BaseModel  # type: ignore

logger = logging.getLogger(__name__)

from simulation.grid import SmartGrid  # type: ignore
from simulation.scada import ScadaControlCenter  # type: ignore
from simulation.ems import EnergyManagementSystem  # type: ignore
from models.rl_agent import ACTIONS, N_ACTIONS  # type: ignore
from models.attack_detector import AttackDetector, AttackType  # type: ignore
# M1 (EHM upgrade) — procedural city + AI planner sub-routers.
from api.city_routes import city_router, planner_router  # type: ignore
# M2 (EHM upgrade) — digital twin, weather, smart faults, microgrid.
from api.twin_routes import twin_router  # type: ignore
from api.weather_routes import weather_router  # type: ignore
from api.fault_routes import fault_router  # type: ignore
from api.microgrid_routes import microgrid_router  # type: ignore
# M3 (EHM upgrade) — advanced RL + XAI.
from api.xai_routes import xai_router  # type: ignore
# M4 (EHM upgrade) — IEEE 1366 metrics + self-improvement.
from api.metrics_routes import metrics_router  # type: ignore
from api.improvement_routes import improvement_router  # type: ignore
# Predictive self-healing + reliability recording (additive).
from api.predictive_routes import predictive_router, reliability_router  # type: ignore

if TYPE_CHECKING:
    from models.lstm_model import DemandForecaster  # type: ignore
    from models.fault_detector import FaultDetector  # type: ignore

router = APIRouter()
grid_lock = threading.Lock()

# M1 sub-routers (additive — do not modify the legacy `/state`,
# `/simulate`, `/event`, etc. endpoints).
router.include_router(city_router)
router.include_router(planner_router)
# M2 sub-routers (additive).
router.include_router(twin_router)
router.include_router(weather_router)
router.include_router(fault_router)
router.include_router(microgrid_router)
router.include_router(xai_router)
router.include_router(metrics_router)
router.include_router(improvement_router)
# M5 (EHM upgrade) — predictive self-healing + reliability time-series.
router.include_router(predictive_router)
router.include_router(reliability_router)


# -----------------------------------------------------------------------
# Dependency helpers — pull singletons from app.state
# -----------------------------------------------------------------------

def get_grid(request: Request) -> SmartGrid:
    return request.app.state.grid


def get_scada(request: Request) -> ScadaControlCenter:
    return request.app.state.scada


def get_ems(request: Request) -> EnergyManagementSystem:
    return request.app.state.ems


def get_forecaster(request: Request):
    return get_scada(request).forecaster


def get_fault_detector(request: Request):
    return get_scada(request).fault_detector


def get_attack_detector(request: Request) -> AttackDetector:
    return request.app.state.attack_detector


# -----------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------

def _apply_action(action_name: str, state_before: dict, grid: SmartGrid, scada: ScadaControlCenter) -> str:
    """Apply an action using SCADA dispatch logic."""
    return scada._dispatch_control_signal(action_name, state_before, grid)


# -----------------------------------------------------------------------
# Request / Response Models
# -----------------------------------------------------------------------

class EventRequest(BaseModel):
    type: str                    # "failure" | "storm" | "clear_storm" | "demand" | "generation" | "restore"
    node_id: Optional[str] = None
    amount: Optional[float] = None


class ActionRequest(BaseModel):
    action_id: int               # 0–4

class NodeRequest(BaseModel):
    type: str                    # "generator" | "substation" | "house"
    position: list[float]        # [x, y]

class PositionRequest(BaseModel):
    x: float
    y: float

class EdgeRequest(BaseModel):
    source: str
    target: str

class NodeTargetRequest(BaseModel):
    node_id: str


# -----------------------------------------------------------------------
# GET /health
# -----------------------------------------------------------------------

@router.get("/health")
def health_check() -> dict:
    return {"status": "ok", "message": "Smart Grid API is running"}


# -----------------------------------------------------------------------
# GET /state
# -----------------------------------------------------------------------

@router.get("/state")
def get_state(request: Request) -> dict:
    """Return the full current grid state without advancing simulation."""
    grid: SmartGrid = get_grid(request)
    return grid.get_state()


# -----------------------------------------------------------------------
# POST /simulate
# -----------------------------------------------------------------------

@router.post("/simulate")
def simulate_step(request: Request) -> dict:
    """
    Advance simulation by 1 timestep.

    Real CPS execution order (enforced here):
      1. grid.update_generation()  — Generation (solar + wind + time-based curves)
      2. grid.update_power_flow()  — Physics FIRST (backward/forward sweep)
      3. ems.run(grid)              — EMS reacts to REAL imbalance (storage dispatch)
      4. grid.update_power_flow()  — Recompute after EMS
      5. scada.execute_control_loop() — SCADA AI (fault detection, FLISR rerouting)
      6. grid.update_power_flow()  — Final recompute (after reroute)

    EMS runs AFTER physics so it reacts to real imbalance (not pre-empt it).
    EMS uses partial control (50 % absorption) so imbalance remains visible.
    """
    with grid_lock:
        grid:  SmartGrid             = get_grid(request)
        ems:   EnergyManagementSystem = get_ems(request)
        scada: ScadaControlCenter    = get_scada(request)

        # ── 1. Generation (solar + wind) ──
        grid.update_generation()

        # ── 2. Physics FIRST ──
        grid.update_power_flow()

        # ── 3. EMS reacts to REAL imbalance ──
        ems_report = ems.run(grid)

        # ── 4. Recompute after EMS ──
        grid.update_power_flow()

        # ── 5. SCADA + FLISR ──
        scada_report = scada.execute_control_loop(grid, ems)

        # ── 6. Final recompute (after reroute) ──
        grid.update_power_flow()

        # ── M2: sync digital twins against the latest physical state.
        # Non-breaking — if no twin_registry is wired (legacy callers),
        # this is a no-op. ──
        twin_reg = getattr(request.app.state, "twin_registry", None)
        if twin_reg is not None:
            twin_reg.register(grid)  # idempotent — picks up new nodes
            twin_reg.sync(grid, dt_hours=1.0)

        # ── M5: IEEE 1366 reliability time-series recording.
        # Lazily import the recorder so legacy callers that don't use
        # the predictive routes don't pull it in.
        #
        # IMPORTANT: this used to swallow ALL exceptions silently which
        # masked solver bugs. We now log any failure and continue — but
        # the error is visible. If the recorder is unavailable, we
        # leave the dict empty rather than faking a sample.
        reliability_sample: dict = {}
        reliability_error: Optional[str] = None
        try:
            from api.predictive_routes import _RECORDER as _RELIABILITY_RECORDER
            step_idx = int(grid.timestep if hasattr(grid, "timestep") else 0)
            _sample = _RELIABILITY_RECORDER.record_from_grid(
                grid,
                timestep=step_idx,
                notes="auto:simulate",
            )
            reliability_sample = _sample.to_dict()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Reliability recorder failed at step %s: %r",
                getattr(grid, "timestep", "?"),
                exc,
            )
            reliability_error = repr(exc)

        return {
            "grid": grid.get_state(),
            "ems": {
                "cycle":            ems_report["cycle"],
                "balance_mw":       ems_report["balance"],
                "total_gen":        ems_report["total_gen"],
                "total_load":       ems_report["total_load"],
                "absorption_ratio": ems_report["absorption_ratio"],
                "log":              ems_report["log"],
                "message":          ems_report["message"],
            },
            "ai": {
                "predicted_load":     scada_report["predicted_load"],
                "decision":           scada_report["decision"],
                "action_result":      scada_report["action_result"],
                "flisr_log":          scada_report.get("flisr_log", []),
                "fault_analysis":     scada_report["fault_analysis"],
                "cycle_id":           scada_report["cycle_id"],
                "timestamp":          scada_report["timestamp"],
                "hour_of_day":        scada_report["hour_of_day"],
                "control_divergence": scada_report["control_divergence"],
                "overload_warnings":  scada_report.get("overload_warnings", []),
                # M5 (EHM upgrade) — expose the rich modular RL state so the
                # XAI panel and the advanced RL agent can consume it.
                "state_features":     scada_report.get("state_features", {}),
                "action_mask":        scada_report.get("action_mask", []),
            },
            # M5 (EHM upgrade) — latest reliability snapshot, so the
            # front-end can plot SAIDI/SAIFI progression without polling
            # a separate endpoint.
            "reliability": reliability_sample,
            "reliability_error": reliability_error,
        }




# -----------------------------------------------------------------------
# Grid Construction APIs (User Controlled)
# -----------------------------------------------------------------------

@router.post("/add_node")
def add_user_node(req: NodeRequest, request: Request) -> dict:
    grid: SmartGrid = get_grid(request)
    try:
        x, y = req.position[0], req.position[1]
        nid = grid.add_user_node(req.type, x, y)
        return {"message": f"Added node: {nid['id']}", "grid": grid.get_state()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/nodes/{node_id}/move")
def move_user_node(node_id: str, req: PositionRequest, request: Request) -> dict:
    grid: SmartGrid = get_grid(request)
    try:
        grid.move_node(node_id, req.x, req.y)
        return {"message": f"Moved {node_id}", "grid": grid.get_state()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/nodes/{node_id}")
def delete_user_node(node_id: str, request: Request) -> dict:
    grid: SmartGrid = get_grid(request)
    try:
        msg = grid.delete_node(node_id)
        return {"message": msg, "grid": grid.get_state()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/connect")
def add_user_edge(req: EdgeRequest, request: Request) -> dict:
    grid: SmartGrid = get_grid(request)
    try:
        msg = grid.add_user_edge(req.source, req.target)
        return {"message": msg, "grid": grid.get_state()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/cut_edge")
def cut_user_edge(req: EdgeRequest, request: Request) -> dict:
    grid: SmartGrid = get_grid(request)
    try:
        msg = grid.cut_user_edge(req.source, req.target)
        return {"message": msg, "grid": grid.get_state()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/fail_node")
def fail_user_node(req: NodeTargetRequest, request: Request) -> dict:
    grid: SmartGrid = get_grid(request)
    if req.node_id not in grid.nodes:
        raise HTTPException(status_code=404, detail="Node not found.")
    msg = grid.inject_failure(req.node_id)
    return {"message": msg, "grid": grid.get_state()}

@router.post("/restore_node")
def restore_user_node(req: NodeTargetRequest, request: Request) -> dict:
    grid: SmartGrid = get_grid(request)
    if req.node_id not in grid.nodes:
        raise HTTPException(status_code=404, detail="Node not found.")
    msg = grid.restore_node(req.node_id)
    return {"message": msg, "grid": grid.get_state()}

@router.post("/command/add_house")
def add_house_to_pole(req: NodeTargetRequest, request: Request) -> dict:
    grid: SmartGrid = get_grid(request)
    if req.node_id not in grid.nodes:
        raise HTTPException(status_code=404, detail="Node not found.")
    msg = grid.add_house(req.node_id)
    return {"message": msg, "grid": grid.get_state()}

@router.get("/ai/suggestions")
def get_ai_suggestions(request: Request) -> dict:
    grid: SmartGrid = get_grid(request)
    return {"suggestions": grid.suggest_tie_lines()}
    
@router.post("/ai/suggest_parent")
def post_suggest_parent(req: PositionRequest, request: Request) -> dict:
    grid: SmartGrid = get_grid(request)
    return grid.suggest_best_parent(req.x, req.y)

# -----------------------------------------------------------------------
# POST /event
# -----------------------------------------------------------------------

@router.post("/event")
def trigger_event(req: EventRequest, request: Request) -> dict:
    """
    Trigger a grid event.
    type: "failure" | "storm" | "clear_storm" | "demand" | "generation" | "restore"
    """
    grid: SmartGrid = get_grid(request)

    if req.type == "failure":
        if not req.node_id:
            raise HTTPException(status_code=400, detail="node_id required for failure event")
        try:
            msg = grid.inject_failure(req.node_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"message": msg, "grid": grid.get_state()}

    elif req.type == "storm":
        msg = grid.trigger_storm()
        return {"message": msg, "grid": grid.get_state()}

    elif req.type == "clear_storm":
        msg = grid.clear_storm()
        return {"message": msg, "grid": grid.get_state()}

    elif req.type == "demand":
        amount = req.amount if req.amount is not None else 0.2
        msg = grid.increase_demand(amount)
        return {"message": msg, "grid": grid.get_state()}

    elif req.type == "generation":
        amount = req.amount if req.amount is not None else 0.3
        msg = grid.increase_generation(amount)
        return {"message": msg, "grid": grid.get_state()}

    elif req.type == "restore":
        if not req.node_id:
            raise HTTPException(status_code=400, detail="node_id required for restore event")
        msg = grid.restore_node(req.node_id)
        return {"message": msg, "grid": grid.get_state()}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown event type: {req.type}")


# -----------------------------------------------------------------------
# GET /predict
# -----------------------------------------------------------------------

@router.get("/predict")
def predict_demand(request: Request, node_id: str = "S0") -> dict:
    """Run LSTM forecasting for a given node."""
    grid: SmartGrid = get_grid(request)
    forecaster: DemandForecaster = get_forecaster(request)
    sequence = grid.get_lstm_input(node_id)
    predicted = forecaster.predict(sequence)
    return {
        "node_id": node_id,
        "predicted_load": round(float(predicted), 4),  # type: ignore
        "sequence_length": len(sequence),
    }


# -----------------------------------------------------------------------
# POST /action
# -----------------------------------------------------------------------

@router.post("/action")
def force_action(req: ActionRequest, request: Request) -> dict:
    """Force a specific RL action (0–4)."""
    grid: SmartGrid = get_grid(request)
    scada: ScadaControlCenter = get_scada(request)

    if req.action_id < 0 or req.action_id >= N_ACTIONS:
        raise HTTPException(status_code=400, detail=f"action_id must be 0–{N_ACTIONS - 1}")

    state = grid.get_state()
    action = ACTIONS[req.action_id]
    result = _apply_action(action["name"], state, grid, scada)

    return {
        "action": action,
        "result": result,
        "grid": grid.get_state(),
    }


# -----------------------------------------------------------------------
# GET /fault_analysis
# -----------------------------------------------------------------------

@router.get("/fault_analysis")
def fault_analysis(request: Request) -> dict:
    """
    Run the AI Fault Detector across all live nodes.
    Returns per-node anomaly scores, fault types, and system health.
    """
    grid: SmartGrid     = get_grid(request)
    detector: FaultDetector = get_fault_detector(request)
    return detector.analyse(grid.nodes)


# -----------------------------------------------------------------------
# GET /islanding_analysis
# -----------------------------------------------------------------------

@router.get("/islanding_analysis")
def islanding_analysis(request: Request) -> dict:
    """
    Analyze potential microgrid formation for resilience.
    Returns viable island configurations around healthy generators.
    """
    grid: SmartGrid = get_grid(request)
    failed_nodes = [nid for nid, node in grid.nodes.items() if node.failed]
    return grid.predictive_islanding(failed_nodes)


# -----------------------------------------------------------------------
# POST /reset
# -----------------------------------------------------------------------

@router.post("/reset")
def reset_grid(request: Request) -> dict:  # type: ignore[no-redef]
    """Reset the grid to its initial state."""
    grid: SmartGrid = get_grid(request)
    msg = grid.reset()
    return {"message": msg, "grid": grid.get_state()}


# -----------------------------------------------------------------------
# POST /random_fault
# -----------------------------------------------------------------------

@router.post("/random_fault")
def random_fault(request: Request) -> dict:
    """Inject a random failure on a random healthy pole node."""
    grid: SmartGrid = get_grid(request)
    msg = grid.random_failure()
    return {"message": msg, "grid": grid.get_state()}


# -----------------------------------------------------------------------
# Item 1 — DC power flow readout
# -----------------------------------------------------------------------

@router.get("/dc_state")
def dc_state(request: Request) -> dict:
    """Return the last DC power flow result (angles, line P/I/loss, KCL)."""
    grid: SmartGrid = get_grid(request)
    return grid.get_dc_state()


# Item 2 — AC power flow readout (Newton-Raphson via pandapower)
# -----------------------------------------------------------------------

class ACRunResponse(BaseModel):
    available: bool
    converged: bool
    bus_count: int = 0
    line_count: int = 0
    state: dict = {}


@router.post("/ac_state/run")
def ac_state_run(request: Request) -> dict:
    """Run a fresh AC power flow and return the result.

    This endpoint forces a recompute (rather than serving the cached
    ``grid.ac_state``) so the frontend can pull fresh Q / V values on
    demand. Returns ``{"available": False, "reason": "..."}`` when
    pandapower is not installed or the solve fails.
    """
    grid: SmartGrid = get_grid(request)
    if not grid.ac_enabled:
        return {"available": False, "reason": "AC PF is disabled on this grid"}
    try:
        grid.update_ac_power_flow()
    except Exception as exc:  # noqa: BLE001
        logger.warning("AC PF run failed: %r", exc)
        return {"available": False, "reason": f"AC PF run failed: {exc!r}"}
    return grid.get_ac_state()


@router.get("/ac_state")
def ac_state(request: Request) -> dict:
    """Return the last AC power flow result without recomputing.

    Use ``POST /ac_state/run`` to force a fresh solve.
    """
    grid: SmartGrid = get_grid(request)
    return grid.get_ac_state()


# -----------------------------------------------------------------------
# Item 10 — Cyber-attack endpoints
# -----------------------------------------------------------------------

class AttackRequest(BaseModel):
    type:     str                # "fdia" | "replay" | "ramp"
    target:   str                # edge "u->v" or node_id
    magnitude: Optional[float] = None


@router.post("/attack")
def inject_attack(req: AttackRequest, request: Request) -> dict:
    """
    Inject a cyber attack on a node or edge. Useful for demos and for
    validating the detector. Returns the detector status.
    """
    grid: SmartGrid         = get_grid(request)
    detector: AttackDetector = get_attack_detector(request)
    try:
        atype = AttackType(req.type.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown attack type {req.type!r}. Use fdia|replay|ramp.",
        )
    record = detector.inject_attack(grid, atype, req.target, magnitude=req.magnitude)
    return {"injected": record, "status": detector.status()}


@router.get("/attack_status")
def attack_status(request: Request) -> dict:
    """Return the current detector state."""
    return get_attack_detector(request).status()


@router.post("/attack_clear")
def attack_clear(request: Request) -> dict:
    """Clear all active attacks and detections."""
    get_attack_detector(request).clear_attacks()
    return {"cleared": True}


# -----------------------------------------------------------------------
# M5 (EHM upgrade) — rich modular RL state endpoint
# -----------------------------------------------------------------------


@router.get("/ai/rich_state")
def ai_rich_state(request: Request) -> dict:
    """Return the rich modular RL state + action mask from SCADA.

    Useful for the XAI panel and the advanced agent to consume without
    re-running the per-node extractors.  Falls back to an empty payload
    when the StateBuilder hasn't been initialised yet.
    """
    scada = get_scada(request)
    return {
        "state": scada.get_rich_state(),
        "action_mask": scada.get_action_mask(),
    }
