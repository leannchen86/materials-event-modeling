"""Analyze source-level artifacts in the opXRD pilot subset."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

import numpy as np

from run_opxrd_conv_reconstruction import (
    interpolate_masked_region,
    load_subset,
    peak_mask_starts,
    project_root,
)


def metric_summary(values: list[float]) -> dict[str, float]:
    return {
        "mean": mean(values),
        "median": median(values),
        "std": pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def local_peak_density(spectra: np.ndarray, threshold: float) -> list[float]:
    densities = []
    for spectrum in spectra:
        if spectrum.size < 3:
            densities.append(0.0)
            continue
        peaks = (
            (spectrum[1:-1] > spectrum[:-2])
            & (spectrum[1:-1] >= spectrum[2:])
            & (spectrum[1:-1] >= threshold)
        )
        densities.append(float(np.mean(peaks)))
    return densities


def interpolation_metrics(
    spectra: np.ndarray,
    mask_width: int,
    peak_top_fraction: float,
    seed: int,
) -> dict[str, dict[str, float]]:
    starts = peak_mask_starts(
        xrd=spectra,
        mask_width=mask_width,
        repeats=1,
        peak_top_fraction=peak_top_fraction,
        seed=seed,
    )[0]
    mse_values = []
    mae_values = []
    hidden_mean_values = []
    hidden_std_values = []
    for spectrum, start in zip(spectra, starts):
        end = int(start) + mask_width
        truth = spectrum[int(start) : end]
        prediction = interpolate_masked_region(spectrum, int(start), end)
        diff = prediction - truth
        mse_values.append(float(np.mean(diff * diff)))
        mae_values.append(float(np.mean(np.abs(diff))))
        hidden_mean_values.append(float(np.mean(truth)))
        hidden_std_values.append(float(np.std(truth)))
    return {
        "peak_mask_interpolation_mse": metric_summary(mse_values),
        "peak_mask_interpolation_mae": metric_summary(mae_values),
        "peak_mask_hidden_mean": metric_summary(hidden_mean_values),
        "peak_mask_hidden_std": metric_summary(hidden_std_values),
    }


def transfer_summary_by_source(path: Path) -> dict[str, dict[str, float]]:
    if not path.exists():
        return {}
    manifest = json.loads(path.read_text())
    summary = {}
    for source, values in manifest.get("summary", {}).items():
        summary[source] = {
            "transfer_test_samples": values["test_samples"],
            "transfer_conv_mse_improvement": values[
                "conv_mse_improvement_vs_train_mean"
            ]["mean"],
            "transfer_interpolation_mse_improvement": values[
                "interpolation_mse_improvement_vs_train_mean"
            ]["mean"],
            "transfer_conv_minus_interpolation_mse": values[
                "conv_minus_interpolation_mse"
            ]["mean"],
            "transfer_conv_minus_interpolation_mae": values[
                "conv_minus_interpolation_mae"
            ]["mean"],
            "transfer_mse_win_rate": values["conv_mse_win_rate_vs_interpolation"],
            "transfer_mae_win_rate": values["conv_mae_win_rate_vs_interpolation"],
        }
    return summary


def summarize_source(
    *,
    source: str,
    source_xrd: np.ndarray,
    source_samples: Any,
    args: argparse.Namespace,
    transfer: dict[str, dict[str, float]],
) -> dict[str, Any]:
    span = source_samples["theta_max"] - source_samples["theta_min"]
    positive_fraction = np.mean(source_xrd > args.intensity_threshold, axis=1)
    high_fraction = np.mean(source_xrd > args.high_intensity_threshold, axis=1)
    max_values = np.max(source_xrd, axis=1)
    mean_values = np.mean(source_xrd, axis=1)
    std_values = np.std(source_xrd, axis=1)
    peak_density = local_peak_density(source_xrd, threshold=args.peak_threshold)

    summary: dict[str, Any] = {
        "samples": int(source_xrd.shape[0]),
        "metadata": {
            "labeled_fraction": float(source_samples["is_labeled"].astype(bool).mean()),
            "phase_count": metric_summary(
                [float(value) for value in source_samples["phase_count"].fillna(0)]
            ),
            "points": metric_summary([float(value) for value in source_samples["points"]]),
            "theta_min": metric_summary([float(value) for value in source_samples["theta_min"]]),
            "theta_max": metric_summary([float(value) for value in source_samples["theta_max"]]),
            "theta_span": metric_summary([float(value) for value in span]),
            "raw_intensity_max": metric_summary(
                [float(value) for value in source_samples["intensity_max"]]
            ),
        },
        "processed_spectrum": {
            "mean_intensity": metric_summary([float(value) for value in mean_values]),
            "std_intensity": metric_summary([float(value) for value in std_values]),
            "max_intensity": metric_summary([float(value) for value in max_values]),
            "fraction_above_threshold": metric_summary(
                [float(value) for value in positive_fraction]
            ),
            "fraction_above_high_threshold": metric_summary(
                [float(value) for value in high_fraction]
            ),
            "local_peak_density": metric_summary(peak_density),
        },
        "interpolation": interpolation_metrics(
            source_xrd,
            mask_width=args.mask_width,
            peak_top_fraction=args.peak_top_fraction,
            seed=args.seed,
        ),
    }
    if source in transfer:
        summary["prior_source_transfer"] = transfer[source]
    return summary


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root()
    xrd, samples = load_subset(root)
    transfer = transfer_summary_by_source(root / args.source_transfer_manifest)
    sources = samples["top_level_source"].to_numpy()
    source_summaries = {}
    for source in sorted(samples["top_level_source"].unique()):
        source_mask = sources == source
        source_summaries[source] = summarize_source(
            source=source,
            source_xrd=xrd[source_mask],
            source_samples=samples.loc[source_mask],
            args=args,
            transfer=transfer,
        )

    result = {
        "dataset_id": "opxrd",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "opxrd_source_diagnostics",
        "spectra": int(xrd.shape[0]),
        "theta_points": int(xrd.shape[1]),
        "mask_width": args.mask_width,
        "peak_top_fraction": args.peak_top_fraction,
        "seed": args.seed,
        "intensity_threshold": args.intensity_threshold,
        "high_intensity_threshold": args.high_intensity_threshold,
        "peak_threshold": args.peak_threshold,
        "source_transfer_manifest": str(args.source_transfer_manifest),
        "sources": source_summaries,
        "caveats": [
            "This is an artifact diagnostic, not a model benchmark.",
            "Small sources have noisy statistics.",
            "The processed spectra were normalized per pattern during preprocessing.",
        ],
    }
    output_path = root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mask-width", type=int, default=1024)
    parser.add_argument("--peak-top-fraction", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--intensity-threshold", type=float, default=0.01)
    parser.add_argument("--high-intensity-threshold", type=float, default=0.25)
    parser.add_argument("--peak-threshold", type=float, default=0.05)
    parser.add_argument(
        "--source-transfer-manifest",
        type=Path,
        default=Path("data/manifests/opxrd_source_transfer_a100.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/opxrd_source_diagnostics.json"),
    )
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
