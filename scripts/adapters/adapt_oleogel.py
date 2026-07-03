"""Adapt the oleogel SAXS/WAXS deposit (Zenodo 15268752) into event-grammar v1 envelopes.

Source: data/raw/oleogel_zenodo_15268752 — time-resolved in-situ synchrotron SAXS/WAXS of
monoglyceride oleogels crystallizing under shear (see docs/event-method/refined_a_oleogel_dataset.md).
Nine events total, ALL runs the deposit provides (no sampling):

* 6 shear-cooling runs, ``SR-SAXS-WAXS/MAGs/<run>/{SAXS,WAXS}/<run>_<MOD>_NNNN_sub.csv``
  (2 materials x 3 shear settings; ~280-400 frame-aligned SAXS+WAXS frames per run).
* 3 standalone wide-format WAXS follow-up series, ``WAXS_<sample>_1s_follow-up*.csv``
  (120/60/120 timepoints for follow-up/extended/C18C16 respectively, as repeating
  ``I_subtracted;Sigma_I`` column pairs on one q grid). Zip entry mtimes carry per-run
  export dates (2025-02-21/25) — archive metadata, not experiment timestamps; not mapped.

Slot mapping (what was derived, and from where)
------------------------------------------------
intent
    ``planned`` parsed from the depositors' own run-folder / file names, the only design
    record in the deposit: ``s_<sample>_<shear>_<coolingrate>_<endtemp>`` for MAG runs
    (e.g. s_dmhr_1s_10Cmin_10c -> sample=dmhr, shear_setting=1s, cooling_rate=10Cmin,
    end_temperature=10c) and ``WAXS_<sample>_<shear>_<protocol>.csv`` for follow-ups.
    ``intent.event_group_id`` = ``<sample>_<shear>`` for MAG runs (the designed condition
    cell; the ``_redo`` suffix on s_mopv_25s marks it as a repeat of the mopv/25s condition,
    but the original run is NOT deposited, so no group actually has 2 events).
    NOT derivable: plan ids, protocol documents, what the shear token (1s/25s/50s) means
    quantitatively, sample compositions.
observations
    One observation per frame (MAG runs: modalities saxs+waxs, one CSV file per frame,
    referenced by ``file_path`` relative to the repo root) or per timepoint (follow-ups:
    modality waxs, shared wide CSV referenced by ``file_path``; the inline payload carries
    only the 0-based column indices locating that timepoint's I/Sigma pair in the file).
    Ordering: ``frame_index`` from the filename frame number (MAG) or column-pair position
    (follow-up). NOT derivable: per-frame timestamps or temperature log (none deposited —
    frame index is the only time coordinate), exposure times, instrument/session ids.
outcome
    status "unknown" for every event: the deposit records no completion/failure/abort
    information anywhere. No negative outcomes exist to retain.
provenance
    All axes null (operator, lab, batch, lot, instrument, session, measurement day,
    run order: none appear in any file name, header, or table of the deposit).
    ``source_dataset`` = zenodo_15268752; ``raw_export_profile`` notes the two CSV layouts.
labels
    From ``SR-SAXS-WAXS/MAGs/d-spacings_MAGs.xlsx`` (sheet "SAXS"): a hand-made table of
    "Onset crystallization matlab index" per (material, shear rate); mapped to the 6 MAG
    runs, with the 0-based frame index computed as matlab_index - 1 (the sheet's own
    "number dat file" formula). ``labeler_id`` cites the deposit artifact, not a person —
    the deposit names no labeler. ``assigned_after_raw_data_frozen`` = null: the deposit
    does not say when the table was made. NOT derivable: actual d-spacing values or
    polymorph assignments (despite the filename, the sheet holds only onset indices),
    labels for the 3 follow-up runs, labeler identity/confidence/timing.

Determinism: reads only from data/raw/oleogel_zenodo_15268752, sorted globs, no network.

Usage:
    .venv/bin/python scripts/adapters/adapt_oleogel.py \
        [--output data/interim/event_grammar_v1/oleogel/events.json]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from openpyxl import load_workbook

RAW_REL = Path("data/raw/oleogel_zenodo_15268752")
MAGS_REL = RAW_REL / "SR-SAXS-WAXS" / "MAGs"
LABEL_XLSX_REL = MAGS_REL / "d-spacings_MAGs.xlsx"

FOLLOW_UP_FILES = (
    "WAXS_MO-C18_1s_follow-up.csv",
    "WAXS_MO-C18_1s_follow-up_extended.csv",
    "WAXS_MO-C18C16_1s_follow-up.csv",
)

_FRAME_RE = re.compile(r"_(\d+)_sub\.csv$")
_FOLLOW_UP_RE = re.compile(r"^WAXS_(?P<sample>[A-Za-z0-9-]+)_(?P<shear>\d+s)_(?P<protocol>.+)\.csv$")


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_mag_run_name(run: str) -> dict:
    """``s_<sample>_<shear>_<coolingrate>_<endtemp>[_redo]`` -> namespaced planned dict."""
    parts = run.split("_")
    return {
        "oleogel.sample": parts[1] if len(parts) > 1 else None,
        "oleogel.shear_setting": parts[2] if len(parts) > 2 else None,
        "oleogel.cooling_rate": parts[3] if len(parts) > 3 else None,
        "oleogel.end_temperature": parts[4] if len(parts) > 4 else None,
    }


def load_onset_labels(root: Path) -> dict[tuple[str, str], dict]:
    """Read the deposit's onset-crystallization table, keyed by (sample, shear_setting).

    Sheet "SAXS" layout (rows 6-8): B/C = DMHR shear rate / onset matlab index,
    G/H = MOPV shear rate / onset matlab index. The shear cell "25 (redo)" marks the
    deposited mopv 25s run (the redo). The sheet's third column is the formula
    ``=<matlab index> - 1`` (0-based frame number), recomputed here.
    """
    sheet = load_workbook(root / LABEL_XLSX_REL, data_only=True)["SAXS"]
    labels: dict[tuple[str, str], dict] = {}
    for sample, shear_col, onset_col in (("dmhr", "B", "C"), ("mopv", "G", "H")):
        for row in (6, 7, 8):
            shear_raw, onset = sheet[f"{shear_col}{row}"].value, sheet[f"{onset_col}{row}"].value
            if shear_raw is None or onset is None:
                continue
            shear = re.match(r"\d+", str(shear_raw)).group(0) + "s"
            labels[(sample, shear)] = {
                "labeler_id": "deposit:d-spacings_MAGs.xlsx",
                "label": f"saxs_onset_crystallization_frame_0based={int(onset) - 1}",
                "confidence": None,
                "stage": None,
                "notes": f"sheet SAXS cell {onset_col}{row}: shear rate {shear_raw!r}, "
                         "'Onset crystallization matlab index' (1-based)",
                "oleogel.onset_frame_index_matlab": int(onset),
                "oleogel.onset_frame_index_0based": int(onset) - 1,
            }
    return labels


def frame_observations(root: Path, run_dir: Path) -> list[dict]:
    """Frame-indexed saxs+waxs observations for one MAG run, payloads by file reference."""
    observations: list[dict] = []
    for modality in ("SAXS", "WAXS"):
        for path in sorted((run_dir / modality).glob("*_sub.csv")):
            match = _FRAME_RE.search(path.name)
            if match is None:
                continue
            frame = int(match.group(1))
            observations.append({
                "observation_id": f"{run_dir.name}:{modality.lower()}:{frame:04d}",
                "modality": modality.lower(),
                "kind": "measurement",
                "stage": "in_situ",
                "frame_index": frame,
                "file_path": str(path.relative_to(root)),
                "raw_export_format": "csv:q,I (comma-delimited; NaN at masked q)",
            })
    observations.sort(key=lambda obs: (obs["frame_index"], obs["modality"]))
    return observations


def mag_event(root: Path, run_dir: Path, onset_labels: dict[tuple[str, str], dict]) -> dict:
    run = run_dir.name
    planned = parse_mag_run_name(run)
    key = (planned["oleogel.sample"], planned["oleogel.shear_setting"])
    entry = onset_labels.get(key)
    return {
        "event_id": f"oleogel:{run}",
        "system": "monoglyceride_oleogel",
        "created_at": None,
        "intent": {
            "plan_id": None,
            "event_group_id": f"{key[0]}_{key[1]}",
            "planned": planned,
            "replicate_marker": "redo" if run.lower().endswith("redo") else None,
        },
        "observations": frame_observations(root, run_dir),
        "outcome": {
            "status": "unknown",
            "summary": None,
            "notes": "deposit records no completion/failure status for any run",
        },
        "provenance": _provenance("per-frame csv:q,I under SR-SAXS-WAXS/MAGs"),
        "labels": {"assigned_after_raw_data_frozen": None, "entries": [entry]} if entry else None,
    }


def follow_up_event(root: Path, csv_rel: Path) -> dict:
    match = _FOLLOW_UP_RE.match(csv_rel.name)
    with (root / csv_rel).open() as handle:
        columns = [col.strip() for col in handle.readline().rstrip("\n").split(";")]
    n_timepoints = sum(1 for col in columns if col.startswith("I_subtracted"))
    observations = [
        {
            "observation_id": f"{csv_rel.stem}:waxs:{k:04d}",
            "modality": "waxs",
            "kind": "measurement",
            "stage": None,
            "frame_index": k,
            "file_path": str(csv_rel),
            "payload": {"waxs": {"csv_intensity_column": 1 + 2 * k, "csv_sigma_column": 2 + 2 * k}},
            "raw_export_format": "csv:q x (I_subtracted,Sigma_I) pairs (semicolon-delimited, wide)",
        }
        for k in range(n_timepoints)
    ]
    return {
        "event_id": f"oleogel:{csv_rel.stem}",
        "system": "monoglyceride_oleogel",
        "created_at": None,
        "intent": {
            "plan_id": None,
            "event_group_id": None,
            "planned": {
                "oleogel.sample": match.group("sample"),
                "oleogel.shear_setting": match.group("shear"),
                "oleogel.protocol": match.group("protocol"),
            },
        },
        "observations": observations,
        "outcome": {
            "status": "unknown",
            "summary": None,
            "notes": "deposit records no completion/failure status for any run",
        },
        "provenance": _provenance("standalone wide WAXS follow-up csv"),
        "labels": None,
    }


def _provenance(profile: str) -> dict:
    return {
        "operator_id": None,
        "lab_id": None,
        "batch_id": None,
        "lot_id": None,
        "instrument_id": None,
        "instrument_session_id": None,
        "measurement_day": None,
        "run_order": None,
        "source_dataset": "zenodo_15268752",
        "raw_export_profile": profile,
    }


def build_events(root: Path) -> list[dict]:
    onset_labels = load_onset_labels(root)
    run_dirs = sorted(p for p in (root / MAGS_REL).iterdir() if p.is_dir())
    events = [mag_event(root, run_dir, onset_labels) for run_dir in run_dirs]
    events += [follow_up_event(root, RAW_REL / name) for name in FOLLOW_UP_FILES]
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/interim/event_grammar_v1/oleogel/events.json"),
        help="Output events JSON path (relative paths resolved against the repo root).",
    )
    args = parser.parse_args()
    root = project_root()
    output = args.output if args.output.is_absolute() else root / args.output

    events = build_events(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(events, indent=1) + "\n")

    n_obs = sum(len(event["observations"]) for event in events)
    labeled = sum(1 for event in events if event.get("labels"))
    print(f"wrote {len(events)} events ({n_obs} observations, {labeled} labeled) -> {output}")


if __name__ == "__main__":
    main()
