"""Adapt the RRUFF mineral Raman archive into event-grammar v1 envelopes.

RRUFF is the study's deliberate STRESS CASE: a *measurement archive*, not an event
archive. A specimen is collected from nature and measured; nothing is planned or made,
and no failed/aborted runs are logged. This adapter maps it as honestly as the source
allows and lets the conformance ladder expose the gaps (predicted: grades L0).

Source: data/raw/rruff/excellent_unoriented.zip — 11,415 ``.txt`` files, each a Raman
spectrum with ``##KEY=value`` header lines followed by ``wavenumber, intensity`` rows.
Filenames encode ``{Mineral}__{RRUFFID}__Raman__{wavelength}______Raman_Data_{Processed|
RAW}__{hash}.txt``. Every measurement is exported twice (Processed + RAW); many specimens
were measured at several laser wavelengths (514 / 532 / 780 / 785 nm).

Event boundary
    One event per specimen (RRUFFID). A specimen is the natural unit that was collected
    and then measured.

Slot mapping
    intent        -> null. A specimen is collected, not synthesised; the source records
                     no plan, recipe, or design. (mapping gap)
    observations  -> one observation per distinct measured laser wavelength for that
                     specimen, modality "raman". We reference the deposited export by file
                     (never inline the ~600-1000-point vector). For each (specimen,
                     wavelength) we keep ONE observation and prefer the Processed export,
                     falling back to RAW; the selected and alternate members are both recorded
                     in the payload rather than emitted as a second
                     observation, so multi-observation structure reflects genuine
                     measurement multiplicity (different laser lines) and is not inflated
                     by format duplicates. order_index ranks wavelengths ascending;
                     observation.instrument_id encodes the laser line
                     ("raman_{wavelength}nm"); the real wavelength is in the payload.
    outcome       -> status "unknown". The archive records no per-specimen outcome; a
                     spectrum simply exists. (mapping gap)
    provenance    -> only source_dataset is real at the event (specimen) level. There is
                     NO recorded operator, lab, batch, lot, measurement day, session, or
                     run order for the measurement. Laser wavelength is the one derivable
                     instrument axis, but it varies WITHIN a specimen (multiple lines), so
                     it cannot be a single event-level instrument_id honestly; it lives on
                     each observation instead. (mapping gap: no event-level collection
                     provenance)
    labels        -> labels.entries carry the RRUFF curation: mineral species (##NAMES)
                     and the ##STATUS confirmation flag, both labeler_id "rruff_curation".
                     assigned_after_raw_data_frozen = null: the archive does not state
                     whether curation post-dates the raw spectrum freeze. (mapping gap)

Sample-origin metadata that is NOT measurement-collection provenance (##LOCALITY,
##OWNER, ##SOURCE, ##IDEAL CHEMISTRY, ##URL) is kept on a namespaced event-level
``rruff_specimen`` object, deliberately out of the provenance axes so it cannot lift the
dataset past L0 on sample-custody fields that do not describe how the data was collected.

Not derivable from the source (mapping gaps):
    - intent / plan (none exists)
    - outcome status (never recorded)
    - operator / lab / batch / lot / measurement-day / session / run-order provenance
    - whether labels were frozen after the raw record (assigned_after_raw_data_frozen)
    - a real timestamp (zip mtimes are archive/download times, not measurement times, so
      they are NOT used)

Determinism / scope: reads only from data/raw/rruff/excellent_unoriented.zip, no network.
Uses all specimens and all distinct (wavelength, variant) measurements the filename
pattern parses; members that still do not parse are counted and printed, never silently
dropped. Blank-wavelength files become observations with wavelength null; rare filename
annotation tokens (e.g. "laser_phase_change", the archive's only anomalous-outcome note)
are preserved on the observation (payload rruff.variant_note + notes). Headers are UTF-8
(latin-1 fallback). Specimen metadata is read once per specimen (constant across its
files). events.json stores metadata + file references only (no spectra), keeping it well
under the size cap.

    .venv/bin/python scripts/adapters/adapt_rruff.py
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

RAW_ZIP = Path("data/raw/rruff/excellent_unoriented.zip")
OUT_REL = Path("data/interim/event_grammar_v1/rruff/events.json")

# {Mineral}__{RRUFFID}[_{variant}]__Raman__{wavelength}______Raman_Data_{Processed|RAW}__{hash}.txt
# variant is a rare annotation token (e.g. "laser_phase_change" — the archive's only
# anomalous-outcome note); wavelength may be blank for a handful of files.
NAME_RE = re.compile(
    r"^(?P<mineral>.+?)__(?P<rid>[^_]+)(?:_(?P<variant>[A-Za-z0-9_]+?))?"
    r"__Raman__(?P<wl>\d+(?:-\d+)?|)_+"
    r"Raman_Data_(?P<kind>Processed|RAW)__(?P<hash>[0-9a-fA-F]+)\.txt$"
)

def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_header(raw: bytes) -> dict[str, str]:
    """Read only the ``##KEY=value`` header block; stop at the first data row."""
    meta: dict[str, str] = {}
    try:
        text = raw.decode("utf-8")  # the archive's bytes are UTF-8
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("##"):
            if "=" in line:
                key, value = line[2:].split("=", 1)
                meta[key.strip()] = value.strip()
        elif line and "," in line:
            break  # first data row: header is done
    return meta


