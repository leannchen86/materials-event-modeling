"""Run 006: ablation suite — is the Run 005 SAXS->WAXS win real cross-modal signal?

Cross-event leave-one-run-out (same data as Run 005). For each held-out event, predict WAXS
from several feature sets, each of which kills one alternative explanation:
  waxs_mean | time_only | time_sample | saxs_only | saxs_time | saxs_shuffled
SAXS counts as real cross-modal signal only if saxs_time<time_only, saxs_only<time_sample,
and saxs_only<saxs_shuffled. See docs/event-method/run_log.md (Run 006).
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

from materials_event_modeling.track_b.oleogel_ingest import (
    RUN_NAMES,
    load_event_field,
    parse_run_conditions,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "data/raw/oleogel_zenodo_15268752/SR-SAXS-WAXS.zip"
FEATURE_SETS = ["time_only", "time_sample", "saxs_only", "saxs_time", "saxs_shuffled"]


def area_normalize(spectra):
    tot = spectra.sum(1, keepdims=True)
    return (spectra * (np.median(tot) / np.clip(tot, 1e-6, None))).astype(np.float32)


def zscore(spectra, train_mask, clip=15.0):
    mu = spectra[train_mask].mean(0, keepdims=True)
    sd = spectra[train_mask].std(0, keepdims=True)
    sd = np.where(sd < 1e-6, 1.0, sd)
    return np.clip(((spectra - mu) / sd).astype(np.float32), -clip, clip)


def shuffle_within_events(arr, ev, rng):
    out = arr.copy()
    for run in np.unique(ev):
        idx = np.where(ev == run)[0]
        out[idx] = arr[idx][rng.permutation(idx.size)]
    return out


def features(name, *, saxs_x, saxs_x_shuf, t, samp_oh):
    if name == "time_only":
        return t
    if name == "time_sample":
        return np.hstack([t, samp_oh])
    if name == "saxs_only":
        return saxs_x
    if name == "saxs_time":
        return np.hstack([saxs_x, t])
    if name == "saxs_shuffled":
        return saxs_x_shuf
    raise ValueError(name)


def run(args):
    rng = np.random.default_rng(0)
    saxs = load_event_field(args.zip, RUN_NAMES, "SAXS")
    waxs = load_event_field(args.zip, RUN_NAMES, "WAXS")
    assert saxs.spectra.shape[0] == waxs.spectra.shape[0]
    assert (saxs.event_ids == waxs.event_ids).all()
    sx, wx = area_normalize(saxs.spectra), area_normalize(waxs.spectra)
    ev = waxs.event_ids
    times = waxs.coords[:, 0:1].astype(np.float32)
    samp = np.array([parse_run_conditions(e)["sample"] for e in ev])
    samp_oh = np.stack([(samp == "dmhr").astype(np.float32), (samp == "mopv").astype(np.float32)], 1)

    folds = []
    for test_run in RUN_NAMES:
        train_mask = ev != test_run
        test_mask = ev == test_run
        sx_z, wx_z = zscore(sx, train_mask), zscore(wx, train_mask)
        sx_z_shuf = shuffle_within_events(sx_z, ev, rng)
        saxs_pca = PCA(n_components=args.saxs_pca, random_state=0).fit(sx_z[train_mask])
        waxs_pca = PCA(n_components=args.waxs_pca, random_state=0).fit(wx_z[train_mask])
        saxs_x = saxs_pca.transform(sx_z)
        saxs_x_shuf = saxs_pca.transform(sx_z_shuf)
        y = waxs_pca.transform(wx_z)
        wx_te_true = wx_z[test_mask]

        def waxs_mse(pred_pca):
            return float(np.mean((wx_te_true - waxs_pca.inverse_transform(pred_pca)) ** 2))

        fold = {"test_run": test_run, "waxs_mean_mse": float(np.mean(wx_te_true ** 2))}
        for name in FEATURE_SETS:
            X = features(name, saxs_x=saxs_x, saxs_x_shuf=saxs_x_shuf, t=times, samp_oh=samp_oh)
            ridge = Ridge(alpha=1.0).fit(X[train_mask], y[train_mask])
            mlp = MLPRegressor(hidden_layer_sizes=(128,), max_iter=400, random_state=0).fit(
                X[train_mask], y[train_mask]
            )
            fold[f"{name}__ridge"] = waxs_mse(ridge.predict(X[test_mask]))
            fold[f"{name}__mlp"] = waxs_mse(mlp.predict(X[test_mask]))
        folds.append(fold)

    def med(key):
        return float(statistics.median(f[key] for f in folds))

    cols = ["waxs_mean_mse"] + [f"{n}__mlp" for n in FEATURE_SETS] + [f"{n}__ridge" for n in FEATURE_SETS]
    medians = {c: round(med(c), 3) for c in cols}
    # exclusion checks on the headline (mlp), counted across folds
    checks = {
        "saxs_time_beats_time_only": int(sum(f["saxs_time__mlp"] < f["time_only__mlp"] for f in folds)),
        "saxs_only_beats_time_sample": int(sum(f["saxs_only__mlp"] < f["time_sample__mlp"] for f in folds)),
        "saxs_only_beats_saxs_shuffled": int(sum(f["saxs_only__mlp"] < f["saxs_shuffled__mlp"] for f in folds)),
        "time_only_beats_mean": int(sum(f["time_only__mlp"] < f["waxs_mean_mse"] for f in folds)),
        "saxs_shuffled_approx_mean": int(sum(f["saxs_shuffled__mlp"] >= 0.9 * f["waxs_mean_mse"] for f in folds)),
        "n_folds": len(folds),
    }
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "oleogel_modality_ablation",
        "saxs_pca": args.saxs_pca,
        "waxs_pca": args.waxs_pca,
        "medians_over_folds": medians,
        "exclusion_checks_mlp": checks,
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
    p.add_argument("--output", type=Path, default=Path("data/manifests/oleogel_modality_ablation.json"))
    return p.parse_args()


def main():
    r = run(parse_args())
    print(json.dumps({"medians_over_folds": r["medians_over_folds"],
                      "exclusion_checks_mlp": r["exclusion_checks_mlp"]}, indent=2))


if __name__ == "__main__":
    main()
