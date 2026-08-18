"""final_paper_experiment.py — Stage 37 end-to-end driver.

Runs the paper experiment in three sizes:

  1. **smoke** — 1 seed, 10 ticks, 2 faults. Should run in seconds.
  2. **medium** — 3 seeds, 30 ticks, 4 faults. Should run in < 1 min.
  3. **final** — 5 seeds, 50 ticks, 5 faults. The "publication" run.

Each size writes its outputs to ``--output-dir/{size}/`` plus a
``final_summary.json`` aggregating the three sizes.

Usage::

    python -m experiments.final_paper_experiment \
        --output-dir ../paper_final

Limitations
-----------
* The script is intentionally simple — it shells out to
  ``paper_experiment.py`` for each size rather than reimplementing
  the logic. That keeps the smoke / medium / final configs in one
  place.
* The final run is what the paper cites; smoke and medium are
  smoke-tests of the pipeline.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict


REPO = Path(__file__).resolve().parents[1]


def _run_size(*, seeds: int, ticks: int, faults: int, out_dir: Path) -> Dict[str, Any]:
    """Run paper_experiment at the given size and return wall-clock + outputs."""
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "experiments.paper_experiment",
         "--seeds", str(seeds), "--ticks", str(ticks),
         "--faults", str(faults),
         "--output-dir", str(out_dir)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=900,  # 15 min cap per size
    )
    elapsed = time.perf_counter() - t0
    summary_path = out_dir / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    return {
        "seeds": seeds,
        "ticks": ticks,
        "faults_per_run": faults,
        "wall_clock_s": elapsed,
        "exit_code": proc.returncode,
        "summary": summary,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", type=str, default="../paper_final",
                    help="Root output directory (smoke/medium/final land here).")
    args = ap.parse_args()

    root = Path(args.output_dir).resolve()
    sizes = [
        ("smoke",  dict(seeds=1, ticks=10, faults=2)),
        ("medium", dict(seeds=3, ticks=30, faults=4)),
        ("final",  dict(seeds=5, ticks=50, faults=5)),
    ]
    runs: list = []
    for name, cfg in sizes:
        print(f"=== {name} ===", flush=True)
        result = _run_size(**cfg, out_dir=root / name)
        result["size"] = name
        runs.append(result)
        print(f"  wall_clock={result['wall_clock_s']:.2f}s "
              f"exit={result['exit_code']}", flush=True)
        if result["exit_code"] != 0:
            print(f"  FAILED — see {root / name}", flush=True)
            return 1

    # Aggregate
    overall = {
        "schema_version": 1,
        "sizes": runs,
        "all_passed": all(r["exit_code"] == 0 for r in runs),
    }
    (root / "final_summary.json").write_text(
        json.dumps(overall, indent=2, default=str), encoding="utf-8",
    )
    print(f"Wrote {root / 'final_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())