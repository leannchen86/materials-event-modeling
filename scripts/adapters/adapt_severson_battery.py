"""Adapt the Severson et al. 2019 battery cycling batches (matr.io) into event-grammar v1 envelopes.

Source: every ``data/raw/severson/batch*.mat`` present — MATLAB v7.3 (HDF5) batch files
(batch1 = 2017-05-12, batch2 = 2017-06-30, batch3 = 2018-04-12; the full study is 124 usable
cells). One event per physical cell (barcode), ALL cells in every available file. LFP/graphite
cells cycled to end of life under a fast-charging policy sweep on a multi-channel cycler.

Continuation linkage (in-data, no external assumption): cells sharing a barcode across batch
files are the same physical cell whose test continued in a later batch. Records are merged into
one event in batch-date order; if the continuation's cycle numbering restarts, it is re-indexed
by the primary record's last cycle (mechanical re-indexing, recorded in the event notes). Each
observation carries ``instrument_session_id`` = the batch date and ``instrument_id`` = the
channel of the file it came from, so merged trajectories honestly record that they span
collection sessions. Same-barcode records with DIFFERENT policies are never merged (kept as
separate events with a warning).

Observation quality flags (grammar v1.1 lesson from the first A/B run): per-cycle QDischarge
outside (0.5, 1.3) Ah is physically implausible for a 1.1 Ah nominal cell (a sensor glitch of
2.88 Ah at one cycle was found to poison ridge features); such observations get
``include_in_raw_objective: false`` with the reason in ``notes``. The data stays; the flag
tells consumers to exclude it from learned features.

Slot mapping (what was derived, and from where)
------------------------------------------------
intent
    A REAL plan slot: ``planned`` from the file's own ``batch.policy`` / ``batch.policy_readable``
    per-cell fields — the designed fast-charging protocol (e.g. ``5_4C-40PER_3_6C`` = 5.4C to 40%
    SOC then 3.6C to 80%). The C-rates and SOC switch point are parsed out of the policy string
    itself. ``intent.event_group_id`` = the policy string (22 of 23 policies have 2-3 replicate
    cells). NOT derivable: plan ids, the full protocol document, cell chemistry/spec sheet (not
    recorded in the file).
observations
    One observation per charge/discharge cycle from ``batch.summary`` (per-cycle scalar series),
    ordered by ``cycle_index`` = the summary's own ``cycle`` vector. Inline payload scalars
    (namespaced ``cycling``): QDischarge/QCharge [Ah], IR [Ohm], Tavg/Tmax/Tmin [C],
    chargetime [min]. The full within-cycle raw curves (I, V, Qc, Qd, T, Qdlin, Tdlin,
    discharge_dQdV, t — the basis of the paper's dQ(V) feature) are NOT inlined: no per-cycle
    files exist, so each observation's ``file_path`` references the source archive
    (data/raw/severson/batch1.mat); the curves live at HDF5 group ``batch.cycles{cell_index}``
    keyed by cycle number (reading those curves also needs the batch-level ``batch.Vdlin``
    voltage basis vector, which is not carried into events). NOT derivable: absolute per-cycle
    timestamps/dates (``batch.cycles{cell}.t`` records within-cycle elapsed minutes that reset
    each cycle, so cycle order is the only cross-cycle coordinate), rest periods, instrument
    session boundaries.
outcome
    Derived from the file's own capacity data, not asserted: the dataset's end-of-life
    criterion is 80% of nominal capacity (0.88 Ah of 1.1 Ah). A cell whose QDischarge series
    (excluding <0.5 Ah logging artifacts) reaches <= 0.88 Ah within its record gets status
    "success" with ``outcome.summary`` = the recorded cycle_life. A cell whose record ends
    ABOVE the criterion never reached EOL in this file — its run is right-censored/truncated
    (several batch-1 cells are known to continue cycling in a later batch of the original
    study) — and gets status "unknown" with the tail capacity recorded. A censor is retained
    evidence, not a failed or ambiguous experimental outcome. The file flags no cells as
    noisy/excluded (no such field exists in batch1.mat).
provenance
    ONLY what the file records: ``batch_id`` = the file's root ``batch_date`` variable
    ("2017-05-12"); ``instrument_id`` = "channel_<n>" from per-cell ``batch.channel_id`` (the
    cycler channel; decoded, like ``barcode``, from MATLAB string objects stored in the
    ``#subsystem#/MCOS`` opaque group of the v7.3 file). The cell barcode (physical cell id,
    e.g. EL150800460514) becomes part of event_id. NOT recorded anywhere in the file: operator,
    lab, lot, instrument session, per-cell measurement day, run order.
labels
    null for every event: the source attaches no post-hoc human/machine labels. ``cycle_life``
    is the dataset's inherited summary label but it is an end-of-run outcome here, not a label
    assigned after a frozen raw record; treating it as ``labels`` would fabricate freezing
    metadata the source does not have.

Caps/sampling: none — every cell in every locally present batch file is used. Determinism:
reads only data/raw/severson/batch*.mat, iterates files by name and cells in file order, no
network.

Usage:
    .venv/bin/python scripts/adapters/adapt_severson_battery.py \
        [--output data/interim/event_grammar_v1/severson_battery/events.json]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import h5py
import numpy as np

RAW_DIR = Path("data/raw/severson")

# Physically plausible per-cycle ranges for a 1.1 Ah nominal LFP cell on a fast-charge
# protocol. Outside any window = sensor/logging artifact -> include_in_raw_objective:
# false. QD: nominal ~1.07, EOL 0.88. IR: ~0.015-0.02 Ohm (0.0 = missing reading).
# chargetime: protocols run ~10-13 min (419.9-min spikes observed = same glitch class as
# the 2.88 Ah QD spike). Flags are observation-level because the grammar has no
# field-level flag yet — a v1.1 candidate; the cost is dropping a healthy QD point when a
# sibling field glitches (~tens of points out of ~800/cell).
PLAUSIBLE_RANGES = {
    "qdischarge_ah": (0.5, 1.3),
    "ir_ohm": (0.001, 0.1),
    "chargetime_min": (3.0, 120.0),
}

NOMINAL_CAPACITY_AH = 1.1
EOL_CAPACITY_AH = 0.8 * NOMINAL_CAPACITY_AH  # 0.88 Ah, the dataset's cycle-life criterion
# The summary series stops at the last cycle ABOVE the criterion (trajectory length =
# cycle_life - 1), so completed runs end 0.0001-0.003 Ah above 0.88 while truncated runs
# end at 0.913+ — a clean gap. The tolerance sits inside that gap.
EOL_TOLERANCE_AH = 0.005
ARTIFACT_FLOOR_AH = 0.5  # QDischarge readings below this are logging artifacts, not capacity

SUMMARY_FIELDS = (
    ("QDischarge", "qdischarge_ah"),
    ("QCharge", "qcharge_ah"),
    ("IR", "ir_ohm"),
    ("Tavg", "tavg_c"),
    ("Tmax", "tmax_c"),
    ("Tmin", "tmin_c"),
    ("chargetime", "chargetime_min"),
)

# e.g. 5_4C-40PER_3_6C -> first rate 5.4C until 40% SOC, then 3.6C (underscores = decimal points).
# batch1 writes '3_6C-80PER_3_6C' (hyphen before the SOC switch); batches 2-3 write
# '3_6C_30PER_6C' (underscore); batch3 adds a '_NEWSTRUCTURE' protocol tag and one string
# omits the trailing 'C'. All mean: c1 to soc%, then c2 (underscores = decimals). The full
# original string stays as the policy/group id; only the numeric parameters are parsed out.
_POLICY_RE = re.compile(
    r"^(?P<c1>[0-9_]+)C[-_](?P<soc>\d+)PER_(?P<c2>[0-9_]+?)C?(?:_NEWSTRUCTURE)?$"
)

_MCOS_MAGIC = 3707764736  # first uint32 of a MATLAB opaque-string reference


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _mcos_string(f: h5py.File, meta_ref) -> str:
    """Decode a MATLAB string object via its #subsystem#/MCOS entry.

    The in-place reference is a (1,6) uint32 array whose 5th element is a 1-based object index;
    MCOS[index + 1] holds [.., .., .., .., nchars, <UTF-16LE chars packed into uint64s>].
    """
    mcos = np.array(f["#subsystem#"]["MCOS"]).ravel()
    meta = np.array(f[mcos[int(meta_ref[4]) + 1]]).ravel().astype(np.uint64)
    nchars = int(meta[4])
    return meta[5:].tobytes()[: nchars * 2].decode("utf-16-le")


def mat_string(f: h5py.File, ref) -> str:
    """Decode a cell's string field: plain char array or opaque MATLAB string object."""
    data = np.array(f[ref]).ravel()
    if data.dtype == np.uint32 and data.size == 6 and int(data[0]) == _MCOS_MAGIC:
        return _mcos_string(f, data)
    return "".join(chr(int(c)) for c in data if int(c) > 0)


