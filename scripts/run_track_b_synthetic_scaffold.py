"""Generate and evaluate a synthetic Track B event scaffold."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from materials_event_modeling.track_b.eval import evaluate_synthetic_track_b
from materials_event_modeling.track_b.synthetic import generate_synthetic_track_b


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run(args: argparse.Namespace) -> dict[str, object]:
    dataset = generate_synthetic_track_b(
        n_groups=args.groups,
        replicates_per_group=args.replicates_per_group,
        n_theta=args.theta_points,
        seed=args.seed,
    )
    evaluation = evaluate_synthetic_track_b(dataset.event_table, dataset.spectra)
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "track_b_synthetic_event_scaffold",
        "seed": args.seed,
        "groups": args.groups,
        "replicates_per_group": args.replicates_per_group,
        "theta_points": args.theta_points,
        "hypotheses": [
            "Event-process features should predict held-out synthetic spectra better than label-only features.",
            "Replicate retrieval should improve when using event-process or raw-measurement features instead of labels alone.",
            "Legacy labels should split across multiple hidden regimes, showing that labels are lossy projections in this synthetic world.",
        ],
        "evaluation": evaluation,
        "caveats": [
            "Synthetic hidden regimes are known only because this is a scaffold test.",
            "This is not evidence about calcium carbonate chemistry.",
            "The purpose is to test Track B analysis logic before real lab data exists.",
        ],
    }

    output_path = project_root() / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    if args.events_output is not None:
        events_path = project_root() / args.events_output
        events_path.parent.mkdir(parents=True, exist_ok=True)
        serializable_events = {
            "theta": dataset.theta.tolist(),
            "events": dataset.events,
            "event_table": dataset.event_table.to_dict(orient="records"),
            "spectra": np.round(dataset.spectra, 5).tolist(),
        }
        events_path.write_text(json.dumps(serializable_events, indent=2, sort_keys=True) + "\n")

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", type=int, default=32)
    parser.add_argument("--replicates-per-group", type=int, default=3)
    parser.add_argument("--theta-points", type=int, default=512)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/track_b_synthetic_event_scaffold.json"),
    )
    parser.add_argument(
        "--events-output",
        type=Path,
        default=None,
        help="Optional path for the generated synthetic event dataset.",
    )
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
