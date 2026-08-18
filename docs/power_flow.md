# Power Flow

EHM ships with two power-flow solvers in `backend/simulation/`:

| Solver | Module | Inputs | Outputs | Approximation |
|--------|--------|--------|---------|---------------|
| DC PF  | `power_flow.py` | P injection, line X | voltage angles, line MW | V=1 pu, θ small |
| AC PF  | `ac_power_flow.py` | P+jQ injection, line Y-bus | voltage magnitude & angle, P+jQ flow | balanced positive-sequence Newton-Raphson |

The DC solver is always available and depends only on NumPy/NetworkX.
The AC solver wraps `pandapower` (added to `requirements.txt`) and can
be disabled — if pandapower is not installed, `update_ac_power_flow()`
returns an error explaining how to install it.

## Power-flow direction is bidirectional

EHM's `SmartGrid` uses a `networkx.DiGraph` for implementation, but the
graph data structure stores edges in **both directions** (`u→v` and
`v→u`) so a DC PF solve correctly handles reverse flow. This matches
the behaviour expected in a modern distribution network with rooftop PV,
battery storage, DERs, and microgrids — bidirectional flow is the
default, not the exception. Bidirectional flow is required for:

- **Net metering**: a household PV inverter exporting to the grid shows
  up as a negative load on the bus, which the BFS / DC PF overlay
  handles as a sign-flip on the same edge.
- **Battery round-trip**: charge and discharge cycles invert the edge flow.
- **Microgrid islanding**: when a microgrid exports back to the grid,
  the flow direction reverses on the tie switch.

The "power flows DOWN only" claim that appeared in early planning
notes was an early-stage assumption and is **not** a property of the
current solver — bidirectional flow has always been modelled by
storing both `u→v` and `v→u` edges.

## Why DC PF (and not just AC PF)?

DC PF is a linear approximation of full AC power flow widely used in
transmission planning, contingency screening, and real-time market
clearing software (Stott, "Review of Load-Flow Calculation Methods",
Proceedings of the IEEE 1974). For the EHM scope — distribution-level,
49-node or 13-node, 11 kV base — DC PF is appropriate because:

- **Computational cost is O(n²) per timestep** (linear solve on a small
  B-matrix).
- **Voltage magnitudes are nominally 1.0 pu** at all buses, which is
  fine for distribution feeders where voltage deviations are small.
- **KCL is enforced exactly** — the previous BFS heuristic violated KCL
  at every multi-child bus.

DC PF does **not** solve for reactive power, voltage magnitudes, or
regulator/transformer tap dynamics. AC PF addresses these.

## DC PF equations (per-unit)

For each bus `i`:

```
P_i = Σ_j  B_ij · (θ_i − θ_j),   for all non-slack buses i
```

For each line `(i, j)`:

```
P_ij = (θ_i − θ_j) / X_ij     [MW]
I_ij = |P_ij| / V_base        [A, after per-unit conversion]
loss_ij = I²_ij · R_ij        [MW]
```

The B-matrix is built once at grid construction:

```
B_ij = −1 / X_ij                 (off-diagonal, for active edges)
B_ii = Σ_{k≠i} 1 / X_ik          (diagonal)
```

A slack bus is chosen (the first generator by default; the main substation
is the fallback), and its row/column are removed from the system. Each
weakly-connected component is solved independently, which is the standard
fix for singular B-matrices under partial islanding.

## AC PF equations (per-unit, balanced positive-sequence)

AC PF uses Newton-Raphson on the Y-bus with the polar form:

```
P_i = V_i · Σ V_j · (G_ij · cos θ_ij + B_ij · sin θ_ij)
Q_i = V_i · Σ V_j · (G_ij · sin θ_ij − B_ij · cos θ_ij)
```

Where:

- `V_i` is the per-unit voltage magnitude at bus i
- `θ_ij = θ_i − θ_j` is the angle difference
- `G_ij + jB_ij` is the (i, j) entry of the Y-bus admittance matrix
- `P_i = P_gen_i − P_load_i`, `Q_i = Q_gen_i − Q_load_i`

Newton-Raphson iterates the linearised mismatch equations
`J · [Δθ, ΔV/V] = [ΔP, ΔQ]` until |ΔP| and |ΔQ| converge below the
default 1e-6 tolerance.

## Calibration

EHM's per-line reactance values come from
`simulation/power_flow.py:DEFAULT_X_BY_TYPE`:

| Edge kind    | X (per-unit, 10 MVA / 11 kV base) |
|--------------|------------------------------------|
| substation   | 0.01 |
| transformer  | 0.02 |
| feeder       | 0.05 |
| lateral      | 0.08 |
| tie          | 0.10 |

These values match typical distribution-feeder reactances from Kersting's
*Distribution System Modeling and Analysis*, Table 4.1, scaled to per-unit
on a 10 MVA / 11 kV base.

Per-line resistance is calibrated from the existing `resistance` edge
attribute, scaled by 10× to bring it into a meaningful per-unit range.
This is a documented calibration choice; production deployment with real
line data should override `line_impedance` directly.

## Validation

- **5-bus textbook case** (`_self_test_5bus()`) verifies DC PF KCL within
  machine precision (1e-15) and angle polarity.
- **IEEE 13-bus** via `experiments/ieee13_validation.py`: EHM DC PF and
  pandapower DC PF both converge on the IEEE 13-bus topology and agree
  in sign and magnitude on the slack-anchored angles (the report at
  `experiments/results/ieee13_validation.json` lists the per-bus diffs).
- **On-demand 49-node grid**: KCL residuals after DC PF are typically
  <1e-15 (numpy float precision).

## Integration with the rest of EHM

`SmartGrid.update_power_flow()` runs DC PF on every tick *after* the BFS
flow. The DC PF result overwrites per-edge `flow`, `current_a`, and
`loss_mw`, and sets per-node `voltage_angle`. The BFS continues to drive
visualisation and FLISR candidate enumeration; the DC PF result is the
physically consistent overlay consumed by `/state` and `/dc_state`.

`SmartGrid.update_ac_power_flow()` (optional) runs AC PF and stores the
result on `grid.ac_state`. The result is exposed via `/ac_state` and
includes per-bus `v_mag_pu`, `theta_deg`, and per-line MW+MVAR.

## Limitations

- **DC PF: voltage magnitudes are not solved** — every bus is 1.0 pu.
  Voltage drops on long laterals are therefore invisible. AC PF is the
  fix.
- **DC PF: no reactive power** — Q injection is ignored. AC PF solves Q.
- **DC PF: no thermal limits enforced at the PF layer** — `update_power_flow`
  does the line-trip check separately after DC PF returns.
- **AC PF: balanced positive-sequence only** — no per-phase unbalance.
  Three-phase unbalanced loads (e.g. IEEE 13-bus's mixed spot loads) are
  converted to equivalent positive-sequence before the solve.
- **AC PF: regulator/transformer tap dynamics deferred** — auto-tap
  control would require a discrete-control loop on top of NR. Treated
  as fixed series impedance for now.
- **AC PF: switching transients deferred** — tie switch 684↔680 is the
  only controllable switch; close/open actions are simulated atomically.

## References

- B. Stott, "Review of Load-Flow Calculation Methods", *Proceedings of the IEEE*, 1974.
- W. H. Kersting, *Distribution System Modeling and Analysis*, 4th ed.
- IEEE PES Distribution System Analysis Subcommittee, IEEE 13-bus test feeder specification, 1992.
- L. Thurner et al., "pandapower — an Open-Source Python Tool for Convenient Modeling, Analysis, and Optimization of Electric Power Systems", *HICSS 2018*.
