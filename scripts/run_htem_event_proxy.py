"""Build an HTEM mini event table and test event-context prediction of XRD structure."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold, KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


HTEM_API_BASE_URL = "https://htem-api.nlr.gov/api"

PROCESS_NUMERIC_FIELDS = (
    "deposition_sample_time_min",
    "deposition_cycles",
    "deposition_base_pressure_mtorr",
    "deposition_initial_temp_c",
)
PROCESS_CATEGORICAL_FIELDS = (
    "deposition_compounds",
    "deposition_power",
    "deposition_gases",
    "deposition_gas_flow_sccm",
    "deposition_substrate_material",
)
POSITION_FIELDS = ("position", "x_mm", "y_mm")
PROVENANCE_NUMERIC_FIELDS = ("quality", "sample_date_year", "sciround")
PROVENANCE_CATEGORICAL_FIELDS = ("pdac", "person_id")
LOCAL_PROP_FIELDS = (
    "absolute_temp_c",
    "fpm_conductivity",
    "fpm_resistivity",
    "fpm_sheet_resistance",
    "fpm_standard_deviation",
    "opt_average_vis_trans",
    "opt_direct_bandgap",
    "thickness",
    "xrf_concentration",
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def api_url(path: str, query: dict[str, str] | None = None) -> str:
    url = f"{HTEM_API_BASE_URL}/{path.lstrip('/')}"
    if query:
        return f"{url}?{urllib.parse.urlencode(query)}"
    return url


def fetch_json(url: str, timeout: int = 240) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "materials-event-modeling/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def fetch_json_cached(url: str, cache_path: Path, force: bool) -> Any:
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text())

    payload = fetch_json(url)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    return payload


def stable_chunk_name(prefix: str, ids: list[int]) -> str:
    digest = hashlib.sha256(",".join(map(str, ids)).encode()).hexdigest()[:12]
    return f"{prefix}_{len(ids)}_{digest}.json"


def chunks(values: list[int], chunk_size: int) -> Iterable[list[int]]:
    for start in range(0, len(values), chunk_size):
        yield values[start : start + chunk_size]


def scalar_float(value: Any) -> float:
    if value is None:
        return math.nan
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return math.nan
    return math.nan


def summarize_numeric_like(value: Any) -> dict[str, float]:
    if isinstance(value, list):
        numbers = [scalar_float(item) for item in value]
        numbers = [item for item in numbers if not math.isnan(item)]
        if not numbers:
            return {"value": math.nan, "count": 0.0, "sum": 0.0, "max": math.nan}
        return {
            "value": float(np.mean(numbers)),
            "count": float(len(numbers)),
            "sum": float(np.sum(numbers)),
            "max": float(np.max(numbers)),
        }

    number = scalar_float(value)
    return {
        "value": number,
        "count": 0.0 if math.isnan(number) else 1.0,
        "sum": 0.0 if math.isnan(number) else number,
        "max": number,
    }


def signed_log1p(value: float) -> float:
    if math.isnan(value):
        return math.nan
    if not math.isfinite(value):
        return math.nan
    return math.copysign(math.log1p(abs(value)), value)


def categorical_text(value: Any) -> str:
    if value is None:
        return "__missing__"
    if isinstance(value, list):
        parts = ["__missing__" if item is None else str(item) for item in value]
        return "|".join(parts)
    return str(value)


def sample_date_year(value: Any) -> float:
    if not isinstance(value, str) or len(value) < 4:
        return math.nan
    try:
        return float(value[:4])
    except ValueError:
        return math.nan


def element_system(record: dict[str, Any]) -> str:
    return "|".join(record.get("elements") or []) or "none"


def parse_element_system_filter(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return "|".join(part.strip() for part in normalized.replace("|", ",").split(",") if part.strip())


def select_libraries(
    records: list[dict[str, Any]],
    max_libraries: int,
    min_xrd_positions: int,
    seed: int,
    element_system_filter: str | None,
) -> list[dict[str, Any]]:
    candidates = [
        record
        for record in records
        if isinstance(record.get("has_xrd"), (int, float))
        and int(record["has_xrd"]) >= min_xrd_positions
        and (element_system_filter is None or element_system(record) == element_system_filter)
    ]
    if not candidates:
        raise RuntimeError(
            "No HTEM libraries match "
            f"element_system={element_system_filter!r} and min_xrd_positions={min_xrd_positions}."
        )
    rng = np.random.default_rng(seed)
    indices = np.arange(len(candidates))
    rng.shuffle(indices)
    selected_indices = indices[: min(max_libraries, len(indices))]
    return [candidates[index] for index in selected_indices]


def fetch_records(cache_dir: Path, force: bool) -> list[dict[str, Any]]:
    url = api_url("sample_library/count")
    records = fetch_json_cached(url, cache_dir / "sample_library_records.json", force=force)
    if not isinstance(records, list):
        raise RuntimeError(f"Expected HTEM sample library list, got {type(records).__name__}")
    return records


def fetch_properties(ids: list[int], cache_dir: Path, chunk_size: int, force: bool) -> list[dict[str, Any]]:
    properties: list[dict[str, Any]] = []
    for chunk in chunks(ids, chunk_size):
        url = api_url("sample_library/prop", {"ids": ",".join(map(str, chunk))})
        path = cache_dir / stable_chunk_name("properties", chunk)
        payload = fetch_json_cached(url, path, force=force)
        if isinstance(payload, list):
            properties.extend(payload)
        print(f"loaded properties for {len(chunk)} libraries", file=sys.stderr)
    return properties


def fetch_spectra(ids: list[int], cache_dir: Path, chunk_size: int, force: bool) -> dict[str, list[Any]]:
    combined: dict[str, list[Any]] = defaultdict(list)
    for chunk in chunks(ids, chunk_size):
        url = api_url("sample_library/spectra", {"ids": ",".join(map(str, chunk))})
        path = cache_dir / stable_chunk_name("spectra", chunk)
        payload = fetch_json_cached(url, path, force=force)
        if isinstance(payload, dict):
            for key, values in payload.items():
                if isinstance(values, list):
                    combined[key].extend(values)
        print(f"loaded spectra for {len(chunk)} libraries", file=sys.stderr)
    return dict(combined)


def property_value(prop_entry: dict[str, Any], field: str, index: int) -> Any:
    values = prop_entry.get(field)
    if isinstance(values, list) and index < len(values):
        return values[index]
    return None


def sample_metadata(record: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "sample_library_id": int(record["id"]),
        "sample_library_id_text": str(record["id"]),
        "elements_text": categorical_text(record.get("elements")),
        "sample_date_year": sample_date_year(record.get("sample_date")),
    }
    for field in PROCESS_NUMERIC_FIELDS + PROVENANCE_NUMERIC_FIELDS:
        if field == "sample_date_year":
            continue
        row[field] = scalar_float(record.get(field))
    for field in PROCESS_CATEGORICAL_FIELDS + PROVENANCE_CATEGORICAL_FIELDS:
        row[f"{field}_text"] = categorical_text(record.get(field))
    return row


def add_element_columns(events: pd.DataFrame, records_by_id: dict[int, dict[str, Any]]) -> pd.DataFrame:
    elements = sorted(
        {
            element
            for record in records_by_id.values()
            for element in (record.get("elements") or [])
            if element is not None
        }
    )
    for element in elements:
        column = f"element_{element}"
        events[column] = [
            float(element in (records_by_id[int(sample_id)].get("elements") or []))
            for sample_id in events["sample_library_id"]
        ]
    return events


def spectra_by_position(entry: dict[str, Any]) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    positions = np.asarray(entry.get("position", []), dtype=np.int64)
    angles = np.asarray(entry.get("angle", []), dtype=np.float32)
    measurements = np.asarray(entry.get("measurement", []), dtype=np.float32)
    result = {}
    if not (positions.size == angles.size == measurements.size):
        return result

    for position in sorted(np.unique(positions)):
        mask = positions == position
        angle = angles[mask]
        measurement = measurements[mask]
        order = np.argsort(angle)
        result[int(position)] = (angle[order], measurement[order])
    return result


def normalize_spectrum(measurement: np.ndarray) -> np.ndarray:
    spectrum = np.nan_to_num(measurement.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    spectrum = np.log1p(np.maximum(spectrum, 0.0))
    scale = float(np.max(spectrum))
    if scale > 0:
        spectrum = spectrum / scale
    return spectrum.astype(np.float32)


def build_event_table(
    records: list[dict[str, Any]],
    properties: list[dict[str, Any]],
    spectra: dict[str, list[Any]],
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    records_by_id = {int(record["id"]): record for record in records}
    properties_by_id = {int(entry["sample_library_id"]): entry for entry in properties}
    xrd_by_id = {int(entry["sample_library_id"]): entry for entry in spectra.get("xrd", [])}

    rows: list[dict[str, Any]] = []
    xrd_rows: list[np.ndarray] = []
    reference_angle: np.ndarray | None = None

    for sample_id, xrd_entry in sorted(xrd_by_id.items()):
        record = records_by_id.get(sample_id)
        prop_entry = properties_by_id.get(sample_id)
        if record is None or prop_entry is None:
            continue

        prop_positions = prop_entry.get("position") or []
        prop_index_by_position = {
            int(position): index for index, position in enumerate(prop_positions) if position is not None
        }

        metadata = sample_metadata(record)
        for position, (angle, measurement) in spectra_by_position(xrd_entry).items():
            if position not in prop_index_by_position:
                continue

            if reference_angle is None:
                reference_angle = angle.astype(np.float32)
            elif angle.shape != reference_angle.shape or not np.allclose(angle, reference_angle):
                measurement = np.interp(reference_angle, angle, measurement).astype(np.float32)

            index = prop_index_by_position[position]
            row = dict(metadata)
            row["position"] = float(position)
            row["x_mm"] = scalar_float(property_value(prop_entry, "x_mm", index))
            row["y_mm"] = scalar_float(property_value(prop_entry, "y_mm", index))
            row["xrf_compounds_text"] = categorical_text(property_value(prop_entry, "xrf_compounds", index))

            for field in LOCAL_PROP_FIELDS:
                summary = summarize_numeric_like(property_value(prop_entry, field, index))
                row[f"{field}_value"] = signed_log1p(summary["value"])
                row[f"{field}_count"] = summary["count"]
                row[f"{field}_sum"] = signed_log1p(summary["sum"])
                row[f"{field}_max"] = signed_log1p(summary["max"])

            xrd_rows.append(normalize_spectrum(measurement))
            rows.append(row)

    if reference_angle is None or not rows:
        raise RuntimeError("No aligned HTEM event rows with XRD spectra were built.")

    events = pd.DataFrame(rows)
    events = add_element_columns(events, records_by_id)
    xrd = np.vstack(xrd_rows).astype(np.float32)
    return events, xrd, reference_angle


def split_definitions(events: pd.DataFrame, n_splits: int) -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
    indices = np.arange(len(events))
    random_cv = KFold(n_splits=n_splits, shuffle=True, random_state=17)
    splits: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {
        "random_position": list(random_cv.split(indices)),
    }

    library_groups = events["sample_library_id"].to_numpy()
    library_splits = min(n_splits, len(np.unique(library_groups)))
    if library_splits >= 2:
        splits["held_out_library"] = list(
            GroupKFold(n_splits=library_splits).split(indices, groups=library_groups)
        )

    pdac_groups = events["pdac_text"].to_numpy()
    pdac_splits = min(n_splits, len(np.unique(pdac_groups)))
    if pdac_splits >= 2:
        splits["held_out_pdac"] = list(
            GroupKFold(n_splits=pdac_splits).split(indices, groups=pdac_groups)
        )
    return splits


def feature_sets(events: pd.DataFrame) -> dict[str, dict[str, list[str]]]:
    def observed_numeric(columns: list[str]) -> list[str]:
        return [column for column in columns if column in events and events[column].notna().any()]

    element_columns = sorted(column for column in events.columns if column.startswith("element_"))
    process_numeric = observed_numeric(list(PROCESS_NUMERIC_FIELDS))
    process_categorical = [f"{field}_text" for field in PROCESS_CATEGORICAL_FIELDS]
    provenance_numeric = observed_numeric(list(PROVENANCE_NUMERIC_FIELDS))
    provenance_categorical = [f"{field}_text" for field in PROVENANCE_CATEGORICAL_FIELDS]
    position_numeric = observed_numeric(list(POSITION_FIELDS))
    local_numeric = observed_numeric([
        column
        for column in events.columns
        if any(column.startswith(f"{field}_") for field in LOCAL_PROP_FIELDS)
    ])

    recipe_numeric = element_columns + process_numeric
    recipe_categorical = ["elements_text"] + process_categorical
    local_categorical = ["xrf_compounds_text"]

    return {
        "recipe_only": {
            "numeric": recipe_numeric,
            "categorical": recipe_categorical,
        },
        "position_only": {
            "numeric": position_numeric,
            "categorical": [],
        },
        "recipe_plus_position": {
            "numeric": recipe_numeric + position_numeric,
            "categorical": recipe_categorical,
        },
        "local_measurements_no_xrd": {
            "numeric": recipe_numeric + position_numeric + local_numeric,
            "categorical": recipe_categorical + local_categorical,
        },
        "provenance_only": {
            "numeric": provenance_numeric,
            "categorical": provenance_categorical,
        },
        "sample_id_only": {
            "numeric": [],
            "categorical": ["sample_library_id_text"],
        },
        "sample_id_plus_position": {
            "numeric": position_numeric,
            "categorical": ["sample_library_id_text"],
        },
    }


def make_model(numeric: list[str], categorical: list[str], alpha: float) -> Pipeline:
    transformers = []
    if numeric:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            )
        )
    if categorical:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="constant", fill_value="__missing__")),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                categorical,
            )
        )
    if not transformers:
        raise ValueError("At least one numeric or categorical feature is required.")

    return Pipeline(
        [
            ("features", ColumnTransformer(transformers=transformers)),
            ("ridge", Ridge(alpha=alpha)),
        ]
    )


def metrics(truth: np.ndarray, prediction: np.ndarray, baseline_mse: float) -> dict[str, float]:
    diff = prediction - truth
    mse = float(np.mean(diff * diff))
    mae = float(np.mean(np.abs(diff)))
    return {
        "mse": mse,
        "mae": mae,
        "rmse": float(np.sqrt(mse)),
        "relative_mse_vs_train_mean": mse / baseline_mse if baseline_mse else math.nan,
        "mse_improvement_vs_train_mean": 1.0 - (mse / baseline_mse) if baseline_mse else math.nan,
    }


def summarize(values: list[float]) -> dict[str, float]:
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
    }


def evaluate(
    events: pd.DataFrame,
    xrd: np.ndarray,
    n_components: int,
    n_splits: int,
    alpha: float,
) -> dict[str, Any]:
    splits = split_definitions(events, n_splits=n_splits)
    configs = feature_sets(events)
    results: dict[str, dict[str, Any]] = {}

    for split_name, split_list in splits.items():
        split_trials: list[dict[str, Any]] = []
        model_trials: dict[str, list[dict[str, float]]] = defaultdict(list)
        explained_variances = []
        for fold, (train_idx, test_idx) in enumerate(split_list):
            target_components = min(n_components, len(train_idx) - 1, xrd.shape[1])
            pca = PCA(n_components=target_components, random_state=17)
            y_train = pca.fit_transform(xrd[train_idx])
            y_test = pca.transform(xrd[test_idx])
            explained_variances.append(float(np.sum(pca.explained_variance_ratio_)))

            train_mean = np.mean(y_train, axis=0, keepdims=True)
            baseline = np.repeat(train_mean, len(test_idx), axis=0)
            baseline_mse = float(np.mean((baseline - y_test) ** 2))
            baseline_metrics = metrics(y_test, baseline, baseline_mse=baseline_mse)
            model_trials["train_mean"].append(baseline_metrics)

            for name, config in configs.items():
                model = make_model(
                    numeric=config["numeric"],
                    categorical=config["categorical"],
                    alpha=alpha,
                )
                model.fit(events.iloc[train_idx], y_train)
                prediction = model.predict(events.iloc[test_idx])
                model_trials[name].append(metrics(y_test, prediction, baseline_mse=baseline_mse))

            split_trials.append(
                {
                    "fold": fold,
                    "train_events": int(len(train_idx)),
                    "test_events": int(len(test_idx)),
                    "target_components": int(target_components),
                    "target_explained_variance": explained_variances[-1],
                    "baseline_mse": baseline_mse,
                }
            )

        results[split_name] = {
            "folds": len(split_list),
            "target_explained_variance": summarize(explained_variances),
            "folds_detail": split_trials,
            "models": {
                model_name: {
                    metric_name: summarize([trial[metric_name] for trial in trials])
                    for metric_name in trials[0]
                }
                for model_name, trials in sorted(model_trials.items())
            },
        }

    return results


def pre_run_hypothesis(element_system_filter: str | None) -> str:
    if element_system_filter:
        return (
            f"Restricting to one HTEM element system ({element_system_filter}) should reduce broad "
            "chemistry/family shift. Random-position splits should still expose within-library "
            "shortcuts. If recipe/process features still fail held-out-library transfer inside "
            "the fixed element system, then the previous collapse was not mainly caused by broad "
            "element-family mixing."
        )
    return (
        "Position-level HTEM rows should expose event-shaped structure, but random "
        "position splits may overstate success because positions from the same sample "
        "library leak context. Held-out-library and held-out-PDAC splits are the real "
        "controls."
    )


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
    results = evaluate(
        events=events,
        xrd=xrd,
        n_components=args.target_pca_components,
        n_splits=args.n_splits,
        alpha=args.ridge_alpha,
    )

    result = {
        "dataset_id": "htem",
        "task": "event_proxy_xrd_pca_prediction",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pre_run_hypothesis": pre_run_hypothesis(element_system_filter),
        "api_base_url": HTEM_API_BASE_URL,
        "element_system_filter": element_system_filter,
        "selected_library_count": len(selected_ids),
        "selected_library_ids": selected_ids,
        "min_xrd_positions": args.min_xrd_positions,
        "event_count": int(len(events)),
        "xrd_points": int(xrd.shape[1]),
        "angle_min": float(np.min(angle)),
        "angle_max": float(np.max(angle)),
        "target": {
            "description": "PCA scores of normalized position-level XRD spectra.",
            "normalization": "log1p(nonnegative intensity), then per-spectrum max normalization.",
            "local_measurement_transform": "signed log1p for local non-XRD measurement values, sums, and maxima.",
            "target_pca_components": args.target_pca_components,
        },
        "feature_sets": {
            name: {
                "numeric": config["numeric"],
                "categorical": config["categorical"],
            }
            for name, config in feature_sets(events).items()
        },
        "results": results,
        "caveats": [
            "This is a public-data event-proxy run, not evidence that HTEM is a complete event log.",
            "Random position splits leak sample-library context and should be treated as a shortcut diagnostic.",
            "Local non-XRD measurements are post-fabrication measurements, not necessarily prospective inputs.",
            "XRD PCA prediction is an objective feedback task, not a phase-label benchmark.",
        ],
    }

    output_path = root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-libraries", type=int, default=32)
    parser.add_argument("--min-xrd-positions", type=int, default=40)
    parser.add_argument(
        "--element-system",
        default=None,
        help="Optional exact element system filter, for example `Cu,S,Sn` or `Cu|S|Sn`.",
    )
    parser.add_argument("--chunk-size", type=int, default=4)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--n-splits", type=int, default=4)
    parser.add_argument("--target-pca-components", type=int, default=8)
    parser.add_argument("--ridge-alpha", type=float, default=10.0)
    parser.add_argument("--force-fetch", action="store_true")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("data/interim/htem_event_proxy"),
        help="Ignored local cache for HTEM API responses.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/htem_event_proxy_xrd_prediction.json"),
    )
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
