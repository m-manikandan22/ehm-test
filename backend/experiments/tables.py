"""tables.py — Per-policy and paired-comparison tables for the paper.

Built on top of ``experiments.runner``. Given the manifest produced by
``run_experiment``, this module produces:

  * ``per_policy``  : one row per (controller, weather_mode, metric)
    with the mean / std over seeds.
  * ``paired``      : per-metric paired difference between each config
    and the anchor config (default: rule_based).

Both tables are serialisable to JSON; ``render_markdown`` returns a
human-readable Markdown string suitable for the paper appendix.
"""
from __future__ import annotations

import math
import statistics
from typing import Dict, List, Optional


_METRIC_KEYS = (
    "n_faults", "n_restored", "restoration_rate",
    "avg_restoration_steps", "actions_taken",
    "illegal_actions_attempted", "voltage_violation_count",
    "critical_load_interruption_steps",
    "total_customer_minutes_interrupted", "energy_not_served_mwh",
    "n_steps",
)


def _safe_mean(xs: List[float]) -> Optional[float]:
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return sum(xs) / len(xs)


def _safe_std(xs: List[float]) -> Optional[float]:
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return 0.0 if xs else None
    try:
        return statistics.stdev(xs)
    except statistics.StatisticsError:
        return 0.0


def build_report(
    *,
    runs: List[dict],
    anchor_label: str = "rule_based",
) -> dict:
    """Build per-policy and paired tables from a list of run dicts.

    Parameters
    ----------
    runs : list of dict
        Output of ``run_experiment``'s ``manifest["runs"]``.
    anchor_label : str
        The label whose per-seed metrics are subtracted from every
        other config's per-seed metrics to build the paired table.

    Returns
    -------
    dict
        ``{"per_policy": [...], "paired": [...]}``
    """
    # Group runs by (controller, weather) and metric
    buckets: Dict[tuple, List[dict]] = {}
    for r in runs:
        key = (r.get("controller_label", "?"), r.get("weather_mode", "?"))
        buckets.setdefault(key, []).append(r)

    per_policy: List[dict] = []
    for (label, weather), bucket in sorted(buckets.items()):
        row = {"controller_label": label, "weather_mode": weather}
        for mk in _METRIC_KEYS:
            vals = [r["metrics"].get(mk) for r in bucket]
            row[f"{mk}_mean"] = _safe_mean(vals)
            row[f"{mk}_std"] = _safe_std(vals)
            row[f"{mk}_n"] = len(vals)
        per_policy.append(row)

    # Paired table: same metric, anchor subtracted
    paired: List[dict] = []
    # Group by seed_id + weather for pairing
    by_seed: Dict[tuple, Dict[str, dict]] = {}
    for r in runs:
        key = (r.get("seed_id"), r.get("weather_mode"))
        by_seed.setdefault(key, {})[r.get("controller_label", "?")] = r

    other_labels = sorted({
        r.get("controller_label") for r in runs
        if r.get("controller_label") != anchor_label
    })

    for other in other_labels:
        diffs_per_metric: Dict[str, List[float]] = {mk: [] for mk in _METRIC_KEYS}
        n_pairs = 0
        for key, by_label in by_seed.items():
            if anchor_label not in by_label or other not in by_label:
                continue
            anchor_run = by_label[anchor_label]
            other_run = by_label[other]
            n_pairs += 1
            for mk in _METRIC_KEYS:
                a = anchor_run["metrics"].get(mk)
                b = other_run["metrics"].get(mk)
                if a is not None and b is not None:
                    diffs_per_metric[mk].append(b - a)
        row = {
            "controller_label": other,
            "anchor_label": anchor_label,
            "n_pairs": n_pairs,
        }
        for mk in _METRIC_KEYS:
            row[f"delta_{mk}_mean"] = _safe_mean(diffs_per_metric[mk])
            row[f"delta_{mk}_std"] = _safe_std(diffs_per_metric[mk])
        paired.append(row)

    return {"per_policy": per_policy, "paired": paired}


def render_markdown(tables: dict, *, title: str = "Ablation tables") -> str:
    """Render the table dict as a Markdown report."""
    lines = [f"# {title}", ""]

    # Per-policy
    lines.append("## Per-policy summary")
    if tables.get("per_policy"):
        cols = ["controller_label", "weather_mode"]
        cols += [
            f"{mk}_mean" for mk in (
                "n_faults", "restoration_rate", "voltage_violation_count",
                "energy_not_served_mwh",
            )
        ]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("|" + "|".join(["---"] * len(cols)) + "|")
        for row in tables["per_policy"]:
            cells = [str(row.get(c, "")) for c in cols]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    # Paired
    lines.append("## Paired comparison (anchor = rule_based)")
    if tables.get("paired"):
        cols = ["controller_label", "anchor_label", "n_pairs"]
        cols += [
            f"delta_{mk}_mean" for mk in (
                "restoration_rate", "voltage_violation_count",
                "energy_not_served_mwh",
            )
        ]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("|" + "|".join(["---"] * len(cols)) + "|")
        for row in tables["paired"]:
            cells = [str(row.get(c, "")) for c in cols]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    return "\n".join(lines)
