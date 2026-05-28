"""Run ontology stress-test evaluations."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    mean_absolute_error,
    roc_auc_score,
    silhouette_score,
)
from sklearn.model_selection import GroupKFold, KFold, StratifiedKFold, cross_val_predict
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from materials_event_modeling.data.nist import DATASET_ID


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_processed_nist(root: Path) -> tuple[np.lib.npyio.NpzFile, pd.DataFrame]:
    arrays_path = root / "data" / "processed" / DATASET_ID / "xrd_arrays.npz"
    samples_path = root / "data" / "interim" / DATASET_ID / "samples.csv"
    if not arrays_path.exists() or not samples_path.exists():
        raise FileNotFoundError(
            "Processed NIST files are missing. Run "
            "`python3 scripts/preprocess_xrd.py nist_mds2_2301` first."
        )
    return np.load(arrays_path), pd.read_csv(samples_path)


def _xrd_pca_estimator(n_components: int, final_estimator: BaseEstimator) -> BaseEstimator:
    return make_pipeline(
        StandardScaler(),
        PCA(n_components=n_components, random_state=17),
        final_estimator,
    )


def _combined_estimator(n_components: int, final_estimator: BaseEstimator) -> BaseEstimator:
    preprocessor = ColumnTransformer(
        transformers=[
            ("metadata", StandardScaler(), [0, 1]),
            (
                "xrd_pca",
                make_pipeline(StandardScaler(), PCA(n_components=n_components, random_state=17)),
                slice(2, None),
            ),
        ]
    )
    return make_pipeline(preprocessor, final_estimator)


def make_feature_sets(arrays: np.lib.npyio.NpzFile, samples: pd.DataFrame) -> dict[str, dict[str, Any]]:
    xrd = arrays["xrd_area_norm"].astype(np.float32)
    metadata = samples[["v_fraction", "temp_c"]].to_numpy(dtype=np.float32)
    combined = np.hstack([metadata, xrd])
    xrd_pca_10_embedding = make_pipeline(
        StandardScaler(), PCA(n_components=10, random_state=17)
    ).fit_transform(xrd)
    xrd_pca_25_embedding = make_pipeline(
        StandardScaler(), PCA(n_components=25, random_state=17)
    ).fit_transform(xrd)
    return {
        "composition_temp": {
            "cv_features": metadata,
            "embedding": metadata,
            "classifier": make_pipeline(
                StandardScaler(),
                LogisticRegression(class_weight="balanced", max_iter=5000, random_state=17),
            ),
            "regressor": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        },
        "xrd_pca_10": {
            "cv_features": xrd,
            "embedding": xrd_pca_10_embedding,
            "classifier": _xrd_pca_estimator(
                10,
                LogisticRegression(class_weight="balanced", max_iter=5000, random_state=17),
            ),
            "regressor": _xrd_pca_estimator(10, Ridge(alpha=1.0)),
        },
        "xrd_pca_25": {
            "cv_features": xrd,
            "embedding": xrd_pca_25_embedding,
            "classifier": _xrd_pca_estimator(
                25,
                LogisticRegression(class_weight="balanced", max_iter=5000, random_state=17),
            ),
            "regressor": _xrd_pca_estimator(25, Ridge(alpha=1.0)),
        },
        "composition_temp_plus_xrd_pca_10": {
            "cv_features": combined,
            "embedding": np.hstack([metadata, xrd_pca_10_embedding]),
            "classifier": _combined_estimator(
                10,
                LogisticRegression(class_weight="balanced", max_iter=5000, random_state=17),
            ),
            "regressor": _combined_estimator(10, Ridge(alpha=1.0)),
        },
    }


def binary_cv_metrics(
    features: np.ndarray,
    target: np.ndarray,
    groups: np.ndarray,
    estimator: BaseEstimator,
) -> dict[str, float | None]:
    random_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=17)
    random_scores = cross_val_predict(estimator, features, target, cv=random_cv, method="predict_proba")[
        :, 1
    ]
    random_pred = random_scores >= 0.5

    grouped_metrics: dict[str, float | None] = {
        "grouped_temp_roc_auc": None,
        "grouped_temp_average_precision": None,
        "grouped_temp_balanced_accuracy": None,
    }
    unique_groups = np.unique(groups)
    if len(unique_groups) >= 3:
        grouped_cv = GroupKFold(n_splits=len(unique_groups))
        grouped_scores = cross_val_predict(
            estimator,
            features,
            target,
            cv=grouped_cv,
            groups=groups,
            method="predict_proba",
        )[:, 1]
        grouped_pred = grouped_scores >= 0.5
        grouped_metrics = {
            "grouped_temp_roc_auc": float(roc_auc_score(target, grouped_scores)),
            "grouped_temp_average_precision": float(average_precision_score(target, grouped_scores)),
            "grouped_temp_balanced_accuracy": float(balanced_accuracy_score(target, grouped_pred)),
        }

    return {
        "random_cv_roc_auc": float(roc_auc_score(target, random_scores)),
        "random_cv_average_precision": float(average_precision_score(target, random_scores)),
        "random_cv_balanced_accuracy": float(balanced_accuracy_score(target, random_pred)),
        **grouped_metrics,
    }


def entropy_cv_metrics(
    features: np.ndarray,
    entropy: np.ndarray,
    groups: np.ndarray,
    estimator: BaseEstimator,
) -> dict[str, float]:
    random_cv = KFold(n_splits=5, shuffle=True, random_state=17)
    random_pred = cross_val_predict(estimator, features, entropy, cv=random_cv)

    grouped_cv = GroupKFold(n_splits=len(np.unique(groups)))
    grouped_pred = cross_val_predict(estimator, features, entropy, cv=grouped_cv, groups=groups)
    return {
        "random_cv_mae": float(mean_absolute_error(entropy, random_pred)),
        "grouped_temp_mae": float(mean_absolute_error(entropy, grouped_pred)),
    }


def label_compactness(features: np.ndarray, labels: np.ndarray) -> dict[str, float | None]:
    if len(set(labels.tolist())) < 2:
        return {"silhouette_consensus_label": None}
    return {"silhouette_consensus_label": float(silhouette_score(features, labels))}


def neighbor_label_purity(features: np.ndarray, labels: np.ndarray, k: int = 5) -> float:
    scaled = StandardScaler().fit_transform(features)
    neighbors = NearestNeighbors(n_neighbors=k + 1).fit(scaled)
    indices = neighbors.kneighbors(return_distance=False)[:, 1:]
    purity = [np.mean(labels[row_indices] == labels[idx]) for idx, row_indices in enumerate(indices)]
    return float(np.mean(purity))


def run_nist_tests() -> dict[str, object]:
    root = project_root()
    arrays, samples = load_processed_nist(root)
    feature_sets = make_feature_sets(arrays, samples)

    human = samples[samples["human_consensus_label"].notna()].copy()
    human_indices = human["sample_index"].to_numpy(dtype=int)
    target_disagree = human["human_disagree"].astype(bool).to_numpy()
    entropy = human["human_label_entropy"].to_numpy(dtype=float)
    consensus = human["human_consensus_label"].astype(int).to_numpy()
    groups = human["temp_c"].to_numpy()

    results: dict[str, object] = {
        "dataset_id": DATASET_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "initial_human_label_disagreement_and_compactness_baselines",
        "n_human_labeled": int(len(human)),
        "n_human_disagreeing": int(target_disagree.sum()),
        "feature_sets": {},
        "caveats": [
            "This is observational and predictive, not causal.",
            "Random CV can overestimate performance on combinatorial grids; grouped-by-temperature CV is included as a harder check.",
            "Compactness and nearest-neighbor metrics use full-dataset embeddings as descriptive diagnostics; predictive CV fits PCA inside each fold.",
        ],
    }

    for name, feature_set in feature_sets.items():
        cv_features = feature_set["cv_features"][human_indices]
        embedding = feature_set["embedding"][human_indices]
        metrics = {
            "disagreement_prediction": binary_cv_metrics(
                cv_features,
                target_disagree,
                groups,
                feature_set["classifier"],
            ),
            "entropy_prediction": entropy_cv_metrics(
                cv_features,
                entropy,
                groups,
                feature_set["regressor"],
            ),
            "compactness": label_compactness(embedding, consensus),
            "nearest_neighbor_consensus_label_purity_k5": neighbor_label_purity(
                embedding, consensus, k=5
            ),
        }
        results["feature_sets"][name] = metrics

    output_path = root / "data" / "manifests" / f"{DATASET_ID}_initial_ontology_tests.json"
    output_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=[DATASET_ID], help="Dataset identifier to evaluate.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dataset == DATASET_ID:
        print(json.dumps(run_nist_tests(), indent=2, sort_keys=True))
        return
    raise AssertionError(f"Unhandled dataset: {args.dataset}")


if __name__ == "__main__":
    main()
