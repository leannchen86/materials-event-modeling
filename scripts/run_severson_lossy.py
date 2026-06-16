"""Run 015: is the battery cycle_life label a lossy summary of the degradation trajectory?

A (natural coordinate / sanity): does the early-cycle trajectory predict cycle_life?
B (lossy): do cells close in cycle_life have similar aging *shape* (capacity vs fraction-of-life)?
If not, the single lifetime number discards the degradation-mode coordinate -> lossy.
See docs/event-method/run_log.md (Run 015).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.neighbors import KNeighborsRegressor

from materials_event_modeling.data.severson import early_features, life_shape, load_cells

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAT = ROOT / "data/raw/severson/batch1.mat"


def zscore(X):
    mu, sd = X.mean(0, keepdims=True), X.std(0, keepdims=True)
    return (X - mu) / np.where(sd < 1e-9, 1.0, sd)


def loo_spearman(X, y, k=3):
    preds = np.zeros_like(y, dtype=float)
    for i in range(len(y)):
        tr = np.arange(len(y)) != i
        preds[i] = KNeighborsRegressor(n_neighbors=k).fit(X[tr], y[tr]).predict(X[i : i + 1])[0]
    return float(spearmanr(preds, y).statistic)


def run(args):
    rng = np.random.default_rng(0)
    cells = load_cells(args.mat)
    cl = np.array([c["cycle_life"] for c in cells], dtype=float)
    Xe = zscore(np.stack([early_features(c) for c in cells]))
    Xs = zscore(np.stack([life_shape(c) for c in cells]))
    n = len(cells)

    # A: natural-coordinate sanity
    a_obs = loo_spearman(Xe, cl)
    a_shuf = float(np.mean([loo_spearman(Xe, rng.permutation(cl)) for _ in range(5)]))

    # B: lossy — pairwise relationship of |Δcycle_life| to shape vs early distance
    iu = np.triu_indices(n, 1)
    dcl = np.abs(cl[:, None] - cl[None, :])[iu]
    dshape = np.linalg.norm(Xs[:, None, :] - Xs[None, :, :], axis=2)[iu]
    dearly = np.linalg.norm(Xe[:, None, :] - Xe[None, :, :], axis=2)[iu]
    sp_shape = float(spearmanr(dcl, dshape).statistic)
    sp_early = float(spearmanr(dcl, dearly).statistic)

    # nearest-in-lifetime shape ratio
    dcl_full = np.abs(cl[:, None] - cl[None, :])
    np.fill_diagonal(dcl_full, np.inf)
    dshape_full = np.linalg.norm(Xs[:, None, :] - Xs[None, :, :], axis=2)
    nn = np.argmin(dcl_full, axis=1)
    nn_shape = float(np.mean([dshape_full[i, nn[i]] for i in range(n)]))
    ratio = round(nn_shape / float(dshape[dshape > 0].mean()), 3)

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "severson_battery_lossy",
        "n_cells": n,
        "cycle_life_range": [round(float(cl.min())), round(float(cl.max()))],
        "n_policies": len({c["policy"] for c in cells}),
        "A_natural_coordinate": {
            "loo_spearman_early_to_cyclelife": round(a_obs, 3),
            "shuffled_control": round(a_shuf, 3),
        },
        "B_lossy": {
            "spearman_dcl_vs_shape_dist": round(sp_shape, 3),
            "spearman_dcl_vs_early_dist": round(sp_early, 3),
            "nearest_in_life_shape_ratio_vs_allpairs": ratio,
        },
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    return result


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mat", type=Path, default=DEFAULT_MAT)
    p.add_argument("--output", type=Path, default=Path("data/manifests/severson_lossy.json"))
    return p.parse_args()


def main():
    print(json.dumps(run(parse_args()), indent=2))


if __name__ == "__main__":
    main()