def collect_members(
    zf: zipfile.ZipFile,
) -> tuple[dict[str, dict[tuple[int, str], dict[str, str]]], list[str]]:
    """Map RRUFFID -> (wavelength, variant) -> {Processed,RAW export -> member name}.

    Wavelength -1 means the filename records no laser line. The variant token ("" for
    normal measurements) preserves the archive's rare annotations, e.g.
    "laser_phase_change". Returns the specimen map plus any members whose names still do
    not parse (counted and reported, never silently dropped).
    """
    specimens: dict[str, dict[tuple[int, str], dict[str, str]]] = {}
    skipped: list[str] = []
    for name in zf.namelist():
        base = name.split("/")[-1]
        match = NAME_RE.match(base)
        if not match:
            if base.endswith(".txt"):
                skipped.append(base)
            continue
        rid = match.group("rid")
        # "514-5" is the archive's spelling of 514.5 nm; blank means unrecorded (-1).
        wl_str = match.group("wl")
        wl = float(wl_str.replace("-", ".")) if wl_str else -1.0
        variant = match.group("variant") or ""
        kind = match.group("kind")
        specimens.setdefault(rid, {}).setdefault((wl, variant), {})[kind] = name
    return specimens, skipped


def build_observations(rid: str, by_key: dict[tuple[int, str], dict[str, str]]) -> list[dict]:
    observations = []
    for order_index, (wl, variant) in enumerate(sorted(by_key)):
        exports = by_key[(wl, variant)]
        # Preserve the historical Processed-first policy, but expose both exact members so
        # RAW -> Processed is an auditable edge rather than an invisible adapter choice.
        chosen_kind = "Processed" if "Processed" in exports else "RAW"
        member = exports[chosen_kind]
        alt_kind = "RAW" if chosen_kind == "Processed" else "Processed"
        alt_member = exports.get(alt_kind)
        wl_tag = f"{wl:g}nm" if wl > 0 else "unknown_wl"
        obs_id = f"{rid}__{wl_tag}" + (f"__{variant}" if variant else "")
        observations.append(
            {
                "observation_id": obs_id,
                "modality": "raman",
                "kind": "measurement",
                "stage": f"deposited_{chosen_kind.lower()}_export",
                "order_index": order_index,
                "instrument_id": f"raman_{wl_tag}",
                "raw_export_format": f"rruff_txt_{chosen_kind.lower()}",
                "file_path": f"{RAW_ZIP.as_posix()}::{member}",
                "payload": {
                    "rruff.raman_wavelength_nm": wl if wl > 0 else None,
                    "rruff.zip_member": member,
                    "rruff.selected_export": chosen_kind,
                    "rruff.alt_export": alt_kind if alt_member else None,
                    "rruff.alt_zip_member": alt_member,
                    "rruff.variant_note": variant or None,
                },
                "notes": (
                    f"archive annotation: {variant}" if variant else None
                ),
            }
        )
    return observations


