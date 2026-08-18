# EHM Project — Final Roadmap (Post Critical 10)

## What landed (Critical 10)

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | In-house DC Power Flow (PyPSA-free) | ✅ | `simulation/power_flow.py`, KCL residual <1e-15 on 49-bus grid |
| 2 | Fixed DQN state vector | ✅ | `STATE_DIM = 72`, real node names, 5/5 tests |
| 3 | Real-data training hook + sample CSVs | ✅ | `data/sample_load.csv` (662 rows), `data/sample_faults.csv` (1500 rows) |
| 4 | Baselines + benchmark runner | ✅ | `benchmarks/baselines.py`, `runner.py`, `scenarios.py` |
| 5 | Statistical reporting | ✅ | `benchmarks/report.py`: mean ± std, 95% CI, paired t-test |
| 6 | Silent excepts → logged warnings | ✅ | 0 silent excepts remain; module-level loggers in 3 modules |
| 7 | pytest + GitHub Actions CI | ✅ | `tests/` with 5 files, 25 tests, `.github/workflows/ci.yml` |
| 8 | Dockerfile + docker-compose | ✅ | `backend/Dockerfile`, `docker-compose.yml` |
| 9 | IEEE 13-bus digital twin | ✅ | `simulation/ieee13.py`, 13 buses, 13 lines, DC PF passes |
| 10 | Cyber-attack detection | ✅ | `models/attack_detector.py`: FDIA, REPLAY, RAMP; 4/4 tests |

## What changed at a glance

```
backend/
├── simulation/
│   ├── power_flow.py     ← In-house DC PF solver
│   ├── ac_power_flow.py  ← NEW: pandapower-backed AC PF
│   ├── ieee13.py         ← IEEE 13-bus digital twin
│   ├── grid.py           ← +dc_state, get_dc_state(), get_rl_state() fixed,
│   │                       bus_map, line_impedance, voltage_angle,
│   │                       ac_state, get_ac_state()
│   │                       update_ac_power_flow()
│   ├── node.py           ← +voltage_angle
│   └── scada.py          ← +logger, fix silent except
├── digital_twin/
│   ├── twin.py           ← failure_risk_indicator (back-compat alias)
│   ├── degradation.py    ← docstring: "simulation-based, not validated"
│   └── twin_registry.py  ← +rebuild(grid) for /city/generate
├── api/
│   ├── routes.py         ← +/ac_state, /attack, /attack_status, /attack_clear,
│   │                       silent excepts → logged warnings,
│   │                       twin registry fallback → 503
│   ├── twin_routes.py    ← strict DI on app.state.twin_registry
│   ├── predictive_routes.py ← strict DI on app.state.twin_registry
│   ├── improvement_routes.py ← step_failures surfaced in response
│   ├── city_routes.py    ← rebuilds TwinRegistry on /city/generate
│   └── main.py           ← +app.state.attack_detector
├── models/
│   ├── rl_agent.py       ← STATE_DIM=72, real node names, replay save/load,
│   │                       smart_warmup docstring: "rule-guided bootstrap,
│   │                       not behavioural cloning"
│   ├── rl/expert_policy.py ← NEW: rule ladder extracted, shared with
│   │                          benchmarks/baselines.py
│   ├── lstm_model.py     ← csv_path arg, _load_csv_data
│   ├── fault_detector.py ← csv_path arg, _load_fault_csv
│   └── attack_detector.py ← FDIA, REPLAY, RAMP
├── metrics/
│   └── statistics.py     ← NEW: centralised mean/std/CI/t-test
├── experiments/          ← NEW: experiments framework
│   ├── baselines/        ← random, rule_based, dqn, flisr_only, persistence
│   ├── policies.py       ← PolicyRegistry extension
│   ├── runner.py         ← generalised runner
│   ├── aggregate.py      ← mean ± std, 95% CI, paired t-test
│   ├── monte_carlo.py    ← N-seed sweep
│   ├── ablation.py       ← drop-one-component
│   ├── topology_comparison.py
│   ├── predictive_vs_reactive.py
│   └── ieee13_validation.py ← pandapower reference comparison
├── benchmarks/           ← baselines, scenarios, runner, report
├── tests/                ← ~30 existing + ~10 new tests
├── data/                 ← sample_load.csv, sample_faults.csv
├── pytest.ini
├── Dockerfile
└── .dockerignore
.github/workflows/ci.yml
docs/                    ← ARCHITECTURE.md, METRICS_REFERENCE.md,
                            RESEARCH_NOTES.md, power_flow.md (now
                            bidirectional-flow + AC PF), digital_twin.md
                            (now honest about validation status),
                            cyber_attack.md (now honest about
                            limitations), VALIDATION.md (NEW: single
                            source of truth for what is validated),
                            and this roadmap.
```

