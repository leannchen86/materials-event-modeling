"""Run a small masked autoencoder baseline for NIST XRD reconstruction."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from materials_event_modeling.data.nist import DATASET_ID
from materials_event_modeling.eval.masked_reconstruction import (
    EvaluationAccumulator,
    MissingPCA,
    interpolate_masked_region,
    load_processed,
    mask_starts,
    split_iterators,
)


class MaskedMLPAutoencoder(nn.Module):
    """A small global masked-reconstruction model for 1D XRD spectra."""

    def __init__(self, n_features: int, hidden_dim: int, latent_dim: int, dropout: float) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features * 2, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, latent_dim),
            nn.GELU(),
            nn.Linear(latent_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, n_features),
        )

    def forward(self, spectrum_and_mask: torch.Tensor) -> torch.Tensor:
        return self.net(spectrum_and_mask)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def choose_device(device_name: str) -> torch.device:
    if device_name != "auto":
        return torch.device(device_name)
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def standardize_train_test(
    x_train: np.ndarray,
    x_all: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x_train.mean(axis=0, keepdims=True)
    std = x_train.std(axis=0, keepdims=True)
    std = np.maximum(std, 1e-6)
    return ((x_train - mean) / std).astype(np.float32), mean.astype(np.float32), std.astype(np.float32)


def make_masked_batch(
    batch: torch.Tensor,
    mask_width: int,
    rng: np.random.Generator,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    batch_np = batch.cpu().numpy()
    observed = np.ones_like(batch_np, dtype=np.float32)
    max_start = batch_np.shape[1] - mask_width + 1
    starts = rng.integers(0, max_start, size=batch_np.shape[0])
    for row_idx, start in enumerate(starts):
        observed[row_idx, start : start + mask_width] = 0.0
    masked = batch_np * observed
    model_input = np.concatenate([masked, observed], axis=1)
    missing = 1.0 - observed
    return (
        torch.as_tensor(model_input, dtype=torch.float32, device=device),
        batch.to(device),
        torch.as_tensor(missing, dtype=torch.float32, device=device),
    )


def masked_loss(
    prediction: torch.Tensor,
    target: torch.Tensor,
    missing: torch.Tensor,
    observed_loss_weight: float,
) -> torch.Tensor:
    masked = ((prediction - target) ** 2 * missing).sum() / missing.sum().clamp_min(1.0)
    if observed_loss_weight <= 0:
        return masked
    observed = 1.0 - missing
    observed_loss = ((prediction - target) ** 2 * observed).sum() / observed.sum().clamp_min(1.0)
    return masked + observed_loss_weight * observed_loss


def train_autoencoder(
    x_train_z: np.ndarray,
    mask_width: int,
    hidden_dim: int,
    latent_dim: int,
    dropout: float,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    weight_decay: float,
    observed_loss_weight: float,
    seed: int,
    device: torch.device,
) -> MaskedMLPAutoencoder:
    torch.manual_seed(seed)
    model = MaskedMLPAutoencoder(
        n_features=x_train_z.shape[1],
        hidden_dim=hidden_dim,
        latent_dim=latent_dim,
        dropout=dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=learning_rate,
        weight_decay=weight_decay,
    )
    loader = DataLoader(
        TensorDataset(torch.as_tensor(x_train_z, dtype=torch.float32)),
        batch_size=batch_size,
        shuffle=True,
        drop_last=False,
    )
    rng = np.random.default_rng(seed)
    model.train()
    for _epoch in range(epochs):
        for (batch,) in loader:
            model_input, target, missing = make_masked_batch(batch, mask_width, rng, device)
            optimizer.zero_grad(set_to_none=True)
            loss = masked_loss(model(model_input), target, missing, observed_loss_weight)
            loss.backward()
            optimizer.step()
    return model


def autoencoder_predict_masks(
    model: MaskedMLPAutoencoder,
    x_z: np.ndarray,
    mean: np.ndarray,
    std: np.ndarray,
    starts: np.ndarray,
    mask_width: int,
    device: torch.device,
) -> np.ndarray:
    observed = np.ones_like(x_z, dtype=np.float32)
    for row_idx, start in enumerate(starts):
        observed[row_idx, start : start + mask_width] = 0.0
    masked = x_z * observed
    model_input = torch.as_tensor(np.concatenate([masked, observed], axis=1), device=device)
    model.eval()
    with torch.no_grad():
        prediction_z = model(model_input).cpu().numpy()
    return prediction_z * std + mean


def evaluate(
    mask_width: int,
    repeats: int,
    pca_components: list[int],
    epochs: int,
    hidden_dim: int,
    latent_dim: int,
    dropout: float,
    batch_size: int,
    learning_rate: float,
    weight_decay: float,
    observed_loss_weight: float,
    n_splits: int,
    device: torch.device,
) -> dict[str, dict[str, dict[str, float]]]:
    root = project_root()
    _, xrd, samples = load_processed(root)
    metadata = samples[["v_fraction", "temp_c"]].to_numpy(dtype=np.float32)
    starts = mask_starts(
        n_samples=xrd.shape[0],
        n_features=xrd.shape[1],
        mask_width=mask_width,
        repeats=repeats,
    )
    results = {}

    for split_name, splits in split_iterators(samples, n_splits=n_splits).items():
        accumulator = EvaluationAccumulator()
        for fold_idx, (train_idx, test_idx) in enumerate(splits):
            print(
                f"training {split_name} fold {fold_idx + 1}/{len(splits)} "
                f"on {device} ({epochs} epochs)",
                file=sys.stderr,
            )
            train_mean = xrd[train_idx].mean(axis=0)
            metadata_model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
            metadata_model.fit(metadata[train_idx], xrd[train_idx])
            metadata_prediction = metadata_model.predict(metadata[test_idx])
            pca_models = {
                f"pca_missing_{n_components}": MissingPCA.fit(xrd[train_idx], n_components)
                for n_components in pca_components
            }

            x_train_z, mean, std = standardize_train_test(xrd[train_idx], xrd)
            x_all_z = ((xrd - mean) / std).astype(np.float32)
            autoencoder = train_autoencoder(
                x_train_z=x_train_z,
                mask_width=mask_width,
                hidden_dim=hidden_dim,
                latent_dim=latent_dim,
                dropout=dropout,
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=learning_rate,
                weight_decay=weight_decay,
                observed_loss_weight=observed_loss_weight,
                seed=17 + fold_idx + 1000 * len(split_name),
                device=device,
            )

            for repeat in range(repeats):
                repeat_starts = starts[repeat, test_idx]
                auto_prediction = autoencoder_predict_masks(
                    model=autoencoder,
                    x_z=x_all_z[test_idx],
                    mean=mean,
                    std=std,
                    starts=repeat_starts,
                    mask_width=mask_width,
                    device=device,
                )
                for local_idx, sample_idx in enumerate(test_idx):
                    start = int(repeat_starts[local_idx])
                    end = start + mask_width
                    truth = xrd[sample_idx, start:end]

                    accumulator.update("train_mean", truth, train_mean[start:end])
                    accumulator.update(
                        "linear_interpolation",
                        truth,
                        interpolate_masked_region(xrd[sample_idx], start, end),
                    )
                    accumulator.update(
                        "composition_temp_ridge",
                        truth,
                        metadata_prediction[local_idx, start:end],
                    )
                    accumulator.update(
                        "masked_mlp_autoencoder",
                        truth,
                        auto_prediction[local_idx, start:end],
                    )
                    for model_name, model in pca_models.items():
                        accumulator.update(
                            model_name,
                            truth,
                            model.reconstruct_mask(xrd[sample_idx], start, end),
                        )

        results[split_name] = accumulator.metrics()
    return results


def run(args: argparse.Namespace) -> dict[str, object]:
    device = choose_device(args.device)
    result = {
        "dataset_id": DATASET_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "masked_xrd_autoencoder_reconstruction",
        "device": str(device),
        "mask_width": args.mask_width,
        "repeats": args.repeats,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "hidden_dim": args.hidden_dim,
        "latent_dim": args.latent_dim,
        "dropout": args.dropout,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "observed_loss_weight": args.observed_loss_weight,
        "pca_components": args.pca_components,
        "splits": evaluate(
            mask_width=args.mask_width,
            repeats=args.repeats,
            pca_components=args.pca_components,
            epochs=args.epochs,
            hidden_dim=args.hidden_dim,
            latent_dim=args.latent_dim,
            dropout=args.dropout,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            weight_decay=args.weight_decay,
            observed_loss_weight=args.observed_loss_weight,
            n_splits=args.n_splits,
            device=device,
        ),
        "caveats": [
            "This is a tiny neural baseline on 352 spectra, so failure to beat PCA is plausible and informative.",
            "The training objective is masked raw-signal reconstruction; labels are not used.",
            "The model is evaluated only on held-out masked regions, not full-spectrum reconstruction.",
        ],
    }
    output_path = (
        project_root() / "data" / "manifests" / f"{DATASET_ID}_masked_xrd_autoencoder.json"
    )
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=[DATASET_ID], help="Dataset identifier to evaluate.")
    parser.add_argument("--device", default="auto", help="auto, cpu, mps, or cuda.")
    parser.add_argument("--mask-width", type=int, default=256)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--pca-components", type=int, nargs="+", default=[5])
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--hidden-dim", type=int, default=512)
    parser.add_argument("--latent-dim", type=int, default=64)
    parser.add_argument("--dropout", type=float, default=0.05)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument(
        "--observed-loss-weight",
        type=float,
        default=0.05,
        help="Small auxiliary reconstruction loss on unmasked points.",
    )
    parser.add_argument("--n-splits", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dataset == DATASET_ID:
        print(json.dumps(run(args), indent=2, sort_keys=True))
        return
    raise AssertionError(f"Unhandled dataset: {args.dataset}")


if __name__ == "__main__":
    main()
