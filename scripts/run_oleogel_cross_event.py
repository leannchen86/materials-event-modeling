"""Run 004: leave-one-run-out cross-event masked-frame test (oleogel WAXS).

The real HJ2 test. Train on 5 events; for the held-out 6th, predict its eval frames from a
few of its own observed anchors. The model cannot memorise the test event's trajectory, so
it must *use* the observed anchors. Compared against dense within-test-event interpolation
and the test-event mean. z-scoring and PCA are fit on train events only (no leakage).

See docs/event-method/run_log.md (Run 004).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA

from materials_event_modeling.track_b.oleogel_ingest import RUN_NAMES, load_event_field
from materials_event_modeling.track_b.oleogel_masked import (
    evenly_spaced,
    model_predict,
    train_set_model_multi,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "data/raw/oleogel_zenodo_15268752/SR-SAXS-WAXS.zip"


def interp_predict(spec_z, times, anchors, cand_times):
    a = anchors[np.argsort(times[anchors])]
    xa, ya = times[a], spec_z[a]
    out = np.empty((len(cand_times), spec_z.shape[1]), np.float32)
    for r, t in enumerate(cand_times):
        if t <= xa[0]:
            out[r] = ya[0]
        elif t >= xa[-1]:
            out[r] = ya[-1]
        else:
            j = int(np.searchsorted(xa, t) - 1)
            w = (t - xa[j]) / (xa[j + 1] - xa[j])
            out[r] = (1 - w) * ya[j] + w * ya[j + 1]
    return out


def run(args):
    field = load_event_field(args.zip, RUN_NAMES, args.modality)
    spectra = field.spectra.copy()
    if args.normalize == "area":
        tot = spectra.sum(1, keepdims=True)
        spectra = (spectra * (np.median(tot) / np.clip(tot, 1e-6, None))).astype(np.float32)
    times = field.coords[:, 0]
    ev = field.event_ids

    folds = []
    for test_run in RUN_NAMES:
        test_mask = ev == test_run
        train_mask = ~test_mask
        mu = spectra[train_mask].mean(0, keepdims=True)
        sd = spectra[train_mask].std(0, keepdims=True) + 1e-6
        spec_z = ((spectra - mu) / sd).astype(np.float32)
        pca = PCA(n_components=args.pca, random_state=args.seed).fit(spec_z[train_mask])
        targets = pca.transform(spec_z).astype(np.float32)

        train_events = [np.where(ev == r)[0] for r in RUN_NAMES if r != test_run]
        model = train_set_model_multi(
            spec_z, times, targets, train_events, max_obs=args.max_obs,
            n_examples=args.n_examples, epochs=args.epochs, batch_size=args.batch_size,
            lr=args.lr, seed=args.seed,
        )

        test_idx = np.where(test_mask)[0]
        eval_idx = test_idx[np.arange(0, test_idx.size, args.eval_stride)]
        pool_idx = np.setdiff1d(test_idx, eval_idx)
        cand_times = times[eval_idx]
        truth = spec_z[eval_idx]

        def mse(p):
            return float(np.mean((truth - p) ** 2))

        model_mse = {}
        for k in args.k_list:
            anchors = evenly_spaced(pool_idx, k)
            model_mse[k] = mse(
                model_predict(model, spec_z, times, anchors, cand_times, pca, max_obs=args.max_obs)
            )
        interp_dense = mse(interp_predict(spec_z, times, pool_idx, cand_times))
        event_mean = mse(np.tile(spec_z[pool_idx].mean(0), (truth.shape[0], 1)))
        kmax = max(args.k_list)
        folds.append({
            "test_run": test_run,
            "n_test_frames": int(test_idx.size),
            "model_mse_by_k": {str(k): model_mse[k] for k in args.k_list},
            "model_mse_kmax": model_mse[kmax],
            "interp_dense_mse": interp_dense,
            "event_mean_mse": event_mean,
            "model_beats_interp": model_mse[kmax] < interp_dense,
        })

    kmax = max(args.k_list)
    agg = {
        "mean_model_kmax": float(np.mean([f["model_mse_kmax"] for f in folds])),
        "mean_interp_dense": float(np.mean([f["interp_dense_mse"] for f in folds])),
        "mean_event_mean": float(np.mean([f["event_mean_mse"] for f in folds])),
        "folds_model_beats_interp": int(sum(f["model_beats_interp"] for f in folds)),
        "n_folds": len(folds),
        "mean_model_by_k": {
            str(k): float(np.mean([f["model_mse_by_k"][str(k)] for f in folds])) for k in args.k_list
        },
    }
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "oleogel_cross_event_loro",
        "normalize": args.normalize,
        "modality": args.modality,
        "pca": args.pca,
        "max_obs": args.max_obs,
        "k_list": args.k_list,
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
    p.add_argument("--modality", default="WAXS")
    p.add_argument("--normalize", choices=["none", "area"], default="area")
    p.add_argument("--pca", type=int, default=8)
    p.add_argument("--max-obs", type=int, default=48)
    p.add_argument("--k-list", type=int, nargs="+", default=[6, 12, 24, 48])
    p.add_argument("--n-examples", type=int, default=8000)
    p.add_argument("--eval-stride", type=int, default=5)
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--output", type=Path, default=Path("data/manifests/oleogel_cross_event.json"))
    return p.parse_args()


def main():
    print(json.dumps(run(parse_args())["aggregate"], indent=2))


if __name__ == "__main__":
    main()
