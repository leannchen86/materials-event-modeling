"""Evaluation utilities for Track B synthetic event scaffolds."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log2

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.metrics import silhouette_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass(frozen=True)
class PredictionResult:
    mse: float
    relative_mse_vs_train_mean: float
    mse_improvement_vs_train_mean: float


PLANNED_CONDITION_COLUMNS = [
    "planned_temperature_c",
    "planned_aging_time_minutes",
    "planned_mixing_intensity",
    "planned_additive_level",
]

OBSERVED_TRAJECTORY_COLUMNS = [
    "observed_temperature_c",
    "observed_aging_time_minutes",
    "observed_mixing_intensity",
    "observed_additive_level",
    "initial_ph",
    "final_ph",
    "early_turbidity",
]

FULL_EVENT_COLUMNS = PLANNED_CONDITION_COLUMNS + OBSERVED_TRAJECTORY_COLUMNS


def mean_squared_error(truth: np.ndarray, prediction: np.ndarray) -> float:
    diff = truth - prediction
    return float(np.mean(diff * diff))


def numeric_matrix(table: pd.DataFrame, columns: list[str]) -> np.ndarray:
    values = table[columns].astype(float).copy()
    for column in columns:
        values[column] = values[column].fillna(values[column].median())
    return values.to_numpy(dtype=np.float32)


def label_matrix(table: pd.DataFrame) -> np.ndarray:
    encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    return encoder.fit_transform(table[["legacy_label"]]).astype(np.float32)


def cross_validated_spectrum_prediction(
    table: pd.DataFrame,
    spectra: np.ndarray,
    features: np.ndarray,
    *,
    groups: np.ndarray,
    n_splits: int,
) -> PredictionResult:
    group_cv = GroupKFold(n_splits=n_splits)
    train_mean_errors = []
    model_errors = []
    for train_idx, test_idx in group_cv.split(features, groups=groups):
        train_mean = spectra[train_idx].mean(axis=0)
        model = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
        model.fit(features[train_idx], spectra[train_idx])
        prediction = model.predict(features[test_idx])
        train_mean_prediction = np.tile(train_mean, (test_idx.size, 1))
        train_mean_errors.append(mean_squared_error(spectra[test_idx], train_mean_prediction))
        model_errors.append(mean_squared_error(spectra[test_idx], prediction))

    train_mean_mse = float(np.mean(train_mean_errors))
    model_mse = float(np.mean(model_errors))
    relative = model_mse / train_mean_mse
    return PredictionResult(
        mse=model_mse,
        relative_mse_vs_train_mean=relative,
        mse_improvement_vs_train_mean=1.0 - relative,
    )


def nearest_neighbor_hit_rate(features: np.ndarray, groups: np.ndarray) -> float:
    scaler = StandardScaler()
    x = scaler.fit_transform(features)
    distances = np.sum((x[:, None, :] - x[None, :, :]) ** 2, axis=2)
    np.fill_diagonal(distances, np.inf)
    nearest = np.argmin(distances, axis=1)
    return float(np.mean(groups[nearest] == groups))


def entropy(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return -sum((count / total) * log2(count / total) for count in counts.values())


def label_projection_audit(table: pd.DataFrame) -> dict[str, object]:
    label_summaries = {}
    entropies = []
    for label, label_rows in table.groupby("legacy_label"):
        regime_counts = Counter(label_rows["hidden_regime"])
        label_entropy = entropy(regime_counts)
        entropies.append(label_entropy)
        label_summaries[label] = {
            "events": len(label_rows),
            "hidden_regime_counts": dict(sorted(regime_counts.items())),
            "hidden_regime_entropy": label_entropy,
            "splits_into_multiple_regimes": len(regime_counts) > 1,
        }
    return {
        "labels": label_summaries,
        "mean_hidden_regime_entropy_per_label": float(np.mean(entropies)),
        "labels_that_split": [
            label
            for label, summary in label_summaries.items()
            if summary["splits_into_multiple_regimes"]
        ],
    }


def silhouette_audit(table: pd.DataFrame, spectra: np.ndarray) -> dict[str, float]:
    projected = PCA(n_components=8, random_state=17).fit_transform(spectra)
    results = {}
    for column in ["legacy_label", "hidden_regime"]:
        labels = table[column].astype(str).to_numpy()
        if len(set(labels)) < 2:
            results[column] = 0.0
        else:
            results[column] = float(silhouette_score(projected, labels))
    return results


def missingness_report(table: pd.DataFrame) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for value in table["missing_fields"].fillna(""):
        for field in str(value).split(";"):
            if field:
                counts[field] += 1
    return dict(sorted(counts.items()))


def evaluate_synthetic_track_b(table: pd.DataFrame, spectra: np.ndarray) -> dict[str, object]:
    groups = table["replicate_group"].to_numpy()
    n_splits = min(4, len(np.unique(groups)))

    label_features = label_matrix(table)
    planned_features = numeric_matrix(table, PLANNED_CONDITION_COLUMNS)
    observed_features = numeric_matrix(table, OBSERVED_TRAJECTORY_COLUMNS)
    full_event_features = numeric_matrix(table, FULL_EVENT_COLUMNS)
    spectra_features = PCA(n_components=12, random_state=17).fit_transform(spectra)

    prediction_results = {
        "label_only": cross_validated_spectrum_prediction(
            table, spectra, label_features, groups=groups, n_splits=n_splits
        ).__dict__,
        "planned_conditions": cross_validated_spectrum_prediction(
            table, spectra, planned_features, groups=groups, n_splits=n_splits
        ).__dict__,
        "observed_trajectory": cross_validated_spectrum_prediction(
            table, spectra, observed_features, groups=groups, n_splits=n_splits
        ).__dict__,
        "full_event": cross_validated_spectrum_prediction(
            table, spectra, full_event_features, groups=groups, n_splits=n_splits
        ).__dict__,
    }

    retrieval_results = {
        "label_only": nearest_neighbor_hit_rate(label_features, groups),
        "planned_conditions": nearest_neighbor_hit_rate(planned_features, groups),
        "observed_trajectory": nearest_neighbor_hit_rate(observed_features, groups),
        "full_event": nearest_neighbor_hit_rate(full_event_features, groups),
        "raw_measurement_pca": nearest_neighbor_hit_rate(spectra_features, groups),
    }

    return {
        "event_count": len(table),
        "replicate_group_count": len(np.unique(groups)),
        "prediction": prediction_results,
        "replicate_retrieval_hit_rate": retrieval_results,
        "label_projection_audit": label_projection_audit(table),
        "spectral_silhouette": silhouette_audit(table, spectra),
        "missingness": missingness_report(table),
    }
