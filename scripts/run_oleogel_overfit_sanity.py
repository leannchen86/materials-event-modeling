"""Overfit-one-event sanity for the oleogel WAXS masked-frame task (refined-a).

Karpathy step: shake out parsing bugs and confirm the masked-frame signal is learnable
on a SINGLE event before any scale-up. A tiny mean-pool set model is compared against the
event_mean and linear-time-interpolation baselines on a within-event held-out frame grid.

See docs/event-method/run_log.md (Run 001) for hypothesis / expectation.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from sklearn.decomposition import PCA
from torch import nn

from materials_event_modeling.track_b.oleogel_ingest import load_run, parse_run_conditions

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "data/raw/oleogel_zenodo_15268752/SR-SAXS-WAXS.zip"


class TinySetModel(nn.Module):
    """Mean-pool set encoder: observed (spectrum, time) tokens + candidate time -> target PCA."""

    def __init__(self, n_q: int, target_dim: int, d: int = 64) -> None:
        super().__init__()
        self.spec_enc = nn.Sequential(nn.Linear(n_q, 128), nn.GELU(), nn.Linear(128, d))
        self.time_enc = nn.Sequential(nn.Linear(1, 32), nn.GELU(), nn.Linear(32, d))
        self.cand_enc = nn.Sequential(nn.Linear(1, 32), nn.GELU(), nn.Linear(32, d))
        self.head = nn.Sequential(
            nn.LayerNorm(d), nn.Linear(d, d), nn.GELU(), nn.Linear(d, target_dim)
        )

    def forward(self, obs_spec, obs_time, obs_mask, cand_time):
        tok = self.spec_enc(obs_spec) + self.time_enc(obs_time)
        mask = obs_mask.unsqueeze(-1).float()
        pooled = (tok * mask).sum(1) / mask.sum(1).clamp_min(1.0)
        return self.head(pooled + self.cand_enc(cand_time))


def build_examples(spec_z, times, targets, pool_idx, *, max_obs, n_examples, rng):
    n_q = spec_z.shape[1]
    obs_spec = np.zeros((n_examples, max_obs, n_q), np.float32)
    obs_time = np.zeros((n_examples, max_obs, 1), np.float32)
    obs_mask = np.zeros((n_examples, max_obs), np.float32)
    cand_time = np.zeros((n_examples, 1), np.float32)
    y = np.zeros((n_examples, targets.shape[1]), np.float32)
    for n in range(n_examples):
        cand = int(rng.choice(pool_idx))
        others = pool_idx[pool_idx != cand]
        k = int(rng.integers(4, max_obs + 1))
        obs = rng.choice(others, size=min(k, others.size), replace=False)
        obs_spec[n, : obs.size] = spec_z[obs]
        obs_time[n, : obs.size, 0] = times[obs]
        obs_mask[n, : obs.size] = 1.0
        cand_time[n, 0] = times[cand]
        y[n] = targets[cand]
    return (
        torch.from_numpy(obs_spec),
        torch.from_numpy(obs_time),
        torch.from_numpy(obs_mask),
        torch.from_numpy(cand_time),
        torch.from_numpy(y),
    )


def evenly_spaced(pool_idx, k):
    return pool_idx[np.linspace(0, pool_idx.size - 1, k).round().astype(int)]


def run(args: argparse.Namespace) -> dict:
    rng = np.random.default_rng(args.seed)
    torch.manual_seed(args.seed)
    field = load_run(args.zip, args.run, modality=args.modality)
    spectra, times = field.spectra, field.coords[:, 0]
    n_frames, n_q = spectra.shape

    # z-score per q bin so MSE is comparable across bins; event_mean becomes the zero vector.
    mu = spectra.mean(0, keepdims=True)
    sd = spectra.std(0, keepdims=True) + 1e-6
    spec_z = ((spectra - mu) / sd).astype(np.float32)

    pca = PCA(n_components=args.pca, random_state=args.seed).fit(spec_z)
    targets = pca.transform(spec_z).astype(np.float32)

    all_idx = np.arange(n_frames)
    eval_idx = all_idx[:: args.eval_stride]
    pool_idx = np.setdiff1d(all_idx, eval_idx)

    # ---- train ----
    tr = build_examples(spec_z, times, targets, pool_idx, max_obs=args.max_obs,
                        n_examples=args.n_examples, rng=rng)
    model = TinySetModel(n_q=n_q, target_dim=args.pca)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    loss_fn = nn.MSELoss()
    obs_spec, obs_time, obs_mask, cand_time, y = tr
    bs = args.batch_size
    train_mse = float("nan")
    for epoch in range(args.epochs):
        perm = torch.randperm(obs_spec.shape[0])
        model.train()
        for i in range(0, perm.numel(), bs):
            b = perm[i : i + bs]
            opt.zero_grad(set_to_none=True)
            pred = model(obs_spec[b], obs_time[b], obs_mask[b], cand_time[b])
            loss = loss_fn(pred, y[b])
            loss.backward()
            opt.step()
        if epoch == args.epochs - 1:
            model.eval()
            with torch.no_grad():
                train_mse = float(loss_fn(model(obs_spec, obs_time, obs_mask, cand_time), y))

    # ---- eval on held-out frames: observe a fixed even subset of the pool ----
    obs = evenly_spaced(pool_idx, args.max_obs)
    es = np.zeros((1, args.max_obs, n_q), np.float32)
    et = np.zeros((1, args.max_obs, 1), np.float32)
    em = np.zeros((1, args.max_obs), np.float32)
    es[0, : obs.size] = spec_z[obs]
    et[0, : obs.size, 0] = times[obs]
    em[0, : obs.size] = 1.0
    obs_sorted = obs[np.argsort(times[obs])]

    def model_pred(t):
        ct = np.array([[t]], np.float32)
        with torch.no_grad():
            z = model(torch.from_numpy(es), torch.from_numpy(et), torch.from_numpy(em),
                      torch.from_numpy(ct)).numpy()
        return pca.inverse_transform(z)[0]

    def interp_pred(t):
        return np.array([np.interp(t, times[obs_sorted], spec_z[obs_sorted][:, j]) for j in range(n_q)],
                        np.float32)

    mse = {"model": [], "linear_time_interp": [], "event_mean": []}
    for c in eval_idx:
        truth = spec_z[c]
        mse["model"].append(float(np.mean((truth - model_pred(times[c])) ** 2)))
        mse["linear_time_interp"].append(float(np.mean((truth - interp_pred(times[c])) ** 2)))
        mse["event_mean"].append(float(np.mean(truth ** 2)))  # z-space mean is 0
    mse = {k: float(np.mean(v)) for k, v in mse.items()}

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "oleogel_overfit_sanity",
        "run": args.run,
        "conditions": parse_run_conditions(args.run),
        "modality": args.modality,
        "n_frames": int(n_frames),
        "n_q": int(n_q),
        "q_range": [float(field.q.min()), float(field.q.max())],
        "spectra_finite": bool(np.isfinite(spectra).all()),
        "zero_frames": int((np.abs(spectra).sum(1) == 0).sum()),
        "eval_candidates": int(eval_idx.size),
        "pca_explained_var": float(pca.explained_variance_ratio_.sum()),
        "train_mse_final": train_mse,
        "eval_mse_zspace": mse,
        "model_beats_event_mean": mse["model"] < mse["event_mean"],
        "model_beats_interp": mse["model"] < mse["linear_time_interp"],
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--run", default="s_mopv_1s_10Cmin_10c")
    p.add_argument("--modality", default="WAXS")
    p.add_argument("--pca", type=int, default=8)
    p.add_argument("--max-obs", type=int, default=12)
    p.add_argument("--n-examples", type=int, default=4000)
    p.add_argument("--eval-stride", type=int, default=5)
    p.add_argument("--epochs", type=int, default=120)
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--output", type=Path, default=Path("data/manifests/oleogel_overfit_sanity.json"))
    return p.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2))


if __name__ == "__main__":
    main()
