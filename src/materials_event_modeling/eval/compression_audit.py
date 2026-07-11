"""Task-relevant compression audits over out-of-fold predictions.

The evaluator deliberately starts *after* model fitting.  A materials task decides which
models, features, and cross-fitting scheme are credible; this module standardizes the part
that should not vary between tasks:

* risk on the events both representations can express,
* count- and importance-weighted event support plus explicit decision-instance support,
* paired cluster-bootstrap uncertainty,
* environment-specific diagnostics, and
* bounded-adequacy versus premature-compression verdicts.

Positive risk gaps mean the richer/reference representation has lower loss.  A risk result
never repairs missing support: a compressed representation that drops failed or censored
events can look excellent on the selected rows that remain, so support and risk are always
reported separately.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from numbers import Number
from typing import Any

import numpy as np

LossFunction = Callable[[np.ndarray, np.ndarray], np.ndarray]
RiskAggregator = Callable[[np.ndarray, np.ndarray], float]


@dataclass(frozen=True)
class PredictionArm:
    """Out-of-fold predictions and the events a representation can express.

    ``available`` describes representational availability, not whether the prediction is
    finite.  Keep the distinction explicit: an absent paper-shaped row is support loss;
    an NaN prediction for an otherwise representable row is an evaluation failure.
    """

    name: str
    predictions: np.ndarray
    available: np.ndarray | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def squared_error(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    """Per-example squared error for a continuous target."""
    truth, prediction = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    if truth.shape != prediction.shape:
        raise ValueError("squared_error requires truth and prediction with identical shapes")
    return np.square(prediction - truth)


def absolute_error(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    """Per-example absolute error for a continuous target."""
    truth, prediction = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    if truth.shape != prediction.shape:
        raise ValueError("absolute_error requires truth and prediction with identical shapes")
    return np.abs(prediction - truth)


def binary_brier(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    """Per-example Brier loss for binary probabilities."""
    truth, prediction = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    if truth.shape != prediction.shape:
        raise ValueError("binary_brier requires truth and prediction with identical shapes")
    if np.any(~np.isfinite(truth)) or np.any((truth < 0.0) | (truth > 1.0)):
        raise ValueError("binary_brier targets must be finite and lie in [0, 1]")
    if np.any((prediction < 0.0) | (prediction > 1.0)):
        raise ValueError("binary_brier predictions must lie in [0, 1]")
    return np.square(prediction - truth)


def binary_log_loss(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    """Per-example binary log loss in bits.

    This is the special case where a risk gap estimates conditional usable information.
    It is secondary at small pilot scale because probability calibration is data hungry.
    """
    truth, prediction = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    if truth.shape != prediction.shape:
        raise ValueError("binary_log_loss requires truth and prediction with identical shapes")
    if np.any(~np.isfinite(truth)) or np.any((truth < 0.0) | (truth > 1.0)):
        raise ValueError("binary_log_loss targets must be finite and lie in [0, 1]")
    if np.any((prediction < 0.0) | (prediction > 1.0)):
        raise ValueError("binary_log_loss predictions must lie in [0, 1]")
    probability = np.clip(prediction, 1e-12, 1.0 - 1e-12)
    return -(truth * np.log2(probability) + (1.0 - truth) * np.log2(1.0 - probability))


def _availability(arm: PredictionArm, n: int) -> np.ndarray:
    predictions = np.asarray(arm.predictions)
    if predictions.ndim == 0 or predictions.shape[0] != n:
        raise ValueError(f"arm {arm.name!r} must have {n} predictions")
    if arm.available is None:
        return np.ones(n, dtype=bool)
    return _boolean_mask(
        arm.available,
        n,
        name=f"arm {arm.name!r} availability",
    )


def _boolean_mask(values: np.ndarray, n: int, *, name: str) -> np.ndarray:
    mask = np.asarray(values)
    if mask.shape != (n,):
        raise ValueError(f"{name} must have shape ({n},)")
    if not np.issubdtype(mask.dtype, np.bool_):
        raise ValueError(f"{name} must contain strict booleans without missing values")
    return mask


def _finite_rows(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim == 1:
        return np.isfinite(array)
    return np.all(np.isfinite(array), axis=tuple(range(1, array.ndim)))


def _weights(
    values: np.ndarray | None,
    n: int,
    *,
    name: str,
    allow_zero: bool = True,
) -> np.ndarray:
    if values is None:
        return np.ones(n, dtype=float)
    weights = np.asarray(values, dtype=float)
    if weights.shape != (n,):
        raise ValueError(f"{name} must have shape ({n},)")
    if np.any(~np.isfinite(weights)) or np.any(weights < 0.0):
        raise ValueError(f"{name} must contain finite, non-negative values")
    if not allow_zero and np.any(weights <= 0.0):
        raise ValueError(f"{name} must contain strictly positive values")
    return weights


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    total = float(weights.sum())
    if total <= 0.0:
        raise ValueError("cannot calculate a weighted risk with zero total weight")
    return float(np.sum(values * weights) / total)


def _missing_or_nonfinite_scalar(value: object) -> bool:
    if value is None:
        return True
    array = np.asarray(value)
    if array.ndim != 0:
        return True
    if array.dtype.kind in "mM":
        return bool(np.isnat(array))
    if isinstance(value, Number):
        try:
            return not bool(np.isfinite(value))
        except TypeError:
            try:
                return not math.isfinite(float(str(value)))
            except (TypeError, ValueError):
                return True
    try:
        equals_self = value == value
        return not bool(equals_self)
    except (TypeError, ValueError):
        return True


def _label_token(value: object, *, name: str) -> str:
    if _missing_or_nonfinite_scalar(value):
        raise ValueError(f"{name} contains a missing or non-finite label")
    if not isinstance(
        value,
        (str, bytes, bool, int, float, complex, Decimal, date, datetime, np.generic),
    ):
        raise ValueError(
            f"{name} labels must use stable scalar string, numeric, or date/time types"
        )
    try:
        hash(value)
    except TypeError as exc:
        raise ValueError(f"{name} labels must be hashable scalars") from exc
    return f"{type(value).__name__}:{value!r}"


def _encode_labels(values: np.ndarray, mask: np.ndarray, *, name: str) -> np.ndarray:
    encoded = np.empty(values.size, dtype=object)
    for index, value in enumerate(values.tolist()):
        if mask[index]:
            encoded[index] = _label_token(value, name=name)
        else:
            encoded[index] = f"outside_universe:{index}"
    return encoded


def _valid_representation_rows(values: np.ndarray) -> np.ndarray:
    if values.dtype.kind in "biufc":
        return _finite_rows(values)
    if values.dtype.kind in "mM":
        missing = np.isnat(values)
        if values.ndim == 1:
            return ~missing
        return ~np.any(missing, axis=tuple(range(1, values.ndim)))
    flattened = values.reshape(values.shape[0], -1)
    return np.array(
        [
            not any(_missing_or_nonfinite_scalar(value) for value in row.tolist())
            for row in flattened
        ],
        dtype=bool,
    )


def mean_risk(losses: np.ndarray, weights: np.ndarray) -> float:
    """Weighted arithmetic mean for additive per-example losses."""
    return _weighted_mean(losses, weights)


def root_mean_risk(squared_losses: np.ndarray, weights: np.ndarray) -> float:
    """Root weighted mean, used with per-example squared errors to obtain RMSE."""
    mean = _weighted_mean(squared_losses, weights)
    if mean < 0.0:
        raise ValueError("root_mean_risk requires non-negative per-example losses")
    return float(np.sqrt(mean))


def _aggregate_risk(
    aggregate: RiskAggregator,
    losses: np.ndarray,
    weights: np.ndarray,
) -> float:
    value = np.asarray(aggregate(losses, weights))
    if value.shape != () or not np.isfinite(value):
        raise ValueError("risk aggregate must return a finite scalar")
    return float(value)


def _evaluate_arm_loss(
    loss: LossFunction,
    truth: np.ndarray,
    predictions: np.ndarray,
    eligible: np.ndarray,
    *,
    arm_name: str,
) -> np.ndarray:
    values = np.full(truth.size, np.nan, dtype=float)
    count = int(eligible.sum())
    if count == 0:
        return values
    evaluated = np.asarray(loss(truth[eligible], predictions[eligible]), dtype=float)
    if evaluated.shape != (count,):
        raise ValueError("loss must return one value per eligible example")
    if not np.all(np.isfinite(evaluated)):
        raise ValueError(f"{arm_name} arm has a non-finite loss on an available event")
    values[eligible] = evaluated
    return values


def _cluster_bootstrap_ci(
    compressed_loss: np.ndarray,
    reference_loss: np.ndarray,
    weights: np.ndarray,
    clusters: np.ndarray,
    *,
    aggregate: RiskAggregator,
    seed: int,
    n_boot: int,
) -> list[float | None]:
    unique = list(dict.fromkeys(clusters.tolist()))
    if len(unique) < 2 or compressed_loss.size < 2:
        return [None, None]
    rng = np.random.default_rng(seed)
    indices = {cluster: np.flatnonzero(clusters == cluster) for cluster in unique}
    statistics: list[float] = []
    for _ in range(n_boot):
        sampled = rng.integers(0, len(unique), size=len(unique))
        draw = np.concatenate([indices[unique[index]] for index in sampled])
        compressed_risk = _aggregate_risk(
            aggregate,
            compressed_loss[draw],
            weights[draw],
        )
        reference_risk = _aggregate_risk(
            aggregate,
            reference_loss[draw],
            weights[draw],
        )
        statistics.append(compressed_risk - reference_risk)
    return [
        float(np.percentile(statistics, 2.5)),
        float(np.percentile(statistics, 97.5)),
    ]


def _risk_verdict(ci95: list[float | None], risk_tolerance: float) -> str:
    low, high = ci95
    if low is None or high is None:
        return "inconclusive"
    if low > risk_tolerance:
        return "premature_compression"
    if high <= risk_tolerance:
        return "bounded_risk_adequacy"
    return "inconclusive"


def _compact_advantage_verdict(
    ci95: list[float | None],
    tolerance: float | None,
) -> str:
    if tolerance is None:
        return "not_declared"
    _, high = ci95
    if high is None:
        return "inconclusive"
    if high < -tolerance:
        return "compact_arm_advantage"
    return "not_demonstrated"


def _risk_result(
    compressed_loss: np.ndarray,
    reference_loss: np.ndarray,
    mask: np.ndarray,
    sample_weights: np.ndarray,
    clusters: np.ndarray,
    *,
    aggregate: RiskAggregator,
    risk_tolerance: float,
    compact_advantage_tolerance: float | None,
    seed: int,
    n_boot: int,
) -> dict[str, Any]:
    selected = np.flatnonzero(mask)
    if selected.size == 0:
        return {
            "common_support_count": 0,
            "compressed_risk": None,
            "reference_risk": None,
            "risk_gap_compressed_minus_reference": None,
            "risk_gap_ci95": [None, None],
            "verdict": "not_estimable",
            "compact_advantage_verdict": "not_estimable",
        }
    weights = sample_weights[selected]
    compressed = compressed_loss[selected]
    reference = reference_loss[selected]
    ci95 = _cluster_bootstrap_ci(
        compressed,
        reference,
        weights,
        clusters[selected],
        aggregate=aggregate,
        seed=seed,
        n_boot=n_boot,
    )
    compressed_risk = _aggregate_risk(aggregate, compressed, weights)
    reference_risk = _aggregate_risk(aggregate, reference, weights)
    return {
        "common_support_count": int(selected.size),
        "compressed_risk": compressed_risk,
        "reference_risk": reference_risk,
        "risk_gap_compressed_minus_reference": compressed_risk - reference_risk,
        "risk_gap_ci95": ci95,
        "verdict": _risk_verdict(ci95, risk_tolerance),
        "compact_advantage_verdict": _compact_advantage_verdict(
            ci95,
            compact_advantage_tolerance,
        ),
    }


def _support_result(
    universe_mask: np.ndarray,
    compressed_available: np.ndarray,
    reference_available: np.ndarray,
    event_importance_weights: np.ndarray,
    *,
    event_support_tolerance: float,
    weighted_event_support_tolerance: float,
) -> dict[str, Any]:
    reference_population = universe_mask & reference_available
    compressed_population = universe_mask & compressed_available
    compressed_missing = universe_mask & ~compressed_available
    reference_missing = universe_mask & ~reference_available
    excluded = reference_population & ~compressed_available
    reference_count = int(reference_population.sum())
    relative_excluded_fraction = (
        float(excluded.sum() / reference_count) if reference_count else None
    )
    reference_importance_weight = float(np.sum(event_importance_weights[reference_population]))
    excluded_importance_weight = float(np.sum(event_importance_weights[excluded]))
    universe_importance_weight = float(np.sum(event_importance_weights[universe_mask]))
    compressed_missing_importance_weight = float(
        np.sum(event_importance_weights[compressed_missing])
    )
    importance_excluded_fraction = (
        excluded_importance_weight / reference_importance_weight
        if reference_importance_weight > 0.0
        else None
    )
    universe_count = int(universe_mask.sum())
    event_support_loss = (
        float(compressed_missing.sum() / universe_count) if universe_count else None
    )
    weighted_event_support_loss = (
        compressed_missing_importance_weight / universe_importance_weight
        if universe_importance_weight > 0.0
        else None
    )
    if event_support_loss is None:
        support_verdict = "not_estimable"
    elif event_support_loss > event_support_tolerance:
        support_verdict = "support_loss"
    elif weighted_event_support_loss is None:
        support_verdict = "not_estimable"
    elif weighted_event_support_loss > weighted_event_support_tolerance:
        support_verdict = "support_loss"
    else:
        support_verdict = "within_support_tolerances"
    return {
        "universe_count": universe_count,
        "compressed_event_count": int(compressed_population.sum()),
        "reference_event_count": reference_count,
        "compressed_event_coverage": (
            float(compressed_population.sum() / universe_count) if universe_count else None
        ),
        "reference_event_coverage": (
            float(reference_population.sum() / universe_count) if universe_count else None
        ),
        "compressed_event_support_loss_fraction": event_support_loss,
        "reference_event_support_loss_fraction": (
            float(reference_missing.sum() / universe_count) if universe_count else None
        ),
        "compressed_event_importance_support_loss_fraction": weighted_event_support_loss,
        "events_excluded_by_compression_count": int(excluded.sum()),
        "events_excluded_by_compression_fraction_of_reference": relative_excluded_fraction,
        "event_importance_excluded_by_compression": excluded_importance_weight,
        "event_importance_excluded_by_compression_fraction_of_reference": (
            importance_excluded_fraction
        ),
        "event_support_tolerance": float(event_support_tolerance),
        "weighted_event_support_tolerance": float(weighted_event_support_tolerance),
        "verdict": support_verdict,
    }


def _component_verdict(support: dict[str, Any], risk: dict[str, Any]) -> str:
    """Verdict for event support + common-support risk, not the full audit."""
    if support["verdict"] == "support_loss" or risk["verdict"] == "premature_compression":
        return "loss_detected"
    if (
        support["verdict"] == "within_support_tolerances"
        and risk["verdict"] == "bounded_risk_adequacy"
    ):
        return "bounded_event_support_and_common_risk"
    return "inconclusive"


def audit_information_cutoff(
    latest_state_time: np.ndarray,
    state_cutoff: float,
    *,
    available: np.ndarray | None = None,
    assay_ready_time: np.ndarray | None = None,
    decision_deadline: float | None = None,
) -> dict[str, Any]:
    """Audit material-state and optional decision-availability cutoffs separately.

    An offline task may assay a specimen after it was arrested, so long as the specimen's state
    time satisfies ``state_cutoff`` and later acquisition remains blinded.  A real-time or
    turnaround claim additionally supplies ``assay_ready_time`` and ``decision_deadline``.
    """
    if not np.isfinite(state_cutoff):
        raise ValueError("state_cutoff must be finite")
    state_times = np.asarray(latest_state_time, dtype=float)
    if state_times.ndim != 1:
        raise ValueError("latest_state_time must be one-dimensional")
    mask = (
        np.ones(state_times.size, dtype=bool)
        if available is None
        else _boolean_mask(available, state_times.size, name="available")
    )
    if decision_deadline is not None:
        if not np.isfinite(decision_deadline):
            raise ValueError("decision_deadline must be finite")
        if decision_deadline < state_cutoff:
            raise ValueError("decision_deadline must not precede state_cutoff")
        if assay_ready_time is None:
            raise ValueError("assay_ready_time is required when decision_deadline is declared")

    assay_times: np.ndarray | None = None
    if assay_ready_time is not None:
        assay_times = np.asarray(assay_ready_time, dtype=float)
        if assay_times.shape != state_times.shape:
            raise ValueError("assay_ready_time must have the same shape as latest_state_time")

    state_violations = np.flatnonzero(
        mask & np.isfinite(state_times) & (state_times > state_cutoff)
    )
    unknown_state = np.flatnonzero(mask & ~np.isfinite(state_times))
    observed_state = state_times[mask & np.isfinite(state_times)]

    if assay_times is None:
        assay_violations = np.array([], dtype=int)
        chronology_violations = np.array([], dtype=int)
        unknown_assay = np.array([], dtype=int)
        observed_assay = np.array([], dtype=float)
    else:
        unknown_assay = np.flatnonzero(mask & ~np.isfinite(assay_times))
        observed_assay = assay_times[mask & np.isfinite(assay_times)]
        assay_violations = (
            np.array([], dtype=int)
            if decision_deadline is None
            else np.flatnonzero(
                mask & np.isfinite(assay_times) & (assay_times > decision_deadline)
            )
        )
        chronology_violations = np.flatnonzero(
            mask
            & np.isfinite(state_times)
            & np.isfinite(assay_times)
            & (assay_times < state_times)
        )

    violations = np.union1d(
        np.union1d(state_violations, assay_violations),
        chronology_violations,
    )
    unknown = np.union1d(unknown_state, unknown_assay)
    if violations.size:
        verdict = "violated"
    elif unknown.size:
        verdict = "unverifiable"
    else:
        verdict = "passed"
    return {
        "state_cutoff": float(state_cutoff),
        "decision_deadline": (
            float(decision_deadline) if decision_deadline is not None else None
        ),
        "operational_mode": (
            "deadline_constrained" if decision_deadline is not None else "offline_sampled_state"
        ),
        "state_time_checked_count": int(observed_state.size),
        "assay_time_checked_count": int(observed_assay.size),
        "violation_count": int(violations.size),
        "violation_indices": violations.tolist(),
        "state_violation_indices": state_violations.tolist(),
        "assay_deadline_violation_indices": assay_violations.tolist(),
        "assay_before_state_violation_indices": chronology_violations.tolist(),
        "unknown_time_count": int(unknown.size),
        "unknown_time_indices": unknown.tolist(),
        "unknown_state_time_indices": unknown_state.tolist(),
        "unknown_assay_time_indices": unknown_assay.tolist(),
        "latest_observed_state_time": (
            float(observed_state.max()) if observed_state.size else None
        ),
        "latest_observed_assay_time": (
            float(observed_assay.max()) if observed_assay.size else None
        ),
        "verdict": verdict,
        "passed": verdict == "passed",
    }


def audit_pair_collisions(
    representation: np.ndarray,
    pairs: np.ndarray,
    *,
    available: np.ndarray | None = None,
    pair_universe: np.ndarray | None = None,
    decision_weights: np.ndarray | None = None,
    decision_support_tolerance: float = 0.0,
    weighted_decision_support_tolerance: float = 0.0,
    collision_tolerance: float | None = None,
    weighted_collision_tolerance: float | None = None,
) -> dict[str, Any]:
    """Measure pair decisions that a representation collapses to identical inputs.

    ``pairs`` contains integer event indices.  Count- and decision-weighted support are separate.
    The pairwise-accuracy ceilings assume a deterministic scorer, perfect ordering on
    non-colliding pairs, and ties worth 0.5.
    """
    values = np.asarray(representation)
    if values.ndim == 0:
        raise ValueError("representation must have one row per event")
    n = values.shape[0]
    pair_indices = np.asarray(pairs)
    if pair_indices.ndim != 2 or pair_indices.shape[1] != 2:
        raise ValueError("pairs must have shape (n_pairs, 2)")
    if not np.issubdtype(pair_indices.dtype, np.integer):
        raise ValueError("pairs must contain integer event indices")
    if pair_indices.size and (pair_indices.min() < 0 or pair_indices.max() >= n):
        raise ValueError("pairs contain an event index outside the representation")
    if pair_indices.size and np.any(pair_indices[:, 0] == pair_indices[:, 1]):
        raise ValueError("pairs must not contain self-comparisons")
    event_available = (
        np.ones(n, dtype=bool)
        if available is None
        else _boolean_mask(available, n, name="available")
    )
    n_pairs = pair_indices.shape[0]
    universe = (
        np.ones(n_pairs, dtype=bool)
        if pair_universe is None
        else _boolean_mask(pair_universe, n_pairs, name="pair_universe")
    )
    for tolerance, name in (
        (decision_support_tolerance, "decision_support_tolerance"),
        (weighted_decision_support_tolerance, "weighted_decision_support_tolerance"),
    ):
        if not np.isfinite(tolerance) or not 0.0 <= tolerance <= 1.0:
            raise ValueError(f"{name} must be finite and lie in [0, 1]")
    for tolerance, name in (
        (collision_tolerance, "collision_tolerance"),
        (weighted_collision_tolerance, "weighted_collision_tolerance"),
    ):
        if tolerance is not None and (
            not np.isfinite(tolerance) or not 0.0 <= tolerance <= 1.0
        ):
            raise ValueError(f"{name} must be finite and lie in [0, 1]")
    weights = _weights(decision_weights, n_pairs, name="decision_weights")

    valid_rows = _valid_representation_rows(values)
    if not np.all(valid_rows[event_available]):
        raise ValueError("representation has a missing or non-finite value on an available event")

    left_indices, right_indices = pair_indices[:, 0], pair_indices[:, 1]
    representable = universe & event_available[left_indices] & event_available[right_indices]
    if values.ndim == 1:
        identical = values[left_indices] == values[right_indices]
    else:
        identical = np.all(
            values[left_indices] == values[right_indices],
            axis=tuple(range(1, values.ndim)),
        )
    collisions = representable & identical
    universe_weight = float(np.sum(weights[universe]))
    if decision_count := int(universe.sum()):
        if universe_weight <= 0.0:
            raise ValueError("decision_weights must have positive total weight in pair_universe")
    representable_weight = float(np.sum(weights[representable]))
    collision_weight = float(np.sum(weights[collisions]))
    representable_count = int(representable.sum())
    decision_coverage = representable_count / decision_count if decision_count else None
    decision_weight_coverage = (
        representable_weight / universe_weight if universe_weight > 0.0 else None
    )
    decision_support_loss = (
        1.0 - decision_coverage if decision_coverage is not None else None
    )
    weighted_decision_support_loss = (
        1.0 - decision_weight_coverage if decision_weight_coverage is not None else None
    )
    if decision_support_loss is None or weighted_decision_support_loss is None:
        support_verdict = "not_estimable"
    elif (
        decision_support_loss > decision_support_tolerance
        or weighted_decision_support_loss > weighted_decision_support_tolerance
    ):
        support_verdict = "decision_support_loss"
    else:
        support_verdict = "within_decision_support_tolerances"
    weighted_collision_rate = (
        collision_weight / representable_weight if representable_weight > 0.0 else None
    )
    collision_rate = (
        float(collisions.sum() / representable.sum()) if representable.any() else None
    )
    if collision_tolerance is None and weighted_collision_tolerance is None:
        collision_verdict = "not_declared"
    elif (
        (collision_tolerance is not None and collision_rate is None)
        or (weighted_collision_tolerance is not None and weighted_collision_rate is None)
    ):
        collision_verdict = "not_estimable"
    elif (
        collision_tolerance is not None
        and collision_rate is not None
        and collision_rate > collision_tolerance
    ) or (
        weighted_collision_tolerance is not None
        and weighted_collision_rate is not None
        and weighted_collision_rate > weighted_collision_tolerance
    ):
        collision_verdict = "collision_bound_exceeded"
    else:
        collision_verdict = "within_collision_tolerance"
    return {
        "decision_count": decision_count,
        "representable_decision_count": representable_count,
        "decision_coverage": decision_coverage,
        "decision_weight_coverage": decision_weight_coverage,
        "decision_support_loss_fraction": decision_support_loss,
        "decision_weight_support_loss_fraction": weighted_decision_support_loss,
        "decision_support_tolerance": float(decision_support_tolerance),
        "weighted_decision_support_tolerance": float(
            weighted_decision_support_tolerance
        ),
        "decision_support_verdict": support_verdict,
        "collision_count": int(collisions.sum()),
        "collision_rate_on_representable_decisions": collision_rate,
        "decision_weighted_collision_rate": weighted_collision_rate,
        "collision_tolerance": (
            float(collision_tolerance) if collision_tolerance is not None else None
        ),
        "weighted_collision_tolerance": (
            float(weighted_collision_tolerance)
            if weighted_collision_tolerance is not None
            else None
        ),
        "collision_verdict": collision_verdict,
        "pairwise_accuracy_ceiling_if_noncollisions_perfect": (
            1.0 - 0.5 * collision_rate
            if collision_rate is not None
            else None
        ),
        "decision_weighted_pairwise_accuracy_ceiling_if_noncollisions_perfect": (
            1.0 - 0.5 * weighted_collision_rate
            if weighted_collision_rate is not None
            else None
        ),
    }


def audit_compression_pair(
    y_true: np.ndarray,
    compressed: PredictionArm,
    reference: PredictionArm,
    *,
    loss: LossFunction,
    metric_name: str,
    risk_tolerance: float,
    clusters: np.ndarray,
    aggregate: RiskAggregator = mean_risk,
    compact_advantage_tolerance: float | None = None,
    event_support_tolerance: float = 0.0,
    weighted_event_support_tolerance: float = 0.0,
    universe: np.ndarray | None = None,
    sample_weights: np.ndarray | None = None,
    event_importance_weights: np.ndarray | None = None,
    environments: np.ndarray | None = None,
    transfer_rule: str | None = None,
    environment_evaluation: str = "descriptive_slices",
    seed: int = 0,
    n_boot: int = 2000,
) -> dict[str, Any]:
    """Compare a compressed arm with a richer reference on risk and support.

    Predictions must be genuinely out of fold (or fixed without fitting).  The function
    cannot infer that property from arrays, so callers must record the cross-fitting scheme
    in each arm's metadata and run manifest.
    """
    truth = np.asarray(y_true)
    if truth.ndim != 1:
        raise ValueError("y_true must be one-dimensional")
    n = truth.size
    if not np.isfinite(risk_tolerance) or risk_tolerance < 0.0:
        raise ValueError("risk_tolerance must be finite and non-negative")
    if compact_advantage_tolerance is not None and (
        not np.isfinite(compact_advantage_tolerance) or compact_advantage_tolerance < 0.0
    ):
        raise ValueError("compact_advantage_tolerance must be finite and non-negative")
    if not 0.0 <= event_support_tolerance <= 1.0:
        raise ValueError("event_support_tolerance must lie in [0, 1]")
    if not 0.0 <= weighted_event_support_tolerance <= 1.0:
        raise ValueError("weighted_event_support_tolerance must lie in [0, 1]")
    if n_boot <= 0:
        raise ValueError("n_boot must be positive")
    if transfer_rule not in (None, "all_environments"):
        raise ValueError("transfer_rule must be None or 'all_environments'")
    if transfer_rule is not None and environments is None:
        raise ValueError("a transfer_rule requires environment labels")
    if environment_evaluation not in ("descriptive_slices", "held_out_environment"):
        raise ValueError(
            "environment_evaluation must be 'descriptive_slices' or 'held_out_environment'"
        )
    if transfer_rule is not None and environment_evaluation != "held_out_environment":
        raise ValueError(
            "a transfer_rule requires predictions from a declared held_out_environment design"
        )

    compressed_predictions = np.asarray(compressed.predictions)
    reference_predictions = np.asarray(reference.predictions)
    compressed_available = _availability(compressed, n)
    reference_available = _availability(reference, n)
    universe_mask = (
        np.ones(n, dtype=bool)
        if universe is None
        else _boolean_mask(universe, n, name="universe")
    )
    row_weights = _weights(sample_weights, n, name="sample_weights")
    if np.any(row_weights[universe_mask] <= 0.0):
        raise ValueError("sample_weights must be strictly positive in the declared universe")
    event_importance = _weights(
        event_importance_weights,
        n,
        name="event_importance_weights",
    )
    raw_cluster_values = np.asarray(clusters)
    if raw_cluster_values.shape != (n,):
        raise ValueError(f"clusters must have shape ({n},)")
    cluster_values = _encode_labels(
        raw_cluster_values,
        universe_mask,
        name="clusters",
    )

    if not np.all(_finite_rows(truth)[universe_mask]):
        raise ValueError("y_true contains a non-finite value in the declared universe")
    compressed_eligible = universe_mask & compressed_available
    reference_eligible = universe_mask & reference_available
    if not np.all(_finite_rows(compressed_predictions)[compressed_eligible]):
        raise ValueError("compressed arm has a non-finite prediction on an available event")
    if not np.all(_finite_rows(reference_predictions)[reference_eligible]):
        raise ValueError("reference arm has a non-finite prediction on an available event")
    compressed_loss = _evaluate_arm_loss(
        loss,
        truth,
        compressed_predictions,
        compressed_eligible,
        arm_name="compressed",
    )
    reference_loss = _evaluate_arm_loss(
        loss,
        truth,
        reference_predictions,
        reference_eligible,
        arm_name="reference",
    )
    common = universe_mask & compressed_available & reference_available

    support = _support_result(
        universe_mask,
        compressed_available,
        reference_available,
        event_importance,
        event_support_tolerance=event_support_tolerance,
        weighted_event_support_tolerance=weighted_event_support_tolerance,
    )

    risk = _risk_result(
        compressed_loss,
        reference_loss,
        common,
        row_weights,
        cluster_values,
        aggregate=aggregate,
        risk_tolerance=risk_tolerance,
        compact_advantage_tolerance=compact_advantage_tolerance,
        seed=seed,
        n_boot=n_boot,
    )

    environment_results: dict[str, Any] = {}
    if environments is not None:
        raw_environment_values = np.asarray(environments)
        if raw_environment_values.shape != (n,):
            raise ValueError(f"environments must have shape ({n},)")
        environment_values = _encode_labels(
            raw_environment_values,
            universe_mask,
            name="environments",
        )
        unique_environments = list(dict.fromkeys(environment_values[universe_mask].tolist()))
        if transfer_rule is not None and len(unique_environments) < 2:
            raise ValueError("a transfer_rule requires at least two represented environments")
        for value in unique_environments:
            in_environment = universe_mask & (environment_values == value)
            environment_results[str(value)] = {
                "support": _support_result(
                    in_environment,
                    compressed_available,
                    reference_available,
                    event_importance,
                    event_support_tolerance=event_support_tolerance,
                    weighted_event_support_tolerance=weighted_event_support_tolerance,
                ),
                "common_support_risk": _risk_result(
                    compressed_loss,
                    reference_loss,
                    common & in_environment,
                    row_weights,
                    cluster_values,
                    aggregate=aggregate,
                    risk_tolerance=risk_tolerance,
                    compact_advantage_tolerance=compact_advantage_tolerance,
                    seed=seed,
                    n_boot=n_boot,
                ),
            }
            environment_results[str(value)]["component_verdict"] = _component_verdict(
                environment_results[str(value)]["support"],
                environment_results[str(value)]["common_support_risk"],
            )

    pooled_component_verdict = _component_verdict(support, risk)
    per_environment = [result["component_verdict"] for result in environment_results.values()]
    if environments is None:
        environment_consistency_verdict = "not_evaluated"
    elif len(environment_results) < 2:
        environment_consistency_verdict = "not_estimable"
    elif all(verdict == "loss_detected" for verdict in per_environment):
        environment_consistency_verdict = "loss_detected_in_every_observed_environment"
    elif all(
        verdict == "bounded_event_support_and_common_risk" for verdict in per_environment
    ):
        environment_consistency_verdict = (
            "bounded_event_support_and_common_risk_in_every_observed_environment"
        )
    else:
        environment_consistency_verdict = "inconclusive_or_heterogeneous"

    if environments is None:
        transfer_verdict = "not_evaluated"
    elif transfer_rule is None:
        transfer_verdict = "not_declared"
    elif len(environment_results) < 2:
        transfer_verdict = "not_estimable"
    elif environment_consistency_verdict == "loss_detected_in_every_observed_environment":
        transfer_verdict = "loss_detected_in_every_held_out_environment"
    elif environment_consistency_verdict.startswith("bounded_event_support"):
        transfer_verdict = (
            "bounded_event_support_and_common_risk_in_every_held_out_environment"
        )
    else:
        transfer_verdict = "inconclusive_or_heterogeneous_across_held_out_environments"

    return {
        "task": "task_relevant_compression_audit",
        "compressed_arm": compressed.name,
        "reference_arm": reference.name,
        "metric": metric_name,
        "risk_aggregation": getattr(aggregate, "__name__", repr(aggregate)),
        "positive_gap_means": "reference representation has lower task risk",
        "risk_tolerance": float(risk_tolerance),
        "compact_advantage_tolerance": (
            float(compact_advantage_tolerance)
            if compact_advantage_tolerance is not None
            else None
        ),
        "support": support,
        "common_support_risk": risk,
        "environment_results": environment_results,
        "environment_evaluation": environment_evaluation,
        "environment_consistency_verdict": environment_consistency_verdict,
        "pooled_component_verdict": pooled_component_verdict,
        "transfer_rule": transfer_rule,
        "transfer_verdict": transfer_verdict,
        "full_audit_verdict": "not_computed",
        "component_scope": "Event support and common-support risk only; decision support, "
        "collisions, and any deployment utility must be audited separately.",
        "qualifier": "Verdict is specific to the declared task, environments, model "
        "families, cross-fitting protocol, and data scale.",
        "arm_metadata": {
            compressed.name: compressed.metadata,
            reference.name: reference.metadata,
        },
    }


def audit_prediction_bundle(
    y_true: np.ndarray,
    arms: dict[str, PredictionArm],
    comparisons: list[tuple[str, str]],
    **audit_kwargs: Any,
) -> dict[str, Any]:
    """Run several declared compressed→reference comparisons over one prediction bundle."""
    results: dict[str, Any] = {}
    for compressed_name, reference_name in comparisons:
        if compressed_name not in arms or reference_name not in arms:
            raise KeyError(f"unknown comparison: {compressed_name!r} -> {reference_name!r}")
        key = f"{compressed_name}__to__{reference_name}"
        results[key] = audit_compression_pair(
            y_true,
            arms[compressed_name],
            arms[reference_name],
            **audit_kwargs,
        )
    return {
        "task": "task_relevant_compression_audit_bundle",
        "comparisons": results,
    }
