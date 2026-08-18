"""
main.py - FastAPI application entry point.

Uses the FastAPI lifespan context manager to initialise singletons and
store them in app.state, making them accessible via dependency injection
in routes (no mutable module-level globals).

The EHM upgrade (M0+) introduces a lightweight DI Container (`di.Container`)
that lets *every* module — not just FastAPI routes — look up the same
singletons.  The container is process-global and is registered in this
lifespan; existing `app.state.*` lookups continue to work unchanged so
backward compatibility is preserved.

Run with:
  python main.py
  OR
  uvicorn main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import sys
import os
from contextlib import asynccontextmanager

# Ensure backend root is on the Python path so relative imports resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore

from simulation.grid import SmartGrid  # type: ignore
from simulation.scada import ScadaControlCenter  # type: ignore
from simulation.ems import EnergyManagementSystem  # type: ignore
from models.attack_detector import AttackDetector, AttackType  # type: ignore
from api.routes import router  # type: ignore

# M0 — DI container + observability.
from di import Container, get_container  # type: ignore
from observability.logging_setup import get_logger  # type: ignore
from observability.metrics_store import get_store  # type: ignore

# M2 — digital twin, weather, smart faults, microgrid.
from digital_twin.twin_registry import TwinRegistry  # type: ignore
from weather.weather_engine import WeatherEngine  # type: ignore
from faults.smart_fault_injector import SmartFaultInjector  # type: ignore
from microgrid.microgrid_controller import MicrogridController  # type: ignore
# M3 — advanced RL + XAI.
from rl.advanced_rl_agent import AdvancedDQNAgent  # type: ignore


# -----------------------------------------------------------------------
# Lifespan - initialise once, store in app.state and DI Container
# -----------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: build singletons. Shutdown: nothing to clean up."""
    log = get_logger("main")
    print("=" * 60)
    print("  AI Self-Healing Smart Grid - Backend Starting Up")
    print("=" * 60)

    # Initialise the process-global metrics ring buffer first so other
    # modules can record into it during their own setup.
    metrics = get_store()
    metrics.record("startup", {"event": "begin"}, timestamp=0)

    print("\n[1/3] Initialising Structural Level (Physical Grid)...")
    app.state.grid = SmartGrid()
    g: SmartGrid = app.state.grid
    print(f"      Grid created: {len(g.nodes)} nodes, "
          f"{g.graph.number_of_edges()} edges")

    print("\n[2/3] Booting Energy Management System (EMS Layer)...")
    app.state.ems = EnergyManagementSystem()
    print("      EMS ready - absorption ratio: 50 %, partial control mode")

    print("\n[3/3] Booting SCADA Control Center (AI Layer)...")
    app.state.scada = ScadaControlCenter()
    app.state.scada.warmup_ai(g)  # Pre-train RL agent on grid bounds

    # Item 10 — Cyber-attack detector
    app.state.attack_detector = AttackDetector()

    # 🔥 CRITICAL FIX — INITIAL ENERGY FLOW
    for _ in range(3):
        g.update_generation()
        g.update_power_flow()

    # ----- M0: register all built singletons in the DI container -----
    # Existing routes keep using `app.state.*`; future code can use
    # `get_container().get("grid")` instead.
    container: Container = get_container()
    container.register("grid", lambda: app.state.grid)
    container.register("ems", lambda: app.state.ems)
    container.register("scada", lambda: app.state.scada)
    container.register("attack_detector", lambda: app.state.attack_detector)
    container.register("forecaster", lambda: app.state.scada.forecaster)
    container.register("fault_detector", lambda: app.state.scada.fault_detector)
    container.register("rl_agent", lambda: app.state.scada.rl_agent)
    container.register("metrics_store", lambda: get_store())
    container.register("logger", lambda: get_logger("main"))

    # ----- M2: digital twin, weather, smart faults, microgrid -----
    twin_reg = TwinRegistry()
    twin_reg.register(g)
    twin_reg.sync(g, dt_hours=1.0)
    app.state.twin_registry = twin_reg

    weather = WeatherEngine(seed=42)
    app.state.weather_engine = weather

    injector = SmartFaultInjector(seed=42)
    app.state.fault_injector = injector

    controller = MicrogridController()
    app.state.microgrid_controller = controller

    container.register("twin_registry", lambda: app.state.twin_registry)
    container.register("weather_engine", lambda: app.state.weather_engine)
    container.register("fault_injector", lambda: app.state.fault_injector)
    container.register("microgrid_controller", lambda: app.state.microgrid_controller)

    # ----- M3: advanced RL + XAI -----
    advanced_agent = AdvancedDQNAgent()
    app.state.advanced_agent = advanced_agent
    container.register("advanced_agent", lambda: app.state.advanced_agent)
    log.info(
        "startup complete",
        extra={"nodes": len(g.nodes), "edges": g.graph.number_of_edges(),
               "twins": len(twin_reg), "weather_state": weather.state.value},
    )
    metrics.record("startup", {"event": "complete"}, timestamp=1)

    print("\n[OK] All systems ready.\n")
    print("=" * 60)

    yield   # application runs here

    # Teardown (nothing required)


# -----------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------

app = FastAPI(
    title="AI Self-Healing Smart Grid SCADA API",
    description=(
        "Real-time smart grid architecture with a separated SCADA Control Center "
        "managing fault detection and multi-agent demand response."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# CORS - allow React dev server and any local origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


# -----------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn  # type: ignore
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
