"""Shared masked-frame set model + memory-light example builders for oleogel runs.

Factored out of the Run 001 sanity so density-sweep / cross-event / JEPA runs reuse the
same model. Examples are stored as *indices* into the event's spectra (gathered per batch),
so memory stays small even for large anchor budgets.
"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn


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
        m = obs_mask.unsqueeze(-1).float()
        pooled = (tok * m).sum(1) / m.sum(1).clamp_min(1.0)
        return self.head(pooled + self.cand_enc(cand_time))


def evenly_spaced(idx: np.ndarray, k: int) -> np.ndarray:
    if k >= idx.size:
        return idx
    return idx[np.linspace(0, idx.size - 1, k).round().astype(int)]


def build_index_examples(pool_idx, *, max_obs, n_examples, rng, min_obs=4):
    obs_idx = np.zeros((n_examples, max_obs), np.int64)
    obs_mask = np.zeros((n_examples, max_obs), np.float32)
    cand_idx = np.zeros(n_examples, np.int64)
    for n in range(n_examples):
        cand = int(rng.choice(pool_idx))
        others = pool_idx[pool_idx != cand]
        k = int(rng.integers(min_obs, max_obs + 1))
        obs = rng.choice(others, size=min(k, others.size), replace=False)
        obs_idx[n, : obs.size] = obs
        obs_mask[n, : obs.size] = 1.0
        cand_idx[n] = cand
    return obs_idx, obs_mask, cand_idx


def train_set_model(
    spec_z, times, targets, pool_idx, *, max_obs=48, n_examples=6000, epochs=120,
    batch_size=256, lr=2e-4, seed=0, device="cpu",
):
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)
    obs_idx, obs_mask, cand_idx = build_index_examples(
        pool_idx, max_obs=max_obs, n_examples=n_examples, rng=rng
    )
    spec_t = torch.from_numpy(spec_z).to(device)
    time_t = torch.from_numpy(times.astype(np.float32)).to(device)
    targ_t = torch.from_numpy(targets).to(device)
    oi = torch.from_numpy(obs_idx)
    om = torch.from_numpy(obs_mask).to(device)
    ci = torch.from_numpy(cand_idx)
    model = TinySetModel(spec_z.shape[1], targets.shape[1]).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    loss_fn = nn.MSELoss()
    for _ in range(epochs):
        perm = torch.randperm(n_examples)
        model.train()
        for i in range(0, n_examples, batch_size):
            b = perm[i : i + batch_size]
            o = oi[b].to(device)
            obs_spec = spec_t[o]
            obs_time = time_t[o].unsqueeze(-1)
            cand_time = time_t[ci[b].to(device)].unsqueeze(-1)
            y = targ_t[ci[b].to(device)]
            opt.zero_grad(set_to_none=True)
            loss = loss_fn(model(obs_spec, obs_time, om[b], cand_time), y)
            loss.backward()
            opt.step()
    return model


def model_predict(model, spec_z, times, anchors, cand_times, pca, *, max_obs, device="cpu"):
    """Predict full z-spectra for candidates from a fixed anchor set."""
    model.eval()
    a = anchors[:max_obs]
    es = np.zeros((1, max_obs, spec_z.shape[1]), np.float32)
    et = np.zeros((1, max_obs, 1), np.float32)
    em = np.zeros((1, max_obs), np.float32)
    es[0, : a.size] = spec_z[a]
    et[0, : a.size, 0] = times[a]
    em[0, : a.size] = 1.0
    es_t = torch.from_numpy(es).to(device)
    et_t = torch.from_numpy(et).to(device)
    em_t = torch.from_numpy(em).to(device)
    preds = []
    with torch.no_grad():
        for t in cand_times:
            ct = torch.tensor([[t]], dtype=torch.float32, device=device)
            z = model(es_t, et_t, em_t, ct).cpu().numpy()
            preds.append(pca.inverse_transform(z)[0])
    return np.asarray(preds, np.float32)
