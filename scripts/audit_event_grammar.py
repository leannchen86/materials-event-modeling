"""Grade an event-grammar dataset on the L0-L3 conformance ladder.

Loads events (a JSON array, a single event, or a directory of JSON files),
runs the conformance checks from ``materials_event_modeling.grammar``, prints
the graded report, and writes a manifest with run identity.

    .venv/bin/python scripts/audit_event_grammar.py \
        --events data/interim/event_grammar_v1/<dataset>/events.json \
        --dataset <dataset>
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from materials_event_modeling.grammar import conformance_report
from materials_event_modeling.run_identity import run_identity
from materials_event_modeling.track_b.event_ingest import load_event_records


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def print_report(report: dict) -> None:
    print(
        f"\nEvent-grammar conformance — {report.get('dataset', '?')}  "
        f"({report['event_count']} events)\n"
    )
    for name, level in report["levels"].items():
        marker = "PASS" if level["passed"] else "FAIL"
        failed = [k for k, ok in level["checks"].items() if not ok]
        detail = "" if level["passed"] else f"  failed: {', '.join(failed)}"
        print(f"  {name:<32}{marker}{detail}")
    richness = report["levels"]["l0_raw_trace"]["trace_richness"]
    print(
        f"\n  level: {report['level']} ({report['level_name']})   "
        f"median obs/event: {richness['median_observations_per_event']}, "
        f"multi-obs fraction: {richness['multi_observation_fraction']}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True,
                        help="Events JSON file or directory of JSON files.")
    parser.add_argument("--dataset", type=str, default=None,
                        help="Dataset id for the report/manifest name.")
    parser.add_argument("--output", type=Path, default=None,
                        help="Default: data/manifests/event_grammar_conformance_<dataset>.json")
    args = parser.parse_args()

    events_path = args.events if args.events.is_absolute() else project_root() / args.events
    events = load_event_records(events_path)
    dataset = args.dataset or events_path.stem

    report = conformance_report(events)
    report["dataset"] = dataset
    report["events_path"] = str(args.events)
    report["created_at"] = datetime.now(timezone.utc).isoformat()
    report["run_identity"] = run_identity()

    print_report(report)

    rel = args.output or Path(f"data/manifests/event_grammar_conformance_{dataset}.json")
    output = Path(rel) if Path(rel).is_absolute() else project_root() / rel
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    try:
        shown = output.relative_to(project_root())
    except ValueError:
        shown = output
    print(f"  wrote {shown}\n")


if __name__ == "__main__":
    main()
