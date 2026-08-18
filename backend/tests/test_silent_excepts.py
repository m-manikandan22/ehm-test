"""test_silent_excepts.py — Regression net for previously-silent except blocks.

These tests assert that bugs the silent ``except Exception: pass`` blocks
used to mask now surface. They are *not* tests of expected behaviour;
they are tests that the safety nets are gone.

If a test in this file fails, it almost always means we silently
re-introduced an exception swallow somewhere.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest


_BACKEND = Path(__file__).resolve().parent.parent


# Files we touched during the silent-except cleanup.
# If you intentionally add a silent except in one of these, update
# this list and document the rationale in a docstring above the block.
_FILES_ALLOWED_TO_KEEP_SILENT_EXCEPTS: dict[str, str] = {
    # The tests/test_integration.py file is the regression net for
    # solver robustness; it now expects update_power_flow() to raise.
    "simulation/power_flow.py": (
        "_get_impedance catches per-edge lookup failures and "
        "synthesises defaults — this is a known acceptable case."
    ),
    "simulation/scada.py": (
        "FLISR per-cluster tie scoring catches broad exceptions to fall "
        "back to penalty=999; documented at scada.py."
    ),
}


def _scan_for_silent_excepts(path: Path) -> list[tuple[int, str]]:
    """Return (line_number, line_text) for every ``except Exception: pass``."""
    text = path.read_text(encoding="utf-8", errors="replace")
    hits: list[tuple[int, str]] = []
    # Multi-line: ``except Exception:\n  pass`` (any indent).
    pattern = re.compile(
        r"except[^:]*Exception[^:]*:\s*\n\s+pass\b",
        re.MULTILINE,
    )
    for m in pattern.finditer(text):
        line_no = text.count("\n", 0, m.start()) + 1
        line = text.splitlines()[line_no - 1]
        hits.append((line_no, line))
    return hits


def test_no_silent_except_in_improvement_routes():
    """``backend/api/improvement_routes.py`` must not silently swallow exceptions."""
    src = (_BACKEND / "api" / "improvement_routes.py").read_text(encoding="utf-8")
    pattern = re.compile(r"except[^\n]*:\s*\n\s+pass\b", re.MULTILINE)
    matches = list(pattern.finditer(src))
    assert not matches, (
        "Silent except:pass found in api/improvement_routes.py: "
        f"{[m.start() for m in matches]}"
    )


def test_no_silent_except_in_routes_main():
    """``backend/api/routes.py`` must not silently swallow exceptions in /simulate."""
    src = (_BACKEND / "api" / "routes.py").read_text(encoding="utf-8")
    pattern = re.compile(r"except[^\n]*:\s*\n\s+pass\b", re.MULTILINE)
    matches = list(pattern.finditer(src))
    assert not matches, (
        "Silent except:pass found in api/routes.py: "
        f"{[m.start() for m in matches]}"
    )


def test_no_silent_except_integration_test():
    """``backend/tests/test_integration.py`` must not wrap solver calls in try/except/pass."""
    src = (_BACKEND / "tests" / "test_integration.py").read_text(encoding="utf-8")
    pattern = re.compile(
        r"update_power_flow\(\)\s*\n\s+except[^\n]*:\s*\n\s+pass\b",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(src))
    assert not matches, (
        "test_integration.py wraps update_power_flow in silent except: "
        f"{[m.start() for m in matches]}"
    )


def test_autonomous_logs_snapshot_failures():
    """``AutonomousImprovementLoop.step`` must log snapshot failures."""
    from improvement.autonomous import AutonomousImprovementLoop
    src = inspect.getsource(AutonomousImprovementLoop.step)
    # The new behaviour: log a warning. Old behaviour: pass.
    assert "logger.warning" in src, (
        "AutonomousImprovementLoop.step should call logger.warning on snapshot "
        "failures (no silent 'pass')."
    )


def test_improvement_routes_run_returns_step_failures():
    """``POST /improvement/run`` must report step failures in its response."""
    from api.improvement_routes import improvement_run
    src = inspect.getsource(improvement_run)
    assert "step_failures" in src, (
        "improvement_run should count step_failures and include them in the "
        "response so callers can invalidate the run."
    )


def test_routes_simulate_returns_reliability_error():
    """``POST /simulate`` must surface reliability-recorder failures."""
    from api import routes as _routes_mod  # noqa: F401 (smoke import)
    src = inspect.getsource(_routes_mod)
    assert "reliability_error" in src, (
        "routes.py should set reliability_error in /simulate response."
    )
