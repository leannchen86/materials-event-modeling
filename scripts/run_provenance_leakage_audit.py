"""Audit a dataset for provenance leakage (collection-artifact / contamination check).

Unifies the opXRD source-predictability and normalization-control diagnostics behind one
reusable, dataset-agnostic tool. For each feature representation it measures how
recoverable the provenance label (originating lab/instrument) is, scores the leakage on
a 0-1 scale, assigns a clean/elevated/severe verdict, and — with --include-controls —
checks whether a preprocessing control neutralizes the confound.

The audit core lives in ``materials_event_modeling.audit.provenance_leakage`` and is
modality-agnostic; this script only provides dataset *adapters* that turn a corpus into
``{feature_set_name: matrix}`` + provenance labels. Adding a dataset = one adapter
function registered in ``DATASETS``.

    .venv/bin/python scripts/run_provenance_leakage_audit.py --dataset opxrd --include-controls

The opXRD adapter is self-contained (numpy + sklearn + pandas only) so the tool stays
portable and free of the project's torch training stack.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from materials_event_modeling.audit.provenance_leakage import (
    audit_feature_sets,
    control_efficacy,
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------------------
# opXRD adapter — feature builders mirror analyze_opxrd_source_predictability.py and
# analyze_opxrd_normalization_controls.py, kept self-contained so the audit tool has no
# torch dependency.
# --------------------------------------------------------------------------------------


def _local_peak_density(spectra: np.ndarray, threshold: float) -> np.ndarray:
    values = []
    for spectrum in spectra:
        peaks = (
            (spectrum[1:-1] > spectrum[:-2])
            & (spectrum[1:-1] >= spectrum[2:])
            & (spectrum[1:-1] >= threshold)
        )
        values.append(float(np.mean(peaks)))
    return np.asarray(values, dtype=np.float32)


def _spectrum_summary_features(xrd: np.ndarray, peak_threshold: float) -> np.ndarray:
    quantiles = np.quantile(xrd, [0.1, 0.25, 0.5, 0.75, 0.9], axis=1).T
    features = [
        xrd.mean(axis=1),
        xrd.std(axis=1),
        xrd.max(axis=1),
        np.mean(xrd > 0.01, axis=1),
        np.mean(xrd > 0.05, axis=1),
        np.mean(xrd > 0.25, axis=1),
        _local_peak_density(xrd, threshold=peak_threshold),
    ]
    return np.column_stack([*features, quantiles]).astype(np.float32)


def _metadata_features(samples: pd.DataFrame) -> np.ndarray:
    raw = samples[
        ["points", "theta_min", "theta_max", "intensity_min", "intensity_max", "phase_count"]
    ].copy()
    raw["theta_span"] = raw["theta_max"] - raw["theta_min"]
    raw["is_labeled"] = samples["is_labeled"].astype(bool).astype(float)
    return raw.fillna(0).to_numpy(dtype=np.float32)


def _coverage_mask(theta: np.ndarray, samples: pd.DataFrame) -> np.ndarray:
    theta_min = samples["theta_min"].to_numpy(dtype=np.float32)[:, None]
    theta_max = samples["theta_max"].to_numpy(dtype=np.float32)[:, None]
    return ((theta[None, :] >= theta_min) & (theta[None, :] <= theta_max)).astype(np.float32)


def _row_zscore(x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    center = x.mean(axis=1, keepdims=True)
    scale = x.std(axis=1, keepdims=True)
    return ((x - center) / np.maximum(scale, eps)).astype(np.float32)


def _row_l1(x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    denom = np.sum(np.abs(x), axis=1, keepdims=True)
    return (x / np.maximum(denom, eps)).astype(np.float32)


def _derivative(x: np.ndarray) -> np.ndarray:
    return np.diff(x, axis=1).astype(np.float32)


def _pca(x: np.ndarray, components: int, seed: int) -> np.ndarray:
    n_components = min(components, x.shape[0] - 1, x.shape[1])
    return PCA(n_components=n_components, random_state=seed).fit_transform(x).astype(np.float32)


def load_opxrd(args: argparse.Namespace) -> dict[str, Any]:
    """Return feature sets + provenance labels for the opXRD processed subset."""
    root = project_root()
    manifest_path = root / "data/manifests/opxrd_processed_subset.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            "Processed opXRD subset is missing. Run "
            "`.venv/bin/python scripts/preprocess_opxrd.py --max-spectra 4096 --points 4096`."
        )
    manifest = json.loads(manifest_path.read_text())
    with np.load(root / manifest["arrays_path"]) as data:
        xrd = data["xrd"].astype(np.float32)
        theta = data["theta"].astype(np.float32)
    samples = pd.read_csv(root / manifest["samples_path"])
    samples["top_level_source"] = samples["member_name"].str.split("/", n=1).str[0]

    counts = samples["top_level_source"].value_counts()
    kept = sorted(counts[counts >= args.min_source_samples].index.tolist())
    keep_mask = samples["top_level_source"].isin(kept).to_numpy()
    xrd = xrd[keep_mask]
    samples = samples.loc[keep_mask].reset_index(drop=True)
    labels = samples["top_level_source"].to_numpy()

    feature_sets: dict[str, np.ndarray] = {
        "metadata": _metadata_features(samples),
        "spectrum_summary": _spectrum_summary_features(xrd, args.peak_threshold),
        "xrd_pca": _pca(xrd, args.pca_components, args.seed),
    }

    control_pairs: list[tuple[str, str]] = []
    if args.include_controls:
        coverage = _coverage_mask(theta, samples)
        coverage_fraction = coverage.mean(axis=0)
        crop_mask = coverage_fraction >= args.min_coverage_fraction
        if int(crop_mask.sum()) < args.min_crop_points:
            raise RuntimeError(
                f"Only {int(crop_mask.sum())} theta points meet coverage "
                f"{args.min_coverage_fraction}; lower --min-coverage-fraction."
            )
        cropped = xrd[:, crop_mask]
        for name, matrix in {
            "coverage_mask_pca": coverage,
            "full_xrd_pca": xrd,
            "full_xrd_row_zscore_pca": _row_zscore(xrd),
            "full_xrd_l1_pca": _row_l1(xrd),
            "crop_xrd_pca": cropped,
            "crop_xrd_row_zscore_pca": _row_zscore(cropped),
            "crop_xrd_l1_pca": _row_l1(cropped),
            "crop_xrd_derivative_pca": _derivative(_row_zscore(cropped)),
        }.items():
            feature_sets[name] = _pca(matrix, args.pca_components, args.seed)
        # The decontamination-remediation check: does the strongest control neutralize
        # the leakage present in the raw representation?
        control_pairs.append(("full_xrd_pca", "crop_xrd_derivative_pca"))

    return {
        "feature_sets": feature_sets,
        "labels": labels,
        "control_pairs": control_pairs,
        "meta": {
            "dataset_id": "opxrd",
            "spectra": int(xrd.shape[0]),
            "theta_points": int(xrd.shape[1]),
            "min_source_samples": args.min_source_samples,
        },
    }


DATASETS: dict[str, Callable[[argparse.Namespace], dict[str, Any]]] = {
    "opxrd": load_opxrd,
}


def print_report(report: dict[str, Any], meta: dict[str, Any], efficacy: list[dict[str, Any]]) -> None:
    chance = report["results"][0]["chance_balanced_accuracy"] if report["results"] else 0.0
    print(
        f"\nProvenance-leakage audit — {meta.get('dataset_id', '?')}  "
        f"({report['n_classes']} sources, {report['n_items']} items, "
        f"chance bal-acc {chance:.3f}, {report['n_splits']}-fold)\n"
    )
    print(f"  {'feature_set':<32}{'leakage':>9}{'bal_acc':>9}  severity")
    print(f"  {'-' * 32}{'-' * 9}{'-' * 9}  {'-' * 8}")
    for r in report["results"]:
        print(
            f"  {r['feature_set']:<32}{r['leakage_score']:>9.3f}"
            f"{r['balanced_accuracy']:>9.3f}  {r['severity']}"
        )
    print(
        f"\n  worst: {report['worst_feature_set']} "
        f"(score {report['worst_leakage_score']:.3f}, {report['worst_severity']})"
    )
    print(f"  {report['recommendation']}")
    for e in efficacy:
        verdict = "NEUTRALIZED" if e["neutralized"] else f"still {e['control_severity']}"
        print(
            f"\n  control efficacy: {e['baseline']} ({e['baseline_leakage_score']:.3f}) "
            f"-> {e['control']} ({e['control_leakage_score']:.3f}): "
            f"{e['relative_reduction'] * 100:.0f}% leakage reduction, {verdict}"
        )
    print()


def run(args: argparse.Namespace) -> dict[str, Any]:
    bundle = DATASETS[args.dataset](args)
    report = audit_feature_sets(
        bundle["feature_sets"], bundle["labels"], n_splits=args.n_splits, seed=args.seed
    )
    efficacy = [
        control_efficacy(report, baseline, control)
        for baseline, control in bundle["control_pairs"]
    ]
    report["dataset"] = args.dataset
    report["dataset_meta"] = bundle["meta"]
    report["control_efficacy"] = efficacy
    report["created_at"] = datetime.now(timezone.utc).isoformat()

    print_report(report, bundle["meta"], efficacy)

    output = project_root() / args.output if args.output else None
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(f"  wrote {output.relative_to(project_root())}\n")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(DATASETS), default="opxrd")
    parser.add_argument("--include-controls", action="store_true",
                        help="Also audit normalization/coverage controls and report efficacy.")
    parser.add_argument("--min-source-samples", type=int, default=15)
    parser.add_argument("--n-splits", type=int, default=3)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--pca-components", type=int, default=32)
    parser.add_argument("--peak-threshold", type=float, default=0.05)
    parser.add_argument("--min-coverage-fraction", type=float, default=0.95)
    parser.add_argument("--min-crop-points", type=int, default=256)
    parser.add_argument("--output", type=Path,
                        default=Path("data/manifests/provenance_leakage_audit_opxrd.json"))
    return parser.parse_args()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
