"""Create first-pass diagnostic plots for the NIST dataset."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from materials_event_modeling.data.nist import DATASET_ID, LABEL_MEANINGS


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_processed(root: Path) -> tuple[np.lib.npyio.NpzFile, pd.DataFrame]:
    arrays_path = root / "data" / "processed" / DATASET_ID / "xrd_arrays.npz"
    samples_path = root / "data" / "interim" / DATASET_ID / "samples.csv"
    if not arrays_path.exists() or not samples_path.exists():
        raise FileNotFoundError(
            "Processed NIST files are missing. Run "
            "`python3 scripts/preprocess_xrd.py nist_mds2_2301` first."
        )
    return np.load(arrays_path), pd.read_csv(samples_path)


def human_subset(samples: pd.DataFrame) -> pd.DataFrame:
    return samples[samples["human_consensus_label"].notna()].copy()


def plot_composition_entropy(samples: pd.DataFrame, output_path: Path) -> None:
    human = human_subset(samples)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    scatter = ax.scatter(
        human["nb_fraction"],
        human["temp_c"],
        c=human["human_label_entropy"],
        s=np.where(human["human_disagree"], 56, 28),
        cmap="viridis",
        edgecolor="black",
        linewidth=0.4,
    )
    ax.set_xlabel("Nb fraction")
    ax.set_ylabel("Temperature (C)")
    ax.set_title("Human-label entropy over composition-temperature grid")
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Shannon entropy across human labels")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_xrd_pca(arrays: np.lib.npyio.NpzFile, samples: pd.DataFrame, output_dir: Path) -> None:
    human = human_subset(samples)
    xrd = arrays["xrd_area_norm"].astype(np.float32)
    pca = make_pipeline(StandardScaler(), PCA(n_components=2, random_state=17))
    coords = pca.fit_transform(xrd)[human["sample_index"].to_numpy(dtype=int)]
    explained = pca.named_steps["pca"].explained_variance_ratio_

    labels = human["human_consensus_label"].astype(int).to_numpy()
    fig, ax = plt.subplots(figsize=(6.5, 5.2))
    for label in sorted(LABEL_MEANINGS):
        mask = labels == label
        ax.scatter(
            coords[mask, 0],
            coords[mask, 1],
            s=42,
            alpha=0.82,
            label=f"{label}: {LABEL_MEANINGS[label]}",
        )
    ax.set_xlabel(f"XRD PC1 ({explained[0]:.1%} var.)")
    ax.set_ylabel(f"XRD PC2 ({explained[1]:.1%} var.)")
    ax.set_title("XRD PCA colored by human consensus label")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(output_dir / "xrd_pca_consensus_label.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 5.2))
    scatter = ax.scatter(
        coords[:, 0],
        coords[:, 1],
        c=human["human_label_entropy"],
        s=np.where(human["human_disagree"], 56, 28),
        cmap="viridis",
        edgecolor="black",
        linewidth=0.3,
    )
    ax.set_xlabel(f"XRD PC1 ({explained[0]:.1%} var.)")
    ax.set_ylabel(f"XRD PC2 ({explained[1]:.1%} var.)")
    ax.set_title("XRD PCA colored by human-label entropy")
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Shannon entropy across human labels")
    fig.tight_layout()
    fig.savefig(output_dir / "xrd_pca_human_entropy.png", dpi=180)
    plt.close(fig)


def run() -> dict[str, object]:
    root = project_root()
    arrays, samples = load_processed(root)
    output_dir = root / "outputs" / DATASET_ID
    output_dir.mkdir(parents=True, exist_ok=True)

    plot_composition_entropy(samples, output_dir / "composition_temp_human_entropy.png")
    plot_xrd_pca(arrays, samples, output_dir)

    manifest = {
        "dataset_id": DATASET_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_dir.relative_to(root)),
        "plots": sorted(path.name for path in output_dir.glob("*.png")),
    }
    manifest_path = root / "data" / "manifests" / f"{DATASET_ID}_plots.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=[DATASET_ID], help="Dataset identifier to plot.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dataset == DATASET_ID:
        print(json.dumps(run(), indent=2, sort_keys=True))
        return
    raise AssertionError(f"Unhandled dataset: {args.dataset}")


if __name__ == "__main__":
    main()

