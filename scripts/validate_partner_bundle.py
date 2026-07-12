#!/usr/bin/env python3
"""Validate a partner collection bundle and print a strict JSON report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from materials_event_modeling.partner.bundle import READINESS_LEVELS, validate_partner_bundle
from materials_event_modeling.run_identity import run_identity


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundle",
        type=Path,
        help="Bundle-index JSON file or directory containing one partner_bundle.v1 index",
    )
    parser.add_argument(
        "--schema-dir",
        type=Path,
        default=None,
        help="Schema directory (defaults to the repository schemas directory)",
    )
    parser.add_argument(
        "--readiness",
        choices=READINESS_LEVELS,
        default=None,
        help="Readiness gate to enforce (defaults to the gate implied by bundle purpose)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = validate_partner_bundle(
        args.bundle,
        schema_dir=args.schema_dir,
        readiness=args.readiness,
    )
    report["run_identity"] = run_identity(
        {
            "validator": "partner_bundle.v1",
            "bundle_argument": str(args.bundle),
            "requested_readiness": args.readiness,
        }
    )
    json.dump(report, sys.stdout, allow_nan=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