def parse_policy(policy: str) -> dict:
    """Parse designed parameters out of the policy string; None fields if the format deviates."""
    match = _POLICY_RE.match(policy)
    if match is None:
        return {"charge_c_rate_1": None, "soc_switch_percent": None, "charge_c_rate_2": None}
    return {
        "charge_c_rate_1": float(match.group("c1").replace("_", ".")),
        "soc_switch_percent": int(match.group("soc")),
        "charge_c_rate_2": float(match.group("c2").replace("_", ".")),
    }


def cycle_observations(
    f: h5py.File, summary_ref, barcode: str, batch_date: str, channel: str, rel_path: str
) -> list[dict]:
    """One cycling observation per cycle: inline scalars, session/instrument, quality flag."""
    summary = f[summary_ref]
    cycles = np.array(summary["cycle"]).ravel().astype(int)
    series = {key: np.array(summary[name]).ravel().astype(float) for name, key in SUMMARY_FIELDS}
    observations = []
    for j, cycle in enumerate(cycles):
        payload = {key: round(float(values[j]), 6) for key, values in series.items()}
        violations = [
            f"{key}={payload[key]} outside {bounds}"
            for key, bounds in PLAUSIBLE_RANGES.items()
            if not bounds[0] <= payload[key] <= bounds[1]
        ]
        observations.append({
            "observation_id": f"{barcode}:{batch_date}:cycling:{cycle:04d}",
            "modality": "cycling",
            "kind": "measurement",
            "cycle_index": int(cycle),
            "payload": {"cycling": payload},
            "file_path": rel_path,
            "instrument_id": f"channel_{channel}",
            "instrument_session_id": batch_date,
            "raw_export_format": "matlab v7.3 hdf5; within-cycle curves at batch.cycles{cell}",
            "include_in_raw_objective": not violations,
            "notes": None if not violations else (
                "physical-bounds flag: " + "; ".join(violations)
                + " — sensor/logging artifact, exclude from features"
            ),
        })
    return observations


