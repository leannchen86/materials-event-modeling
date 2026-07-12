"""Generate the controlled pilot's 48-event assignment table — and certify the design.

Implements the counterbalancing scheme of docs/controlled-collection/pilot_design_prereg.md
deterministically from a committed seed, asserts every design constraint, then builds
skeleton grammar-v1 events from the table and runs the REAL conformance checks on them:
the L3 counterbalancing check must pass on the design itself, before any chemistry. (L2 is
earned during collection — it requires actually retaining failures — so the certification
reports L0/L1/L3 structure and states L2 as a collection obligation, not a design property.)

Outputs:
  docs/controlled-collection/pilot_assignment.csv   (the lab-facing table)
  data/manifests/pilot_assignment.json              (table + certification + run identity)
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from materials_event_modeling.grammar.conformance import check_l0, check_l1, check_l3
from materials_event_modeling.grammar.event import parse_event
from materials_event_modeling.run_identity import run_identity

SEED = 20260709  # committed; changing it is a design change and needs a new prereg commit

FACTORS = {
    "concentration_m": (0.1, 0.5),
    "temperature_c": (22.0, 40.0),
    "mg_ratio": (0.0, 0.2),
    "mixing_route": ("fast_no_aging", "slow_30min_aging"),
}
N_SESSIONS = 4
N_REPLICATES = 3
OPERATORS = ("O1", "O2")
LOTS = ("L1", "L2")


def build_rows() -> list[dict]:
    rng = np.random.default_rng(SEED)
    conditions = []
    for c in range(16):
        bits = [(c >> b) & 1 for b in range(4)]
        conditions.append({name: FACTORS[name][bit]
                           for name, bit in zip(FACTORS, bits, strict=True)})

    rows = []
    for c, planned in enumerate(conditions):
        for r in range(N_REPLICATES):
            rows.append({
                "event_id": f"pilot:c{c:02d}:r{r + 1}",
                "condition": c,
                "replicate": r + 1,
                **planned,
                # Cyclic Latin rectangle: every pair of replicates is cross-session.
                "session": f"D{(c + r) % N_SESSIONS + 1}",
                # Operator/lot must NOT derive from (c + r): that is the session index,
                # and reusing it confounds the axes (the first draft did exactly this and
                # the constraint assertions below caught it — all-O1 sessions). (c//4 + r)
                # varies within a condition and is orthogonal enough to (c + r) mod 4 to
                # balance 6/6 within every session; lot adds c so it half-agrees with
                # operator instead of duplicating it.
                "operator": OPERATORS[(c // 4 + r) % 2],
                "lot": LOTS[(c // 4 + r + c) % 2],
            })
    # Run order: independent shuffle within each session.
    by_session: dict[str, list[dict]] = {}
    for row in rows:
        by_session.setdefault(row["session"], []).append(row)
    for session_rows in by_session.values():
        order = rng.permutation(len(session_rows))
        for slot, idx in enumerate(order):
            session_rows[idx]["run_order"] = slot + 1
    return rows


def assert_constraints(rows: list[dict]) -> dict:
    by_condition: dict[int, list[dict]] = {}
    by_session: dict[str, list[dict]] = {}
    for row in rows:
        by_condition.setdefault(row["condition"], []).append(row)
        by_session.setdefault(row["session"], []).append(row)

    assert len(rows) == 48 and len(by_condition) == 16 and len(by_session) == N_SESSIONS
    for session_rows in by_session.values():
        assert len(session_rows) == 12, "each session hosts exactly 12 events"
    for reps in by_condition.values():
        assert len({r["session"] for r in reps}) == 3, "3 replicates on 3 distinct sessions"
        assert len({r["operator"] for r in reps}) == 2, "each condition sees both operators"
        assert len({r["lot"] for r in reps}) == 2, "each condition sees both lots"
    op_balance = {s: sorted(r["operator"] for r in v) for s, v in by_session.items()}
    for s, ops in op_balance.items():
        assert 4 <= ops.count("O1") <= 8, f"session {s} operator balance broke: {ops}"
    lot_balance = {s: sorted(r["lot"] for r in v) for s, v in by_session.items()}
    for s, lots in lot_balance.items():
        assert 4 <= lots.count("L1") <= 8, f"session {s} lot balance broke: {lots}"
    agree = sum(1 for r in rows if (r["operator"] == "O1") == (r["lot"] == "L1")) / len(rows)
    assert 0.25 <= agree <= 0.75, f"operator and lot are near-duplicates (agreement {agree})"
    return {
        "events": len(rows),
        "conditions": len(by_condition),
        "sessions": {s: len(v) for s, v in sorted(by_session.items())},
        "operator_by_session": {s: v.count("O1") for s, v in sorted(op_balance.items())},
        "cross_session_pairs": "all (every replicate pair spans two sessions)",
    }


def skeleton_events(rows: list[dict]) -> list:
    """Grammar-v1 skeletons with the design's intent/provenance and placeholder
    observations at the four planned timepoints — enough for the structural checks."""
    events = []
    for row in rows:
        observations = [
            {
                "observation_id": f"{row['event_id']}:xrd:t{t}",
                "modality": "xrd",
                "timepoint_minutes": float(t),
                "file_path": f"data/raw/pilot/{row['event_id']}/t{t}.xy",
            }
            for t in (5, 15, 60, 1440)
        ]
        events.append(parse_event({
            "event_id": row["event_id"],
            "system": "calcium_carbonate_pilot",
            "intent": {
                "plan_id": f"c{row['condition']:02d}",
                "event_group_id": f"c{row['condition']:02d}",
                "planned": {f"caco3.{k}": row[k] for k in FACTORS},
            },
            "observations": observations,
            "outcome": {"status": "unknown"},  # earned during collection, not designable
            "provenance": {
                "operator_id": row["operator"],
                "lot_id": row["lot"],
                "instrument_session_id": row["session"],
                "measurement_day": row["session"],
                "run_order": row["run_order"],
                "source_dataset": "controlled_pilot",
            },
        }))
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path,
                        default=Path("docs/controlled-collection/pilot_assignment.csv"))
    parser.add_argument("--output", type=Path,
                        default=Path("data/manifests/pilot_assignment.json"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]

    rows = build_rows()
    constraints = assert_constraints(rows)

    events = skeleton_events(rows)
    l0, l1, l3 = check_l0(events), check_l1(events), check_l3(events)
    certification = {
        "l0_raw_trace_structure": l0["passed"],
        "l1_provenance_axes": l1["passed"],
        "l1_logged_axes": l1["evidence"]["logged_axes"],
        "l3_counterbalancing": l3["passed"],
        "l3_evidence": l3["evidence"],
        "l2_note": "L2 (negatives retained, labels frozen after raw) is a COLLECTION "
                   "obligation — it cannot be certified by design, only by conduct.",
    }
    assert l0["passed"] and l1["passed"] and l3["passed"], "design fails its own checker"

    csv_path = root / args.csv
    fieldnames = ["event_id", "condition", "replicate", *FACTORS.keys(),
                  "session", "operator", "lot", "run_order"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["session"], r["run_order"])))

    manifest = {
        "task": "pilot_assignment",
        "seed": SEED,
        "constraints": constraints,
        "design_certification": certification,
        "csv": str(args.csv),
        "rows": rows,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_identity": run_identity(),
    }
    out = root / args.output
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"wrote {args.csv} ({len(rows)} events) and {args.output}")
    print(f"design certification: L0 structure {l0['passed']}, L1 axes "
          f"{l1['evidence']['logged_axes']}, L3 counterbalancing {l3['passed']} "
          f"({l3['evidence']['replicated_group_count']} replicated groups, "
          f"{l3['evidence']['groups_with_provenance_variation']} with provenance variation)")


if __name__ == "__main__":
    main()
