"""Run the retrospective Severson downstream-compression engineering audit.

This runner executes two complete nested held-batch fits: the primary analysis excludes
targets whose end of life was learned from a later collection-batch continuation, while the
all-observed-EOL sensitivity includes them.  It then sends both prediction bundles through the
generic support-aware compression evaluator.  The result is deliberately nonconfirmatory; see
``docs/controlled-collection/severson_downstream_compression_dry_run.md``.

Input: ``data/interim/event_grammar_v1/severson_battery/events.json``.
Output: ``data/manifests/severson_downstream_compression_audit.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from materials_event_modeling.eval.compression_audit import (
    PredictionArm,
    absolute_error,
    audit_prediction_bundle,
    mean_risk,
)
from materials_event_modeling.eval.severson_downstream import (
    ARM_NAMES,
    RIDGE_ALPHAS,
    S100_NAMES,
    X100_CYCLES,
    DownstreamRow,
    HeldBatchOOFResult,
    held_batch_oof,
    load_downstream_rows,
    policy_macro_weights,
    summarize_x100,
)
from materials_event_modeling.run_identity import run_identity

EVENTS_REL = Path("data/interim/event_grammar_v1/severson_battery/events.json")
OUTPUT_REL = Path("data/manifests/severson_downstream_compression_audit.json")
DESIGN_REL = Path("docs/controlled-collection/severson_downstream_compression_dry_run.md")

EXPECTED_ATTEMPTS = 135
EXPECTED_EXACT_TARGETS = 128
EXPECTED_PRIMARY_TARGETS = 123
EXPECTED_CENSORED = 7
EXPECTED_CROSS_BATCH_TARGETS = 5
EXPECTED_BATCHES = ("2017-05-12", "2017-06-30", "2018-04-12")
EXPECTED_ATTEMPTS_BY_BATCH = {
    "2017-05-12": 46,
    "2017-06-30": 43,
    "2018-04-12": 46,
}
EXPECTED_ALL_EOL_BY_BATCH = {
    "2017-05-12": 41,
    "2017-06-30": 43,
    "2018-04-12": 44,
}
EXPECTED_PRIMARY_BY_BATCH = {
    "2017-05-12": 36,
    "2017-06-30": 43,
    "2018-04-12": 44,
}

COMPARISONS = (
    ("C", "C_S100"),
    ("C", "C_X100"),
    ("C_S100", "C_S100_X100"),
    ("C_X100", "C_S100_X100"),
    ("C_S100", "C_X100"),
)

ARM_DEFINITIONS = {
    "C": {
        "parents": [],
        "contents": "three planned charge-policy scalars",
    },
    "C_S100": {
        "parents": ["C", "S100"],
        "contents": "context plus seven deterministic summaries of X100",
    },
    "C_X100": {
        "parents": ["C", "X100"],
        "contents": "context plus QDischarge at cycles 2 through 100",
    },
    "C_S100_X100": {
        "parents": ["C", "S100", "X100"],
        "contents": "context plus the deterministic summary and its source trajectory",
    },
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root().resolve()))
    except ValueError:
        return str(path)


def _json_safe(value: Any) -> Any:
    """Convert numerical containers to strict JSON, replacing non-finite scalars with null."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (float, np.floating)):
        numeric = float(value)
        return numeric if np.isfinite(numeric) else None
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    raise TypeError(f"unsupported manifest value: {type(value).__name__}")


def _exact_targets(rows: list[DownstreamRow]) -> np.ndarray:
    return np.array([row.target_exact for row in rows], dtype=bool)


def _primary_targets(rows: list[DownstreamRow]) -> np.ndarray:
    return np.array(
        [row.target_exact and not row.cross_batch_target_provenance for row in rows],
        dtype=bool,
    )


def _targets(rows: list[DownstreamRow]) -> np.ndarray:
    return np.array(
        [row.log_cycle_life if row.log_cycle_life is not None else np.nan for row in rows],
        dtype=float,
    )


def _labels(rows: list[DownstreamRow], attribute: str) -> np.ndarray:
    return np.array([getattr(row, attribute) for row in rows], dtype=object)


