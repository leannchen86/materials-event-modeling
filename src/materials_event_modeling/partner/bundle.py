"""Structural and semantic validation for partner collection bundles.

The JSON Schemas define the on-disk contract.  This module enforces the properties
that JSON Schema cannot express: immutable file evidence, cross-table references,
lineage acyclicity, split isolation, temporal ordering, denominator reconciliation,
and phase readiness.  Validation is read-only and returns a strict-JSON-safe report.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn, cast

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource

SCHEMA_FILENAMES = {
    "study": "partner_study.v1.schema.json",
    "bundle": "partner_bundle.v1.schema.json",
    "rows": "partner_rows.v1.schema.json",
}

ROW_ID_FIELDS = {
    "assignment": "assignment_id",
    "attempt": "attempt_id",
    "physical_node": "node_id",
    "physical_edge": "edge_id",
    "artifact": "artifact_id",
    "transformation": "transformation_id",
    "representation": "representation_id",
    "outcome": "outcome_id",
    "cost": "cost_id",
    "decision": "decision_id",
    "correction": "correction_id",
}

TABLE_ROW_TYPES = {
    "assignments": "assignment",
    "attempts": "attempt",
    "events": None,
    "physical_nodes": "physical_node",
    "physical_edges": "physical_edge",
    "artifacts": "artifact",
    "transformations": "transformation",
    "representations": "representation",
    "outcomes": "outcome",
    "costs": "cost",
    "decisions": "decision",
    "corrections": "correction",
}
TABLE_ROW_SCHEMAS = {
    "assignments": "partner_rows.v1.schema.json#/$defs/assignment",
    "attempts": "partner_rows.v1.schema.json#/$defs/attempt",
    "events": "event_grammar.v1.schema.json",
    "physical_nodes": "partner_rows.v1.schema.json#/$defs/physicalNode",
    "physical_edges": "partner_rows.v1.schema.json#/$defs/physicalEdge",
    "artifacts": "partner_rows.v1.schema.json#/$defs/artifact",
    "transformations": "partner_rows.v1.schema.json#/$defs/transformation",
    "representations": "partner_rows.v1.schema.json#/$defs/representation",
    "outcomes": "partner_rows.v1.schema.json#/$defs/outcome",
    "costs": "partner_rows.v1.schema.json#/$defs/cost",
    "decisions": "partner_rows.v1.schema.json#/$defs/decision",
    "corrections": "partner_rows.v1.schema.json#/$defs/correction",
}

_TIME_UNITS_TO_SECONDS = {
    "microseconds": 1e-6,
    "milliseconds": 1e-3,
    "seconds": 1.0,
    "minutes": 60.0,
    "hours": 3600.0,
    "days": 86400.0,
}
_ANALYTIC_PARTITIONS = {"train", "validation", "test", "external_test"}
READINESS_LEVELS = (
    "golden",
    "pilot",
    "confirmatory_start",
    "input_close",
    "outcome_reveal",
    "external_validation",
    "release",
)


class StrictJSONError(ValueError):
    """Raised when a JSON document is not strict or is ambiguous."""


def _reject_constant(value: str) -> NoReturn:
    raise StrictJSONError(f"non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJSONError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _loads_strict(text: str, *, source: str) -> Any:
    try:
        value = json.loads(
            text,
            parse_constant=_reject_constant,
            object_pairs_hook=_unique_object,
        )
    except (json.JSONDecodeError, StrictJSONError) as exc:
        raise StrictJSONError(f"{source}: {exc}") from exc
    _assert_finite(value, source=source)
    return value


def _assert_finite(value: Any, *, source: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise StrictJSONError(f"{source}: non-finite number is forbidden")
    if isinstance(value, dict):
        for child in value.values():
            _assert_finite(child, source=source)
    elif isinstance(value, list):
        for child in value:
            _assert_finite(child, source=source)


def load_strict_json(path: Path) -> Any:
    """Read a JSON document while rejecting NaN, Infinity, and duplicate keys."""
    return _loads_strict(path.read_text(encoding="utf-8"), source=str(path))


def _safe_bundle_path(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("bundle path must be a nonempty string")
    candidate_text = relative.replace("\\", "/")
    candidate = Path(candidate_text)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"unsafe bundle-relative path: {relative!r}")
    root_resolved = root.resolve()
    resolved = (root_resolved / candidate).resolve()
    if not resolved.is_relative_to(root_resolved):
        raise ValueError(f"bundle path escapes root: {relative!r}")
    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _instance_path(parts: Iterable[object]) -> str:
    path = "$"
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"
    return path


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        result = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return result if result.tzinfo is not None else None


def _elapsed_seconds(value: object) -> tuple[float, str] | None:
    if not isinstance(value, dict):
        return None
    numeric = value.get("value")
    unit = value.get("unit")
    origin = value.get("origin")
    if not isinstance(numeric, (int, float)) or isinstance(numeric, bool):
        return None
    if not isinstance(unit, str) or not isinstance(origin, str):
        return None
    if unit in _TIME_UNITS_TO_SECONDS:
        return float(numeric) * _TIME_UNITS_TO_SECONDS[unit], origin
    if unit in {"cycles", "process_steps"}:
        return float(numeric), f"{origin}\0{unit}"
    return None


@dataclass
class _Report:
    blocking_errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    counts: dict[str, Any] = field(default_factory=dict)
    hashes: dict[str, Any] = field(default_factory=dict)
    readiness: dict[str, dict[str, Any]] = field(default_factory=dict)

    def error(self, code: str, message: str, **context: Any) -> None:
        self.blocking_errors.append({"code": code, "message": message, **context})

    def warning(self, code: str, message: str, **context: Any) -> None:
        self.warnings.append({"code": code, "message": message, **context})

    def check(self, name: str, passed: bool, *, details: Any = None) -> None:
        entry: dict[str, Any] = {"passed": bool(passed)}
        if details is not None:
            entry["details"] = details
        self.checks[name] = entry

    def finish(self, *, requested_readiness: str | None) -> dict[str, Any]:
        blocking = sorted(
            self.blocking_errors,
            key=lambda item: (
                str(item.get("code", "")),
                str(item.get("path", "")),
                str(item.get("row_id", "")),
                str(item.get("message", "")),
            ),
        )
        warnings = sorted(
            self.warnings,
            key=lambda item: (
                str(item.get("code", "")),
                str(item.get("path", "")),
                str(item.get("row_id", "")),
                str(item.get("message", "")),
            ),
        )
        return {
            "valid": not blocking,
            "requested_readiness": requested_readiness,
            "blocking_errors": blocking,
            "warnings": warnings,
            "checks": dict(sorted(self.checks.items())),
            "counts": self.counts,
            "hashes": self.hashes,
            "readiness": self.readiness,
        }


@dataclass(frozen=True)
class _LoadedTable:
    descriptor: dict[str, Any]
    path: Path
    rows: tuple[dict[str, Any], ...]


def _schema_errors(validator: Any, instance: object) -> list[str]:
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: (list(error.absolute_path), error.message),
    )
    return [f"{_instance_path(error.absolute_path)}: {error.message}" for error in errors]


def _schema_registry(schemas: Mapping[str, dict[str, Any]]) -> Registry:
    registry = Registry()
    for schema in schemas.values():
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            registry = registry.with_resource(schema_id, Resource.from_contents(schema))
    return registry


def _acyclic(nodes: Iterable[str], edges: Iterable[tuple[str, str]]) -> tuple[bool, list[str]]:
    adjacency: defaultdict[str, set[str]] = defaultdict(set)
    indegree: Counter[str] = Counter()
    all_nodes = set(nodes)
    for source, target in edges:
        all_nodes.add(source)
        all_nodes.add(target)
        if target not in adjacency[source]:
            adjacency[source].add(target)
            indegree[target] += 1
    queue = sorted(node for node in all_nodes if indegree[node] == 0)
    visited: list[str] = []
    while queue:
        node = queue.pop(0)
        visited.append(node)
        for child in sorted(adjacency[node]):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
                queue.sort()
    cyclic = sorted(all_nodes.difference(visited))
    return not cyclic, cyclic


def _transitive_reachability(
    nodes: Iterable[str], edges: Iterable[tuple[str, str]]
) -> dict[str, set[str]]:
    """Return every directed descendant while terminating safely on malformed cycles."""
    adjacency: defaultdict[str, set[str]] = defaultdict(set)
    all_nodes = set(nodes)
    for source, target in edges:
        adjacency[source].add(target)
        all_nodes.update((source, target))
    result: dict[str, set[str]] = {}
    for source in all_nodes:
        seen: set[str] = set()
        stack = list(adjacency[source])
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(adjacency[node].difference(seen))
        result[source] = seen
    return result


def _load_schema_set(schema_dir: Path, report: _Report) -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    for name, filename in SCHEMA_FILENAMES.items():
        path = schema_dir / filename
        try:
            value = load_strict_json(path)
        except (OSError, StrictJSONError) as exc:
            report.error("schema_unreadable", str(exc), path=str(path))
            continue
        if not isinstance(value, dict):
            report.error("schema_not_object", "schema root must be an object", path=str(path))
            continue
        try:
            Draft202012Validator.check_schema(value)
        except SchemaError as exc:
            report.error("schema_invalid", str(exc), path=str(path))
            continue
        schemas[name] = value
        report.hashes[f"schema:{filename}"] = _sha256_file(path)
    report.check(
        "schemas_loaded",
        len(schemas) == len(SCHEMA_FILENAMES),
        details={"loaded": sorted(schemas), "expected": sorted(SCHEMA_FILENAMES)},
    )
    return schemas


def _read_table_rows(path: Path) -> list[Any]:
    suffixes = [suffix.lower() for suffix in path.suffixes]
    if suffixes and suffixes[-1] in {".jsonl", ".ndjson"}:
        rows: list[Any] = []
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    raise StrictJSONError(f"{path}:{line_number}: blank JSONL row")
                rows.append(
                    _loads_strict(line, source=f"{path}:{line_number}")
                )
        return rows
    if suffixes and suffixes[-1] == ".json":
        value = load_strict_json(path)
        if not isinstance(value, list):
            raise StrictJSONError(f"{path}: JSON table must be an array")
        return value
    raise StrictJSONError(f"{path}: table must use .jsonl, .ndjson, or .json")


def _json_pointer(root: object, pointer: str) -> object:
    value = root
    if not pointer:
        return value
    if not pointer.startswith("/"):
        raise ValueError(f"unsupported schema fragment: #{pointer}")
    for encoded_part in pointer[1:].split("/"):
        part = encoded_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, Mapping):
            raise ValueError(f"schema fragment does not exist: #{pointer}")
        mapping = cast(Mapping[str, object], value)
        if part not in mapping:
            raise ValueError(f"schema fragment does not exist: #{pointer}")
        value = mapping[part]
    return value


def _table_row_validator(
    schema_dir: Path,
    declaration: object,
    known_schemas: Mapping[str, dict[str, Any]],
    registry: Registry,
) -> tuple[Any, str | None]:
    if not isinstance(declaration, str) or not declaration:
        raise ValueError("row_schema must be a nonempty string")
    filename, separator, fragment = declaration.partition("#")
    if not filename or Path(filename).name != filename:
        raise ValueError(f"row_schema must name a local schema file: {declaration!r}")
    path = schema_dir / filename
    root_schema = next(
        (
            schema
            for schema in known_schemas.values()
            if schema.get("$id", "").endswith(f"/{filename}")
        ),
        None,
    )
    if root_schema is None:
        value = load_strict_json(path)
        if not isinstance(value, dict):
            raise ValueError(f"row schema root is not an object: {path}")
        root_schema = value
    selected = _json_pointer(root_schema, fragment) if separator else root_schema
    if not isinstance(selected, dict):
        raise ValueError(f"row schema fragment is not an object: {declaration!r}")
    selected_mapping = cast(dict[str, Any], selected)
    declared_type: str | None = None
    row_type_schema = selected_mapping.get("properties", {}).get("row_type")
    if isinstance(row_type_schema, dict) and isinstance(row_type_schema.get("const"), str):
        declared_type = row_type_schema["const"]
    if separator:
        validation_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": f"#{fragment}",
            "$defs": root_schema.get("$defs", {}),
        }
    else:
        validation_schema = root_schema
    return (
        Draft202012Validator(
            validation_schema,
            registry=registry,
            format_checker=FormatChecker(),
        ),
        declared_type,
    )


def _load_tables(
    root: Path,
    bundle: dict[str, Any],
    schema_dir: Path,
    schemas: Mapping[str, dict[str, Any]],
    registry: Registry,
    report: _Report,
) -> list[_LoadedTable]:
    descriptors = bundle.get("tables")
    if not isinstance(descriptors, list):
        return []
    loaded: list[_LoadedTable] = []
    table_ids: set[str] = set()
    table_paths: set[Path] = set()
    row_counts: Counter[str] = Counter()
    skipped_semantic_rows = 0
    for descriptor_index, descriptor_value in enumerate(descriptors):
        descriptor_path = f"$.tables[{descriptor_index}]"
        if not isinstance(descriptor_value, dict):
            continue
        descriptor = cast(dict[str, Any], descriptor_value)
        table_id = descriptor.get("table_id")
        if not isinstance(table_id, str):
            continue
        if table_id in table_ids:
            report.error(
                "duplicate_table_id",
                f"table_id {table_id!r} appears more than once",
                path=descriptor_path,
            )
            continue
        table_ids.add(table_id)
        try:
            path = _safe_bundle_path(root, descriptor.get("path"))
        except ValueError as exc:
            report.error("unsafe_table_path", str(exc), path=descriptor_path)
            continue
        if not path.is_file():
            report.error(
                "table_file_missing",
                f"declared table file does not exist: {path}",
                path=descriptor_path,
            )
            continue
        if path in table_paths:
            report.error(
                "duplicate_table_path",
                "one physical ledger file cannot satisfy multiple table declarations",
                path=descriptor_path,
            )
            continue
        table_paths.add(path)
        observed_bytes = path.stat().st_size
        observed_sha256 = _sha256_file(path)
        report.hashes[f"table:{table_id}"] = {
            "path": str(descriptor.get("path")),
            "sha256": observed_sha256,
            "bytes": observed_bytes,
        }
        if descriptor.get("bytes") != observed_bytes:
            report.error(
                "table_bytes_mismatch",
                f"declared bytes={descriptor.get('bytes')!r}, observed={observed_bytes}",
                path=descriptor_path,
            )
        if descriptor.get("sha256") != observed_sha256:
            report.error(
                "table_hash_mismatch",
                "declared SHA-256 does not match table bytes",
                path=descriptor_path,
            )
        try:
            values = _read_table_rows(path)
        except (OSError, StrictJSONError) as exc:
            report.error("table_json_invalid", str(exc), path=str(descriptor.get("path")))
            continue
        if descriptor.get("row_count") != len(values):
            report.error(
                "table_row_count_mismatch",
                f"declared row_count={descriptor.get('row_count')!r}, observed={len(values)}",
                path=descriptor_path,
            )
        try:
            validator, declared_type = _table_row_validator(
                schema_dir,
                descriptor.get("row_schema"),
                schemas,
                registry,
            )
        except (OSError, StrictJSONError, ValueError, SchemaError) as exc:
            report.error(
                "row_schema_unreadable",
                str(exc),
                path=descriptor_path,
            )
            continue
        expected_type = TABLE_ROW_TYPES.get(table_id)
        expected_schema = TABLE_ROW_SCHEMAS.get(table_id)
        if declared_type != expected_type or descriptor.get("row_schema") != expected_schema:
            report.error(
                "table_row_schema_type_mismatch",
                f"table {table_id!r} requires {expected_schema!r} and row type "
                f"{expected_type!r}; declaration resolves to {declared_type!r}",
                path=descriptor_path,
            )
        expected_schema_filename = str(expected_schema).partition("#")[0]
        expected_schema_path = schema_dir / expected_schema_filename
        expected_schema_hash = _sha256_file(expected_schema_path)
        if descriptor.get("row_schema_sha256") != expected_schema_hash:
            report.error(
                "table_row_schema_hash_mismatch",
                f"table {table_id!r} row-schema hash differs from {expected_schema_filename}",
                path=descriptor_path,
            )
        rows: list[dict[str, Any]] = []
        for row_index, value in enumerate(values):
            row_path = f"{descriptor.get('path')}[{row_index}]"
            if not isinstance(value, dict):
                report.error("table_row_not_object", "ledger row must be an object", path=row_path)
                continue
            errors = _schema_errors(validator, value)
            for message in errors:
                report.error("row_schema_invalid", message, path=row_path)
            actual_type = value.get("row_type")
            type_matches = declared_type is None or actual_type == declared_type
            if not type_matches:
                report.error(
                    "row_type_mismatch",
                    f"table declares {declared_type!r} but row has {actual_type!r}",
                    path=row_path,
                )
            if isinstance(actual_type, str):
                row_counts[actual_type] += 1
            # Semantic checks assume the structural contract. Invalid rows remain
            # blocking evidence but are excluded here so malformed field types cannot
            # crash later cross-table checks or manufacture misleading secondary errors.
            if not errors and type_matches and declared_type == expected_type:
                rows.append(value)
            else:
                skipped_semantic_rows += 1
        loaded.append(_LoadedTable(descriptor=descriptor, path=path, rows=tuple(rows)))
    report.counts["tables"] = len(loaded)
    report.counts["rows_by_type"] = dict(sorted(row_counts.items()))
    report.counts["semantic_rows_skipped"] = skipped_semantic_rows
    report.check(
        "table_files_match_manifest",
        not any(
            error["code"]
            in {
                "unsafe_table_path",
                "table_file_missing",
                "table_bytes_mismatch",
                "table_hash_mismatch",
                "table_json_invalid",
                "table_row_count_mismatch",
                "duplicate_table_path",
            }
            for error in report.blocking_errors
        ),
    )
    report.check(
        "rows_match_schema",
        not any(
            error["code"]
            in {
                "row_schema_invalid",
                "row_schema_unreadable",
                "table_row_not_object",
                "row_type_mismatch",
                "table_row_schema_type_mismatch",
                "table_row_schema_hash_mismatch",
            }
            for error in report.blocking_errors
        ),
    )
    report.check(
        "table_declarations_consistent",
        not any(
            error["code"]
            in {
                "duplicate_table_path",
                "table_row_schema_type_mismatch",
                "table_row_schema_hash_mismatch",
            }
            for error in report.blocking_errors
        ),
    )
    return loaded


def _index_rows(
    tables: Sequence[_LoadedTable], report: _Report
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, dict[str, Any]]]]:
    rows_by_type: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    indexes: dict[str, dict[str, dict[str, Any]]] = {
        row_type: {} for row_type in ROW_ID_FIELDS
    }
    primary_id_owner: dict[str, str] = {}
    event_ids: set[str] = set()
    planned_event_ids: set[str] = set()
    for table in tables:
        for row in table.rows:
            row_type = row.get("row_type")
            if not isinstance(row_type, str) or row_type not in ROW_ID_FIELDS:
                continue
            rows_by_type[row_type].append(row)
            id_field = ROW_ID_FIELDS[row_type]
            row_id = row.get(id_field)
            if not isinstance(row_id, str):
                continue
            if row_id in indexes[row_type]:
                report.error(
                    "duplicate_row_id",
                    f"duplicate {id_field} {row_id!r}",
                    row_type=row_type,
                    row_id=row_id,
                )
            else:
                indexes[row_type][row_id] = row
            previous_type = primary_id_owner.get(row_id)
            if previous_type is not None and previous_type != row_type:
                report.error(
                    "primary_id_reused",
                    f"primary ID {row_id!r} is reused by {previous_type} and {row_type}",
                    row_id=row_id,
                )
            primary_id_owner[row_id] = row_type
            if row_type == "attempt":
                event_id = row.get("event_id")
                if isinstance(event_id, str):
                    if event_id in event_ids:
                        report.error(
                            "duplicate_event_id",
                            f"event_id {event_id!r} appears on multiple attempts",
                            row_id=row_id,
                        )
                    event_ids.add(event_id)
            elif row_type == "assignment":
                planned_event_id = row.get("planned_event_id")
                if isinstance(planned_event_id, str):
                    if planned_event_id in planned_event_ids:
                        report.error(
                            "duplicate_planned_event_id",
                            f"planned_event_id {planned_event_id!r} appears on multiple assignments",
                            row_id=row_id,
                        )
                    planned_event_ids.add(planned_event_id)
    report.check(
        "row_ids_unique",
        not any(
            error["code"]
            in {
                "duplicate_row_id",
                "primary_id_reused",
                "duplicate_event_id",
                "duplicate_planned_event_id",
            }
            for error in report.blocking_errors
        ),
    )
    return dict(rows_by_type), indexes


def _row_identity(row: Mapping[str, Any]) -> str | None:
    row_type = row.get("row_type")
    if not isinstance(row_type, str):
        return None
    id_field = ROW_ID_FIELDS.get(row_type)
    value = row.get(id_field) if id_field is not None else None
    return value if isinstance(value, str) else None


def _reference_values(row: Mapping[str, Any], field_name: str) -> list[str]:
    value = row.get(field_name)
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _require_references(
    report: _Report,
    row: Mapping[str, Any],
    field_name: str,
    targets: Mapping[str, Any],
    target_kind: str,
) -> None:
    for value in _reference_values(row, field_name):
        if value not in targets:
            report.error(
                "missing_reference",
                f"{field_name} references absent {target_kind} {value!r}",
                row_type=row.get("row_type"),
                row_id=_row_identity(row),
                field=field_name,
                target_id=value,
            )


def _validate_study_identity(
    study: Mapping[str, Any],
    bundle: Mapping[str, Any],
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]],
    report: _Report,
) -> None:
    study_id = study.get("study_id")
    bundle_study_id = bundle.get("study_id")
    if study_id != bundle_study_id:
        report.error(
            "study_id_mismatch",
            f"study has {study_id!r}; bundle has {bundle_study_id!r}",
        )
    for row_type, rows in rows_by_type.items():
        for row in rows:
            if row.get("study_id") != study_id:
                report.error(
                    "row_study_id_mismatch",
                    f"row study_id {row.get('study_id')!r} does not match {study_id!r}",
                    row_type=row_type,
                    row_id=_row_identity(row),
                )
    report.check(
        "study_identity_consistent",
        not any(
            error["code"] in {"study_id_mismatch", "row_study_id_mismatch"}
            for error in report.blocking_errors
        ),
    )


def _validate_references(
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]],
    indexes: Mapping[str, Mapping[str, dict[str, Any]]],
    report: _Report,
) -> None:
    assignments = indexes["assignment"]
    attempts = indexes["attempt"]
    nodes = indexes["physical_node"]
    artifacts = indexes["artifact"]
    transformations = indexes["transformation"]
    representations = indexes["representation"]
    corrections = indexes["correction"]

    assignment_event_ids = {
        row.get("planned_event_id"): row
        for row in rows_by_type.get("assignment", [])
        if isinstance(row.get("planned_event_id"), str)
    }
    for row in rows_by_type.get("attempt", []):
        _require_references(report, row, "assignment_id", assignments, "assignment")
        _require_references(report, row, "retry_of_attempt_id", attempts, "attempt")
        _require_references(report, row, "rework_of_attempt_id", attempts, "attempt")
        row_id = _row_identity(row)
        for field_name in ("retry_of_attempt_id", "rework_of_attempt_id"):
            if row.get(field_name) == row_id:
                report.error(
                    "self_reference",
                    f"{field_name} cannot reference its own attempt",
                    row_type="attempt",
                    row_id=row_id,
                    field=field_name,
                )
        assignment = assignments.get(str(row.get("assignment_id")))
        if assignment is not None and row.get("event_id") != assignment.get("planned_event_id"):
            report.error(
                "attempt_event_assignment_mismatch",
                "attempt event_id differs from its assignment planned_event_id",
                row_type="attempt",
                row_id=row_id,
            )
        event_id = row.get("event_id")
        if isinstance(event_id, str) and event_id not in assignment_event_ids:
            report.error(
                "missing_reference",
                f"event_id references no planned_event_id {event_id!r}",
                row_type="attempt",
                row_id=row_id,
                field="event_id",
                target_id=event_id,
            )

    for row in rows_by_type.get("physical_node", []):
        _require_references(report, row, "source_attempt_ids", attempts, "attempt")
        _require_references(
            report, row, "independent_parent_id", nodes, "independent physical parent"
        )
    for row in rows_by_type.get("physical_edge", []):
        _require_references(report, row, "source_node_ids", nodes, "physical node")
        _require_references(report, row, "target_node_ids", nodes, "physical node")
    for row in rows_by_type.get("artifact", []):
        _require_references(report, row, "subject_node_ids", nodes, "physical node")
        _require_references(report, row, "attempt_ids", attempts, "attempt")
        _require_references(report, row, "source_artifact_ids", artifacts, "artifact")
    for row in rows_by_type.get("transformation", []):
        for field_name in (
            "input_artifact_ids",
            "output_artifact_ids",
            "reference_artifact_ids",
        ):
            _require_references(report, row, field_name, artifacts, "artifact")
        for field_name in ("input_representation_ids", "output_representation_ids"):
            _require_references(report, row, field_name, representations, "representation")
        for method_field in ("code", "configuration"):
            method = row.get(method_field)
            if isinstance(method, dict):
                _require_references(
                    report,
                    method,
                    "artifact_id",
                    artifacts,
                    "artifact",
                )
    for row in rows_by_type.get("representation", []):
        _require_references(report, row, "subject_node_id", nodes, "physical node")
        _require_references(report, row, "attempt_id", attempts, "attempt")
        _require_references(report, row, "source_artifact_ids", artifacts, "artifact")
        _require_references(
            report, row, "source_representation_ids", representations, "representation"
        )
        _require_references(
            report, row, "transformation_ids", transformations, "transformation"
        )
        _require_references(report, row, "value_artifact_id", artifacts, "artifact")
        _require_references(
            report, row, "actual_workflow_artifact_id", artifacts, "artifact"
        )
        subject = nodes.get(str(row.get("subject_node_id")))
        if subject is not None and row.get("attempt_id") not in subject.get(
            "source_attempt_ids", []
        ):
            report.error(
                "representation_attempt_subject_mismatch",
                "representation attempt_id is not a source attempt of its subject node",
                row_type="representation",
                row_id=_row_identity(row),
            )
    for row in rows_by_type.get("outcome", []):
        _require_references(report, row, "subject_node_id", nodes, "physical node")
        _require_references(report, row, "source_attempt_ids", attempts, "attempt")
        _require_references(report, row, "source_artifact_ids", artifacts, "artifact")
        _require_references(
            report, row, "transformation_ids", transformations, "transformation"
        )
        subject = nodes.get(str(row.get("subject_node_id")))
        if subject is not None and not set(_reference_values(row, "source_attempt_ids")).issubset(
            set(_reference_values(subject, "source_attempt_ids"))
        ):
            report.error(
                "outcome_attempt_subject_mismatch",
                "outcome source_attempt_ids are not all sources of its subject node",
                row_type="outcome",
                row_id=_row_identity(row),
            )
    for row in rows_by_type.get("cost", []):
        _require_references(report, row, "linked_attempt_id", attempts, "attempt")
        _require_references(report, row, "linked_node_id", nodes, "physical node")
        _require_references(report, row, "linked_artifact_id", artifacts, "artifact")
        _require_references(
            report, row, "linked_representation_id", representations, "representation"
        )
        _require_references(report, row, "evidence_artifact_ids", artifacts, "artifact")
    for row in rows_by_type.get("decision", []):
        _require_references(report, row, "subject_node_id", nodes, "physical node")
        _require_references(report, row, "attempt_id", attempts, "attempt")
        _require_references(
            report, row, "actual_report_artifact_id", artifacts, "artifact"
        )
        _require_references(
            report,
            row,
            "available_representation_ids",
            representations,
            "representation",
        )
        subject = nodes.get(str(row.get("subject_node_id")))
        if subject is not None and row.get("attempt_id") not in _reference_values(
            subject, "source_attempt_ids"
        ):
            report.error(
                "decision_attempt_subject_mismatch",
                "decision attempt_id is not a source attempt of its subject node",
                row_type="decision",
                row_id=_row_identity(row),
            )
        for representation_id in _reference_values(row, "available_representation_ids"):
            representation = representations.get(representation_id)
            if representation is not None and (
                representation.get("subject_node_id") != row.get("subject_node_id")
                or representation.get("attempt_id") != row.get("attempt_id")
            ):
                report.error(
                    "decision_representation_subject_mismatch",
                    "decision cites a representation for another subject or attempt",
                    row_type="decision",
                    row_id=_row_identity(row),
                    target_id=representation_id,
                )
    for row in rows_by_type.get("correction", []):
        _require_references(
            report,
            row,
            "supersedes_correction_id",
            corrections,
            "correction",
        )
        if row.get("supersedes_correction_id") == row.get("correction_id"):
            report.error(
                "self_reference",
                "correction cannot supersede itself",
                row_type="correction",
                row_id=_row_identity(row),
            )
        for affected in row.get("affected_records", []):
            if not isinstance(affected, dict):
                continue
            affected_type = affected.get("row_type")
            affected_id = affected.get("record_id")
            if (
                isinstance(affected_type, str)
                and affected_type in indexes
                and affected_id not in indexes[affected_type]
            ):
                report.error(
                    "correction_affected_record_missing",
                    f"correction references absent {affected_type} {affected_id!r}",
                    row_type="correction",
                    row_id=_row_identity(row),
                    target_id=affected_id,
                )
            before_hash = affected.get("before_sha256")
            if before_hash is not None and before_hash not in row.get("before_hashes", []):
                report.error(
                    "correction_before_hash_unlinked",
                    "affected-record before_sha256 is absent from before_hashes",
                    row_type="correction",
                    row_id=_row_identity(row),
                    target_id=affected_id,
                )
    for row_type in ("assignment", "attempt"):
        for row in rows_by_type.get(row_type, []):
            source_record = row.get("source_record")
            if isinstance(source_record, dict):
                _require_references(
                    report, source_record, "source_artifact_id", artifacts, "artifact"
                )
                artifact_id = source_record.get("source_artifact_id")
                artifact = artifacts.get(str(artifact_id))
                source_hash = source_record.get("source_sha256")
                if (
                    artifact is not None
                    and source_hash is not None
                    and artifact.get("sha256") is not None
                    and source_hash != artifact.get("sha256")
                ):
                    report.error(
                        "source_hash_mismatch",
                        "source_record SHA-256 differs from referenced artifact",
                        row_type=row_type,
                        row_id=_row_identity(row),
                    )
    report.check(
        "referential_integrity",
        not any(
            error["code"]
            in {
                "missing_reference",
                "self_reference",
                "attempt_event_assignment_mismatch",
                "representation_attempt_subject_mismatch",
                "outcome_attempt_subject_mismatch",
                "decision_attempt_subject_mismatch",
                "decision_representation_subject_mismatch",
                "correction_affected_record_missing",
                "correction_before_hash_unlinked",
                "source_hash_mismatch",
            }
            for error in report.blocking_errors
        ),
    )


def _validate_attempt_state_machine(
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]],
    indexes: Mapping[str, Mapping[str, dict[str, Any]]],
    report: _Report,
) -> None:
    assignments = indexes["assignment"]
    attempts = indexes["attempt"]
    for assignment in rows_by_type.get("assignment", []):
        row_id = _row_identity(assignment)
        created_at = _parse_timestamp(assignment.get("created_at"))
        scheduled_at = _parse_timestamp(assignment.get("scheduled_at"))
        if created_at is not None and scheduled_at is not None and created_at > scheduled_at:
            report.error(
                "assignment_clock_order_invalid",
                "assignment created_at occurs after scheduled_at",
                row_type="assignment",
                row_id=row_id,
            )

    for attempt in rows_by_type.get("attempt", []):
        row_id = _row_identity(attempt)
        assignment = assignments.get(str(attempt.get("assignment_id")))
        if assignment is not None:
            if assignment.get("status") != "released":
                report.error(
                    "attempt_from_unreleased_assignment",
                    "an initiated attempt requires a released assignment",
                    row_type="attempt",
                    row_id=row_id,
                )
            if attempt.get("nonconfirmatory") != assignment.get("nonconfirmatory"):
                report.error(
                    "attempt_assignment_scope_mismatch",
                    "attempt and assignment must share nonconfirmatory scope",
                    row_type="attempt",
                    row_id=row_id,
                )

        created_at = _parse_timestamp(attempt.get("created_at"))
        started_at = _parse_timestamp(attempt.get("started_at"))
        ended_at = _parse_timestamp(attempt.get("ended_at"))
        if created_at is not None and started_at is not None and created_at > started_at:
            report.error(
                "attempt_clock_order_invalid",
                "attempt record must be created no later than execution start",
                row_type="attempt",
                row_id=row_id,
            )
        if started_at is not None and ended_at is not None and started_at > ended_at:
            report.error(
                "attempt_clock_order_invalid",
                "attempt started_at occurs after ended_at",
                row_type="attempt",
                row_id=row_id,
            )

        state = attempt.get("attempt_state")
        execution = attempt.get("execution_status")
        disposition = attempt.get("disposition")
        if state == "completed" and (
            ended_at is None or execution == "unknown" or disposition == "in_progress"
        ):
            report.error(
                "attempt_state_inconsistent",
                "completed attempt requires an end time, resolved execution status, and disposition",
                row_type="attempt",
                row_id=row_id,
            )
        if state in {"initiated", "in_progress"} and (
            ended_at is not None or execution != "unknown" or disposition != "in_progress"
        ):
            report.error(
                "attempt_state_inconsistent",
                "initiated/in-progress attempt must remain open with unknown execution status",
                row_type="attempt",
                row_id=row_id,
            )
        if execution in {"failure", "ambiguous", "aborted"} and not attempt.get(
            "status_reason_codes"
        ):
            report.error(
                "attempt_resolution_reason_missing",
                "failure, ambiguous, and aborted attempts require a reason code",
                row_type="attempt",
                row_id=row_id,
            )
        if attempt.get("retry_of_attempt_id") is not None and attempt.get(
            "rework_of_attempt_id"
        ) is not None:
            report.error(
                "attempt_has_retry_and_rework_parent",
                "an attempt cannot simultaneously be a retry and a rework",
                row_type="attempt",
                row_id=row_id,
            )
        for parent_field in ("retry_of_attempt_id", "rework_of_attempt_id"):
            parent_id = attempt.get(parent_field)
            parent = attempts.get(str(parent_id)) if parent_id is not None else None
            parent_ended = _parse_timestamp(parent.get("ended_at")) if parent is not None else None
            if (
                parent_ended is not None
                and started_at is not None
                and parent_ended > started_at
            ):
                report.error(
                    "attempt_lineage_clock_invalid",
                    f"{parent_field} parent ends after the child starts",
                    row_type="attempt",
                    row_id=row_id,
                    target_id=parent_id,
                )

    codes = {
        "assignment_clock_order_invalid",
        "attempt_from_unreleased_assignment",
        "attempt_assignment_scope_mismatch",
        "attempt_clock_order_invalid",
        "attempt_state_inconsistent",
        "attempt_resolution_reason_missing",
        "attempt_has_retry_and_rework_parent",
        "attempt_lineage_clock_invalid",
    }
    report.check(
        "assignment_attempt_state_machine",
        not any(error["code"] in codes for error in report.blocking_errors),
    )


def _validate_dags(
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]],
    indexes: Mapping[str, Mapping[str, dict[str, Any]]],
    report: _Report,
) -> None:
    physical_edges: list[tuple[str, str]] = []
    for row in rows_by_type.get("physical_edge", []):
        physical_edges.extend(
            (source, target)
            for source in _reference_values(row, "source_node_ids")
            for target in _reference_values(row, "target_node_ids")
        )
    physical_ok, physical_cycle = _acyclic(indexes["physical_node"], physical_edges)
    if not physical_ok:
        report.error(
            "physical_lineage_cycle",
            "physical lineage must be acyclic",
            cycle_nodes=physical_cycle[:20],
        )
    report.check(
        "physical_lineage_acyclic",
        physical_ok,
        details={"nodes": len(indexes["physical_node"]), "edges": len(physical_edges)},
    )

    attempt_edges: list[tuple[str, str]] = []
    for row in rows_by_type.get("attempt", []):
        target = row.get("attempt_id")
        if not isinstance(target, str):
            continue
        attempt_edges.extend(
            (source, target)
            for field_name in ("retry_of_attempt_id", "rework_of_attempt_id")
            for source in _reference_values(row, field_name)
        )
    attempts_ok, attempt_cycle = _acyclic(indexes["attempt"], attempt_edges)
    if not attempts_ok:
        report.error(
            "attempt_lineage_cycle",
            "retry/rework lineage must be acyclic",
            cycle_nodes=attempt_cycle[:20],
        )
    correction_edges = [
        (source, str(row.get("correction_id")))
        for row in rows_by_type.get("correction", [])
        for source in _reference_values(row, "supersedes_correction_id")
    ]
    corrections_ok, correction_cycle = _acyclic(indexes["correction"], correction_edges)
    if not corrections_ok:
        report.error(
            "correction_lineage_cycle",
            "correction supersession lineage must be acyclic",
            cycle_nodes=correction_cycle[:20],
        )

    resource_nodes = {
        *(f"artifact:{value}" for value in indexes["artifact"]),
        *(f"representation:{value}" for value in indexes["representation"]),
        *(f"transformation:{value}" for value in indexes["transformation"]),
    }
    transform_edges: list[tuple[str, str]] = []
    producers: defaultdict[str, list[str]] = defaultdict(list)
    for row in rows_by_type.get("artifact", []):
        output = f"artifact:{row.get('artifact_id')}"
        transform_edges.extend(
            (f"artifact:{source}", output)
            for source in _reference_values(row, "source_artifact_ids")
        )
    for row in rows_by_type.get("representation", []):
        output = f"representation:{row.get('representation_id')}"
        transform_edges.extend(
            (f"representation:{source}", output)
            for source in _reference_values(row, "source_representation_ids")
        )
        transform_edges.extend(
            (f"artifact:{source}", output)
            for source in _reference_values(row, "source_artifact_ids")
        )
    for row in rows_by_type.get("transformation", []):
        transformation_id = str(row.get("transformation_id"))
        transform_node = f"transformation:{transformation_id}"
        method_artifact_ids = [
            artifact_id
            for method_field in ("code", "configuration")
            for method in [row.get(method_field)]
            if isinstance(method, dict)
            for artifact_id in _reference_values(method, "artifact_id")
        ]
        inputs = [
            *(f"artifact:{value}" for value in _reference_values(row, "input_artifact_ids")),
            *(
                f"artifact:{value}"
                for value in _reference_values(row, "reference_artifact_ids")
            ),
            *(f"artifact:{value}" for value in method_artifact_ids),
            *(
                f"representation:{value}"
                for value in _reference_values(row, "input_representation_ids")
            ),
        ]
        outputs = [
            *(f"artifact:{value}" for value in _reference_values(row, "output_artifact_ids")),
            *(
                f"representation:{value}"
                for value in _reference_values(row, "output_representation_ids")
            ),
        ]
        transform_edges.extend((value, transform_node) for value in inputs)
        transform_edges.extend((transform_node, value) for value in outputs)
        for value in outputs:
            producers[value].append(transformation_id)
        started_at = _parse_timestamp(row.get("started_at"))
        finished_at = _parse_timestamp(row.get("finished_at"))
        if started_at is not None and finished_at is not None and started_at > finished_at:
            report.error(
                "transformation_clock_order_invalid",
                "transformation started_at occurs after finished_at",
                row_type="transformation",
                row_id=transformation_id,
            )
        for method_field in ("code", "configuration"):
            method = row.get(method_field)
            if not isinstance(method, dict):
                continue
            artifact_id = method.get("artifact_id")
            artifact = indexes["artifact"].get(str(artifact_id))
            if (
                artifact is None
                or method.get("sha256") is None
                or method.get("sha256") != artifact.get("sha256")
            ):
                report.error(
                    "transformation_method_hash_mismatch",
                    f"{method_field} hash must match its referenced artifact",
                    row_type="transformation",
                    row_id=transformation_id,
                    target_id=artifact_id,
                )
    for resource, producer_ids in producers.items():
        if len(producer_ids) > 1:
            report.error(
                "multiple_transformation_producers",
                f"{resource} is declared as output by multiple transformations",
                transformation_ids=sorted(producer_ids),
            )
    transform_ok, transform_cycle = _acyclic(resource_nodes, transform_edges)
    if not transform_ok:
        report.error(
            "transformation_lineage_cycle",
            "artifact/representation transformation lineage must be acyclic",
            cycle_nodes=transform_cycle[:20],
        )
    report.check(
        "transformation_lineage_acyclic",
        transform_ok
        and not any(
            error["code"]
            in {"transformation_clock_order_invalid", "transformation_method_hash_mismatch"}
            for error in report.blocking_errors
        ),
        details={"nodes": len(resource_nodes), "edges": len(transform_edges)},
    )

    transformations = indexes["transformation"]
    for row in rows_by_type.get("representation", []):
        representation_id = str(row.get("representation_id"))
        for transformation_id in _reference_values(row, "transformation_ids"):
            transformation = transformations.get(transformation_id)
            if transformation is not None and representation_id not in _reference_values(
                transformation, "output_representation_ids"
            ):
                report.error(
                    "transformation_backreference_mismatch",
                    "representation cites a transformation that does not output it",
                    row_type="representation",
                    row_id=representation_id,
                    transformation_id=transformation_id,
                )


def _validate_artifact_files(
    root: Path,
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]],
    report: _Report,
) -> None:
    checked = 0
    for row in rows_by_type.get("artifact", []):
        location = row.get("location")
        if not isinstance(location, dict) or location.get("status") != "available_bundle_file":
            continue
        artifact_id = str(row.get("artifact_id"))
        try:
            path = _safe_bundle_path(root, location.get("path"))
        except ValueError as exc:
            report.error(
                "unsafe_artifact_path", str(exc), row_type="artifact", row_id=artifact_id
            )
            continue
        if not path.is_file():
            report.error(
                "artifact_file_missing",
                f"declared artifact file does not exist: {path}",
                row_type="artifact",
                row_id=artifact_id,
            )
            continue
        observed_bytes = path.stat().st_size
        observed_hash = _sha256_file(path)
        checked += 1
        report.hashes[f"artifact:{artifact_id}"] = {
            "path": str(location.get("path")),
            "sha256": observed_hash,
            "bytes": observed_bytes,
        }
        if row.get("bytes") != observed_bytes:
            report.error(
                "artifact_bytes_mismatch",
                f"declared bytes={row.get('bytes')!r}, observed={observed_bytes}",
                row_type="artifact",
                row_id=artifact_id,
            )
        if row.get("sha256") != observed_hash:
            report.error(
                "artifact_hash_mismatch",
                "declared SHA-256 does not match artifact bytes",
                row_type="artifact",
                row_id=artifact_id,
            )
    report.counts["bundle_artifacts_verified"] = checked
    report.check(
        "bundle_artifacts_match_ledger",
        not any(
            error["code"]
            in {
                "unsafe_artifact_path",
                "artifact_file_missing",
                "artifact_bytes_mismatch",
                "artifact_hash_mismatch",
            }
            for error in report.blocking_errors
        ),
    )


def _compare_elapsed(left: object, right: object) -> bool | None:
    left_value = _elapsed_seconds(left)
    right_value = _elapsed_seconds(right)
    if left_value is None or right_value is None or left_value[1] != right_value[1]:
        return None
    return left_value[0] <= right_value[0]


def _validate_representation_semantics(
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]], report: _Report
) -> None:
    for row in rows_by_type.get("representation", []):
        row_id = _row_identity(row)
        status = row.get("status")
        available = row.get("primary_analysis_available")
        reason_codes = row.get("availability_reason_codes")
        if status == "available" and available is not True:
            report.error(
                "representation_availability_inconsistent",
                "available representation must be primary_analysis_available",
                row_type="representation",
                row_id=row_id,
            )
        if status != "available" and available is not False:
            report.error(
                "representation_availability_inconsistent",
                "non-available representation cannot be primary_analysis_available",
                row_type="representation",
                row_id=row_id,
            )
        if status != "available" and not reason_codes:
            report.error(
                "representation_missing_reason",
                "non-available representation requires an availability reason",
                row_type="representation",
                row_id=row_id,
            )

        state_comparison = _compare_elapsed(
            row.get("latest_material_state"), row.get("declared_state_cutoff")
        )
        declared_state_status = row.get("state_cutoff_status")
        expected_state_status = (
            "unverifiable"
            if state_comparison is None
            else "passed"
            if state_comparison
            else "failed"
        )
        if declared_state_status != expected_state_status:
            report.error(
                "state_cutoff_status_mismatch",
                f"declared {declared_state_status!r}; clocks imply {expected_state_status!r}",
                row_type="representation",
                row_id=row_id,
            )

        deadline = row.get("declared_decision_deadline")
        deadline_comparison = _compare_elapsed(row.get("operational_ready_elapsed"), deadline)
        declared_deadline_status = row.get("decision_deadline_status")
        expected_deadline_status = (
            "not_declared"
            if deadline is None
            else "unverifiable"
            if deadline_comparison is None
            else "passed"
            if deadline_comparison
            else "failed"
        )
        if declared_deadline_status != expected_deadline_status:
            report.error(
                "decision_deadline_status_mismatch",
                f"declared {declared_deadline_status!r}; clocks imply {expected_deadline_status!r}",
                row_type="representation",
                row_id=row_id,
            )
        if available is True and (
            declared_state_status != "passed" or declared_deadline_status != "passed"
        ):
            report.error(
                "ineligible_representation_marked_available",
                "primary-analysis representation must pass cutoff and decision deadline",
                row_type="representation",
                row_id=row_id,
            )
        if available is True and row.get("prohibited_input_check") != "passed":
            report.error(
                "prohibited_input_check_not_passed",
                "primary-analysis representation must pass prohibited-input checks",
                row_type="representation",
                row_id=row_id,
            )
        if available is True and row.get("builder_blinding_attestation") is not True:
            report.error(
                "builder_blinding_missing",
                "primary-analysis representation requires builder blinding attestation",
                row_type="representation",
                row_id=row_id,
            )

        # Acquisition can begin before the latest in-situ material state, so those two
        # clocks are not ordered against each other. Both must precede construction.
        clock_pairs = (
            ("material_state_at", "constructed_at"),
            ("acquired_at", "constructed_at"),
            ("constructed_at", "operationally_available_at"),
            ("operationally_available_at", "frozen_at"),
        )
        for earlier_field, later_field in clock_pairs:
            earlier = _parse_timestamp(row.get(earlier_field))
            later = _parse_timestamp(row.get(later_field))
            if earlier is not None and later is not None and earlier > later:
                report.error(
                    "representation_clock_order_invalid",
                    f"{earlier_field} occurs after {later_field}",
                    row_type="representation",
                    row_id=row_id,
                )
    report.check(
        "representation_cutoff_and_deadline_consistent",
        not any(
            error["code"]
            in {
                "state_cutoff_status_mismatch",
                "decision_deadline_status_mismatch",
                "ineligible_representation_marked_available",
                "representation_clock_order_invalid",
            }
            for error in report.blocking_errors
        ),
    )


def _validate_outcome_semantics(
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]], report: _Report
) -> None:
    censor_statuses = {"right_censored", "left_censored", "interval_censored"}
    for row in rows_by_type.get("outcome", []):
        row_id = _row_identity(row)
        status = row.get("status")
        eligible = row.get("eligible")
        value = row.get("value")
        lower = row.get("lower_bound")
        upper = row.get("upper_bound")
        censor_reason = row.get("censoring_reason_code")
        if status == "ineligible":
            if eligible is not False:
                report.error(
                    "outcome_eligibility_inconsistent",
                    "ineligible status requires eligible=false",
                    row_type="outcome",
                    row_id=row_id,
                )
        elif eligible is not True:
            report.error(
                "outcome_eligibility_inconsistent",
                "every status except ineligible refers to a scientifically eligible target",
                row_type="outcome",
                row_id=row_id,
            )
        if status == "observed_exact":
            if value is None or lower is not None or upper is not None or censor_reason is not None:
                report.error(
                    "exact_outcome_semantics_invalid",
                    "exact outcome requires value and forbids censoring bounds/reason",
                    row_type="outcome",
                    row_id=row_id,
                )
            target_type = row.get("target_type")
            numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
            value_valid = True
            if target_type in {"continuous", "time_to_event"}:
                value_valid = numeric and (
                    target_type != "time_to_event" or float(value) >= 0
                )
            elif target_type == "count":
                value_valid = isinstance(value, int) and not isinstance(value, bool) and value >= 0
            elif target_type == "binary":
                value_valid = isinstance(value, bool) or (
                    numeric and float(value) in {0.0, 1.0}
                )
            elif target_type == "categorical":
                value_valid = isinstance(value, str)
            if not value_valid:
                report.error(
                    "outcome_value_type_mismatch",
                    "exact outcome value is incompatible with target_type",
                    row_type="outcome",
                    row_id=row_id,
                )
            if row.get("followup_status") != "complete":
                report.error(
                    "exact_outcome_followup_invalid",
                    "exact outcome requires complete follow-up",
                    row_type="outcome",
                    row_id=row_id,
                )
        elif status in censor_statuses:
            valid_bounds = (
                status == "right_censored" and lower is not None and upper is None
            ) or (status == "left_censored" and lower is None and upper is not None) or (
                status == "interval_censored"
                and isinstance(lower, (int, float))
                and isinstance(upper, (int, float))
                and not isinstance(lower, bool)
                and not isinstance(upper, bool)
                and float(lower) < float(upper)
            )
            if value is not None or not valid_bounds or censor_reason is None:
                report.error(
                    "censored_outcome_semantics_invalid",
                    "censored outcome has inconsistent value, bounds, or reason",
                    row_type="outcome",
                    row_id=row_id,
                )
        else:
            if value is not None or lower is not None or upper is not None:
                report.error(
                    "null_outcome_semantics_invalid",
                    "missing/not-followed/unresolved/ineligible outcomes cannot carry values or bounds",
                    row_type="outcome",
                    row_id=row_id,
                )
            if not row.get("eligibility_reason_codes"):
                report.error(
                    "null_outcome_reason_missing",
                    "non-observed outcome requires an explicit reason code",
                    row_type="outcome",
                    row_id=row_id,
                )
        assayed_at = _parse_timestamp(row.get("assayed_at"))
        created_at = _parse_timestamp(row.get("created_at"))
        accessible_at = _parse_timestamp(row.get("accessible_at"))
        if assayed_at is not None and created_at is not None and assayed_at > created_at:
            report.error(
                "outcome_clock_order_invalid",
                "outcome assayed_at occurs after created_at",
                row_type="outcome",
                row_id=row_id,
            )
        if created_at is not None and accessible_at is not None and created_at > accessible_at:
            report.error(
                "outcome_clock_order_invalid",
                "outcome created_at occurs after accessible_at",
                row_type="outcome",
                row_id=row_id,
            )
    report.check(
        "outcome_exact_and_censor_semantics",
        not any(
            error["code"]
            in {
                "outcome_eligibility_inconsistent",
                "exact_outcome_semantics_invalid",
                "exact_outcome_followup_invalid",
                "censored_outcome_semantics_invalid",
                "null_outcome_semantics_invalid",
                "null_outcome_reason_missing",
                "outcome_value_type_mismatch",
                "outcome_clock_order_invalid",
            }
            for error in report.blocking_errors
        ),
    )


def _validate_events(
    tables: Sequence[_LoadedTable],
    indexes: Mapping[str, Mapping[str, dict[str, Any]]],
    report: _Report,
) -> None:
    event_rows = [
        row
        for table in tables
        if table.descriptor.get("table_id") == "events"
        for row in table.rows
    ]
    events: dict[str, dict[str, Any]] = {}
    for row in event_rows:
        event_id = row.get("event_id")
        if not isinstance(event_id, str):
            continue
        if event_id in events:
            report.error(
                "duplicate_event_ledger_id",
                f"event ledger repeats event_id {event_id!r}",
                row_id=event_id,
            )
        events[event_id] = row
    attempt_by_event = {
        str(row.get("event_id")): row for row in indexes["attempt"].values()
    }
    for event_id in sorted(set(attempt_by_event).difference(events)):
        report.error(
            "attempt_event_missing",
            f"attempt event_id {event_id!r} has no event-ledger row",
            row_id=event_id,
        )
    for event_id in sorted(set(events).difference(attempt_by_event)):
        report.error(
            "orphan_event",
            f"event-ledger row {event_id!r} has no attempt",
            row_id=event_id,
        )
    for event_id in sorted(set(events).intersection(attempt_by_event)):
        event_outcome = events[event_id].get("outcome")
        event_status = event_outcome.get("status") if isinstance(event_outcome, dict) else None
        attempt_status = attempt_by_event[event_id].get("execution_status")
        if isinstance(event_status, str) and event_status != attempt_status:
            report.error(
                "event_attempt_status_mismatch",
                f"event status {event_status!r} differs from attempt {attempt_status!r}",
                row_id=event_id,
            )
    report.counts["events"] = len(event_rows)
    report.check(
        "attempt_event_ledger_consistent",
        not any(
            error["code"]
            in {
                "duplicate_event_ledger_id",
                "attempt_event_missing",
                "orphan_event",
                "event_attempt_status_mismatch",
            }
            for error in report.blocking_errors
        ),
    )


def _validate_partition_isolation(
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]], report: _Report
) -> None:
    nodes = {
        str(row.get("node_id")): row for row in rows_by_type.get("physical_node", [])
    }
    physical_edges = [
        (source, target)
        for edge in rows_by_type.get("physical_edge", [])
        for source in _reference_values(edge, "source_node_ids")
        for target in _reference_values(edge, "target_node_ids")
    ]
    descendants = _transitive_reachability(nodes, physical_edges)
    parent_partitions: defaultdict[str, set[str]] = defaultdict(set)
    attempt_partitions: defaultdict[str, set[str]] = defaultdict(set)
    for row in rows_by_type.get("physical_node", []):
        partition = row.get("partition")
        parent_id = row.get("independent_parent_id")
        row_id = _row_identity(row)
        if partition in _ANALYTIC_PARTITIONS and not isinstance(parent_id, str):
            report.error(
                "analytic_node_missing_independent_parent",
                "analytic physical node requires independent_parent_id",
                row_type="physical_node",
                row_id=row_id,
            )
        if isinstance(parent_id, str) and isinstance(partition, str):
            parent_partitions[parent_id].add(partition)
            if row_id != parent_id and row_id not in descendants.get(parent_id, set()):
                report.error(
                    "independent_parent_not_ancestor",
                    "declared independent parent is not this node or a physical ancestor",
                    row_type="physical_node",
                    row_id=row_id,
                    independent_parent_id=parent_id,
                )
        for attempt_id in _reference_values(row, "source_attempt_ids"):
            if isinstance(partition, str):
                attempt_partitions[attempt_id].add(partition)
        if row.get("nonconfirmatory") is True and partition in _ANALYTIC_PARTITIONS:
            report.error(
                "nonconfirmatory_node_in_analysis_partition",
                "nonconfirmatory physical node cannot enter an analytic partition",
                row_type="physical_node",
                row_id=row_id,
            )
        if partition == "nonconfirmatory" and row.get("nonconfirmatory") is not True:
            report.error(
                "partition_flag_mismatch",
                "nonconfirmatory partition requires nonconfirmatory=true",
                row_type="physical_node",
                row_id=row_id,
            )
    for parent_id, partitions in sorted(parent_partitions.items()):
        analytic = partitions.intersection(_ANALYTIC_PARTITIONS)
        if len(analytic) > 1:
            report.error(
                "independent_parent_partition_leakage",
                "descendants of one independent parent cross analytic partitions",
                independent_parent_id=parent_id,
                partitions=sorted(analytic),
            )
        if "nonconfirmatory" in partitions and analytic:
            report.error(
                "nonconfirmatory_parent_partition_leakage",
                "one independent parent contributes to both nonconfirmatory and analytic data",
                independent_parent_id=parent_id,
                partitions=sorted(partitions),
            )
    for source_id, target_id in physical_edges:
        source = nodes.get(source_id)
        target = nodes.get(target_id)
        if source is None or target is None:
            continue
        source_parent = source.get("independent_parent_id")
        target_parent = target.get("independent_parent_id")
        if (
            isinstance(source_parent, str)
            and isinstance(target_parent, str)
            and source_parent != target_parent
        ):
            report.error(
                "physical_edge_parent_mismatch",
                "connected descendants declare different independent parents",
                source_node_id=source_id,
                target_node_id=target_id,
                source_parent_id=source_parent,
                target_parent_id=target_parent,
            )
        source_nonconfirmatory = (
            source.get("nonconfirmatory") is True
            or source.get("partition") == "nonconfirmatory"
        )
        if source_nonconfirmatory and target.get("partition") in _ANALYTIC_PARTITIONS:
            report.error(
                "nonconfirmatory_ancestry_in_analysis_partition",
                "analytic node descends from a nonconfirmatory physical node",
                source_node_id=source_id,
                target_node_id=target_id,
            )
    for attempt_id, partitions in sorted(attempt_partitions.items()):
        analytic = partitions.intersection(_ANALYTIC_PARTITIONS)
        if len(analytic) > 1:
            report.error(
                "attempt_partition_leakage",
                "one attempt contributes physical descendants to multiple analytic partitions",
                row_id=attempt_id,
                partitions=sorted(analytic),
            )
    report.counts["independent_parents"] = len(parent_partitions)
    report.counts["independent_parents_by_partition"] = dict(
        sorted(
            Counter(
                partition
                for partitions in parent_partitions.values()
                for partition in partitions
                if partition in _ANALYTIC_PARTITIONS or partition == "nonconfirmatory"
            ).items()
        )
    )
    report.check(
        "independent_parent_partition_isolation",
        not any(
            error["code"]
            in {
                "analytic_node_missing_independent_parent",
                "independent_parent_partition_leakage",
                "nonconfirmatory_parent_partition_leakage",
                "independent_parent_not_ancestor",
                "physical_edge_parent_mismatch",
                "nonconfirmatory_ancestry_in_analysis_partition",
                "attempt_partition_leakage",
                "nonconfirmatory_node_in_analysis_partition",
                "partition_flag_mismatch",
            }
            for error in report.blocking_errors
        ),
    )


def _validate_unit_freeze_order(
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]], report: _Report
) -> None:
    outcomes_by_subject: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    outcomes_by_attempt: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for outcome in rows_by_type.get("outcome", []):
        subject_id = outcome.get("subject_node_id")
        if isinstance(subject_id, str):
            outcomes_by_subject[subject_id].append(outcome)
        for attempt_id in _reference_values(outcome, "source_attempt_ids"):
            outcomes_by_attempt[attempt_id].append(outcome)
    physical_edges = [
        (source, target)
        for edge in rows_by_type.get("physical_edge", [])
        for source in _reference_values(edge, "source_node_ids")
        for target in _reference_values(edge, "target_node_ids")
    ]
    node_ids = [
        str(node.get("node_id")) for node in rows_by_type.get("physical_node", [])
    ]
    descendants = _transitive_reachability(node_ids, physical_edges)
    comparisons = 0
    relevant_pairs = 0
    unmatched_representations = 0
    for representation in rows_by_type.get("representation", []):
        subject_id = representation.get("subject_node_id")
        attempt_id = representation.get("attempt_id")
        frozen_at = _parse_timestamp(representation.get("frozen_at"))
        if not isinstance(subject_id, str) or frozen_at is None:
            continue
        relevant: dict[str, dict[str, Any]] = {}
        candidate_subjects = {subject_id, *descendants.get(subject_id, set())}
        for candidate_subject in candidate_subjects:
            for outcome in outcomes_by_subject.get(candidate_subject, []):
                outcome_id = _row_identity(outcome)
                if outcome_id is not None:
                    relevant[outcome_id] = outcome
        if isinstance(attempt_id, str):
            for outcome in outcomes_by_attempt.get(attempt_id, []):
                outcome_id = _row_identity(outcome)
                if outcome_id is not None:
                    relevant[outcome_id] = outcome
        if not relevant:
            unmatched_representations += 1
        for outcome in relevant.values():
            relevant_pairs += 1
            accessible_at = _parse_timestamp(outcome.get("accessible_at"))
            if accessible_at is None:
                continue
            comparisons += 1
            if frozen_at >= accessible_at:
                report.error(
                    "unit_freeze_after_outcome_access",
                    "representation must freeze strictly before its subject outcome is accessible",
                    row_type="representation",
                    row_id=_row_identity(representation),
                    outcome_id=_row_identity(outcome),
                )
    report.counts["unit_freeze_outcome_comparisons"] = comparisons
    report.counts["unit_freeze_relevant_pairs"] = relevant_pairs
    report.counts["unit_freeze_unmatched_representations"] = unmatched_representations
    report.check(
        "unit_level_freeze_precedes_outcome_access",
        comparisons == relevant_pairs and unmatched_representations == 0
        and
        not any(
            error["code"] == "unit_freeze_after_outcome_access"
            for error in report.blocking_errors
        ),
        details={
            "comparisons": comparisons,
            "relevant_pairs": relevant_pairs,
            "unmatched_representations": unmatched_representations,
        },
    )


def _validate_decisions_and_corrections(
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]],
    indexes: Mapping[str, Mapping[str, dict[str, Any]]],
    report: _Report,
) -> None:
    physical_edges = [
        (source, target)
        for edge in rows_by_type.get("physical_edge", [])
        for source in _reference_values(edge, "source_node_ids")
        for target in _reference_values(edge, "target_node_ids")
    ]
    descendants = _transitive_reachability(indexes["physical_node"], physical_edges)
    decision_keys: Counter[tuple[object, object]] = Counter(
        (row.get("attempt_id"), row.get("subject_node_id"))
        for row in rows_by_type.get("decision", [])
    )
    for key, count in decision_keys.items():
        if count > 1:
            report.error(
                "duplicate_subject_decision",
                "attempt and subject have multiple primary decision rows",
                attempt_id=key[0],
                subject_node_id=key[1],
            )
    for row in rows_by_type.get("decision", []):
        row_id = _row_identity(row)
        allowed = row.get("allowed_actions")
        actual = row.get("actual_action")
        if isinstance(allowed, list) and actual not in allowed:
            report.error(
                "decision_action_not_allowed",
                "actual_action is not in the row's allowed_actions",
                row_type="decision",
                row_id=row_id,
            )
        fallback = row.get("fallback")
        if isinstance(fallback, dict) and fallback.get("used") is True:
            fallback_action = fallback.get("action")
            if isinstance(allowed, list) and fallback_action not in allowed:
                report.error(
                    "fallback_action_not_allowed",
                    "fallback action is not in allowed_actions",
                    row_type="decision",
                    row_id=row_id,
                )
            if fallback_action != actual:
                report.error(
                    "fallback_action_mismatch",
                    "when fallback is used, its action must equal actual_action",
                    row_type="decision",
                    row_id=row_id,
                )
        if row.get("actual_report_available") is False and not (
            isinstance(fallback, dict) and fallback.get("used") is True
        ):
            report.error(
                "missing_report_without_fallback",
                "an unavailable ordinary report requires an explicit fallback",
                row_type="decision",
                row_id=row_id,
            )
        if row.get("decision_mode") == "shadow" and row.get("research_output_visible") is not False:
            report.error(
                "shadow_output_visible",
                "shadow-mode research output must not be visible to the decision maker",
                row_type="decision",
                row_id=row_id,
            )
        decided_at = _parse_timestamp(row.get("decided_at"))
        deadline_at = _parse_timestamp(row.get("decision_deadline_at"))
        if decided_at is not None and deadline_at is not None and decided_at > deadline_at:
            report.error(
                "decision_after_deadline",
                "decision occurred after its declared absolute deadline",
                row_type="decision",
                row_id=row_id,
            )
        for representation_id in _reference_values(row, "available_representation_ids"):
            representation = indexes["representation"].get(representation_id)
            if representation is None:
                continue
            ready_at = _parse_timestamp(representation.get("operationally_available_at"))
            if representation.get("primary_analysis_available") is not True:
                report.error(
                    "decision_cites_unavailable_representation",
                    "decision availability list contains an unavailable representation",
                    row_type="decision",
                    row_id=row_id,
                    target_id=representation_id,
                )
            if decided_at is not None and (ready_at is None or ready_at > decided_at):
                report.error(
                    "decision_cites_late_representation",
                    "decision availability list contains a representation not ready by decision time",
                    row_type="decision",
                    row_id=row_id,
                    target_id=representation_id,
                )
        report_artifact_id = row.get("actual_report_artifact_id")
        report_artifact = indexes["artifact"].get(str(report_artifact_id))
        if report_artifact is not None:
            report_subject = row.get("subject_node_id")
            artifact_subjects = _reference_values(report_artifact, "subject_node_ids")
            subject_linked = any(
                artifact_subject == report_subject
                or report_subject in descendants.get(artifact_subject, set())
                for artifact_subject in artifact_subjects
            )
            if (
                report_artifact.get("artifact_role") != "conventional_report"
                or row.get("attempt_id")
                not in _reference_values(report_artifact, "attempt_ids")
                or not subject_linked
            ):
                report.error(
                    "decision_report_artifact_mismatch",
                    "actual report artifact must be a conventional report on this attempt lineage",
                    row_type="decision",
                    row_id=row_id,
                    target_id=report_artifact_id,
                )
    for row in rows_by_type.get("correction", []):
        row_id = _row_identity(row)
        if row.get("status") == "applied":
            approvals = row.get("approvals")
            if not isinstance(approvals, list) or not approvals or any(
                not isinstance(approval, dict) or approval.get("status") != "approved"
                for approval in approvals
            ):
                report.error(
                    "applied_correction_not_approved",
                    "every recorded approval on an applied correction must be approved",
                    row_type="correction",
                    row_id=row_id,
                )
            approved_people = {
                approval.get("approver_id")
                for approval in approvals or []
                if isinstance(approval, dict) and approval.get("status") == "approved"
            }
            if row.get("nonconfirmatory") is False and len(approved_people) < 2:
                report.error(
                    "confirmatory_correction_lacks_two_person_approval",
                    "applied confirmatory correction requires two distinct approvers",
                    row_type="correction",
                    row_id=row_id,
                )
            if set(row.get("before_hashes", [])).intersection(row.get("after_hashes", [])):
                report.error(
                    "applied_correction_hash_unchanged",
                    "an applied correction must create successor bytes rather than reuse a prior hash",
                    row_type="correction",
                    row_id=row_id,
                )
        discovered_at = _parse_timestamp(row.get("discovered_at"))
        for approval in row.get("approvals", []):
            if not isinstance(approval, dict):
                continue
            decided_at = _parse_timestamp(approval.get("decided_at"))
            if (
                discovered_at is not None
                and decided_at is not None
                and decided_at < discovered_at
            ):
                report.error(
                    "correction_approval_predates_discovery",
                    "correction approval cannot precede discovery",
                    row_type="correction",
                    row_id=row_id,
                )
        if row.get("outcome_access_state") in {"outcomes_accessed", "unverifiable"}:
            impact = row.get("impact")
            claim = impact.get("claim") if isinstance(impact, dict) else None
            if row.get("status") == "applied" and claim not in {"downgraded", "withdrawn"}:
                report.error(
                    "post_outcome_correction_claim_not_downgraded",
                    "post-access applied correction must downgrade or withdraw the frozen claim",
                    row_type="correction",
                    row_id=row_id,
                )
    report.check(
        "decision_and_correction_semantics",
        not any(
            error["code"]
            in {
                "decision_action_not_allowed",
                "fallback_action_not_allowed",
                "fallback_action_mismatch",
                "missing_report_without_fallback",
                "shadow_output_visible",
                "decision_after_deadline",
                "decision_cites_unavailable_representation",
                "decision_cites_late_representation",
                "decision_report_artifact_mismatch",
                "duplicate_subject_decision",
                "applied_correction_not_approved",
                "confirmatory_correction_lacks_two_person_approval",
                "applied_correction_hash_unchanged",
                "correction_approval_predates_discovery",
                "post_outcome_correction_claim_not_downgraded",
            }
            for error in report.blocking_errors
        ),
    )


def _validate_study_contract(
    study: Mapping[str, Any],
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]],
    indexes: Mapping[str, Mapping[str, dict[str, Any]]],
    report: _Report,
) -> None:
    artifacts = indexes["artifact"]
    attempts = indexes["attempt"]
    nodes = indexes["physical_node"]
    physical_edges = [
        (source, target)
        for edge in rows_by_type.get("physical_edge", [])
        for source in _reference_values(edge, "source_node_ids")
        for target in _reference_values(edge, "target_node_ids")
    ]
    physical_descendants = _transitive_reachability(nodes, physical_edges)

    specs: dict[str, dict[str, Any]] = {}
    for spec_value in study.get("representations", []):
        if not isinstance(spec_value, dict):
            continue
        spec_id = spec_value.get("representation_spec_id")
        if not isinstance(spec_id, str):
            continue
        if spec_id in specs:
            report.error(
                "duplicate_representation_spec_id",
                f"representation_spec_id {spec_id!r} is duplicated",
            )
        specs[spec_id] = spec_value
    spec_edges: list[tuple[str, str]] = []
    for spec_id, spec in specs.items():
        for parent in _reference_values(spec, "parent_representation_spec_ids"):
            if parent not in specs:
                report.error(
                    "missing_representation_spec_parent",
                    f"representation spec {spec_id!r} cites absent parent {parent!r}",
                )
            spec_edges.append((parent, spec_id))
        workflow = spec.get("actual_workflow_artifact")
        if isinstance(workflow, dict):
            for field_name in ("artifact_id", "practitioner_validation_artifact_id"):
                artifact_id = workflow.get(field_name)
                if artifact_id is not None and artifact_id not in artifacts:
                    report.error(
                        "study_artifact_reference_missing",
                        f"representation spec {spec_id!r} {field_name} is absent",
                        target_id=artifact_id,
                    )
    specs_ok, spec_cycle = _acyclic(specs, spec_edges)
    if not specs_ok:
        report.error(
            "representation_spec_cycle",
            "declared representation ladder must be acyclic",
            cycle_nodes=spec_cycle[:20],
        )
    specs_by_role: defaultdict[str, set[str]] = defaultdict(set)
    for spec_id, spec in specs.items():
        role = spec.get("role")
        if isinstance(role, str):
            specs_by_role[role].add(spec_id)
    required_roles = {"context", "native_evidence", "conventional_report"}
    missing_roles = sorted(required_roles.difference(specs_by_role))
    if missing_roles:
        report.error(
            "required_representation_role_missing",
            "study must declare context, native evidence, and the actual conventional report",
            missing_roles=missing_roles,
        )

    arms: dict[str, dict[str, Any]] = {}
    analysis_arms = study.get("analysis_arms")
    if isinstance(analysis_arms, dict):
        for arm_value in analysis_arms.get("arms", []):
            if not isinstance(arm_value, dict):
                continue
            arm_id = arm_value.get("arm_id")
            if not isinstance(arm_id, str):
                continue
            if arm_id in arms:
                report.error("duplicate_arm_id", f"arm_id {arm_id!r} is duplicated")
            arms[arm_id] = arm_value
            for spec_id in _reference_values(arm_value, "representation_spec_ids"):
                if spec_id not in specs:
                    report.error(
                        "arm_representation_spec_missing",
                        f"arm {arm_id!r} cites absent representation spec {spec_id!r}",
                    )
        comparison_ids: set[str] = set()
        for comparison in analysis_arms.get("comparisons", []):
            if not isinstance(comparison, dict):
                continue
            comparison_id = comparison.get("comparison_id")
            if isinstance(comparison_id, str):
                if comparison_id in comparison_ids:
                    report.error(
                        "duplicate_comparison_id",
                        f"comparison_id {comparison_id!r} is duplicated",
                    )
                comparison_ids.add(comparison_id)
            for field_name in ("compact_arm_id", "reference_arm_id"):
                arm_id = comparison.get(field_name)
                if arm_id not in arms:
                    report.error(
                        "comparison_arm_missing",
                        f"comparison cites absent {field_name} {arm_id!r}",
                    )
            if comparison.get("compact_arm_id") == comparison.get("reference_arm_id"):
                report.error(
                    "comparison_arms_identical",
                    "comparison compact and reference arms must differ",
                    comparison_id=comparison_id,
                )

    arm_spec_sets = [
        set(_reference_values(arm, "representation_spec_ids")) for arm in arms.values()
    ]
    arm_role_sets = [
        {
            str(specs[spec_id].get("role"))
            for spec_id in spec_ids
            if spec_id in specs
        }
        for spec_ids in arm_spec_sets
    ]
    missing_arm_role_sets: list[list[str]] = []
    if not any(observed == {"context"} for observed in arm_role_sets):
        missing_arm_role_sets.append(["context_only"])
    for required in (
        {"context", "native_evidence"},
        {"context", "conventional_report"},
        {"context", "native_evidence", "conventional_report"},
    ):
        if not any(required == observed for observed in arm_role_sets):
            missing_arm_role_sets.append(sorted(required))
    if specs_by_role.get("label_or_grade") and not any(
        observed == {"context", "label_or_grade"} for observed in arm_role_sets
    ):
        missing_arm_role_sets.append(["context", "label_or_grade"])
    if missing_arm_role_sets:
        report.error(
            "required_analysis_arm_missing",
            "analysis must include context, native, report, and native-plus-report arms",
            missing_role_sets=missing_arm_role_sets,
        )
    uncovered_required_specs = sorted(
        spec_id
        for spec_id, spec in specs.items()
        if spec.get("required_for_analysis") is True
        and not any(spec_id in arm_specs for arm_specs in arm_spec_sets)
    )
    if uncovered_required_specs:
        report.error(
            "required_representation_spec_not_in_arm",
            "every required representation spec must appear in a frozen analysis arm",
            representation_spec_ids=uncovered_required_specs,
        )
    if arms and not any(arm.get("primary") is True for arm in arms.values()):
        report.error("primary_arm_missing", "at least one analysis arm must be primary")
    comparisons = analysis_arms.get("comparisons", []) if isinstance(analysis_arms, dict) else []
    if comparisons and not any(
        isinstance(comparison, dict) and comparison.get("primary") is True
        for comparison in comparisons
    ):
        report.error(
            "primary_comparison_missing", "at least one frozen comparison must be primary"
        )

    representation_pairs: dict[tuple[str, str], dict[str, Any]] = {}
    representation_subjects_by_attempt: defaultdict[str, set[str]] = defaultdict(set)
    for row in rows_by_type.get("representation", []):
        row_id = _row_identity(row)
        spec_id = row.get("representation_spec_id")
        attempt_id = row.get("attempt_id")
        if spec_id not in specs:
            report.error(
                "representation_spec_missing",
                f"row cites absent representation spec {spec_id!r}",
                row_type="representation",
                row_id=row_id,
            )
            continue
        if not isinstance(attempt_id, str):
            continue
        pair = (attempt_id, str(spec_id))
        subject_id = row.get("subject_node_id")
        if isinstance(subject_id, str):
            representation_subjects_by_attempt[attempt_id].add(subject_id)
        if pair in representation_pairs:
            report.error(
                "duplicate_attempt_representation_spec",
                "attempt has multiple rows for one representation spec",
                row_type="representation",
                row_id=row_id,
            )
        representation_pairs[pair] = row
        spec = specs[str(spec_id)]
        expected = {
            "declared_state_cutoff": spec.get("state_cutoff"),
            "declared_decision_deadline": spec.get("decision_deadline"),
        }
        for field_name, expected_value in expected.items():
            if row.get(field_name) != expected_value:
                report.error(
                    "representation_spec_value_mismatch",
                    f"{field_name} differs from declared representation spec",
                    row_type="representation",
                    row_id=row_id,
                    field=field_name,
                )
        feature_schema = row.get("feature_schema")
        if isinstance(feature_schema, dict) and (
            feature_schema.get("version") != spec.get("feature_schema_version")
            or feature_schema.get("sha256") != spec.get("feature_schema_sha256")
        ):
            report.error(
                "feature_schema_mismatch",
                "row feature schema differs from declared representation spec",
                row_type="representation",
                row_id=row_id,
            )
        allowed_reasons = set(_reference_values(spec, "availability_reason_codes"))
        unexpected_reasons = set(_reference_values(row, "availability_reason_codes")).difference(
            allowed_reasons
        )
        if unexpected_reasons:
            report.error(
                "undeclared_availability_reason",
                "representation uses reason codes absent from its spec",
                row_type="representation",
                row_id=row_id,
                reason_codes=sorted(unexpected_reasons),
            )
    for attempt_id, subject_ids in representation_subjects_by_attempt.items():
        if len(subject_ids) > 1:
            report.error(
                "attempt_representation_subject_mismatch",
                "all representation arms for one attempt must target the same physical subject",
                attempt_id=attempt_id,
                subject_node_ids=sorted(subject_ids),
            )
    role_artifact_roles = {
        "native_evidence": {"native_trace", "process_log", "intermediate"},
        "calibrated_trace": {"intermediate"},
        "intermediate": {"intermediate"},
        "engineered_features": {"intermediate"},
        "conventional_report": {"conventional_report"},
        "label_or_grade": {"label_or_grade"},
    }
    for row in rows_by_type.get("representation", []):
        row_id = _row_identity(row)
        spec_id = row.get("representation_spec_id")
        spec = specs.get(str(spec_id))
        if spec is None:
            continue
        expected_parent_specs = set(
            _reference_values(spec, "parent_representation_spec_ids")
        )
        actual_parent_specs: set[str] = set()
        for source_id in _reference_values(row, "source_representation_ids"):
            source = indexes["representation"].get(source_id)
            if source is None:
                continue
            source_spec = source.get("representation_spec_id")
            if isinstance(source_spec, str):
                actual_parent_specs.add(source_spec)
            if (
                source.get("attempt_id") != row.get("attempt_id")
                or source.get("subject_node_id") != row.get("subject_node_id")
            ):
                report.error(
                    "representation_parent_scope_mismatch",
                    "representation parent must belong to the same attempt and subject",
                    row_type="representation",
                    row_id=row_id,
                    target_id=source_id,
                )
        if row.get("status") == "available":
            if actual_parent_specs != expected_parent_specs:
                report.error(
                    "representation_parent_spec_mismatch",
                    "available row does not instantiate its declared representation parents",
                    row_type="representation",
                    row_id=row_id,
                    expected_parent_specs=sorted(expected_parent_specs),
                    actual_parent_specs=sorted(actual_parent_specs),
                )
            if expected_parent_specs and not row.get("transformation_ids"):
                report.error(
                    "representation_transformation_missing",
                    "derived available representation requires a transformation record",
                    row_type="representation",
                    row_id=row_id,
                )
            if row.get("value_artifact_id") is None and row.get("inline_domain_values") is None:
                report.error(
                    "available_representation_value_missing",
                    "available representation requires a value artifact or inline value",
                    row_type="representation",
                    row_id=row_id,
                )
        elif not actual_parent_specs.issubset(expected_parent_specs):
            report.error(
                "representation_parent_spec_mismatch",
                "unavailable row cites a source outside its declared representation parents",
                row_type="representation",
                row_id=row_id,
                expected_parent_specs=sorted(expected_parent_specs),
                actual_parent_specs=sorted(actual_parent_specs),
            )

        workflow_contract = spec.get("actual_workflow_artifact")
        if (
            isinstance(workflow_contract, dict)
            and workflow_contract.get("status") == "actual_existing_workflow"
            and row.get("actual_workflow_artifact_id") is None
        ):
            report.error(
                "actual_workflow_instance_missing",
                "actual-workflow representation requires its per-attempt workflow artifact",
                row_type="representation",
                row_id=row_id,
            )
        role = spec.get("role")
        expected_artifact_roles = role_artifact_roles.get(str(role))
        source_artifacts = [
            artifacts[artifact_id]
            for artifact_id in _reference_values(row, "source_artifact_ids")
            if artifact_id in artifacts
        ]
        if role == "native_evidence" and not any(
            artifact.get("artifact_role") in {"native_trace", "process_log"}
            for artifact in source_artifacts
        ):
            report.error(
                "native_representation_source_missing",
                "native-evidence representation must directly cite retained native/process bytes",
                row_type="representation",
                row_id=row_id,
            )
        value_artifact = artifacts.get(str(row.get("value_artifact_id")))
        if (
            value_artifact is not None
            and expected_artifact_roles is not None
            and value_artifact.get("artifact_role") not in expected_artifact_roles
        ):
            report.error(
                "representation_value_artifact_role_mismatch",
                "value artifact role is incompatible with the representation role",
                row_type="representation",
                row_id=row_id,
            )
        if value_artifact is not None and role != "context":
            artifact_subjects = _reference_values(value_artifact, "subject_node_ids")
            row_subject = row.get("subject_node_id")
            subject_linked = any(
                artifact_subject == row_subject
                or row_subject in physical_descendants.get(artifact_subject, set())
                for artifact_subject in artifact_subjects
            )
            if (
                row.get("attempt_id")
                not in _reference_values(value_artifact, "attempt_ids")
                or not subject_linked
            ):
                report.error(
                    "representation_value_artifact_scope_mismatch",
                    "value artifact must be linked to the attempt and subject lineage",
                    row_type="representation",
                    row_id=row_id,
                )
        workflow_artifact = artifacts.get(str(row.get("actual_workflow_artifact_id")))
        workflow_role_expectation = {
            "native_evidence": {"native_trace", "process_log"},
            "conventional_report": {"conventional_report"},
            "label_or_grade": {"label_or_grade"},
        }.get(str(role))
        if (
            workflow_artifact is not None
            and workflow_role_expectation is not None
            and workflow_artifact.get("artifact_role") not in workflow_role_expectation
        ):
            report.error(
                "actual_workflow_artifact_role_mismatch",
                "per-attempt workflow artifact role is incompatible with its representation",
                row_type="representation",
                row_id=row_id,
            )
    for attempt_id in attempts:
        for spec_id in specs:
            if (attempt_id, spec_id) not in representation_pairs:
                report.error(
                    "required_representation_row_missing",
                    "attempt lacks an explicit available or unavailable representation row",
                    attempt_id=attempt_id,
                    representation_spec_id=spec_id,
                )

    outcome_spec = study.get("delayed_outcome")
    if isinstance(outcome_spec, dict):
        assay_method_id = outcome_spec.get("assay_method_artifact_id")
        assay_method = artifacts.get(str(assay_method_id))
        if assay_method is None:
            report.error(
                "study_artifact_reference_missing",
                "delayed-outcome assay method artifact is absent",
                target_id=assay_method_id,
            )
        if outcome_spec.get("failure_aware") is not True:
            report.error(
                "delayed_outcome_not_failure_aware",
                "primary delayed outcome must preserve early failure or censoring information",
            )
        unit_graph = study.get("unit_graph")
        if isinstance(unit_graph, dict) and outcome_spec.get(
            "physical_subject_type"
        ) != unit_graph.get("outcome_subject_type"):
            report.error(
                "outcome_subject_contract_mismatch",
                "delayed outcome subject type differs from the declared physical-unit graph",
            )
        outcome_subject_type = outcome_spec.get("physical_subject_type")
        for row in rows_by_type.get("representation", []):
            subject = nodes.get(str(row.get("subject_node_id")))
            if subject is not None and subject.get("node_type") != outcome_subject_type:
                report.error(
                    "representation_subject_type_mismatch",
                    "representation must be indexed to the declared outcome subject type",
                    row_type="representation",
                    row_id=_row_identity(row),
                )
        subject_ids = {
            node_id
            for node_id, node in nodes.items()
            if node.get("node_type") == outcome_subject_type
        }
        outcomes_by_subject: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        permitted_statuses = set(
            outcome_spec.get("censoring", {}).get("permitted_statuses", [])
            if isinstance(outcome_spec.get("censoring"), dict)
            else []
        )
        for row in rows_by_type.get("outcome", []):
            row_id = _row_identity(row)
            subject_id = row.get("subject_node_id")
            if isinstance(subject_id, str):
                outcomes_by_subject[subject_id].append(row)
            field_matches = {
                "outcome_spec_id": outcome_spec.get("outcome_spec_id"),
                "outcome_spec_version": outcome_spec.get("outcome_spec_version"),
                "target_name": outcome_spec.get("primary_target_name"),
                "target_type": outcome_spec.get("target_type"),
                "target_unit": outcome_spec.get("target_unit"),
                "outcome_horizon": outcome_spec.get("outcome_horizon"),
                "independent_of_early_report": outcome_spec.get(
                    "independent_of_early_report"
                ),
            }
            for field_name, expected_value in field_matches.items():
                if row.get(field_name) != expected_value:
                    report.error(
                        "outcome_spec_value_mismatch",
                        f"{field_name} differs from delayed-outcome contract",
                        row_type="outcome",
                        row_id=row_id,
                        field=field_name,
                    )
            if row.get("status") not in permitted_statuses:
                report.error(
                    "outcome_status_not_permitted",
                    f"outcome status {row.get('status')!r} is not permitted by the study",
                    row_type="outcome",
                    row_id=row_id,
                )
            required_source_roles = set(outcome_spec.get("source_artifact_roles", []))
            observed_source_roles = {
                artifacts[artifact_id].get("artifact_role")
                for artifact_id in _reference_values(row, "source_artifact_ids")
                if artifact_id in artifacts
            }
            if not required_source_roles.issubset(observed_source_roles):
                report.error(
                    "outcome_source_artifact_role_missing",
                    "outcome does not carry every frozen evidence/product artifact role",
                    row_type="outcome",
                    row_id=row_id,
                    missing_roles=sorted(required_source_roles - observed_source_roles),
                )
            assay_environment = row.get("assay_environment")
            missing_environment_fields = [
                field_name
                for field_name in outcome_spec.get("measured_environment_fields", [])
                if not isinstance(assay_environment, dict)
                or assay_environment.get(field_name) is None
            ]
            if missing_environment_fields:
                report.error(
                    "outcome_environment_field_missing",
                    "outcome assay environment omits a frozen measured field",
                    row_type="outcome",
                    row_id=row_id,
                    field_names=missing_environment_fields,
                )
            followup_policy = outcome_spec.get("selective_followup_policy")
            if followup_policy == "all_eligible" and row.get("eligible") is True and row.get(
                "followup_status"
            ) == "not_selected":
                report.error(
                    "all_eligible_followup_violated",
                    "all-eligible policy cannot omit an eligible subject from follow-up",
                    row_type="outcome",
                    row_id=row_id,
                )
            if followup_policy == "probability_sample_known_inclusion" and row.get(
                "eligible"
            ) is True:
                payload = row.get("domain_payload")
                probability = (
                    payload.get("followup_inclusion_probability")
                    if isinstance(payload, dict)
                    else None
                )
                if (
                    not isinstance(probability, (int, float))
                    or isinstance(probability, bool)
                    or not 0 < float(probability) <= 1
                ):
                    report.error(
                        "followup_inclusion_probability_missing",
                        "probability-sampled follow-up requires a positive known inclusion probability",
                        row_type="outcome",
                        row_id=row_id,
                    )
        missing_outcome_subjects: list[str] = []
        duplicate_outcome_subjects: list[str] = []
        for subject_id in sorted(subject_ids):
            count = len(outcomes_by_subject.get(subject_id, []))
            if count == 0:
                missing_outcome_subjects.append(subject_id)
            elif count > 1:
                duplicate_outcome_subjects.append(subject_id)
                report.error(
                    "duplicate_primary_outcome_subject",
                    f"outcome subject has {count} primary outcome rows",
                    row_id=subject_id,
                )
        for subject_id in sorted(set(outcomes_by_subject).difference(subject_ids)):
            report.error(
                "outcome_subject_type_mismatch",
                "outcome is attached to a node of the wrong declared subject type",
                row_id=subject_id,
            )
        report.check(
            "outcome_subject_coverage",
            not missing_outcome_subjects and not duplicate_outcome_subjects,
            details={
                "declared_subjects": len(subject_ids),
                "covered_subjects": len(subject_ids) - len(missing_outcome_subjects),
                "missing_subject_ids": missing_outcome_subjects[:20],
                "duplicate_subject_ids": duplicate_outcome_subjects[:20],
            },
        )

    unit_graph = study.get("unit_graph")
    if isinstance(unit_graph, dict):
        allowed_node_types = set(unit_graph.get("node_types", []))
        allowed_relations = set(unit_graph.get("edge_relations", []))
        for row in rows_by_type.get("physical_node", []):
            if row.get("node_type") not in allowed_node_types:
                report.error(
                    "undeclared_physical_node_type",
                    f"node_type {row.get('node_type')!r} is absent from the study graph",
                    row_type="physical_node",
                    row_id=_row_identity(row),
                )
        for row in rows_by_type.get("physical_edge", []):
            if row.get("relation") not in allowed_relations:
                report.error(
                    "undeclared_physical_edge_relation",
                    f"relation {row.get('relation')!r} is absent from the study graph",
                    row_type="physical_edge",
                    row_id=_row_identity(row),
                )

    environment_design = study.get("environment_design")
    external_validation = (
        environment_design.get("external_validation")
        if isinstance(environment_design, dict)
        else None
    )
    if isinstance(external_validation, dict) and external_validation.get("mode") != "none":
        site_artifact_id = external_validation.get("site_set_artifact_id")
        site_artifact = artifacts.get(str(site_artifact_id))
        if site_artifact is None or site_artifact.get("sha256") != external_validation.get(
            "site_set_sha256"
        ):
            report.error(
                "external_site_set_hash_mismatch",
                "external site-set ID/hash must match an artifact ledger row",
                target_id=site_artifact_id,
            )
        mode = external_validation.get("mode")
        if mode == "zero_shot" and (
            external_validation.get("calibration_unit_count") != 0
            or external_validation.get("model_retraining_allowed") is not False
            or external_validation.get("same_report_schema_required") is not True
            or external_validation.get("same_transformation_graph_required") is not True
        ):
            report.error(
                "external_validation_mode_inconsistent",
                "zero-shot validation forbids calibration/retraining and requires the same reporting pipeline",
            )
        if mode == "site_calibration_then_frozen_test" and (
            external_validation.get("calibration_unit_count", 0) < 1
            or external_validation.get("model_retraining_allowed") is not False
        ):
            report.error(
                "external_validation_mode_inconsistent",
                "site-calibration mode requires calibration units and forbids model retraining",
            )

    decision_contract = study.get("decision")
    if isinstance(decision_contract, dict):
        artifact_id = decision_contract.get("current_decision_rule_artifact_id")
        if artifact_id not in artifacts:
            report.error(
                "study_artifact_reference_missing",
                "current decision-rule artifact is absent",
                target_id=artifact_id,
            )
        allowed_actions = set(decision_contract.get("allowed_actions", []))
        for row in rows_by_type.get("decision", []):
            if set(row.get("allowed_actions", [])) != allowed_actions:
                report.error(
                    "decision_contract_mismatch",
                    "decision row allowed_actions differ from the study contract",
                    row_type="decision",
                    row_id=_row_identity(row),
                )
            if row.get("decision_deadline") != decision_contract.get("decision_deadline"):
                report.error(
                    "decision_contract_mismatch",
                    "decision row deadline differs from the study contract",
                    row_type="decision",
                    row_id=_row_identity(row),
                )
        if any(
            row.get("action_can_affect_outcome") is True
            for row in rows_by_type.get("decision", [])
        ):
            payload = decision_contract.get("domain_payload")
            estimand = (
                payload.get("post_cutoff_action_estimand")
                if isinstance(payload, dict)
                else None
            )
            if estimand not in {
                "existing_policy",
                "fixed_post_cutoff_protocol",
                "pre_action_reference_outcome",
                "causal_policy_with_logged_propensities",
            }:
                report.error(
                    "outcome_action_estimand_missing",
                    "outcome-affecting actions require a frozen post-cutoff action estimand",
                )
            elif estimand == "causal_policy_with_logged_propensities":
                missing_propensities = [
                    _row_identity(row)
                    for row in rows_by_type.get("decision", [])
                    if row.get("action_can_affect_outcome") is True
                    and (
                        not isinstance(row.get("action_propensity"), (int, float))
                        or isinstance(row.get("action_propensity"), bool)
                        or float(row.get("action_propensity")) <= 0
                    )
                ]
                if missing_propensities:
                    report.error(
                        "causal_action_propensity_missing",
                        "causal-policy estimand requires a positive logged action propensity",
                        decision_ids=missing_propensities,
                    )

    report.counts["representation_specs"] = len(specs)
    report.counts["analysis_arms"] = len(arms)
    report.check(
        "study_contract_semantics",
        not any(
            error["code"]
            in {
                "duplicate_representation_spec_id",
                "missing_representation_spec_parent",
                "representation_spec_cycle",
                "required_representation_role_missing",
                "duplicate_arm_id",
                "arm_representation_spec_missing",
                "duplicate_comparison_id",
                "comparison_arm_missing",
                "comparison_arms_identical",
                "required_analysis_arm_missing",
                "required_representation_spec_not_in_arm",
                "primary_arm_missing",
                "primary_comparison_missing",
                "representation_spec_missing",
                "duplicate_attempt_representation_spec",
                "required_representation_row_missing",
                "representation_spec_value_mismatch",
                "feature_schema_mismatch",
                "undeclared_availability_reason",
                "attempt_representation_subject_mismatch",
                "representation_parent_scope_mismatch",
                "representation_parent_spec_mismatch",
                "representation_transformation_missing",
                "available_representation_value_missing",
                "actual_workflow_instance_missing",
                "representation_value_artifact_role_mismatch",
                "representation_value_artifact_scope_mismatch",
                "native_representation_source_missing",
                "actual_workflow_artifact_role_mismatch",
                "outcome_spec_value_mismatch",
                "outcome_status_not_permitted",
                "outcome_source_artifact_role_missing",
                "outcome_environment_field_missing",
                "all_eligible_followup_violated",
                "followup_inclusion_probability_missing",
                "delayed_outcome_not_failure_aware",
                "outcome_subject_contract_mismatch",
                "representation_subject_type_mismatch",
                "duplicate_primary_outcome_subject",
                "outcome_subject_type_mismatch",
                "undeclared_physical_node_type",
                "undeclared_physical_edge_relation",
                "external_site_set_hash_mismatch",
                "external_validation_mode_inconsistent",
                "study_artifact_reference_missing",
                "decision_contract_mismatch",
                "outcome_action_estimand_missing",
                "causal_action_propensity_missing",
            }
            for error in report.blocking_errors
        ),
    )


def _validate_denominators(
    root: Path,
    bundle: Mapping[str, Any],
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]],
    indexes: Mapping[str, Mapping[str, dict[str, Any]]],
    report: _Report,
) -> None:
    declared = bundle.get("source_denominator_counts")
    if not isinstance(declared, dict):
        return
    assignments = list(rows_by_type.get("assignment", []))
    attempts = list(rows_by_type.get("attempt", []))
    outcomes = list(rows_by_type.get("outcome", []))
    assignment_status = Counter(row.get("status") for row in assignments)
    execution_status = Counter(row.get("execution_status") for row in attempts)
    eligible_subjects = {
        str(row.get("subject_node_id")) for row in outcomes if row.get("eligible") is True
    }
    followed_subjects = {
        str(row.get("subject_node_id"))
        for row in outcomes
        if row.get("eligible") is True
        and row.get("followup_status") not in {"not_selected", "unknown"}
        and row.get("status") != "not_followed"
    }
    observed = {
        "source_population_count": len(assignments),
        # These are cumulative denominator counts: every assignment was planned;
        # every attempt was initiated. The remaining fields partition later states.
        "planned_assignments": len(assignments),
        "released_assignments": assignment_status["released"],
        "not_started_assignments": assignment_status["not_started"],
        "cancelled_assignments": assignment_status["cancelled"],
        "initiated_attempts": len(attempts),
        "completed_attempts": execution_status["success"],
        "failed_attempts": execution_status["failure"],
        "ambiguous_attempts": execution_status["ambiguous"],
        "aborted_attempts": execution_status["aborted"],
        "unknown_attempts": execution_status["unknown"],
        "retries": sum(row.get("retry_of_attempt_id") is not None for row in attempts),
        "reworks": sum(row.get("rework_of_attempt_id") is not None for row in attempts),
        "eligible_followup_units": len(eligible_subjects),
        "followed_units": len(followed_subjects),
        "right_censored_units": len(
            {
                str(row.get("subject_node_id"))
                for row in outcomes
                if row.get("status") == "right_censored"
            }
        ),
        "missing_outcome_units": len(
            {
                str(row.get("subject_node_id"))
                for row in outcomes
                if row.get("status") in {"missing", "not_followed", "unresolved"}
            }
        ),
    }
    mismatches: dict[str, dict[str, Any]] = {}
    for field_name, observed_value in observed.items():
        if declared.get(field_name) != observed_value:
            mismatches[field_name] = {
                "declared": declared.get(field_name),
                "observed": observed_value,
            }
    if mismatches:
        report.error(
            "source_denominator_mismatch",
            "source denominator counts do not reconcile with ledger rows",
            mismatches=mismatches,
        )
    source_artifact_id = declared.get("source_ledger_artifact_id")
    source_artifact = indexes["artifact"].get(str(source_artifact_id))
    if source_artifact is None:
        report.error(
            "source_denominator_artifact_missing",
            "source denominator artifact is absent from the artifact ledger",
            target_id=source_artifact_id,
        )
    elif source_artifact.get("sha256") != declared.get("source_ledger_sha256"):
        report.error(
            "source_denominator_hash_mismatch",
            "source denominator SHA-256 differs from its artifact ledger row",
            target_id=source_artifact_id,
        )
    snapshot_matches = False
    if source_artifact is not None:
        location = source_artifact.get("location")
        if not isinstance(location, dict) or location.get("status") != "available_bundle_file":
            report.error(
                "source_denominator_snapshot_unavailable",
                "independent source denominator must be delivered as a hash-verified bundle file",
                target_id=source_artifact_id,
            )
        else:
            try:
                snapshot_path = _safe_bundle_path(root, location.get("path"))
                snapshot = load_strict_json(snapshot_path)
            except (OSError, StrictJSONError, ValueError) as exc:
                report.error(
                    "source_denominator_snapshot_invalid",
                    str(exc),
                    target_id=source_artifact_id,
                )
            else:
                snapshot_mapping = snapshot if isinstance(snapshot, dict) else {}
                comparable_fields = {
                    key: value
                    for key, value in declared.items()
                    if key not in {"source_ledger_artifact_id", "source_ledger_sha256"}
                }
                mismatched_snapshot_fields = {
                    key: {"declared": expected, "snapshot": snapshot_mapping.get(key)}
                    for key, expected in comparable_fields.items()
                    if snapshot_mapping.get(key) != expected
                }
                if snapshot_mapping.get("schema_version") != (
                    "partner_source_denominator.v1"
                ):
                    mismatched_snapshot_fields["schema_version"] = {
                        "declared": "partner_source_denominator.v1",
                        "snapshot": snapshot_mapping.get("schema_version"),
                    }
                if mismatched_snapshot_fields:
                    report.error(
                        "source_denominator_snapshot_mismatch",
                        "independent source snapshot does not match declared denominators",
                        mismatches=mismatched_snapshot_fields,
                    )
                else:
                    snapshot_matches = True
    report.counts["ledger_denominators"] = observed
    report.check(
        "source_denominators_reconcile",
        not mismatches
        and source_artifact is not None
        and source_artifact.get("sha256") == declared.get("source_ledger_sha256")
        and snapshot_matches,
        details={"mismatches": mismatches},
    )


def _validate_governance_semantics(
    study: Mapping[str, Any],
    bundle: Mapping[str, Any],
    tables: Sequence[_LoadedTable],
    indexes: Mapping[str, Mapping[str, dict[str, Any]]],
    report: _Report,
) -> None:
    firewall = study.get("firewall_and_freeze")
    artifacts = indexes["artifact"]
    if not isinstance(firewall, dict):
        return

    access_artifact_id = firewall.get("access_control_matrix_artifact_id")
    if access_artifact_id not in artifacts:
        report.error(
            "governance_artifact_missing",
            "access-control matrix artifact is absent",
            target_id=access_artifact_id,
        )
    representation_roles = set(firewall.get("representation_builder_roles", []))
    outcome_roles = set(firewall.get("outcome_builder_roles", []))
    outcome_access_roles = set(firewall.get("outcome_table_access_roles", []))
    if representation_roles.intersection(outcome_roles | outcome_access_roles):
        report.error(
            "firewall_role_overlap",
            "representation builders cannot also build or access confirmatory outcomes",
            overlapping_roles=sorted(
                representation_roles.intersection(outcome_roles | outcome_access_roles)
            ),
        )

    assignment_table = next(
        (table for table in tables if table.descriptor.get("table_id") == "assignments"),
        None,
    )
    assignment_sha256 = firewall.get("assignment_sha256")
    if assignment_sha256 is not None and (
        assignment_table is None or _sha256_file(assignment_table.path) != assignment_sha256
    ):
        report.error(
            "frozen_assignment_hash_mismatch",
            "firewall assignment_sha256 differs from the delivered assignment ledger",
        )

    first_outcome_access = _parse_timestamp(firewall.get("first_outcome_access_at"))
    lock_names = (
        "design_lock",
        "analysis_freeze",
        "raw_freeze",
        "representation_freeze",
    )
    locked_records: list[dict[str, Any]] = []
    for lock_name in lock_names:
        lock = firewall.get(lock_name)
        if not isinstance(lock, dict) or lock.get("status") != "locked":
            continue
        locked_records.append(lock)
        artifact_id = lock.get("manifest_artifact_id")
        artifact = artifacts.get(str(artifact_id))
        if artifact is None or artifact.get("sha256") != lock.get("manifest_sha256"):
            report.error(
                "freeze_manifest_hash_mismatch",
                f"{lock_name} manifest ID/hash does not match an artifact ledger row",
                target_id=artifact_id,
            )
        locked_at = _parse_timestamp(lock.get("locked_at"))
        if (
            first_outcome_access is not None
            and locked_at is not None
            and locked_at >= first_outcome_access
        ):
            report.error(
                "freeze_after_outcome_access",
                f"{lock_name} must lock strictly before first outcome access",
            )

    detached_study_hash = firewall.get("study_spec_sha256")
    design_lock = firewall.get("design_lock")
    design_manifest_hash = (
        design_lock.get("manifest_sha256") if isinstance(design_lock, dict) else None
    )
    if locked_records and (
        detached_study_hash is None or detached_study_hash != design_manifest_hash
    ):
        report.error(
            "detached_study_hash_mismatch",
            "study_spec_sha256 must identify the detached design-lock manifest, not self-hash this JSON",
        )

    signoffs = study.get("signoffs")
    if isinstance(signoffs, dict):
        signoff_values = [
            value
            for key, value in signoffs.items()
            if key != "additional_signoffs" and isinstance(value, dict)
        ]
        additional = signoffs.get("additional_signoffs")
        if isinstance(additional, list):
            signoff_values.extend(value for value in additional if isinstance(value, dict))
        for signoff in signoff_values:
            if signoff.get("status") == "signed" and signoff.get(
                "signed_spec_sha256"
            ) != detached_study_hash:
                report.error(
                    "signoff_study_hash_mismatch",
                    "signed owner hash differs from the detached frozen study specification",
                    signatory_id=signoff.get("signatory_id"),
                )

    for release in (study.get("release"), bundle.get("release_status")):
        if not isinstance(release, dict):
            continue
        artifact_id = release.get("release_artifact_id")
        release_hash = release.get("release_sha256")
        if artifact_id is None and release_hash is None:
            continue
        artifact = artifacts.get(str(artifact_id))
        if artifact is None or artifact.get("sha256") != release_hash:
            report.error(
                "release_artifact_hash_mismatch",
                "release artifact ID/hash does not match the artifact ledger",
                target_id=artifact_id,
            )

    governance_codes = {
        "governance_artifact_missing",
        "firewall_role_overlap",
        "frozen_assignment_hash_mismatch",
        "freeze_manifest_hash_mismatch",
        "freeze_after_outcome_access",
        "detached_study_hash_mismatch",
        "signoff_study_hash_mismatch",
        "release_artifact_hash_mismatch",
    }
    report.check(
        "governance_hashes_and_access",
        not any(error["code"] in governance_codes for error in report.blocking_errors),
        details={"locked_freezes": len(locked_records)},
    )


def _canonical_condition(value: object) -> str:
    return json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))


def _validate_bridge_crossing(
    study: Mapping[str, Any],
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]],
    indexes: Mapping[str, Mapping[str, dict[str, Any]]],
    report: _Report,
    *, blocking: bool,
) -> bool:
    design = study.get("environment_design")
    if not isinstance(design, dict):
        return False
    axis = design.get("primary_held_out_axis")
    coverage = design.get("bridge_coverage")
    if not isinstance(axis, str) or not isinstance(coverage, dict):
        return False
    assignments = indexes["assignment"]
    attempts = list(rows_by_type.get("attempt", []))
    explicitly_bridge: list[dict[str, Any]] = []
    for row in attempts:
        assignment = assignments.get(str(row.get("assignment_id")))
        if assignment is None:
            continue
        payload = assignment.get("domain_payload")
        condition = assignment.get("planned_condition")
        if (
            (isinstance(payload, dict) and payload.get("stream") == "bridge")
            or (
                isinstance(condition, dict)
                and condition.get("bridge_panel") is True
            )
        ):
            explicitly_bridge.append(row)
    bridge_attempts = explicitly_bridge or attempts
    if not explicitly_bridge and attempts:
        emit = report.error if blocking else report.warning
        emit(
            "bridge_membership_implicit",
            "no frozen bridge marker found; crossing check uses every attempt",
        )
    condition_environments: defaultdict[str, set[str]] = defaultdict(set)
    environment_conditions: defaultdict[str, set[str]] = defaultdict(set)
    parent_ids: set[str] = set()
    attempts_with_environment = 0
    nodes_by_attempt: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in rows_by_type.get("physical_node", []):
        for attempt_id in _reference_values(node, "source_attempt_ids"):
            nodes_by_attempt[attempt_id].append(node)
    for attempt in bridge_attempts:
        assignment = assignments.get(str(attempt.get("assignment_id")))
        if assignment is None:
            continue
        provenance = attempt.get("provenance")
        actual_environment = provenance.get(axis) if isinstance(provenance, dict) else None
        planned_environment = assignment.get("planned_environment")
        environment = actual_environment
        if environment is None and not blocking and isinstance(planned_environment, dict):
            environment = planned_environment.get(axis)
        if environment is None:
            continue
        attempts_with_environment += 1
        environment_text = str(environment)
        condition = _canonical_condition(assignment.get("planned_condition"))
        condition_environments[condition].add(environment_text)
        environment_conditions[environment_text].add(condition)
        for node in nodes_by_attempt.get(str(attempt.get("attempt_id")), []):
            parent_id = node.get("independent_parent_id")
            if isinstance(parent_id, str):
                parent_ids.add(parent_id)
    minimum_levels = int(coverage.get("minimum_primary_environment_levels", 2))
    minimum_conditions = int(coverage.get("minimum_conditions_per_environment", 1))
    minimum_units = int(coverage.get("minimum_independent_units", 1))
    failures: list[str] = []
    crossed_design = design.get("crossed_environment_design")
    primary_axes = (
        [
            entry
            for entry in crossed_design.get("axes", [])
            if isinstance(entry, dict) and entry.get("axis_name") == axis
        ]
        if isinstance(crossed_design, dict)
        else []
    )
    if blocking and (
        not isinstance(crossed_design, dict)
        or crossed_design.get("conditions_cross_primary_environment") is not True
        or crossed_design.get("crossed_not_nested") is not True
        or len(primary_axes) != 1
        or primary_axes[0].get("held_out") is not True
        or primary_axes[0].get("crossed_with_condition") is not True
    ):
        failures.append("frozen_crossed_design")
    if blocking and not explicitly_bridge:
        failures.append("explicit_bridge_membership")
    if blocking and attempts_with_environment < len(bridge_attempts):
        failures.append("actual_environment_complete")
    if len(environment_conditions) < minimum_levels:
        failures.append("primary_environment_levels")
    if len(parent_ids) < minimum_units:
        failures.append("independent_units")
    if any(len(conditions) < minimum_conditions for conditions in environment_conditions.values()):
        failures.append("conditions_per_environment")
    observed_environments = set(environment_conditions)
    full_crossing_required = isinstance(crossed_design, dict) and (
        crossed_design.get("crossed_not_nested") is True
        or coverage.get("conditions_repeated_across_primary_environments") is True
    )
    if condition_environments and any(
        len(environments) < minimum_levels
        or (full_crossing_required and environments != observed_environments)
        for environments in condition_environments.values()
    ):
        failures.append("condition_crossing")
    passed = not failures
    if failures:
        emit = report.error if blocking and coverage.get("coverage_failure_blocks_claim") else report.warning
        emit(
            "bridge_crossing_insufficient",
            "observed bridge panel does not meet frozen crossing requirements",
            failed_requirements=failures,
        )
    report.counts["bridge"] = {
        "attempts": len(bridge_attempts),
        "explicit_membership": bool(explicitly_bridge),
        "environment_levels": len(environment_conditions),
        "conditions": len(condition_environments),
        "independent_units": len(parent_ids),
    }
    report.check(
        "bridge_crossing",
        passed,
        details={"failed_requirements": failures},
    )
    return passed


def _validate_nonconfirmatory_scope(
    bundle: Mapping[str, Any],
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]],
    indexes: Mapping[str, Mapping[str, dict[str, Any]]],
    report: _Report,
) -> None:
    scope = bundle.get("nonconfirmatory_scope")
    if not isinstance(scope, dict):
        return
    fields = {
        "assignment_ids": "assignment",
        "attempt_ids": "attempt",
        "physical_node_ids": "physical_node",
        "artifact_ids": "artifact",
    }
    for field_name, row_type in fields.items():
        for row_id in _reference_values(scope, field_name):
            row = indexes[row_type].get(row_id)
            if row is None:
                report.error(
                    "nonconfirmatory_scope_reference_missing",
                    f"{field_name} cites absent {row_type} {row_id!r}",
                    target_id=row_id,
                )
            elif row.get("nonconfirmatory") is not True:
                report.error(
                    "nonconfirmatory_scope_flag_mismatch",
                    "scope-listed record must carry nonconfirmatory=true",
                    row_type=row_type,
                    row_id=row_id,
                )
    if bundle.get("purpose") in {"golden_bundle_nonconfirmatory", "pilot_nonconfirmatory"}:
        for row_type in (
            "assignment",
            "attempt",
            "physical_node",
            "physical_edge",
            "artifact",
            "transformation",
            "representation",
            "outcome",
            "cost",
            "decision",
            "correction",
        ):
            for row in rows_by_type.get(row_type, []):
                if row.get("nonconfirmatory") is not True:
                    report.error(
                        "nonconfirmatory_bundle_contains_confirmatory_row",
                        "golden/pilot bundle row must be permanently nonconfirmatory",
                        row_type=row_type,
                        row_id=_row_identity(row),
                    )
    report.check(
        "nonconfirmatory_scope_consistent",
        not any(
            error["code"]
            in {
                "nonconfirmatory_scope_reference_missing",
                "nonconfirmatory_scope_flag_mismatch",
                "nonconfirmatory_bundle_contains_confirmatory_row",
            }
            for error in report.blocking_errors
        ),
    )


def _readiness_requirements(
    level: str,
    study: Mapping[str, Any],
    bundle: Mapping[str, Any],
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]],
    bridge_passed: bool,
) -> dict[str, bool]:
    confirmatory = level not in {"golden", "pilot"}

    def in_scope(row: Mapping[str, Any]) -> bool:
        return not confirmatory or row.get("nonconfirmatory") is False

    attempts = [row for row in rows_by_type.get("attempt", []) if in_scope(row)]
    outcomes = [row for row in rows_by_type.get("outcome", []) if in_scope(row)]
    artifacts = [row for row in rows_by_type.get("artifact", []) if in_scope(row)]
    representations = [
        row for row in rows_by_type.get("representation", []) if in_scope(row)
    ]
    decisions = [row for row in rows_by_type.get("decision", []) if in_scope(row)]
    costs = [row for row in rows_by_type.get("cost", []) if in_scope(row)]
    allowed_locations = (
        {"available_bundle_file"}
        if level == "golden"
        else {"available_bundle_file", "available_external"}
    )
    available_roles = {
        row.get("artifact_role")
        for row in artifacts
        if isinstance(row.get("location"), dict)
        and row["location"].get("status") in allowed_locations
    }
    has_negative = any(
        row.get("execution_status") in {"failure", "ambiguous", "aborted"}
        or row.get("retry_of_attempt_id") is not None
        or row.get("rework_of_attempt_id") is not None
        for row in attempts
    ) or any(
        row.get("status")
        in {
            "right_censored",
            "left_censored",
            "interval_censored",
            "missing",
            "not_followed",
        }
        for row in outcomes
    )
    data_requirements = {
        "ordinary_attempt_present": any(
            row.get("execution_status") == "success" for row in attempts
        ),
        "native_evidence_present": "native_trace" in available_roles,
        "actual_report_present": "conventional_report" in available_roles,
        "outcome_evidence_present": bool(
            {"outcome_evidence", "outcome_product"}.intersection(available_roles)
        ),
        "representation_rows_present": bool(representations),
        "outcome_rows_present": bool(outcomes),
        "decision_rows_present": bool(decisions),
        "cost_rows_present": bool(costs),
    }
    if level == "golden":
        data_requirements.update(
            {
                "negative_or_censored_attempt_present": has_negative,
                "purpose_matches": bundle.get("purpose") == "golden_bundle_nonconfirmatory",
                "bundle_inference_status_matches": bundle.get("inference_status")
                == "nonconfirmatory",
                "study_inference_status_matches": study.get("inference_status")
                == "golden_bundle_nonconfirmatory",
            }
        )
        return data_requirements
    if level == "pilot":
        data_requirements.update(
            {
                "purpose_matches": bundle.get("purpose") == "pilot_nonconfirmatory",
                "bundle_inference_status_matches": bundle.get("inference_status")
                == "nonconfirmatory",
                "study_inference_status_matches": study.get("inference_status")
                == "pilot_nonconfirmatory",
                "multiple_independent_units": len(
                    {
                        row.get("independent_parent_id")
                        for row in rows_by_type.get("physical_node", [])
                        if row.get("independent_parent_id") is not None
                    }
                )
                >= 2,
            }
        )
        return data_requirements
    firewall = study.get("firewall_and_freeze")
    locks = (
        [
            firewall.get(name)
            for name in (
                "design_lock",
                "analysis_freeze",
                "raw_freeze",
                "representation_freeze",
            )
        ]
        if isinstance(firewall, dict)
        else []
    )
    signoffs = study.get("signoffs")
    named_signoffs = (
        [
            signoffs.get(name)
            for name in (
                "scientific_owner",
                "practitioner_action_owner",
                "outcome_assay_owner",
                "data_lineage_owner",
            )
        ]
        if isinstance(signoffs, dict)
        else []
    )
    rights = bundle.get("rights")
    environment_design = study.get("environment_design")
    external_validation = (
        environment_design.get("external_validation")
        if isinstance(environment_design, dict)
        else None
    )
    delayed_outcome = study.get("delayed_outcome")
    artifact_policy = study.get("artifact_policy")
    study_release = study.get("release")
    bundle_release = bundle.get("release_status")
    crossed_design = (
        environment_design.get("crossed_environment_design")
        if isinstance(environment_design, dict)
        else None
    )
    primary_axis = (
        environment_design.get("primary_held_out_axis")
        if isinstance(environment_design, dict)
        else None
    )
    axis_entries = (
        [
            entry
            for entry in crossed_design.get("axes", [])
            if isinstance(entry, dict) and entry.get("axis_name") == primary_axis
        ]
        if isinstance(crossed_design, dict)
        else []
    )
    assignments = [row for row in rows_by_type.get("assignment", []) if in_scope(row)]
    streams = {
        row.get("domain_payload", {}).get("stream")
        for row in assignments
        if isinstance(row.get("domain_payload"), dict)
    }
    report_spec_ids = {
        spec.get("representation_spec_id")
        for spec in study.get("representations", [])
        if isinstance(spec, dict) and spec.get("role") == "conventional_report"
    }
    native_spec_ids = {
        spec.get("representation_spec_id")
        for spec in study.get("representations", [])
        if isinstance(spec, dict) and spec.get("role") == "native_evidence"
    }
    available_specs_by_attempt: defaultdict[str, set[object]] = defaultdict(set)
    for row in representations:
        if row.get("primary_analysis_available") is True:
            available_specs_by_attempt[str(row.get("attempt_id"))].add(
                row.get("representation_spec_id")
            )
    matched_native_report_attempt = any(
        native_spec_ids.intersection(spec_ids) and report_spec_ids.intersection(spec_ids)
        for spec_ids in available_specs_by_attempt.values()
    )
    bridge_assignment_ids = {
        str(row.get("assignment_id"))
        for row in assignments
        if isinstance(row.get("domain_payload"), dict)
        and row["domain_payload"].get("stream") == "bridge"
    }
    bridge_attempts = [
        row for row in attempts if row.get("assignment_id") in bridge_assignment_ids
    ]
    decisions_by_attempt = {
        str(row.get("attempt_id")): row for row in decisions
    }
    outcomes_by_attempt = {
        attempt_id
        for row in outcomes
        for attempt_id in _reference_values(row, "source_attempt_ids")
    }
    bridge_input_chains_complete = bool(bridge_attempts) and all(
        row.get("attempt_state") == "completed"
        and report_spec_ids.intersection(
            available_specs_by_attempt.get(str(row.get("attempt_id")), set())
        )
        and decisions_by_attempt.get(str(row.get("attempt_id")), {}).get(
            "actual_report_available"
        )
        is True
        for row in bridge_attempts
    )
    bridge_outcome_chains_complete = bridge_input_chains_complete and all(
        str(row.get("attempt_id")) in outcomes_by_attempt for row in bridge_attempts
    )
    corrections_clear = not any(
        row.get("status") in {"proposed", "approved", "invalidates_analysis"}
        or (
            isinstance(row.get("impact"), dict)
            and (
                row["impact"].get("analysis") == "invalidated"
                or row["impact"].get("claim")
                in {"requires_refreeze", "downgraded", "withdrawn"}
            )
        )
        for row in rows_by_type.get("correction", [])
    )
    start = {
        "purpose_matches": bundle.get("purpose") == "confirmatory_collection",
        "bundle_inference_status_matches": bundle.get("inference_status")
        in {"firewalled_preanalysis", "preregistered_confirmatory"},
        "study_inference_status_matches": study.get("inference_status")
        == "preregistered_confirmatory",
        "assignments_registered": bool(assignments),
        "native_and_bridge_streams_registered": {"native", "bridge"}.issubset(streams),
        "all_freezes_locked": len(locks) == 4
        and all(isinstance(lock, dict) and lock.get("status") == "locked" for lock in locks),
        "all_owner_signoffs_signed": len(named_signoffs) == 4
        and all(
            isinstance(signoff, dict) and signoff.get("status") == "signed"
            for signoff in named_signoffs
        ),
        "frozen_assignment_hash_present": isinstance(
            firewall.get("assignment_sha256") if isinstance(firewall, dict) else None,
            str,
        ),
        "detached_study_hash_present": isinstance(
            firewall.get("study_spec_sha256") if isinstance(firewall, dict) else None,
            str,
        ),
        "rights_allow_science": isinstance(rights, dict)
        and rights.get("raw_upstream_accessible") is True
        and rights.get("study_use_permitted") is True
        and rights.get("publication_permitted") is True
        and (
            rights.get("minimum_release") != "aggregate_audit_outputs"
            or rights.get("independent_verifier_access") is True
        ),
        "release_path_usable": isinstance(study_release, dict)
        and study_release.get("raw_data_usable_for_study") is True
        and study_release.get("publishable_outputs") is True
        and isinstance(bundle_release, dict)
        and bundle_release.get("status") != "blocked",
        "native_retention_required": isinstance(artifact_policy, dict)
        and artifact_policy.get("native_artifact_retention_required") is True,
        "crossed_design_frozen": isinstance(crossed_design, dict)
        and crossed_design.get("conditions_cross_primary_environment") is True
        and crossed_design.get("crossed_not_nested") is True
        and len(axis_entries) == 1
        and axis_entries[0].get("held_out") is True
        and axis_entries[0].get("crossed_with_condition") is True,
        "external_validation_reserved": isinstance(external_validation, dict)
        and external_validation.get("mode") != "none"
        and external_validation.get("frozen_test_unit_count", 0) > 0
        and external_validation.get("site_set_artifact_id") is not None
        and external_validation.get("site_set_sha256") is not None,
        "failure_aware_outcome": isinstance(delayed_outcome, dict)
        and delayed_outcome.get("failure_aware") is True,
        "corrections_clear": corrections_clear,
    }
    if level == "confirmatory_start":
        return start

    input_close = {
        **start,
        "attempt_rows_present": bool(attempts),
        "representation_rows_present": bool(representations),
        "decision_rows_present": bool(decisions),
        "cost_rows_present": bool(costs),
        "native_evidence_present": "native_trace" in available_roles,
        "actual_report_present": "conventional_report" in available_roles,
        "matched_native_report_attempt_present": matched_native_report_attempt,
        "bridge_membership_frozen": bool(bridge_assignment_ids),
        "bridge_crossing_passed": bridge_passed,
        "bridge_input_chains_complete": bridge_input_chains_complete,
        "representation_builders_blinded": bool(representations)
        and all(row.get("builder_blinding_attestation") is True for row in representations),
    }
    if level == "input_close":
        return input_close

    outcome_reveal = {
        **input_close,
        "outcome_rows_present": bool(outcomes),
        "outcome_evidence_present": bool(
            {"outcome_evidence", "outcome_product"}.intersection(available_roles)
        ),
        "bridge_outcome_chains_complete": bridge_outcome_chains_complete,
        "outcome_independence_attested": bool(outcomes)
        and all(
            row.get("independent_of_early_report") is True
            and row.get("builder_blinding_attestation") is True
            for row in outcomes
        ),
    }
    if level == "outcome_reveal":
        return outcome_reveal

    if level == "external_validation":
        return {
            **outcome_reveal,
            "purpose_matches": bundle.get("purpose") == "external_validation",
            "bundle_inference_status_matches": bundle.get("inference_status")
            == "external_frozen_test",
            "study_inference_status_matches": study.get("inference_status")
            in {"preregistered_confirmatory", "closed"},
            "external_test_partition_present": any(
                row.get("partition") == "external_test"
                and row.get("nonconfirmatory") is False
                for row in rows_by_type.get("physical_node", [])
            ),
        }
    return {
        **outcome_reveal,
        "purpose_matches": bundle.get("purpose") == "analysis_release",
        "bundle_inference_status_matches": bundle.get("inference_status")
        == "analysis_complete",
        "study_inference_status_matches": study.get("inference_status") == "closed",
        "release_approved": isinstance(bundle_release, dict)
        and bundle_release.get("status")
        in {"aggregate_only", "deidentified_bundle", "public"}
        and bundle_release.get("publishable_outputs") is True,
    }


def _validate_readiness(
    requested: str,
    study: Mapping[str, Any],
    bundle: Mapping[str, Any],
    rows_by_type: Mapping[str, Sequence[dict[str, Any]]],
    bridge_passed: bool,
    report: _Report,
) -> None:
    core_validation_passed = not report.blocking_errors
    for level in READINESS_LEVELS:
        requirements = _readiness_requirements(
            level, study, bundle, rows_by_type, bridge_passed
        )
        if level in {"golden", "pilot", "outcome_reveal", "external_validation", "release"}:
            requirements["outcome_subject_coverage"] = bool(
                report.checks.get("outcome_subject_coverage", {}).get("passed")
            )
            requirements["unit_freeze_fully_verifiable"] = bool(
                report.checks.get(
                    "unit_level_freeze_precedes_outcome_access", {}
                ).get("passed")
            )
        if level not in {"golden", "pilot"}:
            requirements["governance_hashes_verified"] = bool(
                report.checks.get("governance_hashes_and_access", {}).get("passed")
            )
        requirements["core_validation_passed"] = core_validation_passed
        report.readiness[level] = {
            "ready": all(requirements.values()),
            "requirements": requirements,
        }
    requested_result = report.readiness[requested]
    if not requested_result["ready"]:
        failed = sorted(
            name
            for name, passed in requested_result["requirements"].items()
            if not passed
        )
        report.error(
            "readiness_gate_failed",
            f"bundle does not satisfy requested {requested} readiness",
            failed_requirements=failed,
        )
    report.check(
        f"{requested}_readiness",
        bool(requested_result["ready"]),
        details={
            "failed_requirements": sorted(
                name
                for name, passed in requested_result["requirements"].items()
                if not passed
            )
        },
    )


def _find_bundle_index(path: Path) -> tuple[Path, Path]:
    if path.is_file():
        root = path.parent.resolve()
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            raise ValueError("bundle index symlink escapes its bundle directory")
        return root, resolved
    if not path.is_dir():
        raise FileNotFoundError(f"bundle path does not exist: {path}")
    root = path.resolve()
    matches: list[Path] = []
    for candidate in sorted(root.glob("*.json")):
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root):
            raise ValueError(f"bundle index candidate escapes root: {candidate.name}")
        try:
            value = load_strict_json(resolved)
        except (OSError, StrictJSONError):
            continue
        if isinstance(value, dict) and value.get("schema_version") == "partner_bundle.v1":
            matches.append(resolved)
    if len(matches) != 1:
        raise FileNotFoundError(
            f"bundle directory must contain exactly one partner_bundle.v1 JSON index; found {len(matches)}"
        )
    return root, matches[0]


def _infer_readiness(bundle: Mapping[str, Any]) -> str:
    purpose = bundle.get("purpose")
    if purpose == "golden_bundle_nonconfirmatory":
        return "golden"
    if purpose == "pilot_nonconfirmatory":
        return "pilot"
    if purpose == "external_validation":
        return "external_validation"
    if purpose == "analysis_release":
        return "release"
    return "confirmatory_start"


def validate_partner_bundle(
    bundle_path: str | Path,
    *,
    schema_dir: str | Path | None = None,
    readiness: str | None = None,
) -> dict[str, Any]:
    """Validate one bundle index and every declared file without modifying it.

    ``bundle_path`` may name the bundle-index JSON file or a directory containing
    exactly one ``partner_bundle.v1`` index. ``readiness`` is one of ``golden``,
    ``pilot``, ``confirmatory_start``, ``input_close``, ``outcome_reveal``,
    ``external_validation``, or ``release``; when omitted it is inferred from bundle
    purpose. The legacy value ``confirmatory`` aliases ``outcome_reveal``.
    """
    report = _Report()
    schema_root = (
        Path(schema_dir).resolve()
        if schema_dir is not None
        else Path(__file__).resolve().parents[3] / "schemas"
    )
    try:
        root, index_path = _find_bundle_index(Path(bundle_path))
    except (OSError, StrictJSONError, ValueError) as exc:
        report.error("bundle_index_unreadable", str(exc), path=str(bundle_path))
        return report.finish(requested_readiness=readiness)
    try:
        bundle_value = load_strict_json(index_path)
    except (OSError, StrictJSONError) as exc:
        report.error("bundle_index_invalid_json", str(exc), path=str(index_path))
        return report.finish(requested_readiness=readiness)
    if not isinstance(bundle_value, dict):
        report.error("bundle_index_not_object", "bundle index must be a JSON object")
        return report.finish(requested_readiness=readiness)
    bundle = bundle_value
    report.hashes["bundle_index"] = {
        "path": str(index_path.relative_to(root)),
        "sha256": _sha256_file(index_path),
        "bytes": index_path.stat().st_size,
    }

    schemas = _load_schema_set(schema_root, report)
    if len(schemas) != len(SCHEMA_FILENAMES):
        return report.finish(requested_readiness=readiness)
    registry = _schema_registry(schemas)
    bundle_validator = Draft202012Validator(
        schemas["bundle"], registry=registry, format_checker=FormatChecker()
    )
    bundle_schema_errors = _schema_errors(bundle_validator, bundle)
    for message in bundle_schema_errors:
        report.error("bundle_schema_invalid", message, path=str(index_path))
    report.check("bundle_matches_schema", not bundle_schema_errors)
    if bundle_schema_errors:
        return report.finish(requested_readiness=readiness)

    requested = readiness or _infer_readiness(bundle)
    if requested == "confirmatory":
        requested = "outcome_reveal"
    if requested not in READINESS_LEVELS:
        report.error(
            "invalid_readiness",
            f"readiness must be one of {', '.join(READINESS_LEVELS)}; "
            f"received {requested!r}",
        )
        return report.finish(requested_readiness=requested)

    study_descriptor = bundle.get("study_spec")
    if not isinstance(study_descriptor, dict):
        report.error("study_descriptor_missing", "bundle lacks a usable study_spec descriptor")
        return report.finish(requested_readiness=requested)
    try:
        study_path = _safe_bundle_path(root, study_descriptor.get("path"))
    except ValueError as exc:
        report.error("unsafe_study_path", str(exc))
        return report.finish(requested_readiness=requested)
    if not study_path.is_file():
        report.error("study_file_missing", f"study specification does not exist: {study_path}")
        return report.finish(requested_readiness=requested)
    observed_study_hash = _sha256_file(study_path)
    observed_study_bytes = study_path.stat().st_size
    report.hashes["study_spec"] = {
        "path": str(study_descriptor.get("path")),
        "sha256": observed_study_hash,
        "bytes": observed_study_bytes,
    }
    if study_descriptor.get("sha256") != observed_study_hash:
        report.error("study_hash_mismatch", "study descriptor SHA-256 does not match file")
    if study_descriptor.get("bytes") != observed_study_bytes:
        report.error(
            "study_bytes_mismatch",
            f"declared bytes={study_descriptor.get('bytes')!r}, observed={observed_study_bytes}",
        )
    expected_schema_hash = report.hashes.get(f"schema:{SCHEMA_FILENAMES['study']}")
    if study_descriptor.get("schema_sha256") != expected_schema_hash:
        report.error(
            "study_schema_hash_mismatch",
            "study descriptor schema_sha256 does not match the validator's study schema",
        )
    try:
        study_value = load_strict_json(study_path)
    except (OSError, StrictJSONError) as exc:
        report.error("study_json_invalid", str(exc), path=str(study_path))
        return report.finish(requested_readiness=requested)
    if not isinstance(study_value, dict):
        report.error("study_not_object", "study specification must be a JSON object")
        return report.finish(requested_readiness=requested)
    study = study_value
    study_validator = Draft202012Validator(
        schemas["study"], registry=registry, format_checker=FormatChecker()
    )
    study_schema_errors = _schema_errors(study_validator, study)
    for message in study_schema_errors:
        report.error("study_schema_invalid", message, path=str(study_path))
    report.check("study_matches_schema", not study_schema_errors)
    if study_schema_errors:
        return report.finish(requested_readiness=requested)

    tables = _load_tables(root, bundle, schema_root, schemas, registry, report)
    rows_by_type, indexes = _index_rows(tables, report)
    _validate_study_identity(study, bundle, rows_by_type, report)
    _validate_references(rows_by_type, indexes, report)
    _validate_attempt_state_machine(rows_by_type, indexes, report)
    _validate_dags(rows_by_type, indexes, report)
    _validate_events(tables, indexes, report)
    _validate_artifact_files(root, rows_by_type, report)
    _validate_representation_semantics(rows_by_type, report)
    _validate_outcome_semantics(rows_by_type, report)
    _validate_partition_isolation(rows_by_type, report)
    _validate_unit_freeze_order(rows_by_type, report)
    _validate_decisions_and_corrections(rows_by_type, indexes, report)
    _validate_study_contract(study, rows_by_type, indexes, report)
    _validate_governance_semantics(study, bundle, tables, indexes, report)
    _validate_denominators(root, bundle, rows_by_type, indexes, report)
    _validate_nonconfirmatory_scope(bundle, rows_by_type, indexes, report)
    bridge_passed = _validate_bridge_crossing(
        study,
        rows_by_type,
        indexes,
        report,
        blocking=requested
        in {"pilot", "input_close", "outcome_reveal", "external_validation", "release"},
    )
    _validate_readiness(requested, study, bundle, rows_by_type, bridge_passed, report)
    report.counts["blocking_errors"] = len(report.blocking_errors)
    report.counts["warnings"] = len(report.warnings)
    result = report.finish(requested_readiness=requested)
    _assert_finite(result, source="validation report")
    return result
