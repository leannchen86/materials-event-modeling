"""Run a small sample-size and seed curve for the opXRD CNN reconstructor."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


SCRIPT_NAME = "scripts/run_opxrd_conv_reconstruction.py"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def metric_summary(values: list[float]) -> dict[str, float]:
    return {
        "mean": mean(values),
        "std": pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def run_single(
    *,
    root: Path,
    max_samples: int,
    seed: int,
    args: argparse.Namespace,
    output_path: Path,
) -> dict[str, Any]:
    command = [
        sys.executable,
        SCRIPT_NAME,
        "--max-samples",
        str(max_samples),
        "--mask-width",
        str(args.mask_width),
        "--train-mask-strategy",
        args.train_mask_strategy,
        "--eval-mask-strategy",
        args.eval_mask_strategy,
        "--epochs",
        str(args.epochs),
        "--batch-size",
        str(args.batch_size),
        "--channels",
        str(args.channels),
        "--depth",
        str(args.depth),
        "--n-splits",
        str(args.n_splits),
        "--device",
        args.device,
        "--peak-top-fraction",
        str(args.peak_top_fraction),
        "--repeats",
        str(args.repeats),
        "--learning-rate",
        str(args.learning_rate),
        "--weight-decay",
        str(args.weight_decay),
        "--observed-loss-weight",
        str(args.observed_loss_weight),
        "--seed",
        str(seed),
        "--output",
        str(output_path.relative_to(root)),
        "--split-kinds",
        *args.split_kinds,
    ]
    print(f"running max_samples={max_samples} seed={seed}", file=sys.stderr)
    subprocess.run(command, cwd=root, check=True, stdout=subprocess.DEVNULL)
    return json.loads(output_path.read_text())


def summarize_trials(trials: list[dict[str, Any]]) -> dict[str, Any]:
    by_sample: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for trial in trials:
        by_sample[int(trial["max_samples"])].append(trial)

    sample_summaries = {}
    for max_samples, sample_trials in sorted(by_sample.items()):
        split_names = sorted(sample_trials[0]["splits"])
        split_summaries = {}
        for split_name in split_names:
            conv_mse_improvements = [
                trial["splits"][split_name]["masked_conv_reconstructor"][
                    "mse_improvement_vs_train_mean"
                ]
                for trial in sample_trials
            ]
            interpolation_mse_improvements = [
                trial["splits"][split_name]["linear_interpolation"][
                    "mse_improvement_vs_train_mean"
                ]
                for trial in sample_trials
            ]
            conv_mse = [
                trial["splits"][split_name]["masked_conv_reconstructor"]["mse"]
                for trial in sample_trials
            ]
            interpolation_mse = [
                trial["splits"][split_name]["linear_interpolation"]["mse"]
                for trial in sample_trials
            ]
            conv_mae = [
                trial["splits"][split_name]["masked_conv_reconstructor"]["mae"]
                for trial in sample_trials
            ]
            interpolation_mae = [
                trial["splits"][split_name]["linear_interpolation"]["mae"]
                for trial in sample_trials
            ]
            mse_delta = [conv - interp for conv, interp in zip(conv_mse, interpolation_mse)]
            mae_delta = [conv - interp for conv, interp in zip(conv_mae, interpolation_mae)]
            split_summaries[split_name] = {
                "trials": len(sample_trials),
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
        sample_summaries[str(max_samples)] = split_summaries
    return sample_summaries


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root()
    trial_dir = root / "data" / "interim" / "opxrd" / "conv_scaling_runs"
    trial_dir.mkdir(parents=True, exist_ok=True)

    trials = []
    for max_samples in args.sample_sizes:
        for seed in args.seeds:
            output_path = trial_dir / f"sample_{max_samples}_seed_{seed}.json"
            result = run_single(
                root=root,
                max_samples=max_samples,
                seed=seed,
                args=args,
                output_path=output_path,
            )
            result["max_samples"] = max_samples
            result["seed"] = seed
            result["trial_path"] = str(output_path.relative_to(root))
            trials.append(result)

    summary = {
        "dataset_id": "opxrd",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "masked_xrd_conv_scaling",
        "sample_sizes": args.sample_sizes,
        "seeds": args.seeds,
        "mask_width": args.mask_width,
        "train_mask_strategy": args.train_mask_strategy,
        "eval_mask_strategy": args.eval_mask_strategy,
        "peak_top_fraction": args.peak_top_fraction,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "channels": args.channels,
        "depth": args.depth,
        "n_splits": args.n_splits,
        "split_kinds": args.split_kinds,
        "summary": summarize_trials(trials),
        "trials": [
            {
                "max_samples": trial["max_samples"],
                "seed": trial["seed"],
                "trial_path": trial["trial_path"],
                "splits": trial["splits"],
            }
            for trial in trials
        ],
        "caveats": [
            "This is a modest local replication curve, not full opXRD pretraining.",
            "The main success criterion is whether CNN MSE beats interpolation under peak masks and source shift.",
            "MAE is tracked separately because interpolation may still win on average absolute error.",
        ],
    }
    output_path = root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-sizes", type=int, nargs="+", default=[256, 512])
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--device", default="auto")
    parser.add_argument("--mask-width", type=int, default=1024)
    parser.add_argument("--train-mask-strategy", choices=["random", "peak"], default="peak")
    parser.add_argument("--eval-mask-strategy", choices=["random", "peak"], default="peak")
    parser.add_argument("--peak-top-fraction", type=float, default=0.02)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--n-splits", type=int, default=3)
    parser.add_argument(
        "--split-kinds",
        nargs="+",
        choices=["random_kfold", "held_out_top_level_source"],
        default=["random_kfold", "held_out_top_level_source"],
    )
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--channels", type=int, default=32)
    parser.add_argument("--depth", type=int, default=10)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--observed-loss-weight", type=float, default=0.05)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/opxrd_masked_xrd_conv_scaling.json"),
    )
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
