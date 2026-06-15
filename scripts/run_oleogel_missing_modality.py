"""Run 005: cross-event missing-modality test (predict WAXS from SAXS), oleogel.

A task time-interpolation cannot do: predict the WAXS (crystal-structure) frame from the
SAXS (nanostructure) frame at the SAME timepoint. Leave-one-run-out across the 6 events;
only a learned cross-modal mapping can beat predicting the mean. See run_log.md (Run 005).
"""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor

from materials_event_modeling.track_b.oleogel_ingest import RUN_NAMES, load_event_field

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "data/raw/oleogel_zenodo_15268752/SR-SAXS-WAXS.zip"


def area_normalize(spectra):
    tot = spectra.sum(1, keepdims=True)
    return (spectra * (np.median(tot) / np.clip(tot, 1e-6, None))).astype(np.float32)


def zscore(spectra, train_mask, clip=15.0):
    mu = spectra[train_mask].mean(0, keepdims=True)
    sd = spectra[train_mask].std(0, keepdims=True)
    sd = np.where(sd < 1e-6, 1.0, sd)  # guard near-constant bins (Run 004 blow-up fix)
    return np.clip(((spectra - mu) / sd).astype(np.float32), -clip, clip)


def run(args):
    saxs = load_event_field(args.zip, RUN_NAMES, "SAXS")
    waxs = load_event_field(args.zip, RUN_NAMES, "WAXS")
    assert saxs.spectra.shape[0] == waxs.spectra.shape[0], "SAXS/WAXS frame counts differ"
    assert (saxs.event_ids == waxs.event_ids).all(), "SAXS/WAXS event ordering differs"
    sx, wx = area_normalize(saxs.spectra), area_normalize(waxs.spectra)
    ev = waxs.event_ids

    folds = []
    for test_run in RUN_NAMES:
        train_mask = ev != test_run
        test_mask = ev == test_run
        sx_z, wx_z = zscore(sx, train_mask), zscore(wx, train_mask)
        saxs_pca = PCA(n_components=args.saxs_pca, random_state=0).fit(sx_z[train_mask])
        waxs_pca = PCA(n_components=args.waxs_pca, random_state=0).fit(wx_z[train_mask])
        x_tr, y_tr = saxs_pca.transform(sx_z[train_mask]), waxs_pca.transform(wx_z[train_mask])
        x_te = saxs_pca.transform(sx_z[test_mask])
        wx_te_true = wx_z[test_mask]

        def waxs_mse(pred_pca):
            return float(np.mean((wx_te_true - waxs_pca.inverse_transform(pred_pca)) ** 2))

        ridge = Ridge(alpha=1.0).fit(x_tr, y_tr)
        mlp = MLPRegressor(hidden_layer_sizes=(128,), max_iter=400, random_state=0).fit(x_tr, y_tr)
        folds.append({
            "test_run": test_run,
            "n_test_frames": int(test_mask.sum()),
            "waxs_mean_mse": float(np.mean(wx_te_true ** 2)),  # predict train mean (=0 in z)
            "ridge_mse": waxs_mse(ridge.predict(x_te)),
            "mlp_mse": waxs_mse(mlp.predict(x_te)),
        })

    keys = ["waxs_mean_mse", "ridge_mse", "mlp_mse"]
    agg = {k: {"mean": float(np.mean([f[k] for f in folds])),
               "median": float(statistics.median(f[k] for f in folds))} for k in keys}
    agg["ridge_beats_mean_folds"] = int(sum(f["ridge_mse"] < f["waxs_mean_mse"] for f in folds))
    agg["mlp_beats_mean_folds"] = int(sum(f["mlp_mse"] < f["waxs_mean_mse"] for f in folds))
    agg["mlp_beats_ridge_folds"] = int(sum(f["mlp_mse"] < f["ridge_mse"] for f in folds))
    agg["n_folds"] = len(folds)

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "oleogel_missing_modality_saxs_to_waxs",
        "saxs_pca": args.saxs_pca,
        "waxs_pca": args.waxs_pca,
        "aggregate": agg,
        "folds": folds,
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    return result


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--saxs-pca", type=int, default=30)
    p.add_argument("--waxs-pca", type=int, default=8)
    p.add_argument("--output", type=Path, default=Path("data/manifests/oleogel_missing_modality.json"))
    return p.parse_args()


def main():
    print(json.dumps(run(parse_args())["aggregate"], indent=2))


if __name__ == "__main__":
    main()
