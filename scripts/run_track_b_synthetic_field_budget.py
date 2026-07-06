"""Synthetic Track B field-budget stress test.

This test asks how many partial observations per event are needed before missing
measurements can be reconstructed from the event itself. It is a pre-lab design scaffold,
not a chemistry simulation.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from materials_event_modeling.track_b.field_prediction import (
    evaluate_partial_observation_budget,
)
from materials_event_modeling.track_b.synthetic_field import generate_synthetic_event_field

DEFAULT_SEEDS = [17, 29, 41, 53, 67]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    summary_rows = []
    for (strategy, observed_count, model), group in df.groupby(
        ["strategy", "observed_count", "model"], sort=True
    ):
        summary_rows.append(
            {
                "strategy": strategy,
                "observed_count": int(observed_count),
                "model": model,
                "seeds": len(group),
                "mse_mean": float(group["mse"].mean()),
                "mse_std": float(group["mse"].std(ddof=0)),
                "improvement_vs_global_mean_mean": float(
                    group["improvement_vs_global_mean"].mean()
                ),
                "improvement_vs_global_mean_std": float(
                    group["improvement_vs_global_mean"].std(ddof=0)
                ),
                "improvement_vs_event_mean_mean": float(
                    group["improvement_vs_event_mean"].mean()
                ),
                "improvement_vs_event_mean_std": float(
                    group["improvement_vs_event_mean"].std(ddof=0)
                ),
            }
        )
    return summary_rows


def compact_budget_summary(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact = []
    for row in summary_rows:
        if row["model"] not in {"event_mean", "idw_all", "nearest_neighbor"}:
            continue
        compact.append(
            {
                "strategy": row["strategy"],
                "observed_count": row["observed_count"],
                "model": row["model"],
                "mse_mean": row["mse_mean"],
                "improvement_vs_global_mean_mean": row["improvement_vs_global_mean_mean"],
                "improvement_vs_event_mean_mean": row["improvement_vs_event_mean_mean"],
            }
        )
    return compact


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seeds = DEFAULT_SEEDS[: args.seed_count]
    for seed in seeds:
        field = generate_synthetic_event_field(
            n_events=args.events,
            observations_per_event=args.observations_per_event,
            n_theta=args.theta_points,
            seed=seed,
        )
        results = evaluate_partial_observation_budget(
            event_ids=field.event_ids,
            coords=field.coords,
            spectra=field.spectra,
            observed_counts=args.observed_counts,
            random_repeats=args.random_repeats,
            seed=seed + 1000,
        )
        for result in results:
            row = result.__dict__.copy()
            row["seed"] = seed
            rows.append(row)

    summary_rows = summarize(rows)
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "track_b_synthetic_field_budget",
        "events": args.events,
        "observations_per_event": args.observations_per_event,
        "theta_points": args.theta_points,
        "observed_counts": args.observed_counts,
        "random_repeats": args.random_repeats,
        "seeds": seeds,
        "hypotheses": [
            "Event-local observations should predict held-out observations better than a global mean.",
            "Inverse-distance field reconstruction should improve over a flat event mean once enough observations are available.",
            "Space-filling observation should be more stable than random observation at small budgets.",
        ],
        "rows": rows,
        "summary": summary_rows,
        "compact_budget_summary": compact_budget_summary(summary_rows),
        "caveats": [
            "The field coordinates are synthetic proxies for time, spatial position, vial position, or another partial-observation axis.",
            "This test informs pilot design only; it is not evidence about real material-making events.",
            "A real lab pilot must define which partial-observation axis is practical: time points, positions, vials, or modalities.",
        ],
    }

    output_path = project_root() / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=int, default=24)
    parser.add_argument("--observations-per-event", type=int, default=12)
    parser.add_argument("--theta-points", type=int, default=512)
    parser.add_argument("--observed-counts", type=int, nargs="+", default=[1, 2, 3, 4, 6, 8])
    parser.add_argument("--random-repeats", type=int, default=8)
    parser.add_argument("--seed-count", type=int, default=len(DEFAULT_SEEDS))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/track_b_synthetic_field_budget.json"),
    )
    return parser.parse_args()


def main() -> None:
    result = run(parse_args())
    printable = {
        "task": result["task"],
        "hypotheses": result["hypotheses"],
        "compact_budget_summary": result["compact_budget_summary"],
        "caveats": result["caveats"],
    }
    print(json.dumps(printable, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
