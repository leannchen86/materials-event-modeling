"""Preprocess raw XRD files into model-ready arrays."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from materials_event_modeling.data.nist import DATASET_ID, area_normalize_xrd, load_dataset


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def preprocess_nist() -> dict[str, object]:
    root = project_root()
    dataset = load_dataset(root)
    output_dir = root / "data" / "processed" / DATASET_ID
    interim_dir = root / "data" / "interim" / DATASET_ID
    manifest_path = root / "data" / "manifests" / f"{DATASET_ID}_processed.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    interim_dir.mkdir(parents=True, exist_ok=True)

    xrd_area_norm = area_normalize_xrd(dataset.xrd)
    npz_path = output_dir / "xrd_arrays.npz"
    np.savez_compressed(
        npz_path,
        theta=dataset.theta,
        xrd_raw=dataset.xrd,
        xrd_area_norm=xrd_area_norm,
    )

    samples_path = interim_dir / "samples.csv"
    dataset.samples.to_csv(samples_path, index=False)

    human_rows = dataset.samples["human_consensus_label"].notna()
    machine_rows = dataset.samples["machine_consensus_label"].notna()
    manifest = {
        "dataset_id": DATASET_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "arrays_path": str(npz_path.relative_to(root)),
        "samples_path": str(samples_path.relative_to(root)),
        "theta_points": int(dataset.theta.shape[0]),
        "spectra": int(dataset.xrd.shape[0]),
        "normalizations": {
            "xrd_raw": "as provided by NIST",
            "xrd_area_norm": "per-spectrum minimum shifted to zero, divided by summed intensity",
        },
        "human_labeled_rows": int(human_rows.sum()),
        "human_disagreeing_rows": int(dataset.samples.loc[human_rows, "human_disagree"].sum()),
        "machine_labeled_rows": int(machine_rows.sum()),
        "machine_disagreeing_rows": int(dataset.samples.loc[machine_rows, "machine_disagree"].sum()),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dataset",
        choices=[DATASET_ID],
        help="Dataset identifier to preprocess.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dataset == DATASET_ID:
        print(json.dumps(preprocess_nist(), indent=2, sort_keys=True))
        return
    raise AssertionError(f"Unhandled dataset: {args.dataset}")


if __name__ == "__main__":
    main()
