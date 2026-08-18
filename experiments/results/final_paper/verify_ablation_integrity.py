"""verify_ablation_integrity.py — Phase 6 verification.

For every pre-baked ExperimentConfig, this script:
  1. Builds the controller for that config.
  2. Runs a tiny scenario (3 ticks, 1 fault) and records:
       - active_modules (from config)
       - disabled_modules (from config)
       - controller kind chosen
       - whether any LSTM/predictive/twin call path was exercised
       - whether the run was valid
       - controller_runtime
  3. Emits a JSON + Markdown report.

The script does NOT alter any algorithm — it only inspects the
runtime behaviour of each configuration to confirm that the labels
match what actually happens.
"""
from __future__ import annotations

import json
import os
import sys
import time
import importlib
from typing import Dict, List

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(THIS_DIR)))
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")
for p in (BACKEND_ROOT, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from experiments.experiment_config import ABLATION_CONFIGS  # noqa: E402
from experiments.runner import make_controller, run_single  # noqa: E402
from experiments.scenario import make_scenario  # noqa: E402

# Patch-in counters into the relevant modules so we can count
# LSTM / DigitalTwin / Predictive / Reward / DQN invocations.
import experiments.runner as _runner  # noqa: E402
import simulation.ac_power_flow  # noqa: E402

# Counter instrumentation
COUNTERS = {
    "dqn_select_action": 0,
    "lstm_predict": 0,
    "twin_sync": 0,
    "predictive_healer_run": 0,
    "reward_shaping": 0,
    "flisr_restore": 0,
}


def _trace_calls():
    """Wrap the relevant call sites with counters via monkey-patch."""
    # Wrap make_controller to wrap the returned DQN adapter so we can
    # count DQN select_action calls.
    orig_make_controller = _runner.make_controller

    def wrapped_make_controller(config):
        result = orig_make_controller(config)
        kind, controller = result
        if kind == "dqn":
            # Wrap _DQNAdapter.choose_action to count calls.
            orig_choose = controller.choose_action
            def counted_choose(state, grid_state=None):
                COUNTERS["dqn_select_action"] += 1
                return orig_choose(state, grid_state)
            # We can't easily replace method on _DQNAdapter; wrap chain.
            # Instead, monkey-patch the adapter class.
            from experiments.runner import _DQNAdapter
            _orig = _DQNAdapter.choose_action
            def _wrapped(self, state, grid_state=None):
                COUNTERS["dqn_select_action"] += 1
                return _orig(self, state, grid_state)
            _DQNAdapter.choose_action = _wrapped
        return result

    _runner.make_controller = wrapped_make_controller

    # Wrap PredictiveSelfHealer.run
    try:
        from self_healing.predictor import PredictiveSelfHealer
        _orig_run = PredictiveSelfHealer.run
        def _wrapped_run(self, grid, twin):
            COUNTERS["predictive_healer_run"] += 1
            return _orig_run(self, grid, twin)
        PredictiveSelfHealer.run = _wrapped_run
    except Exception:
        pass

    # Wrap TwinRegistry.sync
    try:
        from digital_twin.twin_registry import TwinRegistry
        _orig_sync = TwinRegistry.sync
        def _wrapped_sync(self, grid, dt_hours=1.0):
            COUNTERS["twin_sync"] += 1
            return _orig_sync(self, grid, dt_hours=dt_hours)
        TwinRegistry.sync = _wrapped_sync
    except Exception:
        pass

    # Wrap FLISR flisr_restore
    try:
        from simulation.grid import SmartGrid
        _orig_flisr = SmartGrid.flisr_restore
        def _wrapped_flisr(self):
            COUNTERS["flisr_restore"] += 1
            return _orig_flisr(self)
        SmartGrid.flisr_restore = _wrapped_flisr
    except Exception:
        pass


def _reset_counters():
    for k in COUNTERS:
        COUNTERS[k] = 0


def _verify_one(label: str, config, scenario) -> Dict[str, object]:
    _reset_counters()
    t0 = time.time()
    run = run_single(config=config, scenario=scenario)
    elapsed = time.time() - t0

    active   = config.active_modules()
    disabled = config.disabled_modules()

    expected_dqn       = "dqn" in active
    expected_lstm      = "lstm" in active
    expected_twin      = "digital_twin" in active
    expected_predictive = "predictive_healing" in active
    expected_flisr     = "flisr" in active

    # Decide whether controller is DQN, random, persistence, or rule-based.
    ctrl_kind = run.get("controller", "?")

    return {
        "label":                  label,
        "active_modules":         active,
        "disabled_modules":       disabled,
        "controller_kind":        ctrl_kind,
        "valid":                  bool(run["validity"]["valid"]),
        "invalid_reason":         run["validity"].get("invalid_reason"),
        "runtime_s":              round(elapsed, 4),
        "expected_dqn_active":       expected_dqn,
        "expected_lstm_active":      expected_lstm,
        "expected_twin_active":      expected_twin,
        "expected_predictive_active": expected_predictive,
        "expected_flisr_active":     expected_flisr,
        "counters": dict(COUNTERS),
    }


def main() -> int:
    out_dir = os.path.join("experiments", "results", "final_paper", "logs")
    os.makedirs(out_dir, exist_ok=True)

    _trace_calls()

    # Use one short scenario (5 ticks, 1 fault) for all configs.
    scenario = make_scenario(
        seed=0, total_steps=5, fault_count=1, weather_mode="normal",
        label="ablation_integrity_seed0",
    )

    results: List[Dict[str, object]] = []
    for label, cfg in ABLATION_CONFIGS.items():
        try:
            r = _verify_one(label, cfg, scenario)
        except Exception as exc:
            r = {
                "label": label,
                "error": repr(exc),
            }
        results.append(r)
        print(f"[{label}] controller={r.get('controller_kind')} "
              f"active={r.get('active_modules')} "
              f"counters={r.get('counters')}")

    # Build a per-config adoption assessment.
    adoption: Dict[str, str] = {}
    for r in results:
        if "error" in r:
            adoption[r["label"]] = f"ERROR: {r['error']}"
            continue
        c = r["counters"]
        # Check 1: DQN controller kind aligns with config
        if r["expected_dqn_active"]:
            if r["controller_kind"] == "dqn":
                adoption[r["label"]] = "OK"
            else:
                adoption[r["label"]] = (
                    f"WARN: expected dqn controller, got {r['controller_kind']}"
                )
        # Check 2: predictive healing counter aligns with toggle
        if r["expected_predictive_active"]:
            if c["predictive_healer_run"] > 0:
                pass  # good
            else:
                adoption[r["label"]] = (
                    f"WARN: predictive_healing flagged enabled but "
                    f"PredictiveSelfHealer.run was never called"
                )
        else:
            if c["predictive_healer_run"] > 0:
                adoption[r["label"]] = (
                    f"FAIL: predictive_healing flagged disabled but "
                    f"PredictiveSelfHealer.run was called {c['predictive_healer_run']} time(s)"
                )
        # Check 3: twin sync counter aligns with toggle
        if r["expected_twin_active"]:
            if c["twin_sync"] == 0:
                adoption[r["label"]] = (
                    f"WARN: digital_twin flagged enabled but "
                    f"TwinRegistry.sync was never called"
                )
        else:
            if c["twin_sync"] > 0:
                adoption[r["label"]] = (
                    f"FAIL: digital_twin flagged disabled but "
                    f"TwinRegistry.sync was called {c['twin_sync']} time(s)"
                )
        # Check 4: FLISR alignment
        if r["expected_flisr_active"]:
            if c["flisr_restore"] == 0:
                adoption[r["label"]] = (
                    f"WARN: flisr flagged enabled but flisr_restore not called"
                )
        else:
            if c["flisr_restore"] > 0:
                adoption[r["label"]] = (
                    f"FAIL: flisr flagged disabled but flisr_restore called"
                )

    report = {
        "schema_version": "1.0",
        "scenario": {
            "seed": 0,
            "ticks": 5,
            "faults": 1,
        },
        "per_config": results,
        "adoption_summary": adoption,
    }

    json_path = os.path.join(out_dir, "ablation_integrity_report.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)

    # Markdown summary
    md_lines = [
        "# EHM-simulation — Ablation Integrity Report",
        "",
        "Each pre-baked `ExperimentConfig` is run for a 5-tick scenario "
        "with one fault. The runtime instrumentation counts how many "
        "times each module (DigitalTwin, PredictiveHealer, FLISR, DQN) "
        "actually executes during the run.",
        "",
        "| Config | Controller | Active modules | Disabled modules | "
        "Twin.sync | PredictiveHeal.run | FLISR | DQN select | Adoption |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        if "error" in r:
            md_lines.append(f"| {r['label']} | ERROR | — | — | — | — | — | — |"
                            f" {r['error']} |")
            continue
        c = r["counters"]
        active = ", ".join(r["active_modules"]) or "—"
        disabled = ", ".join(r["disabled_modules"]) or "—"
        ad = adoption.get(r["label"], "OK")
        md_lines.append(
            f"| {r['label']} | {r['controller_kind']} | {active} | {disabled} | "
            f"{c['twin_sync']} | {c['predictive_healer_run']} | "
            f"{c['flisr_restore']} | {c['dqn_select_action']} | {ad} |"
        )
    with open(os.path.join(out_dir, "ablation_integrity_report.md"), "w") as f:
        f.write("\n".join(md_lines))

    print(f"Wrote {json_path}")
    print(f"Wrote {os.path.join(out_dir, 'ablation_integrity_report.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
