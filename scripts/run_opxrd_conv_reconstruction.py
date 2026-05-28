"""Train a small 1D convolutional masked reconstructor on the opXRD pilot subset."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import GroupKFold, KFold
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


DATASET_ID = "opxrd"


@dataclass
class ErrorAccumulator:
    squared_error_sum: float = 0.0
    absolute_error_sum: float = 0.0
    count: int = 0

    def update(self, truth: np.ndarray, prediction: np.ndarray) -> None:
        diff = prediction - truth
        self.squared_error_sum += float(np.sum(diff * diff))
        self.absolute_error_sum += float(np.sum(np.abs(diff)))
        self.count += int(diff.size)

    def metrics(self) -> dict[str, float]:
        mse = self.squared_error_sum / self.count
        return {
            "mae": self.absolute_error_sum / self.count,
            "mse": mse,
            "rmse": float(np.sqrt(mse)),
        }


@dataclass
class EvaluationAccumulator:
    models: dict[str, ErrorAccumulator] = field(default_factory=lambda: defaultdict(ErrorAccumulator))

    def update(self, model_name: str, truth: np.ndarray, prediction: np.ndarray) -> None:
        self.models[model_name].update(truth, prediction)

    def metrics(self) -> dict[str, dict[str, float]]:
        results = {name: acc.metrics() for name, acc in sorted(self.models.items())}
        mean_mse = results["train_mean"]["mse"]
        for values in results.values():
            values["relative_mse_vs_train_mean"] = values["mse"] / mean_mse
            values["mse_improvement_vs_train_mean"] = 1.0 - values["relative_mse_vs_train_mean"]
        return results


class ResidualConvBlock(nn.Module):
    def __init__(self, channels: int, dilation: int, dropout: float) -> None:
        super().__init__()
        padding = dilation
        self.net = nn.Sequential(
            nn.Conv1d(channels, channels, kernel_size=3, padding=padding, dilation=dilation),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Conv1d(channels, channels, kernel_size=3, padding=padding, dilation=dilation),
        )
        self.activation = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.activation(x + self.net(x))


class MaskedConvReconstructor(nn.Module):
    """A compact dilated CNN for masked 1D XRD reconstruction."""

    def __init__(self, channels: int, depth: int, dropout: float) -> None:
        super().__init__()
        blocks = []
        for idx in range(depth):
            blocks.append(ResidualConvBlock(channels, dilation=2 ** idx, dropout=dropout))
        self.net = nn.Sequential(
            nn.Conv1d(2, channels, kernel_size=7, padding=3),
            nn.GELU(),
            *blocks,
            nn.Conv1d(channels, 1, kernel_size=1),
        )

    def forward(self, masked_spectrum: torch.Tensor, observed_mask: torch.Tensor) -> torch.Tensor:
        x = torch.stack([masked_spectrum, observed_mask], dim=1)
        return self.net(x).squeeze(1)


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


def load_subset(root: Path) -> tuple[np.ndarray, pd.DataFrame]:
    manifest_path = root / "data" / "manifests" / "opxrd_processed_subset.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            "Processed opXRD subset is missing. Run "
            "`.venv/bin/python scripts/preprocess_opxrd.py --max-spectra 4096 --points 4096` first."
        )
    manifest = json.loads(manifest_path.read_text())
    arrays_path = root / manifest["arrays_path"]
    samples_path = root / manifest["samples_path"]
    with np.load(arrays_path) as data:
        xrd = data["xrd"].astype(np.float32)
    samples = pd.read_csv(samples_path)
    samples["top_level_source"] = samples["member_name"].str.split("/", n=1).str[0]
    return xrd, samples


def select_spread_indices(n_samples: int, max_samples: int) -> np.ndarray:
    if max_samples >= n_samples:
        return np.arange(n_samples)
    return np.linspace(0, n_samples - 1, num=max_samples, dtype=np.int64)


def allocate_source_balanced_counts(
    source_counts: dict[str, int],
    max_samples: int,
    alpha: float,
) -> dict[str, int]:
    total_available = sum(source_counts.values())
    if max_samples >= total_available:
        return dict(source_counts)
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("--source-balance-alpha must be between 0 and 1.")

    allocated = {source: 0 for source in source_counts}
    remaining = max_samples
    active = set(source_counts)
    while remaining > 0 and active:
        weights = {source: float(source_counts[source]) ** alpha for source in active}
        weight_sum = sum(weights.values())
        increments = {}
        for source in sorted(active):
            available = source_counts[source] - allocated[source]
            raw = remaining * weights[source] / weight_sum
            increments[source] = min(available, int(np.floor(raw)))

        if sum(increments.values()) == 0:
            source = max(active, key=lambda item: source_counts[item] - allocated[item])
            increments[source] = 1

        for source, increment in increments.items():
            allocated[source] += increment
            remaining -= increment
        active = {
            source
            for source in active
            if allocated[source] < source_counts[source]
        }

    return allocated


def select_sample_indices(
    samples: pd.DataFrame,
    max_samples: int,
    strategy: str,
    source_balance_alpha: float,
) -> np.ndarray:
    if strategy == "spread":
        return select_spread_indices(len(samples), max_samples)
    if strategy != "source_balanced":
        raise ValueError(f"Unsupported sample strategy: {strategy}")

    source_counts = samples["top_level_source"].value_counts().sort_index().to_dict()
    target_counts = allocate_source_balanced_counts(
        source_counts=source_counts,
        max_samples=max_samples,
        alpha=source_balance_alpha,
    )
    selected = []
    for source, target_count in sorted(target_counts.items()):
        source_indices = np.flatnonzero(samples["top_level_source"].to_numpy() == source)
        if target_count >= len(source_indices):
            selected.extend(source_indices.tolist())
        elif target_count > 0:
            selected.extend(
                source_indices[
                    np.linspace(0, len(source_indices) - 1, num=target_count, dtype=np.int64)
                ].tolist()
            )
    return np.array(sorted(selected), dtype=np.int64)


def split_iterators(
    samples: pd.DataFrame,
    n_splits: int,
    split_kinds: list[str],
    seed: int,
) -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
    indices = np.arange(len(samples))
    splits: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {}
    if "random_kfold" in split_kinds:
        random_cv = KFold(n_splits=n_splits, shuffle=True, random_state=17 + seed)
        splits["random_kfold"] = list(random_cv.split(indices))
    if "held_out_top_level_source" in split_kinds:
        groups = samples["top_level_source"].to_numpy()
        group_splits = min(n_splits, len(np.unique(groups)))
        grouped_cv = GroupKFold(n_splits=group_splits)
        splits["held_out_top_level_source"] = list(grouped_cv.split(indices, groups=groups))
    return splits


def random_mask_starts(
    n_samples: int,
    n_features: int,
    mask_width: int,
    repeats: int,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(1701 + mask_width + seed)
    return rng.integers(0, n_features - mask_width + 1, size=(repeats, n_samples))


def peak_mask_starts(
    xrd: np.ndarray,
    mask_width: int,
    repeats: int,
    peak_top_fraction: float,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(3407 + mask_width + seed)
    n_samples, n_features = xrd.shape
    starts = np.empty((repeats, n_samples), dtype=np.int64)
    candidates_per_spectrum = max(8, int(round(n_features * peak_top_fraction)))
    candidates_per_spectrum = min(candidates_per_spectrum, n_features)

    for sample_idx, spectrum in enumerate(xrd):
        candidate_indices = np.argpartition(spectrum, -candidates_per_spectrum)[
            -candidates_per_spectrum:
        ]
        if candidate_indices.size == 0 or float(np.max(spectrum[candidate_indices])) <= 0:
            starts[:, sample_idx] = rng.integers(0, n_features - mask_width + 1, size=repeats)
            continue
        for repeat in range(repeats):
            center = int(rng.choice(candidate_indices))
            starts[repeat, sample_idx] = int(
                np.clip(center - mask_width // 2, 0, n_features - mask_width)
            )
    return starts


def build_mask_starts(
    xrd: np.ndarray,
    mask_width: int,
    repeats: int,
    strategy: str,
    peak_top_fraction: float,
    seed: int,
) -> np.ndarray:
    if strategy == "random":
        return random_mask_starts(
            n_samples=xrd.shape[0],
            n_features=xrd.shape[1],
            mask_width=mask_width,
            repeats=repeats,
            seed=seed,
        )
    if strategy == "peak":
        return peak_mask_starts(
            xrd=xrd,
            mask_width=mask_width,
            repeats=repeats,
            peak_top_fraction=peak_top_fraction,
            seed=seed,
        )
    raise ValueError(f"Unsupported mask strategy: {strategy}")


def make_observed_masks(
    spectra: np.ndarray,
    starts: np.ndarray,
    mask_width: int,
) -> np.ndarray:
    observed = np.ones_like(spectra, dtype=np.float32)
    for row_idx, start in enumerate(starts):
        observed[row_idx, start : start + mask_width] = 0.0
    return observed


def interpolation_baseline_full(
    spectra: np.ndarray,
    starts: np.ndarray,
    mask_width: int,
) -> np.ndarray:
    baseline = spectra.copy()
    for row_idx, start in enumerate(starts):
        end = int(start) + mask_width
        baseline[row_idx, start:end] = interpolate_masked_region(spectra[row_idx], int(start), end)
    return baseline.astype(np.float32)


def sample_training_starts(
    batch: np.ndarray,
    mask_width: int,
    strategy: str,
    peak_top_fraction: float,
    rng: np.random.Generator,
) -> np.ndarray:
    n_samples, n_features = batch.shape
    if strategy == "random":
        return rng.integers(0, n_features - mask_width + 1, size=n_samples)
    if strategy != "peak":
        raise ValueError(f"Unsupported training mask strategy: {strategy}")

    starts = np.empty(n_samples, dtype=np.int64)
    candidates_per_spectrum = max(8, int(round(n_features * peak_top_fraction)))
    candidates_per_spectrum = min(candidates_per_spectrum, n_features)
    for row_idx, spectrum in enumerate(batch):
        candidate_indices = np.argpartition(spectrum, -candidates_per_spectrum)[
            -candidates_per_spectrum:
        ]
        if candidate_indices.size == 0 or float(np.max(spectrum[candidate_indices])) <= 0:
            starts[row_idx] = int(rng.integers(0, n_features - mask_width + 1))
            continue
        center = int(rng.choice(candidate_indices))
        starts[row_idx] = int(np.clip(center - mask_width // 2, 0, n_features - mask_width))
    return starts


def make_training_batch(
    batch: torch.Tensor,
    mask_width: int,
    strategy: str,
    peak_top_fraction: float,
    prediction_mode: str,
    rng: np.random.Generator,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    batch_np = batch.numpy()
    starts = sample_training_starts(
        batch=batch_np,
        mask_width=mask_width,
        strategy=strategy,
        peak_top_fraction=peak_top_fraction,
        rng=rng,
    )
    observed = make_observed_masks(batch_np, starts, mask_width)
    if prediction_mode == "residual":
        baseline = interpolation_baseline_full(batch_np, starts, mask_width)
    elif prediction_mode == "direct":
        baseline = np.zeros_like(batch_np, dtype=np.float32)
    else:
        raise ValueError(f"Unsupported prediction mode: {prediction_mode}")
    target = torch.as_tensor(batch_np, dtype=torch.float32, device=device)
    observed_tensor = torch.as_tensor(observed, dtype=torch.float32, device=device)
    baseline_tensor = torch.as_tensor(baseline, dtype=torch.float32, device=device)
    masked = target * observed_tensor
    missing = 1.0 - observed_tensor
    return masked, observed_tensor, baseline_tensor, missing


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


def train_model(
    x_train: np.ndarray,
    mask_width: int,
    train_mask_strategy: str,
    prediction_mode: str,
    peak_top_fraction: float,
    channels: int,
    depth: int,
    dropout: float,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    weight_decay: float,
    observed_loss_weight: float,
    seed: int,
    device: torch.device,
) -> tuple[MaskedConvReconstructor, list[float]]:
    torch.manual_seed(seed)
    model = MaskedConvReconstructor(channels=channels, depth=depth, dropout=dropout).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    loader = DataLoader(
        TensorDataset(torch.as_tensor(x_train, dtype=torch.float32)),
        batch_size=batch_size,
        shuffle=True,
        drop_last=False,
    )
    rng = np.random.default_rng(seed)
    losses = []
    model.train()
    for _epoch in range(epochs):
        epoch_loss = 0.0
        epoch_batches = 0
        for (batch,) in loader:
            masked, observed, baseline, missing = make_training_batch(
                batch=batch,
                mask_width=mask_width,
                strategy=train_mask_strategy,
                peak_top_fraction=peak_top_fraction,
                prediction_mode=prediction_mode,
                rng=rng,
                device=device,
            )
            target = batch.to(device)
            optimizer.zero_grad(set_to_none=True)
            prediction = model(masked, observed)
            if prediction_mode == "residual":
                prediction = baseline + prediction
            loss = masked_loss(prediction, target, missing, observed_loss_weight)
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.detach().cpu())
            epoch_batches += 1
        losses.append(epoch_loss / max(epoch_batches, 1))
    return model, losses


def predict_masks(
    model: MaskedConvReconstructor,
    spectra: np.ndarray,
    starts: np.ndarray,
    mask_width: int,
    prediction_mode: str,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    observed = make_observed_masks(spectra, starts, mask_width)
    if prediction_mode == "residual":
        baseline = interpolation_baseline_full(spectra, starts, mask_width)
    elif prediction_mode == "direct":
        baseline = np.zeros_like(spectra, dtype=np.float32)
    else:
        raise ValueError(f"Unsupported prediction mode: {prediction_mode}")
    predictions = []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(spectra), batch_size):
            end = start + batch_size
            target = torch.as_tensor(spectra[start:end], dtype=torch.float32, device=device)
            observed_tensor = torch.as_tensor(observed[start:end], dtype=torch.float32, device=device)
            baseline_tensor = torch.as_tensor(baseline[start:end], dtype=torch.float32, device=device)
            masked = target * observed_tensor
            prediction = model(masked, observed_tensor)
            if prediction_mode == "residual":
                prediction = baseline_tensor + prediction
            prediction = prediction.cpu().numpy()
            predictions.append(prediction)
    return np.concatenate(predictions, axis=0)


def interpolate_masked_region(spectrum: np.ndarray, start: int, end: int) -> np.ndarray:
    positions = np.arange(spectrum.size)
    mask = np.ones(spectrum.size, dtype=bool)
    mask[start:end] = False
    return np.interp(positions[start:end], positions[mask], spectrum[mask])


def evaluate(
    xrd: np.ndarray,
    samples: pd.DataFrame,
    mask_width: int,
    eval_mask_strategy: str,
    train_mask_strategy: str,
    prediction_mode: str,
    repeats: int,
    n_splits: int,
    split_kinds: list[str],
    peak_top_fraction: float,
    seed: int,
    channels: int,
    depth: int,
    dropout: float,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    weight_decay: float,
    observed_loss_weight: float,
    device: torch.device,
) -> tuple[dict[str, dict[str, dict[str, float]]], dict[str, list[float]]]:
    eval_starts = build_mask_starts(
        xrd=xrd,
        mask_width=mask_width,
        repeats=repeats,
        strategy=eval_mask_strategy,
        peak_top_fraction=peak_top_fraction,
        seed=seed,
    )
    results = {}
    fold_losses = {}

    for split_name, splits in split_iterators(samples, n_splits, split_kinds, seed).items():
        accumulator = EvaluationAccumulator()

        for fold_idx, (train_idx, test_idx) in enumerate(splits):
            print(
                f"training {split_name} fold {fold_idx + 1}/{len(splits)} "
                f"on {device} ({epochs} epochs)",
                file=sys.stderr,
            )
            train_mean = xrd[train_idx].mean(axis=0)
            model, losses = train_model(
                x_train=xrd[train_idx],
                mask_width=mask_width,
                train_mask_strategy=train_mask_strategy,
                prediction_mode=prediction_mode,
                peak_top_fraction=peak_top_fraction,
                channels=channels,
                depth=depth,
                dropout=dropout,
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=learning_rate,
                weight_decay=weight_decay,
                observed_loss_weight=observed_loss_weight,
                seed=17 + seed + fold_idx + 1000 * len(split_name),
                device=device,
            )
            fold_losses[f"{split_name}_fold_{fold_idx}"] = losses

            for repeat in range(repeats):
                repeat_starts = eval_starts[repeat, test_idx]
                conv_prediction = predict_masks(
                    model=model,
                    spectra=xrd[test_idx],
                    starts=repeat_starts,
                    mask_width=mask_width,
                    prediction_mode=prediction_mode,
                    batch_size=batch_size,
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
                        "masked_conv_reconstructor",
                        truth,
                        conv_prediction[local_idx, start:end],
                    )

        results[split_name] = accumulator.metrics()
    return results, fold_losses


def run(args: argparse.Namespace) -> dict[str, object]:
    device = choose_device(args.device)
    root = project_root()
    xrd, samples = load_subset(root)
    selected = select_sample_indices(
        samples=samples,
        max_samples=args.max_samples,
        strategy=args.sample_strategy,
        source_balance_alpha=args.source_balance_alpha,
    )
    xrd = xrd[selected]
    samples = samples.iloc[selected].reset_index(drop=True)

    splits, fold_losses = evaluate(
        xrd=xrd,
        samples=samples,
        mask_width=args.mask_width,
        eval_mask_strategy=args.eval_mask_strategy,
        train_mask_strategy=args.train_mask_strategy,
        prediction_mode=args.prediction_mode,
        repeats=args.repeats,
        n_splits=args.n_splits,
        split_kinds=args.split_kinds,
        peak_top_fraction=args.peak_top_fraction,
        seed=args.seed,
        channels=args.channels,
        depth=args.depth,
        dropout=args.dropout,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        observed_loss_weight=args.observed_loss_weight,
        device=device,
    )
    result = {
        "dataset_id": DATASET_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "masked_xrd_conv_reconstruction",
        "subset": "opxrd_processed_subset",
        "spectra": int(xrd.shape[0]),
        "theta_points": int(xrd.shape[1]),
        "sample_strategy": args.sample_strategy,
        "source_balance_alpha": args.source_balance_alpha,
        "top_level_source_counts": samples["top_level_source"].value_counts().sort_index().to_dict(),
        "device": str(device),
        "mask_width": args.mask_width,
        "train_mask_strategy": args.train_mask_strategy,
        "eval_mask_strategy": args.eval_mask_strategy,
        "prediction_mode": args.prediction_mode,
        "peak_top_fraction": args.peak_top_fraction,
        "seed": args.seed,
        "repeats": args.repeats,
        "n_splits": args.n_splits,
        "split_kinds": args.split_kinds,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "channels": args.channels,
        "depth": args.depth,
        "dropout": args.dropout,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "observed_loss_weight": args.observed_loss_weight,
        "approximate_receptive_field": int(1 + 4 * sum(2**idx for idx in range(args.depth))),
        "splits": splits,
        "fold_loss_first_last": {
            fold: {"first": losses[0], "last": losses[-1]} for fold, losses in fold_losses.items()
        },
        "caveats": [
            "This is a small neural pilot on a fixed opXRD subset, not full-scale pretraining.",
            "The training objective is raw-signal reconstruction; labels are not used.",
            "The key comparison is against local interpolation on peak masks and held-out-source splits.",
        ],
    }
    output_path = root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="auto", help="auto, cpu, mps, or cuda.")
    parser.add_argument("--max-samples", type=int, default=512)
    parser.add_argument(
        "--sample-strategy",
        choices=["spread", "source_balanced"],
        default="spread",
        help="How to choose a subset from the processed opXRD archive sample.",
    )
    parser.add_argument(
        "--source-balance-alpha",
        type=float,
        default=0.5,
        help="Source allocation exponent for source_balanced sampling; 1=count-proportional, 0=equal-source.",
    )
    parser.add_argument("--mask-width", type=int, default=1024)
    parser.add_argument("--train-mask-strategy", choices=["random", "peak"], default="peak")
    parser.add_argument("--eval-mask-strategy", choices=["random", "peak"], default="peak")
    parser.add_argument("--prediction-mode", choices=["direct", "residual"], default="direct")
    parser.add_argument("--peak-top-fraction", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--n-splits", type=int, default=3)
    parser.add_argument(
        "--split-kinds",
        nargs="+",
        choices=["random_kfold", "held_out_top_level_source"],
        default=["random_kfold", "held_out_top_level_source"],
    )
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--channels", type=int, default=32)
    parser.add_argument("--depth", type=int, default=10)
    parser.add_argument("--dropout", type=float, default=0.05)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--observed-loss-weight", type=float, default=0.05)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/opxrd_masked_xrd_conv_reconstruction.json"),
        help="Path for the JSON result, relative to project root unless absolute.",
    )
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
