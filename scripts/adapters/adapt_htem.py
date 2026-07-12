"""Adapt the locally cached NREL HTEM sample-library tables into event-grammar v1 envelopes.

One event per thin-film sample library, built ONLY from the local API cache under
``data/interim/htem_event_proxy/`` (written by ``scripts/run_htem_event_proxy.py``; no network).
A library is included when the cache holds both its per-position properties entry and its XRD
spectra entry — 95 libraries at the time of writing. This is a locality cap, not a sample of the
full HTEM database (1,891 records in ``sample_library_records.json``): only these 95 have
position-level payloads on disk.

Slot mapping (source field -> envelope slot):

* intent.planned  <- the per-library deposition recipe fields recorded in
  ``sample_library_records.json`` (``deposition_compounds/power/gases/gas_flow_sccm/
  sample_time_min/cycles/substrate_material/base_pressure_mtorr/initial_temp_c``), non-null
  fields only. These are recorded as plan-shaped metadata, not a full process trajectory.
  ``plan_id`` / ``event_group_id`` are null: HTEM records no explicit plan or replicate-group id.
* observations    <- position-indexed rows, several modalities per position:
  - ``xrd``: deposited spectrum referenced by ``file_path`` (the cached spectra chunk, relative to the
    repo root) plus ``payload.htem`` locator {table, spectra_key, sample_library_id, position,
    n_points}; XRD-derived ``peak_count`` (a string in the source) rides along in the payload.
  - ``optical_absorption`` (17/95 libraries): deposited absorption-vs-energy spectrum, referenced the
    same way.
  - ``xrf``, ``four_point_probe``, ``optical_summary``, ``profilometry``: small per-position
    scalars/lists inlined in ``payload.htem`` from the properties table.
  - ``temperature`` (``absolute_temp_c``): per-position temperature whose semantics the source
    does not document, so ``kind`` is left null.
  Every observation carries ``order_index`` = source ``position`` (1..44); ``spatial_position``
  = ``x_mm``/``y_mm`` where the properties table records them.
* outcome         <- status "unknown" for every event. HTEM records no success/failure/abort
  status for a library; the ``quality`` integer (rater and timing unrecorded) is NOT an outcome.
* provenance      <- only what the record carries: ``person_id`` -> operator_id (90/95),
  ``pdac`` (combinatorial deposition-chamber id) -> instrument_id as ``pdac_<n>`` (95/95),
  ``sample_date`` -> measurement_day, date part (41/95 — note this is the library/sample date,
  the closest day axis the source records, not literally a measurement date). Library/sample ids
  are identifiers, not provenance axes, and are kept out. ``sciround`` (38/95, semantics
  undocumented) stays in the event-level ``source_extras``.
* labels          <- null. ``quality`` (1-5) and per-position ``xrf_compounds`` are label-like,
  but the source records no labeler identity and no assignment timing relative to raw-data
  freezing, so they cannot honestly fill the labels slot; ``quality`` is kept in
  ``source_extras`` and ``xrf_compounds`` stays raw inside the xrf observation payload.

Could NOT be derived (mapping gaps): plan/replicate-group ids; any outcome status or failure
log; batch/lot/lab/session axes; run order; labeler identity or label-freezing timing; the
observed process trajectory (only planned deposition settings exist); measurement timestamps.

Deterministic: sorted library ids, sorted positions, fixed modality order; reads only data/.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

DEPOSITION_FIELDS = (
    "deposition_compounds",
    "deposition_power",
    "deposition_gases",
    "deposition_gas_flow_sccm",
    "deposition_sample_time_min",
    "deposition_cycles",
    "deposition_substrate_material",
    "deposition_base_pressure_mtorr",
    "deposition_initial_temp_c",
)

# Per-position property fields grouped into observation modalities (kind "measurement").
PROPERTY_MODALITIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("xrf", ("xrf_compounds", "xrf_concentration")),
    ("four_point_probe", ("fpm_conductivity", "fpm_resistivity", "fpm_sheet_resistance",
                          "fpm_standard_deviation")),
    ("optical_summary", ("opt_average_vis_trans", "opt_direct_bandgap")),
    ("profilometry", ("thickness",)),
)

SOURCE_EXTRA_FIELDS = ("num", "elements", "quality", "sciround", "has_xrd", "has_xrf",
                       "has_opt", "has_ele")


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_cache(cache_dir: Path) -> tuple[dict[int, dict], dict[int, dict], dict[str, dict]]:
    """Return (records_by_id, properties_by_id, spectra locators by kind)."""
    records = json.loads((cache_dir / "sample_library_records.json").read_text())
    records_by_id = {int(r["id"]): r for r in records}

    properties_by_id: dict[int, dict] = {}
    for path in sorted(cache_dir.glob("properties_*.json")):
        for entry in json.loads(path.read_text()):
            properties_by_id.setdefault(int(entry["sample_library_id"]), entry)

    # spectra[kind][library_id] = {"table": <repo-relative path>, "entry": <raw entry>}
    spectra: dict[str, dict[int, dict[str, Any]]] = {"xrd": {}, "optical": {}}
    root = project_root()
    for path in sorted(cache_dir.glob("spectra_*.json")):
        payload = json.loads(path.read_text())
        rel = str(path.relative_to(root))
        for kind in ("xrd", "optical"):
            for entry in payload.get(kind, []):
                spectra[kind].setdefault(
                    int(entry["sample_library_id"]), {"table": rel, "entry": entry}
                )
    return records_by_id, properties_by_id, spectra


def positions_with_counts(entry: dict[str, Any]) -> list[tuple[int, int]]:
    """Sorted (position, n_points) pairs from a flat spectra entry."""
    counts = Counter(int(p) for p in entry.get("position", []) if p is not None)
    return sorted(counts.items())


def scalar_or_none(values: Any, index: int) -> Any:
    if isinstance(values, list) and index < len(values):
        return values[index]
    return None


def spatial(prop_entry: dict, index: int) -> dict[str, Any] | None:
    x = scalar_or_none(prop_entry.get("x_mm"), index)
    y = scalar_or_none(prop_entry.get("y_mm"), index)
    if x is None and y is None:
        return None
    return {"x": x, "y": y, "unit": "mm"}


def build_intent(record: dict) -> dict[str, Any] | None:
    planned = {
        f: record[f] for f in DEPOSITION_FIELDS
        if record.get(f) not in (None, "", [])
    }
    if not planned:
        return None
    return {"plan_id": None, "event_group_id": None, "planned": planned}


def build_provenance(record: dict) -> dict[str, Any]:
    person = record.get("person_id")
    pdac = record.get("pdac")
    date = record.get("sample_date")
    return {
        "operator_id": str(person) if person not in (None, "") else None,
        "lab_id": None,
        "batch_id": None,
        "lot_id": None,
        "instrument_id": f"pdac_{pdac}" if pdac not in (None, "") else None,
        "instrument_session_id": None,
        "measurement_day": str(date)[:10] if date not in (None, "") else None,
        "run_order": None,
        "source_dataset": "htem",
    }


def build_observations(
    library_id: int,
    prop_entry: dict,
    xrd_loc: dict[str, Any],
    optical_loc: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    prop_positions = prop_entry.get("position") or []
    index_by_position = {int(p): i for i, p in enumerate(prop_positions) if p is not None}
    observations: list[dict[str, Any]] = []

    def base(position: int, modality: str) -> dict[str, Any]:
        index = index_by_position.get(position)
        return {
            "observation_id": f"htem_{library_id}_p{position:02d}_{modality}",
            "modality": modality,
            "kind": "measurement",
            "stage": None,
            "order_index": position,
            "spatial_position": spatial(prop_entry, index) if index is not None else None,
        }

    for position, n_points in positions_with_counts(xrd_loc["entry"]):
        obs = base(position, "xrd")
        index = index_by_position.get(position)
        peak_count = scalar_or_none(prop_entry.get("peak_count"), index) if index is not None \
            else None
        obs["file_path"] = xrd_loc["table"]
        obs["payload"] = {"htem": {
            "table": xrd_loc["table"], "spectra_key": "xrd", "sample_library_id": library_id,
            "position": position, "n_points": n_points, "peak_count": peak_count,
        }}
        observations.append(obs)

    if optical_loc is not None:
        for position, n_points in positions_with_counts(optical_loc["entry"]):
            obs = base(position, "optical_absorption")
            obs["file_path"] = optical_loc["table"]
            obs["payload"] = {"htem": {
                "table": optical_loc["table"], "spectra_key": "optical",
                "sample_library_id": library_id, "position": position, "n_points": n_points,
            }}
            observations.append(obs)

    for position, index in sorted(index_by_position.items()):
        for modality, fields in PROPERTY_MODALITIES:
            values = {f: scalar_or_none(prop_entry.get(f), index) for f in fields}
            if all(v is None for v in values.values()):
                continue
            obs = base(position, modality)
            obs["payload"] = {"htem": {"position": position, **values}}
            observations.append(obs)
        temp = scalar_or_none(prop_entry.get("absolute_temp_c"), index)
        if temp is not None:
            obs = base(position, "temperature")
            obs["kind"] = None  # source does not document what this per-position temp is
            obs["payload"] = {"htem": {"position": position, "absolute_temp_c": temp}}
            observations.append(obs)

    return observations


def build_events(cache_dir: Path) -> list[dict[str, Any]]:
    records_by_id, properties_by_id, spectra = load_cache(cache_dir)
    library_ids = sorted(set(properties_by_id) & set(spectra["xrd"]) & set(records_by_id))

    events: list[dict[str, Any]] = []
    for library_id in library_ids:
        record = records_by_id[library_id]
        date = record.get("sample_date")
        events.append({
            "event_id": f"htem_sample_library_{library_id}",
            "system": "thin_film_library",
            "created_at": str(date) if date not in (None, "") else None,
            "intent": build_intent(record),
            "observations": build_observations(
                library_id,
                properties_by_id[library_id],
                spectra["xrd"][library_id],
                spectra["optical"].get(library_id),
            ),
            "outcome": {"status": "unknown", "summary": None, "notes": None},
            "provenance": build_provenance(record),
            "labels": None,
            "source_extras": {f: record.get(f) for f in SOURCE_EXTRA_FIELDS},
        })
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=Path("data/interim/htem_event_proxy"))
    parser.add_argument(
        "--output", type=Path, default=Path("data/interim/event_grammar_v1/htem/events.json")
    )
    args = parser.parse_args()

    root = project_root()
    cache_dir = args.cache_dir if args.cache_dir.is_absolute() else root / args.cache_dir
    output = args.output if args.output.is_absolute() else root / args.output

    events = build_events(cache_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(events, indent=1, sort_keys=True) + "\n")

    n_obs = sum(len(e["observations"]) for e in events)
    print(f"wrote {len(events)} events ({n_obs} observations) -> {output.relative_to(root)}")


if __name__ == "__main__":
    main()
