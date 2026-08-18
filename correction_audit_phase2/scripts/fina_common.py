"""Shared helpers for the corrected Experiment-B final audit pipeline.

Reads ONLY the corrected 540-run raw dataset and the legitimate
Experiment-A dataset. No reruns. No parameter changes.
"""
from __future__ import annotations

import json
import os
import statistics
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORRECTED_B = os.path.join(
    os.path.dirname(ROOT),
    "correction_audit_phase1",
    "experiment_B_corrected_rerun",
    "experiment_B_runs.json",
)
EXP_A_BASELINE = os.path.join(os.path.dirname(ROOT), "paper_results", "raw", "baseline_results.json")
EXP_A_ABLATION = os.path.join(os.path.dirname(ROOT), "paper_results", "raw", "ablation_results.json")

POLICIES = [
    "persistence", "random", "rule_based", "dqn_core_only",
    "full_stack", "no_lstm", "no_twin", "no_predictive", "no_reward",
]
STRESS_LEVELS = ["moderate", "severe"]

# Pre-registered primary outcomes (name, metric, direction, effect threshold)
PRIMARY_OUTCOMES = [
    {
        "key": "PO1_ens",
        "metric": "stress_cumulative_unserved_energy",
        "direction": "lower",           # lower is better
        "threshold": "median reduction >= 5%",
        "threshold_kind": "rel_pct",
        "threshold_value": 5.0,
    },
    {
        "key": "PO2_restoration_time",
        "metric": "resilience_time_to_50pct_restoration",
        "direction": "lower",
        "threshold": "median reduction >= 5%",
        "threshold_kind": "rel_pct",
        "threshold_value": 5.0,
    },
    {
        "key": "PO3_critical_load",
        "metric": "stress_critical_load_restored_pct",
        "direction": "higher",          # higher is better
        "threshold": "median improvement >= 2 pp",
        "threshold_kind": "abs_pp",
        "threshold_value": 2.0,
    },
    {
        "key": "PO4_saidi",
        "metric": "saidi",
        "direction": "lower",
        "threshold": "median reduction >= 5%",
        "threshold_kind": "rel_pct",
        "threshold_value": 5.0,
    },
]

BASELINE_PAIRS = [
    ("full_stack", "persistence"),
    ("full_stack", "random"),
    ("full_stack", "rule_based"),
    ("full_stack", "dqn_core_only"),
]
ABLATION_PAIRS = [
    ("full_stack", "no_lstm"),
    ("full_stack", "no_twin"),
    ("full_stack", "no_predictive"),
    ("full_stack", "no_reward"),
]
ALL_PAIRS = BASELINE_PAIRS + ABLATION_PAIRS

# Module counters per policy group (expected activation from frozen config).
FLISR_POLICIES = {"rule_based", "dqn_core_only", "full_stack", "no_lstm", "no_twin", "no_predictive", "no_reward"}
LSTM_POLICIES = {"full_stack", "no_twin", "no_predictive", "no_reward"}
TWIN_POLICIES = {"full_stack", "no_lstm", "no_predictive", "no_reward"}
PREDICTIVE_POLICIES = {"full_stack", "no_lstm", "no_twin", "no_reward"}
DQN_POLICIES = {"dqn_core_only", "full_stack", "no_lstm", "no_twin", "no_predictive", "no_reward"}


def load_corrected_b() -> pd.DataFrame:
    with open(CORRECTED_B, encoding="utf-8") as f:
        d = json.load(f)
    rows = []
    for r in d["runs"]:
        m = r.get("metrics", {})
        mc = m.get("module_call_counts", {})
        row = {
            "seed": int(r.get("seed")),
            "stress_level": str(r.get("stress_level")),
            "policy": str(r.get("policy")),
            "controller_label": str(r.get("controller_label")),
            "valid": bool(r.get("valid", r.get("validity", {}).get("valid", False))),
            "invalid_reason": (r.get("validity") or {}).get("invalid_reason", ""),
        }
        for k, v in m.items():
            if k == "module_call_counts":
                continue
            if k in ("faults",):
                row["n_fault_records"] = len(v)
                continue
            if isinstance(v, (int, float)):
                row[k] = float(v)
            elif isinstance(v, str):
                row[k] = v
        for k, v in mc.items():
            row["mc_" + k] = int(v)
        rows.append(row)
    return pd.DataFrame(rows)