def _validate_real_dataset(
    rows: list[DownstreamRow],
    primary_eligible: np.ndarray,
    all_eol_eligible: np.ndarray,
) -> dict[str, Any]:
    batches = _labels(rows, "batch")
    censored_rows = [row for row in rows if row.target_status == "right_censored"]
    censored_lower_bounds = np.array(
        [
            row.life_lower_bound if row.life_lower_bound is not None else np.nan
            for row in censored_rows
        ],
        dtype=float,
    )
    if (
        censored_lower_bounds.shape != (EXPECTED_CENSORED,)
        or not np.all(np.isfinite(censored_lower_bounds))
        or np.any(censored_lower_bounds <= 0.0)
    ):
        raise AssertionError("right-censored rows must have finite positive lifetime lower bounds")
    counts = {
        "attempts": len(rows),
        "exact_scalar_targets": int(all_eol_eligible.sum()),
        "primary_targets": int(primary_eligible.sum()),
        "right_censored": sum(row.target_status == "right_censored" for row in rows),
        "cross_batch_target_provenance": sum(
            row.cross_batch_target_provenance for row in rows
        ),
        "batches": len(set(batches.tolist())),
        "attempts_by_batch": {
            batch: int(np.sum(batches == batch)) for batch in sorted(set(batches.tolist()))
        },
        "all_eol_by_batch": {
            batch: int(np.sum((batches == batch) & all_eol_eligible))
            for batch in sorted(set(batches.tolist()))
        },
        "primary_by_batch": {
            batch: int(np.sum((batches == batch) & primary_eligible))
            for batch in sorted(set(batches.tolist()))
        },
        "attempts_with_interpolation": sum(bool(row.interpolated_cycles) for row in rows),
        "interpolated_grid_points": sum(len(row.interpolated_cycles) for row in rows),
    }
    expected = {
        "attempts": EXPECTED_ATTEMPTS,
        "exact_scalar_targets": EXPECTED_EXACT_TARGETS,
        "primary_targets": EXPECTED_PRIMARY_TARGETS,
        "right_censored": EXPECTED_CENSORED,
        "cross_batch_target_provenance": EXPECTED_CROSS_BATCH_TARGETS,
        "batches": len(EXPECTED_BATCHES),
        "attempts_by_batch": EXPECTED_ATTEMPTS_BY_BATCH,
        "all_eol_by_batch": EXPECTED_ALL_EOL_BY_BATCH,
        "primary_by_batch": EXPECTED_PRIMARY_BY_BATCH,
        "attempts_with_interpolation": 16,
        "interpolated_grid_points": 16,
    }
    if counts != expected:
        raise AssertionError(f"Severson invariant-count mismatch: observed={counts}, expected={expected}")
    return {
        "observed": counts,
        "expected": expected,
        "censored_lower_bound_validation": {
            "count": int(censored_lower_bounds.size),
            "all_finite_positive": True,
            "minimum_cycles": float(np.min(censored_lower_bounds)),
            "maximum_cycles": float(np.max(censored_lower_bounds)),
        },
        "passed": True,
    }


def _validate_fit(
    rows: list[DownstreamRow],
    result: HeldBatchOOFResult,
    expected_eligible: np.ndarray,
) -> None:
    if not np.array_equal(result.analysis_eligible, expected_eligible):
        raise AssertionError("held_batch_oof changed the declared analysis universe")
    if len(result.folds) != len(EXPECTED_BATCHES):
        raise AssertionError("held_batch_oof did not emit exactly three outer folds")
    held_batches = tuple(fold["held_batch"] for fold in result.folds)
    if held_batches != EXPECTED_BATCHES:
        raise AssertionError(f"unexpected outer-fold order: {held_batches}")
    for fold in result.folds:
        if fold["event_overlap_count"] or fold["policy_overlap_count"]:
            raise AssertionError("an outer fold shares events or charge policies")
        for arm in ARM_NAMES:
            arm_metadata = fold["arms"][arm]
            if arm_metadata["predicted_attempt_count"] != fold["test_attempt_count"]:
                raise AssertionError(f"arm {arm} did not predict every available test attempt")
    for arm in ARM_NAMES:
        if not np.all(result.features.available[arm]):
            raise AssertionError(f"the frozen real-data run unexpectedly lacks arm {arm}")
        predictions = result.predictions[arm]
        if predictions.shape != (len(rows),) or not np.all(np.isfinite(predictions)):
            raise AssertionError(f"arm {arm} lacks one finite held-batch prediction per attempt")