def build_event(
    rid: str, by_key: dict[tuple[int, str], dict[str, str]], meta: dict[str, str]
) -> dict:
    label_entries = []
    mineral = meta.get("NAMES")
    if mineral:
        label_entries.append(
            {
                "labeler_id": "rruff_curation",
                "label": mineral,
                "confidence": None,
                "stage": None,
                "notes": "mineral species (##NAMES)",
            }
        )
    status = meta.get("STATUS")
    if status:
        label_entries.append(
            {
                "labeler_id": "rruff_curation",
                "label": status,
                "confidence": None,
                "stage": None,
                "notes": "curation confirmation flag (##STATUS)",
            }
        )

    return {
        "event_id": rid,
        "system": "mineral_raman",
        "created_at": None,
        # No plan exists: a specimen is collected from nature, not designed or made.
        "intent": None,
        "observations": build_observations(rid, by_key),
        # The archive records no per-specimen outcome; a spectrum simply exists.
        "outcome": {
            "status": "unknown",
            "summary": None,
            "notes": "RRUFF records measurements, not experiment outcomes.",
        },
        # Only source_dataset is real at the specimen level. Laser wavelength (the one
        # derivable instrument axis) varies within a specimen and lives on observations.
        "provenance": {
            "operator_id": None,
            "lab_id": None,
            "batch_id": None,
            "lot_id": None,
            "instrument_id": None,
            "instrument_session_id": None,
            "measurement_day": None,
            "run_order": None,
            "source_dataset": "rruff",
            "deposited_export_profile": "excellent_unoriented; Processed preferred over RAW",
        },
        "labels": {
            "assigned_after_raw_data_frozen": None,
            "entries": label_entries,
        },
        # Sample-origin metadata: custody/where-collected, NOT measurement provenance.
        # Namespaced and kept off the provenance axes on purpose.
        "rruff_specimen": {
            "locality": meta.get("LOCALITY"),
            "owner": meta.get("OWNER"),
            "source": meta.get("SOURCE"),
            "ideal_chemistry": meta.get("IDEAL CHEMISTRY"),
            "measured_chemistry": meta.get("MEASURED CHEMISTRY"),
            "cell_parameters": meta.get("CELL PARAMETERS"),
            "description": meta.get("DESCRIPTION"),
            "url": meta.get("URL"),
        },
    }


def build_events(zip_path: Path) -> list[dict]:
    with zipfile.ZipFile(zip_path) as zf:
        specimens, skipped = collect_members(zf)
        if skipped:
            print(f"  note: {len(skipped)} .txt members did not parse and were skipped; "
                  f"examples: {skipped[:3]}")
        events = []
        for rid in sorted(specimens):
            by_key = specimens[rid]
            # Read one header per specimen (metadata is constant across its files).
            first_member = by_key[sorted(by_key)[0]]
            probe = first_member.get("Processed") or first_member.get("RAW")
            meta = parse_header(zf.read(probe))
            events.append(build_event(rid, by_key, meta))
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, default=None,
                        help="Override raw zip path (default: data/raw/rruff/...).")
    parser.add_argument("--output", type=Path, default=None,
                        help=f"Output events.json (default: {OUT_REL}).")
    args = parser.parse_args()

    root = project_root()
    zip_path = args.zip or (root / RAW_ZIP)
    zip_path = zip_path if zip_path.is_absolute() else root / zip_path
    out_path = args.output or (root / OUT_REL)
    out_path = out_path if out_path.is_absolute() else root / out_path

    events = build_events(zip_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(events, indent=2, allow_nan=False) + "\n")

    multi = sum(1 for e in events if len(e["observations"]) >= 2)
    total_obs = sum(len(e["observations"]) for e in events)
    print(f"wrote {len(events)} events, {total_obs} observations -> {out_path}")
    print(f"multi-observation specimens (>=2 wavelengths): {multi} "
          f"({multi / max(len(events), 1):.3f})")


if __name__ == "__main__":
    main()
