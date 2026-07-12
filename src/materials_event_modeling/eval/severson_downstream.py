"""Frozen helpers for the retrospective Severson downstream-compression dry run.

This module owns feature construction and nested held-batch prediction only.  It does not
interpret results or call the generic compression-audit evaluator.  In particular, target
eligibility is supplied to :func:`held_batch_oof` by the caller so the primary analysis and
the all-observed-EOL sensitivity refit every scaler, hyperparameter choice, and ridge model.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

X100_CYCLES = np.arange(2, 101, dtype=int)
CONTEXT_KEYS = (
    "cell.charge_c_rate_1",
    "cell.soc_switch_percent",
    "cell.charge_c_rate_2",
)
S100_NAMES = (
    "mean_capacity",
    "capacity_cycle_100",
    "ols_slope_cycles_2_100",
    "maximum_minus_final",
    "final_minus_first",
    "ols_slope_cycles_51_100",
    "log10_variance_first_differences",
)
ARM_NAMES = ("C", "C_S100", "C_X100", "C_S100_X100")
RIDGE_ALPHAS = (1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0, 1000.0)

_ARM_WIDTHS = {
    "C": len(CONTEXT_KEYS),
    "C_S100": len(CONTEXT_KEYS) + len(S100_NAMES),
    "C_X100": len(CONTEXT_KEYS) + X100_CYCLES.size,
    "C_S100_X100": len(CONTEXT_KEYS) + len(S100_NAMES) + X100_CYCLES.size,
}


@dataclass(frozen=True)
class X100Extraction:
    """One fixed-grid early discharge-capacity trace and its support metadata."""

    values: np.ndarray
    observed_mask: np.ndarray
    available: bool
    reason: str
    interpolated_cycles: tuple[int, ...]
    accepted_cycle_count: int
    rejected_cycle_count: int


@dataclass(frozen=True)
class DownstreamRow:
    """One physical-cell attempt, including inputs and separately recorded target support."""

    event_id: str
    policy: str
    batch: str
    context: np.ndarray
    context_available: bool
    context_reason: str
    target_status: str
    target_exact: bool
    cycle_life: float | None
    log_cycle_life: float | None
    life_lower_bound: float | None
    continuation_batches: tuple[str, ...]
    cross_batch_target_provenance: bool
    x100: np.ndarray
    s100: np.ndarray
    x100_available: bool
    x100_reason: str
    observed_mask: np.ndarray
    interpolated_cycles: tuple[int, ...]
    accepted_cycle_count: int
    rejected_cycle_count: int


@dataclass(frozen=True)
class FeatureBundle:
    """Aligned feature matrices plus representational availability for every arm."""

    matrices: dict[str, np.ndarray]
    available: dict[str, np.ndarray]
    reasons: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class AlphaSelection:
    """Policy-grouped inner-CV result; metadata contains JSON-serializable scalars."""

    selected_alpha: float
    candidate_scores: tuple[dict[str, Any], ...]
    n_splits: int
    folds: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class HeldBatchOOFResult:
    """Strictly held-batch predictions and enough fit state to audit every refit."""

    predictions: dict[str, np.ndarray]
    analysis_eligible: np.ndarray
    features: FeatureBundle
    folds: tuple[dict[str, Any], ...]
    metadata: dict[str, Any]


def _unavailable_x100(
    reason: str,
    *,
    observed_mask: np.ndarray | None = None,
    accepted_cycle_count: int = 0,
    rejected_cycle_count: int = 0,
) -> X100Extraction:
    mask = (
        np.zeros(X100_CYCLES.size, dtype=bool)
        if observed_mask is None
        else np.asarray(observed_mask, dtype=bool)
    )
    return X100Extraction(
        values=np.full(X100_CYCLES.size, np.nan, dtype=float),
        observed_mask=mask,
        available=False,
        reason=reason,
        interpolated_cycles=(),
        accepted_cycle_count=int(accepted_cycle_count),
        rejected_cycle_count=int(rejected_cycle_count),
    )


def _cycle_index(observation: dict[str, Any]) -> int | None:
    value = observation.get("cycle_index")
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(numeric) or not numeric.is_integer():
        return None
    return int(numeric)


def extract_x100(event: dict[str, Any]) -> X100Extraction:
    """Construct QDischarge cycles 2--100 after filtering rejected observations.

    Only accepted cycling observations inside the cutoff are inspected for capacity values.
    Consequently, neither a rejected point nor a post-cutoff value can become an interpolation
    anchor.  Missing interior values are linearly interpolated within the same cell; missing
    endpoints, duplicates, or malformed accepted values make the representation unavailable.
    """
    accepted: dict[int, float] = {}
    rejected_count = 0
    for raw_observation in event.get("observations", []):
        if not isinstance(raw_observation, dict):
            continue
        observation = raw_observation
        if observation.get("modality") != "cycling":
            continue
        cycle = _cycle_index(observation)
        if cycle is None or cycle < int(X100_CYCLES[0]) or cycle > int(X100_CYCLES[-1]):
            continue
        if observation.get("include_in_raw_objective") is False:
            rejected_count += 1
            continue
        if cycle in accepted:
            mask = np.isin(X100_CYCLES, list(accepted))
            return _unavailable_x100(
                "duplicate_accepted_cycle",
                observed_mask=mask,
                accepted_cycle_count=len(accepted),
                rejected_cycle_count=rejected_count,
            )
        try:
            value = float(observation["payload"]["cycling"]["qdischarge_ah"])
        except (KeyError, TypeError, ValueError):
            mask = np.isin(X100_CYCLES, list(accepted))
            return _unavailable_x100(
                "malformed_accepted_qdischarge",
                observed_mask=mask,
                accepted_cycle_count=len(accepted),
                rejected_cycle_count=rejected_count,
            )
        if not np.isfinite(value):
            mask = np.isin(X100_CYCLES, list(accepted))
            return _unavailable_x100(
                "nonfinite_accepted_qdischarge",
                observed_mask=mask,
                accepted_cycle_count=len(accepted),
                rejected_cycle_count=rejected_count,
            )
        accepted[cycle] = value

    observed_mask = np.isin(X100_CYCLES, list(accepted))
    missing_start = int(X100_CYCLES[0]) not in accepted
    missing_end = int(X100_CYCLES[-1]) not in accepted
    if missing_start and missing_end:
        reason = "missing_cycles_2_and_100"
    elif missing_start:
        reason = "missing_cycle_2"
    elif missing_end:
        reason = "missing_cycle_100"
    else:
        reason = ""
    if reason:
        return _unavailable_x100(
            reason,
            observed_mask=observed_mask,
            accepted_cycle_count=len(accepted),
            rejected_cycle_count=rejected_count,
        )

    observed_cycles = np.array(sorted(accepted), dtype=int)
    observed_values = np.array([accepted[cycle] for cycle in observed_cycles], dtype=float)
    values = np.interp(X100_CYCLES, observed_cycles, observed_values)
    if not np.all(np.isfinite(values)):
        return _unavailable_x100(
            "interpolation_produced_nonfinite_values",
            observed_mask=observed_mask,
            accepted_cycle_count=len(accepted),
            rejected_cycle_count=rejected_count,
        )
    interpolated = tuple(int(value) for value in X100_CYCLES[~observed_mask])
    return X100Extraction(
        values=np.asarray(values, dtype=float),
        observed_mask=observed_mask,
        available=True,
        reason="available_interpolated" if interpolated else "available_complete_grid",
        interpolated_cycles=interpolated,
        accepted_cycle_count=len(accepted),
        rejected_cycle_count=rejected_count,
    )


def summarize_x100(x100: np.ndarray) -> np.ndarray:
    """Return the frozen seven-scalar deterministic summary of one X100 vector."""
    values = np.asarray(x100, dtype=float)
    if values.shape != (X100_CYCLES.size,):
        raise ValueError(f"x100 must have shape ({X100_CYCLES.size},)")
    if not np.all(np.isfinite(values)):
        raise ValueError("x100 must contain only finite values")
    late = slice(49, 99)  # cycles 51--100 on the cycles-2--100 grid
    return np.array(
        [
            float(np.mean(values)),
            float(values[-1]),
            float(np.polyfit(X100_CYCLES, values, 1)[0]),
            float(np.max(values) - values[-1]),
            float(values[-1] - values[0]),
            float(np.polyfit(X100_CYCLES[late], values[late], 1)[0]),
            float(np.log10(np.var(np.diff(values), ddof=0) + 1e-12)),
        ],
        dtype=float,
    )


def _context(event: dict[str, Any]) -> tuple[np.ndarray, bool, str]:
    try:
        planned = event["intent"]["planned"]
        context = np.array([float(planned[key]) for key in CONTEXT_KEYS], dtype=float)
    except (KeyError, TypeError, ValueError):
        return np.full(len(CONTEXT_KEYS), np.nan), False, "missing_or_malformed_context"
    if not np.all(np.isfinite(context)):
        return context, False, "nonfinite_context"
    return context, True, "available"


def _accepted_last_cycle(event: dict[str, Any]) -> float | None:
    cycles: list[int] = []
    for observation in event.get("observations", []):
        if not isinstance(observation, dict):
            continue
        if observation.get("modality") != "cycling":
            continue
        if observation.get("include_in_raw_objective") is False:
            continue
        cycle = _cycle_index(observation)
        if cycle is not None:
            cycles.append(cycle)
    return float(max(cycles)) if cycles else None


def _target(event: dict[str, Any]) -> tuple[str, bool, float | None, float | None, float | None]:
    outcome = event.get("outcome") or {}
    status = outcome.get("status")
    summary = outcome.get("summary") or {}
    raw_cycle_life = summary.get("cell.cycle_life_cycles")
    if status == "success":
        if raw_cycle_life is None:
            raise ValueError("a successful event must have a numeric cycle-life target")
        try:
            cycle_life = float(raw_cycle_life)
        except (TypeError, ValueError) as exc:
            raise ValueError("a successful event must have a numeric cycle-life target") from exc
        if not np.isfinite(cycle_life) or cycle_life <= 0.0:
            raise ValueError("a successful event must have a finite positive cycle-life target")
        return "observed_eol", True, cycle_life, float(np.log10(cycle_life)), None
    if summary.get("cell.record_truncated") is True:
        last_cycle = _accepted_last_cycle(event)
        lower_bound = last_cycle + 1.0 if last_cycle is not None else None
        return "right_censored", False, None, None, lower_bound
    return f"unavailable_{status or 'unknown'}", False, None, None, None


def _continuation_batches(event: dict[str, Any]) -> tuple[str, ...]:
    source_ref = event.get("source_ref") or {}
    raw = source_ref.get("merged_from_batches")
    if raw is None:
        return ()
    if not isinstance(raw, list) or not all(isinstance(value, str) and value for value in raw):
        raise ValueError("source_ref.merged_from_batches must be null or a list of batch labels")
    return tuple(raw)


def load_downstream_rows(path: Path) -> list[DownstreamRow]:
    """Load all attempt rows without using target or provenance fields as features."""
    raw_events = json.loads(path.read_text())
    if not isinstance(raw_events, list):
        raise ValueError("Severson event file must contain a JSON list")
    rows: list[DownstreamRow] = []
    seen_ids: set[str] = set()
    for raw_event in raw_events:
        if not isinstance(raw_event, dict):
            raise ValueError("every Severson event must be a JSON object")
        event = raw_event
        event_id = event.get("event_id")
        policy = (event.get("intent") or {}).get("event_group_id")
        batch = (event.get("provenance") or {}).get("batch_id")
        for value, name in ((event_id, "event_id"), (policy, "policy"), (batch, "batch")):
            if not isinstance(value, str) or not value:
                raise ValueError(f"every event must have a non-empty {name}")
        assert isinstance(event_id, str)
        assert isinstance(policy, str)
        assert isinstance(batch, str)
        if event_id in seen_ids:
            raise ValueError(f"duplicate event_id: {event_id}")
        seen_ids.add(event_id)

        context, context_available, context_reason = _context(event)
        extraction = extract_x100(event)
        s100 = (
            summarize_x100(extraction.values)
            if extraction.available
            else np.full(len(S100_NAMES), np.nan, dtype=float)
        )
        target_status, target_exact, cycle_life, log_cycle_life, lower_bound = _target(event)
        continuation_batches = _continuation_batches(event)
        rows.append(
            DownstreamRow(
                event_id=event_id,
                policy=policy,
                batch=batch,
                context=context,
                context_available=context_available,
                context_reason=context_reason,
                target_status=target_status,
                target_exact=target_exact,
                cycle_life=cycle_life,
                log_cycle_life=log_cycle_life,
                life_lower_bound=lower_bound,
                continuation_batches=continuation_batches,
                cross_batch_target_provenance=len(set(continuation_batches)) > 1,
                x100=extraction.values,
                s100=s100,
                x100_available=extraction.available,
                x100_reason=extraction.reason,
                observed_mask=extraction.observed_mask,
                interpolated_cycles=extraction.interpolated_cycles,
                accepted_cycle_count=extraction.accepted_cycle_count,
                rejected_cycle_count=extraction.rejected_cycle_count,
            )
        )
    if not rows:
        raise ValueError("Severson event file contains no events")
    return rows


def build_feature_bundle(rows: list[DownstreamRow]) -> FeatureBundle:
    """Build the four frozen arms while keeping availability separate from NaN storage."""
    if not rows:
        raise ValueError("rows must not be empty")
    matrices = {
        name: np.full((len(rows), width), np.nan, dtype=float)
        for name, width in _ARM_WIDTHS.items()
    }
    available = {name: np.zeros(len(rows), dtype=bool) for name in ARM_NAMES}
    reasons: dict[str, list[str]] = {name: [] for name in ARM_NAMES}
    for index, row in enumerate(rows):
        context_ok = row.context_available and np.all(np.isfinite(row.context))
        x100_ok = (
            row.x100_available
            and np.all(np.isfinite(row.x100))
            and np.all(np.isfinite(row.s100))
        )
        arm_values = {
            "C": row.context,
            "C_S100": np.concatenate([row.context, row.s100]),
            "C_X100": np.concatenate([row.context, row.x100]),
            "C_S100_X100": np.concatenate([row.context, row.s100, row.x100]),
        }
        for name in ARM_NAMES:
            needs_x100 = name != "C"
            is_available = bool(context_ok and (x100_ok or not needs_x100))
            available[name][index] = is_available
            if is_available:
                matrices[name][index] = arm_values[name]
                reasons[name].append("available")
            elif not context_ok:
                reasons[name].append(f"context:{row.context_reason}")
            else:
                reasons[name].append(f"x100:{row.x100_reason}")
    return FeatureBundle(
        matrices=matrices,
        available=available,
        reasons={name: tuple(values) for name, values in reasons.items()},
    )


def _strict_eligibility(rows: list[DownstreamRow], values: np.ndarray) -> np.ndarray:
    eligible = np.asarray(values)
    if eligible.shape != (len(rows),) or not np.issubdtype(eligible.dtype, np.bool_):
        raise ValueError(f"analysis_eligible must be strict booleans with shape ({len(rows)},)")
    for index in np.flatnonzero(eligible):
        row = rows[int(index)]
        if not row.target_exact or row.log_cycle_life is None:
            raise ValueError(
                f"analysis_eligible includes a row without an exact scalar target: {row.event_id}"
            )
    if not eligible.any():
        raise ValueError("analysis_eligible must contain at least one exact target")
    return eligible.astype(bool, copy=True)


def policy_macro_weights(
    rows: list[DownstreamRow], analysis_eligible: np.ndarray
) -> np.ndarray:
    """Give every eligible policy unit total mass one; non-analysis rows receive zero."""
    eligible = _strict_eligibility(rows, analysis_eligible)
    counts = Counter(rows[int(index)].policy for index in np.flatnonzero(eligible))
    weights = np.zeros(len(rows), dtype=float)
    for index in np.flatnonzero(eligible):
        weights[index] = 1.0 / counts[rows[int(index)].policy]
    return weights


def _hash_labels(values: list[str] | tuple[str, ...]) -> str:
    payload = json.dumps(sorted(values), separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _policy_macro_mae(
    y_true: np.ndarray, y_pred: np.ndarray, policies: np.ndarray
) -> float:
    values = []
    for policy in sorted(set(policies.tolist())):
        mask = policies == policy
        values.append(float(np.mean(np.abs(y_pred[mask] - y_true[mask]))))
    return float(np.mean(values))


def _ridge_pipeline(alpha: float) -> Pipeline:
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=alpha)),
        ]
    )


def select_policy_macro_alpha(
    X: np.ndarray,
    y: np.ndarray,
    policies: np.ndarray,
    *,
    event_ids: list[str] | tuple[str, ...] | None = None,
    alphas: tuple[float, ...] = RIDGE_ALPHAS,
) -> AlphaSelection:
    """Select ridge alpha from policy-grouped inner OOF policy-macro MAE."""
    features = np.asarray(X, dtype=float)
    targets = np.asarray(y, dtype=float)
    groups = np.asarray(policies)
    if features.ndim != 2 or features.shape[0] == 0:
        raise ValueError("X must be a non-empty two-dimensional matrix")
    n = features.shape[0]
    if targets.shape != (n,) or groups.shape != (n,):
        raise ValueError("y and policies must have one value per X row")
    if not np.all(np.isfinite(features)) or not np.all(np.isfinite(targets)):
        raise ValueError("inner tuning requires finite features and targets")
    labels = [str(value) for value in groups.tolist()]
    if any(not value for value in labels):
        raise ValueError("policies must be non-empty labels")
    groups = np.asarray(labels, dtype=object)
    identifiers = [str(index) for index in range(n)] if event_ids is None else list(event_ids)
    if len(identifiers) != n or len(set(identifiers)) != n:
        raise ValueError("event_ids must be unique and have one value per X row")

    alpha_grid = tuple(sorted({float(alpha) for alpha in alphas}))
    if not alpha_grid or any(not np.isfinite(alpha) or alpha <= 0.0 for alpha in alpha_grid):
        raise ValueError("alphas must contain unique finite positive values")
    n_policies = len(set(labels))
    n_splits = min(5, n_policies)
    if n_splits < 2:
        raise ValueError("inner tuning requires at least two represented policies")
    split_indices = list(GroupKFold(n_splits=n_splits).split(features, targets, groups))
    fold_metadata: list[dict[str, Any]] = []
    for fold_index, (train, validation) in enumerate(split_indices):
        train_policies = sorted(set(groups[train].tolist()))
        validation_policies = sorted(set(groups[validation].tolist()))
        overlap = sorted(set(train_policies) & set(validation_policies))
        if overlap:
            raise AssertionError("an inner GroupKFold split shares policies")
        fold_metadata.append(
            {
                "fold_index": int(fold_index),
                "train_count": int(train.size),
                "validation_count": int(validation.size),
                "train_policy_count": len(train_policies),
                "validation_policy_count": len(validation_policies),
                "train_event_ids_sha256": _hash_labels([identifiers[i] for i in train]),
                "validation_event_ids_sha256": _hash_labels(
                    [identifiers[i] for i in validation]
                ),
                "train_policies_sha256": _hash_labels(train_policies),
                "validation_policies_sha256": _hash_labels(validation_policies),
                "policy_overlap_count": 0,
            }
        )

    scores: list[dict[str, Any]] = []
    for alpha in alpha_grid:
        predictions = np.full(n, np.nan, dtype=float)
        for train, validation in split_indices:
            model = _ridge_pipeline(alpha)
            model.fit(features[train], targets[train])
            predictions[validation] = model.predict(features[validation])
        if not np.all(np.isfinite(predictions)):
            raise AssertionError("inner GroupKFold did not produce one finite prediction per row")
        scores.append(
            {
                "alpha": float(alpha),
                "policy_macro_mae": _policy_macro_mae(targets, predictions, groups),
            }
        )
    selected = min(scores, key=lambda result: (result["policy_macro_mae"], result["alpha"]))
    return AlphaSelection(
        selected_alpha=float(selected["alpha"]),
        candidate_scores=tuple(scores),
        n_splits=n_splits,
        folds=tuple(fold_metadata),
    )


def _model_metadata(model: Pipeline) -> dict[str, Any]:
    scaler = model.named_steps["scaler"]
    ridge = model.named_steps["ridge"]
    return {
        "scaler_mean": [float(value) for value in scaler.mean_],
        "scaler_scale": [float(value) for value in scaler.scale_],
        "scaler_variance": [float(value) for value in scaler.var_],
        "ridge_coefficients": [float(value) for value in np.ravel(ridge.coef_)],
        "ridge_intercept": float(ridge.intercept_),
    }


def held_batch_oof(
    rows: list[DownstreamRow],
    analysis_eligible: np.ndarray,
    *,
    alphas: tuple[float, ...] = RIDGE_ALPHAS,
) -> HeldBatchOOFResult:
    """Refit nested StandardScaler→Ridge models and predict each held batch once.

    Every available attempt in a held batch receives a prediction, including censored or
    sensitivity-excluded rows.  Only ``analysis_eligible`` rows enter fitting and alpha
    selection.  Supplying a different eligibility mask therefore performs a full sensitivity
    refit rather than reusing predictions trained on excluded target provenance.
    """
    if not rows:
        raise ValueError("rows must not be empty")
    eligible = _strict_eligibility(rows, analysis_eligible)
    features = build_feature_bundle(rows)
    event_ids = np.asarray([row.event_id for row in rows], dtype=object)
    policies = np.asarray([row.policy for row in rows], dtype=object)
    batches = np.asarray([row.batch for row in rows], dtype=object)
    targets = np.array(
        [row.log_cycle_life if row.log_cycle_life is not None else np.nan for row in rows],
        dtype=float,
    )
    unique_batches = sorted(set(batches.tolist()))
    if len(unique_batches) < 2:
        raise ValueError("held-batch OOF requires at least two represented batches")
    predictions = {
        name: np.full(len(rows), np.nan, dtype=float)
        for name in ARM_NAMES
    }
    fold_metadata: list[dict[str, Any]] = []

    for held_batch in unique_batches:
        outer_test = batches == held_batch
        outer_train_attempts = ~outer_test
        train_events = set(event_ids[outer_train_attempts].tolist())
        test_events = set(event_ids[outer_test].tolist())
        train_policies_all = set(policies[outer_train_attempts].tolist())
        test_policies_all = set(policies[outer_test].tolist())
        event_overlap = sorted(train_events & test_events)
        policy_overlap = sorted(train_policies_all & test_policies_all)
        if event_overlap:
            raise AssertionError("an outer held-batch fold shares event IDs")
        if policy_overlap:
            raise AssertionError("an outer held-batch fold shares policy IDs")

        fold: dict[str, Any] = {
            "held_batch": str(held_batch),
            "train_batches": sorted(set(batches[outer_train_attempts].tolist())),
            "train_attempt_count": int(outer_train_attempts.sum()),
            "test_attempt_count": int(outer_test.sum()),
            "train_target_count": int((outer_train_attempts & eligible).sum()),
            "test_target_count": int((outer_test & eligible).sum()),
            "train_policy_count": len(train_policies_all),
            "test_policy_count": len(test_policies_all),
            "train_event_ids_sha256": _hash_labels(sorted(train_events)),
            "test_event_ids_sha256": _hash_labels(sorted(test_events)),
            "train_policies_sha256": _hash_labels(sorted(train_policies_all)),
            "test_policies_sha256": _hash_labels(sorted(test_policies_all)),
            "event_overlap_count": 0,
            "policy_overlap_count": 0,
            "arms": {},
        }
        for arm_name in ARM_NAMES:
            arm_available = features.available[arm_name]
            train_mask = outer_train_attempts & eligible & arm_available
            predict_mask = outer_test & arm_available
            train_indices = np.flatnonzero(train_mask)
            predict_indices = np.flatnonzero(predict_mask)
            if train_indices.size == 0:
                raise ValueError(f"arm {arm_name} has no eligible outer-training rows")
            selection = select_policy_macro_alpha(
                features.matrices[arm_name][train_indices],
                targets[train_indices],
                policies[train_indices],
                event_ids=event_ids[train_indices].tolist(),
                alphas=alphas,
            )
            model = _ridge_pipeline(selection.selected_alpha)
            model.fit(features.matrices[arm_name][train_indices], targets[train_indices])
            if np.any(np.isfinite(predictions[arm_name][predict_indices])):
                raise AssertionError("an attempt received more than one outer-fold prediction")
            predictions[arm_name][predict_indices] = model.predict(
                features.matrices[arm_name][predict_indices]
            )
            fold["arms"][arm_name] = {
                "train_count": int(train_indices.size),
                "predicted_attempt_count": int(predict_indices.size),
                "feature_width": int(features.matrices[arm_name].shape[1]),
                "selected_alpha": selection.selected_alpha,
                "inner_n_splits": selection.n_splits,
                "inner_candidate_scores": list(selection.candidate_scores),
                "inner_folds": list(selection.folds),
                "model": _model_metadata(model),
            }
        fold_metadata.append(fold)

    for arm_name in ARM_NAMES:
        available = features.available[arm_name]
        if not np.all(np.isfinite(predictions[arm_name][available])):
            raise AssertionError(f"arm {arm_name} lacks a finite held-batch prediction")
        if np.any(np.isfinite(predictions[arm_name][~available])):
            raise AssertionError(f"arm {arm_name} predicted a representation-unavailable row")

    metadata = {
        "outer_split": "leave_one_complete_batch_out",
        "inner_split": "GroupKFold_by_charge_policy",
        "inner_selection_metric": "mean_per_policy_inner_oof_mae_log10_cycles",
        "fit_sample_weights": False,
        "prediction_scope": "every_representation_available_held_batch_attempt",
        "batch_order": [str(value) for value in unique_batches],
        "analysis_eligible_count": int(eligible.sum()),
        "analysis_event_ids_sha256": _hash_labels(event_ids[eligible].tolist()),
        "ridge_alphas": [float(value) for value in sorted(set(alphas))],
        "arm_names": list(ARM_NAMES),
    }
    return HeldBatchOOFResult(
        predictions=predictions,
        analysis_eligible=eligible,
        features=features,
        folds=tuple(fold_metadata),
        metadata=metadata,
    )
