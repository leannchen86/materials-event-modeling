"""Graded conformance checks for event-grammar datasets (L0-L3).

A dataset of events (schemas/event_grammar.v1.schema.json envelopes, or legacy
material_event records) is graded on cumulative levels:

* **L0 — raw trace.** Unique event boundaries; observations carry raw payloads
  (inline or by file reference) and are orderable by some index (time, space,
  cycle, frame, or explicit order).
* **L1 — provenance.** At least two provenance axes (operator, lab, batch, lot,
  instrument, session, day, run order) are actually logged across the dataset.
* **L2 — negatives + frozen labels.** Outcome status is recorded per event with
  failed/ambiguous/aborted outcomes retained, and labels (where present) are
  marked as assigned after the raw record was frozen.
* **L3 — counterbalanced design.** Replicated plan groups exist and provenance
  varies within them (replicate-level counterbalancing, the pilot-stress lesson).

The level is the highest k with every check at levels <= k passing. A dataset
that fails L0 is "below_l0": expressible in the envelope but not event-shaped.
Checks return evidence (fractions, counts, examples), not just booleans — the
point is a conformance *report* a data producer can act on, and metrics such as
``trace_richness`` are reported without gating a level.

Design note: docs/spine/event_grammar_validation_note.md. This module extends
(and imports from) track_b.event_ingest rather than replacing it: event_ingest
answers "is this pilot ready for the planned analyses", conformance answers
"how much of the event grammar does this dataset actually record".
"""

from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Any

from materials_event_modeling.track_b.event_ingest import (
    event_observations,
    normalize_missing,
    value_from_event,
)

CONFORMANCE_LEVELS: dict[int, str] = {
    -1: "below_l0",
    0: "l0_raw_trace",
    1: "l1_provenance",
    2: "l2_negatives_frozen_labels",
    3: "l3_counterbalanced",
}

# Provenance axes that count toward L1. source_dataset is excluded: it is
# constant within any single-dataset audit and would be a free pass.
PROVENANCE_AXES: tuple[str, ...] = (
    "operator_id",
    "lab_id",
    "batch_id",
    "lot_id",
    "instrument_id",
    "instrument_session_id",
    "measurement_day",
    "run_order",
)

# Observation keys that make a trajectory orderable.
INDEX_KEYS: tuple[str, ...] = (
    "timestamp",
    "timepoint_minutes",
    "time_s",
    "cycle_index",
    "frame_index",
    "order_index",
    "spatial_position",
)

NEGATIVE_STATUSES = {"failure", "ambiguous", "aborted"}

# Fraction thresholds (explicit so a report can cite them; heuristic, tunable).
PAYLOAD_FRACTION = 0.9
ORDERABLE_FRACTION = 0.9
PROVENANCE_FRACTION = 0.9
OUTCOME_FRACTION = 0.9
FROZEN_LABEL_FRACTION = 0.9
MIN_REPLICATED_GROUPS = 4


def _has_payload(observation: dict[str, Any]) -> bool:
    payload = observation.get("payload")
    if isinstance(payload, dict) and payload:
        return True
    return observation.get("file_path") not in {"", None}


def _has_index(observation: dict[str, Any]) -> bool:
    for key in INDEX_KEYS:
        value = observation.get(key)
        if key == "spatial_position":
            if isinstance(value, dict) and any(
                value.get(axis) is not None for axis in ("x", "y")
            ):
                return True
        elif value not in {"", None}:
            return True
    return False


def _event_outcome_status(event: dict[str, Any]) -> str | None:
    outcome = event.get("outcome")
    if isinstance(outcome, dict):
        status = outcome.get("status")
        if status not in {"", None}:
            return str(status)
    return None


def _plan_signature(event: dict[str, Any]) -> str | None:
    """Plan signature from the envelope intent, falling back to legacy fields."""
    intent = event.get("intent")
    if isinstance(intent, dict):
        planned = intent.get("planned")
        if isinstance(planned, dict):
            parts = [
                f"{key}={planned[key]}"
                for key in sorted(planned)
                if planned[key] not in {"", None}
            ]
            if parts:
                return "|".join(parts)
        if intent.get("plan_id") not in {"", None}:
            return str(intent["plan_id"])
        if intent.get("event_group_id") not in {"", None}:
            return str(intent["event_group_id"])
    process = event.get("process") or {}
    planned = process.get("planned_conditions") or process.get("conditions") or {}
    parts = [
        f"{key}={planned[key]}" for key in sorted(planned) if planned[key] not in {"", None}
    ]
    if parts:
        return "|".join(parts)
    legacy_plan = event.get("pre_registered_plan_id")
    if legacy_plan not in {"", None}:
        return str(legacy_plan)
    return None


