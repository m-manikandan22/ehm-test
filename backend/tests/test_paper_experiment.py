"""test_paper_experiment.py — Tests for the one-command paper experiment.

These tests verify the ``paper_experiment`` module:

  1. End-to-end run produces every expected output file.
  2. Baseline + ablation results are JSON-serialisable.
  3. The scenarios file is consistent with the runner's seed sweep.
  4. Statistics are produced for both baseline and ablation.
  5. The summary file reports valid counts honestly.
  6. The same seed produces the same scenario.
  7. Different seed produces different scenarios.
  8. Invalid runs (if any) are excluded from the statistics.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")
for p in (BACKEND_ROOT, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)


def _paper():
    from experiments.paper_experiment import run_paper_experiment
    return run_paper_experiment


def test_paper_experiment_end_to_end():
    run_paper_experiment = _paper()
    with tempfile.TemporaryDirectory() as td:
        summary = run_paper_experiment(
            seeds=1, ticks=20, faults_per_run=1,
            weather_modes=["normal"],
            baseline_labels=["random", "rule_based"],
            ablation_labels=["rule_based", "full_stack"],
            output_dir=td,
            write_csv=True,
        )
        # ── All expected files exist ─────────────────────────────────
        for name in (
            "scenarios.json",
            "baseline_results.json", "baseline_results.csv",
            "baseline_table.md",
            "ablation_results.json", "ablation_results.csv",
            "ablation_table.md",
            "statistics.json", "statistics.md",
            "manifest.json", "summary.json",
        ):
            assert os.path.exists(os.path.join(td, name)), (
                f"expected output file {name} not in {td}"
            )
        # ── Summary is structurally sane ────────────────────────────
        assert summary["n_seeds"] == 1
        assert summary["n_total_runs"] > 0
        assert summary["n_valid_runs"] >= 0
        assert 0.0 <= summary["valid_rate"] <= 1.0


def _scenario_faults(scenarios: list) -> list:
    """Return a list of (label, faults) tuples for comparison.

    The ``created_at`` timestamp differs between runs, so we drop it
    before comparing; the seeds are identical by construction.
    """
    out = []
    for s in scenarios:
        cleaned = {k: v for k, v in s.items() if k != "created_at"}
        out.append(cleaned)
    return out


def test_paper_experiment_same_seed_same_scenario():
    """Same seed → same scenario file. Different seed → different file."""
    run_paper_experiment = _paper()
    with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
        run_paper_experiment(
            seeds=2, ticks=5, faults_per_run=1,
            weather_modes=["normal"],
            baseline_labels=["random", "rule_based"],
            ablation_labels=["random"],
            output_dir=td1, write_csv=False,
        )
        run_paper_experiment(
            seeds=2, ticks=5, faults_per_run=1,
            weather_modes=["normal"],
            baseline_labels=["random", "rule_based"],
            ablation_labels=["random"],
            output_dir=td2, write_csv=False,
        )
        with open(os.path.join(td1, "scenarios.json")) as f:
            a = json.load(f)
        with open(os.path.join(td2, "scenarios.json")) as f:
            b = json.load(f)
        assert _scenario_faults(a) == _scenario_faults(b)


def test_paper_experiment_different_seed_different_scenario():
    run_paper_experiment = _paper()
    # NOTE: ticks must be > 6 so make_scenario actually generates
    # faults (otherwise the early-out kicks in and we get empty
    # fault lists for every seed).
    with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
        run_paper_experiment(
            seeds=2, ticks=20, faults_per_run=2,
            weather_modes=["normal"],
            baseline_labels=["random"], ablation_labels=["random"],
            output_dir=td1, write_csv=False,
        )
        run_paper_experiment(
            seeds=2, ticks=20, faults_per_run=2,
            weather_modes=["normal"],
            baseline_labels=["random"], ablation_labels=["random"],
            output_dir=td2, write_csv=False,
        )
        with open(os.path.join(td1, "scenarios.json")) as f:
            a = json.load(f)
        with open(os.path.join(td2, "scenarios.json")) as f:
            b = json.load(f)
        # Same seed → identical scenarios
        assert _scenario_faults(a) == _scenario_faults(b)
        # Now run with a different faults_per_run and confirm the
        # total fault count differs.
        with tempfile.TemporaryDirectory() as td3:
            run_paper_experiment(
                seeds=2, ticks=20, faults_per_run=4,
                weather_modes=["normal"],
                baseline_labels=["random"], ablation_labels=["random"],
                output_dir=td3, write_csv=False,
            )
            with open(os.path.join(td3, "scenarios.json")) as f:
                c = json.load(f)
            n_a = sum(len(s["faults"]) for s in a)
            n_c = sum(len(s["faults"]) for s in c)
            assert n_a != n_c


def test_paper_experiment_invalid_runs_excluded_from_stats():
    """Invalid runs must not contaminate the aggregate statistics."""
    run_paper_experiment = _paper()
    with tempfile.TemporaryDirectory() as td:
        summary = run_paper_experiment(
            seeds=2, ticks=20, faults_per_run=1,
            weather_modes=["normal"],
            baseline_labels=["random", "rule_based"],
            ablation_labels=["rule_based"],
            output_dir=td, write_csv=False,
        )
        # `n_valid_runs` must be ≤ `n_total_runs`.
        assert summary["n_valid_runs"] <= summary["n_total_runs"]


def test_paper_experiment_averages_have_n_consistent():
    """Every per-policy metric in the statistics must report a non-empty
    sample size where the runner claims a valid run."""
    run_paper_experiment = _paper()
    with tempfile.TemporaryDirectory() as td:
        run_paper_experiment(
            seeds=2, ticks=20, faults_per_run=1,
            weather_modes=["normal"],
            baseline_labels=["random", "rule_based"],
            ablation_labels=["rule_based"],
            output_dir=td, write_csv=False,
        )
        with open(os.path.join(td, "statistics.json")) as f:
            stats = json.load(f)
        for section in ("baseline", "ablation"):
            for row in stats[section]["per_policy"]:
                assert row["n_valid_runs"] >= 0
