"""Tests for the task-relevant compression audit instrument."""

from __future__ import annotations

from decimal import Decimal

import numpy as np
import pytest

from materials_event_modeling.eval.compression_audit import (
    PredictionArm,
    audit_compression_pair,
    audit_information_cutoff,
    audit_pair_collisions,
    audit_prediction_bundle,
    binary_brier,
    binary_log_loss,
    root_mean_risk,
    squared_error,
)


def test_support_loss_is_not_hidden_by_zero_common_support_gap() -> None:
    truth = np.array([0.0, 1.0, 2.0, 3.0])
    compressed = PredictionArm(
        "paper",
        predictions=truth.copy(),
        available=np.array([True, True, False, False]),
    )
    reference = PredictionArm("event", predictions=truth.copy())
    report = audit_compression_pair(
        truth,
        compressed,
        reference,
        loss=squared_error,
        metric_name="mse",
        risk_tolerance=0.01,
        event_importance_weights=np.array([1.0, 1.0, 2.0, 2.0]),
        clusters=np.array(["a", "b", "c", "d"]),
        n_boot=200,
    )

    assert report["common_support_risk"]["verdict"] == "bounded_risk_adequacy"
    assert report["support"]["events_excluded_by_compression_count"] == 2
    assert report["support"]["events_excluded_by_compression_fraction_of_reference"] == 0.5
    assert np.isclose(
        report["support"][
            "event_importance_excluded_by_compression_fraction_of_reference"
        ],
        4.0 / 6.0,
    )
    assert report["pooled_component_verdict"] == "loss_detected"


def test_importance_weighted_event_support_can_exceed_the_count_margin() -> None:
    truth = np.zeros(10)
    compressed = PredictionArm(
        "paper",
        predictions=truth.copy(),
        available=np.array([True] * 9 + [False]),
    )
    reference = PredictionArm("event", predictions=truth.copy())
    report = audit_compression_pair(
        truth,
        compressed,
        reference,
        loss=squared_error,
        metric_name="mse",
        risk_tolerance=0.01,
        event_support_tolerance=0.2,
        weighted_event_support_tolerance=0.2,
        event_importance_weights=np.array([1.0] * 9 + [9.0]),
        clusters=np.arange(10),
        n_boot=100,
    )

    assert report["support"]["events_excluded_by_compression_fraction_of_reference"] == 0.1
    assert report["support"][
        "event_importance_excluded_by_compression_fraction_of_reference"
    ] == 0.5
    assert report["support"]["verdict"] == "support_loss"


def test_zero_total_event_importance_cannot_yield_an_adequacy_verdict() -> None:
    truth = np.zeros(2)
    report = audit_compression_pair(
        truth,
        PredictionArm("summary", predictions=truth),
        PredictionArm("trace", predictions=truth),
        loss=squared_error,
        metric_name="mse",
        risk_tolerance=0.1,
        event_support_tolerance=1.0,
        weighted_event_support_tolerance=1.0,
        event_importance_weights=np.zeros(2),
        clusters=np.arange(2),
        n_boot=20,
    )
    assert report["support"]["verdict"] == "not_estimable"
    assert report["pooled_component_verdict"] == "inconclusive"


def test_shared_omission_fails_absolute_support_even_when_relative_loss_is_zero() -> None:
    truth = np.zeros(4)
    availability = np.array([True, True, False, False])
    compressed = PredictionArm("paper", predictions=truth.copy(), available=availability)
    reference = PredictionArm("event", predictions=truth.copy(), available=availability)
    report = audit_compression_pair(
        truth,
        compressed,
        reference,
        loss=squared_error,
        metric_name="mse",
        risk_tolerance=0.01,
        clusters=np.arange(4),
        n_boot=100,
    )

    assert report["support"]["events_excluded_by_compression_count"] == 0
    assert report["support"]["compressed_event_support_loss_fraction"] == 0.5
    assert report["support"]["reference_event_support_loss_fraction"] == 0.5
    assert report["support"]["verdict"] == "support_loss"
    assert report["pooled_component_verdict"] == "loss_detected"


