"""Tests for the modality-agnostic provenance-leakage audit core."""

from __future__ import annotations

import numpy as np

from materials_event_modeling.audit.provenance_leakage import (
    audit_feature_sets,
    classify_severity,
    control_efficacy,
    leakage_score,
)


def test_leakage_score_endpoints() -> None:
    assert leakage_score(0.2, 0.2) == 0.0  # at chance
    assert leakage_score(1.0, 0.2) == 1.0  # perfect recovery
    # halfway from chance to perfect
    assert abs(leakage_score(0.6, 0.2) - 0.5) < 1e-9
    assert leakage_score(0.1, 0.2) == 0.0  # below chance clamps to 0


def test_classify_severity_bands() -> None:
    assert classify_severity(0.05) == "clean"
    assert classify_severity(0.30) == "elevated"
    assert classify_severity(0.80) == "severe"


def _two_class_labels(n: int) -> np.ndarray:
    return np.array(["a"] * (n // 2) + ["b"] * (n - n // 2))


def test_separable_features_flagged_severe() -> None:
    rng = np.random.default_rng(0)
    n = 120
    labels = _two_class_labels(n)
    # A feature perfectly aligned with the label (leaky) and pure noise (clean).
    signal = np.where(labels == "a", 0.0, 8.0)[:, None] + rng.normal(0, 0.2, (n, 1))
    noise = rng.normal(0, 1.0, (n, 4))
    report = audit_feature_sets(
        {"leaky": signal, "clean": noise}, labels, n_splits=3, seed=0
    )
    by_name = {r["feature_set"]: r for r in report["results"]}
    assert by_name["leaky"]["severity"] == "severe"
    assert by_name["leaky"]["leakage_score"] > by_name["clean"]["leakage_score"]
    assert report["worst_feature_set"] == "leaky"  # ranked worst-first


def test_control_efficacy_reports_reduction() -> None:
    rng = np.random.default_rng(1)
    n = 120
    labels = _two_class_labels(n)
    leaky = np.where(labels == "a", 0.0, 8.0)[:, None] + rng.normal(0, 0.2, (n, 1))
    clean = rng.normal(0, 1.0, (n, 4))
    report = audit_feature_sets({"raw": leaky, "fixed": clean}, labels, n_splits=3, seed=1)
    eff = control_efficacy(report, baseline="raw", control="fixed")
    assert eff["absolute_reduction"] > 0
    assert 0.0 <= eff["relative_reduction"] <= 1.0
    # The control is strongly less leaky than the raw (perfectly separable) feature.
    # We avoid asserting an exact "clean" verdict: with small n a balanced probe can
    # extract slightly-above-chance recoverability from pure noise, which is itself the
    # finite-sample caveat the audit warns about.
    assert eff["control_leakage_score"] < eff["baseline_leakage_score"]
    assert eff["relative_reduction"] > 0.5
    assert eff["control_severity"] != "severe"