def _event_labels(event: dict[str, Any]) -> list[dict[str, Any]]:
    labels = event.get("labels") or {}
    entries = labels.get("entries")
    if isinstance(entries, list):
        return [entry for entry in entries if isinstance(entry, dict)]
    # Legacy field name.
    human = labels.get("human_labels")
    if isinstance(human, list):
        return [entry for entry in human if isinstance(entry, dict)]
    return []


def check_l0(events: list[dict[str, Any]]) -> dict[str, Any]:
    event_ids = [event.get("event_id") for event in events]
    unique_ids = len(set(event_ids)) == len(event_ids) and all(
        e not in {"", None} for e in event_ids
    )

    with_payload = 0
    orderable = 0
    multi_obs = 0
    obs_counts: list[int] = []
    for event in events:
        observations = event_observations(event)
        obs_counts.append(len(observations))
        if any(_has_payload(obs) for obs in observations):
            with_payload += 1
        if len(observations) >= 2:
            multi_obs += 1
            if all(_has_index(obs) for obs in observations):
                orderable += 1

    n = max(len(events), 1)
    payload_fraction = with_payload / n
    # Orderability is judged on events where ordering is meaningful (>= 2 obs).
    orderable_fraction = orderable / multi_obs if multi_obs else 1.0

    checks = {
        "nonempty": len(events) > 0,
        "unique_event_ids": bool(unique_ids),
        "payload_fraction": payload_fraction >= PAYLOAD_FRACTION,
        "orderable_fraction": orderable_fraction >= ORDERABLE_FRACTION,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "evidence": {
            "event_count": len(events),
            "events_with_payload_fraction": round(payload_fraction, 3),
            "orderable_multi_obs_fraction": round(orderable_fraction, 3),
            "multi_observation_events": multi_obs,
        },
        # Richness is reported, not gated: single-observation events are valid
        # events, but a dataset of them is a measurement archive, not traces.
        "trace_richness": {
            "median_observations_per_event": median(obs_counts) if obs_counts else 0,
            "multi_observation_fraction": round(multi_obs / n, 3),
        },
    }


def check_l1(events: list[dict[str, Any]]) -> dict[str, Any]:
    n = max(len(events), 1)
    axis_coverage: dict[str, float] = {}
    axis_distinct: dict[str, int] = {}
    for axis in PROVENANCE_AXES:
        values = [value_from_event(event, axis) for event in events]
        non_null = [v for v in values if v not in {"", None}]
        axis_coverage[axis] = round(len(non_null) / n, 3)
        axis_distinct[axis] = len({str(v) for v in non_null})

    logged_axes = [
        axis for axis in PROVENANCE_AXES if axis_coverage[axis] >= PROVENANCE_FRACTION
    ]
    return {
        "passed": len(logged_axes) >= 2,
        "checks": {"at_least_two_axes_logged": len(logged_axes) >= 2},
        "evidence": {
            "logged_axes": logged_axes,
            "axis_coverage": axis_coverage,
            "axis_distinct_values": axis_distinct,
        },
    }


