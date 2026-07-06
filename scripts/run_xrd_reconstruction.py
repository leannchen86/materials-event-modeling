"""Run masked-XRD reconstruction baselines on the NIST dataset."""

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
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold, KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from materials_event_modeling.data.nist import DATASET_ID

SPECTRUM_SCALE = 1000.0


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


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_processed(root: Path) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    arrays_path = root / "data" / "processed" / DATASET_ID / "xrd_arrays.npz"
    samples_path = root / "data" / "interim" / DATASET_ID / "samples.csv"
    if not arrays_path.exists() or not samples_path.exists():
        raise FileNotFoundError(
            "Processed NIST files are missing. Run "
            "`python3 scripts/preprocess_xrd.py nist_mds2_2301` first."
        )
    arrays = np.load(arrays_path)
    theta = arrays["theta"].astype(np.float32)
    # Scale area-normalized spectra so absolute errors are readable. Relative metrics are unchanged.
    xrd = arrays["xrd_area_norm"].astype(np.float32) * SPECTRUM_SCALE
    samples = pd.read_csv(samples_path)
    return theta, xrd, samples


def mask_starts(n_samples: int, n_features: int, mask_width: int, repeats: int) -> np.ndarray:
    rng = np.random.default_rng(17 + mask_width)
    return rng.integers(0, n_features - mask_width + 1, size=(repeats, n_samples))


def interpolate_masked_region(spectrum: np.ndarray, start: int, end: int) -> np.ndarray:
    positions = np.arange(spectrum.size)
    mask = np.ones(spectrum.size, dtype=bool)
    mask[start:end] = False
    return np.interp(positions[start:end], positions[mask], spectrum[mask])


@dataclass(frozen=True)
class MissingPCA:
    scaler: StandardScaler
    pca: PCA

    @classmethod
    def fit(cls, x_train: np.ndarray, n_components: int) -> MissingPCA:
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_train)
        pca = PCA(n_components=n_components, random_state=17)
        pca.fit(x_scaled)
        return cls(scaler=scaler, pca=pca)

    def reconstruct_mask(self, spectrum: np.ndarray, start: int, end: int) -> np.ndarray:
        observed = np.ones(spectrum.size, dtype=bool)
        observed[start:end] = False

        scaled = self.scaler.transform(spectrum[None, :])[0]
        centered_observed = scaled[observed] - self.pca.mean_[observed]
        basis_observed = self.pca.components_[:, observed].T
        coefficients, *_ = np.linalg.lstsq(basis_observed, centered_observed, rcond=None)
        reconstructed_scaled = self.pca.mean_ + coefficients @ self.pca.components_
        reconstructed = self.scaler.inverse_transform(reconstructed_scaled[None, :])[0]
        return reconstructed[start:end]


def split_iterators(samples: pd.DataFrame, n_splits: int) -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
    indices = np.arange(len(samples))
    groups = samples["temp_c"].to_numpy()
    random_cv = KFold(n_splits=n_splits, shuffle=True, random_state=17)
    grouped_cv = GroupKFold(n_splits=len(np.unique(groups)))
    return {
        "random_kfold": list(random_cv.split(indices)),
        "held_out_temperature": list(grouped_cv.split(indices, groups=groups)),
    }


def evaluate_mask_width(
    xrd: np.ndarray,
    metadata: np.ndarray,
    samples: pd.DataFrame,
    mask_width: int,
    repeats: int,
    pca_components: list[int],
    n_splits: int,
) -> dict[str, dict[str, dict[str, float]]]:
    starts = mask_starts(
        n_samples=xrd.shape[0],
        n_features=xrd.shape[1],
        mask_width=mask_width,
        repeats=repeats,
    )
    results = {}

    for split_name, splits in split_iterators(samples, n_splits=n_splits).items():
        accumulator = EvaluationAccumulator()

        for train_idx, test_idx in splits:
            train_mean = xrd[train_idx].mean(axis=0)
            metadata_model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
            metadata_model.fit(metadata[train_idx], xrd[train_idx])
            metadata_prediction = metadata_model.predict(metadata[test_idx])

            pca_models = {
                f"pca_missing_{n_components}": MissingPCA.fit(xrd[train_idx], n_components)
                for n_components in pca_components
            }

            for repeat in range(repeats):
                for local_idx, sample_idx in enumerate(test_idx):
                    start = int(starts[repeat, sample_idx])
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
                    for model_name, model in pca_models.items():
                        accumulator.update(
                            model_name,
                            truth,
                            model.reconstruct_mask(xrd[sample_idx], start, end),
                        )

        results[split_name] = accumulator.metrics()

    return results


def run(mask_widths: list[int], repeats: int, pca_components: list[int], n_splits: int) -> dict[str, object]:
    root = project_root()
    _, xrd, samples = load_processed(root)
    metadata = samples[["v_fraction", "temp_c"]].to_numpy(dtype=np.float32)

    results: dict[str, object] = {
        "dataset_id": DATASET_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "masked_xrd_reconstruction",
        "spectrum_input": "xrd_area_norm_scaled_by_1000",
        "spectra": int(xrd.shape[0]),
        "theta_points": int(xrd.shape[1]),
        "repeats": repeats,
        "pca_components": pca_components,
        "mask_widths": {},
        "caveats": [
            "This is a reconstruction/prediction task, not a causal claim.",
            "Linear interpolation is a strong local baseline for smooth regions but cannot infer hidden peaks well.",
            "Held-out-temperature splits test extrapolation across temperatures and are much harder than random folds.",
        ],
    }

    for mask_width in mask_widths:
        results["mask_widths"][str(mask_width)] = evaluate_mask_width(
            xrd=xrd,
            metadata=metadata,
            samples=samples,
            mask_width=mask_width,
            repeats=repeats,
            pca_components=pca_components,
            n_splits=n_splits,
        )

    output_path = root / "data" / "manifests" / f"{DATASET_ID}_masked_xrd_reconstruction.json"
    output_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=[DATASET_ID], help="Dataset identifier to evaluate.")
    parser.add_argument("--mask-widths", type=int, nargs="+", default=[256])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--pca-components", type=int, nargs="+", default=[5, 10, 25])
    parser.add_argument("--n-splits", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dataset == DATASET_ID:
        print(
            json.dumps(
                run(
                    mask_widths=args.mask_widths,
                    repeats=args.repeats,
                    pca_components=args.pca_components,
                    n_splits=args.n_splits,
                ),
                indent=2,
                sort_keys=True,
            )
        )
        return
    raise AssertionError(f"Unhandled dataset: {args.dataset}")


if __name__ == "__main__":
    main()

