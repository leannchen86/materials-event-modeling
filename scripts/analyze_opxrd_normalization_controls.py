"""Test whether normalization/coverage controls reduce opXRD source predictability."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from analyze_opxrd_source_predictability import (
    evaluate_feature_set,
    metadata_features,
    spectrum_summary_features,
)
from run_opxrd_conv_reconstruction import load_subset, project_root
from sklearn.decomposition import PCA


def load_theta(root: Path) -> np.ndarray:
    manifest = json.loads((root / "data/manifests/opxrd_processed_subset.json").read_text())
    with np.load(root / manifest["arrays_path"]) as data:
        return data["theta"].astype(np.float32)


def coverage_mask(theta: np.ndarray, samples: Any) -> np.ndarray:
    theta_min = samples["theta_min"].to_numpy(dtype=np.float32)[:, None]
    theta_max = samples["theta_max"].to_numpy(dtype=np.float32)[:, None]
    return ((theta[None, :] >= theta_min) & (theta[None, :] <= theta_max)).astype(np.float32)


def row_zscore(x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    center = x.mean(axis=1, keepdims=True)
    scale = x.std(axis=1, keepdims=True)
    return ((x - center) / np.maximum(scale, eps)).astype(np.float32)


def row_l1_normalize(x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    denom = np.sum(np.abs(x), axis=1, keepdims=True)
    return (x / np.maximum(denom, eps)).astype(np.float32)


def derivative(x: np.ndarray) -> np.ndarray:
    return np.diff(x, axis=1).astype(np.float32)


def pca_features(x: np.ndarray, components: int, seed: int) -> tuple[np.ndarray, float]:
    n_components = min(components, x.shape[0] - 1, x.shape[1])
    pca = PCA(n_components=n_components, random_state=seed)
    features = pca.fit_transform(x).astype(np.float32)
    return features, float(np.sum(pca.explained_variance_ratio_))


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root()
    theta = load_theta(root)
    xrd, samples = load_subset(root)
    counts = samples["top_level_source"].value_counts().sort_index()
    kept_sources = sorted(counts[counts >= args.min_source_samples].index.tolist())
    keep_mask = samples["top_level_source"].isin(kept_sources).to_numpy()
    xrd = xrd[keep_mask]
    samples = samples.loc[keep_mask].reset_index(drop=True)
    labels = samples["top_level_source"].to_numpy()
    class_counts = samples["top_level_source"].value_counts().sort_index().to_dict()
    n_splits = min(args.n_splits, min(class_counts.values()))

    coverage = coverage_mask(theta, samples)
    coverage_fraction = coverage.mean(axis=0)
    crop_mask = coverage_fraction >= args.min_coverage_fraction
    if int(crop_mask.sum()) < args.min_crop_points:
        raise RuntimeError(
            f"Only {int(crop_mask.sum())} theta points meet min coverage "
            f"{args.min_coverage_fraction}; lower --min-coverage-fraction."
        )
    cropped_xrd = xrd[:, crop_mask]
    cropped_theta = theta[crop_mask]

    feature_sets: dict[str, np.ndarray] = {
        "metadata": metadata_features(samples),
        "spectrum_summary": spectrum_summary_features(xrd, peak_threshold=args.peak_threshold),
    }

    for name, matrix in {
        "coverage_mask_pca": coverage,
        "full_xrd_pca": xrd,
        "full_xrd_row_zscore_pca": row_zscore(xrd),
        "full_xrd_l1_pca": row_l1_normalize(xrd),
        "crop_xrd_pca": cropped_xrd,
        "crop_xrd_row_zscore_pca": row_zscore(cropped_xrd),
        "crop_xrd_l1_pca": row_l1_normalize(cropped_xrd),
        "crop_xrd_derivative_pca": derivative(row_zscore(cropped_xrd)),
    }.items():
        features, explained = pca_features(matrix, args.pca_components, args.seed)
        feature_sets[name] = features
        feature_sets[f"{name}_explained_variance_marker"] = np.full(
            (features.shape[0], 1),
            explained,
            dtype=np.float32,
        )

    explained_variance = {}
    filtered_feature_sets = {}
    for name, features in feature_sets.items():
        if name.endswith("_explained_variance_marker"):
            explained_variance[name.removesuffix("_explained_variance_marker")] = float(
                features[0, 0]
            )
        else:
            filtered_feature_sets[name] = features

    results = [
        evaluate_feature_set(
            name=name,
            features=features,
            labels=labels,
            classes=kept_sources,
            n_splits=n_splits,
            seed=args.seed,
        )
        for name, features in filtered_feature_sets.items()
    ]

    result = {
        "dataset_id": "opxrd",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "opxrd_normalization_controls",
        "spectra": int(xrd.shape[0]),
        "theta_points": int(xrd.shape[1]),
        "sources": class_counts,
        "n_splits": n_splits,
        "seed": args.seed,
        "pca_components": args.pca_components,
        "peak_threshold": args.peak_threshold,
        "min_coverage_fraction": args.min_coverage_fraction,
        "crop_points": int(crop_mask.sum()),
        "crop_theta_min": float(cropped_theta[0]),
        "crop_theta_max": float(cropped_theta[-1]),
        "pca_explained_variance": explained_variance,
        "results": results,
        "caveats": [
            "This is an artifact-control diagnostic, not a source classifier benchmark.",
            "Coverage-controlled crops reduce theta-range artifacts but do not prove chemistry.",
            "If source predictability remains high after controls, embeddings may still encode measurement style.",
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
    parser.add_argument("--min-coverage-fraction", type=float, default=0.95)
    parser.add_argument("--min-crop-points", type=int, default=256)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/opxrd_normalization_controls.json"),
    )
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
