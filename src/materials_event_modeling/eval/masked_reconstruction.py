"""Shared utilities for masked XRD reconstruction experiments."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.model_selection import GroupKFold, KFold
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

