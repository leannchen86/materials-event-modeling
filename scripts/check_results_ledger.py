#!/usr/bin/env python3
"""Invalidation hook for docs/spine/results_ledger.json.

The ledger is the single source of truth for load-bearing headline numbers.
Each entry either points into a run manifest (source.kind == "manifest") or
carries a by_construction / literal value. This script:

  1. HARD CHECK (exit 1 on failure): for every manifest-sourced entry, resolve
     the JSON pointer in the live manifest, round it to the ledger's displayed
     precision, and assert it matches the ledger 'display'. This is what catches
     a re-run that silently moved a number: the manifest changes, the ledger no
     longer matches, and the check fails -- listing every doc in 'cited_in' as
     the propagation worklist.

  2. ADVISORY (report only, never fails): for every entry, check that each doc in
     'cited_in' actually contains the display string, and flag docs that contain
     the string but are NOT declared in 'cited_in' (undeclared duplication).
     Advisory because prose numbers collide (0.73 as many different facts), so a
     fuzzy text match is a hint, not an invariant.

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


def display_matches(canonical: float, shown: str) -> bool:
    """Does the ledger's display string round-match the live manifest value?"""
    nums = re.findall(r"-?\d+\.?\d*", shown)
    if not nums:
        return False
    shown_num = nums[0]
    decimals = len(shown_num.split(".")[1]) if "." in shown_num else 0
    return round(canonical, decimals) == float(shown_num)


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
            try:
                canonical = resolve(manifest, src["pointer"])
            except (KeyError, IndexError) as exc:
                hard_failures.append(
                    f"[{key}] pointer {src['pointer']!r} does not resolve in {mpath}: {exc}"
                )
                continue
            if not isinstance(canonical, (int, float)):
                hard_failures.append(
                    f"[{key}] pointer {src['pointer']!r} resolved to non-numeric {canonical!r}"
                )
                continue
            if not display_matches(float(canonical), e["display"]):
                worklist = "\n      - ".join(e["cited_in"])
                hard_failures.append(
                    f"[{key}] STALE: manifest value {canonical} != ledger display {e['display']!r}.\n"
                    f"    Update the ledger and these docs:\n      - {worklist}"
                )
        elif kind == "literal" and src.get("pointer_todo"):
            advisories.append(f"[{key}] literal with pointer_todo -- pin a manifest pointer and convert to kind:manifest.")

        # Advisory: does each cited doc actually contain the display string?
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
