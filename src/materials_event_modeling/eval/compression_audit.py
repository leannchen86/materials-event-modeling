"""Task-relevant compression audits over out-of-fold predictions.

The evaluator deliberately starts *after* model fitting.  A materials task decides which
models, features, and cross-fitting scheme are credible; this module standardizes the part
that should not vary between tasks:

* risk on the events both representations can express,
* event and decision-weighted support loss,
* paired cluster-bootstrap uncertainty,
* environment-specific diagnostics, and
* bounded-adequacy versus premature-compression verdicts.

Positive risk gaps mean the richer/reference representation has lower loss.  A risk result
never repairs missing support: a compressed representation that drops failed or censored
events can look excellent on the selected rows that remain, so support and risk are always
reported separately.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
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
    available = np.asarray(arm.available, dtype=bool)
    if available.shape != (n,):
        raise ValueError(f"arm {arm.name!r} availability must have shape ({n},)")
    return available


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


def _label_token(value: object, *, name: str) -> str:
    if value is None or (
        isinstance(value, (float, np.floating)) and not np.isfinite(value)
    ):
        raise ValueError(f"{name} contains a missing or non-finite label")
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


def mean_risk(losses: np.ndarray, weights: np.ndarray) -> float:
    """Weighted arithmetic mean for additive per-example losses."""
    return _weighted_mean(losses, weights)


def root_mean_risk(squared_losses: np.ndarray, weights: np.ndarray) -> float:
    """Root weighted mean, used with per-example squared errors to obtain RMSE."""
    mean = _weighted_mean(squared_losses, weights)
    if mean < 0.0:
        raise ValueError("root_mean_risk requires non-negative per-example losses")
    return float(np.sqrt(mean))


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
        statistics.append(
            aggregate(compressed_loss[draw], weights[draw])
            - aggregate(reference_loss[draw], weights[draw])
        )
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
    if high < -risk_tolerance:
        return "compressed_representation_better"
    if high <= risk_tolerance:
        return "bounded_risk_adequacy"
    return "inconclusive"


def _risk_result(
    compressed_loss: np.ndarray,
    reference_loss: np.ndarray,
    mask: np.ndarray,
    sample_weights: np.ndarray,
    clusters: np.ndarray,
    *,
    aggregate: RiskAggregator,
    risk_tolerance: float,
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
    compressed_risk = aggregate(compressed, weights)
    reference_risk = aggregate(reference, weights)
    if not np.isfinite(compressed_risk) or not np.isfinite(reference_risk):
        raise ValueError("risk aggregate must return a finite scalar")
    return {
        "common_support_count": int(selected.size),
        "compressed_risk": compressed_risk,
        "reference_risk": reference_risk,
        "risk_gap_compressed_minus_reference": compressed_risk - reference_risk,
        "risk_gap_ci95": ci95,
        "verdict": _risk_verdict(ci95, risk_tolerance),
    }


def _support_result(
    universe_mask: np.ndarray,
    compressed_available: np.ndarray,
    reference_available: np.ndarray,
    decision_weights: np.ndarray,
    *,
    event_support_tolerance: float,
    decision_support_tolerance: float,
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
    decision_reference_weight = float(np.sum(decision_weights[reference_population]))
    decision_excluded_weight = float(np.sum(decision_weights[excluded]))
    decision_universe_weight = float(np.sum(decision_weights[universe_mask]))
    compressed_decision_missing_weight = float(np.sum(decision_weights[compressed_missing]))
    decision_excluded_fraction = (
        decision_excluded_weight / decision_reference_weight
        if decision_reference_weight > 0.0
        else None
    )
    support_exceeds_margin = (
        (
            universe_mask.any()
            and compressed_missing.sum() / universe_mask.sum() > event_support_tolerance
        )
        or (
            decision_universe_weight > 0.0
            and compressed_decision_missing_weight / decision_universe_weight
            > decision_support_tolerance
        )
    )
    universe_count = int(universe_mask.sum())
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
        "compressed_event_support_loss_fraction": (
            float(compressed_missing.sum() / universe_count) if universe_count else None
        ),
        "reference_event_support_loss_fraction": (
            float(reference_missing.sum() / universe_count) if universe_count else None
        ),
        "compressed_decision_weight_support_loss_fraction": (
            compressed_decision_missing_weight / decision_universe_weight
            if decision_universe_weight > 0.0
            else None
        ),
        "events_excluded_by_compression_count": int(excluded.sum()),
        "events_excluded_by_compression_fraction_of_reference": relative_excluded_fraction,
        "decision_weight_excluded_by_compression": decision_excluded_weight,
        "decision_weight_excluded_by_compression_fraction_of_reference": (
            decision_excluded_fraction
        ),
        "event_support_tolerance": float(event_support_tolerance),
        "decision_support_tolerance": float(decision_support_tolerance),
        "verdict": "support_loss" if support_exceeds_margin else "within_support_tolerances",
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
    if (
        support["verdict"] == "within_support_tolerances"
        and risk["verdict"] == "compressed_representation_better"
    ):
        return "compressed_representation_better_on_common_support"
    return "inconclusive"


def audit_information_cutoff(
    latest_input_time: np.ndarray,
    cutoff: float,
    *,
    available: np.ndarray | None = None,
) -> dict[str, Any]:
    """Check that a representation consumed no information created after its cutoff."""
    if not np.isfinite(cutoff):
        raise ValueError("cutoff must be finite")
    times = np.asarray(latest_input_time, dtype=float)
    if times.ndim != 1:
        raise ValueError("latest_input_time must be one-dimensional")
    mask = np.ones(times.size, dtype=bool) if available is None else np.asarray(available, bool)
    if mask.shape != times.shape:
        raise ValueError("available must have the same shape as latest_input_time")
    violations = np.flatnonzero(mask & np.isfinite(times) & (times > cutoff))
    unknown = np.flatnonzero(mask & ~np.isfinite(times))
    observed = times[mask & np.isfinite(times)]
    if violations.size:
        verdict = "violated"
    elif unknown.size:
        verdict = "unverifiable"
    else:
        verdict = "passed"
    return {
        "cutoff": float(cutoff),
        "checked_count": int(observed.size),
        "violation_count": int(violations.size),
        "violation_indices": violations.tolist(),
        "unknown_time_count": int(unknown.size),
        "unknown_time_indices": unknown.tolist(),
        "latest_observed_input_time": float(observed.max()) if observed.size else None,
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
) -> dict[str, Any]:
    """Measure pair decisions that a representation collapses to identical inputs.

    ``pairs`` contains integer event indices.  The reported pairwise-accuracy ceiling assumes a
    deterministic scorer, perfect ordering on non-colliding pairs, and ties worth 0.5.
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
    event_available = (
        np.ones(n, dtype=bool) if available is None else np.asarray(available, dtype=bool)
    )
    if event_available.shape != (n,):
        raise ValueError(f"available must have shape ({n},)")
    n_pairs = pair_indices.shape[0]
    universe = (
        np.ones(n_pairs, dtype=bool)
        if pair_universe is None
        else np.asarray(pair_universe, dtype=bool)
    )
    if universe.shape != (n_pairs,):
        raise ValueError(f"pair_universe must have shape ({n_pairs},)")
    weights = _weights(decision_weights, n_pairs, name="decision_weights")

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
    representable_weight = float(np.sum(weights[representable]))
    collision_weight = float(np.sum(weights[collisions]))
    weighted_collision_rate = (
        collision_weight / representable_weight if representable_weight > 0.0 else None
    )
    return {
        "decision_count": int(universe.sum()),
        "representable_decision_count": int(representable.sum()),
        "decision_coverage": (
            representable_weight / universe_weight if universe_weight > 0.0 else None
        ),
        "collision_count": int(collisions.sum()),
        "collision_rate_on_representable_decisions": (
            float(collisions.sum() / representable.sum()) if representable.any() else None
        ),
        "decision_weighted_collision_rate": weighted_collision_rate,
        "pairwise_accuracy_ceiling_if_noncollisions_perfect": (
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
    aggregate: RiskAggregator = mean_risk,
    metric_name: str,
    risk_tolerance: float,
    clusters: np.ndarray,
    event_support_tolerance: float = 0.0,
    decision_support_tolerance: float = 0.0,
    universe: np.ndarray | None = None,
    sample_weights: np.ndarray | None = None,
    decision_weights: np.ndarray | None = None,
    environments: np.ndarray | None = None,
    transfer_rule: str | None = None,
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
    if not 0.0 <= event_support_tolerance <= 1.0:
        raise ValueError("event_support_tolerance must lie in [0, 1]")
    if not 0.0 <= decision_support_tolerance <= 1.0:
        raise ValueError("decision_support_tolerance must lie in [0, 1]")
    if n_boot <= 0:
        raise ValueError("n_boot must be positive")
    if transfer_rule not in (None, "all_environments"):
        raise ValueError("transfer_rule must be None or 'all_environments'")

    compressed_predictions = np.asarray(compressed.predictions)
    reference_predictions = np.asarray(reference.predictions)
    compressed_available = _availability(compressed, n)
    reference_available = _availability(reference, n)
    universe_mask = (
        np.ones(n, dtype=bool) if universe is None else np.asarray(universe, dtype=bool)
    )
    if universe_mask.shape != (n,):
        raise ValueError(f"universe must have shape ({n},)")
    row_weights = _weights(
        sample_weights,
        n,
        name="sample_weights",
        allow_zero=False,
    )
    decision = _weights(decision_weights, n, name="decision_weights")
    raw_cluster_values = np.asarray(clusters)
    if raw_cluster_values.shape != (n,):
        raise ValueError(f"clusters must have shape ({n},)")
    cluster_values = _encode_labels(
        raw_cluster_values,
        universe_mask,
        name="clusters",
    )

    compressed_loss = np.asarray(loss(truth, compressed_predictions), dtype=float)
    reference_loss = np.asarray(loss(truth, reference_predictions), dtype=float)
    if compressed_loss.shape != (n,) or reference_loss.shape != (n,):
        raise ValueError("loss must return one value per example")
    if not np.all(_finite_rows(truth)[universe_mask]):
        raise ValueError("y_true contains a non-finite value in the declared universe")
    compressed_eligible = universe_mask & compressed_available
    reference_eligible = universe_mask & reference_available
    if not np.all(_finite_rows(compressed_predictions)[compressed_eligible]):
        raise ValueError("compressed arm has a non-finite prediction on an available event")
    if not np.all(_finite_rows(reference_predictions)[reference_eligible]):
        raise ValueError("reference arm has a non-finite prediction on an available event")
    if not np.all(np.isfinite(compressed_loss[compressed_eligible])):
        raise ValueError("compressed arm has a non-finite loss on an available event")
    if not np.all(np.isfinite(reference_loss[reference_eligible])):
        raise ValueError("reference arm has a non-finite loss on an available event")
    common = universe_mask & compressed_available & reference_available

    support = _support_result(
        universe_mask,
        compressed_available,
        reference_available,
        decision,
        event_support_tolerance=event_support_tolerance,
        decision_support_tolerance=decision_support_tolerance,
    )

    risk = _risk_result(
        compressed_loss,
        reference_loss,
        common,
        row_weights,
        cluster_values,
        aggregate=aggregate,
        risk_tolerance=risk_tolerance,
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
        for value in unique_environments:
            in_environment = universe_mask & (environment_values == value)
            environment_results[str(value)] = {
                "support": _support_result(
                    in_environment,
                    compressed_available,
                    reference_available,
                    decision,
                    event_support_tolerance=event_support_tolerance,
                    decision_support_tolerance=decision_support_tolerance,
                ),
                "common_support_risk": _risk_result(
                    compressed_loss,
                    reference_loss,
                    common & in_environment,
                    row_weights,
                    cluster_values,
                    aggregate=aggregate,
                    risk_tolerance=risk_tolerance,
                    seed=seed,
                    n_boot=n_boot,
                ),
            }
            environment_results[str(value)]["component_verdict"] = _component_verdict(
                environment_results[str(value)]["support"],
                environment_results[str(value)]["common_support_risk"],
            )

    pooled_component_verdict = _component_verdict(support, risk)
    if environments is None:
        transfer_verdict = "not_evaluated"
    elif transfer_rule is None:
        transfer_verdict = "not_declared"
    elif len(environment_results) < 2:
        transfer_verdict = "not_estimable"
    else:
        per_environment = [
            result["component_verdict"] for result in environment_results.values()
        ]
        if all(verdict == "loss_detected" for verdict in per_environment):
            transfer_verdict = "loss_detected_in_every_environment"
        elif all(
            verdict == "bounded_event_support_and_common_risk"
            for verdict in per_environment
        ):
            transfer_verdict = "bounded_event_support_and_common_risk_in_every_environment"
        elif all(
            verdict == "compressed_representation_better_on_common_support"
            for verdict in per_environment
        ):
            transfer_verdict = "compressed_representation_better_in_every_environment"
        else:
            transfer_verdict = "inconclusive_or_heterogeneous"

    return {
        "task": "task_relevant_compression_audit",
        "compressed_arm": compressed.name,
        "reference_arm": reference.name,
        "metric": metric_name,
        "risk_aggregation": getattr(aggregate, "__name__", repr(aggregate)),
        "positive_gap_means": "reference representation has lower task risk",
        "risk_tolerance": float(risk_tolerance),
        "support": support,
        "common_support_risk": risk,
        "environment_results": environment_results,
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
