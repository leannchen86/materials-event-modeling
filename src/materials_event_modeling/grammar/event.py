"""Typed event-grammar v1 envelope and boundary parser.

Everything downstream consumes the frozen ``Event`` structure rather than raw dictionaries.
The parser normalizes types but leaves grouping, richness, and outcome meaning to consumers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Provenance axes that can carry collection identity. source_dataset is excluded from
# `axes()` (constant within a single-dataset audit) but kept on the record.
PROVENANCE_AXES: tuple[str, ...] = (
    "operator_id", "lab_id", "batch_id", "lot_id",
    "instrument_id", "instrument_session_id", "measurement_day", "run_order",
)


def _as_float(value: object) -> float | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_str(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


@dataclass(frozen=True)
class SpatialPosition:
    x: float | None
    y: float | None


@dataclass(frozen=True)
class Observation:
    observation_id: str
    modality: str
    kind: str | None
    stage: str | None
    timestamp: str | None
    timepoint_minutes: float | None
    time_s: float | None
    cycle_index: float | None
    frame_index: float | None
    order_index: float | None
    spatial_position: SpatialPosition | None
    payload: dict[str, Any] | None
    file_path: str | None
    include_in_raw_objective: bool | None

    @property
    def has_payload(self) -> bool:
        return bool(self.payload) or self.file_path is not None

    @property
    def has_index(self) -> bool:
        if any(v is not None for v in (
            self.timestamp, self.timepoint_minutes, self.time_s,
            self.cycle_index, self.frame_index, self.order_index,
        )):
            return True
        pos = self.spatial_position
        return pos is not None and (pos.x is not None or pos.y is not None)

    @property
    def kept_for_raw_objective(self) -> bool:
        return self.include_in_raw_objective is not False


@dataclass(frozen=True)
class Provenance:
    operator_id: str | None
    lab_id: str | None
    batch_id: str | None
    lot_id: str | None
    instrument_id: str | None
    instrument_session_id: str | None
    measurement_day: str | None
    run_order: float | None
    source_dataset: str | None

    def axis(self, name: str) -> str | None:
        """Stringified value of one provenance axis (for distinct-count / grouping)."""
        value = getattr(self, name)
        return None if value is None else str(value)


@dataclass(frozen=True)
class Intent:
    plan_id: str | None
    event_group_id: str | None
    planned: dict[str, Any]

    def signature(self) -> tuple[tuple[str, str], ...] | None:
        """Structured, hashable plan key — NOT a concatenated string (a value containing
        '|' or '=' can't collide, and the structure is preserved). None when no plan."""
        parts = tuple(
            (key, str(self.planned[key]))
            for key in sorted(self.planned)
            if self.planned[key] not in (None, "")
        )
        if parts:
            return parts
        if self.plan_id is not None:
            return (("plan_id", self.plan_id),)
        if self.event_group_id is not None:
            return (("event_group_id", self.event_group_id),)
        return None


@dataclass(frozen=True)
class Label:
    labeler_id: str
    label: str


@dataclass(frozen=True)
class Labels:
    assigned_after_raw_data_frozen: bool | None
    entries: tuple[Label, ...]


@dataclass(frozen=True)
class Outcome:
    status: str  # success | failure | ambiguous | aborted | unknown
    summary: dict[str, Any] | None
    # Was an outcome status EXPLICITLY recorded? An event that deliberately logs
    # status="unknown" (an honest "we don't know") is distinct from one with no outcome
    # field at all — conformance counts the former as "outcome recorded", not the latter.
    recorded: bool


@dataclass(frozen=True)
class Event:
    event_id: str
    system: str
    intent: Intent | None
    observations: tuple[Observation, ...]
    outcome: Outcome
    provenance: Provenance
    labels: Labels | None


NEGATIVE_STATUSES = frozenset({"failure", "ambiguous", "aborted"})


# --------------------------------------------------------------------------------------
# Boundary parser.
# --------------------------------------------------------------------------------------


def _parse_spatial(raw: object) -> SpatialPosition | None:
    if not isinstance(raw, dict):
        return None
    x, y = _as_float(raw.get("x")), _as_float(raw.get("y"))
    if x is None and y is None:
        return None
    return SpatialPosition(x=x, y=y)


def _parse_observation(raw: dict[str, Any]) -> Observation:
    return Observation(
        observation_id=str(raw["observation_id"]),
        modality=str(raw["modality"]),
        kind=_as_str(raw.get("kind")),
        stage=_as_str(raw.get("stage")),
        timestamp=_as_str(raw.get("timestamp") or raw.get("measurement_time")),
        timepoint_minutes=_as_float(raw.get("timepoint_minutes")),
        time_s=_as_float(raw.get("time_s")),
        cycle_index=_as_float(raw.get("cycle_index")),
        frame_index=_as_float(raw.get("frame_index")),
        order_index=_as_float(raw.get("order_index")),
        spatial_position=_parse_spatial(raw.get("spatial_position")),
        payload=raw.get("payload") if isinstance(raw.get("payload"), dict) else None,
        file_path=_as_str(raw.get("file_path")),
        include_in_raw_objective=(
            raw["include_in_raw_objective"]
            if isinstance(raw.get("include_in_raw_objective"), bool)
            else None
        ),
    )


def _parse_provenance(raw: dict[str, Any]) -> Provenance:
    prov_raw = raw.get("provenance")
    prov = prov_raw if isinstance(prov_raw, dict) else {}
    return Provenance(
        operator_id=_as_str(prov.get("operator_id")),
        lab_id=_as_str(prov.get("lab_id")),
        batch_id=_as_str(prov.get("batch_id")),
        lot_id=_as_str(prov.get("lot_id")),
        instrument_id=_as_str(prov.get("instrument_id")),
        instrument_session_id=_as_str(prov.get("instrument_session_id")),
        measurement_day=_as_str(prov.get("measurement_day")),
        run_order=_as_float(prov.get("run_order")),
        source_dataset=_as_str(prov.get("source_dataset")),
    )


def _parse_intent(raw: dict[str, Any]) -> Intent | None:
    intent = raw.get("intent")
    if isinstance(intent, dict):
        planned = intent.get("planned")
        return Intent(
            plan_id=_as_str(intent.get("plan_id")),
            event_group_id=_as_str(intent.get("event_group_id")),
            planned=planned if isinstance(planned, dict) else {},
        )
    return None


def _parse_labels(raw: dict[str, Any]) -> Labels | None:
    labels = raw.get("labels")
    if not isinstance(labels, dict):
        return None
    raw_entries = labels.get("entries")
    entries: list[Label] = []
    if isinstance(raw_entries, list):
        for entry in raw_entries:
            if isinstance(entry, dict) and entry.get("label") not in (None, ""):
                entries.append(Label(
                    labeler_id=str(entry.get("labeler_id", "unknown")),
                    label=str(entry["label"]),
                ))
    frozen = labels.get("assigned_after_raw_data_frozen")
    return Labels(
        assigned_after_raw_data_frozen=frozen if isinstance(frozen, bool) else None,
        entries=tuple(entries),
    )


def _parse_outcome(raw: dict[str, Any]) -> Outcome:
    outcome = raw.get("outcome")
    if isinstance(outcome, dict) and outcome.get("status") not in (None, ""):
        summary = outcome.get("summary")
        return Outcome(
            status=str(outcome["status"]),
            summary=summary if isinstance(summary, dict) else None,
            recorded=True,
        )
    return Outcome(status="unknown", summary=None, recorded=False)


def parse_event(raw: dict[str, Any]) -> Event:
    """Parse one event-grammar v1-shaped dictionary into a typed event."""
    raw_observations = raw.get("observations")
    observations = [
        _parse_observation(observation)
        for observation in raw_observations if isinstance(observation, dict)
    ] if isinstance(raw_observations, list) else []
    return Event(
        event_id=str(raw["event_id"]),
        system=str(raw.get("system", "unknown")),
        intent=_parse_intent(raw),
        observations=tuple(observations),
        outcome=_parse_outcome(raw),
        provenance=_parse_provenance(raw),
        labels=_parse_labels(raw),
    )


def load_events(path: Path) -> list[Event]:
    """Load a JSON array / single event / directory of JSON files, parsed to Events."""
    import json

    if path.is_dir():
        events: list[Event] = []
        for child in sorted(path.glob("*.json")):
            events.extend(load_events(child))
        return events
    payload = json.loads(path.read_text())
    raw_list = payload if isinstance(payload, list) else [payload]
    return [parse_event(r) for r in raw_list]