def test_positive_common_support_gap_detects_premature_compression() -> None:
    truth = np.zeros(8)
    compressed = PredictionArm("label", predictions=np.ones(8))
    reference = PredictionArm("trace", predictions=np.zeros(8))
    report = audit_compression_pair(
        truth,
        compressed,
        reference,
        loss=squared_error,
        metric_name="mse",
        risk_tolerance=0.1,
        clusters=np.repeat(np.arange(4), 2),
        n_boot=200,
    )

    risk = report["common_support_risk"]
    assert risk["risk_gap_compressed_minus_reference"] == 1.0
    assert risk["risk_gap_ci95"] == [1.0, 1.0]
    assert risk["verdict"] == "premature_compression"
    assert report["pooled_component_verdict"] == "loss_detected"


def test_adequacy_is_bounded_and_environment_specific() -> None:
    truth = np.zeros(8)
    compressed = PredictionArm("summary", predictions=np.full(8, 0.1))
    reference = PredictionArm("trace", predictions=np.zeros(8))
    environments = np.repeat(["day_1", "day_2"], 4)
    report = audit_compression_pair(
        truth,
        compressed,
        reference,
        loss=squared_error,
        metric_name="mse",
        risk_tolerance=0.02,
        clusters=np.arange(8),
        environments=environments,
        transfer_rule="all_environments",
        environment_evaluation="held_out_environment",
        n_boot=200,
    )

    assert report["common_support_risk"]["verdict"] == "bounded_risk_adequacy"
    assert set(report["environment_results"]) == {"str:'day_1'", "str:'day_2'"}
    assert all(
        result["common_support_risk"]["verdict"] == "bounded_risk_adequacy"
        for result in report["environment_results"].values()
    )
    assert all(
        result["support"]["verdict"] == "within_support_tolerances"
        for result in report["environment_results"].values()
    )
    assert report["pooled_component_verdict"] == "bounded_event_support_and_common_risk"
    assert (
        report["transfer_verdict"]
        == "bounded_event_support_and_common_risk_in_every_held_out_environment"
    )


def test_heterogeneous_environments_do_not_inherit_a_pooled_transfer_verdict() -> None:
    truth = np.zeros(104)
    compressed = PredictionArm("summary", predictions=np.r_[np.ones(100), np.zeros(4)])
    reference = PredictionArm("trace", predictions=np.r_[np.zeros(100), np.ones(4)])
    report = audit_compression_pair(
        truth,
        compressed,
        reference,
        loss=squared_error,
        metric_name="mse",
        risk_tolerance=0.1,
        clusters=np.arange(104),
        environments=np.array(["day_1"] * 100 + ["day_2"] * 4),
        transfer_rule="all_environments",
        environment_evaluation="held_out_environment",
        compact_advantage_tolerance=0.1,
        n_boot=200,
    )

    assert report["pooled_component_verdict"] == "loss_detected"
    assert (
        report["transfer_verdict"]
        == "inconclusive_or_heterogeneous_across_held_out_environments"
    )
    assert (
        report["environment_results"]["str:'day_1'"]["component_verdict"]
        == "loss_detected"
    )
    assert (
        report["environment_results"]["str:'day_2'"]["component_verdict"]
        == "bounded_event_support_and_common_risk"
    )
    day_2_risk = report["environment_results"]["str:'day_2'"]["common_support_risk"]
    assert day_2_risk["verdict"] == "bounded_risk_adequacy"
    assert day_2_risk["compact_advantage_verdict"] == "compact_arm_advantage"


def test_log_loss_gap_is_reported_in_bits() -> None:
    truth = np.array([0.0, 0.0, 1.0, 1.0])
    compressed = PredictionArm("label", predictions=np.full(4, 0.5))
    reference = PredictionArm("trace", predictions=np.array([0.1, 0.1, 0.9, 0.9]))
    report = audit_compression_pair(
        truth,
        compressed,
        reference,
        loss=binary_log_loss,
        metric_name="binary_log_loss_bits",
        risk_tolerance=0.01,
        clusters=np.arange(4),
        n_boot=200,
    )

    assert report["common_support_risk"]["risk_gap_compressed_minus_reference"] > 0.8
    assert report["pooled_component_verdict"] == "loss_detected"


