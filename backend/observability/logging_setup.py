"""
logging_setup.py — single root logger + child loggers for every module.

Why a single root logger?
-------------------------
The previous codebase had ad-hoc `logging.getLogger(__name__)` calls
scattered across files with no agreed format.  An IEEE reviewer who runs
the benchmark expects to be able to grep for a single, well-known logger
name and see a consistent time-stamped record.  This module gives us:

  - One root logger `ehm` (configurable via `EHM_LOG_LEVEL`).
  - Child loggers: `ehm.grid`, `ehm.scada`, `ehm.rl`, `ehm.lstm`,
    `ehm.fault`, `ehm.attack`, `ehm.metrics`, `ehm.city`, `ehm.twin`,
    `ehm.weather`, `ehm.fault_injector`, `ehm.microgrid`, `ehm.xai`,
    `ehm.improvement`, `ehm.planner`.
  - A JSON formatter for production and a concise formatter for dev.
  - Idempotent `setup_logging()` so callers can invoke it any number of
    times without duplicating handlers.

Backward compatibility
----------------------
The old code that does `logging.getLogger(__name__)` is not affected.
We attach a single handler to the `ehm` logger at level WARNING by
default; the root `logging` module remains untouched so other libraries
(torch, fastapi, uvicorn) keep their own log streams.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional

_ROOT_NAME = "ehm"
_CHILD_NAMES = (
    "grid", "scada", "rl", "lstm", "fault", "attack", "metrics",
    "city", "twin", "weather", "fault_injector", "microgrid", "xai",
    "improvement", "planner",
)


class _JsonFormatter(logging.Formatter):
    """Minimal JSON line formatter for production use."""

    _RESERVED = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message", "asctime", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        import json
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Pass-through extras (e.g. timestep=, node_id=) that callers
        # attached via logger.info("...", extra={...}).
        for k, v in record.__dict__.items():
            if k in self._RESERVED or k.startswith("_"):
                continue
            try:
                json.dumps(v)
                payload[k] = v
            except TypeError:
                payload[k] = repr(v)
        return json.dumps(payload, separators=(",", ":"))


_configured = False


def setup_logging(
    level: Optional[str] = None,
    json_format: Optional[bool] = None,
) -> logging.Logger:
    """Idempotently configure the `ehm` logger and return it.

    Parameters
    ----------
    level : str, optional
        "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL".  Defaults
        to the value of `EHM_LOG_LEVEL` env var, or "INFO".
    json_format : bool, optional
        If True, use the JSON formatter.  Defaults to True when
        `EHM_LOG_JSON=1` env var is set, otherwise False (human-friendly).
    """
    global _configured
    root = logging.getLogger(_ROOT_NAME)
    if _configured:
        # Allow re-configuration for tests.
        if level is not None:
            root.setLevel(_parse_level(level))
        return root

    if level is None:
        level = os.environ.get("EHM_LOG_LEVEL", "INFO")
    if json_format is None:
        json_format = os.environ.get("EHM_LOG_JSON", "0") == "1"

    root.setLevel(_parse_level(level))
    # Do not propagate to Python's root logger — keeps our output separate
    # from uvicorn's stream unless the operator wires them up.
    root.propagate = False

    handler = logging.StreamHandler(stream=sys.stdout)
    if json_format:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname).1s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )
    root.addHandler(handler)

    # Pre-create child loggers so they show up in logging.Logger.manager
    # even before any module logs to them.  Cheap, and helps debugging.
    for child in _CHILD_NAMES:
        logging.getLogger(f"{_ROOT_NAME}.{child}")

    _configured = True
    return root


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the `ehm` namespace.

    Usage: `log = get_logger("grid")` produces a logger named `ehm.grid`.
    Calling this *also* calls `setup_logging()` once, so callers don't
    need to wire logging up themselves.
    """
    if not name.startswith(_ROOT_NAME + ".") and name != _ROOT_NAME:
        name = f"{_ROOT_NAME}.{name}"
    setup_logging()
    return logging.getLogger(name)


def _parse_level(level: str) -> int:
    level = (level or "").upper()
    return getattr(logging, level, logging.INFO)
