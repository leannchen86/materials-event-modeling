"""Predict held-out HTEM XRD positions from within-library spatial neighbors."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from run_htem_event_proxy import (
    HTEM_API_BASE_URL,
    LOCAL_PROP_FIELDS,
    build_event_table,
    fetch_properties,
    fetch_records,
    fetch_spectra,
    parse_element_system_filter,
    select_libraries,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


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
            "mse": mse,
            "mae": self.absolute_error_sum / self.count,
            "rmse": float(np.sqrt(mse)),
        }


@dataclass
class RepeatResult:
    repeat: int
    split_kind: str
    train_events: int = 0
    test_events: int = 0
    libraries: int = 0
    models: dict[str, ErrorAccumulator] = field(default_factory=lambda: defaultdict(ErrorAccumulator))

    def update(self, model_name: str, truth: np.ndarray, prediction: np.ndarray) -> None:
        self.models[model_name].update(truth, prediction)

    def metrics(self) -> dict[str, Any]:
        results = {name: accumulator.metrics() for name, accumulator in sorted(self.models.items())}
        global_mse = results["global_mean"]["mse"]
        library_mse = results["library_mean"]["mse"]
        for values in results.values():
            values["relative_mse_vs_global_mean"] = values["mse"] / global_mse
            values["mse_improvement_vs_global_mean"] = 1.0 - values["relative_mse_vs_global_mean"]
            values["relative_mse_vs_library_mean"] = values["mse"] / library_mse
            values["mse_improvement_vs_library_mean"] = 1.0 - values["relative_mse_vs_library_mean"]
        return {
            "repeat": self.repeat,
            "split_kind": self.split_kind,
            "libraries": self.libraries,
            "train_events": self.train_events,
            "test_events": self.test_events,
            "models": results,
        }


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def coordinate_matrix(events: pd.DataFrame, indices: np.ndarray) -> np.ndarray:
    return events.loc[indices, ["x_mm", "y_mm"]].to_numpy(dtype=np.float32)


def polynomial_features(
    train_coords: np.ndarray,
    target_coords: np.ndarray,
    degree: int,
) -> tuple[np.ndarray, np.ndarray]:
    center = train_coords.mean(axis=0, keepdims=True)
    scale = train_coords.std(axis=0, keepdims=True)
    scale = np.maximum(scale, 1e-6)
    train = (train_coords - center) / scale
    target = (target_coords - center) / scale
    if degree == 1:
        return train, target
    if degree == 2:
        train_features = np.column_stack(
            [train[:, 0], train[:, 1], train[:, 0] ** 2, train[:, 1] ** 2, train[:, 0] * train[:, 1]]
        )
        target_features = np.column_stack(
            [
                target[:, 0],
                target[:, 1],
                target[:, 0] ** 2,
                target[:, 1] ** 2,
                target[:, 0] * target[:, 1],
            ]
        )
        return train_features, target_features
    raise ValueError(f"Unsupported degree: {degree}")


def nearest_prediction(
    train_xrd: np.ndarray,
    train_coords: np.ndarray,
    target_coords: np.ndarray,
) -> np.ndarray:
    distances = np.linalg.norm(target_coords[:, None, :] - train_coords[None, :, :], axis=2)
    nearest = np.argmin(distances, axis=1)
    return train_xrd[nearest]


def idw_prediction(
    train_xrd: np.ndarray,
    train_coords: np.ndarray,
    target_coords: np.ndarray,
    *,
    k: int | None,
    power: float,
) -> np.ndarray:
    distances = np.linalg.norm(target_coords[:, None, :] - train_coords[None, :, :], axis=2)
    if k is not None and k < distances.shape[1]:
        selected = np.argpartition(distances, kth=k - 1, axis=1)[:, :k]
        selected_distances = np.take_along_axis(distances, selected, axis=1)
        selected_xrd = train_xrd[selected]
    else:
        selected_distances = distances
        selected_xrd = np.repeat(train_xrd[None, :, :], repeats=target_coords.shape[0], axis=0)

    weights = 1.0 / np.maximum(selected_distances, 1e-6) ** power
    weights = weights / np.sum(weights, axis=1, keepdims=True)
    return np.sum(selected_xrd * weights[:, :, None], axis=1)


def ridge_prediction(
    train_xrd: np.ndarray,
    train_coords: np.ndarray,
    target_coords: np.ndarray,
    *,
    degree: int,
    alpha: float,
) -> np.ndarray:
    train_features, target_features = polynomial_features(train_coords, target_coords, degree=degree)
    model = Ridge(alpha=alpha)
    model.fit(train_features, train_xrd)
    return model.predict(target_features).astype(np.float32)


def local_feature_columns(events: pd.DataFrame) -> list[str]:
    columns = [
        column
        for column in events.columns
        if any(column.startswith(f"{field}_") for field in LOCAL_PROP_FIELDS)
    ]
    return sorted(column for column in columns if events[column].notna().any())


def feature_matrix(events: pd.DataFrame, indices: np.ndarray, columns: list[str]) -> np.ndarray:
    if not columns:
        raise ValueError("At least one feature column is required.")
    return events.loc[indices, columns].to_numpy(dtype=np.float32)


def numeric_ridge_prediction(
    train_features: np.ndarray,
    target_features: np.ndarray,
    train_target: np.ndarray,
    *,
    alpha: float,
) -> np.ndarray:
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=alpha)),
        ]
    )
    model.fit(train_features, train_target)
    return model.predict(target_features).astype(np.float32)


def leave_one_out_idw_prediction(
    train_xrd: np.ndarray,
    train_coords: np.ndarray,
    *,
    power: float,
) -> np.ndarray:
    distances = np.linalg.norm(train_coords[:, None, :] - train_coords[None, :, :], axis=2)
    np.fill_diagonal(distances, np.inf)
    weights = 1.0 / np.maximum(distances, 1e-6) ** power
    weights[~np.isfinite(weights)] = 0.0
    weights_sum = np.sum(weights, axis=1, keepdims=True)
    weights = weights / np.maximum(weights_sum, 1e-12)
    return weights @ train_xrd


def random_position_split(
    group_indices: np.ndarray,
    rng: np.random.Generator,
    test_fraction: float,
    min_test_positions: int,
    min_train_positions: int,
) -> tuple[np.ndarray, np.ndarray] | None:
    n_positions = group_indices.size
    test_count = max(min_test_positions, int(round(n_positions * test_fraction)))
    test_count = min(test_count, n_positions - min_train_positions)
    if test_count < min_test_positions:
        return None
    shuffled = group_indices.copy()
    rng.shuffle(shuffled)
    test_idx = np.sort(shuffled[:test_count])
    train_idx = np.sort(shuffled[test_count:])
    return train_idx, test_idx


def row_holdout_split(
    events: pd.DataFrame,
    group_indices: np.ndarray,
    rng: np.random.Generator,
    min_test_positions: int,
    min_train_positions: int,
) -> tuple[np.ndarray, np.ndarray] | None:
    y_values = events.loc[group_indices, "y_mm"].round(6)
    unique_rows = np.array(sorted(y_values.dropna().unique()))
    if unique_rows.size < 2:
        return None

    candidate_rows = unique_rows.copy()
    rng.shuffle(candidate_rows)
    for y_value in candidate_rows:
        test_mask = y_values.to_numpy() == y_value
        test_idx = group_indices[test_mask]
        train_idx = group_indices[~test_mask]
        if test_idx.size >= min_test_positions and train_idx.size >= min_train_positions:
            return np.sort(train_idx), np.sort(test_idx)
    return None


def build_splits(
    events: pd.DataFrame,
    *,
    split_kind: str,
    repeat: int,
    seed: int,
    test_fraction: float,
    min_test_positions: int,
    min_train_positions: int,
) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    rng = np.random.default_rng(seed + repeat * 9973 + (0 if split_kind == "random_positions" else 1))
    splits = {}
    for sample_id, group in events.groupby("sample_library_id", sort=True):
        group_indices = group.index.to_numpy(dtype=np.int64)
        if split_kind == "random_positions":
            split = random_position_split(
                group_indices=group_indices,
                rng=rng,
                test_fraction=test_fraction,
                min_test_positions=min_test_positions,
                min_train_positions=min_train_positions,
            )
        elif split_kind == "held_out_row":
            split = row_holdout_split(
                events=events,
                group_indices=group_indices,
                rng=rng,
                min_test_positions=min_test_positions,
                min_train_positions=min_train_positions,
            )
        else:
            raise ValueError(f"Unsupported split kind: {split_kind}")

        if split is not None:
            splits[int(sample_id)] = split
    return splits


def evaluate_split(
    events: pd.DataFrame,
    xrd: np.ndarray,
    *,
    split_kind: str,
    repeat: int,
    seed: int,
    test_fraction: float,
    min_test_positions: int,
    min_train_positions: int,
    idw_power: float,
    ridge_alpha: float,
    local_ridge_alpha: float,
) -> dict[str, Any]:
    splits = build_splits(
        events,
        split_kind=split_kind,
        repeat=repeat,
        seed=seed,
        test_fraction=test_fraction,
        min_test_positions=min_test_positions,
        min_train_positions=min_train_positions,
    )
    train_indices = np.concatenate([train_idx for train_idx, _ in splits.values()])
    global_mean = np.mean(xrd[train_indices], axis=0)
    local_columns = local_feature_columns(events)

    result = RepeatResult(repeat=repeat, split_kind=split_kind, libraries=len(splits))
    for _sample_id, (train_idx, test_idx) in sorted(splits.items()):
        train_xrd = xrd[train_idx]
        test_xrd = xrd[test_idx]
        train_coords = coordinate_matrix(events, train_idx)
        test_coords = coordinate_matrix(events, test_idx)

        library_mean = np.mean(train_xrd, axis=0)
        idw_all = idw_prediction(
            train_xrd,
            train_coords,
            test_coords,
            k=None,
            power=idw_power,
        )
        local_train = feature_matrix(events, train_idx, local_columns)
        local_test = feature_matrix(events, test_idx, local_columns)
        xy_local_train = np.column_stack([train_coords, local_train])
        xy_local_test = np.column_stack([test_coords, local_test])
        train_idw_loo = leave_one_out_idw_prediction(
            train_xrd,
            train_coords,
            power=idw_power,
        )
        local_residual = numeric_ridge_prediction(
            local_train,
            local_test,
            train_xrd - train_idw_loo,
            alpha=local_ridge_alpha,
        )
        predictions = {
            "global_mean": np.repeat(global_mean[None, :], repeats=test_idx.size, axis=0),
            "library_mean": np.repeat(library_mean[None, :], repeats=test_idx.size, axis=0),
            "nearest_neighbor": nearest_prediction(train_xrd, train_coords, test_coords),
            "idw_3": idw_prediction(
                train_xrd,
                train_coords,
                test_coords,
                k=min(3, train_idx.size),
                power=idw_power,
            ),
            "idw_all": idw_all,
            "xy_ridge_linear": ridge_prediction(
                train_xrd,
                train_coords,
                test_coords,
                degree=1,
                alpha=ridge_alpha,
            ),
            "xy_ridge_quadratic": ridge_prediction(
                train_xrd,
                train_coords,
                test_coords,
                degree=2,
                alpha=ridge_alpha,
            ),
            "local_ridge_direct": numeric_ridge_prediction(
                local_train,
                local_test,
                train_xrd,
                alpha=local_ridge_alpha,
            ),
            "xy_local_ridge_direct": numeric_ridge_prediction(
                xy_local_train,
                xy_local_test,
                train_xrd,
                alpha=local_ridge_alpha,
            ),
            "idw_all_plus_local_residual": idw_all + local_residual,
        }
        for name, prediction in predictions.items():
            result.update(name, test_xrd, prediction)
        result.train_events += int(train_idx.size)
        result.test_events += int(test_idx.size)

    return result.metrics()


def summarize(values: list[float]) -> dict[str, float]:
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
    }


def summarize_trials(trials: list[dict[str, Any]]) -> dict[str, Any]:
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trial in trials:
        by_split[trial["split_kind"]].append(trial)

    summary = {}
    for split_kind, split_trials in sorted(by_split.items()):
        model_names = sorted(split_trials[0]["models"])
        summary[split_kind] = {
            "repeats": len(split_trials),
            "libraries": summarize([trial["libraries"] for trial in split_trials]),
            "train_events": summarize([trial["train_events"] for trial in split_trials]),
            "test_events": summarize([trial["test_events"] for trial in split_trials]),
            "models": {
                model_name: {
                    metric_name: summarize(
                        [trial["models"][model_name][metric_name] for trial in split_trials]
                    )
                    for metric_name in split_trials[0]["models"][model_name]
                }
                for model_name in model_names
            },
        }
    return summary


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root()
    cache_dir = root / args.cache_dir
    records = fetch_records(cache_dir=cache_dir, force=args.force_fetch)
    element_system_filter = parse_element_system_filter(args.element_system)
    selected_records = select_libraries(
        records=records,
        max_libraries=args.max_libraries,
        min_xrd_positions=args.min_xrd_positions,
        seed=args.seed,
        element_system_filter=element_system_filter,
    )
    selected_ids = [int(record["id"]) for record in selected_records]
    print(f"selected {len(selected_ids)} HTEM libraries", file=sys.stderr)

    properties = fetch_properties(
        ids=selected_ids,
        cache_dir=cache_dir,
        chunk_size=args.chunk_size,
        force=args.force_fetch,
    )
    spectra = fetch_spectra(
        ids=selected_ids,
        cache_dir=cache_dir,
        chunk_size=args.chunk_size,
        force=args.force_fetch,
    )
    events, xrd, angle = build_event_table(selected_records, properties, spectra)

    trials = []
    for split_kind in args.split_kinds:
        for repeat in range(args.repeats):
            print(f"evaluating split={split_kind} repeat={repeat}", file=sys.stderr)
            trials.append(
                evaluate_split(
                    events=events,
                    xrd=xrd,
                    split_kind=split_kind,
                    repeat=repeat,
                    seed=args.seed,
                    test_fraction=args.test_fraction,
                    min_test_positions=args.min_test_positions,
                    min_train_positions=args.min_train_positions,
                    idw_power=args.idw_power,
                    ridge_alpha=args.ridge_alpha,
                    local_ridge_alpha=args.local_ridge_alpha,
                )
            )

    result = {
        "dataset_id": "htem",
        "task": "within_library_spatial_field_xrd_prediction",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pre_run_hypothesis": (
            "If HTEM's useful event structure is inside each sample library rather than "
            "across libraries, then within-library spatial predictors should beat a flat "
            "library-mean baseline. Nearest-neighbor or distance-weighted interpolation "
            "should be strong on random held-out positions; row holdout should be harder "
            "and tests whether the field model extrapolates across the spatial grid."
            " Local non-XRD features are tested both as direct predictors and as residual "
            "corrections over the strongest spatial smoother."
        ),
        "api_base_url": HTEM_API_BASE_URL,
        "element_system_filter": element_system_filter,
        "selected_library_count": len(selected_ids),
        "selected_library_ids": selected_ids,
        "event_count": len(events),
        "xrd_points": int(xrd.shape[1]),
        "angle_min": float(np.min(angle)),
        "angle_max": float(np.max(angle)),
        "normalization": "log1p(nonnegative intensity), then per-spectrum max normalization.",
        "split_kinds": args.split_kinds,
        "repeats": args.repeats,
        "test_fraction": args.test_fraction,
        "min_test_positions": args.min_test_positions,
        "min_train_positions": args.min_train_positions,
        "idw_power": args.idw_power,
        "ridge_alpha": args.ridge_alpha,
        "local_ridge_alpha": args.local_ridge_alpha,
        "local_feature_columns": local_feature_columns(events),
        "summary": summarize_trials(trials),
        "trials": trials,
        "caveats": [
            "This is within-library spatial prediction, not transfer to unseen material-making events.",
            "Neighbor baselines use XRD measurements from other positions in the same sample library.",
            "Strong random-position performance can reflect smooth spatial interpolation, not broad discovery.",
            "Held-out-row splits are a harder spatial extrapolation control.",
            "Local non-XRD measurements are post-fabrication observations, not prospective synthesis inputs.",
            "Residual models are only useful if they improve over idw_all, not merely over global or library means.",
        ],
    }

    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--element-system", default="Cu,S,Sn")
    parser.add_argument("--max-libraries", type=int, default=65)
    parser.add_argument("--min-xrd-positions", type=int, default=40)
    parser.add_argument("--chunk-size", type=int, default=5)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument(
        "--split-kinds",
        nargs="+",
        default=["random_positions", "held_out_row"],
        choices=["random_positions", "held_out_row"],
    )
    parser.add_argument("--test-fraction", type=float, default=0.25)
    parser.add_argument("--min-test-positions", type=int, default=8)
    parser.add_argument("--min-train-positions", type=int, default=16)
    parser.add_argument("--idw-power", type=float, default=2.0)
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    parser.add_argument("--local-ridge-alpha", type=float, default=100000.0)
    parser.add_argument("--force-fetch", action="store_true")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("data/interim/htem_event_proxy"),
        help="Local cache for HTEM API responses.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/htem_spatial_field_prediction_cu_s_sn.json"),
    )
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