def _prediction_arms(result: HeldBatchOOFResult) -> dict[str, PredictionArm]:
    return {
        name: PredictionArm(
            name=name,
            predictions=result.predictions[name],
            available=result.features.available[name],
            metadata={
                "cross_fitting": "leave_one_complete_batch_out",
                "inner_selection": "GroupKFold_by_charge_policy_policy_macro_MAE",
                "feature_width": int(result.features.matrices[name].shape[1]),
            },
        )
        for name in ARM_NAMES
    }


def _audit_bundle(
    rows: list[DownstreamRow],
    result: HeldBatchOOFResult,
    *,
    weighting: str,
) -> dict[str, Any]:
    eligible = result.analysis_eligible
    if weighting == "policy_macro":
        weights = policy_macro_weights(rows, eligible)
    elif weighting == "cell_micro":
        weights = np.ones(len(rows), dtype=float)
    else:
        raise ValueError(f"unknown weighting: {weighting}")
    return audit_prediction_bundle(
        _targets(rows),
        _prediction_arms(result),
        list(COMPARISONS),
        loss=absolute_error,
        metric_name="mae_log10_cycles",
        risk_tolerance=0.0,
        clusters=_labels(rows, "policy"),
        aggregate=mean_risk,
        event_support_tolerance=0.0,
        weighted_event_support_tolerance=0.0,
        universe=eligible,
        sample_weights=weights,
        event_importance_weights=weights,
        environments=_labels(rows, "batch"),
        transfer_rule="all_environments",
        environment_evaluation="held_out_environment",
        seed=0,
        n_boot=2000,
    )


def _weighted_mae(errors: np.ndarray, weights: np.ndarray) -> float | None:
    total = float(np.sum(weights))
    return float(np.sum(errors * weights) / total) if total > 0.0 else None


def _per_batch_risks(
    rows: list[DownstreamRow], result: HeldBatchOOFResult
) -> dict[str, Any]:
    targets = _targets(rows)
    batches = _labels(rows, "batch")
    policies = _labels(rows, "policy")
    output: dict[str, Any] = {}
    for batch in sorted(set(batches.tolist())):
        universe = result.analysis_eligible & (batches == batch)
        policy_weights = policy_macro_weights(rows, universe)
        arms: dict[str, Any] = {}
        for name in ARM_NAMES:
            mask = universe & result.features.available[name]
            errors = np.zeros(len(rows), dtype=float)
            errors[mask] = np.abs(result.predictions[name][mask] - targets[mask])
            arms[name] = {
                "eligible_count": int(mask.sum()),
                "policy_macro_mae_log10_cycles": _weighted_mae(
                    errors[mask], policy_weights[mask]
                ),
                "cell_micro_mae_log10_cycles": (
                    float(np.mean(errors[mask])) if mask.any() else None
                ),
            }
        comparisons: dict[str, Any] = {}
        for compressed, reference in COMPARISONS:
            key = f"{compressed}__to__{reference}"
            comparisons[key] = {
                "positive_means_reference_lower_risk": True,
                "policy_macro_gap": (
                    arms[compressed]["policy_macro_mae_log10_cycles"]
                    - arms[reference]["policy_macro_mae_log10_cycles"]
                ),
                "cell_micro_gap": (
                    arms[compressed]["cell_micro_mae_log10_cycles"]
                    - arms[reference]["cell_micro_mae_log10_cycles"]
                ),
            }
        output[batch] = {
            "target_count": int(universe.sum()),
            "policy_count": len(set(policies[universe].tolist())),
            "arms": arms,
            "comparisons": comparisons,
        }
    return output


def _pooled_arm_risks(
    rows: list[DownstreamRow], result: HeldBatchOOFResult
) -> dict[str, dict[str, float | int | None]]:
    targets = _targets(rows)
    policy_weights = policy_macro_weights(rows, result.analysis_eligible)
    output: dict[str, dict[str, float | int | None]] = {}
    for arm in ARM_NAMES:
        mask = result.analysis_eligible & result.features.available[arm]
        errors = np.abs(result.predictions[arm][mask] - targets[mask])
        output[arm] = {
            "eligible_count": int(mask.sum()),
            "policy_macro_mae_log10_cycles": _weighted_mae(
                errors, policy_weights[mask]
            ),
            "cell_micro_mae_log10_cycles": (
                float(np.mean(errors)) if errors.size else None
            ),
        }
    return output