def check_l2(events: list[dict[str, Any]]) -> dict[str, Any]:
    n = max(len(events), 1)
    statuses = [_event_outcome_status(event) for event in events]
    with_status = sum(1 for s in statuses if s is not None)
    negatives = sum(1 for s in statuses if s in NEGATIVE_STATUSES)

    labeled_events = [event for event in events if _event_labels(event)]
    if labeled_events:
        frozen = sum(
            1
            for event in labeled_events
            if (event.get("labels") or {}).get("assigned_after_raw_data_frozen") is True
        )
        frozen_fraction = frozen / len(labeled_events)
    else:
        frozen_fraction = None  # no labels: freezing is not applicable

    checks = {
        "outcome_status_fraction": with_status / n >= OUTCOME_FRACTION,
        "negative_outcomes_retained": negatives >= 1,
        "labels_frozen_after_raw": (
            frozen_fraction is None or frozen_fraction >= FROZEN_LABEL_FRACTION
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "evidence": {
            "events_with_outcome_status_fraction": round(with_status / n, 3),
            "negative_outcome_count": negatives,
            "labeled_event_count": len(labeled_events),
            "frozen_label_fraction": (
                round(frozen_fraction, 3) if frozen_fraction is not None else None
            ),
        },
    }


def check_l3(events: list[dict[str, Any]]) -> dict[str, Any]:
    groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        signature = _plan_signature(event)
        if signature is not None:
            groups[signature].append(event)

    replicated = {sig: evs for sig, evs in groups.items() if len(evs) >= 2}
    varied_groups = 0
    for evs in replicated.values():
        for axis in PROVENANCE_AXES:
            values = {normalize_missing(value_from_event(event, axis)) for event in evs}
            values.discard("missing")
            if len(values) >= 2:
                varied_groups += 1
                break

    checks = {
        "replicated_plan_groups": len(replicated) >= MIN_REPLICATED_GROUPS,
        "provenance_varies_within_groups": (
            len(replicated) > 0 and varied_groups >= max(1, len(replicated) // 2)
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "evidence": {
            "plan_group_count": len(groups),
            "replicated_group_count": len(replicated),
            "groups_with_provenance_variation": varied_groups,
        },
    }


def selection_risk(events: list[dict[str, Any]], levels: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """Flag the data-selection risks that ARE visible in the events themselves.

    Deliberately narrow. Most selection biases of public data — publication bias toward
    successes, pre-filtered "excellent" subsets, single-institution curation, "raw" that
    was already processed — are NOT in the events and cannot be measured here; they are
    stated in docs/spine/data_assumptions_and_limits.md. This surfaces only the two
    facets the record exposes: whether negatives were retained (success-bias), and how
    many independent provenance units exist (few-clusters risk). Absence of a flag is not
    absence of bias.
    """
    l1, l2 = levels[1]["evidence"], levels[2]["evidence"]
    negatives = l2["negative_outcome_count"]
    status_fraction = l2["events_with_outcome_status_fraction"]
    distinct = l1["axis_distinct_values"]
    logged = l1["logged_axes"]
    logged_unit_counts = {a: distinct[a] for a in logged}
    min_units = min(logged_unit_counts.values()) if logged_unit_counts else 0

    if status_fraction < OUTCOME_FRACTION:
        success_bias = "unknown_outcomes_not_recorded"
    elif negatives == 0:
        success_bias = "high_no_negatives_recorded"  # success-biased or failures filtered
    elif negatives < 0.05 * max(len(events), 1):
        success_bias = "elevated_few_negatives"
    else:
        success_bias = "low_negatives_present"

    return {
        "success_bias_risk": success_bias,
        "negative_outcome_count": negatives,
        "provenance_units_per_logged_axis": logged_unit_counts,
        "min_independent_provenance_units": min_units,
        # Provenance claims live at the unit level; few units = wide CIs, weak transfer.
        "few_provenance_units_risk": "high" if 0 < min_units < 5 else (
            "none_logged" if not logged_unit_counts else "lower"
        ),
        "note": "Measures only success-bias and provenance-unit count. Publication bias, "
                "pre-filtering, single-source curation, and processing-before-deposit are "
                "NOT visible here — see docs/spine/data_assumptions_and_limits.md.",
    }


def conformance_report(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Grade a dataset of events on the L0-L3 conformance ladder."""
    levels = {
        0: check_l0(events),
        1: check_l1(events),
        2: check_l2(events),
        3: check_l3(events),
    }
    level = -1
    for k in (0, 1, 2, 3):
        if levels[k]["passed"]:
            level = k
        else:
            break
    return {
        "task": "event_grammar_conformance",
        "grammar_version": "v1",
        "event_count": len(events),
        "level": level,
        "level_name": CONFORMANCE_LEVELS[level],
        "levels": {CONFORMANCE_LEVELS[k]: report for k, report in levels.items()},
        "selection_risk": selection_risk(events, levels),
        "thresholds": {
            "payload_fraction": PAYLOAD_FRACTION,
            "orderable_fraction": ORDERABLE_FRACTION,
            "provenance_fraction": PROVENANCE_FRACTION,
            "outcome_fraction": OUTCOME_FRACTION,
            "frozen_label_fraction": FROZEN_LABEL_FRACTION,
            "min_replicated_groups": MIN_REPLICATED_GROUPS,
        },
        "caveats": [
            "Levels grade what the dataset RECORDS, not the quality of the science.",
            "A dataset with no negative outcomes fails L2 by design: from the outside, "
            "'all successes' and 'failures filtered out' are indistinguishable.",
            "trace_richness is reported but not gated: single-observation events are "
            "valid, but a dataset of them is a measurement archive, not event traces.",
        ],
    }
