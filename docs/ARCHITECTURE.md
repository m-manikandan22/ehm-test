# EHM Architecture (Clean)

## Layered view

```
┌──────────────────────────────────────────────────────────────────────┐
│ INTERFACE — FastAPI routes (api/) + React components (frontend/src) │
│   - Legacy endpoints preserved: /state, /simulate, /event, /action │
│   - M1: /city/*, /planner/*                                         │
│   - 
M2: /twins/*, /weather/*, /fault/*, /microgrid/*                │
│   - M3: /explain/*                                                  │
│   - M4: /metrics/*, /improvement/*                                  │
└────────────────────────┬─────────────────────────────────────────────┘
                         │ depends on
┌────────────────────────▼─────────────────────────────────────────────┐
│ APPLICATION — simulators, planners, evaluators, RL agents            │
│   - simulation/  (SmartGrid, ScadaControlCenter, EMS, IEEE-13)       │
│   - models/      (LSTM, DQN, ANN, AttackDetector)                    │
│   - city/        (procedural city + zoning + road network)           │
│   - planning/    (AI planner, objectives, topology KPIs)             │
│   - digital_twin/(twin + degradation model + registry)               │
│   - weather/     (Markov weather engine + YAML configs)              │
│   - faults/      (fault catalog + smart injector)                   │
│   - microgrid/   (islanding controller)                              │
│   - rl/          (state builder, rewards, action mask, explainer,   │
│                   advanced agent, policy registry)                   │
│   - metrics/     (IEEE 1366, forecast metrics, grid KPIs, registry) │
│   - improvement/ (evaluator + redesigner)                            │
└────────────────────────┬─────────────────────────────────────────────┘
                         │ depends on
┌────────────────────────▼─────────────────────────────────────────────┐
│ DOMAIN — pure data types (dataclasses, enums)                       │
│   - simulation/node.py    (GridNode + node history)                  │
│   - digital_twin/twin.py  (DigitalTwin dataclass)                   │
│   - faults/fault_catalog.py (Fault enum + dataclass)                 │
│   - weather/weather_engine.py (WeatherState enum)                    │
│   - rl/action_mask.py    (AdvancedAction enum)                      │
│   - metrics/             (no types — pure functions)                │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE — DI, logging, config, tracing                       │
│   - di.py                    (Container: register/get/has/names)     │
│   - observability/           (logging_setup, metrics_store, tracing) │
│   - config/settings.py       (pydantic-settings env loader)          │
│   - utils/seeds.py           (deterministic RNG helpers)             │
└──────────────────────────────────────────────────────────────────────┘
```

## Dependency rule

- Interface layer depends on Application.
- Application depends on Domain (and may inject Infrastructure).
- Domain depends on **nothing** inside the project.
- Infrastructure is wired in `main.py`'s lifespan (DI container) and
  in `tests/conftest.py` (fixtures).

## Backward compatibility

Every existing FastAPI endpoint (`/state`, `/simulate`, `/event`,
`/predict`, `/action`, `/reset`, `/health`, `/fault_analysis`,
`/islanding_analysis`, `/dc_state`, `/attack*`, `/ai/suggestions`)
is preserved verbatim.  New modules add *new* endpoints and
*new* sub-modules; legacy code is never replaced.

## Determinism

RNG sources are funneled through `utils/seeds.make_rng` so
benchmarks are reproducible.  Configuration that affects
benchmarks lives in `config/settings.py`.
