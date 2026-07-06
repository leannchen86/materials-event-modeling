"""Field-prediction utilities for Track B event-style measurements."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class FieldBudgetResult:
    strategy: str
    observed_count: int
    model: str
    mse: float
    improvement_vs_global_mean: float
    improvement_vs_event_mean: float | None


def mean_squared_error(truth: np.ndarray, prediction: np.ndarray) -> float:
    diff = truth - prediction
    return float(np.mean(diff * diff))


def farthest_first_indices(coords: np.ndarray, count: int) -> np.ndarray:
    if count >= len(coords):
        return np.arange(len(coords), dtype=int)

    center = coords.mean(axis=0)
    first = int(np.argmin(np.sum((coords - center) ** 2, axis=1)))
    selected = [first]
    remaining = set(range(len(coords))) - {first}

    while len(selected) < count:
        best_idx = None
        best_distance = -np.inf
        selected_coords = coords[np.array(selected)]
        for idx in remaining:
            distance = float(np.min(np.sum((selected_coords - coords[idx]) ** 2, axis=1)))
            if distance > best_distance:
                best_distance = distance
                best_idx = idx
        assert best_idx is not None
        selected.append(best_idx)
        remaining.remove(best_idx)

    return np.array(selected, dtype=int)


def inverse_distance_prediction(
    observed_coords: np.ndarray,
    observed_spectra: np.ndarray,
    target_coords: np.ndarray,
    *,
    power: float = 2.0,
) -> np.ndarray:
    distances = np.linalg.norm(target_coords[:, None, :] - observed_coords[None, :, :], axis=2)
    weights = 1.0 / np.maximum(distances, 1e-6) ** power
    weights = weights / weights.sum(axis=1, keepdims=True)
    return weights @ observed_spectra


def coordinate_ridge_prediction(
    observed_coords: np.ndarray,
    observed_spectra: np.ndarray,
    target_coords: np.ndarray,
) -> np.ndarray | None:
    if len(observed_coords) < 3:
        return None
    coord_scaler = StandardScaler()
    scaled_observed = coord_scaler.fit_transform(observed_coords)
    scaled_target = coord_scaler.transform(target_coords)
    model = Ridge(alpha=1.0)
    model.fit(scaled_observed, observed_spectra)
    return model.predict(scaled_target)


def evaluate_partial_observation_budget(
    *,
    event_ids: np.ndarray,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed_counts: list[int],
    random_repeats: int = 8,
    seed: int = 17,
) -> list[FieldBudgetResult]:
    """Evaluate missing-measurement prediction from partial observations per event.

    The same event can contain many observations, such as time points, spatial positions,
    repeated droplets, or measurement modalities. For each budget, this hides unobserved
    measurements and predicts them from the observed subset of the same event.
    """

    rng = np.random.default_rng(seed)
    unique_events = np.array(sorted(set(event_ids.tolist())))
    rows: list[FieldBudgetResult] = []

    for observed_count in observed_counts:
        for strategy in ["random", "space_filling"]:
            repeats = random_repeats if strategy == "random" else 1
            error_sums: dict[str, list[float]] = {
                "global_mean": [],
                "event_mean": [],
                "nearest_neighbor": [],
                "idw_all": [],
                "coordinate_ridge": [],
            }

            for _ in range(repeats):
                selected_by_event: dict[str, np.ndarray] = {}
                observed_global_spectra = []

                for event_id in unique_events:
                    event_idx = np.flatnonzero(event_ids == event_id)
                    event_coords = coords[event_idx]
                    if observed_count >= len(event_idx):
                        selected_local = np.arange(len(event_idx), dtype=int)
                    elif strategy == "random":
                        selected_local = rng.choice(
                            len(event_idx), size=observed_count, replace=False
                        )
                    else:
                        selected_local = farthest_first_indices(event_coords, observed_count)
                    selected = event_idx[selected_local]
                    selected_by_event[str(event_id)] = selected
                    observed_global_spectra.append(spectra[selected])

                global_mean = np.vstack(observed_global_spectra).mean(axis=0)

                for event_id in unique_events:
                    event_idx = np.flatnonzero(event_ids == event_id)
                    observed_idx = selected_by_event[str(event_id)]
                    heldout_idx = np.setdiff1d(event_idx, observed_idx, assume_unique=False)
                    if len(heldout_idx) == 0:
                        continue

                    observed_coords = coords[observed_idx]
                    observed_spectra = spectra[observed_idx]
                    target_coords = coords[heldout_idx]
                    target_spectra = spectra[heldout_idx]

                    global_prediction = np.tile(global_mean, (len(heldout_idx), 1))
                    event_mean = observed_spectra.mean(axis=0)
                    event_prediction = np.tile(event_mean, (len(heldout_idx), 1))

                    nearest_distances = np.linalg.norm(
                        target_coords[:, None, :] - observed_coords[None, :, :],
                        axis=2,
                    )
                    nearest_prediction = observed_spectra[np.argmin(nearest_distances, axis=1)]
                    idw_prediction = inverse_distance_prediction(
                        observed_coords, observed_spectra, target_coords
                    )
                    ridge_prediction = coordinate_ridge_prediction(
                        observed_coords, observed_spectra, target_coords
                    )

                    error_sums["global_mean"].append(
                        mean_squared_error(target_spectra, global_prediction)
                    )
                    event_mse = mean_squared_error(target_spectra, event_prediction)
                    error_sums["event_mean"].append(event_mse)
                    error_sums["nearest_neighbor"].append(
                        mean_squared_error(target_spectra, nearest_prediction)
                    )
                    error_sums["idw_all"].append(
                        mean_squared_error(target_spectra, idw_prediction)
                    )
                    if ridge_prediction is not None:
                        error_sums["coordinate_ridge"].append(
                            mean_squared_error(target_spectra, ridge_prediction)
                        )

            global_mse = float(np.mean(error_sums["global_mean"]))
            event_mean_mse = float(np.mean(error_sums["event_mean"]))
            for model_name, errors in error_sums.items():
                if not errors:
                    continue
                mse = float(np.mean(errors))
                if model_name == "event_mean":
                    improvement_vs_event_mean = 0.0
                else:
                    improvement_vs_event_mean = 1.0 - (mse / event_mean_mse)
                rows.append(
                    FieldBudgetResult(
                        strategy=strategy,
                        observed_count=observed_count,
                        model=model_name,
                        mse=mse,
                        improvement_vs_global_mean=1.0 - (mse / global_mse),
                        improvement_vs_event_mean=improvement_vs_event_mean,
                    )
                )

    return rows

