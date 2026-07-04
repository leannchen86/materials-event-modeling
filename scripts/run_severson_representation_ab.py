"""Representation A/B on grammar-adapted Severson batch 1 (rung 3 of the validation ladder).

Compares a grammar-preserved representation (A: intent + per-cycle trajectory + censored
outcomes) against the paper-shaped projection of the same data (B: recipe + final number)
on three pre-registered tasks: cycle-life regression, within-policy replicate ranking,
and trajectory forecasting. Pre-registration (hypotheses H1-H5, baselines, splits):
docs/controlled-collection/severson_representation_ab.md — committed before this ran.

Input: data/interim/event_grammar_v1/severson_battery/events.json (regenerate with
scripts/adapters/adapt_severson_battery.py). Output: data/manifests/
severson_representation_ab.json with run identity.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from materials_event_modeling.eval.severson_ab import (
    load_cells,
    representation,
)
from materials_event_modeling.run_identity import run_identity

EVENTS_REL = Path("data/interim/event_grammar_v1/severson_battery/events.json")
K_CYCLES = (10, 50, 100)
FORECAST_FROM = 100
FORECAST_AT = (200, 300)
SEEDS = (0, 1, 2)
N_FOLDS = 5
BOOTSTRAP = 2000


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def make_model(name: str, seed: int):
    if name == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=1.0, random_state=seed))
    return RandomForestRegressor(n_estimators=300, min_samples_leaf=2, random_state=seed)


# --------------------------------------------------------------------------------------
# Task 1 — cycle-life regression
# --------------------------------------------------------------------------------------


def regression_task(cells: list[dict]) -> dict:
    eol = [c for c in cells if not c["censored"]]
    y = np.log10([c["cycle_life"] for c in eol])
    groups = np.array([c["policy"] for c in eol])
    batches = np.array([c["batch"] for c in eol])
    split_names = ["random_cell", "held_out_policy"]
    if len(set(batches)) >= 2:
        split_names.append("held_out_batch")
    results: dict = {}
    for k in K_CYCLES:
        for rep in ("B_policy", "A_trajectory", "A_full"):
            X = np.array([representation(c, rep, k) for c in eol])
            for model_name in ("ridge", "forest"):
                for split_name in split_names:
                    rmses, rhos, fold_rho_means = [], [], []
                    per_batch_rhos: dict[str, list[float]] = {}
                    for seed in SEEDS:
                        if split_name == "random_cell":
                            folds = list(
                                KFold(N_FOLDS, shuffle=True, random_state=seed).split(X)
                            )
                        elif split_name == "held_out_batch":
                            # One fold per collection batch (deterministic; seeds only
                            # affect model randomness).
                            folds = [
                                (np.where(batches != b)[0], np.where(batches == b)[0])
                                for b in sorted(set(batches))
                            ]
                        else:
                            # Assign whole policies to folds (seed-shuffled), so test
                            # cells never share a policy with training cells.
                            rng = np.random.default_rng(seed)
                            shuffled = rng.permutation(sorted(set(groups)))
                            fold_of = {g: i % N_FOLDS for i, g in enumerate(shuffled)}
                            fold_ids = np.array([fold_of[g] for g in groups])
                            folds = [
                                (np.where(fold_ids != f)[0], np.where(fold_ids == f)[0])
                                for f in range(N_FOLDS)
                            ]
                        pred = np.zeros_like(y)
                        fold_rhos = []
                        for fold_idx, (tr, te) in enumerate(folds):
                            model = make_model(model_name, seed)
                            model.fit(X[tr], y[tr])
                            pred[te] = model.predict(X[te])
                            # Per-fold rank correlation: the only valid Spearman when
                            # folds have heterogeneous target distributions (pooling
                            # across batch folds mixes between-batch shifts into the
                            # rank statistic — a Simpson-style artifact).
                            if len(te) >= 3 and len(set(y[te])) > 1:
                                fold_rho = float(spearmanr(pred[te], y[te]).statistic)
                                fold_rhos.append(fold_rho)
                                if split_name == "held_out_batch":
                                    batch_name = sorted(set(batches))[fold_idx]
                                    per_batch_rhos.setdefault(batch_name, []).append(fold_rho)
                        rmses.append(float(np.sqrt(np.mean((pred - y) ** 2))))
                        rhos.append(float(spearmanr(pred, y).statistic))
                        fold_rho_means.append(float(np.mean(fold_rhos)))
                    key = f"k{k}|{rep}|{model_name}|{split_name}"
                    results[key] = {
                        "rmse_log10": {"mean": float(np.mean(rmses)), "std": float(np.std(rmses))},
                        "spearman_pooled": {
                            "mean": float(np.mean(rhos)), "std": float(np.std(rhos)),
                            "note": "pooled out-of-fold; INVALID for held_out_batch "
                                    "(between-fold target shifts) — use per-fold",
                        },
                        "spearman": {
                            "mean": float(np.mean(fold_rho_means)),
                            "std": float(np.std(fold_rho_means)),
                            "note": "mean of per-fold Spearman (the quotable statistic)",
                        },
                    }
                    if per_batch_rhos:
                        results[key]["per_batch_spearman"] = {
                            b: {"mean": float(np.mean(v)), "std": float(np.std(v))}
                            for b, v in sorted(per_batch_rhos.items())
                        }
    # Train-mean baseline (split-independent for Spearman: undefined; report RMSE only).
    results["baseline_train_mean"] = {
        "rmse_log10": {"mean": float(np.std(y)), "std": 0.0},
        "note": "predicting the mean: RMSE = std of targets; Spearman undefined",
    }
    return {"n_eol_cells": len(eol), "results": results}


# --------------------------------------------------------------------------------------
# Task 2 — within-policy replicate ranking (leave-one-policy-out scores)
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


def pairwise_accuracy(pairs: list[tuple[str, str]], scores: dict[str, float]) -> float:
    total = 0.0
    for winner, loser in pairs:
        if scores[winner] > scores[loser]:
            total += 1.0
        elif scores[winner] == scores[loser]:
            total += 0.5
    return total / len(pairs) if pairs else float("nan")


def bootstrap_ci(values: np.ndarray, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    stats = [
        float(values[rng.integers(0, len(values), len(values))].mean())
        for _ in range(BOOTSTRAP)
    ]
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def cluster_bootstrap_ci(
    values: np.ndarray, clusters: list[str], seed: int = 0
) -> tuple[float, float]:
    """Bootstrap over CLUSTERS (policy groups), not pairs. Pairs within a replicate
    group share cells, so a pair-level bootstrap understates variance — most pairs come
    from a few large groups. This is the quotable CI."""
    rng = np.random.default_rng(seed)
    uniq = sorted(set(clusters))
    idx = {g: np.where(np.array(clusters) == g)[0] for g in uniq}
    stats = []
    for _ in range(BOOTSTRAP):
        sampled = rng.choice(uniq, size=len(uniq), replace=True)
        vals = np.concatenate([values[idx[g]] for g in sampled])
        stats.append(float(vals.mean()))
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def ranking_task(cells: list[dict]) -> dict:
    k = 100
    pairs_all, counts = ranking_pairs(cells)
    eol_ids = {c["event_id"] for c in cells if not c["censored"]}
    pairs_eol_only = [p for p in pairs_all if p[0] in eol_ids and p[1] in eol_ids]
    out: dict = {"pair_counts": counts,
                 "pairs_total": len(pairs_all), "pairs_eol_only": len(pairs_eol_only)}
    policy_of = {c["event_id"]: c["policy"] for c in cells}
    pair_clusters = [policy_of[w] for w, _ in pairs_all]
    for rep in ("B_policy", "A_trajectory", "A_full"):
        for model_name in ("ridge", "forest"):
            per_pair_accs = []
            for seed in SEEDS:
                scores = loo_policy_scores(cells, rep, k, model_name, seed)
                per_pair = np.array([
                    1.0 if scores[w] > scores[l] else (0.5 if scores[w] == scores[l] else 0.0)
                    for w, l in pairs_all
                ])
                per_pair_accs.append(per_pair)
            mean_per_pair = np.mean(per_pair_accs, axis=0)
            lo, hi = bootstrap_ci(mean_per_pair)
            clo, chi = cluster_bootstrap_ci(mean_per_pair, pair_clusters)
            out[f"{rep}|{model_name}"] = {
                "pairwise_accuracy": float(mean_per_pair.mean()),
                "per_seed_accuracy": [float(p.mean()) for p in per_pair_accs],
                "bootstrap_ci95_pairs": [lo, hi],
                "bootstrap_ci95_clusters": [clo, chi],
                "accuracy_eol_pairs_only": float(np.mean([
                    v for (w, l), v in zip(pairs_all, mean_per_pair)
                    if w in eol_ids and l in eol_ids
                ])) if pairs_eol_only else None,
            }
    return out


# --------------------------------------------------------------------------------------
# Task 3 — trajectory forecast (QDischarge at future cycles)
# --------------------------------------------------------------------------------------


def forecast_task(cells: list[dict]) -> dict:
    out: dict = {}
    for horizon in FORECAST_AT:
        usable = []
        for c in cells:
            at = np.where(c["cycles"] == horizon)[0]
            if at.size:
                usable.append((c, float(c["series"]["qdischarge_ah"][at[0]])))
        if len(usable) < 10:
            out[f"h{horizon}"] = {"note": f"only {len(usable)} cells reach cycle {horizon}"}
            continue
        y = np.array([t for _, t in usable])
        # Per-cell linear extrapolation from cycles 50..100 — the strongest cheap baseline.
        extrap = []
        for c, _ in usable:
            m = (c["cycles"] >= 50) & (c["cycles"] <= FORECAST_FROM)
            coeff = np.polyfit(c["cycles"][m], c["series"]["qdischarge_ah"][m], 1)
            extrap.append(float(np.polyval(coeff, horizon)))
        extrap = np.array(extrap)
        entry: dict = {
            "n_cells": len(usable),
            "baseline_train_mean_rmse": float(np.std(y)),
            "baseline_extrapolation_rmse": float(np.sqrt(np.mean((extrap - y) ** 2))),
        }
        for rep in ("B_policy", "A_full"):
            X = np.array([representation(c, rep, FORECAST_FROM) for c, _ in usable])
            for model_name in ("ridge", "forest"):
                rmses = []
                for seed in SEEDS:
                    pred = np.zeros_like(y)
                    for tr, te in KFold(N_FOLDS, shuffle=True, random_state=seed).split(X):
                        model = make_model(model_name, seed)
                        model.fit(X[tr], y[tr])
                        pred[te] = model.predict(X[te])
                    rmses.append(float(np.sqrt(np.mean((pred - y) ** 2))))
                entry[f"{rep}|{model_name}_rmse"] = {
                    "mean": float(np.mean(rmses)), "std": float(np.std(rmses)),
                }
        out[f"h{horizon}"] = entry
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, default=EVENTS_REL)
    parser.add_argument("--output", type=Path,
                        default=Path("data/manifests/severson_representation_ab.json"))
    args = parser.parse_args()
    root = project_root()

    cells = load_cells(root / args.events)
    censored = sum(c["censored"] for c in cells)
    print(f"loaded {len(cells)} cells ({censored} censored), "
          f"{len({c['policy'] for c in cells})} policies")

    report = {
        "task": "severson_representation_ab",
        "pre_registration": "docs/controlled-collection/severson_representation_ab.md",
        "n_cells": len(cells),
        "n_censored": censored,
        "seeds": list(SEEDS),
        "regression": regression_task(cells),
        "ranking": ranking_task(cells),
        "forecast": forecast_task(cells),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_identity": run_identity(),
    }

    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.output}")

    reg = report["regression"]["results"]
    splits = ["random_cell", "held_out_policy"]
    if any(key.endswith("held_out_batch") for key in reg):
        splits.append("held_out_batch")
    for split in splits:
        for rep in ("B_policy", "A_trajectory", "A_full"):
            r = reg[f"k100|{rep}|ridge|{split}"]
            print(f"  k100 {split:<16} {rep:<13} ridge  spearman "
                  f"{r['spearman']['mean']:.3f}±{r['spearman']['std']:.3f}  "
                  f"rmse {r['rmse_log10']['mean']:.3f}")
    for key, val in report["ranking"].items():
        if isinstance(val, dict) and "pairwise_accuracy" in val:
            clo, chi = val["bootstrap_ci95_clusters"]
            print(f"  ranking {key:<24} acc {val['pairwise_accuracy']:.3f} "
                  f"cluster-CI [{clo:.3f}, {chi:.3f}]")


if __name__ == "__main__":
    main()
