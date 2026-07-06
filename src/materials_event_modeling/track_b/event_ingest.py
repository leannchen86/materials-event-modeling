"""LEGACY pilot-readiness audit for material_event records (Track B mock CaCO3 set).

Consumed only by ``scripts/audit_track_b_event_dataset.py`` on the legacy
``material_event.schema.json`` shape. It keeps its own dict-based reader on purpose: its
``provenance_counts`` deliberately bundles ``pre_registered_plan_id`` and
``raw_export_profile`` alongside the collection axes — a flatter shape than the typed
``grammar.event.Event`` (which separates intent / provenance / per-observation export).
Forcing it onto the typed model would change this readiness report for no active benefit.

For all NEW / grammar-v1 data, the canonical parser is ``grammar.event.parse_event`` and
the grader is ``grammar.conformance`` — use those, not this module.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

AMBIGUITY_TERMS = {
    "ambiguous",
    "uncertain",
    "possible",
    "mixed",
    "mixture",
    "transition",
    "partial",
    "variation",
    "low_signal",
}

FAILURE_TERMS = {
    "fail",
    "failed",
    "failure",
    "no_product",
    "no_precipitate",
    "bad",
    "invalid",
    "deviation",
}


@dataclass(frozen=True)
class EventAudit:
    event_count: int
    modality_counts: dict[str, int]
    observation_counts_by_modality: dict[str, int]
    provenance_counts: dict[str, int]
    label_counts: dict[str, int]
    readiness: dict[str, Any]
    warnings: list[str]


def load_event_records(path: Path) -> list[dict[str, Any]]:
    """Load a single event, a JSON array, or JSON files from a directory."""

    if path.is_dir():
        events: list[dict[str, Any]] = []
        for child in sorted(path.glob("*.json")):
            events.extend(load_event_records(child))
        return events

    payload = json.loads(path.read_text())
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    raise TypeError(f"unsupported event JSON payload in {path}")


def value_from_event(event: dict[str, Any], key: str) -> Any:
    provenance = event.get("provenance") or {}
    if key in provenance and provenance[key] not in {"", None}:
        return provenance[key]
    return event.get(key)


def normalize_missing(value: Any) -> str:
    if value in {"", None}:
        return "missing"
    return str(value)


def modality_measurements(event: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    measurements = event.get("measurements") or {}
    normalized = {}
    for modality, entries in measurements.items():
        if isinstance(entries, list):
            normalized[modality] = [entry for entry in entries if isinstance(entry, dict)]
        elif isinstance(entries, dict):
            normalized[modality] = [entries]
        else:
            normalized[modality] = []
    return normalized


def event_observations(event: dict[str, Any]) -> list[dict[str, Any]]:
    observations = event.get("observations")
    if isinstance(observations, list):
        return [entry for entry in observations if isinstance(entry, dict)]

    synthesized = []
    for modality, entries in modality_measurements(event).items():
        for idx, entry in enumerate(entries):
            synthesized.append(
                {
                    "observation_id": f"{event.get('event_id', 'event')}_{modality}_{idx}",
                    "modality": modality,
                    "file_path": entry.get("file_path"),
                    "instrument_id": entry.get("instrument_id"),
                    "instrument_session_id": entry.get("instrument_session_id"),
                    "raw_export_format": entry.get("raw_export_format"),
                    "timestamp": entry.get("measurement_time") or entry.get("timestamp"),
                    "include_in_raw_objective": event.get("data_quality", {}).get(
                        "include_in_raw_objective"
                    ),
                }
            )
    return synthesized


def planned_signature(event: dict[str, Any]) -> str:
    process = event.get("process") or {}
    planned = process.get("planned_conditions") or process.get("conditions") or {}
    parts = []
    for key in sorted(planned):
        value = planned[key]
        if value not in {"", None}:
            parts.append(f"{key}={value}")
    return "|".join(parts) or normalize_missing(event.get("pre_registered_plan_id"))


def label_terms(label: str) -> set[str]:
    lowered = label.lower().replace("-", "_")
    return set(lowered.split("_")) | {lowered}


def labels_for_event(event: dict[str, Any]) -> list[str]:
    labels = event.get("labels") or {}
    human_labels = labels.get("human_labels") or []
    return [
        str(label.get("label"))
        for label in human_labels
        if isinstance(label, dict) and label.get("label") not in {"", None}
    ]


def summarize_modalities(events: list[dict[str, Any]]) -> tuple[Counter[str], Counter[str]]:
    measurement_counts: Counter[str] = Counter()
    observation_counts: Counter[str] = Counter()
    for event in events:
        for modality, entries in modality_measurements(event).items():
            measurement_counts[modality] += len(entries)
        for observation in event_observations(event):
            observation_counts[normalize_missing(observation.get("modality"))] += 1
    return measurement_counts, observation_counts


def summarize_provenance(events: list[dict[str, Any]]) -> dict[str, int]:
    keys = [
        "operator_id",
        "lab_id",
        "batch_id",
        "pre_registered_plan_id",
        "instrument_session_id",
        "source_dataset",
        "raw_export_profile",
    ]
    return {
        key: len({normalize_missing(value_from_event(event, key)) for event in events})
        for key in keys
    }


def file_reference_report(events: list[dict[str, Any]], *, base_dir: Path | None) -> dict[str, Any]:
    paths = []
    for event in events:
        for observation in event_observations(event):
            file_path = observation.get("file_path")
            if file_path:
                paths.append(str(file_path))
    if base_dir is None:
        return {"referenced_files": len(paths), "checked_files": False}

    missing = []
    for file_path in paths:
        candidate = Path(file_path)
        if not candidate.is_absolute():
            candidate = base_dir / candidate
        if not candidate.exists():
            missing.append(file_path)
    return {
        "referenced_files": len(paths),
        "checked_files": True,
        "missing_referenced_files": len(missing),
        "missing_examples": missing[:10],
    }


def readiness_report(events: list[dict[str, Any]]) -> dict[str, Any]:
    event_count = len(events)
    observations_by_event = {event.get("event_id"): event_observations(event) for event in events}
    modality_sets = {
        event_id: {normalize_missing(obs.get("modality")) for obs in observations}
        for event_id, observations in observations_by_event.items()
    }
    partial_ready_events = {
        event_id: sum(1 for obs in observations if obs.get("include_in_raw_objective") is not False)
        for event_id, observations in observations_by_event.items()
    }
    events_with_multiple_modalities = sum(len(modalities) >= 2 for modalities in modality_sets.values())
    events_with_partial_observations = sum(count >= 3 for count in partial_ready_events.values())
    label_counts = Counter(label for event in events for label in labels_for_event(event))
    ambiguity_labels = 0
    failure_labels = 0
    for label, count in label_counts.items():
        terms = label_terms(label)
        if terms & AMBIGUITY_TERMS:
            ambiguity_labels += count
        if terms & FAILURE_TERMS:
            failure_labels += count

    planned_groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        planned_groups[planned_signature(event)].append(event)
    replicate_group_count = sum(len(group) >= 2 for group in planned_groups.values())

    return {
        "masked_event_reconstruction": {
            "ready": events_with_partial_observations >= 8,
            "events_with_at_least_3_observations": events_with_partial_observations,
            "criterion": "at least 8 events with >=3 event-internal observations",
        },
        "missing_modality_prediction": {
            "ready": events_with_multiple_modalities >= 8,
            "events_with_at_least_2_modalities": events_with_multiple_modalities,
            "criterion": "at least 8 events with >=2 modalities",
        },
        "provenance_shortcut_tests": {
            "ready": event_count >= 12,
            "criterion": "at least 12 events plus nontrivial provenance variation",
        },
        "failure_ambiguity_as_data": {
            "ready": (ambiguity_labels + failure_labels) > 0,
            "ambiguity_label_count": ambiguity_labels,
            "failure_label_count": failure_labels,
            "criterion": "retain ambiguous/failed/partial labels as probes",
        },
        "replicate_retrieval": {
            "ready": replicate_group_count >= 4,
            "replicate_group_count": replicate_group_count,
            "criterion": "at least 4 planned-condition groups with replicates",
        },
        "event_native_vs_label_baseline": {
            "ready": event_count >= 24 and len(label_counts) >= 2,
            "label_count": len(label_counts),
            "criterion": "enough events and labels to compare event objectives against label baselines",
        },
    }


def confounding_warnings(events: list[dict[str, Any]]) -> list[str]:
    warnings = []
    groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        groups[planned_signature(event)].append(event)

    for plan, plan_events in groups.items():
        if len(plan_events) < 2:
            continue
        operators = {normalize_missing(value_from_event(event, "operator_id")) for event in plan_events}
        batches = {normalize_missing(value_from_event(event, "batch_id")) for event in plan_events}
        if len(operators) == 1:
            warnings.append(f"planned group '{plan}' has replicates from only one operator")
        if len(batches) == 1:
            warnings.append(f"planned group '{plan}' has replicates from only one batch")
    return warnings


def audit_events(
    events: list[dict[str, Any]],
    *,
    file_base_dir: Path | None = None,
) -> dict[str, Any]:
    measurement_counts, observation_counts = summarize_modalities(events)
    label_counts = Counter(label for event in events for label in labels_for_event(event))
    frozen_label_count = sum(
        1 for event in events if (event.get("labels") or {}).get("assigned_after_raw_data_frozen")
    )
    warnings = confounding_warnings(events)

    return {
        "event_count": len(events),
        "systems": dict(sorted(Counter(event.get("system", "missing") for event in events).items())),
        "modality_counts": dict(sorted(measurement_counts.items())),
        "observation_counts_by_modality": dict(sorted(observation_counts.items())),
        "provenance_counts": summarize_provenance(events),
        "labels_as_probes": dict(sorted(label_counts.items())),
        "labels_frozen_after_raw_data": {
            "events_with_frozen_labels": frozen_label_count,
            "events_without_frozen_labels": len(events) - frozen_label_count,
        },
        "file_references": file_reference_report(events, base_dir=file_base_dir),
        "readiness": readiness_report(events),
        "warnings": warnings,
    }
