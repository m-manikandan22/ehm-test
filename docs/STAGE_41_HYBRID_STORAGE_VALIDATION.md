# Stage 41 — Hybrid-Storage Validation

This document validates the hybrid-storage model against the on-disk
artefacts and source code. We do NOT run a new hybrid-storage
experiment in Stage 41 — we evaluate the existing
`hybrid_storage_final.json` honestly.

---

## 1. The on-disk artefact

`experiments/results/hybrid_storage_final.json`:

| Policy | ENS (MWh) | CMI | recoveries |
|---|---:|---:|---:|
| hybrid | 0.0000 | 0.00 | 0 |
| battery_only | 0.0000 | 0.00 | 0 |
| supercap_only | 0.0000 | 0.00 | 0 |
| none | 0.0000 | 0.00 | 0 |

Header: `scenario_seed = 0, total_steps = 40, fault_count = 5`.

**Every policy — including the no-storage baseline — returns zero
ENS and zero CMI.** The scenario cannot distinguish policies.

## 2. Why the scenario cannot distinguish policies

* The scenario injects 5 faults at random timesteps in [5, 39] on a
  49-node grid.
* The grid has 5 generation sources (SOLAR, WIND, NUCLEAR, COAL, GAS)
  and 24 residential loads.
* The faults are FLISR-healable (pole, transformer). The harness
  runs FLISR every 4 ticks (`runner.py` line 297).
* Even with `enable_storage = False`, the residual load is served
  by the conventional generators.

There is **no scenario in the existing artefact where demand exceeds
generation for long enough that storage is needed**. So storage adds
no observable benefit.

## 3. What the model can represent (latent capability)

The `backend/simulation/node.py::GridNode` does implement:

* `battery_level` (SOC)
* `supercap_level` (supercap SOC)
* `use_battery(amount)` — discharges the battery
* `use_supercapacitor(amount)` — discharges the supercap

These are real physical effects — they actually change the grid's
energy balance. So the model can represent hybrid storage; the
**paper experiments** simply never stress it.

## 4. Why the Stage-26 paper experiments cannot expose hybrid storage

The Stage-26 runner hard-codes:

```python
elif name == "use_battery":
    for node in grid.nodes.values():
        if (getattr(node, "node_type", "") == "house"
                and float(getattr(node, "battery_level", 0.0) or 0.0) > 0.2):
            node.use_battery(0.2)
```

This dispatches `use_battery` *only when the DQN picks action 1*.
The action-mask in `rl_agent.py::select_action` enables action 1 only
when `balance < -0.1`. So the battery is used when the system is in
deficit.

In the Stage-26 default scenario, the system is rarely in deficit
because FLISR restores generation faster than faults accumulate.

## 5. Scenarios that WOULD expose hybrid storage

These are the scenarios in `STAGE_41_SCENARIO_MATRIX.md` that should
be implemented in Stage 42:

* **Scenario B** — single fault + 1.5× demand for 10 ticks.
* **Scenario C** — single fault + low renewable (solar/wind at 0.2).
* **Scenario E** — fault + high demand + low renewable (compound).
* **Scenario I** — storage stress: SOC = 0.1 at fault onset.

None of these scenarios exist in the current codebase. Adding them
requires:

1. A way to set battery SOC at scenario start (e.g.
   `Scenario.battery_soc_init`).
2. A demand multiplier per scenario.
3. A renewable multiplier per scenario.

We do **not** add these in Stage 41 because the user has forbidden
rebuilding the project.

## 6. Voltage support claim — Stage 40 said it is a "DC-PF proxy"

The Stage-40 gate states:

> *"Round-trip efficiency and voltage are DC-PF proxies."*

This means the simulation does **not** run a full AC power flow with
frequency-dependent battery behaviour. So the claim "the
supercapacitor responds to transient stress" is *not* supported by
the simulation. The supercapacitor's role in this model is purely a
fast discharge of stored energy, indistinguishable from the
battery except for the magnitude of the discharge.

## 7. Honest framing

> **The hybrid-storage model exists in the codebase but is not
> exercised by the Stage-26 paper experiments. The existing
> `hybrid_storage_final.json` shows complete saturation (zero ENS,
> zero CMI for every policy) and therefore cannot support a
> contribution claim. Hybrid storage is a *future-work* component
> that requires harder scenarios (Stage 42).**

## 8. Recommendations for Stage 42

1. Implement scenarios B, C, E, I from the scenario matrix.
2. Re-run the hybrid-storage experiment with these scenarios.
3. Report the *differences* in ENS, CMI, final SOC, and
   supercap discharge events.
4. If differences are still negligible, report that honestly.