def _direct_ordering(gap: float) -> str:
    if gap > 0.0:
        return "C_X100_lower_policy_macro_MAE_than_C_S100"
    if gap < 0.0:
        return "C_S100_lower_policy_macro_MAE_than_C_X100"
    return "C_S100_and_C_X100_tied"


def _structured_result_verdict(
    primary: dict[str, dict[str, float | int | None]],
    sensitivity: dict[str, dict[str, float | int | None]],
) -> dict[str, Any]:
    primary_s = primary["C_S100"]["policy_macro_mae_log10_cycles"]
    primary_x = primary["C_X100"]["policy_macro_mae_log10_cycles"]
    sensitivity_s = sensitivity["C_S100"]["policy_macro_mae_log10_cycles"]
    sensitivity_x = sensitivity["C_X100"]["policy_macro_mae_log10_cycles"]
    if None in (primary_s, primary_x, sensitivity_s, sensitivity_x):
        raise AssertionError("the real-data pooled S100/X100 risks must be estimable")
    assert primary_s is not None
    assert primary_x is not None
    assert sensitivity_s is not None
    assert sensitivity_x is not None
    primary_gap = float(primary_s) - float(primary_x)
    sensitivity_gap = float(sensitivity_s) - float(sensitivity_x)
    reversal = bool(primary_gap * sensitivity_gap < 0.0)

    def best_arm(risks: dict[str, dict[str, float | int | None]]) -> str:
        values: dict[str, float] = {}
        for arm, arm_risks in risks.items():
            value = arm_risks["policy_macro_mae_log10_cycles"]
            if value is None:
                raise AssertionError("all real-data arm risks must be estimable")
            values[arm] = float(value)
        return min(values, key=values.__getitem__)

    return {
        "metric": "pooled_policy_macro_MAE_log10_cycles",
        "positive_direct_gap_means": "C_X100 has lower risk than C_S100",
        "primary_C_S100_minus_C_X100_gap": primary_gap,
        "primary_direct_ordering": _direct_ordering(primary_gap),
        "all_eol_contaminated_sensitivity_C_S100_minus_C_X100_gap": sensitivity_gap,
        "all_eol_contaminated_sensitivity_direct_ordering": _direct_ordering(
            sensitivity_gap
        ),
        "direct_ordering_reverses_when_contaminated_targets_are_included": reversal,
        "primary_best_arm_by_pooled_policy_macro_MAE": best_arm(primary),
        "all_eol_contaminated_sensitivity_best_arm_by_pooled_policy_macro_MAE": best_arm(
            sensitivity
        ),
        "descriptive_verdict": (
            "S100-versus-X100 ordering is continuation-sensitive and therefore unstable."
            if reversal
            else "No continuation-driven S100-versus-X100 ordering reversal was observed."
        ),
        "inference_status": "retrospective_posthoc_nonconfirmatory",
        "scientific_claim_allowed": False,
    }


def _worst_cells(
    rows: list[DownstreamRow], result: HeldBatchOOFResult, *, limit: int = 5
) -> dict[str, list[dict[str, Any]]]:
    targets = _targets(rows)
    output: dict[str, list[dict[str, Any]]] = {}
    for arm in ARM_NAMES:
        mask = result.analysis_eligible & result.features.available[arm]
        indices = np.flatnonzero(mask)
        errors = np.abs(result.predictions[arm][indices] - targets[indices])
        order = indices[np.argsort(-errors, kind="stable")[:limit]]
        output[arm] = []
        for index in order:
            row = rows[int(index)]
            prediction = float(result.predictions[arm][index])
            target_log = row.log_cycle_life
            if target_log is None:
                raise AssertionError("worst-cell universe contains a row without an exact target")
            output[arm].append(
                {
                    "event_id": row.event_id,
                    "batch": row.batch,
                    "policy": row.policy,
                    "target_log10_cycles": row.log_cycle_life,
                    "target_cycles": row.cycle_life,
                    "prediction_log10_cycles": prediction,
                    "prediction_cycles": float(10.0**prediction),
                    "absolute_error_log10_cycles": float(
                        abs(prediction - target_log)
                    ),
                    "signed_error_log10_cycles": float(
                        prediction - target_log
                    ),
                    "capacity_cycle_100_ah": float(row.x100[-1]),
                    "interpolated_cycles": list(row.interpolated_cycles),
                    "rejected_early_observation_count": row.rejected_cycle_count,
                    "cross_batch_target_provenance": row.cross_batch_target_provenance,
                    "continuation_batches": list(row.continuation_batches),
                }
            )
    return output