def test_nonfinite_prediction_on_an_available_event_is_rejected() -> None:
    truth = np.zeros(4)
    compressed = PredictionArm("label", predictions=np.array([0.0, np.nan, 0.0, 0.0]))
    reference = PredictionArm("trace", predictions=np.zeros(4))
    with pytest.raises(ValueError, match="non-finite prediction"):
        audit_compression_pair(
            truth,
            compressed,
            reference,
            loss=squared_error,
            metric_name="mse",
            risk_tolerance=0.1,
            clusters=np.arange(4),
            n_boot=100,
        )


def test_bundle_and_information_cutoff_contract() -> None:
    truth = np.zeros(4)
    arms = {
        "C+L60": PredictionArm("C+L60", predictions=np.ones(4)),
        "C+L60+X60": PredictionArm("C+L60+X60", predictions=np.zeros(4)),
    }
    bundle = audit_prediction_bundle(
        truth,
        arms,
        [("C+L60", "C+L60+X60")],
        loss=squared_error,
        metric_name="mse",
        risk_tolerance=0.1,
        clusters=np.arange(4),
        n_boot=100,
    )
    assert "C+L60__to__C+L60+X60" in bundle["comparisons"]

    cutoff = audit_information_cutoff(
        np.array([5.0, 60.0, 61.0, 24.0 * 60.0]),
        60.0,
        available=np.array([True, True, True, False]),
    )
    assert not cutoff["passed"]
    assert cutoff["violation_indices"] == [2]

    unknown = audit_information_cutoff(np.array([5.0, np.nan]), 60.0)
    assert not unknown["passed"]
    assert unknown["verdict"] == "unverifiable"
    assert unknown["unknown_time_indices"] == [1]

    with pytest.raises(ValueError, match="state_cutoff must be finite"):
        audit_information_cutoff(np.array([5.0, 60.0]), np.nan)

    offline_assay = audit_information_cutoff(
        np.array([5.0, 60.0]),
        60.0,
        assay_ready_time=np.array([90.0, 180.0]),
    )
    assert offline_assay["passed"]
    assert offline_assay["operational_mode"] == "offline_sampled_state"

    deadline = audit_information_cutoff(
        np.array([5.0, 60.0]),
        60.0,
        assay_ready_time=np.array([90.0, 181.0]),
        decision_deadline=180.0,
    )
    assert deadline["verdict"] == "violated"
    assert deadline["state_violation_indices"] == []
    assert deadline["assay_deadline_violation_indices"] == [1]

    chronology = audit_information_cutoff(
        np.array([5.0, 60.0]),
        60.0,
        assay_ready_time=np.array([4.0, 180.0]),
    )
    assert chronology["verdict"] == "violated"
    assert chronology["assay_before_state_violation_indices"] == [0]


def test_risk_weights_must_be_strictly_positive() -> None:
    truth = np.zeros(4)
    with pytest.raises(ValueError, match="strictly positive"):
        audit_compression_pair(
            truth,
            PredictionArm("summary", predictions=np.zeros(4)),
            PredictionArm("trace", predictions=np.zeros(4)),
            loss=squared_error,
            metric_name="mse",
            risk_tolerance=0.1,
            sample_weights=np.array([1.0, 1.0, 0.0, 1.0]),
            clusters=np.arange(4),
            n_boot=100,
        )


def test_rmse_aggregates_before_taking_the_risk_gap() -> None:
    truth = np.zeros(4)
    report = audit_compression_pair(
        truth,
        PredictionArm("summary", predictions=np.full(4, 2.0)),
        PredictionArm("trace", predictions=np.full(4, 1.0)),
        loss=squared_error,
        aggregate=root_mean_risk,
        metric_name="rmse",
        risk_tolerance=0.1,
        clusters=np.arange(4),
        n_boot=100,
    )

    risk = report["common_support_risk"]
    assert risk["compressed_risk"] == 2.0
    assert risk["reference_risk"] == 1.0
    assert risk["risk_gap_compressed_minus_reference"] == 1.0
    assert risk["risk_gap_ci95"] == [1.0, 1.0]
    assert report["risk_aggregation"] == "root_mean_risk"


