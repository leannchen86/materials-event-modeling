"""Audit Track B material-making event records for event-native learning readiness."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from materials_event_modeling.track_b.event_ingest import audit_events, load_event_records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path("examples/track_b/calcium_carbonate_mock_events.json"),
        help="Event JSON file, JSON array, or directory of JSON files.",
    )
    parser.add_argument(
        "--file-base-dir",
        type=Path,
        default=None,
        help="Optional base directory for checking referenced raw files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/track_b_event_dataset_audit.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    events = load_event_records(args.path)
    audit = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "track_b_event_dataset_audit",
        "source": str(args.path),
        **audit_events(events, file_base_dir=args.file_base_dir),
    }
    output_path = Path(__file__).resolve().parents[1] / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
