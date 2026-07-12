"""Adversarial validation tests for the partner collection bundle contract."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, cast

import pytest

from materials_event_modeling.partner import validate_partner_bundle

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_BUNDLE = REPO_ROOT / "data/examples/partner_golden_bundle_synthetic"

JsonObject = dict[str, Any]


def _copy_bundle(tmp_path: Path) -> Path:
    destination = tmp_path / "bundle"
    shutil.copytree(GOLDEN_BUNDLE, destination)
    return destination


def _read_object(path: Path) -> JsonObject:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(JsonObject, value)


def _write_object(path: Path, value: JsonObject) -> None:
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _table_descriptor(index: JsonObject, table_id: str) -> JsonObject:
    tables = index["tables"]
    assert isinstance(tables, list)
    descriptor = next(
        item
        for item in tables
        if isinstance(item, dict) and item.get("table_id") == table_id
    )
    return cast(JsonObject, descriptor)


def _load_table(root: Path, table_id: str) -> list[JsonObject]:
    index = _read_object(root / "bundle.json")
    descriptor = _table_descriptor(index, table_id)
    value = json.loads((root / str(descriptor["path"])).read_text(encoding="utf-8"))
    assert isinstance(value, list)
    assert all(isinstance(row, dict) for row in value)
    return cast(list[JsonObject], value)


def _write_table(root: Path, table_id: str, rows: list[JsonObject]) -> None:
    text = json.dumps(rows, allow_nan=False, indent=2, sort_keys=True) + "\n"
    _write_table_text(root, table_id, text, row_count=len(rows))


def _write_table_text(
    root: Path,
    table_id: str,
    text: str,
    *,
    row_count: int | None = None,
) -> None:
    index_path = root / "bundle.json"
    index = _read_object(index_path)
    descriptor = _table_descriptor(index, table_id)
    table_path = root / str(descriptor["path"])
    table_path.write_text(text, encoding="utf-8")
    descriptor["sha256"] = _sha256(table_path)
    descriptor["bytes"] = table_path.stat().st_size
    if row_count is not None:
        descriptor["row_count"] = row_count
    _write_object(index_path, index)


def _write_study(root: Path, study: JsonObject) -> None:
    study_path = root / "study_spec.json"
    _write_object(study_path, study)
    index_path = root / "bundle.json"
    index = _read_object(index_path)
    descriptor = cast(JsonObject, index["study_spec"])
    descriptor["sha256"] = _sha256(study_path)
    descriptor["bytes"] = study_path.stat().st_size
    _write_object(index_path, index)


def _validate(root: Path, *, readiness: str | None = None) -> JsonObject:
    return validate_partner_bundle(root, readiness=readiness)


def _error_codes(report: JsonObject) -> set[str]:
    errors = report["blocking_errors"]
    assert isinstance(errors, list)
    return {
        str(error["code"])
        for error in errors
        if isinstance(error, dict) and "code" in error
    }


def test_real_synthetic_golden_bundle_is_valid() -> None:
    report = _validate(GOLDEN_BUNDLE)

    assert report["valid"] is True
    assert report["requested_readiness"] == "golden"
    assert report["blocking_errors"] == []
    assert report["readiness"]["golden"]["ready"] is True


@pytest.mark.parametrize("malformation", ["nan", "duplicate_key"])
def test_strict_json_rejects_nonfinite_and_duplicate_keys(
    tmp_path: Path, malformation: str
) -> None:
    root = _copy_bundle(tmp_path)
    index = _read_object(root / "bundle.json")
    descriptor = _table_descriptor(index, "assignments")
    table_path = root / str(descriptor["path"])
    text = table_path.read_text(encoding="utf-8")
    if malformation == "nan":
        assert '"nonconfirmatory": true' in text
        text = text.replace('"nonconfirmatory": true', '"nonconfirmatory": NaN', 1)
    else:
        needle = '"assignment_id": "assignment-syn-ordinary-001",'
        assert needle in text
        text = text.replace(needle, f'{needle}\n    "assignment_id": "duplicate",', 1)
    _write_table_text(root, "assignments", text)

    report = _validate(root)

    assert report["valid"] is False
    assert "table_json_invalid" in _error_codes(report)


def test_wrong_table_hash_is_blocking(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    index_path = root / "bundle.json"
    index = _read_object(index_path)
    _table_descriptor(index, "attempts")["sha256"] = "0" * 64
    _write_object(index_path, index)

    report = _validate(root)

    assert report["valid"] is False
    assert "table_hash_mismatch" in _error_codes(report)
    assert report["readiness"]["golden"]["ready"] is False
    assert (
        report["readiness"]["golden"]["requirements"]["core_validation_passed"]
        is False
    )


def test_wrong_artifact_hash_is_blocking(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    artifacts = _load_table(root, "artifacts")
    artifact = next(
        row
        for row in artifacts
        if row.get("artifact_role") == "native_trace"
        and isinstance(row.get("location"), dict)
        and row["location"].get("status") == "available_bundle_file"
    )
    artifact_path = root / str(artifact["location"]["path"])
    artifact_path.write_bytes(artifact_path.read_bytes() + b"\ncorrupted")

    report = _validate(root)

    assert report["valid"] is False
    assert "artifact_hash_mismatch" in _error_codes(report)


def test_orphan_outcome_is_blocking(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    outcomes = _load_table(root, "outcomes")
    outcomes[0]["subject_node_id"] = "node-does-not-exist"
    _write_table(root, "outcomes", outcomes)

    report = _validate(root)

    assert report["valid"] is False
    assert "missing_reference" in _error_codes(report)


def test_physical_graph_cycle_is_blocking(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    edges = _load_table(root, "physical_edges")
    reverse = copy.deepcopy(edges[0])
    reverse["edge_id"] = "edge-synthetic-cycle"
    reverse["source_node_ids"], reverse["target_node_ids"] = (
        reverse["target_node_ids"],
        reverse["source_node_ids"],
    )
    edges.append(reverse)
    _write_table(root, "physical_edges", edges)

    report = _validate(root)

    assert report["valid"] is False
    assert "physical_lineage_cycle" in _error_codes(report)


def test_missing_representation_row_is_blocking(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    representations = _load_table(root, "representations")
    representations.pop()
    _write_table(root, "representations", representations)

    report = _validate(root)

    assert report["valid"] is False
    assert "required_representation_row_missing" in _error_codes(report)


@pytest.mark.parametrize(
    ("value_field", "limit_field", "error_code"),
    [
        ("latest_material_state", "declared_state_cutoff", "state_cutoff_status_mismatch"),
        (
            "operational_ready_elapsed",
            "declared_decision_deadline",
            "decision_deadline_status_mismatch",
        ),
    ],
)
def test_cutoff_and_deadline_violations_are_blocking(
    tmp_path: Path,
    value_field: str,
    limit_field: str,
    error_code: str,
) -> None:
    root = _copy_bundle(tmp_path)
    representations = _load_table(root, "representations")
    row = representations[0]
    row[value_field] = copy.deepcopy(row[limit_field])
    row[value_field]["value"] = float(row[limit_field]["value"]) + 1.0
    _write_table(root, "representations", representations)

    report = _validate(root)

    assert report["valid"] is False
    assert error_code in _error_codes(report)


def test_outcome_access_before_representation_freeze_is_blocking(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    representations = _load_table(root, "representations")
    outcomes = _load_table(root, "outcomes")
    outcome = outcomes[0]
    representation = next(
        row for row in representations if row["subject_node_id"] == outcome["subject_node_id"]
    )
    representation["nonconfirmatory"] = False
    outcome["nonconfirmatory"] = False
    outcome["accessible_at"] = representation["frozen_at"]
    _write_table(root, "representations", representations)
    _write_table(root, "outcomes", outcomes)

    report = _validate(root)

    assert report["valid"] is False
    assert "unit_freeze_after_outcome_access" in _error_codes(report)


def test_independent_parent_cannot_cross_partitions(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    nodes = _load_table(root, "physical_nodes")
    ordinary = next(row for row in nodes if row["node_id"] == "node-assay-ordinary")
    failure = next(row for row in nodes if row["node_id"] == "node-assay-failure")
    for row, partition in ((ordinary, "train"), (failure, "test")):
        row["independent_parent_id"] = "independent-parent-shared"
        row["partition"] = partition
        row["nonconfirmatory"] = False
    _write_table(root, "physical_nodes", nodes)

    report = _validate(root)

    assert report["valid"] is False
    assert "independent_parent_partition_leakage" in _error_codes(report)


def test_nested_assignments_fail_confirmatory_bridge_crossing(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    assignments = _load_table(root, "assignments")
    assignments[1]["planned_condition"] = {
        "temperature_c": 35.0,
        "duration_min": 60,
    }
    _write_table(root, "assignments", assignments)

    report = _validate(root, readiness="outcome_reveal")

    assert report["valid"] is False
    assert "bridge_crossing_insufficient" in _error_codes(report)
    assert report["checks"]["bridge_crossing"]["passed"] is False


def test_shadow_decision_cannot_expose_research_output(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    decisions = _load_table(root, "decisions")
    assert decisions[0]["decision_mode"] == "shadow"
    decisions[0]["research_output_visible"] = True
    _write_table(root, "decisions", decisions)

    report = _validate(root)

    assert report["valid"] is False
    assert "row_schema_invalid" in _error_codes(report)


def test_silent_retry_reusing_an_event_is_blocking(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    attempts = _load_table(root, "attempts")
    retry = copy.deepcopy(attempts[0])
    retry["attempt_id"] = "attempt-synthetic-silent-retry"
    retry["retry_of_attempt_id"] = None
    attempts.append(retry)
    _write_table(root, "attempts", attempts)

    report = _validate(root)

    assert report["valid"] is False
    assert "duplicate_event_id" in _error_codes(report)


def test_source_denominator_mismatch_is_blocking(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    index_path = root / "bundle.json"
    index = _read_object(index_path)
    denominator = cast(JsonObject, index["source_denominator_counts"])
    denominator["initiated_attempts"] = int(denominator["initiated_attempts"]) + 1
    _write_object(index_path, index)

    report = _validate(root)

    assert report["valid"] is False
    assert "source_denominator_mismatch" in _error_codes(report)
    assert "source_denominator_snapshot_mismatch" in _error_codes(report)


def test_row_schema_hash_is_frozen(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    index_path = root / "bundle.json"
    index = _read_object(index_path)
    _table_descriptor(index, "attempts")["row_schema_sha256"] = "0" * 64
    _write_object(index_path, index)

    report = _validate(root)

    assert report["valid"] is False
    assert "table_row_schema_hash_mismatch" in _error_codes(report)


def test_representation_rows_must_instantiate_declared_parent_dag(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    representations = _load_table(root, "representations")
    report_row = next(
        row for row in representations if row["representation_id"] == "rep-ordinary-report"
    )
    report_row["source_representation_ids"] = ["rep-ordinary-native"]
    _write_table(root, "representations", representations)

    report = _validate(root)

    assert report["valid"] is False
    assert "representation_parent_spec_mismatch" in _error_codes(report)


def test_decision_cannot_cite_unavailable_representation(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    representations = _load_table(root, "representations")
    native = next(
        row for row in representations if row["representation_id"] == "rep-ordinary-native"
    )
    native["status"] = "unavailable"
    native["primary_analysis_available"] = False
    native["availability_reason_codes"] = ["synthetic.native_unavailable"]
    _write_table(root, "representations", representations)

    report = _validate(root)

    assert report["valid"] is False
    assert "decision_cites_unavailable_representation" in _error_codes(report)


def test_transformation_method_hash_must_match_artifact(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    transformations = _load_table(root, "transformations")
    code = cast(JsonObject, transformations[0]["code"])
    code["sha256"] = "0" * 64
    _write_table(root, "transformations", transformations)

    report = _validate(root)

    assert report["valid"] is False
    assert "transformation_method_hash_mismatch" in _error_codes(report)


def test_freeze_order_follows_physical_descendants(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    representations = _load_table(root, "representations")
    outcomes = _load_table(root, "outcomes")
    representation = next(
        row for row in representations if row["representation_id"] == "rep-ordinary-native"
    )
    outcome = next(row for row in outcomes if row["outcome_id"] == "outcome-ordinary-lifetime")
    representation["subject_node_id"] = "node-specimen-ordinary"
    representation["frozen_at"] = outcome["accessible_at"]
    _write_table(root, "representations", representations)

    report = _validate(root)

    assert report["valid"] is False
    assert "unit_freeze_after_outcome_access" in _error_codes(report)


def test_connected_nodes_cannot_invent_different_independent_parents(
    tmp_path: Path,
) -> None:
    root = _copy_bundle(tmp_path)
    nodes = _load_table(root, "physical_nodes")
    assay = next(row for row in nodes if row["node_id"] == "node-assay-ordinary")
    assay["independent_parent_id"] = "node-batch-failure"
    _write_table(root, "physical_nodes", nodes)

    report = _validate(root)

    assert report["valid"] is False
    assert "physical_edge_parent_mismatch" in _error_codes(report)
    assert "independent_parent_not_ancestor" in _error_codes(report)


def test_nonconfirmatory_edge_cannot_be_silently_reclassified(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    edges = _load_table(root, "physical_edges")
    edges[0]["nonconfirmatory"] = False
    _write_table(root, "physical_edges", edges)

    report = _validate(root)

    assert report["valid"] is False
    assert "nonconfirmatory_bundle_contains_confirmatory_row" in _error_codes(report)


def test_applied_confirmatory_correction_requires_two_approvers(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    corrections = _load_table(root, "corrections")
    correction = corrections[0]
    correction["status"] = "applied"
    correction["applied_change"] = "Synthetic successor record"
    correction["after_hashes"] = ["1" * 64]
    correction["approvals"][0]["status"] = "approved"
    correction["nonconfirmatory"] = False
    _write_table(root, "corrections", corrections)

    report = _validate(root)

    assert report["valid"] is False
    assert "confirmatory_correction_lacks_two_person_approval" in _error_codes(report)


def test_malformed_bundle_index_is_reported(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    index_path = root / "bundle.json"
    index_path.write_text('{"schema_version": NaN}', encoding="utf-8")

    report = validate_partner_bundle(index_path)

    assert report["valid"] is False
    assert "bundle_index_invalid_json" in _error_codes(report)


def test_escaping_bundle_index_symlink_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text('{"schema_version":"partner_bundle.v1"}\n', encoding="utf-8")
    index_path = root / "bundle.json"
    index_path.symlink_to(outside)

    report = validate_partner_bundle(index_path)

    assert report["valid"] is False
    assert "bundle_index_unreadable" in _error_codes(report)


def test_schema_invalid_study_returns_report_instead_of_crashing(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    study = _read_object(root / "study_spec.json")
    environment = cast(JsonObject, study["environment_design"])
    coverage = cast(JsonObject, environment["bridge_coverage"])
    coverage["minimum_primary_environment_levels"] = "not-an-integer"
    _write_study(root, study)

    report = _validate(root)

    assert report["valid"] is False
    assert "study_schema_invalid" in _error_codes(report)


def test_unsafe_table_path_is_reported(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    index_path = root / "bundle.json"
    index = _read_object(index_path)
    _table_descriptor(index, "assignments")["path"] = "../assignments.json"
    _write_object(index_path, index)

    report = _validate(root)

    assert report["valid"] is False
    assert "bundle_schema_invalid" in _error_codes(report)


def test_readiness_is_not_vacuously_true_without_outcomes_or_representations(
    tmp_path: Path,
) -> None:
    root = _copy_bundle(tmp_path)
    _write_table(root, "outcomes", [])
    _write_table(root, "representations", [])
    index_path = root / "bundle.json"
    index = _read_object(index_path)
    denominator = cast(JsonObject, index["source_denominator_counts"])
    for field_name in (
        "eligible_followup_units",
        "followed_units",
        "right_censored_units",
        "missing_outcome_units",
    ):
        denominator[field_name] = 0
    _write_object(index_path, index)

    report = _validate(root, readiness="golden")

    assert report["valid"] is False
    assert report["readiness"]["golden"]["ready"] is False
    assert "readiness_gate_failed" in _error_codes(report)


def test_confirmatory_start_requires_external_validation_reservation(
    tmp_path: Path,
) -> None:
    root = _copy_bundle(tmp_path)

    report = _validate(root, readiness="confirmatory_start")

    requirements = report["readiness"]["confirmatory_start"]["requirements"]
    assert requirements["external_validation_reserved"] is False
    assert report["readiness"]["confirmatory_start"]["ready"] is False
    readiness_errors = [
        error
        for error in report["blocking_errors"]
        if error.get("code") == "readiness_gate_failed"
    ]
    assert readiness_errors
    assert "external_validation_reserved" in readiness_errors[0]["failed_requirements"]


def test_complete_confirmatory_start_contract_can_pass(tmp_path: Path) -> None:
    root = _copy_bundle(tmp_path)
    scoped_tables = (
        "assignments",
        "attempts",
        "physical_nodes",
        "physical_edges",
        "artifacts",
        "transformations",
        "representations",
        "outcomes",
        "costs",
        "decisions",
        "corrections",
    )
    for table_id in scoped_tables:
        rows = _load_table(root, table_id)
        for row in rows:
            row["nonconfirmatory"] = False
            if table_id == "physical_nodes":
                row["partition"] = "unassigned"
        if table_id == "assignments":
            rows[0]["domain_payload"]["stream"] = "native"
            rows[1]["domain_payload"]["stream"] = "bridge"
        _write_table(root, table_id, rows)

    index_path = root / "bundle.json"
    index = _read_object(index_path)
    index["purpose"] = "confirmatory_collection"
    index["inference_status"] = "firewalled_preanalysis"
    scope = cast(JsonObject, index["nonconfirmatory_scope"])
    for field_name in ("assignment_ids", "attempt_ids", "physical_node_ids", "artifact_ids"):
        scope[field_name] = []
    _write_object(index_path, index)

    artifacts = _load_table(root, "artifacts")
    artifact_by_id = {str(row["artifact_id"]): row for row in artifacts}
    manifest = artifact_by_id["artifact-practitioner-validation"]
    site_set = artifact_by_id["artifact-assignment-snapshot"]
    study = _read_object(root / "study_spec.json")
    study["inference_status"] = "preregistered_confirmatory"
    firewall = cast(JsonObject, study["firewall_and_freeze"])
    firewall["assignment_sha256"] = _sha256(root / "ledgers/assignments.json")
    firewall["study_spec_sha256"] = manifest["sha256"]
    firewall["golden_bundle_policy"] = "outcomes_firewalled_from_analysis_team"
    for lock_name in (
        "design_lock",
        "analysis_freeze",
        "raw_freeze",
        "representation_freeze",
    ):
        firewall[lock_name] = {
            "status": "locked",
            "git_commit": "bf55273",
            "manifest_artifact_id": manifest["artifact_id"],
            "manifest_sha256": manifest["sha256"],
            "locked_at": "2026-01-01T00:00:00Z",
        }
    signoffs = cast(JsonObject, study["signoffs"])
    for signoff_name in (
        "scientific_owner",
        "practitioner_action_owner",
        "outcome_assay_owner",
        "data_lineage_owner",
    ):
        signoff = cast(JsonObject, signoffs[signoff_name])
        signoff["status"] = "signed"
        signoff["signed_at"] = "2026-01-01T00:00:00Z"
        signoff["signed_spec_sha256"] = manifest["sha256"]
    environment = cast(JsonObject, study["environment_design"])
    external = cast(JsonObject, environment["external_validation"])
    external.update(
        {
            "mode": "zero_shot",
            "site_set_artifact_id": site_set["artifact_id"],
            "site_set_sha256": site_set["sha256"],
            "calibration_unit_count": 0,
            "frozen_test_unit_count": 1,
            "model_retraining_allowed": False,
            "same_report_schema_required": True,
            "same_transformation_graph_required": True,
        }
    )
    _write_study(root, study)

    report = _validate(root, readiness="confirmatory_start")

    assert report["valid"] is True
    assert report["readiness"]["confirmatory_start"]["ready"] is True
    requirements = report["readiness"]["confirmatory_start"]["requirements"]
    assert "negative_or_censored_attempt_present" not in requirements
    assert "outcome_rows_present" not in requirements
