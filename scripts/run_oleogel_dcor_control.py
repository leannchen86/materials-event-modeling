"""Run 008: smoothness-controlled SAXS<->WAXS dependence (fixes Run 007's null).

Two smoothness-preserving controls so any remaining dependence is genuine cross-modal
alignment, not shared temporal smoothness:
  - circular-shift null  (roll WAXS_resid in time; preserves its autocorrelation)
  - cross-event baseline (SAXS_resid[E] vs WAXS_resid[other event] -> same smoothness, no
    shared event)
See docs/event-method/run_log.md (Run 008).
"""

from __future__ import annotations

import argparse
import json
import statistics
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
    return ((s - mu) / np.where(sd < 1e-6, 1.0, sd)).astype(np.float32)


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


def centered_dist(X):
    sq = (X * X).sum(1)
    D = np.sqrt(np.clip(sq[:, None] + sq[None, :] - 2 * X @ X.T, 0, None))
    return D - D.mean(0, keepdims=True) - D.mean(1, keepdims=True) + D.mean()


def dcor_from_centered(A, B):
    dcov2, dvarx, dvary = (A * B).mean(), (A * A).mean(), (B * B).mean()
    den = np.sqrt(dvarx * dvary)
    return (float(np.sqrt(max(dcov2, 0) / den)) if den > 0 else 0.0), float(dcov2)


def residuals(M, times, ev):
    """Per-event residual against the leave-one-event-out time-prior."""
    out = {}
    for run_name in RUN_NAMES:
        e_idx = np.where(ev == run_name)[0]
        others = [o for o in RUN_NAMES if o != run_name]
        prior = np.zeros((e_idx.size, M.shape[1]), np.float32)
        for o in others:
            o_idx = np.where(ev == o)[0]
            prior += interp_to(times[o_idx], M[o_idx], times[e_idx])
        out[run_name] = (e_idx, times[e_idx], (M[e_idx] - prior / len(others)).astype(np.float32))
    return out


def run(args):
    rng = np.random.default_rng(0)
    saxs = load_event_field(args.zip, RUN_NAMES, "SAXS")
    waxs = load_event_field(args.zip, RUN_NAMES, "WAXS")
    sx = zscore_global(area_normalize(saxs.spectra))
    wx = zscore_global(area_normalize(waxs.spectra))
    ev, times = waxs.event_ids, waxs.coords[:, 0]
    sx_res = residuals(sx, times, ev)
    wx_res = residuals(wx, times, ev)

    folds = []
    for run_name in RUN_NAMES:
        _, e_times, sx_r = sx_res[run_name]
        _, _, wx_r = wx_res[run_name]
        n = sx_r.shape[0]
        A = centered_dist(sx_r)
        B = centered_dist(wx_r)
        obs_dcor, obs_dcov2 = dcor_from_centered(A, B)

        # circular-shift null (roll WAXS_resid in time => relabel both axes of B)
        min_s = max(5, n // 20)
        shifts = rng.integers(min_s, n - min_s, size=args.n_shift)
        ge = 0
        for s in shifts:
            idx = (np.arange(n) + int(s)) % n
            if (A * B[np.ix_(idx, idx)]).mean() >= obs_dcov2:
                ge += 1
        p_shift = (ge + 1) / (args.n_shift + 1)

        # cross-event baseline: other events' WAXS_resid interpolated onto this event's grid
        cross = []
        for o in RUN_NAMES:
            if o == run_name:
                continue
            _, o_times, wx_o = wx_res[o]
            B_o = centered_dist(interp_to(o_times, wx_o, e_times))
            cross.append(dcor_from_centered(A, B_o)[0])
        cross_med = float(statistics.median(cross))

        folds.append({
            "run": run_name,
            "sample": parse_run_conditions(run_name)["sample"],
            "observed_dcor": round(obs_dcor, 3),
            "p_circular_shift": round(p_shift, 4),
            "cross_event_dcor_median": round(cross_med, 3),
            "obs_minus_cross": round(obs_dcor - cross_med, 3),
            "real_signal": bool(p_shift < 0.05 and obs_dcor > cross_med + args.margin),
        })

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "oleogel_dcor_control",
        "n_shift": args.n_shift,
        "margin": args.margin,
        "n_real_signal": int(sum(f["real_signal"] for f in folds)),
        "folds": folds,
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    return result


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--n-shift", type=int, default=200)
    p.add_argument("--margin", type=float, default=0.05)
    p.add_argument("--output", type=Path, default=Path("data/manifests/oleogel_dcor_control.json"))
    return p.parse_args()


def main():
    print(json.dumps(run(parse_args()), indent=2))


if __name__ == "__main__":
    main()
