"""Adapt the Severson et al. 2019 battery cycling batch (matr.io) into event-grammar v1 envelopes.

Source: data/raw/severson/batch1.mat — MATLAB v7.3 (HDF5) batch file, the only batch downloaded
locally (46 cells; the full study is 124 cells across three batches, the other two ~3 GB files
were deliberately not downloaded — see docs/event-method/severson_battery_audit.md). One event
per cell, ALL 46 cells in the file (no sampling within the batch). LFP/graphite cells cycled to
end of life under a fast-charging policy sweep on a multi-channel cycler.

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
    ABOVE the criterion never reached EOL in this file — its run is truncated (several
    batch-1 cells are known to continue cycling in a later batch of the original study) —
    and gets status "ambiguous" with the tail capacity recorded. These truncated runs are
    honest retained negatives: the source data itself distinguishes them. The file flags no
    cells as noisy/excluded (no such field exists in batch1.mat).
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

Caps/sampling: batch1 only (46 of 124 cells) because only batch1.mat is locally available; all
46 cells and all 38,811 cycle observations in it are used. Determinism: reads only
data/raw/severson/batch1.mat, iterates cells in file order, no network.

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

RAW_REL = Path("data/raw/severson/batch1.mat")

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
_POLICY_RE = re.compile(r"^(?P<c1>[0-9_]+)C-(?P<soc>\d+)PER_(?P<c2>[0-9_]+)C$")

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


def cycle_observations(f: h5py.File, summary_ref, barcode: str) -> list[dict]:
    """One cycling observation per cycle from the summary group, inline scalar payload."""
    summary = f[summary_ref]
    cycles = np.array(summary["cycle"]).ravel().astype(int)
    series = {key: np.array(summary[name]).ravel().astype(float) for name, key in SUMMARY_FIELDS}
    observations = []
    for j, cycle in enumerate(cycles):
        payload = {key: round(float(values[j]), 6) for key, values in series.items()}
        observations.append({
            "observation_id": f"{barcode}:cycling:{cycle:04d}",
            "modality": "cycling",
            "kind": "measurement",
            "cycle_index": int(cycle),
            "payload": {"cycling": payload},
            "file_path": str(RAW_REL),
            "raw_export_format": "matlab v7.3 hdf5; within-cycle curves at batch.cycles{cell}",
        })
    return observations


def cell_event(f: h5py.File, batch: h5py.Group, batch_date: str, i: int) -> dict:
    barcode = mat_string(f, batch["barcode"][i, 0])
    channel = mat_string(f, batch["channel_id"][i, 0])
    policy = mat_string(f, batch["policy"][i, 0])
    policy_readable = mat_string(f, batch["policy_readable"][i, 0])
    cycle_life = float(np.array(f[batch["cycle_life"][i, 0]]).ravel()[0])
    observations = cycle_observations(f, batch["summary"][i, 0], barcode)

    n_cycles = len(observations)
    if n_cycles != int(cycle_life) - 1:
        print(f"  warning: cell {i} ({barcode}) trajectory length {n_cycles} != "
              f"cycle_life - 1 ({int(cycle_life) - 1}); 'completed run' reading is weaker here")

    # Outcome from the capacity data itself: did this record actually reach the 80% EOL
    # criterion, or does it end above it (truncated run)?
    qd = np.array([o["payload"]["cycling"]["qdischarge_ah"] for o in observations], dtype=float)
    valid = qd[qd >= ARTIFACT_FLOOR_AH]
    min_qd = float(valid.min()) if valid.size else float("nan")
    eol_reached = valid.size > 0 and min_qd <= EOL_CAPACITY_AH + EOL_TOLERANCE_AH
    if eol_reached:
        outcome = {
            "status": "success",
            "summary": {"cell.cycle_life_cycles": cycle_life,
                        "cell.min_qdischarge_ah": round(min_qd, 4)},
            "notes": "success = QDischarge reached the 0.88 Ah (80%-of-nominal) end-of-life "
                     "criterion within this record; cycle_life is the file's recorded value",
        }
    else:
        outcome = {
            "status": "ambiguous",
            "summary": {"cell.cycle_life_cycles": cycle_life,
                        "cell.min_qdischarge_ah": round(min_qd, 4),
                        "cell.record_truncated": True},
            "notes": "record ends above the 0.88 Ah EOL criterion: run truncated in this batch "
                     "file (several batch-1 cells continue cycling in a later batch of the "
                     "original study); the recorded cycle_life is not confirmed by this record",
        }

    planned = {"cell.charge_policy": policy, "cell.charge_policy_readable": policy_readable}
    planned.update({f"cell.{k}": v for k, v in parse_policy(policy).items()})
    return {
        "event_id": f"severson:batch1:{barcode}",
        "system": "li_ion_cell",
        "created_at": None,
        "intent": {"plan_id": None, "event_group_id": policy, "planned": planned},
        "observations": observations,
        "outcome": outcome,
        "provenance": {
            "operator_id": None,
            "lab_id": None,
            "batch_id": batch_date,
            "lot_id": None,
            "instrument_id": f"channel_{channel}",
            "instrument_session_id": None,
            "measurement_day": None,
            "run_order": None,
            "source_dataset": "severson_2019_matr_io_batch1",
            "raw_export_profile": "matlab v7.3 hdf5 batch file; per-cycle summary scalars inline, "
                                  "within-cycle curves by archive reference",
        },
        "labels": None,
        "source_ref": {"file_path": str(RAW_REL), "batch_cell_index": i},
    }


def build_events(root: Path) -> list[dict]:
    with h5py.File(root / RAW_REL, "r") as f:
        batch_date = mat_string(f, f["batch_date"].ref) if "batch_date" in f else None
        batch = f["batch"]
        n = batch["cycle_life"].shape[0]
        return [cell_event(f, batch, batch_date, i) for i in range(n)]


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