## Verification commands

```bash
cd backend
python -m pytest tests/ -v          # 25 passed in ~6s
python -m simulation.power_flow     # 5-bus self-test: PASS
python -c "from simulation.grid import SmartGrid; \
           g=SmartGrid(); g.update_power_flow(); \
           print(g.get_dc_state()['kcl_residual_max'])"   # < 1e-15
python -m benchmarks.runner --seeds 30 --output benchmarks/results/full.json
python -m benchmarks.report --input benchmarks/results/full.json \
                            --output benchmarks/results/REPORT.md
```

## What comes next (Strongly Recommended 10)

The remaining items that materially improve the publication case but were
out of scope for the Critical 10 round:

1. **Transformer forecaster (Informer/Autoformer)** to replace the
   lightweight LSTM with a published SOTA baseline.
2. **GNN/GAT state encoder** for the DQN — replace the flattened priority-
   node vector with a 2-layer GAT over the IEEE 13-bus or EHM 49-bus
   graph.
3. **PINN (Physics-Informed Neural Network) load flow** — neural
   surrogate for DC PF that respects KCL by construction. Train on
   current DC PF outputs; validate residual against analytic DC PF.
4. **Digital Twin v2 with AC PF** — extend the IEEE 13-bus module with
   Y-bus + Newton-Raphson, expose `v_mag_pu` and `q_injection` on every
   node.
5. **Federated Learning** — train per-feeder DQN policies and aggregate
   weights via FedAvg, simulating privacy-preserving distributed training.
6. **Online / Continuous RL** — replace batch training with streaming
   PPO/SAC and a replay-buffer with recency weighting.
7. **PMU integration** — ingest 30 Hz synchrophasor streams and feed
   them into the existing LSTM/Detector pipeline.
8. **Voltage stability margin** as an explicit DQN reward signal —
   compute `dV/dP` sensitivity on every state.
9. **Multi-bus LOPF** — extend DC PF to a Linear Optimal Power Flow for
   minimum-cost generation dispatch.
10. **All ablation studies** — DQN vs rule-based vs random, transformer
    vs LSTM, GNN vs MLP, with-vs-without-DC-PF, with-vs-without-attack-
    detector, on the 49-node and IEEE 13-bus grids. Implemented as
    `experiments/ablation.py`.

## Future work — explicitly out of scope for this paper

Items we are not pursuing as part of the current research program. Listed
here so a reviewer understands what is "demonstrative" vs "validated":

1. **Coordinated multi-edge FDIA detection** (Liu et al. 2018). The
   current cyber-attack detector is per-edge by design. A multi-edge
   chi-squared test would close the gap but requires labelled attack
   data we don't have.
2. **PMU-stream integration.** The hooks exist (csv_path loaders) but
   the attack detector is not calibrated against real PMU measurement
   noise.
3. **Empirical calibration of the digital-twin failure-risk indicator.**
   The current `failure_probability` / `failure_risk_indicator` is a
   piecewise linear function of `health`. A real calibration requires
   a recorded transformer-outage dataset and is not part of the current
   project.
4. **Three-phase unbalanced AC PF.** The current AC PF solver is a
   balanced positive-sequence Newton-Raphson. A full three-phase
   solver would require a per-phase Y-bus and a different formulation.
5. **Hardware-in-the-loop deployment.**

## Out of scope

- IEEE 13/34/123-bus AC PF simulation
- Manuscript rewrite with results from the benchmark
- Real PMU data ingestion (lab-only sample CSVs shipped)
- Hardware-in-the-loop deployment