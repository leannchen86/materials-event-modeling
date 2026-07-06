"""Audit HTEM DB as a public proxy for material-making event data."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HTEM_API_BASE_URL = "https://htem-api.nlr.gov/api"
HTEM_APP_URL = "https://htem.nlr.gov/"
HTEM_NREL_SUBMISSION_URL = "https://data.nrel.gov/submissions/75"
HTEM_PAPER_URL = "https://www.nature.com/articles/sdata201853"

MEASUREMENT_FIELDS = ("has_xrd", "has_xrf", "has_opt", "has_ele")
PROCESS_FIELDS = (
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
PROVENANCE_FIELDS = ("sample_date", "person_id", "pdac", "quality", "sciround")


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, list):
        return any(has_value(item) for item in value)
    if isinstance(value, dict):
        return any(has_value(item) for item in value.values())
    return True


def fetch_json(url: str, timeout: int = 120) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "materials-event-modeling/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def api_url(path: str, query: dict[str, str] | None = None) -> str:
    url = f"{HTEM_API_BASE_URL}/{path.lstrip('/')}"
    if query:
        return f"{url}?{urllib.parse.urlencode(query)}"
    return url


def compact_counter(values: list[Any], limit: int = 12) -> dict[str, int]:
    counter = Counter("null" if value is None else str(value) for value in values)
    return dict(counter.most_common(limit))


def field_completeness(records: list[dict[str, Any]], fields: tuple[str, ...]) -> dict[str, Any]:
    total = len(records)
    summary = {}
    for field in fields:
        nonempty = sum(has_value(record.get(field)) for record in records)
        summary[field] = {
            "nonempty": nonempty,
            "fraction": nonempty / total if total else None,
            "top_values": compact_counter([record.get(field) for record in records]),
        }
    return summary


def measurement_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    summary = {}
    for field in MEASUREMENT_FIELDS:
        values = [record.get(field) for record in records]
        nonzero = sum(isinstance(value, (int, float)) and value > 0 for value in values)
        summary[field] = {
            "nonzero": nonzero,
            "fraction": nonzero / total if total else None,
            "top_counts": compact_counter(values),
        }
    return summary


def event_proxy_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    per_record_process = [
        sum(has_value(record.get(field)) for field in PROCESS_FIELDS) for record in records
    ]
    per_record_measurement = [
        sum(isinstance(record.get(field), (int, float)) and record.get(field) > 0 for field in MEASUREMENT_FIELDS)
        for record in records
    ]
    composition_present = [has_value(record.get("elements")) for record in records]
    provenance_present = [
        any(has_value(record.get(field)) for field in PROVENANCE_FIELDS) for record in records
    ]
    date_and_person_present = [
        has_value(record.get("sample_date")) and has_value(record.get("person_id"))
        for record in records
    ]

    def count(mask: list[bool]) -> dict[str, float | int | None]:
        n = sum(mask)
        return {"count": n, "fraction": n / total if total else None}

    rich_mask = [
        composition_present[index]
        and per_record_process[index] > 0
        and per_record_measurement[index] > 0
        and provenance_present[index]
        for index in range(total)
    ]
    xrd_event_mask = [
        composition_present[index]
        and per_record_process[index] > 0
        and (isinstance(records[index].get("has_xrd"), (int, float)) and records[index].get("has_xrd") > 0)
        for index in range(total)
    ]

    return {
        "composition_present": count(composition_present),
        "any_process_field_present": count([value > 0 for value in per_record_process]),
        "any_measurement_present": count([value > 0 for value in per_record_measurement]),
        "any_provenance_present": count(provenance_present),
        "date_and_person_present": count(date_and_person_present),
        "composition_process_measurement_provenance": count(rich_mask),
        "composition_process_xrd": count(xrd_event_mask),
        "process_field_count_distribution": dict(Counter(per_record_process).most_common()),
        "measurement_modality_count_distribution": dict(Counter(per_record_measurement).most_common()),
    }


def element_system_summary(records: list[dict[str, Any]], limit: int = 15) -> dict[str, Any]:
    systems = [tuple(record.get("elements") or []) for record in records]
    element_counts = Counter(element for system in systems for element in system)
    return {
        "top_element_systems": {
            "|".join(system) if system else "none": count
            for system, count in Counter(systems).most_common(limit)
        },
        "top_elements": dict(element_counts.most_common(limit)),
        "unique_element_systems": len(set(systems)),
    }


def summarize_endpoint_payload(payload: Any) -> dict[str, Any]:
    raw_chars = len(json.dumps(payload, separators=(",", ":")))
    if isinstance(payload, dict):
        keys = sorted(payload)
        child_summaries = {}
        for key, value in payload.items():
            if isinstance(value, list):
                child_summaries[key] = summarize_list_payload(value)
        return {"type": "dict", "keys": keys, "raw_json_chars": raw_chars, "children": child_summaries}
    if isinstance(payload, list):
        return summarize_list_payload(payload) | {"raw_json_chars": raw_chars}
    return {"type": type(payload).__name__, "raw_json_chars": raw_chars}


def summarize_list_payload(values: list[Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {"type": "list", "length": len(values)}
    if not values:
        return summary
    first = values[0]
    if isinstance(first, dict):
        summary["entry_keys"] = sorted(first)
        entry_summaries = []
        for entry in values[:3]:
            array_lengths = {
                key: len(value) for key, value in entry.items() if isinstance(value, list)
            }
            entry_summaries.append(
                {
                    "sample_library_id": entry.get("sample_library_id"),
                    "array_lengths": array_lengths,
                }
            )
        summary["first_entries"] = entry_summaries
    return summary


def endpoint_probe(records: list[dict[str, Any]], max_ids: int) -> dict[str, Any]:
    xrd_ids = [
        str(record["id"])
        for record in records
        if isinstance(record.get("has_xrd"), (int, float)) and record.get("has_xrd") > 0
    ]
    selected_ids = xrd_ids[:max_ids]
    if not selected_ids:
        return {"selected_ids": [], "note": "No XRD-bearing sample_library ids found."}

    ids = ",".join(selected_ids)
    spectra = fetch_json(api_url("sample_library/spectra", {"ids": ids}), timeout=180)
    properties = fetch_json(api_url("sample_library/prop", {"ids": ids}), timeout=120)
    return {
        "selected_ids": selected_ids,
        "spectra_endpoint": api_url("sample_library/spectra", {"ids": ids}),
        "properties_endpoint": api_url("sample_library/prop", {"ids": ids}),
        "spectra_summary": summarize_endpoint_payload(spectra),
        "properties_summary": summarize_endpoint_payload(properties),
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    records_url = api_url("sample_library/count")
    records = fetch_json(records_url)
    if not isinstance(records, list):
        raise RuntimeError(f"Expected a list from {records_url}, got {type(records).__name__}")

    filter_probe = fetch_json(api_url("sample_library/count", {"has_xrd": "1"}))
    if not isinstance(filter_probe, list):
        filter_probe_count = None
    else:
        filter_probe_count = len(filter_probe)

    ids_with_xrd = [
        record["id"]
        for record in records
        if isinstance(record.get("has_xrd"), (int, float)) and record.get("has_xrd") > 0
    ]

    result = {
        "dataset_id": "htem",
        "task": "event_proxy_audit",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "api_records_url": records_url,
            "api_base_url": HTEM_API_BASE_URL,
            "app_url": HTEM_APP_URL,
            "nrel_submission_url": HTEM_NREL_SUBMISSION_URL,
            "paper_url": HTEM_PAPER_URL,
        },
        "pre_run_hypothesis": (
            "HTEM should be more event-like than opXRD because it exposes composition, "
            "process, measurement, and provenance fields, but it will probably remain a "
            "sample-library snapshot rather than a full event-trajectory dataset."
        ),
        "api_probe": {
            "records_endpoint_count": len(records),
            "has_xrd_filter_endpoint_count": filter_probe_count,
            "filter_note": (
                "The public count endpoint appears to return sample-library records; "
                "the has_xrd=1 query is kept only as a rough API-behavior probe."
            ),
        },
        "record_keys": sorted(records[0]) if records else [],
        "sample_count": len(records),
        "measurement_summary": measurement_summary(records),
        "process_field_completeness": field_completeness(records, PROCESS_FIELDS),
        "provenance_field_completeness": field_completeness(records, PROVENANCE_FIELDS),
        "event_proxy_summary": event_proxy_summary(records),
        "element_system_summary": element_system_summary(records),
        "quality_counts": compact_counter([record.get("quality") for record in records]),
        "pdac_counts": compact_counter([record.get("pdac") for record in records]),
        "xrd_sample_ids_first": ids_with_xrd[:25],
        "endpoint_probe": endpoint_probe(records, max_ids=args.endpoint_sample_ids)
        if args.endpoint_sample_ids > 0
        else {"selected_ids": [], "note": "Endpoint probe skipped."},
        "caveats": [
            "This audit checks whether HTEM can act as an event-data proxy; it is not a model benchmark.",
            "Sample-library records are not necessarily material-making trajectories.",
            "Nonempty process fields do not imply complete synthesis histories or comparable lab protocols.",
            "Measurement availability counts do not prove raw files are complete or consistently preprocessed.",
            "The public API may expose filtered or derived views of the original database.",
        ],
        "track_b_implications": [
            "Track B should log planned process variables, observed process trajectories, and raw measurement files separately.",
            "Track B should record instrument/session/operator/date fields before labels are assigned.",
            "Track B should avoid collapsing each sample into a static row when within-sample positions and spectra exist.",
            "Track B should preserve missing and failed measurements as first-class event outcomes.",
        ],
    }
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--endpoint-sample-ids",
        type=int,
        default=2,
        help="Number of XRD-bearing sample_library ids to probe via spectra/prop endpoints.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/htem_event_proxy_audit.json"),
        help="Path for the JSON audit summary.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = project_root()
    summary = audit(args)
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
