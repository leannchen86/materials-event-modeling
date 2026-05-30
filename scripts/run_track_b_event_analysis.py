"""Run the Track B event-analysis harness on event records plus raw spectra.

The script is intentionally conservative. It treats labels as probes and evaluates raw
measurement prediction, retrieval, missingness, provenance leakage, and split sensitivity.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score, silhouette_score
from sklearn.model_selection import GroupKFold, KFold, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from materials_event_modeling.track_b.eval import (
    FULL_EVENT_COLUMNS,
    OBSERVED_TRAJECTORY_COLUMNS,
    PLANNED_CONDITION_COLUMNS,
    label_projection_audit,
    mean_squared_error,
    nearest_neighbor_hit_rate,
)


FEATURE_VIEWS = {
    "label_only": {"numeric": [], "categorical": ["legacy_label"]},
    "planned_conditions": {"numeric": PLANNED_CONDITION_COLUMNS, "categorical": []},
    "observed_trajectory": {"numeric": OBSERVED_TRAJECTORY_COLUMNS, "categorical": []},
    "full_event": {"numeric": FULL_EVENT_COLUMNS, "categorical": []},
    "provenance_only": {"numeric": [], "categorical": ["batch_id", "operator_id", "reagent_lot"]},
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def first_label(event: dict[str, Any]) -> str | None:
    human_labels = event.get("labels", {}).get("human_labels", [])
    if not human_labels:
        return None
    return human_labels[0].get("label")


def flatten_events(events: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for event in events:
        process = event.get("process", {})
        planned = process.get("planned_conditions", {})
        observed = process.get("observed_trajectory", {})
        data_quality = event.get("data_quality", {})
        precursors = process.get("precursors", [])
        reagent_lot = None
        if precursors:
            reagent_lot = precursors[0].get("lot_id")
        rows.append(
            {
                "event_id": event.get("event_id"),
                "system": event.get("system"),
                "batch_id": event.get("batch_id"),
                "replicate_group": event.get("pre_registered_plan_id"),
                "operator_id": event.get("operator_id"),
                "reagent_lot": reagent_lot,
                "legacy_label": first_label(event),
                "planned_temperature_c": planned.get("target_temperature_c"),
                "planned_aging_time_minutes": planned.get("target_aging_time_minutes"),
                "planned_mixing_intensity": planned.get("target_mixing_intensity"),
                "planned_additive_level": planned.get("target_additive_level"),
                "observed_temperature_c": observed.get("temperature_c"),
                "observed_aging_time_minutes": observed.get("aging_time_minutes"),
                "observed_mixing_intensity": observed.get("mixing_intensity"),
                "observed_additive_level": observed.get("additive_level"),
                "initial_ph": observed.get("initial_ph"),
                "final_ph": observed.get("final_ph"),
                "early_turbidity": observed.get("early_turbidity"),
                "include_in_raw_objective": data_quality.get("include_in_raw_objective", True),
                "missing_fields": ";".join(data_quality.get("missing_fields", [])),
            }
        )
    return pd.DataFrame(rows)


def load_bundle(path: Path) -> tuple[list[dict[str, Any]], pd.DataFrame, np.ndarray, np.ndarray | None]:
    bundle = read_json(path)
    events = bundle.get("events", [])
    table = pd.DataFrame(bundle["event_table"]) if "event_table" in bundle else flatten_events(events)
    spectra = np.asarray(bundle["spectra"], dtype=np.float32)
    theta = np.asarray(bundle["theta"], dtype=np.float32) if "theta" in bundle else None
    if len(table) != len(spectra):
        raise ValueError(f"table rows ({len(table)}) and spectra rows ({len(spectra)}) differ")
    return events, table, spectra, theta


def schema_audit(events: list[dict[str, Any]]) -> dict[str, Any]:
    required = {"event_id", "system", "created_at", "process", "measurements", "labels", "data_quality"}
    missing_required = Counter()
    labels_before_raw = 0
    xrd_files = 0
    for event in events:
        for field in required:
            if field not in event:
                missing_required[field] += 1
        if not event.get("labels", {}).get("assigned_after_raw_data_frozen", False):
            labels_before_raw += 1
        xrd_files += len(event.get("measurements", {}).get("xrd", []))
    return {
        "event_count": len(events),
        "missing_required_counts": dict(sorted(missing_required.items())),
        "labels_not_marked_after_raw_freeze": labels_before_raw,
        "xrd_file_reference_count": xrd_files,
    }


def missingness_audit(table: pd.DataFrame) -> dict[str, Any]:
    important = [
        "event_id",
        "batch_id",
        "replicate_group",
        "operator_id",
        "reagent_lot",
        "legacy_label",
        *FULL_EVENT_COLUMNS,
    ]
    missing_by_column = {
        column: int(table[column].isna().sum())
        for column in important
        if column in table.columns and int(table[column].isna().sum()) > 0
    }
    explicit_missing = Counter()
    if "missing_fields" in table:
        for value in table["missing_fields"].fillna(""):
            for field in str(value).split(";"):
                if field:
                    explicit_missing[field] += 1
    return {
        "missing_by_column": missing_by_column,
        "explicit_missing_fields": dict(sorted(explicit_missing.items())),
    }


def available_columns(table: pd.DataFrame, columns: list[str]) -> list[str]:
    return [column for column in columns if column in table.columns]


def build_preprocessor(numeric_columns: list[str], categorical_columns: list[str]) -> ColumnTransformer:
    transformers = []
    if numeric_columns:
        transformers.append(
            (
                "num",
                make_pipeline(SimpleImputer(strategy="median"), StandardScaler()),
                numeric_columns,
            )
        )
    if categorical_columns:
        transformers.append(
            (
                "cat",
                make_pipeline(
                    SimpleImputer(strategy="constant", fill_value="missing"),
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                ),
                categorical_columns,
            )
        )
    return ColumnTransformer(transformers)


def split_indices(
    table: pd.DataFrame,
    *,
    split_name: str,
    group_column: str | None,
    n_splits: int,
    seed: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    if group_column is None:
        splitter = KFold(n_splits=min(n_splits, len(table)), shuffle=True, random_state=seed)
        return list(splitter.split(table))

    groups = table[group_column].fillna("missing").astype(str).to_numpy()
    unique_groups = np.unique(groups)
    if len(unique_groups) < 2:
        return []
    splitter = GroupKFold(n_splits=min(n_splits, len(unique_groups)))
    return list(splitter.split(table, groups=groups))


def spectrum_prediction_for_view(
    table: pd.DataFrame,
    spectra: np.ndarray,
    *,
    numeric_columns: list[str],
    categorical_columns: list[str],
    splits: list[tuple[np.ndarray, np.ndarray]],
) -> dict[str, float] | None:
    numeric_columns = available_columns(table, numeric_columns)
    categorical_columns = available_columns(table, categorical_columns)
    if not numeric_columns and not categorical_columns:
        return None

    train_mean_errors = []
    model_errors = []
    used_table = table[numeric_columns + categorical_columns].copy()
    for train_idx, test_idx in splits:
        train_mean = spectra[train_idx].mean(axis=0)
        model = make_pipeline(
            build_preprocessor(numeric_columns, categorical_columns),
            Ridge(alpha=10.0),
        )
        model.fit(used_table.iloc[train_idx], spectra[train_idx])
        prediction = model.predict(used_table.iloc[test_idx])
        train_mean_prediction = np.tile(train_mean, (len(test_idx), 1))
        train_mean_errors.append(mean_squared_error(spectra[test_idx], train_mean_prediction))
        model_errors.append(mean_squared_error(spectra[test_idx], prediction))

    train_mean_mse = float(np.mean(train_mean_errors))
    model_mse = float(np.mean(model_errors))
    return {
        "mse": model_mse,
        "train_mean_mse": train_mean_mse,
        "mse_improvement_vs_train_mean": 1.0 - (model_mse / train_mean_mse),
    }


def prediction_audit(table: pd.DataFrame, spectra: np.ndarray, *, seed: int) -> dict[str, Any]:
    split_specs = {
        "random_event": None,
        "heldout_plan": "replicate_group",
        "heldout_batch": "batch_id",
    }
    results: dict[str, Any] = {}
    for split_name, group_column in split_specs.items():
        splits = split_indices(
            table,
            split_name=split_name,
            group_column=group_column,
            n_splits=4,
            seed=seed,
        )
        if not splits:
            results[split_name] = {"skipped": f"not enough groups for {group_column}"}
            continue
        split_results = {}
        for view, columns in FEATURE_VIEWS.items():
            result = spectrum_prediction_for_view(
                table,
                spectra,
                numeric_columns=columns["numeric"],
                categorical_columns=columns["categorical"],
                splits=splits,
            )
            if result is not None:
                split_results[view] = result
        results[split_name] = {
            "fold_count": len(splits),
            "group_column": group_column,
            "feature_views": split_results,
        }
    return results


def transformed_feature_matrix(
    table: pd.DataFrame,
    *,
    numeric_columns: list[str],
    categorical_columns: list[str],
) -> np.ndarray | None:
    numeric_columns = available_columns(table, numeric_columns)
    categorical_columns = available_columns(table, categorical_columns)
    if not numeric_columns and not categorical_columns:
        return None
    used_table = table[numeric_columns + categorical_columns].copy()
    transformer = build_preprocessor(numeric_columns, categorical_columns)
    return np.asarray(transformer.fit_transform(used_table), dtype=np.float32)


def retrieval_audit(table: pd.DataFrame, spectra: np.ndarray) -> dict[str, float]:
    if "replicate_group" not in table:
        return {}
    groups = table["replicate_group"].fillna("missing").astype(str).to_numpy()
    if len(np.unique(groups)) == len(groups):
        return {"note": "all replicate groups are unique; retrieval is not meaningful"}  # type: ignore[return-value]

    results: dict[str, float] = {}
    for view, columns in FEATURE_VIEWS.items():
        matrix = transformed_feature_matrix(
            table,
            numeric_columns=columns["numeric"],
            categorical_columns=columns["categorical"],
        )
        if matrix is not None:
            results[view] = nearest_neighbor_hit_rate(matrix, groups)
    components = min(12, spectra.shape[0] - 1, spectra.shape[1])
    if components >= 2:
        results["raw_measurement_pca"] = nearest_neighbor_hit_rate(
            PCA(n_components=components, random_state=17).fit_transform(spectra),
            groups,
        )
    return results


def label_audit(table: pd.DataFrame, spectra: np.ndarray) -> dict[str, Any]:
    labels = table["legacy_label"].fillna("missing").astype(str)
    label_counts = dict(sorted(Counter(labels).items()))
    result: dict[str, Any] = {
        "label_counts": label_counts,
    }

    if "replicate_group" in table:
        mixed_groups = 0
        group_count = 0
        for _, group_df in table.groupby(table["replicate_group"].fillna("missing")):
            group_count += 1
            if group_df["legacy_label"].fillna("missing").nunique() > 1:
                mixed_groups += 1
        result["replicate_groups_with_multiple_labels"] = mixed_groups
        result["replicate_label_mixture_rate"] = mixed_groups / max(group_count, 1)

    components = min(8, spectra.shape[0] - 1, spectra.shape[1])
    if components >= 2 and labels.nunique() > 1 and labels.nunique() < len(labels):
        projected = PCA(n_components=components, random_state=17).fit_transform(spectra)
        result["raw_pca_label_silhouette"] = float(silhouette_score(projected, labels))

    if "hidden_regime" in table.columns:
        result["synthetic_hidden_regime_projection"] = label_projection_audit(table)

    return result


def target_predictability(
    features: np.ndarray,
    target: np.ndarray,
    *,
    seed: int,
) -> dict[str, Any] | None:
    target = np.asarray(target).astype(str)
    counts = Counter(target)
    if len(counts) < 2:
        return None
    min_count = min(counts.values())
    if min_count < 2:
        return None
    splits = min(4, min_count)
    cv = StratifiedKFold(n_splits=splits, shuffle=True, random_state=seed)
    accuracies = []
    balanced = []
    for train_idx, test_idx in cv.split(features, target):
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, class_weight="balanced"),
        )
        model.fit(features[train_idx], target[train_idx])
        prediction = model.predict(features[test_idx])
        accuracies.append(float(np.mean(prediction == target[test_idx])))
        balanced.append(float(balanced_accuracy_score(target[test_idx], prediction)))
    majority = max(counts.values()) / len(target)
    return {
        "class_count": len(counts),
        "fold_count": splits,
        "majority_baseline_accuracy": majority,
        "accuracy": float(np.mean(accuracies)),
        "balanced_accuracy": float(np.mean(balanced)),
    }


def provenance_audit(table: pd.DataFrame, spectra: np.ndarray, *, seed: int) -> dict[str, Any]:
    components = min(12, spectra.shape[0] - 1, spectra.shape[1])
    if components < 2:
        return {}
    spectral_features = PCA(n_components=components, random_state=17).fit_transform(spectra)
    full_features = transformed_feature_matrix(
        table,
        numeric_columns=FULL_EVENT_COLUMNS,
        categorical_columns=["legacy_label"],
    )
    results: dict[str, Any] = {}
    for target_column in ["batch_id", "operator_id", "reagent_lot"]:
        if target_column not in table:
            continue
        target = table[target_column].fillna("missing").astype(str).to_numpy()
        target_results = {
            "from_raw_pca": target_predictability(spectral_features, target, seed=seed),
        }
        if full_features is not None:
            target_results["from_event_features"] = target_predictability(
                full_features, target, seed=seed
            )
        results[target_column] = target_results
    return results


def run(args: argparse.Namespace) -> dict[str, Any]:
    bundle_path = project_root() / args.bundle
    events, table, spectra, theta = load_bundle(bundle_path)
    table = table.copy()
    if args.include_only_raw_objective and "include_in_raw_objective" in table:
        keep = table["include_in_raw_objective"].fillna(True).astype(bool).to_numpy()
        table = table.loc[keep].reset_index(drop=True)
        spectra = spectra[keep]

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "track_b_event_analysis_harness",
        "bundle": str(args.bundle),
        "event_count": int(len(table)),
        "theta_points": int(len(theta)) if theta is not None else None,
        "hypotheses": [
            "The harness should reproduce the synthetic event-over-label signal under held-out-plan splits.",
            "Held-out-batch splits should be reported separately because batch/session structure can make claims stricter.",
            "Provenance predictability should be visible if raw spectra or event features carry batch/operator/lot artifacts.",
            "Labels should be audited after raw/event objectives, not used as the primary objective.",
        ],
        "schema_audit": schema_audit(events),
        "missingness_audit": missingness_audit(table),
        "prediction_audit": prediction_audit(table, spectra, seed=args.seed),
        "retrieval_audit": retrieval_audit(table, spectra),
        "label_audit": label_audit(table, spectra),
        "provenance_audit": provenance_audit(table, spectra, seed=args.seed),
        "caveats": [
            "The current run may use synthetic data; synthetic hidden regimes are not chemistry evidence.",
            "Random-event splits can leak replicate or batch context and must not be the main paper claim.",
            "Held-out-plan and held-out-batch splits are stricter checks, not nuisances to hide.",
        ],
    }

    output_path = project_root() / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundle",
        type=Path,
        required=True,
        help="JSON bundle with events, event_table, spectra, and optional theta.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/track_b_event_analysis.json"),
    )
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--include-only-raw-objective", action="store_true")
    return parser.parse_args()


def main() -> None:
    result = run(parse_args())
    printable = {
        "task": result["task"],
        "hypotheses": result["hypotheses"],
        "event_count": result["event_count"],
        "schema_audit": result["schema_audit"],
        "missingness_audit": result["missingness_audit"],
        "prediction_audit": result["prediction_audit"],
        "retrieval_audit": result["retrieval_audit"],
        "label_audit": result["label_audit"],
        "provenance_audit": result["provenance_audit"],
        "caveats": result["caveats"],
    }
    print(json.dumps(printable, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
