"""Preprocess opXRD deposited patterns into standardized fixed-grid arrays."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from materials_event_modeling.data.opxrd import (
    DATASET_ID,
    iter_patterns_from_archive,
    json_member_names,
    pattern_summary,
    raw_archive_path,
    select_member_names,
    standard_theta_grid,
    standardize_intensity,
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def preprocess(max_spectra: int, points: int, selection: str) -> dict[str, object]:
    root = project_root()
    archive_path = raw_archive_path(root)
    if not archive_path.exists():
        raise FileNotFoundError(
            f"Missing {archive_path}. Run `python3 scripts/download_data.py` first."
        )

    output_dir = root / "data" / "processed" / DATASET_ID
    interim_dir = root / "data" / "interim" / DATASET_ID
    manifest_path = root / "data" / "manifests" / f"{DATASET_ID}_processed_subset.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    interim_dir.mkdir(parents=True, exist_ok=True)

    theta = standard_theta_grid(points=points)
    selected_members = select_member_names(
        json_member_names(archive_path),
        max_spectra=max_spectra,
        strategy=selection,
    )
    spectra = []
    rows = []
    skipped = 0

    for pattern in iter_patterns_from_archive(archive_path, member_names=selected_members):
        try:
            intensity = standardize_intensity(pattern.two_theta, pattern.intensity, theta)
        except ValueError:
            skipped += 1
            continue

        row = pattern_summary(pattern)
        row["subset_index"] = len(spectra)
        rows.append(row)
        spectra.append(intensity)
        if len(spectra) >= max_spectra:
            break

    if not spectra:
        raise RuntimeError("No opXRD spectra could be standardized")

    xrd = np.stack(spectra).astype(np.float32)
    npz_path = output_dir / f"xrd_subset_{len(spectra)}_p{points}.npz"
    np.savez_compressed(npz_path, theta=theta, xrd=xrd)

    samples_path = interim_dir / f"samples_subset_{len(spectra)}_p{points}.csv"
    with samples_path.open("w", newline="") as handle:
        fieldnames = [
            "subset_index",
            "member_name",
            "points",
            "theta_min",
            "theta_max",
            "intensity_min",
            "intensity_max",
            "is_labeled",
            "phase_count",
            "institution",
            "contributor_name",
            "original_file_format",
            "measurement_date",
            "tags",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            row = dict(row)
            row["tags"] = json.dumps(row.get("tags", []), sort_keys=True)
            writer.writerow(row)

    manifest = {
        "dataset_id": DATASET_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "archive_path": str(archive_path.relative_to(root)),
        "arrays_path": str(npz_path.relative_to(root)),
        "samples_path": str(samples_path.relative_to(root)),
        "spectra": int(xrd.shape[0]),
        "theta_points": int(theta.shape[0]),
        "requested_max_spectra": max_spectra,
        "selection": selection,
        "skipped_before_subset_complete": skipped,
        "normalization": (
            "per-pattern interpolation to fixed 2-theta grid, minimum shift, "
            "then max-intensity normalization"
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-spectra",
        type=int,
        default=4096,
        help="Number of standardized spectra to materialize for the pilot subset.",
    )
    parser.add_argument(
        "--points",
        type=int,
        default=4096,
        help="Number of fixed-grid two-theta points per spectrum.",
    )
    parser.add_argument(
        "--selection",
        choices=["spread", "first"],
        default="spread",
        help="How to select the pilot subset from archive member order.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        json.dumps(
            preprocess(args.max_spectra, args.points, args.selection),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
