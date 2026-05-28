"""Measure how easily opXRD source identity is recoverable from spectra and metadata."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import numpy as np
from sklearn.decomposition import PCA
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from run_opxrd_conv_reconstruction import load_subset, project_root


def metric_summary(values: list[float]) -> dict[str, float]:
    return {
        "mean": mean(values),
        "std": pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def local_peak_density(spectra: np.ndarray, threshold: float) -> np.ndarray:
    values = []
    for spectrum in spectra:
        peaks = (
            (spectrum[1:-1] > spectrum[:-2])
            & (spectrum[1:-1] >= spectrum[2:])
            & (spectrum[1:-1] >= threshold)
        )
        values.append(float(np.mean(peaks)))
    return np.asarray(values, dtype=np.float32)


def spectrum_summary_features(xrd: np.ndarray, peak_threshold: float) -> np.ndarray:
    quantiles = np.quantile(xrd, [0.1, 0.25, 0.5, 0.75, 0.9], axis=1).T
    features = [
        xrd.mean(axis=1),
        xrd.std(axis=1),
        xrd.max(axis=1),
        np.mean(xrd > 0.01, axis=1),
        np.mean(xrd > 0.05, axis=1),
        np.mean(xrd > 0.25, axis=1),
        local_peak_density(xrd, threshold=peak_threshold),
    ]
    return np.column_stack([*features, quantiles]).astype(np.float32)


def metadata_features(samples: Any) -> np.ndarray:
    raw = samples[
        [
            "points",
            "theta_min",
            "theta_max",
            "intensity_min",
            "intensity_max",
            "phase_count",
        ]
    ].copy()
    raw["theta_span"] = raw["theta_max"] - raw["theta_min"]
    raw["is_labeled"] = samples["is_labeled"].astype(bool).astype(float)
    return raw.fillna(0).to_numpy(dtype=np.float32)


def evaluate_feature_set(
    *,
    name: str,
    features: np.ndarray,
    labels: np.ndarray,
    classes: list[str],
    n_splits: int,
    seed: int,
) -> dict[str, Any]:
    classifier = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=seed,
        ),
    )
    baseline = DummyClassifier(strategy="most_frequent")
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)

    accuracy = []
    balanced_accuracy = []
    baseline_accuracy = []
    baseline_balanced_accuracy = []
    confusion = np.zeros((len(classes), len(classes)), dtype=np.int64)

    for train_idx, test_idx in cv.split(features, labels):
        classifier.fit(features[train_idx], labels[train_idx])
        prediction = classifier.predict(features[test_idx])
        baseline.fit(features[train_idx], labels[train_idx])
        baseline_prediction = baseline.predict(features[test_idx])

        accuracy.append(float(accuracy_score(labels[test_idx], prediction)))
        balanced_accuracy.append(float(balanced_accuracy_score(labels[test_idx], prediction)))
        baseline_accuracy.append(float(accuracy_score(labels[test_idx], baseline_prediction)))
        baseline_balanced_accuracy.append(
            float(balanced_accuracy_score(labels[test_idx], baseline_prediction))
        )
        confusion += confusion_matrix(labels[test_idx], prediction, labels=classes)

    per_class_recall = {}
    for idx, class_name in enumerate(classes):
        row_sum = int(confusion[idx].sum())
        per_class_recall[class_name] = (
            float(confusion[idx, idx] / row_sum) if row_sum else None
        )

    return {
        "feature_set": name,
        "features": int(features.shape[1]),
        "accuracy": metric_summary(accuracy),
        "balanced_accuracy": metric_summary(balanced_accuracy),
        "baseline_accuracy": metric_summary(baseline_accuracy),
        "baseline_balanced_accuracy": metric_summary(baseline_balanced_accuracy),
        "per_class_recall": per_class_recall,
        "confusion_matrix": confusion.tolist(),
        "classes": classes,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root()
    xrd, samples = load_subset(root)
    counts = samples["top_level_source"].value_counts().sort_index()
    kept_sources = sorted(counts[counts >= args.min_source_samples].index.tolist())
    keep_mask = samples["top_level_source"].isin(kept_sources).to_numpy()
    xrd = xrd[keep_mask]
    samples = samples.loc[keep_mask].reset_index(drop=True)
    labels = samples["top_level_source"].to_numpy()
    class_counts = samples["top_level_source"].value_counts().sort_index().to_dict()
    n_splits = min(args.n_splits, min(class_counts.values()))

    summary = spectrum_summary_features(xrd, peak_threshold=args.peak_threshold)
    meta = metadata_features(samples)

    pca = PCA(n_components=args.pca_components, random_state=args.seed)
    pca_features = pca.fit_transform(xrd)

    feature_sets = {
        "metadata": meta,
        "spectrum_summary": summary,
        "xrd_pca": pca_features.astype(np.float32),
        "metadata_plus_spectrum_summary": np.column_stack([meta, summary]).astype(np.float32),
        "xrd_pca_plus_metadata": np.column_stack([pca_features, meta]).astype(np.float32),
    }

    results = [
        evaluate_feature_set(
            name=name,
            features=features,
            labels=labels,
            classes=kept_sources,
            n_splits=n_splits,
            seed=args.seed,
        )
        for name, features in feature_sets.items()
    ]

    result = {
        "dataset_id": "opxrd",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "opxrd_source_predictability",
        "spectra": int(xrd.shape[0]),
        "theta_points": int(xrd.shape[1]),
        "min_source_samples": args.min_source_samples,
        "source_counts": class_counts,
        "n_splits": n_splits,
        "seed": args.seed,
        "pca_components": args.pca_components,
        "peak_threshold": args.peak_threshold,
        "pca_explained_variance_ratio_sum": float(np.sum(pca.explained_variance_ratio_)),
        "results": results,
        "caveats": [
            "This is an artifact diagnostic, not a source-classification benchmark.",
            "Random folds answer whether source imprint is present, not whether it generalizes to new sources.",
            "High source predictability means embeddings can easily encode lab/instrument/preprocessing artifacts.",
        ],
    }
    output_path = root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-source-samples", type=int, default=15)
    parser.add_argument("--n-splits", type=int, default=3)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--pca-components", type=int, default=32)
    parser.add_argument("--peak-threshold", type=float, default=0.05)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/opxrd_source_predictability.json"),
    )
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
