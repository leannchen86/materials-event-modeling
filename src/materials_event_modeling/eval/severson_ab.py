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
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

POLICY_KEYS = ("cell.charge_c_rate_1", "cell.soc_switch_percent", "cell.charge_c_rate_2")

BOOTSTRAP = 2000


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
        summary = outcome.get("summary") or {}
        censored = summary.get("cell.record_truncated") is True
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
                summary["cell.cycle_life_cycles"]
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


def make_model(name: str, seed: int):
    """Regressor by name. ridge/forest are the A/B's originals (unchanged, so the A/B
    reproduces bit-identically); the rest are diverse families for the ranking-robustness
    follow-on — a linear model, a kernel model, boosted and bagged trees, and an
    instance-based model, so 'is the ranking signal model-general or forest-fragile?'
    can be answered across genuinely different inductive biases."""
    if name == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=1.0, random_state=seed))
    if name == "forest":
        return RandomForestRegressor(n_estimators=300, min_samples_leaf=2, random_state=seed)
    if name == "gradient_boosting":
        return GradientBoostingRegressor(n_estimators=200, max_depth=2,
                                         learning_rate=0.05, random_state=seed)
    if name == "svr_rbf":
        return make_pipeline(StandardScaler(), SVR(kernel="rbf", C=10.0, gamma="scale"))
    if name == "knn":
        return make_pipeline(StandardScaler(), KNeighborsRegressor(n_neighbors=5))
    raise ValueError(name)


# --------------------------------------------------------------------------------------
# Within-policy replicate ranking (shared by the A/B and the robustness follow-on)
# --------------------------------------------------------------------------------------


def loo_policy_scores(cells: list[dict], rep: str, k: int, model_name: str, seed: int) -> dict:
    """Score every cell with a model trained on OTHER policies' EOL cells."""
    eol = [c for c in cells if not c["censored"]]
    scores: dict[str, float] = {}
    for policy in sorted({c["policy"] for c in cells}):
        train = [c for c in eol if c["policy"] != policy]
        X = np.array([representation(c, rep, k) for c in train])
        y = np.log10([c["cycle_life"] for c in train])
        model = make_model(model_name, seed)
        model.fit(X, y)
        held = [c for c in cells if c["policy"] == policy]
        for c in held:
            scores[c["event_id"]] = float(
                model.predict(np.array([representation(c, rep, k)]))[0]
            )
    return scores


def ranking_pairs(cells: list[dict]) -> tuple[list[tuple[str, str]], dict]:
    """Within-policy pairs with a resolvable longer-lived member (first id = winner)."""
    by_policy: dict[str, list[dict]] = {}
    for c in cells:
        by_policy.setdefault(c["policy"], []).append(c)
    pairs, counts = [], {"eol_eol": 0, "censored_resolved": 0, "unresolvable": 0}
    for members in by_policy.values():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                if not a["censored"] and not b["censored"]:
                    if a["cycle_life"] == b["cycle_life"]:
                        counts["unresolvable"] += 1
                        continue
                    winner, loser = (a, b) if a["cycle_life"] > b["cycle_life"] else (b, a)
                    counts["eol_eol"] += 1
                elif a["censored"] != b["censored"]:
                    cens, eolc = (a, b) if a["censored"] else (b, a)
                    if cens["life_lower_bound"] > eolc["cycle_life"]:
                        winner, loser = cens, eolc
                        counts["censored_resolved"] += 1
                    else:
                        counts["unresolvable"] += 1
                        continue
                else:
                    counts["unresolvable"] += 1
                    continue
                pairs.append((winner["event_id"], loser["event_id"]))
    return pairs, counts


def per_pair_correct(pairs: list[tuple[str, str]], scores: dict[str, float]) -> np.ndarray:
    """1.0 if the model ranks the longer-lived cell above its sibling, 0.5 on a tie."""
    return np.array([
        1.0 if scores[w] > scores[l] else (0.5 if scores[w] == scores[l] else 0.0)
        for w, l in pairs
    ])


def bootstrap_ci(values: np.ndarray, seed: int = 0, n_boot: int = BOOTSTRAP) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    stats = [
        float(values[rng.integers(0, len(values), len(values))].mean())
        for _ in range(n_boot)
    ]
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def cluster_bootstrap_ci(
    values: np.ndarray, clusters: list[str], seed: int = 0, n_boot: int = BOOTSTRAP
) -> tuple[float, float]:
    """Bootstrap over CLUSTERS (policy groups), not pairs. Pairs within a replicate
    group share cells, so a pair-level bootstrap understates variance — most pairs come
    from a few large groups. This is the quotable CI."""
    rng = np.random.default_rng(seed)
    uniq = sorted(set(clusters))
    idx = {g: np.where(np.array(clusters) == g)[0] for g in uniq}
    stats = []
    for _ in range(n_boot):
        sampled = rng.choice(uniq, size=len(uniq), replace=True)
        vals = np.concatenate([values[idx[g]] for g in sampled])
        stats.append(float(vals.mean()))
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))
