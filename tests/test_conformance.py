"""Tests for the event-grammar conformance ladder (L0-L3)."""

from __future__ import annotations

from typing import Any

from materials_event_modeling.grammar import conformance_report


def _event(
    idx: int,
    *,
    n_obs: int = 3,
    payload: bool = True,
    indexed: bool = True,
    provenance: dict[str, Any] | None = None,
    outcome_status: str | None = "success",
    plan: dict[str, Any] | None = None,
    labels: dict[str, Any] | None = None,
) -> dict[str, Any]:
    observations = []
    for j in range(n_obs):
        obs: dict[str, Any] = {"observation_id": f"e{idx}_o{j}", "modality": "spectrum"}
        if indexed:
            obs["timepoint_minutes"] = float(j)
        if payload:
            obs["payload"] = {"spectrum": {"intensity": [j, j + 1]}}
        observations.append(obs)
    event: dict[str, Any] = {
        "event_id": f"e{idx}",
        "system": "test_system",
        "observations": observations,
        "provenance": provenance or {},
    }
    if outcome_status is not None:
        event["outcome"] = {"status": outcome_status}
    if plan is not None:
        event["intent"] = {"planned": plan}
    if labels is not None:
        event["labels"] = labels
    return event


def test_below_l0_when_observations_have_no_payload() -> None:
    events = [_event(i, payload=False) for i in range(4)]
    report = conformance_report(events)
    assert report["level"] == -1
    assert report["level_name"] == "below_l0"


def test_l0_raw_trace() -> None:
    events = [_event(i) for i in range(4)]
    report = conformance_report(events)
    assert report["level"] == 0
    richness = report["levels"]["l0_raw_trace"]["trace_richness"]
    assert richness["median_observations_per_event"] == 3


def test_l1_requires_two_logged_axes() -> None:
    one_axis = [_event(i, provenance={"operator_id": f"op{i % 2}"}) for i in range(4)]
    assert conformance_report(one_axis)["level"] == 0

    two_axes = [
        _event(i, provenance={"operator_id": f"op{i % 2}", "batch_id": f"b{i % 2}"})
        for i in range(4)
    ]
    report = conformance_report(two_axes)
    assert report["level"] == 1
    assert set(report["levels"]["l1_provenance"]["evidence"]["logged_axes"]) == {
        "operator_id",
        "batch_id",
    }


def test_l2_requires_negative_outcomes_and_frozen_labels() -> None:
    provenance = {"operator_id": "op0", "batch_id": "b0"}
    all_success = [_event(i, provenance=provenance) for i in range(6)]
    report = conformance_report(all_success)
    assert report["level"] == 1  # no negatives recorded -> L2 fails by design
    assert not report["levels"]["l2_negatives_frozen_labels"]["checks"][
        "negative_outcomes_retained"
    ]

    frozen = {"assigned_after_raw_data_frozen": True,
              "entries": [{"labeler_id": "h1", "label": "ring"}]}
    with_negatives = [
        _event(i, provenance=provenance, outcome_status="failure" if i == 0 else "success",
               labels=frozen)
        for i in range(6)
    ]
    assert conformance_report(with_negatives)["level"] == 2

    unfrozen = dict(frozen, assigned_after_raw_data_frozen=False)
    with_unfrozen_labels = [
        _event(i, provenance=provenance, outcome_status="failure" if i == 0 else "success",
               labels=unfrozen)
        for i in range(6)
    ]
    assert conformance_report(with_unfrozen_labels)["level"] == 1


def test_l3_requires_replicates_with_provenance_variation() -> None:
    # 4 plans x 3 replicates; replicates spread across operators and batches.
    events = []
    idx = 0
    for plan in range(4):
        for rep in range(3):
            events.append(
                _event(
                    idx,
                    provenance={"operator_id": f"op{rep}", "batch_id": f"b{rep}"},
                    outcome_status="ambiguous" if idx == 0 else "success",
                    plan={"target_level": plan},
                )
            )
            idx += 1
    report = conformance_report(events)
    assert report["level"] == 3

    # Same design but each plan's replicates share one operator/batch: fails L3.
    confounded = []
    idx = 0
    for plan in range(4):
        for _ in range(3):
            confounded.append(
                _event(
                    idx,
                    provenance={"operator_id": f"op{plan}", "batch_id": f"b{plan}"},
                    outcome_status="ambiguous" if idx == 0 else "success",
                    plan={"target_level": plan},
                )
            )
            idx += 1
    report = conformance_report(confounded)
    assert report["level"] == 2
    assert not report["levels"]["l3_counterbalanced"]["checks"][
        "provenance_varies_within_groups"
    ]


def test_selection_risk_flags_success_bias_and_few_units() -> None:
    prov = {"operator_id": "op0", "batch_id": "b0"}  # 1 unit per axis
    all_success = [_event(i, provenance=prov, outcome_status="success") for i in range(6)]
    risk = conformance_report(all_success)["selection_risk"]
    assert risk["success_bias_risk"] == "high_no_negatives_recorded"
    assert risk["negative_outcome_count"] == 0
    assert risk["few_provenance_units_risk"] == "high"  # 1 distinct value per axis

    # Negatives present + many provenance units -> lower risk on both.
    varied = [
        _event(i, provenance={"operator_id": f"op{i}", "batch_id": f"b{i}"},
               outcome_status="failure" if i % 5 == 0 else "success")
        for i in range(20)
    ]
    risk2 = conformance_report(varied)["selection_risk"]
    assert risk2["success_bias_risk"] in ("low_negatives_present", "elevated_few_negatives")
    assert risk2["few_provenance_units_risk"] == "lower"
    assert "data_assumptions_and_limits" in risk2["note"]


def test_selection_risk_reports_unknown_when_outcomes_missing() -> None:
    prov = {"operator_id": "op0", "batch_id": "b0"}
    no_status = [_event(i, provenance=prov, outcome_status=None) for i in range(6)]
    risk = conformance_report(no_status)["selection_risk"]
    assert risk["success_bias_risk"] == "unknown_outcomes_not_recorded"


def test_legacy_material_event_records_are_gradable() -> None:
    """The CaCO3-pilot shape (measurements + process.planned_conditions) still grades."""
    legacy = {
        "event_id": "legacy_1",
        "system": "calcium_carbonate",
        "provenance": {"operator_id": "op1", "batch_id": "b1"},
        "process": {
            "precursors": [{"name": "CaCl2"}],
            "planned_conditions": {"target_temperature_c": 25},
            "timeline": [],
        },
        "measurements": {
            "xrd": [
                {"file_path": "raw/e1_a.xy", "measurement_time": "2026-06-01T10:00:00Z"},
                {"file_path": "raw/e1_b.xy", "measurement_time": "2026-06-01T11:00:00Z"},
            ]
        },
        "labels": {"assigned_after_raw_data_frozen": True,
                   "human_labels": [{"labeler_id": "h1", "label": "calcite"}]},
        "data_quality": {"include_in_raw_objective": True, "deviations": [],
                         "missing_fields": []},
    }
    report = conformance_report([legacy])
    # Grades without error; single legacy event lacks outcome.status -> at most L1.
    assert report["level"] in (0, 1)
    assert report["levels"]["l0_raw_trace"]["passed"]