def _prediction_plausibility(
    rows: list[DownstreamRow], result: HeldBatchOOFResult
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    survival_floor = float(X100_CYCLES[-1] + 1)
    for arm in ARM_NAMES:
        predictions = result.predictions[arm]
        predicted_cycles = np.power(10.0, predictions)
        available = result.features.available[arm]
        below = np.flatnonzero(available & (predicted_cycles < survival_floor))
        output[arm] = {
            "representation_available_oof_prediction_count": int(available.sum()),
            "analysis_eligible_prediction_count": int(
                np.sum(available & result.analysis_eligible)
            ),
            "minimum_prediction_log10_cycles": float(
                np.min(predictions[available])
            ),
            "maximum_prediction_log10_cycles": float(
                np.max(predictions[available])
            ),
            "minimum_prediction_cycles": float(
                np.min(predicted_cycles[available])
            ),
            "maximum_prediction_cycles": float(
                np.max(predicted_cycles[available])
            ),
            "known_survival_floor_cycles": int(survival_floor),
            "prediction_below_known_survival_floor_count": int(below.size),
            "prediction_below_known_survival_floor_event_ids": [
                rows[int(index)].event_id for index in below
            ],
            "note": (
                "Predictions below 101 cycles violate the known survival bound but are "
                "retained as diagnostics from the frozen unconstrained ridge learner."
            ),
        }
    return output


def _representation_diagnostics(rows: list[DownstreamRow]) -> dict[str, Any]:
    available_rows = [row for row in rows if row.x100_available]
    x100 = np.vstack([row.x100 for row in available_rows])
    s100 = np.vstack([row.s100 for row in available_rows])
    reconstructed = np.vstack([summarize_x100(row.x100) for row in available_rows])
    target_cycles = np.array(
        [row.cycle_life for row in rows if row.target_exact], dtype=float
    )
    summary_ranges = {
        name: {
            "minimum": float(np.min(s100[:, index])),
            "maximum": float(np.max(s100[:, index])),
        }
        for index, name in enumerate(S100_NAMES)
    }
    return {
        "x100_cycle_grid": [int(value) for value in X100_CYCLES],
        "x100_width": int(X100_CYCLES.size),
        "x100_available_count": len(available_rows),
        "x100_minimum_qdischarge_ah": float(np.min(x100)),
        "x100_maximum_qdischarge_ah": float(np.max(x100)),
        "s100_names": list(S100_NAMES),
        "s100_ranges": summary_ranges,
        "s100_reconstruction_max_abs_error": float(np.max(np.abs(s100 - reconstructed))),
        "attempts_with_interpolation": sum(bool(row.interpolated_cycles) for row in rows),
        "interpolated_grid_points": sum(len(row.interpolated_cycles) for row in rows),
        "interpolated_cycle_histogram": {
            str(cycle): sum(cycle in row.interpolated_cycles for row in rows)
            for cycle in sorted({cycle for row in rows for cycle in row.interpolated_cycles})
        },
        "rejected_early_observation_count": sum(row.rejected_cycle_count for row in rows),
        "observed_eol_target_cycles_range": [
            float(np.min(target_cycles)),
            float(np.max(target_cycles)),
        ],
        "known_survival_floor_cycles": int(X100_CYCLES[-1]) + 1,
    }


def _exclusion_reason(row: DownstreamRow, *, primary: bool) -> str:
    if not row.target_exact:
        return row.target_status
    if primary and row.cross_batch_target_provenance:
        return "excluded_cross_batch_target_provenance"
    if not primary and row.cross_batch_target_provenance:
        return "included_contaminated_cross_batch_target_provenance"
    return "included"


def _row_losses(
    row_index: int,
    row: DownstreamRow,
    result: HeldBatchOOFResult,
) -> dict[str, float | None]:
    if not result.analysis_eligible[row_index] or row.log_cycle_life is None:
        return dict.fromkeys(ARM_NAMES)
    return {
        arm: (
            float(abs(result.predictions[arm][row_index] - row.log_cycle_life))
            if result.features.available[arm][row_index]
            else None
        )
        for arm in ARM_NAMES
    }


def _row_ledger(
    rows: list[DownstreamRow],
    primary: HeldBatchOOFResult,
    all_eol: HeldBatchOOFResult,
) -> list[dict[str, Any]]:
    ledger: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        arm_support = {
            arm: {
                "available": bool(primary.features.available[arm][index]),
                "reason": primary.features.reasons[arm][index],
            }
            for arm in ARM_NAMES
        }
        ledger.append(
            {
                "row_index": index,
                "event_id": row.event_id,
                "batch": row.batch,
                "policy": row.policy,
                "target_status": row.target_status,
                "target_exact": row.target_exact,
                "target_cycles": row.cycle_life,
                "target_log10_cycles": row.log_cycle_life,
                "target_lower_bound_cycles": row.life_lower_bound,
                "continuation_batches": list(row.continuation_batches),
                "cross_batch_target_provenance": row.cross_batch_target_provenance,
                "primary_analysis_status": _exclusion_reason(row, primary=True),
                "all_eol_sensitivity_status": _exclusion_reason(row, primary=False),
                "context_available": row.context_available,
                "context_reason": row.context_reason,
                "x100_available": row.x100_available,
                "x100_reason": row.x100_reason,
                "accepted_early_cycle_count": row.accepted_cycle_count,
                "rejected_early_cycle_count": row.rejected_cycle_count,
                "interpolated_cycles": list(row.interpolated_cycles),
                "observed_mask_bits_cycles_2_100": "".join(
                    "1" if value else "0" for value in row.observed_mask
                ),
                "arm_support": arm_support,
                "primary_oof_predictions_log10_cycles": {
                    arm: float(primary.predictions[arm][index]) for arm in ARM_NAMES
                },
                "primary_absolute_error_log10_cycles": _row_losses(
                    index, row, primary
                ),
                "all_eol_sensitivity_oof_predictions_log10_cycles": {
                    arm: float(all_eol.predictions[arm][index]) for arm in ARM_NAMES
                },
                "all_eol_sensitivity_absolute_error_log10_cycles": _row_losses(
                    index, row, all_eol
                ),
            }
        )
    return ledger


def _analysis_report(
    rows: list[DownstreamRow], result: HeldBatchOOFResult, *, label: str
) -> dict[str, Any]:
    included_cross_batch_targets = sum(
        result.analysis_eligible[index] and row.cross_batch_target_provenance
        for index, row in enumerate(rows)
    )
    return {
        "label": label,
        "analysis_eligible_count": int(result.analysis_eligible.sum()),
        "included_cross_batch_target_provenance_count": int(
            included_cross_batch_targets
        ),
        "target_provenance_status": (
            "contaminated_by_cross_batch_continuation_targets"
            if included_cross_batch_targets
            else "cross_batch_continuation_targets_excluded"
        ),
        "fit_metadata": result.metadata,
        "folds": list(result.folds),
        "pooled_arm_risks": _pooled_arm_risks(rows, result),
        "policy_macro_audit": _audit_bundle(rows, result, weighting="policy_macro"),
        "cell_micro_audit": _audit_bundle(rows, result, weighting="cell_micro"),
        "per_batch_risks": _per_batch_risks(rows, result),
        "prediction_physical_plausibility": _prediction_plausibility(rows, result),
        "worst_cells_by_arm": _worst_cells(rows, result),
    }


def build_report(events_path: Path) -> dict[str, Any]:
    rows = load_downstream_rows(events_path)
    all_eol_eligible = _exact_targets(rows)
    primary_eligible = _primary_targets(rows)
    invariant_counts = _validate_real_dataset(rows, primary_eligible, all_eol_eligible)

    primary = held_batch_oof(rows, primary_eligible, alphas=RIDGE_ALPHAS)
    all_eol = held_batch_oof(rows, all_eol_eligible, alphas=RIDGE_ALPHAS)
    _validate_fit(rows, primary, primary_eligible)
    _validate_fit(rows, all_eol, all_eol_eligible)
    primary_report = _analysis_report(
        rows,
        primary,
        label="primary_excludes_five_later_batch_continuation_targets",
    )
    sensitivity_report = _analysis_report(
        rows,
        all_eol,
        label=(
            "contaminated_sensitivity_includes_five_cross_batch_target_provenance_rows"
        ),
    )

    return {
        "task": "severson_downstream_compression_audit",
        "design_document": str(DESIGN_REL),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "inference_status": "retrospective_posthoc_nonconfirmatory",
        "core_verdict_not_for_scientific_inference": True,
        "explicit_verdict": (
            "Engineering dry run only: the support-aware downstream audit path completed on "
            "the frozen public dataset. No arm ordering is confirmatory, no zero-tolerance "
            "evaluator token is a scientific verdict, and no result establishes an industry "
            "report, native-raw advantage, or transfer to future batches."
        ),
        "prohibited_claims": [
            "raw data are universally better",
            "S100 is an actual practitioner report",
            "X100 is native within-cycle electrochemistry",
            "a zero-tolerance core token proves sufficiency or premature compression",
            "three confounded collection batches establish future-batch transfer",
            "cycle life is an independent downstream functional assay",
        ],
        "source": {
            "path": _manifest_path(events_path),
            "sha256": _sha256_file(events_path),
            "bytes": events_path.stat().st_size,
        },
        "frozen_design": {
            "attempt_unit": "physical_cell_event",
            "state_cutoff_cycle": int(X100_CYCLES[-1]),
            "target": "log10(cell.cycle_life_cycles)",
            "environment": "provenance.batch_id",
            "uncertainty_cluster": "intent.event_group_id_charge_policy",
            "primary_loss": "policy_macro_MAE_log10_cycles",
            "outer_split": "leave_one_complete_batch_out",
            "learner": "StandardScaler_then_Ridge",
            "ridge_alpha_grid": list(RIDGE_ALPHAS),
            "arm_names": list(ARM_NAMES),
            "arm_definitions": ARM_DEFINITIONS,
            "s100_names": list(S100_NAMES),
            "comparisons": [
                {
                    "compressed": compressed,
                    "reference": reference,
                    "audit_key": f"{compressed}__to__{reference}",
                }
                for compressed, reference in COMPARISONS
            ],
        },
        "invariant_counts": invariant_counts,
        "representation_diagnostics": _representation_diagnostics(rows),
        "structured_result_verdict": _structured_result_verdict(
            primary_report["pooled_arm_risks"],
            sensitivity_report["pooled_arm_risks"],
        ),
        "primary_excluding_cross_batch_target_provenance": primary_report,
        "all_observed_eol_contaminated_sensitivity": sensitivity_report,
        "row_ledger": _row_ledger(rows, primary, all_eol),
        "run_identity": run_identity(
            {
                "design_status": "frozen_before_new_implementation_and_run",
                "strict_json_nonfinite_policy": "replace_with_null",
            }
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, default=EVENTS_REL)
    parser.add_argument("--output", type=Path, default=OUTPUT_REL)
    args = parser.parse_args()
    root = project_root()
    events_path = args.events if args.events.is_absolute() else root / args.events
    output_path = args.output if args.output.is_absolute() else root / args.output

    report = _json_safe(build_report(events_path))
    payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(payload)

    primary = report["primary_excluding_cross_batch_target_provenance"]
    sensitivity = report["all_observed_eol_contaminated_sensitivity"]
    print(f"wrote {output_path}")
    print(
        "  primary targets: "
        f"{primary['analysis_eligible_count']} | all-EOL sensitivity: "
        f"{sensitivity['analysis_eligible_count']}"
    )
    for label, analysis in (("primary", primary), ("all-EOL sensitivity", sensitivity)):
        print(f"  {label}")
        for fold in analysis["folds"]:
            chosen = ", ".join(
                f"{arm}={fold['arms'][arm]['selected_alpha']:g}" for arm in ARM_NAMES
            )
            print(f"    held {fold['held_batch']}: {chosen}")
    print("  verdict: retrospective, post-hoc, nonconfirmatory engineering dry run")


if __name__ == "__main__":
    main()