def load_exp_a() -> pd.DataFrame:
    with open(EXP_A_BASELINE, encoding="utf-8") as f:
        base = json.load(f)
    with open(EXP_A_ABLATION, encoding="utf-8") as f:
        abl = json.load(f)
    rows = []
    for src in (base, abl):
        for r in src["runs"]:
            m = r.get("metrics", {})
            row = {
                "seed": int(r.get("seed")),
                "policy": str(r.get("policy")),
                "condition": "nominal",
                "valid": bool(r.get("valid", (r.get("validity") or {}).get("valid", False))),
            }
            for k, v in m.items():
                if isinstance(v, (int, float)):
                    row[k] = float(v)
            rows.append(row)
    df = pd.DataFrame(rows)
    # Drop exact duplicate (seed, policy) rows (baseline full_stack duplicates
    # the ablation full_stack records).
    return df.drop_duplicates(subset=["seed", "policy"])


def _ci95_t(xs: np.ndarray) -> Tuple[float, float]:
    n = len(xs)
    if n < 2:
        return float(xs[0]) if n else 0.0, float(xs[0]) if n else 0.0
    m = float(np.mean(xs))
    s = float(np.std(xs, ddof=1))
    tcrit = float(stats.t.ppf(0.975, df=n - 1))
    half = tcrit * s / np.sqrt(n)
    return m - half, m + half


def paired_stats(a: np.ndarray, b: np.ndarray) -> Dict[str, Any]:
    """Paired comparison A vs B. diffs = a - b."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    n = len(a)
    diffs = a - b
    zero_diff = np.all(np.abs(diffs) < 1e-12)

    stat_w, p_w = 0.0, 1.0
    if not zero_diff:
        try:
            res = stats.wilcoxon(a, b, zero_method="wilcox", method="asymptotic")
            stat_w, p_w = float(res.statistic), float(res.pvalue)
        except Exception:
            stat_w, p_w = 0.0, 1.0
    if p_w is None or np.isnan(p_w):
        p_w = 1.0

    t_stat, p_t = 0.0, 1.0
    if not zero_diff:
        try:
            res = stats.ttest_rel(a, b)
            t_stat, p_t = float(res.statistic), float(res.pvalue)
        except Exception:
            t_stat, p_t = 0.0, 1.0
    if p_t is None or np.isnan(p_t):
        p_t = 1.0

    sd_diff = float(np.std(diffs, ddof=1)) if n > 1 else 0.0
    d_cohen = float(np.mean(diffs) / sd_diff) if sd_diff > 0 else 0.0
    cliff = float(np.mean(np.sign(diffs))) if n else 0.0

    rel = np.nan
    denom = b
    if zero_diff:
        rel = 0.0
    else:
        pos = denom[denom > 1e-9]
        if len(pos) == n:
            rel = float(np.median((diffs[denom > 1e-9] / denom[denom > 1e-9]) * 100.0))
        else:
            rel = float("nan")

    lo, hi = _ci95_t(diffs)
    return {
        "n": int(n),
        "mean_a": float(np.mean(a)),
        "sd_a": float(np.std(a, ddof=1)) if n > 1 else 0.0,
        "median_a": float(np.median(a)),
        "iqr_a": float(np.subtract(*np.percentile(a, [75, 25]))),
        "mean_b": float(np.mean(b)),
        "sd_b": float(np.std(b, ddof=1)) if n > 1 else 0.0,
        "median_b": float(np.median(b)),
        "iqr_b": float(np.subtract(*np.percentile(b, [75, 25]))),
        "ci95_diff_low": lo,
        "ci95_diff_high": hi,
        "mean_diff": float(np.mean(diffs)),
        "median_diff": float(np.median(diffs)),
        "rel_diff_pct": rel,
        "wilcoxon_stat": stat_w,
        "wilcoxon_p": p_w,
        "t_stat": t_stat,
        "t_p": p_t,
        "cohens_d": d_cohen,
        "cliffs_delta": cliff,
        "zero_diff_all": bool(zero_diff),
    }


def holm_adjust(pvals: List[float]) -> List[float]:
    """Holm-Bonferroni adjusted p-values (same family, increasing order)."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank in range(m):
        idx = order[rank]
        val = min(1.0, (m - rank) * pvals[idx])
        running = max(running, val)
        adjusted[idx] = running
    return adjusted


def fmt(x: Any, nd: int = 4) -> str:
    if x is None:
        return "nan"
    try:
        if isinstance(x, str):
            return x
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    if np.isnan(x):
        return "nan"
    if np.isfinite(x):
        return f"{x:.{nd}f}"
    return str(x)


def esc_p(p: float) -> str:
    if p is None or np.isnan(p):
        return "nan"
    return f"{p:.4g}"
