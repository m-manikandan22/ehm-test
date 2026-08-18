"""
Phase 0 — Experiment A protection record generator.

This script computes SHA-256 checksums of every file in the Experiment A
result package so that subsequent integrity audits can confirm the
package is unchanged. It writes a JSON protection record. It does NOT
modify any file in the Experiment A package.

Run from project root with the EHM-paper conda environment activated:

    python experiments/results/final_paper/PHASE0_protect_experiment_A.py \
        --paper-dir paper_results \
        --output experiments/results/final_paper/EXPERIMENT_A_PROTECTION.json

The companion markdown report is rendered by PHASE0_render_protection_md.py
so the markdown can be regenerated from the JSON truth without manual
editing (preventing drift between checksums and prose).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
from typing import Dict, List, Tuple


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def list_all_files(root: str) -> List[str]:
    out: List[str] = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            out.append(os.path.relpath(full, ".").replace(os.sep, "/"))
    out.sort()
    return out


def git_head() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return out.decode("ascii", errors="ignore").strip()
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--paper-dir", default="paper_results")
    ap.add_argument("--output",
                    default="experiments/results/final_paper/EXPERIMENT_A_PROTECTION.json")
    args = ap.parse_args()

    paper_dir = args.paper_dir
    if not os.path.isdir(paper_dir):
        print(f"ERROR: {paper_dir} not found", file=sys.stderr)
        return 2

    files = list_all_files(paper_dir)
    if not files:
        print(f"ERROR: no files under {paper_dir}", file=sys.stderr)
        return 2

    # Compute checksums and per-file byte sizes.
    entries: Dict[str, Dict[str, object]] = {}
    total_bytes = 0
    for rel in files:
        full = os.path.join(".", rel)
        size = os.path.getsize(full)
        total_bytes += size
        entries[rel] = {
            "sha256": sha256_of(full),
            "bytes": size,
        }

    # Compute an aggregate hash over all file hashes in sorted order —
    # a tamper-evident fingerprint of the whole package.
    agg = hashlib.sha256()
    for rel in sorted(entries.keys()):
        agg.update(rel.encode("utf-8"))
        agg.update(b"\x00")
        agg.update(entries[rel]["sha256"].encode("ascii"))
        agg.update(b"\x00")
    aggregate = agg.hexdigest()

    record = {
        "schema_version": "1.0",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "experiment_a_status": "FROZEN — no modifications permitted",
        "paper_dir": paper_dir.replace(os.sep, "/"),
        "git_commit_at_protection": git_head(),
        "n_files": len(files),
        "total_bytes": total_bytes,
        "aggregate_sha256": aggregate,
        "files": entries,
        "notes": [
            "This file is the authoritative protection record. Any later "
            "modification to a file under paper_dir/ will cause its SHA-256 "
            "to drift from this record. Detect via PHASE0_verify_protection.py.",
            "Experiment A is not overwritten, not retroactively modified, "
            "and not deleted by Experiment B.",
            "Experiment A's null/saturation finding is a legitimate scientific "
            "result and is preserved as evidence of the need for the stress "
            "benchmark in Experiment B.",
        ],
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, sort_keys=True)

    print(f"Wrote {args.output}")
    print(f"Files protected: {len(files)}  Bytes: {total_bytes}")
    print(f"Aggregate SHA-256: {aggregate}")
    print(f"Git HEAD: {record['git_commit_at_protection']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())