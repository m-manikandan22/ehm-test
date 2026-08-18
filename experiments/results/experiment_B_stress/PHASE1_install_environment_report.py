"""
Phase 1 — Authoritative environment report generator.

Reads the *actual* installed versions from the active EHM-paper Python
interpreter and writes a JSON report. This is the single source of truth
for the environment section of any experiment manifest.

Run from project root with the EHM-paper conda environment activated:

    C:/Users/ELCOT/miniconda3/envs/EHM-paper/python.exe \
        experiments/results/experiment_B_stress/PHASE1_install_environment_report.py \
        --output experiments/results/experiment_B_stress/environment_report.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import subprocess
import sys
from typing import Any, Dict


def _detect_windows_release(plat: platform) -> str:
    """Detect the actual Windows release, since platform.release() can
    return '10' on Windows 11.

    Returns "<Windows-Edition> <Version>" string.
    """
    try:
        if plat.system().lower().startswith("windows"):
            try:
                # Win10+, returns e.g. (10, 0, 22631, ...)
                import sys as _sys  # noqa: WPS433
                ver = _sys.getwindowsversion()  # type: ignore[attr-defined]
                build = ver.build
                if build >= 22000:
                    return f"Windows 11 (build {build})"
                return f"Windows {ver.major} (build {build})"
            except Exception:
                pass
            return f"{plat.system()} {plat.release()}"
        return f"{plat.system()} {plat.release()}"
    except Exception:
        return "unknown"


def _safe_version(import_name: str, attr: str = "__version__") -> str:
    try:
        mod = __import__(import_name)
        return str(getattr(mod, attr, "unknown"))
    except ImportError:
        return "missing"
    except Exception as exc:  # noqa: BLE001
        return f"error:{exc!r}"


def _git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL, timeout=5,
        )
        return out.decode("ascii", errors="ignore").strip()
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--output",
        default="experiments/results/experiment_B_stress/environment_report.json",
    )
    args = ap.parse_args()

    report: Dict[str, Any] = {
        "schema_version": "1.0",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "os": _detect_windows_release(platform),
        "packages": {
            "numpy":      _safe_version("numpy"),
            "torch":      _safe_version("torch"),
            "networkx":   _safe_version("networkx"),
            "scikit-learn": _safe_version("sklearn"),
            "pandapower": _safe_version("pandapower"),
            "pandas":     _safe_version("pandas"),
            "fastapi":    _safe_version("fastapi"),
            "pydantic":   _safe_version("pydantic"),
            "yaml":       _safe_version("yaml"),
        },
    }
    try:
        import torch  # noqa: F401
        report["cuda"] = (
            "available" if torch.cuda.is_available() else "unavailable"
        )
    except ImportError:
        report["cuda"] = "missing"
    report["torch_device"] = (
        "cuda" if report["cuda"] == "available" else "cpu"
    )
    report["git_commit"] = _git_commit()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print(json.dumps(report, indent=2))
    print(f"\nWrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
