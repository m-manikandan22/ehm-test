"""
Verify that Experiment A's protected files have not changed since the
protection record was generated.

Run from project root with the EHM-paper conda environment activated:

    python experiments/results/final_paper/PHASE0_verify_protection.py

Exit code is non-zero if any file has drifted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Dict, List, Tuple


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",
                    default="experiments/results/final_paper/EXPERIMENT_A_PROTECTION.json")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        print(f"ERROR: {args.input} not found", file=sys.stderr)
        return 2

    with open(args.input, "r", encoding="utf-8") as f:
        rec = json.load(f)

    missing: List[str] = []
    drifted: List[Tuple[str, str, str]] = []
    ok = 0
    for rel, info in rec["files"].items():
        if not os.path.isfile(rel):
            missing.append(rel)
            continue
        actual = sha256_of(rel)
        if actual != info["sha256"]:
            drifted.append((rel, info["sha256"], actual))
        else:
            ok += 1

    print(f"Protection file: {args.input}")
    print(f"Generated at:    {rec['generated_at']}")
    print(f"Git commit:      {rec['git_commit_at_protection']}")
    print(f"Files OK:        {ok}")
    print(f"Files missing:   {len(missing)}")
    print(f"Files drifted:   {len(drifted)}")

    if missing:
        print("\nMISSING:")
        for m in missing:
            print(f"  - {m}")
    if drifted:
        print("\nDRIFTED (SHA-256 mismatch):")
        for rel, expected, actual in drifted:
            print(f"  - {rel}")
            print(f"      expected: {expected}")
            print(f"      actual:   {actual}")

    if missing or drifted:
        print("\nVERIFICATION: FAIL")
        return 1
    print("\nVERIFICATION: PASS — Experiment A is unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())