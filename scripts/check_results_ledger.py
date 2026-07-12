#!/usr/bin/env python3
"""Invalidation hook for docs/spine/results_ledger.json.

The ledger is the single source of truth for load-bearing headline numbers.
Each entry either points into a run manifest (source.kind == "manifest") or
carries a by_construction / literal value. This script:

  1. HARD CHECK (exit 1 on failure): resolve every declared pointer/display pair
     in a manifest-sourced entry (primary, family companion, and confidence
     interval where present) and compare at displayed precision.

  2. ADVISORY (report only, never fails): check that each cited document contains
     the primary display string. Prose-number collisions make this a hint, not an
     invariant.

Usage:
  python scripts/check_results_ledger.py            # check
  python scripts/check_results_ledger.py --list     # print the denormalization map
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "docs/spine/results_ledger.json"


def resolve(obj: object, pointer: str) -> object:
    """Walk a dotted JSON pointer with optional [i] list indices."""
    cur = obj
    for part in re.findall(r"[^.\[\]]+", pointer):
        if isinstance(cur, list):
            cur = cur[int(part)]
        elif isinstance(cur, dict):
            cur = cur[part]
        else:
            raise KeyError(f"cannot descend into {type(cur).__name__} at {part!r}")
    return cur


POINTER_DISPLAY_PAIRS = (
    ("pointer", "display"),
    ("family_pointer", "family_display"),
    ("ci_pointer", "ci95_display"),
)


def display_matches(canonical: object, shown: str) -> bool:
    """Do scalar/list values round-match every number rendered in ``shown``?"""
    shown_numbers = re.findall(r"-?\d+\.?\d*", shown)
    canonical_values = canonical if isinstance(canonical, list) else [canonical]
    if len(shown_numbers) != len(canonical_values):
        return False
    for value, rendered in zip(canonical_values, shown_numbers, strict=True):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        decimals = len(rendered.split(".")[1]) if "." in rendered else 0
        if round(float(value), decimals) != float(rendered):
            return False
    return True


def load_entries() -> dict:
    ledger = json.loads(LEDGER.read_text())
    return {k: v for k, v in ledger.items() if not k.startswith("_")}


def cmd_check(entries: dict) -> int:
    hard_failures: list[str] = []
    advisories: list[str] = []
    manifest_cache: dict[str, object] = {}

    for key, e in entries.items():
        src = e["source"]
        kind = src["kind"]

        if kind == "manifest":
            mpath = src["manifest"]
            if mpath not in manifest_cache:
                manifest_cache[mpath] = json.loads((REPO / mpath).read_text())
            manifest = manifest_cache[mpath]
            for pointer_key, display_key in POINTER_DISPLAY_PAIRS:
                if pointer_key not in src:
                    continue
                if display_key not in e:
                    hard_failures.append(
                        f"[{key}] source declares {pointer_key} but entry lacks {display_key}"
                    )
                    continue
                try:
                    canonical = resolve(manifest, src[pointer_key])
                except (KeyError, IndexError) as exc:
                    hard_failures.append(
                        f"[{key}] pointer {src[pointer_key]!r} does not resolve in {mpath}: {exc}"
                    )
                    continue
                if not display_matches(canonical, e[display_key]):
                    worklist = "\n      - ".join(e["cited_in"])
                    hard_failures.append(
                        f"[{key}] STALE: manifest value {canonical} != ledger "
                        f"{display_key} {e[display_key]!r}.\n"
                        f"    Update the ledger and these docs:\n      - {worklist}"
                    )
        elif kind == "literal" and src.get("pointer_todo"):
            advisories.append(f"[{key}] literal with pointer_todo -- pin a manifest pointer and convert to kind:manifest.")

        for doc in e["cited_in"]:
            p = REPO / doc
            if not p.exists():
                advisories.append(f"[{key}] cited_in doc missing on disk: {doc}")
                continue
            if e["display"] not in p.read_text():
                advisories.append(
                    f"[{key}] display {e['display']!r} not found in cited doc {doc} "
                    f"(prose may paraphrase, or the citation is stale)."
                )

    if advisories:
        print("ADVISORIES (non-failing):")
        for a in advisories:
            print("  -", a)
        print()

    if hard_failures:
        print("LEDGER CHECK FAILED:\n")
        for f in hard_failures:
            print("  -", f)
        print(f"\n{len(hard_failures)} hard failure(s). The ledger and the docs above have drifted "
              f"from the manifests. Fix, then re-run.")
        return 1

    print(f"Ledger OK: {len(entries)} entries consistent with their manifests.")
    return 0


def cmd_list(entries: dict) -> int:
    """Print the denormalization map: number -> where it is cited."""
    for key, e in entries.items():
        print(f"\n{key}  =  {e['display']}   ({e['robustness']})")
        print(f"    {e['metric']}")
        src = e["source"]
        if src["kind"] == "manifest":
            print(f"    source: {src['manifest']} :: {src['pointer']}")
        else:
            print(f"    source: {src['kind']}")
        print(f"    cited in {len(e['cited_in'])} docs: {', '.join(Path(d).name for d in e['cited_in'])}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="print the denormalization map instead of checking")
    args = ap.parse_args()
    entries = load_entries()
    return cmd_list(entries) if args.list else cmd_check(entries)


if __name__ == "__main__":
    sys.exit(main())