def load_batch_cells(path: Path, rel_path: str) -> list[dict]:
    """Raw per-cell records (not yet events) from one batch file."""
    records = []
    with h5py.File(path, "r") as f:
        batch_date = mat_string(f, f["batch_date"].ref) if "batch_date" in f else "unknown"
        batch = f["batch"]
        n = batch["cycle_life"].shape[0]
        for i in range(n):
            barcode = mat_string(f, batch["barcode"][i, 0])
            channel = mat_string(f, batch["channel_id"][i, 0])
            policy = mat_string(f, batch["policy"][i, 0])
            records.append({
                "barcode": barcode,
                "batch_date": batch_date,
                "channel": channel,
                "policy": policy,
                "policy_readable": mat_string(f, batch["policy_readable"][i, 0]),
                "file_cycle_life": float(np.array(f[batch["cycle_life"][i, 0]]).ravel()[0]),
                "cell_index": i,
                "rel_path": rel_path,
                "observations": cycle_observations(
                    f, batch["summary"][i, 0], barcode, batch_date, channel, rel_path
                ),
            })
    return records


def derive_outcome(observations: list[dict], file_cycle_life: float, merged: bool) -> dict:
    """Outcome from the (possibly merged) capacity data itself, artifact-flagged cycles excluded."""
    usable = [o for o in observations if o["include_in_raw_objective"]]
    qd = np.array([o["payload"]["cycling"]["qdischarge_ah"] for o in usable], dtype=float)
    cyc = np.array([o["cycle_index"] for o in usable], dtype=float)
    valid = qd >= ARTIFACT_FLOOR_AH
    min_qd = float(qd[valid].min()) if valid.any() else float("nan")
    eol_mask = valid & (qd <= EOL_CAPACITY_AH + EOL_TOLERANCE_AH)
    merged_note = " (record merged across batch files via barcode continuation)" if merged else ""
    if eol_mask.any():
        eol_cycle = float(cyc[eol_mask].min())
        return {
            "status": "success",
            "summary": {"cell.cycle_life_cycles": eol_cycle,
                        "cell.file_recorded_cycle_life": file_cycle_life,
                        "cell.min_qdischarge_ah": round(min_qd, 4)},
            "notes": "success = QDischarge reached the 0.88 Ah (80%-of-nominal) end-of-life "
                     "criterion; cycle_life derived as the first cycle at/below the criterion"
                     + merged_note,
        }
    return {
        "status": "unknown",
        "summary": {"cell.cycle_life_cycles": None,
                    "cell.file_recorded_cycle_life": file_cycle_life,
                    "cell.min_qdischarge_ah": round(min_qd, 4),
                    "cell.record_truncated": True},
        "notes": "record ends above the 0.88 Ah EOL criterion: run truncated (no later "
                 "continuation found by barcode); the file-recorded cycle_life is not confirmed "
                 "by this record" + merged_note,
    }


