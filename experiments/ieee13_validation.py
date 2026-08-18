"""IEEE 13-bus validation: EHM DC PF vs pandapower DC PF reference.

This script compares the in-house DC power flow solver (in
``simulation.power_flow``) against pandapower's built-in DC power flow
on the IEEE 13-bus test feeder, and runs the new AC power flow solver
(``simulation.ac_power_flow``) on the same network. It writes a JSON
report listing what was compared, what the deltas are, and what the
limitations are.

Usage
-----
    cd backend
    python -m experiments.ieee13_validation --output experiments/results/ieee13_validation.json

Status
------
Demonstrative, not research-grade. The IEEE 13-bus builder in
``simulation.ieee13.py`` uses a balanced positive-sequence per-unit
equivalent, not the full per-phase IEEE spec. Comparison is run for
sanity (both solvers should agree to within a few percent when angles
are small) — not for publication-grade validation.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Dict, List


# Allow running as ``python -m experiments.ieee13_validation`` from backend/
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(THIS_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# Apply the pandas 3.0+ CoW compat patch BEFORE importing pandapower.
try:
    from utils.pandas_compat import _apply_pandas_compat_patch
    _apply_pandas_compat_patch()
except Exception:
    pass

from simulation.ieee13 import (  # noqa: E402
    build_ieee13, get_ieee13_metadata)
from simulation.power_flow import dc_power_flow  # noqa: E402


logger = logging.getLogger(__name__)


def _try_pandapower_dc_reference(grid) -> Dict[str, float]:
    """Run pandapower DC PF on the IEEE 13 grid for reference comparison.

    Returns a dict mapping bus_id → voltage angle (degrees). Returns an
    empty dict if pandapower is not installed or the run failed.
    """
    try:
        import pandapower as pp  # type: ignore
    except ImportError:
        logger.warning("pandapower not installed; skipping reference comparison")
        return {}

    try:
        net = pp.create_empty_network(name="IEEE13 reference")
        active_nodes = [
            nid for nid, n in grid.nodes.items()
            if not n.failed and not n.isolated
        ]
        bus_map = {}
        for nid in active_nodes:
            idx = pp.create_bus(net, vn_kv=4.16, name=str(nid))
            bus_map[nid] = int(idx)
        # Slack = "650" (the substation)
        slack = bus_map.get("650") or bus_map[active_nodes[0]]
        pp.create_ext_grid(net, bus=slack, vm_pu=1.02, name="source")

        for nid in active_nodes:
            if nid == "650":
                continue
            p_mw = float(getattr(grid.nodes[nid], "load", 0.0))
            if p_mw > 0:
                pp.create_load(net, bus=bus_map[nid], p_mw=p_mw,
                               q_mvar=p_mw * 0.3287)

        added_pairs = set()
        for u, v, data in grid.graph.edges(data=True):
            if not data.get("active", True):
                continue
            if u not in active_nodes or v not in active_nodes:
                continue
            pair = tuple(sorted((u, v)))
            if pair in added_pairs:
                continue
            added_pairs.add(pair)
            r_pu = float(data.get("resistance", 0.01)) * 10.0
            imp = (grid.line_impedance.get((u, v))
                   or grid.line_impedance.get((v, u)) or {})
            x_pu = float(imp.get("X", 0.05) or 0.05)
            if x_pu <= 0:
                x_pu = 0.05
            # Use create_line_from_parameters because pandapower 2.x
            # requires a ``std_type`` positional arg for create_line and
            # we want to pass our own R/X per-km directly.
            pp.create_line_from_parameters(
                net, from_bus=bus_map[u], to_bus=bus_map[v],
                length_km=1.0, r_ohm_per_km=r_pu, x_ohm_per_km=x_pu,
                c_nf_per_km=0.0, max_i_ka=999.0,
            )

        pp.rundcpp(net)
        bus_to_ehm = {int(idx): nid for nid, idx in bus_map.items()}
        return {
            bus_to_ehm[int(idx)]: float(row["va_degree"])
            for idx, row in net.res_bus.iterrows()
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("pandapower DC PF reference failed: %r", exc)
        return {}


def _try_ehm_ac_pf(grid) -> Dict[str, float]:
    """Run EHM AC power flow and return bus voltage magnitudes."""
    try:
        from simulation.ac_power_flow import run_ac_power_flow
        result = run_ac_power_flow(grid, slack_bus_id="650")
        return result.bus_voltage_pu if result.converged else {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("EHM AC PF failed: %r", exc)
        return {}


def _angle_diff_summary(ehm: Dict[str, float],
                        ref: Dict[str, float]) -> Dict[str, float]:
    """Compute max / mean absolute angle diff (deg) between two angle dicts."""
    diffs: List[float] = []
    common = set(ehm.keys()) & set(ref.keys())
    for nid in common:
        diffs.append(abs(ehm[nid] - ref[nid]))
    if not diffs:
        return {"max_deg": float("nan"),
                "mean_deg": float("nan"),
                "common_buses": 0}
    return {
        "max_deg":   max(diffs),
        "mean_deg":  sum(diffs) / len(diffs),
        "common_buses": len(diffs),
    }


def run_validation(output_path: str) -> Dict[str, object]:
    grid = build_ieee13()
    ehm_dc = dc_power_flow(grid, slack_bus_id="650")
    ref_dc = _try_pandapower_dc_reference(grid)
    ref_v = _try_ehm_ac_pf(grid)

    if ref_dc:
        angle_diff = _angle_diff_summary(
            ehm_dc.bus_angle_deg, ref_dc)
    else:
        angle_diff = {"max_deg": float("nan"),
                      "mean_deg": float("nan"),
                      "common_buses": 0}

    report = {
        "test": "ieee13_validation",
        "metadata": get_ieee13_metadata(),
        "ehm_dc_pf": {
            "converged": bool(ehm_dc.converged),
            "kcl_residual_max": float(ehm_dc.kcl_residual_max),
            "kcl_residual_mean": float(ehm_dc.kcl_residual_mean),
            "bus_count": int(ehm_dc.bus_count),
            "line_count": int(ehm_dc.line_count),
            "bus_angle_deg": ehm_dc.bus_angle_deg,
            "line_flow_mw_summary": {
                f"{u}->{v}": p
                for (u, v), p in list(ehm_dc.line_flow_mw.items())[:25]
            },
            "warnings": ehm_dc.warnings,
        },
        "pandapower_dc_pf_reference": {
            "available": bool(ref_dc),
            "bus_angle_deg": ref_dc,
            "differences_vs_ehm": angle_diff,
        },
        "ehm_ac_pf": {
            "available": bool(ref_v),
            "bus_voltage_pu": ref_v,
            "anatomy_note": (
                "Balanced positive-sequence equivalent of the IEEE 13-bus "
                "feeder via pandapower Newton-Raphson. Not the full "
                "per-phase unbalanced model."
            ),
        },
        "limitations": [
            "IEEE 13-bus builder uses balanced positive-sequence per-unit "
            "equivalent, not the full per-phase spec (no regulators, no Y-Δ "
            "transformer model, no spot / distributed split).",
            "DC PF comparison only validates KCL + angle sign — angle magnitudes "
            "depend on per-unit calibration, not the physics.",
            "AC PF result depends on pandapower install; if not present, the "
            "AC PF block is empty and the validation is incomplete.",
        ],
        "validation_status": (
            "demonstrative"
        ),
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    return report


def _format_report(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# IEEE 13-bus validation report")
    lines.append("")
    md = report["metadata"]
    lines.append(f"Topology: {md['name']} "
                 f"({md['buses']} buses, {md['lines']} lines, "
                 f"V_base={md['voltage_base_kv']} kV, "
                 f"S_base={md['power_base_mva']} MVA)")
    lines.append("")
    ehm = report["ehm_dc_pf"]
    lines.append("## EHM DC PF")
    lines.append(f"- converged: **{ehm['converged']}**")
    lines.append(f"- KCL residual max: {ehm['kcl_residual_max']:.2e}")
    lines.append(f"- buses: {ehm['bus_count']}, lines: {ehm['line_count']}")
    if ehm["warnings"]:
        lines.append(f"- warnings: {len(ehm['warnings'])}")
    lines.append("")
    ref = report["pandapower_dc_pf_reference"]
    lines.append("## Pandapower DC PF reference")
    lines.append(f"- available: **{ref['available']}**")
    if ref["available"]:
        diff = ref["differences_vs_ehm"]
        lines.append(f"- max |Δangle|: {diff['max_deg']:.2e} deg")
        lines.append(f"- mean |Δangle|: {diff['mean_deg']:.2e} deg")
    lines.append("")
    ac = report["ehm_ac_pf"]
    lines.append("## EHM AC PF")
    lines.append(f"- available: **{ac['available']}**")
    if ac["bus_voltage_pu"]:
        v_min = min(ac["bus_voltage_pu"].values())
        v_max = max(ac["bus_voltage_pu"].values())
        lines.append(f"- bus voltage range: [{v_min:.3f}, {v_max:.3f}] p.u.")
    lines.append("")
    lines.append("## Limitations")
    for lim in report["limitations"]:
        lines.append(f"- {lim}")
    lines.append("")
    lines.append(f"Validation status: **{report['validation_status']}**")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", default="experiments/results/ieee13_validation.json",
        help="Path to write the JSON report"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    report = run_validation(args.output)
    md_report = _format_report(report)
    md_path = os.path.splitext(args.output)[0] + ".md"
    with open(md_path, "w") as f:
        f.write(md_report)
    print(f"Wrote {args.output}")
    print(f"Wrote {md_path}")
    # Console summary
    ehm = report["ehm_dc_pf"]
    print(f"EHM DC PF converged={ehm['converged']}, "
          f"KCL max residual={ehm['kcl_residual_max']:.2e}")
    ref = report["pandapower_dc_pf_reference"]
    if ref["available"]:
        diff = ref["differences_vs_ehm"]
        print(f"Pandapower DC PF max |Δangle|={diff['max_deg']:.2e} deg "
              f"over {diff['common_buses']} buses")
    else:
        print("Pandapower DC PF: not available (install pandapower to enable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())