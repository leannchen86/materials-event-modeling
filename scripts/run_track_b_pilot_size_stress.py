"""Stress-test Track B pilot sizes on the synthetic event scaffold.

This is not chemistry evidence. It asks a pre-lab design question: which small pilot
shapes are large and rich enough for the Track B analyses to produce stable signals?
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from materials_event_modeling.track_b.eval import evaluate_synthetic_track_b
from materials_event_modeling.track_b.synthetic import generate_synthetic_track_b


DEFAULT_CONFIGS = [
    {"name": "12_one_shot_12x1", "groups": 12, "replicates_per_group": 1},
    {"name": "12_replicated_6x2", "groups": 6, "replicates_per_group": 2},
    {"name": "24_one_shot_24x1", "groups": 24, "replicates_per_group": 1},
    {"name": "24_replicated_8x3", "groups": 8, "replicates_per_group": 3},
    {"name": "48_one_shot_48x1", "groups": 48, "replicates_per_group": 1},
    {"name": "48_replicated_16x3", "groups": 16, "replicates_per_group": 3},
    {"name": "48_rich_replicates_12x4", "groups": 12, "replicates_per_group": 4},
    {"name": "96_replicated_32x3", "groups": 32, "replicates_per_group": 3},
    {"name": "96_rich_replicates_24x4", "groups": 24, "replicates_per_group": 4},
]


DEFAULT_SEEDS = [17, 29, 41, 53, 67]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def scalar(value: object) -> float:
    return float(value) if value is not None else float("nan")


def extract_metrics(config: dict[str, Any], seed: int, evaluation: dict[str, Any]) -> dict[str, Any]:
    prediction = evaluation["prediction"]
    retrieval = evaluation["replicate_retrieval_hit_rate"]
    projection = evaluation["label_projection_audit"]
    silhouette = evaluation["spectral_silhouette"]
    missingness = evaluation["missingness"]
    event_count = int(evaluation["event_count"])

    label_improvement = scalar(prediction["label_only"]["mse_improvement_vs_train_mean"])
    planned_improvement = scalar(
        prediction["planned_conditions"]["mse_improvement_vs_train_mean"]
    )
    observed_improvement = scalar(
        prediction["observed_trajectory"]["mse_improvement_vs_train_mean"]
    )
    full_improvement = scalar(prediction["full_event"]["mse_improvement_vs_train_mean"])
    best_event_improvement = max(planned_improvement, observed_improvement, full_improvement)

    return {
        "config": config["name"],
        "seed": seed,
        "event_count": event_count,
        "planned_condition_count": int(config["groups"]),
        "replicates_per_group": int(config["replicates_per_group"]),
        "label_mse_improvement": label_improvement,
        "planned_mse_improvement": planned_improvement,
        "observed_mse_improvement": observed_improvement,
        "full_event_mse_improvement": full_improvement,
        "best_event_mse_improvement": best_event_improvement,
        "best_event_gain_over_label": best_event_improvement - label_improvement,
        "planned_gain_over_label": planned_improvement - label_improvement,
        "observed_gain_over_label": observed_improvement - label_improvement,
        "full_event_gain_over_label": full_improvement - label_improvement,
        "label_retrieval_hit_rate": scalar(retrieval["label_only"]),
        "planned_retrieval_hit_rate": scalar(retrieval["planned_conditions"]),
        "observed_retrieval_hit_rate": scalar(retrieval["observed_trajectory"]),
        "full_event_retrieval_hit_rate": scalar(retrieval["full_event"]),
        "raw_measurement_pca_retrieval_hit_rate": scalar(retrieval["raw_measurement_pca"]),
        "labels_that_split_count": int(len(projection["labels_that_split"])),
        "mean_hidden_regime_entropy_per_label": scalar(
            projection["mean_hidden_regime_entropy_per_label"]
        ),
        "legacy_label_silhouette": scalar(silhouette["legacy_label"]),
        "hidden_regime_silhouette": scalar(silhouette["hidden_regime"]),
        "silhouette_gap_hidden_minus_label": (
            scalar(silhouette["hidden_regime"]) - scalar(silhouette["legacy_label"])
        ),
        "missing_final_ph_rate": int(missingness.get("final_ph", 0)) / event_count,
        "missing_early_turbidity_rate": int(missingness.get("early_turbidity", 0)) / event_count,
    }


def mean_std_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    metric_columns = [
        column
        for column in df.columns
        if column
        not in {
            "config",
            "seed",
            "event_count",
            "planned_condition_count",
            "replicates_per_group",
        }
    ]
    summary_rows = []
    for config, config_df in df.groupby("config", sort=False):
        first = config_df.iloc[0]
        summary: dict[str, Any] = {
            "config": config,
            "event_count": int(first["event_count"]),
            "planned_condition_count": int(first["planned_condition_count"]),
            "replicates_per_group": int(first["replicates_per_group"]),
            "seeds": int(len(config_df)),
        }
        for column in metric_columns:
            values = config_df[column].astype(float)
            summary[f"{column}_mean"] = float(values.mean())
            summary[f"{column}_std"] = float(values.std(ddof=0))
        summary["best_event_gain_positive_rate"] = float(
            (config_df["best_event_gain_over_label"] > 0).mean()
        )
        summary["planned_retrieval_useful"] = bool(
            int(first["replicates_per_group"]) > 1
            and float(config_df["planned_retrieval_hit_rate"].mean()) > 0.5
        )
        summary_rows.append(summary)
    return summary_rows


def select_candidate_configs(summary_rows: list[dict[str, Any]]) -> list[str]:
    candidates = []
    for row in summary_rows:
        if row["replicates_per_group"] <= 1:
            continue
        if row["best_event_gain_positive_rate"] < 0.8:
            continue
        if row["planned_retrieval_hit_rate_mean"] < 0.5:
            continue
        if row["labels_that_split_count_mean"] < 2.0:
            continue
        candidates.append(str(row["config"]))
    return candidates


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    configs = DEFAULT_CONFIGS
    seeds = DEFAULT_SEEDS[: args.seed_count]

    for config in configs:
        for seed in seeds:
            dataset = generate_synthetic_track_b(
                n_groups=int(config["groups"]),
                replicates_per_group=int(config["replicates_per_group"]),
                n_theta=args.theta_points,
                seed=seed,
            )
            evaluation = evaluate_synthetic_track_b(dataset.event_table, dataset.spectra)
            rows.append(extract_metrics(config, seed, evaluation))

    summary = mean_std_summary(rows)
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "track_b_pilot_size_stress",
        "theta_points": args.theta_points,
        "seeds": seeds,
        "hypotheses": [
            "Event/process features should usually beat label-only features on held-out synthetic spectrum prediction.",
            "Replicated pilot designs should unlock replicate retrieval; one-shot designs cannot test it.",
            "Very small pilots should be unstable, especially for label projection and event-over-label gains.",
            "At fixed event count, richer replicated events may be more useful for Track B than more one-shot planned conditions, even if prediction alone does not monotonically improve.",
        ],
        "rows": rows,
        "summary": summary,
        "candidate_pilot_shapes": select_candidate_configs(summary),
        "caveats": [
            "Synthetic hidden regimes are known only because this is a scaffold test.",
            "This is a pilot-design stress test, not evidence about real calcium carbonate chemistry.",
            "The purpose is to decide what offline/lab data shape is worth collecting next.",
        ],
    }

    output_path = project_root() / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theta-points", type=int, default=512)
    parser.add_argument("--seed-count", type=int, default=len(DEFAULT_SEEDS))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/track_b_pilot_size_stress.json"),
    )
    return parser.parse_args()


def main() -> None:
    result = run(parse_args())
    printable = {
        "task": result["task"],
        "hypotheses": result["hypotheses"],
        "summary": result["summary"],
        "candidate_pilot_shapes": result["candidate_pilot_shapes"],
        "caveats": result["caveats"],
    }
    print(json.dumps(printable, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
