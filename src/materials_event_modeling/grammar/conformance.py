"""Graded conformance checks for event-grammar datasets (L0-L3).

A dataset of typed ``Event`` records (parsed by ``grammar.event.parse_event`` from either
the v1 envelope or the legacy material_event shape) is graded on cumulative levels:

* **L0 — adapted trace.** Unique event boundaries; observations carry payloads
  (inline or by file reference) and are orderable by some index (time, space,
  cycle, frame, or explicit order). L0 does not certify capture completeness.
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

Design note: docs/spine/event_grammar_validation_note.md. All shape reconciliation lives
in ``grammar.event``; here every access is a typed field on ``Event``.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Any

from materials_event_modeling.grammar.event import (
    NEGATIVE_STATUSES,
    PROVENANCE_AXES,
    Event,
)

CONFORMANCE_LEVELS: dict[int, str] = {
    -1: "below_l0",
    0: "l0_raw_trace",
    1: "l1_provenance",
    2: "l2_negatives_frozen_labels",
    3: "l3_counterbalanced",
}

# Fraction thresholds (explicit so a report can cite them; heuristic, tunable).
PAYLOAD_FRACTION = 0.9
ORDERABLE_FRACTION = 0.9
PROVENANCE_FRACTION = 0.9
OUTCOME_FRACTION = 0.9
FROZEN_LABEL_FRACTION = 0.9
MIN_REPLICATED_GROUPS = 4


def check_l0(events: list[Event]) -> dict[str, Any]:
    event_ids = [event.event_id for event in events]
    unique_ids = len(set(event_ids)) == len(event_ids) and all(event_ids)

    with_payload = 0
    orderable = 0
    multi_obs = 0
    obs_counts: list[int] = []
    for event in events:
        observations = event.observations
        obs_counts.append(len(observations))
        if any(obs.has_payload for obs in observations):
            with_payload += 1
        if len(observations) >= 2:
            multi_obs += 1
            if all(obs.has_index for obs in observations):
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


def check_l1(events: list[Event]) -> dict[str, Any]:
    n = max(len(events), 1)
    axis_coverage: dict[str, float] = {}
    axis_distinct: dict[str, int] = {}
    for axis in PROVENANCE_AXES:
        values = [event.provenance.axis(axis) for event in events]
        non_null = [v for v in values if v is not None]
        axis_coverage[axis] = round(len(non_null) / n, 3)
        axis_distinct[axis] = len(set(non_null))

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


def check_l2(events: list[Event]) -> dict[str, Any]:
    n = max(len(events), 1)
    # An explicit status (incl. a deliberate "unknown") counts as recorded; a missing
    # outcome field does not. Negatives are the failure/ambiguous/aborted statuses.
    with_status = sum(1 for event in events if event.outcome.recorded)
    negatives = sum(1 for event in events if event.outcome.status in NEGATIVE_STATUSES)

    labeled_events = [
        event for event in events if event.labels is not None and event.labels.entries
    ]
    if labeled_events:
        frozen = sum(
            1
            for event in labeled_events
            if event.labels is not None
            and event.labels.assigned_after_raw_data_frozen is True
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


def check_l3(events: list[Event]) -> dict[str, Any]:
    # Group by the structured plan signature (a hashable tuple, not a concat string).
    groups: defaultdict[tuple[tuple[str, str], ...], list[Event]] = defaultdict(list)
    for event in events:
        signature = event.intent.signature() if event.intent is not None else None
        if signature is not None:
            groups[signature].append(event)

    replicated = {sig: evs for sig, evs in groups.items() if len(evs) >= 2}
    varied_groups = 0
    for evs in replicated.values():
        for axis in PROVENANCE_AXES:
            values = {event.provenance.axis(axis) for event in evs}
            values.discard(None)
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


def selection_risk(events: list[Event], levels: dict[int, dict[str, Any]]) -> dict[str, Any]:
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


def conformance_report(events: list[Event]) -> dict[str, Any]:
    """Grade a dataset of parsed ``Event`` records on the L0-L3 conformance ladder."""
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
            "Levels grade the ADAPTED RECORD, not capture completeness or scientific quality.",
            "Signals omitted before the adapter output are outside every level and must be "
            "declared in a separate capture-policy audit.",
            "A dataset with no negative outcomes fails L2 by design: from the outside, "
            "'all successes' and 'failures filtered out' are indistinguishable.",
            "trace_richness is reported but not gated: single-observation events are "
            "valid, but a dataset of them is a measurement archive, not event traces.",
        ],
    }
