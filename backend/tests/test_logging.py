"""test_logging.py — tests for the logging setup module."""
from __future__ import annotations

import io
import json
import logging

import pytest

from observability.logging_setup import (
    get_logger,
    setup_logging,
    _parse_level,
)


@pytest.fixture(autouse=True)
def reset_logging_state():
    """Re-import friendly: clear handlers so each test starts clean."""
    import observability.logging_setup as m
    m._configured = False
    root = logging.getLogger("ehm")
    root.handlers.clear()
    root.setLevel(logging.NOTSET)
    yield
    root.handlers.clear()


def test_setup_logging_is_idempotent():
    a = setup_logging(level="INFO")
    b = setup_logging(level="DEBUG")  # second call should not duplicate
    assert a is b
    handlers = logging.getLogger("ehm").handlers
    assert len(handlers) == 1


def test_get_logger_returns_namespaced_child():
    log = get_logger("grid")
    assert log.name == "ehm.grid"
    log.info("hello")
    # Stream not asserted; just ensure it doesn't raise.


def test_get_logger_does_not_rewrite_existing_name():
    log = get_logger("ehm.scada")
    assert log.name == "ehm.scada"


def test_default_level_is_info():
    setup_logging()
    assert logging.getLogger("ehm").level == logging.INFO


def test_level_override():
    setup_logging(level="DEBUG")
    assert logging.getLogger("ehm").level == logging.DEBUG


def test_parse_level_falls_back_to_info():
    assert _parse_level("bogus") == logging.INFO
    assert _parse_level("") == logging.INFO
    assert _parse_level("warning") == logging.WARNING


def test_json_formatter_renders_valid_json(capsys):
    setup_logging(json_format=True, level="INFO")
    log = get_logger("metrics")
    log.info("step", extra={"timestep": 5, "score": 0.91})
    captured = capsys.readouterr().out
    lines = [ln for ln in captured.splitlines() if ln.strip()]
    assert lines, "expected at least one log line"
    payload = json.loads(lines[-1])
    assert payload["logger"] == "ehm.metrics"
    assert payload["level"] == "INFO"
    assert payload["msg"] == "step"
    assert payload["timestep"] == 5
    assert payload["score"] == 0.91


def test_json_formatter_swallows_unserialisable_extras(capsys):
    setup_logging(json_format=True, level="INFO")
    log = get_logger("twin")
    # `set` is not JSON-serialisable — the formatter must not raise.
    log.info("snapshot", extra={"ids": {1, 2, 3}})
    captured = capsys.readouterr().out
    line = next(ln for ln in captured.splitlines() if ln.strip())
    payload = json.loads(line)
    assert "ids" in payload
    assert isinstance(payload["ids"], str)  # repr'd as string