def test_environment_labels_reject_missing_and_do_not_string_collide() -> None:
    truth = np.zeros(4)
    arms = (
        PredictionArm("summary", predictions=np.zeros(4)),
        PredictionArm("trace", predictions=np.zeros(4)),
    )
    with pytest.raises(ValueError, match="missing or non-finite"):
        audit_compression_pair(
            truth,
            *arms,
            environments=np.array(["day_1", "day_1", np.nan, "day_2"], dtype=object),
            loss=squared_error,
            metric_name="mse",
            risk_tolerance=0.1,
            clusters=np.arange(4),
            n_boot=100,
        )

    report = audit_compression_pair(
        truth,
        *arms,
        environments=np.array([1, 1, "1", "1"], dtype=object),
        loss=squared_error,
        metric_name="mse",
        risk_tolerance=0.1,
        clusters=np.arange(4),
        n_boot=100,
    )
    assert set(report["environment_results"]) == {"int:1", "str:'1'"}

    for missing_label in (
        Decimal("NaN"),
        complex(np.nan, 0.0),
        np.datetime64("NaT", "ns"),
    ):
        with pytest.raises(ValueError, match="missing or non-finite"):
            audit_compression_pair(
                truth,
                *arms,
                environments=np.array(["day_1", "day_1", missing_label, "day_2"], dtype=object),
                loss=squared_error,
                metric_name="mse",
                risk_tolerance=0.1,
                clusters=np.arange(4),
                n_boot=100,
            )


def test_binary_brier_rejects_invalid_targets() -> None:
    with pytest.raises(ValueError, match="targets must be finite"):
        binary_brier(np.array([0.0, 2.0]), np.array([0.1, 0.9]))


def test_loss_is_evaluated_only_inside_each_arms_declared_universe() -> None:
    report = audit_compression_pair(
        np.array([0.0, 1.0, 2.0]),
        PredictionArm("summary", predictions=np.array([0.1, 0.9, 5.0])),
        PredictionArm("trace", predictions=np.array([0.0, 1.0, np.nan])),
        loss=binary_brier,
        metric_name="brier",
        risk_tolerance=0.1,
        universe=np.array([True, True, False]),
        sample_weights=np.array([1.0, 1.0, 0.0]),
        clusters=np.arange(3),
        n_boot=100,
    )
    assert report["common_support_risk"]["common_support_count"] == 2


def test_boolean_masks_reject_missing_or_truthy_non_booleans() -> None:
    truth = np.zeros(2)
    for malformed in (
        np.array([True, np.nan], dtype=object),
        np.array(["True", "False"]),
        np.array([1, 0]),
    ):
        with pytest.raises(ValueError, match="strict booleans"):
            audit_compression_pair(
                truth,
                PredictionArm("summary", predictions=truth, available=malformed),
                PredictionArm("trace", predictions=truth),
                loss=squared_error,
                metric_name="mse",
                risk_tolerance=0.1,
                clusters=np.arange(2),
                n_boot=20,
            )

    with pytest.raises(ValueError, match="strict booleans"):
        audit_information_cutoff(
            np.array([5.0, 10.0]),
            60.0,
            available=np.array([1, 0]),
        )


def test_transfer_claim_requires_held_out_environment_predictions() -> None:
    truth = np.zeros(4)
    with pytest.raises(ValueError, match="held_out_environment"):
        audit_compression_pair(
            truth,
            PredictionArm("summary", predictions=truth),
            PredictionArm("trace", predictions=truth),
            loss=squared_error,
            metric_name="mse",
            risk_tolerance=0.1,
            clusters=np.arange(4),
            environments=np.array(["d1", "d1", "d2", "d2"]),
            transfer_rule="all_environments",
            n_boot=20,
        )

    with pytest.raises(ValueError, match="requires environment labels"):
        audit_compression_pair(
            truth,
            PredictionArm("summary", predictions=truth),
            PredictionArm("trace", predictions=truth),
            loss=squared_error,
            metric_name="mse",
            risk_tolerance=0.1,
            clusters=np.arange(4),
            transfer_rule="all_environments",
            environment_evaluation="held_out_environment",
            n_boot=20,
        )

    with pytest.raises(ValueError, match="at least two represented environments"):
        audit_compression_pair(
            truth,
            PredictionArm("summary", predictions=truth),
            PredictionArm("trace", predictions=truth),
            loss=squared_error,
            metric_name="mse",
            risk_tolerance=0.1,
            clusters=np.arange(4),
            environments=np.array(["d1"] * 4),
            transfer_rule="all_environments",
            environment_evaluation="held_out_environment",
            n_boot=20,
        )


