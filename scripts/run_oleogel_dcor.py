"""Run 007: model-free SAXS<->WAXS dependence beyond the clock (distance correlation).

Capacity-free test: separates "does cross-modal signal EXIST beyond the time-course" from
"can a tuned model exploit/transfer it" (Run 006). Per event, residualise each modality
against a leave-one-event-out time-prior, then measure distance correlation between the SAXS
and WAXS residuals with a permutation null. See docs/event-method/run_log.md (Run 007).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from materials_event_modeling.track_b.oleogel_ingest import (
    RUN_NAMES,
    load_event_field,
    parse_run_conditions,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "data/raw/oleogel_zenodo_15268752/SR-SAXS-WAXS.zip"


def area_normalize(s):
    tot = s.sum(1, keepdims=True)
    return (s * (np.median(tot) / np.clip(tot, 1e-6, None))).astype(np.float32)


def zscore_global(s):
    mu, sd = s.mean(0, keepdims=True), s.std(0, keepdims=True)
    sd = np.where(sd < 1e-6, 1.0, sd)
    return ((s - mu) / sd).astype(np.float32)


def interp_to(src_t, src_y, tgt_t):
    order = np.argsort(src_t)
    xs, ys = src_t[order], src_y[order]
    out = np.empty((len(tgt_t), ys.shape[1]), np.float32)
    for r, t in enumerate(tgt_t):
        jj = int(np.searchsorted(xs, t))
        if jj <= 0:
            out[r] = ys[0]
        elif jj >= len(xs):
            out[r] = ys[-1]
        else:
            w = (t - xs[jj - 1]) / (xs[jj] - xs[jj - 1])
            out[r] = (1 - w) * ys[jj - 1] + w * ys[jj]
    return out


def pdist_euclid(X):
    sq = (X * X).sum(1)
    return np.sqrt(np.clip(sq[:, None] + sq[None, :] - 2 * X @ X.T, 0, None))


def double_center(D):
    return D - D.mean(0, keepdims=True) - D.mean(1, keepdims=True) + D.mean()


def dcor_stats(X, Y, n_perm, rng):
    A, B = double_center(pdist_euclid(X)), double_center(pdist_euclid(Y))
    dcov2, dvarx, dvary = (A * B).mean(), (A * A).mean(), (B * B).mean()
    denom = np.sqrt(dvarx * dvary)
    dcor = float(np.sqrt(max(dcov2, 0) / denom)) if denom > 0 else 0.0
    n = X.shape[0]
    ge = sum((A * B[np.ix_(p := rng.permutation(n), p)]).mean() >= dcov2 for _ in range(n_perm))
    return dcor, (ge + 1) / (n_perm + 1)


def event_time_prior(M, times, ev, test_run):
    e_idx = np.where(ev == test_run)[0]
    others = [o for o in np.unique(ev) if o != test_run]
    acc = np.zeros((e_idx.size, M.shape[1]), np.float32)
    for o in others:
        o_idx = np.where(ev == o)[0]
        acc += interp_to(times[o_idx], M[o_idx], times[e_idx])
    return e_idx, acc / len(others)


def run(args):
    rng = np.random.default_rng(0)
    saxs = load_event_field(args.zip, RUN_NAMES, "SAXS")
    waxs = load_event_field(args.zip, RUN_NAMES, "WAXS")
    sx = zscore_global(area_normalize(saxs.spectra))
    wx = zscore_global(area_normalize(waxs.spectra))
    ev, times = waxs.event_ids, waxs.coords[:, 0]

    folds = []
    for run_name in RUN_NAMES:
        e_idx, sx_prior = event_time_prior(sx, times, ev, run_name)
        _, wx_prior = event_time_prior(wx, times, ev, run_name)
        dcor_raw, _ = dcor_stats(sx[e_idx], wx[e_idx], args.n_perm, rng)
        dcor_res, p = dcor_stats(sx[e_idx] - sx_prior, wx[e_idx] - wx_prior, args.n_perm, rng)
        folds.append({
            "run": run_name,
            "sample": parse_run_conditions(run_name)["sample"],
            "n": int(e_idx.size),
            "dcor_raw": round(dcor_raw, 3),
            "dcor_residual": round(dcor_res, 3),
            "p_value": round(p, 4),
            "significant": bool(p < 0.05),
        })

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "oleogel_dcor_modelfree",
        "n_perm": args.n_perm,
        "n_significant_residual": int(sum(f["significant"] for f in folds)),
        "folds": folds,
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    return result


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--n-perm", type=int, default=200)
    p.add_argument("--output", type=Path, default=Path("data/manifests/oleogel_dcor.json"))
    return p.parse_args()


def main():
    print(json.dumps(run(parse_args()), indent=2))


if __name__ == "__main__":
    main()
