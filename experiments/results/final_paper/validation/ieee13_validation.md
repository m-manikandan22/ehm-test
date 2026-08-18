# IEEE 13-bus validation report

Topology: IEEE 13-bus test feeder (13 buses, 13 lines, V_base=4.16 kV, S_base=5.0 MVA)

## EHM DC PF
- converged: **True**
- KCL residual max: 1.42e-16
- buses: 13, lines: 26

## Pandapower DC PF reference
- available: **True**
- max |Δangle|: 6.78e-02 deg
- mean |Δangle|: 5.09e-02 deg

## EHM AC PF
- available: **True**
- bus voltage range: [1.020, 1.020] p.u.

## Limitations
- IEEE 13-bus builder uses balanced positive-sequence per-unit equivalent, not the full per-phase spec (no regulators, no Y-Δ transformer model, no spot / distributed split).
- DC PF comparison only validates KCL + angle sign — angle magnitudes depend on per-unit calibration, not the physics.
- AC PF result depends on pandapower install; if not present, the AC PF block is empty and the validation is incomplete.

Validation status: **demonstrative**