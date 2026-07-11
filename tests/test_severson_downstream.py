"""Adversarial tests for the retrospective Severson downstream helpers."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from materials_event_modeling.eval.severson_downstream import (
    ARM_NAMES,
    S100_NAMES,
    X100_CYCLES,
    build_feature_bundle,
    extract_x100,
    held_batch_oof,
    load_downstream_rows,
    policy_macro_weights,
    summarize_x100,
)


def _observation(cycle: int, capacity: float, *, accepted: bool = True) -> dict:
    return {
        "observation_id": f"cycle:{cycle}",
        "modality": "cycling",
        "cycle_index": cycle,
        "include_in_raw_objective": accepted,
        "payload": {"cycling": {"qdischarge_ah": capacity}},
    }


def _event(
    event_id: str,
    *,
    batch: str = "batch_0",
    policy: str = "policy_0",
    cycles: range | list[int] | None = None,
    capacity_shift: float = 0.0,
    context: tuple[float, float, float] = (1.0, 40.0, 2.0),
    status: str = "success",
    cycle_life: float | None = 500.0,
    continuation_batches: list[str] | None = None,
) -> dict:
    cycle_values = range(2, 101) if cycles is None else cycles
    observations = [
        _observation(
            cycle,
            capacity_shift + 1.1 - 1e-4 * cycle + 1e-8 * cycle**2,
        )
        for cycle in cycle_values
    ]
    summary: dict[str, object] = {"cell.cycle_life_cycles": cycle_life}
    if status == "ambiguous":
        summary["cell.record_truncated"] = True
    return {
        "event_id": event_id,
        "intent": {
            "event_group_id": policy,
            "planned": {
                "cell.charge_c_rate_1": context[0],
                "cell.soc_switch_percent": context[1],
                "cell.charge_c_rate_2": context[2],
            },
        },
        "observations": observations,
        "outcome": {"status": status, "summary": summary},
        "provenance": {"batch_id": batch},
        "source_ref": {"merged_from_batches": continuation_batches},
    }


def _load_rows(tmp_path: Path, events: list[dict], name: str = "events.json"):
    path = tmp_path / name
    path.write_text(json.dumps(events))
    return load_downstream_rows(path)


def _oof_events(
    *,
    outlier_batch: str | None = None,
    continuation: bool = False,
) -> list[dict]:
    events = []
    for batch_index, batch in enumerate(("batch_0", "batch_1")):
        for policy_index in range(2):
            policy = f"{batch}:policy_{policy_index}"
            for replicate in range(2):
                is_outlier = batch == outlier_batch
                context_offset = 1000.0 if is_outlier else 0.0
                context = (
                    1.0 + 3.0 * batch_index + policy_index + context_offset,
                    30.0 + 10.0 * policy_index + context_offset,
                    2.0 + batch_index + context_offset,
                )
                event_id = f"{batch}:p{policy_index}:r{replicate}"
                continuation_batches = None
                if continuation and event_id == "batch_0:p0:r0":
                    continuation_batches = ["batch_0", "batch_1"]
                events.append(
                    _event(
                        event_id,
                        batch=batch,
                        policy=policy,
                        capacity_shift=(1000.0 if is_outlier else 0.005 * batch_index)
                        + 0.002 * policy_index
                        + 0.0005 * replicate,
                        context=context,
                        cycle_life=(
                            500.0 + 100.0 * batch_index + 80.0 * policy_index + 10.0 * replicate
                        ),
                        continuation_batches=continuation_batches,
                    )
                )
    return events


def _fold(result, held_batch: str) -> dict:
    return next(fold for fold in result.folds if fold["held_batch"] == held_batch)


def test_cutoff_is_applied_before_interpolation_and_future_changes_are_inert() -> None:
    event = _event("cell", cycles=list(range(1, 102)))
    event["observations"][0]["payload"]["cycling"]["qdischarge_ah"] = -1e9
    event["observations"][-1]["payload"]["cycling"]["qdischarge_ah"] = 1e9

    extraction = extract_x100(event)
    assert extraction.available
    assert extraction.values.shape == (99,)
    assert extraction.accepted_cycle_count == 99
    assert extraction.rejected_cycle_count == 0
    assert extraction.interpolated_cycles == ()
    assert extraction.values[0] == pytest.approx(1.1 - 1e-4 * 2 + 1e-8 * 2**2)
    assert extraction.values[-1] == pytest.approx(1.1 - 1e-4 * 100 + 1e-8 * 100**2)

    future_changed = copy.deepcopy(event)
    future_changed["observations"][-1]["payload"]["cycling"]["qdischarge_ah"] = -1e12
    future_changed["outcome"] = {
        "status": "ambiguous",
        "summary": {"cell.record_truncated": True, "cell.cycle_life_cycles": 99999},
    }
    future_changed["source_ref"] = {"merged_from_batches": ["batch_0", "future_batch"]}
    changed = extract_x100(future_changed)
    np.testing.assert_array_equal(changed.values, extraction.values)
    np.testing.assert_array_equal(summarize_x100(changed.values), summarize_x100(extraction.values))

    missing_endpoint = _event("missing", cycles=[*range(2, 100), 101])
    missing_endpoint["observations"][-1]["payload"]["cycling"]["qdischarge_ah"] = 1e12
    unavailable = extract_x100(missing_endpoint)
    assert not unavailable.available
    assert unavailable.reason == "missing_cycle_100"


def test_interpolation_uses_only_accepted_interior_anchors_and_records_mask() -> None:
    event = _event("cell", cycles=list(range(2, 102)))
    cycle_50 = next(
        observation for observation in event["observations"] if observation["cycle_index"] == 50
    )
    cycle_50["include_in_raw_objective"] = False
    cycle_50["payload"]["cycling"]["qdischarge_ah"] = 1e12
    event["observations"][-1]["payload"] = {}

    extraction = extract_x100(event)
    assert extraction.available
    assert extraction.reason == "available_interpolated"
    assert extraction.interpolated_cycles == (50,)
    assert extraction.accepted_cycle_count == 98
    assert extraction.rejected_cycle_count == 1
    assert extraction.observed_mask.shape == (99,)
    assert extraction.observed_mask.dtype == np.bool_
    assert extraction.observed_mask.sum() == 98
    assert not extraction.observed_mask[50 - 2]
    expected = ((1.1 - 1e-4 * 49 + 1e-8 * 49**2) + (1.1 - 1e-4 * 51 + 1e-8 * 51**2)) / 2.0
    assert extraction.values[50 - 2] == pytest.approx(expected)


def test_flagged_endpoints_duplicates_and_nonfinite_values_are_not_repaired() -> None:
    for endpoint, expected_reason in ((2, "missing_cycle_2"), (100, "missing_cycle_100")):
        event = _event(f"missing-{endpoint}")
        observation = next(
            item for item in event["observations"] if item["cycle_index"] == endpoint
        )
        observation["include_in_raw_objective"] = False
        extraction = extract_x100(event)
        assert not extraction.available
        assert extraction.reason == expected_reason

    duplicate = _event("duplicate")
    duplicate["observations"].append(_observation(50, 0.95))
    duplicate_result = extract_x100(duplicate)
    assert not duplicate_result.available
    assert duplicate_result.reason == "duplicate_accepted_cycle"

    nonfinite = _event("nonfinite")
    observation = next(item for item in nonfinite["observations"] if item["cycle_index"] == 50)
    observation["payload"]["cycling"]["qdischarge_ah"] = np.inf
    nonfinite_result = extract_x100(nonfinite)
    assert not nonfinite_result.available
    assert nonfinite_result.reason == "nonfinite_accepted_qdischarge"


def test_s100_is_the_exact_frozen_function_of_x100_and_arm_widths(tmp_path: Path) -> None:
    x100 = X100_CYCLES.astype(float)
    expected = np.array([51.0, 100.0, 1.0, 0.0, 98.0, 1.0, -12.0])
    summary = summarize_x100(x100)
    np.testing.assert_allclose(summary, expected, rtol=0.0, atol=1e-12)
    np.testing.assert_array_equal(summary, summarize_x100(x100.copy()))
    assert S100_NAMES == (
        "mean_capacity",
        "capacity_cycle_100",
        "ols_slope_cycles_2_100",
        "maximum_minus_final",
        "final_minus_first",
        "ols_slope_cycles_51_100",
        "log10_variance_first_differences",
    )

    rows = _load_rows(tmp_path, [_event("cell")])
    bundle = build_feature_bundle(rows)
    assert ARM_NAMES == ("C", "C_S100", "C_X100", "C_S100_X100")
    assert {name: matrix.shape[1] for name, matrix in bundle.matrices.items()} == {
        "C": 3,
        "C_S100": 10,
        "C_X100": 102,
        "C_S100_X100": 109,
    }
    assert all(bundle.available[name].tolist() == [True] for name in ARM_NAMES)
    row = rows[0]
    np.testing.assert_array_equal(row.s100, summarize_x100(row.x100))
    np.testing.assert_array_equal(bundle.matrices["C_S100"][0, 3:], row.s100)
    np.testing.assert_array_equal(bundle.matrices["C_X100"][0, 3:], row.x100)
    np.testing.assert_array_equal(bundle.matrices["C_S100_X100"][0, 3:10], row.s100)
    np.testing.assert_array_equal(bundle.matrices["C_S100_X100"][0, 10:], row.x100)


def test_censoring_target_support_and_early_eol_representation_support_are_separate(
    tmp_path: Path,
) -> None:
    exact = _event("exact", policy="p_exact", cycle_life=1000.0)
    censored = _event(
        "censored",
        policy="p_censored",
        cycles=range(2, 121),
        status="ambiguous",
        cycle_life=9999.0,
    )
    early_eol = _event(
        "early",
        policy="p_early",
        cycles=range(2, 81),
        status="success",
        cycle_life=80.0,
    )
    rows = _load_rows(tmp_path, [exact, censored, early_eol])
    exact_row, censored_row, early_row = rows

    assert exact_row.target_exact
    assert exact_row.log_cycle_life == pytest.approx(3.0)
    assert censored_row.target_status == "right_censored"
    assert not censored_row.target_exact
    assert censored_row.cycle_life is None
    assert censored_row.log_cycle_life is None
    assert censored_row.life_lower_bound == 121.0
    assert censored_row.x100_available
    assert early_row.target_status == "observed_eol"
    assert early_row.target_exact
    assert early_row.cycle_life == 80.0
    assert not early_row.x100_available
    assert early_row.x100_reason == "missing_cycle_100"

    bundle = build_feature_bundle(rows)
    np.testing.assert_array_equal(bundle.available["C"], [True, True, True])
    for arm in ("C_S100", "C_X100", "C_S100_X100"):
        np.testing.assert_array_equal(bundle.available[arm], [True, True, False])
        assert bundle.reasons[arm][2] == "x100:missing_cycle_100"

    analysis_eligible = np.array([True, False, True])
    np.testing.assert_array_equal(policy_macro_weights(rows, analysis_eligible), [1.0, 0.0, 1.0])
    with pytest.raises(ValueError, match="without an exact scalar target"):
        policy_macro_weights(rows, np.array([True, True, False]))


def test_held_batch_and_inner_policy_folds_are_strictly_out_of_fold(
    tmp_path: Path,
) -> None:
    rows = _load_rows(tmp_path, _oof_events())
    eligible = np.array([row.target_exact for row in rows])
    result = held_batch_oof(rows, eligible, alphas=(1.0,))

    assert result.metadata["outer_split"] == "leave_one_complete_batch_out"
    assert result.metadata["inner_split"] == "GroupKFold_by_charge_policy"
    assert result.metadata["analysis_eligible_count"] == 8
    for arm, predictions in result.predictions.items():
        assert arm in ARM_NAMES
        assert predictions.shape == (8,)
        assert np.all(np.isfinite(predictions))

    expected_widths = {"C": 3, "C_S100": 10, "C_X100": 102, "C_S100_X100": 109}
    for fold in result.folds:
        assert fold["held_batch"] not in fold["train_batches"]
        assert fold["train_attempt_count"] == 4
        assert fold["test_attempt_count"] == 4
        assert fold["train_target_count"] == 4
        assert fold["test_target_count"] == 4
        assert fold["train_policy_count"] == 2
        assert fold["test_policy_count"] == 2
        assert fold["event_overlap_count"] == 0
        assert fold["policy_overlap_count"] == 0
        for arm, metadata in fold["arms"].items():
            assert metadata["feature_width"] == expected_widths[arm]
            assert metadata["train_count"] == 4
            assert metadata["predicted_attempt_count"] == 4
            assert metadata["inner_n_splits"] == 2
            assert metadata["selected_alpha"] == 1.0
            for inner_fold in metadata["inner_folds"]:
                assert inner_fold["policy_overlap_count"] == 0
                assert inner_fold["train_policy_count"] == 1
                assert inner_fold["validation_policy_count"] == 1


def test_outer_policy_overlap_is_rejected_even_when_batches_differ(tmp_path: Path) -> None:
    events = _oof_events()
    events[4]["intent"]["event_group_id"] = events[0]["intent"]["event_group_id"]
    rows = _load_rows(tmp_path, events)
    eligible = np.ones(len(rows), dtype=bool)
    with pytest.raises(AssertionError, match="shares policy IDs"):
        held_batch_oof(rows, eligible, alphas=(1.0,))


def test_outer_test_outliers_cannot_change_training_scaler_or_alpha(tmp_path: Path) -> None:
    base_rows = _load_rows(tmp_path, _oof_events(), "base.json")
    outlier_rows = _load_rows(
        tmp_path,
        _oof_events(outlier_batch="batch_0"),
        "outlier.json",
    )
    eligible = np.ones(len(base_rows), dtype=bool)
    base = held_batch_oof(base_rows, eligible, alphas=(0.1, 1.0))
    outlier = held_batch_oof(outlier_rows, eligible, alphas=(0.1, 1.0))

    base_fold = _fold(base, "batch_0")
    outlier_fold = _fold(outlier, "batch_0")
    for arm in ARM_NAMES:
        assert (
            base_fold["arms"][arm]["selected_alpha"] == outlier_fold["arms"][arm]["selected_alpha"]
        )
        assert (
            base_fold["arms"][arm]["inner_candidate_scores"]
            == outlier_fold["arms"][arm]["inner_candidate_scores"]
        )
        assert base_fold["arms"][arm]["model"] == outlier_fold["arms"][arm]["model"]

    test_indices = np.array([row.batch == "batch_0" for row in base_rows])
    assert not np.allclose(
        base.predictions["C"][test_indices],
        outlier.predictions["C"][test_indices],
    )


def test_continuation_sensitivity_refits_models_instead_of_slicing_predictions(
    tmp_path: Path,
) -> None:
    rows = _load_rows(tmp_path, _oof_events(continuation=True))
    continuation_indices = np.array([row.cross_batch_target_provenance for row in rows], dtype=bool)
    assert continuation_indices.sum() == 1
    continuation_index = int(np.flatnonzero(continuation_indices)[0])
    assert rows[continuation_index].continuation_batches == ("batch_0", "batch_1")

    full_eligible = np.array([row.target_exact for row in rows])
    sensitivity_eligible = full_eligible & ~continuation_indices
    full = held_batch_oof(rows, full_eligible, alphas=(1.0,))
    sensitivity = held_batch_oof(rows, sensitivity_eligible, alphas=(1.0,))

    assert full.metadata["analysis_eligible_count"] == 8
    assert sensitivity.metadata["analysis_eligible_count"] == 7
    assert not sensitivity.analysis_eligible[continuation_index]
    for arm in ARM_NAMES:
        assert np.isfinite(sensitivity.predictions[arm][continuation_index])

    # When batch_0 is held out, the excluded continuation is only a test target: fitting is
    # unchanged, while the test-target ledger loses one row.
    full_test_continuation = _fold(full, "batch_0")
    sensitivity_test_continuation = _fold(sensitivity, "batch_0")
    assert full_test_continuation["train_target_count"] == 4
    assert sensitivity_test_continuation["train_target_count"] == 4
    assert full_test_continuation["test_target_count"] == 4
    assert sensitivity_test_continuation["test_target_count"] == 3
    for arm in ARM_NAMES:
        assert (
            full_test_continuation["arms"][arm]["model"]
            == (sensitivity_test_continuation["arms"][arm]["model"])
        )

    # When batch_1 is held out, that same row was in training. Its removal must change the
    # fitted scaler/model, proving this is a complete refit rather than a result-table slice.
    full_train_continuation = _fold(full, "batch_1")
    sensitivity_train_continuation = _fold(sensitivity, "batch_1")
    assert full_train_continuation["train_target_count"] == 4
    assert sensitivity_train_continuation["train_target_count"] == 3
    assert full_train_continuation["test_target_count"] == 4
    assert sensitivity_train_continuation["test_target_count"] == 4
    assert (
        full_train_continuation["arms"]["C"]["model"]["scaler_mean"]
        != (sensitivity_train_continuation["arms"]["C"]["model"]["scaler_mean"])
    )