def test_nonfinite_bootstrap_aggregate_is_rejected() -> None:
    def unstable_aggregate(losses: np.ndarray, weights: np.ndarray) -> float:
        if np.unique(losses).size < 2:
            return float("nan")
        return float(np.average(losses, weights=weights))

    truth = np.zeros(4)
    with pytest.raises(ValueError, match="finite scalar"):
        audit_compression_pair(
            truth,
            PredictionArm("summary", predictions=np.array([0.0, 0.0, 1.0, 1.0])),
            PredictionArm("trace", predictions=np.array([1.0, 1.0, 0.0, 0.0])),
            loss=squared_error,
            aggregate=unstable_aggregate,
            metric_name="unstable",
            risk_tolerance=0.1,
            clusters=np.arange(4),
            n_boot=200,
        )


def test_pair_collisions_separate_ties_from_missing_decisions() -> None:
    representation = np.array([[0.0], [0.0], [1.0], [2.0]])
    pairs = np.array([[0, 1], [1, 2], [2, 3]])
    report = audit_pair_collisions(
        representation,
        pairs,
        available=np.array([True, True, True, False]),
        decision_weights=np.array([2.0, 1.0, 1.0]),
    )

    assert report["decision_count"] == 3
    assert report["representable_decision_count"] == 2
    assert report["decision_coverage"] == 2.0 / 3.0
    assert report["decision_weight_coverage"] == 0.75
    assert report["decision_support_verdict"] == "decision_support_loss"
    assert report["collision_count"] == 1
    assert report["collision_rate_on_representable_decisions"] == 0.5
    assert report["decision_weighted_collision_rate"] == 2.0 / 3.0
    assert report["pairwise_accuracy_ceiling_if_noncollisions_perfect"] == 0.75
    assert np.isclose(
        report[
            "decision_weighted_pairwise_accuracy_ceiling_if_noncollisions_perfect"
        ],
        2.0 / 3.0,
    )


def test_pair_collision_audit_rejects_nonfinite_available_values() -> None:
    with pytest.raises(ValueError, match="missing or non-finite"):
        audit_pair_collisions(
            np.array([np.nan, np.nan]),
            np.array([[0, 1]]),
        )


def test_pair_collision_audit_rejects_self_pairs_and_zero_weight_universes() -> None:
    with pytest.raises(ValueError, match="self-comparisons"):
        audit_pair_collisions(
            np.array([0.0, 1.0]),
            np.array([[0, 0]]),
        )
    with pytest.raises(ValueError, match="positive total weight"):
        audit_pair_collisions(
            np.array([0.0, 1.0]),
            np.array([[0, 1]]),
            decision_weights=np.array([0.0]),
        )


def test_pair_collision_count_and_weighted_bounds_are_separate() -> None:
    representation = np.array([0.0, 0.0, 1.0])
    pairs = np.array([[0, 1], [1, 2]])
    report = audit_pair_collisions(
        representation,
        pairs,
        decision_weights=np.array([9.0, 1.0]),
        collision_tolerance=0.5,
        weighted_collision_tolerance=0.9,
    )
    assert report["collision_rate_on_representable_decisions"] == 0.5
    assert report["decision_weighted_collision_rate"] == 0.9
    assert report["collision_verdict"] == "within_collision_tolerance"

    exceeded = audit_pair_collisions(
        representation,
        pairs,
        decision_weights=np.array([9.0, 1.0]),
        collision_tolerance=0.49,
        weighted_collision_tolerance=0.95,
    )
    assert exceeded["collision_verdict"] == "collision_bound_exceeded"
