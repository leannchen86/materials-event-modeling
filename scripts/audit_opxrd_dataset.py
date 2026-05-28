"""Audit the opXRD archive without unpacking it."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from materials_event_modeling.data.opxrd import (
    DATASET_ID,
    archive_inventory,
    iter_patterns_from_archive,
    raw_archive_path,
    summarize_patterns,
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def audit(max_patterns: int | None) -> dict[str, object]:
    root = project_root()
    archive_path = raw_archive_path(root)
    if not archive_path.exists():
        raise FileNotFoundError(
            f"Missing {archive_path}. Run `python3 scripts/download_data.py opxrd` first."
        )

    inventory = archive_inventory(archive_path)
    pattern_summary = summarize_patterns(
        iter_patterns_from_archive(archive_path, limit=max_patterns)
    )
    return {
        "dataset_id": DATASET_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "max_patterns": max_patterns,
        "archive": inventory,
        "patterns": pattern_summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-patterns",
        type=int,
        default=5000,
        help="Maximum parsed pattern JSON files to inspect. Use 0 for all.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/opxrd_audit.json"),
        help="Path for the JSON audit summary.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = project_root()
    max_patterns = None if args.max_patterns == 0 else args.max_patterns
    summary = audit(max_patterns=max_patterns)
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
