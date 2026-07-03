"""Run 002: density sweep + fair interpolation baseline on oleogel WAXS.

Tunes the interpolation baseline until it hurts: sweeps observed-anchor density and
compares the set-model vs linear-time interpolation (same anchors) vs the densest
possible interpolation (full pool, ~1-frame spacing). Also characterises the early-frame
intensity oscillation flagged in Run 001.

See docs/event-method/run_log.md (Run 002).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA

from materials_event_modeling.track_b.oleogel_ingest import load_run, parse_run_conditions
from materials_event_modeling.track_b.oleogel_masked import (
    evenly_spaced,
    model_predict,
    train_set_model,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "data/raw/oleogel_zenodo_15268752/SR-SAXS-WAXS.zip"


def interp_predict(spec_z, times, anchors, cand_times):
    """Piecewise-linear interpolation in time, vectorised across q bins."""
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


def oscillation_diag(spectra):
    tot = spectra.sum(1)
    detr = tot - np.convolve(tot, np.ones(7) / 7, mode="same")

    def autocorr(lag):
        return float(np.corrcoef(detr[lag:-lag], detr[2 * lag:][: detr.size - 2 * lag])[0, 1])

    cons = float(np.mean([np.corrcoef(spectra[i], spectra[i + 1])[0, 1] for i in range(len(spectra) - 1)]))
    # does per-frame area normalisation tame the oscillation? compare total-CV before/after.
    norm = spectra / tot[:, None]
    norm_total_cv = float(norm.sum(1).std() / norm.sum(1).mean())  # ~0 by construction (sanity)
    area_norm_consecutive_l2 = float(np.mean([np.linalg.norm(norm[i] - norm[i + 1]) for i in range(len(norm) - 1)]))
    return {
        "total_cv": float(tot.std() / tot.mean()),
        "consecutive_frame_shape_corr": cons,
        "detrended_autocorr_lag1": autocorr(1),
        "detrended_autocorr_lag2": autocorr(2),
        "detrended_autocorr_lag3": autocorr(3),
        "tot_first12": [round(float(x), 1) for x in tot[:12]],
        "area_norm_total_cv": norm_total_cv,
        "area_norm_consecutive_l2": area_norm_consecutive_l2,
    }


def run(args):
    field = load_run(args.zip, args.run, args.modality)
    spectra, times = field.spectra, field.coords[:, 0]
    n_frames, n_q = spectra.shape
    if args.normalize == "area":
        # remove the period-3 per-frame exposure/scale artifact (Run 002): rescale each
        # frame to the median total intensity. Shapes are identical (corr 0.9999), so this
        # is a pure scale correction, not a change of signal.
        tot = spectra.sum(1, keepdims=True)
        spectra = (spectra * (np.median(tot) / np.clip(tot, 1e-6, None))).astype(np.float32)
    mu = spectra.mean(0, keepdims=True)
    sd = spectra.std(0, keepdims=True) + 1e-6
    spec_z = ((spectra - mu) / sd).astype(np.float32)
    pca = PCA(n_components=args.pca, random_state=args.seed).fit(spec_z)
    targets = pca.transform(spec_z).astype(np.float32)

    all_idx = np.arange(n_frames)
    eval_idx = all_idx[:: args.eval_stride]
    pool_idx = np.setdiff1d(all_idx, eval_idx)
    cand_times = times[eval_idx]
    truth = spec_z[eval_idx]

    model = train_set_model(
        spec_z, times, targets, pool_idx, max_obs=args.max_obs,
        n_examples=args.n_examples, epochs=args.epochs, batch_size=args.batch_size,
        lr=args.lr, seed=args.seed,
    )

    def mse(pred):
        return float(np.mean((truth - pred) ** 2))

    sweep = []
    for k in args.k_list:
        anchors = evenly_spaced(pool_idx, k)
        m_pred = model_predict(model, spec_z, times, anchors, cand_times, pca, max_obs=args.max_obs)
        i_pred = interp_predict(spec_z, times, anchors, cand_times)
        sweep.append({
            "k": int(k),
            "anchor_spacing_frames": round(n_frames / k, 2),
            "model_mse": mse(m_pred),
            "interp_mse": mse(i_pred),
            "model_beats_interp": mse(m_pred) < mse(i_pred),
        })

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "oleogel_density_sweep",
        "run": args.run,
        "normalize": args.normalize,
        "conditions": parse_run_conditions(args.run),
        "n_frames": int(n_frames),
        "n_q": int(n_q),
        "pca_explained_var": float(pca.explained_variance_ratio_.sum()),
        "event_mean_mse": mse(np.zeros_like(truth)),
        "interp_dense_full_pool_mse": mse(interp_predict(spec_z, times, pool_idx, cand_times)),
        "sweep": sweep,
        "oscillation": oscillation_diag(spectra),
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    return result


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--run", default="s_mopv_1s_10Cmin_10c")
    p.add_argument("--modality", default="WAXS")
    p.add_argument("--normalize", choices=["none", "area"], default="area")
    p.add_argument("--pca", type=int, default=8)
    p.add_argument("--max-obs", type=int, default=48)
    p.add_argument("--k-list", type=int, nargs="+", default=[6, 12, 24, 48])
    p.add_argument("--n-examples", type=int, default=6000)
    p.add_argument("--eval-stride", type=int, default=5)
    p.add_argument("--epochs", type=int, default=120)
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--output", type=Path, default=Path("data/manifests/oleogel_density_sweep.json"))
    return p.parse_args()


def main():
    print(json.dumps(run(parse_args()), indent=2))


if __name__ == "__main__":
    main()
