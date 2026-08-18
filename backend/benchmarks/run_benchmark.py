#!/usr/bin/env python
"""
run_benchmark.py — CLI entry point for the benchmark runner.

Usage:
    python benchmarks/run_benchmark.py --seeds 30 --output benchmarks/results/full.json
"""
from benchmarks.runner import main

if __name__ == "__main__":
    main()