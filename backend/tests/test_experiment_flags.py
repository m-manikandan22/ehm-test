"""test_experiment_flags.py — Stage 17 CLI flag behaviour.

Each ``experiments.*`` entry point must:

  1. Accept ``--seed`` (reproducibility)
  2. Accept a numeric / integer parameter (e.g. ``--max-iterations``)
  3. Accept ``--out`` to override the output path
  4. Run without any flag and produce a valid output file (defaults)
  5. Refuse unknown args cleanly (``argparse`` exits with status 2)

This file covers the topology-planning experiment; new experiments
should mirror this pattern.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    """Invoke the entry point as a subprocess and capture stdout/stderr."""
    cmd = [sys.executable, "-m", "experiments.run_topology_planning", *args]
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_cli_default_produces_output_file():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as t:
        out = Path(t.name)
    try:
        proc = _run_cli("--out", str(out))
        assert proc.returncode == 0, (
            f"CLI failed with code {proc.returncode}: {proc.stderr}"
        )
        assert out.exists()
        with open(out) as f:
            data = json.load(f)
        # Schema sanity
        assert data["max_iterations"] >= 1
        assert "kpis_before" in data
    finally:
        if out.exists():
            out.unlink()


def test_cli_seed_is_accepted_and_recorded():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as t:
        out = Path(t.name)
    try:
        proc = _run_cli("--seed", "17", "--out", str(out))
        assert proc.returncode == 0, proc.stderr
        with open(out) as f:
            data = json.load(f)
        assert data["seed"] == 17
    finally:
        if out.exists():
            out.unlink()


def test_cli_max_iterations_is_accepted():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as t:
        out = Path(t.name)
    try:
        proc = _run_cli("--max-iterations", "3", "--out", str(out))
        assert proc.returncode == 0, proc.stderr
        with open(out) as f:
            data = json.load(f)
        assert data["max_iterations"] == 3
    finally:
        if out.exists():
            out.unlink()


def test_cli_rejects_unknown_flag_cleanly():
    proc = _run_cli("--no-such-flag")
    # argparse exits with status 2 on unknown flag
    assert proc.returncode == 2, (
        f"Expected argparse exit 2, got {proc.returncode}: {proc.stderr}"
    )


def test_cli_help_prints_usage(capsys):
    proc = _run_cli("--help")
    assert proc.returncode == 0
    assert "--seed" in proc.stdout
    assert "--max-iterations" in proc.stdout
    assert "--out" in proc.stdout