def assemble_event(records: list[dict]) -> dict:
    """One event from a barcode's records (batch-date-ordered; later records re-indexed)."""
    records = sorted(records, key=lambda r: r["batch_date"])
    primary = records[0]
    observations = list(primary["observations"])
    merged_from = [primary["batch_date"]]
    for cont in records[1:]:
        offset = max(o["cycle_index"] for o in observations)
        cont_min = min(o["cycle_index"] for o in cont["observations"])
        shift = offset if cont_min <= offset else 0
        for o in cont["observations"]:
            o = dict(o)
            o["cycle_index"] = int(o["cycle_index"] + shift)
            observations.append(o)
        merged_from.append(cont["batch_date"])
    merged = len(records) > 1
    outcome = derive_outcome(observations, primary["file_cycle_life"], merged)

    policy = primary["policy"]
    planned = {"cell.charge_policy": policy,
               "cell.charge_policy_readable": primary["policy_readable"]}
    planned.update({f"cell.{k}": v for k, v in parse_policy(policy).items()})
    return {
        "event_id": f"severson:{primary['barcode']}",
        "system": "li_ion_cell",
        "created_at": None,
        "intent": {"plan_id": None, "event_group_id": policy, "planned": planned},
        "observations": observations,
        "outcome": outcome,
        "provenance": {
            "operator_id": None,
            "lab_id": None,
            "batch_id": primary["batch_date"],
            "lot_id": None,
            "instrument_id": f"channel_{primary['channel']}",
            "instrument_session_id": primary["batch_date"],
            "measurement_day": None,
            "run_order": None,
            "source_dataset": "severson_2019_matr_io",
            "raw_export_profile": "matlab v7.3 hdf5 batch files; per-cycle summary scalars "
                                  "inline, within-cycle curves by archive reference",
        },
        "labels": None,
        "source_ref": {
            "files": [r["rel_path"] for r in records],
            "batch_cell_indices": [r["cell_index"] for r in records],
            "merged_from_batches": merged_from if merged else None,
        },
    }


def build_events(root: Path) -> list[dict]:
    batch_paths = sorted((root / RAW_DIR).glob("batch*.mat"))
    if not batch_paths:
        raise FileNotFoundError(f"no batch*.mat files under {RAW_DIR}")
    print(f"reading {len(batch_paths)} batch file(s): {[p.name for p in batch_paths]}")
    all_records: list[dict] = []
    for path in batch_paths:
        rel = str(RAW_DIR / path.name)
        records = load_batch_cells(path, rel)
        print(f"  {path.name}: {len(records)} cells (batch_date {records[0]['batch_date']})")
        all_records.extend(records)

    by_barcode: dict[str, list[dict]] = {}
    for record in all_records:
        by_barcode.setdefault(record["barcode"], []).append(record)

    events = []
    merged_count = 0
    for barcode in sorted(by_barcode):
        records = by_barcode[barcode]
        policies = sorted({r["policy"] for r in records}, key=len, reverse=True)
        # Continuation records in a later batch may carry a truncated policy label that is
        # a strict suffix of the primary's (e.g. '80PER_3_6C' for '3_6C-80PER_3_6C': same
        # SOC switch and final rate, first stage omitted because the continuation starts
        # past it). Suffix-compatible labels are the same protocol; merge with the full
        # policy string as canonical. Genuinely different policies are never merged.
        compatible = all(policies[0].endswith(p) for p in policies[1:])
        if len(policies) > 1 and not compatible:
            print(f"  warning: barcode {barcode} has {len(records)} records with "
                  f"INCOMPATIBLE policies {policies}; kept as separate events (no merge)")
            for r in records:
                event = assemble_event([r])
                event["event_id"] = f"severson:{barcode}:{r['batch_date']}"
                events.append(event)
            continue
        if len(records) > 1:
            merged_count += 1
            canonical = policies[0]
            for r in records:
                r["policy"] = canonical
        events.append(assemble_event(records))
    if merged_count:
        print(f"  merged {merged_count} barcode continuation(s) across batch files")
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/interim/event_grammar_v1/severson_battery/events.json"),
        help="Output events JSON path (relative paths resolved against the repo root).",
    )
    args = parser.parse_args()
    root = project_root()
    output = args.output if args.output.is_absolute() else root / args.output

    events = build_events(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(events, indent=1) + "\n")

    n_obs = sum(len(event["observations"]) for event in events)
    n_groups = len({event["intent"]["event_group_id"] for event in events})
    print(f"wrote {len(events)} events ({n_obs} cycle observations, {n_groups} charge policies) "
          f"-> {output}")


if __name__ == "__main__":
    main()
