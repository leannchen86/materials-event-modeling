"""Shared feature builders for the Severson representation A/B (rung 3).

Moved verbatim from scripts/run_severson_representation_ab.py so the provenance-leakage
audit can run on EXACTLY the feature matrices the A/B used (the batch-fingerprint probe
must not re-implement them). Any change here changes both the A/B and the audit —
that coupling is the point.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

POLICY_KEYS = ("cell.charge_c_rate_1", "cell.soc_switch_percent", "cell.charge_c_rate_2")


def load_cells(path: Path) -> list[dict]:
    events = json.loads(path.read_text())
    cells = []
    for event in events:
        # Respect adapter quality flags: artifact-flagged observations never enter features.
        obs = sorted(
            (o for o in event["observations"] if o.get("include_in_raw_objective") is not False),
            key=lambda o: o["cycle_index"],
        )
        series = {
            key: np.array([o["payload"]["cycling"][key] for o in obs], dtype=float)
            for key in ("qdischarge_ah", "qcharge_ah", "ir_ohm", "tavg_c", "tmax_c",
                        "tmin_c", "chargetime_min")
        }
        cycles = np.array([o["cycle_index"] for o in obs], dtype=float)
        outcome = event["outcome"]
        censored = outcome["status"] == "ambiguous"
        cells.append({
            "event_id": event["event_id"],
            "policy": event["intent"]["event_group_id"],
            "batch": event["provenance"]["batch_id"],
            "policy_features": [event["intent"]["planned"][k] for k in POLICY_KEYS],
            "series": series,
            "cycles": cycles,
            "censored": censored,
            # For EOL cells cycle_life is the final answer; for censored cells the record
            # length is a LOWER BOUND on life (the run was truncated above the criterion).
            "cycle_life": None if censored else float(
                outcome["summary"]["cell.cycle_life_cycles"]
            ),
            "life_lower_bound": float(cycles.max()) + 1.0,
        })
    return cells


def _slope(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2:
        return 0.0
    return float(np.polyfit(x, y, 1)[0])


def trajectory_features(cell: dict, k: int) -> list[float]:
    """Early-trajectory summary features from cycles 2..k (cycle 1 is anomalous)."""
    mask = (cell["cycles"] >= 2) & (cell["cycles"] <= k)
    c = cell["cycles"][mask]
    feats: list[float] = []
    for key in ("qdischarge_ah", "ir_ohm", "tavg_c", "chargetime_min"):
        y = cell["series"][key][mask]
        feats += [float(y.mean()), float(y[-1]), _slope(c, y)]
    qd = cell["series"]["qdischarge_ah"][mask]
    half = len(qd) // 2
    feats += [
        float(qd.max() - qd[-1]),                       # fade from peak
        float(qd[-1] - qd[0]),                          # net change
        _slope(c[half:], qd[half:]),                    # late-window fade slope
        float(np.log10(np.var(np.diff(qd)) + 1e-12)),   # fade roughness
        float(cell["series"]["tmax_c"][mask].max()),
    ]
    return feats


def representation(cell: dict, rep: str, k: int) -> list[float]:
    if rep == "B_policy":
        return list(cell["policy_features"])
    if rep == "A_trajectory":
        return trajectory_features(cell, k)
    if rep == "A_full":
        return list(cell["policy_features"]) + trajectory_features(cell, k)
    raise ValueError(rep)
