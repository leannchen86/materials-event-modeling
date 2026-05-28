"""Summarize Track B mock event records."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def summarize(path: Path) -> dict[str, object]:
    events = json.loads(path.read_text())
    labels = Counter()
    batches = Counter()
    missing_fields = Counter()
    measurement_counts = Counter()
    for event in events:
        batches[event.get("batch_id") or "missing_batch"] += 1
        for label in event["labels"]["human_labels"]:
            labels[label["label"]] += 1
        for field in event["data_quality"]["missing_fields"]:
            missing_fields[field] += 1
        for measurement_type, values in event["measurements"].items():
            measurement_counts[measurement_type] += len(values)

    return {
        "events": len(events),
        "batches": dict(sorted(batches.items())),
        "labels_as_probes": dict(sorted(labels.items())),
        "missing_fields": dict(sorted(missing_fields.items())),
        "measurement_files": dict(sorted(measurement_counts.items())),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path("examples/track_b/calcium_carbonate_mock_events.json"),
    )
    return parser.parse_args()


def main() -> None:
    print(json.dumps(summarize(parse_args().path), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
