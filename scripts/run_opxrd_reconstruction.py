"""Run masked-XRD reconstruction baselines on the opXRD pilot subset."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.model_selection import GroupKFold, KFold
from sklearn.preprocessing import StandardScaler


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


@dataclass(frozen=True)
class MissingPCA:
    scaler: StandardScaler
    pca: PCA

    @classmethod
    def fit(cls, x_train: np.ndarray, max_components: int) -> "MissingPCA":
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_train)
        pca = PCA(
            n_components=max_components,
            random_state=17,
            svd_solver="randomized",
            iterated_power=3,
        )
        pca.fit(x_scaled)
        return cls(scaler=scaler, pca=pca)

    def reconstruct_mask(self, spectrum: np.ndarray, start: int, end: int, n_components: int) -> np.ndarray:
        observed = np.ones(spectrum.size, dtype=bool)
        observed[start:end] = False

        components = self.pca.components_[:n_components]
        scaled = self.scaler.transform(spectrum[None, :])[0]
        centered_observed = scaled[observed] - self.pca.mean_[observed]
        basis_observed = components[:, observed].T
        coefficients, *_ = np.linalg.lstsq(basis_observed, centered_observed, rcond=None)
        reconstructed_scaled = self.pca.mean_ + coefficients @ components
        reconstructed = self.scaler.inverse_transform(reconstructed_scaled[None, :])[0]
        return reconstructed[start:end]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


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


def select_sample_indices(n_samples: int, max_samples: int) -> np.ndarray:
    if max_samples >= n_samples:
        return np.arange(n_samples)
    return np.linspace(0, n_samples - 1, num=max_samples, dtype=np.int64)


def random_mask_starts(n_samples: int, n_features: int, mask_width: int, repeats: int) -> np.ndarray:
    rng = np.random.default_rng(1701 + mask_width)
    return rng.integers(0, n_features - mask_width + 1, size=(repeats, n_samples))


def peak_mask_starts(
    xrd: np.ndarray,
    mask_width: int,
    repeats: int,
    peak_top_fraction: float,
) -> np.ndarray:
    if not 0 < peak_top_fraction <= 1:
        raise ValueError("peak_top_fraction must be in (0, 1]")

    rng = np.random.default_rng(3407 + mask_width)
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
            start = center - mask_width // 2
            starts[repeat, sample_idx] = int(np.clip(start, 0, n_features - mask_width))
    return starts


def build_mask_starts(
    xrd: np.ndarray,
    mask_width: int,
    repeats: int,
    strategy: str,
    peak_top_fraction: float,
) -> np.ndarray:
    if strategy == "random":
        return random_mask_starts(
            n_samples=xrd.shape[0],
            n_features=xrd.shape[1],
            mask_width=mask_width,
            repeats=repeats,
        )
    if strategy == "peak":
        return peak_mask_starts(
            xrd=xrd,
            mask_width=mask_width,
            repeats=repeats,
            peak_top_fraction=peak_top_fraction,
        )
    raise ValueError(f"Unsupported mask strategy: {strategy}")


def interpolate_masked_region(spectrum: np.ndarray, start: int, end: int) -> np.ndarray:
    positions = np.arange(spectrum.size)
    mask = np.ones(spectrum.size, dtype=bool)
    mask[start:end] = False
    return np.interp(positions[start:end], positions[mask], spectrum[mask])


def split_iterators(
    samples: pd.DataFrame,
    n_splits: int,
) -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
    indices = np.arange(len(samples))
    random_cv = KFold(n_splits=n_splits, shuffle=True, random_state=17)
    groups = samples["top_level_source"].to_numpy()
    group_splits = min(n_splits, len(np.unique(groups)))
    grouped_cv = GroupKFold(n_splits=group_splits)
    return {
        "random_kfold": list(random_cv.split(indices)),
        "held_out_top_level_source": list(grouped_cv.split(indices, groups=groups)),
    }


def evaluate_mask_width(
    xrd: np.ndarray,
    samples: pd.DataFrame,
    mask_width: int,
    mask_strategy: str,
    repeats: int,
    pca_components: list[int],
    n_splits: int,
    peak_top_fraction: float,
) -> dict[str, dict[str, dict[str, float]]]:
    starts = build_mask_starts(
        xrd=xrd,
        mask_width=mask_width,
        repeats=repeats,
        strategy=mask_strategy,
        peak_top_fraction=peak_top_fraction,
    )
    results = {}

    for split_name, splits in split_iterators(samples, n_splits=n_splits).items():
        accumulator = EvaluationAccumulator()

        for train_idx, test_idx in splits:
            train_mean = xrd[train_idx].mean(axis=0)
            pca_model = MissingPCA.fit(xrd[train_idx], max(pca_components))

            for repeat in range(repeats):
                for sample_idx in test_idx:
                    start = int(starts[repeat, sample_idx])
                    end = start + mask_width
                    truth = xrd[sample_idx, start:end]

                    accumulator.update("train_mean", truth, train_mean[start:end])
                    accumulator.update(
                        "linear_interpolation",
                        truth,
                        interpolate_masked_region(xrd[sample_idx], start, end),
                    )
                    for n_components in pca_components:
                        accumulator.update(
                            f"pca_missing_{n_components}",
                            truth,
                            pca_model.reconstruct_mask(
                                xrd[sample_idx], start, end, n_components=n_components
                            ),
                        )

        results[split_name] = accumulator.metrics()

    return results


def run(
    max_samples: int,
    mask_widths: list[int],
    mask_strategies: list[str],
    repeats: int,
    pca_components: list[int],
    n_splits: int,
    peak_top_fraction: float,
) -> dict[str, object]:
    root = project_root()
    xrd, samples = load_subset(root)
    selected = select_sample_indices(len(samples), max_samples=max_samples)
    xrd = xrd[selected]
    samples = samples.iloc[selected].reset_index(drop=True)

    results: dict[str, object] = {
        "dataset_id": DATASET_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "masked_xrd_reconstruction",
        "subset": "opxrd_processed_subset",
        "spectra": int(xrd.shape[0]),
        "theta_points": int(xrd.shape[1]),
        "top_level_source_counts": samples["top_level_source"].value_counts().sort_index().to_dict(),
        "repeats": repeats,
        "pca_components": pca_components,
        "peak_top_fraction": peak_top_fraction,
        "mask_strategies": {},
        "caveats": [
            "This evaluates reconstruction on a pilot subset, not full-dataset pretraining.",
            "Held-out-top-level-source splits stress contributor/instrument shift, not causal mechanisms.",
            "Any neural raw-XRD encoder should beat the strongest simple baseline, including local interpolation where it applies.",
        ],
    }

    for mask_strategy in mask_strategies:
        results["mask_strategies"][mask_strategy] = {}
        for mask_width in mask_widths:
            results["mask_strategies"][mask_strategy][str(mask_width)] = evaluate_mask_width(
                xrd=xrd,
                samples=samples,
                mask_width=mask_width,
                mask_strategy=mask_strategy,
                repeats=repeats,
                pca_components=pca_components,
                n_splits=n_splits,
                peak_top_fraction=peak_top_fraction,
            )

    output_path = root / "data" / "manifests" / "opxrd_masked_xrd_reconstruction_subset.json"
    output_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-samples", type=int, default=1024)
    parser.add_argument("--mask-widths", type=int, nargs="+", default=[256])
    parser.add_argument("--mask-strategies", nargs="+", choices=["random", "peak"], default=["random"])
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--pca-components", type=int, nargs="+", default=[16, 64])
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument(
        "--peak-top-fraction",
        type=float,
        default=0.02,
        help="For peak masks, sample centers from each spectrum's top intensity fraction.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        json.dumps(
            run(
                max_samples=args.max_samples,
                mask_widths=args.mask_widths,
                mask_strategies=args.mask_strategies,
                repeats=args.repeats,
                pca_components=args.pca_components,
                n_splits=args.n_splits,
                peak_top_fraction=args.peak_top_fraction,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
