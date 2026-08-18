"""Generate the research environment report for the paper experiment.

Produces both JSON and Markdown versions of the environment snapshot.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone


def _git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return out.decode("ascii", errors="ignore").strip()
    except Exception:
        return "unknown"


def _safe_import_version(name: str):
    try:
        mod = __import__(name)
        return getattr(mod, "__version__", "unknown")
    except Exception as exc:
        return f"IMPORT_ERROR: {exc}"


def _run_cmd(cmd):
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=10)
        return out.decode("utf-8", errors="ignore").strip()
    except Exception as exc:
        return f"ERROR: {exc}"


def main() -> int:
    out_dir = os.path.join("experiments", "results", "final_paper", "environment")
    os.makedirs(out_dir, exist_ok=True)

    pkg_versions = {
        "python":      f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "numpy":       _safe_import_version("numpy"),
        "torch":       _safe_import_version("torch"),
        "networkx":    _safe_import_version("networkx"),
        "scikit-learn": _safe_import_version("sklearn"),
        "pandapower":  _safe_import_version("pandapower"),
        "fastapi":     _safe_import_version("fastapi"),
        "pydantic":    _safe_import_version("pydantic"),
        "pyyaml":      _safe_import_version("yaml"),
        "networkx":    _safe_import_version("networkx"),
    }

    cuda_available = False
    try:
        import torch
        cuda_available = bool(torch.cuda.is_available())
        pkg_versions["cuda_available"] = "yes" if cuda_available else "no"
        pkg_versions["torch_device"] = (
            f"cuda:{torch.cuda.get_device_name(0)}" if cuda_available else "cpu"
        )
    except Exception:
        pkg_versions["cuda_available"] = "unknown"
        pkg_versions["torch_device"] = "unknown"

    platform_report = {
        "platform":          platform.platform(),
        "system":            platform.system(),
        "release":           platform.release(),
        "machine":           platform.machine(),
        "processor":         platform.processor(),
        "python_implementation": platform.python_implementation(),
    }

    # Check pandapower import usability
    try:
        import pandapower as pp
        pp.create_empty_network(name="env_check")
        pandapower_ok = True
    except Exception as exc:
        pandapower_ok = False
        pkg_versions["pandapower_error"] = repr(exc)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit":   _git_commit(),
        "platform":     platform_report,
        "cuda_available": cuda_available,
        "package_versions": pkg_versions,
        "pandapower_usable": pandapower_ok,
        "python_executable": sys.executable,
    }

    json_path = os.path.join(out_dir, "environment_report.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    md_path = os.path.join(out_dir, "environment_report.md")
    lines = []
    lines.append("# EHM-simulation — Research Environment Report")
    lines.append("")
    lines.append(f"_Generated: {report['generated_at']}_")
    lines.append(f"_Git commit: `{report['git_commit']}`_")
    lines.append("")
    lines.append("## Platform")
    for k, v in platform_report.items():
        lines.append(f"- **{k}**: `{v}`")
    lines.append("")
    lines.append("## CUDA")
    lines.append(f"- CUDA available: **{'yes' if cuda_available else 'no'}**")
    if cuda_available:
        lines.append(f"- PyTorch device: `{pkg_versions.get('torch_device', 'unknown')}`")
    else:
        lines.append("- PyTorch device: `cpu`")
    lines.append("")
    lines.append("## Package versions")
    for k, v in pkg_versions.items():
        lines.append(f"- **{k}**: `{v}`")
    lines.append("")
    lines.append("## Pandapower check")
    lines.append(f"- Pandapower usable for IEEE-13 reference: **{pandapower_ok}**")
    lines.append("")
    with open(md_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
