"""Run leave-one-source-out transfer diagnostics for opXRD reconstruction."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import numpy as np
from run_opxrd_conv_reconstruction import (
    DATASET_ID,
    ErrorAccumulator,
    build_mask_starts,
    choose_device,
    interpolate_masked_region,
    load_subset,
    predict_masks,
    project_root,
    select_sample_indices,
    train_model,
)


def metric_summary(values: list[float]) -> dict[str, float]:
    return {
        "mean": mean(values),
        "std": pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def add_relative_metrics(metrics: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    train_mean_mse = metrics["train_mean"]["mse"]
    for values in metrics.values():
        values["relative_mse_vs_train_mean"] = values["mse"] / train_mean_mse
        values["mse_improvement_vs_train_mean"] = 1.0 - values["relative_mse_vs_train_mean"]
    return metrics


def evaluate_source(
    *,
    xrd: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    eval_starts: np.ndarray,
    args: argparse.Namespace,
    seed: int,
    source_name: str,
) -> dict[str, Any]:
    device = choose_device(args.device)
    train_mean = xrd[train_idx].mean(axis=0)
    model, losses = train_model(
        x_train=xrd[train_idx],
        mask_width=args.mask_width,
        train_mask_strategy=args.train_mask_strategy,
        prediction_mode=args.prediction_mode,
        peak_top_fraction=args.peak_top_fraction,
        channels=args.channels,
        depth=args.depth,
        dropout=args.dropout,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        observed_loss_weight=args.observed_loss_weight,
        seed=9109 + seed,
        device=device,
    )

    accumulators = {
        "train_mean": ErrorAccumulator(),
        "linear_interpolation": ErrorAccumulator(),
        "masked_conv_reconstructor": ErrorAccumulator(),
    }
    for repeat in range(args.repeats):
        repeat_starts = eval_starts[repeat, test_idx]
        conv_prediction = predict_masks(
            model=model,
            spectra=xrd[test_idx],
            starts=repeat_starts,
            mask_width=args.mask_width,
            prediction_mode=args.prediction_mode,
            batch_size=args.batch_size,
            device=device,
        )
        for local_idx, sample_idx in enumerate(test_idx):
            start = int(repeat_starts[local_idx])
            end = start + args.mask_width
            truth = xrd[sample_idx, start:end]
            accumulators["train_mean"].update(truth, train_mean[start:end])
            accumulators["linear_interpolation"].update(
                truth,
                interpolate_masked_region(xrd[sample_idx], start, end),
            )
            accumulators["masked_conv_reconstructor"].update(
                truth,
                conv_prediction[local_idx, start:end],
            )

    metrics = {name: accumulator.metrics() for name, accumulator in accumulators.items()}
    metrics = add_relative_metrics(metrics)
    return {
        "source": source_name,
        "seed": seed,
        "train_samples": int(train_idx.size),
        "test_samples": int(test_idx.size),
        "metrics": metrics,
        "loss_first": losses[0],
        "loss_last": losses[-1],
    }


def summarize_source_trials(trials: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, list[dict[str, Any]]] = {}
    for trial in trials:
        by_source.setdefault(trial["source"], []).append(trial)

    summary = {}
    for source, source_trials in sorted(by_source.items()):
        conv_mse_improvements = [
            trial["metrics"]["masked_conv_reconstructor"]["mse_improvement_vs_train_mean"]
            for trial in source_trials
        ]
        interpolation_mse_improvements = [
            trial["metrics"]["linear_interpolation"]["mse_improvement_vs_train_mean"]
            for trial in source_trials
        ]
        mse_delta = [
            trial["metrics"]["masked_conv_reconstructor"]["mse"]
            - trial["metrics"]["linear_interpolation"]["mse"]
            for trial in source_trials
        ]
        mae_delta = [
            trial["metrics"]["masked_conv_reconstructor"]["mae"]
            - trial["metrics"]["linear_interpolation"]["mae"]
            for trial in source_trials
        ]
        summary[source] = {
            "trials": len(source_trials),
            "test_samples": source_trials[0]["test_samples"],
            "conv_mse_improvement_vs_train_mean": metric_summary(conv_mse_improvements),
            "interpolation_mse_improvement_vs_train_mean": metric_summary(
                interpolation_mse_improvements
            ),
            "conv_minus_interpolation_mse": metric_summary(mse_delta),
            "conv_minus_interpolation_mae": metric_summary(mae_delta),
            "conv_mse_win_rate_vs_interpolation": sum(delta < 0 for delta in mse_delta)
            / len(mse_delta),
            "conv_mae_win_rate_vs_interpolation": sum(delta < 0 for delta in mae_delta)
            / len(mae_delta),
        }
    return summary


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root()
    device = choose_device(args.device)
    xrd, samples = load_subset(root)
    selected = select_sample_indices(
        samples=samples,
        max_samples=args.max_samples,
        strategy=args.sample_strategy,
        source_balance_alpha=args.source_balance_alpha,
    )
    xrd = xrd[selected]
    samples = samples.iloc[selected].reset_index(drop=True)
    sources = samples["top_level_source"].to_numpy()
    source_counts = samples["top_level_source"].value_counts().sort_index().to_dict()

    eval_starts = build_mask_starts(
        xrd=xrd,
        mask_width=args.mask_width,
        repeats=args.repeats,
        strategy=args.eval_mask_strategy,
        peak_top_fraction=args.peak_top_fraction,
        seed=args.eval_seed,
    )

    trials = []
    for source in sorted(source_counts):
        test_idx = np.flatnonzero(sources == source)
        if test_idx.size < args.min_test_samples:
            print(
                f"skipping source={source} test_samples={test_idx.size} "
                f"< min_test_samples={args.min_test_samples}",
                file=sys.stderr,
            )
            continue
        train_idx = np.flatnonzero(sources != source)
        for seed in args.seeds:
            print(
                f"training leave-one-source-out source={source} "
                f"seed={seed} train={train_idx.size} test={test_idx.size} on {device}",
                file=sys.stderr,
            )
            trials.append(
                evaluate_source(
                    xrd=xrd,
                    train_idx=train_idx,
                    test_idx=test_idx,
                    eval_starts=eval_starts,
                    args=args,
                    seed=seed,
                    source_name=source,
                )
            )

    result = {
        "dataset_id": DATASET_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "opxrd_leave_one_source_transfer",
        "subset": "opxrd_processed_subset",
        "spectra": int(xrd.shape[0]),
        "theta_points": int(xrd.shape[1]),
        "sample_strategy": args.sample_strategy,
        "source_balance_alpha": args.source_balance_alpha,
        "top_level_source_counts": source_counts,
        "min_test_samples": args.min_test_samples,
        "device": str(device),
        "mask_width": args.mask_width,
        "train_mask_strategy": args.train_mask_strategy,
        "eval_mask_strategy": args.eval_mask_strategy,
        "prediction_mode": args.prediction_mode,
        "peak_top_fraction": args.peak_top_fraction,
        "seeds": args.seeds,
        "repeats": args.repeats,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "channels": args.channels,
        "depth": args.depth,
        "dropout": args.dropout,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "observed_loss_weight": args.observed_loss_weight,
        "approximate_receptive_field": int(1 + 4 * sum(2**idx for idx in range(args.depth))),
        "summary": summarize_source_trials(trials),
        "trials": trials,
        "caveats": [
            "This is a transfer diagnostic, not a pretraining benchmark.",
            "Small held-out sources have noisy metrics; use min_test_samples to filter them.",
            "Each source is evaluated after training on every other source only.",
        ],
    }
    output_path = root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="auto", help="auto, cpu, mps, or cuda.")
    parser.add_argument("--max-samples", type=int, default=4096)
    parser.add_argument(
        "--sample-strategy",
        choices=["spread", "source_balanced"],
        default="spread",
    )
    parser.add_argument("--source-balance-alpha", type=float, default=0.5)
    parser.add_argument("--min-test-samples", type=int, default=15)
    parser.add_argument("--mask-width", type=int, default=1024)
    parser.add_argument("--train-mask-strategy", choices=["random", "peak"], default="peak")
    parser.add_argument("--eval-mask-strategy", choices=["random", "peak"], default="peak")
    parser.add_argument("--prediction-mode", choices=["direct", "residual"], default="residual")
    parser.add_argument("--peak-top-fraction", type=float, default=0.02)
    parser.add_argument("--eval-seed", type=int, default=0)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--channels", type=int, default=32)
    parser.add_argument("--depth", type=int, default=10)
    parser.add_argument("--dropout", type=float, default=0.05)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--observed-loss-weight", type=float, default=0.05)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/opxrd_source_transfer.json"),
    )
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
