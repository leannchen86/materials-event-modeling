"""Provenance-recoverability audit for collection-artifact risk.

The question this answers, in one sentence: **how much of an incidental provenance
label can a simple model recover from a record's features?**

In this repository the records are experimental spectra and the label is a collection
source. High recovery says that features contain source-associated variation; it does not
identify the physical cause, prove a downstream model used a shortcut, or establish
instrument effects independently of material selection.

The core is modality-agnostic. Callers pass:

* ``feature_sets`` — a mapping ``{name: matrix}`` of (n_items, n_features) arrays, such
  as PCA-reduced spectra or measurement summaries.
* ``labels`` — the per-item provenance/source id to try to recover.

and get back, per feature set, a recoverability measurement plus a normalized score in
``[0, 1]`` and a heuristic risk band. The audit is a reason to add controls and stricter
splits, not a pass/fail decision on its own.

Pure ``numpy`` + ``scikit-learn``; no deep-learning or dataset-specific dependencies.
"""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# Severity thresholds on the normalized leakage score (heuristic, tunable). The score
# is 0.0 at chance and 1.0 at perfect recoverability, so these read as "fraction of the
# way from chance to fully recoverable."
SEVERITY_THRESHOLDS: dict[str, float] = {"elevated": 0.15, "severe": 0.50}


def metric_summary(values: list[float]) -> dict[str, float]:
    """Mean/std/min/max of a list of fold metrics."""
    return {
        "mean": mean(values),
        "std": pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def leakage_score(balanced_accuracy: float, chance: float) -> float:
    """Normalize recoverability to ``[0, 1]``: 0 at chance, 1 at perfect recovery.

    ``(balanced_accuracy - chance) / (1 - chance)`` so the number is comparable across
    audits with different class counts (different ``chance``). Clamped to ``[0, 1]``.
    """
    if chance >= 1.0:
        return 0.0
    return float(min(1.0, max(0.0, (balanced_accuracy - chance) / (1.0 - chance))))


def classify_severity(score: float) -> str:
    """Map a leakage score to ``clean`` / ``elevated`` / ``severe``."""
    if score >= SEVERITY_THRESHOLDS["severe"]:
        return "severe"
    if score >= SEVERITY_THRESHOLDS["elevated"]:
        return "elevated"
    return "clean"


def evaluate_recoverability(
    features: np.ndarray,
    labels: np.ndarray,
    *,
    classes: list[Any] | None = None,
    n_splits: int = 3,
    seed: int = 17,
) -> dict[str, Any]:
    """Cross-validated recoverability of ``labels`` from ``features``.

    A balanced logistic-regression probe (vs a most-frequent ``DummyClassifier``
    baseline) under stratified k-fold. Returns the standard metrics plus the derived
    ``leakage_score`` and ``severity``. Mirrors the estimator used by the original
    opXRD source-predictability scripts so results reproduce.
    """
    features = np.asarray(features, dtype=np.float32)
    labels = np.asarray(labels)
    if classes is None:
        classes = sorted(set(labels.tolist()))

    classifier = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed),
    )
    baseline = DummyClassifier(strategy="most_frequent")
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)

    accuracy: list[float] = []
    balanced_accuracy: list[float] = []
    baseline_accuracy: list[float] = []
    baseline_balanced_accuracy: list[float] = []
    confusion = np.zeros((len(classes), len(classes)), dtype=np.int64)

    for train_idx, test_idx in cv.split(features, labels):
        classifier.fit(features[train_idx], labels[train_idx])
        prediction = classifier.predict(features[test_idx])
        baseline.fit(features[train_idx], labels[train_idx])
        baseline_prediction = baseline.predict(features[test_idx])

        accuracy.append(float(accuracy_score(labels[test_idx], prediction)))
        balanced_accuracy.append(float(balanced_accuracy_score(labels[test_idx], prediction)))
        baseline_accuracy.append(float(accuracy_score(labels[test_idx], baseline_prediction)))
        baseline_balanced_accuracy.append(
            float(balanced_accuracy_score(labels[test_idx], baseline_prediction))
        )
        confusion += confusion_matrix(labels[test_idx], prediction, labels=classes)

    per_class_recall = {}
    for idx, class_name in enumerate(classes):
        row_sum = int(confusion[idx].sum())
        per_class_recall[str(class_name)] = (
            float(confusion[idx, idx] / row_sum) if row_sum else None
        )

    bal_acc_mean = mean(balanced_accuracy)
    # Chance for a most-frequent classifier under balanced accuracy is ~1/n_classes;
    # use the measured baseline so the score reflects the actual fold splits.
    chance = mean(baseline_balanced_accuracy)
    score = leakage_score(bal_acc_mean, chance)

    return {
        "features": int(features.shape[1]),
        "accuracy": metric_summary(accuracy),
        "balanced_accuracy": metric_summary(balanced_accuracy),
        "baseline_accuracy": metric_summary(baseline_accuracy),
        "baseline_balanced_accuracy": metric_summary(baseline_balanced_accuracy),
        "chance_balanced_accuracy": chance,
        "leakage_score": score,
        "severity": classify_severity(score),
        "per_class_recall": per_class_recall,
        "confusion_matrix": confusion.tolist(),
        "classes": [str(c) for c in classes],
    }


def audit_feature_sets(
    feature_sets: dict[str, np.ndarray],
    labels: np.ndarray,
    *,
    n_splits: int = 3,
    seed: int = 17,
) -> dict[str, Any]:
    """Audit provenance recoverability and rank feature sets by heuristic risk.

    Returns a report with per-feature-set results (sorted worst-first), the worst
    observed leakage, and a plain-language recommendation.
    """
    labels = np.asarray(labels)
    classes = sorted(set(labels.tolist()))
    class_counts = {str(c): int((labels == c).sum()) for c in classes}
    if len(classes) < 2:
        raise ValueError("at least two provenance classes are required")
    max_splits = min(class_counts.values())
    if max_splits < 2:
        raise ValueError("each provenance class needs at least two records")
    effective_splits = min(n_splits, max_splits)

    results: dict[str, dict[str, Any]] = {}
    for name, features in feature_sets.items():
        result = evaluate_recoverability(
            features,
            labels,
            classes=classes,
            n_splits=effective_splits,
            seed=seed,
        )
        result["feature_set"] = name
        results[name] = result

    ranked = sorted(
        results.values(), key=lambda r: r["leakage_score"], reverse=True
    )
    worst = ranked[0] if ranked else None
    worst_severity = worst["severity"] if worst else "clean"

    recommendation = {
        "severe": (
            "HIGH RISK: provenance is strongly recoverable. Treat source as a potential "
            "confound, apply collection/normalization controls, and report strict "
            "source-held-out downstream evaluation before making representation claims."
        ),
        "elevated": (
            "ELEVATED RISK: provenance is partially recoverable. Report "
            "leave-one-source-out metrics and evaluate whether controls reduce both "
            "recoverability and downstream performance sensitivity."
        ),
        "clean": (
            "LOW OBSERVED RISK: this probe did not exceed the chosen heuristic threshold. "
            "It does not establish absence of collection artifacts."
        ),
    }[worst_severity]

    return {
        "task": "provenance_recoverability_audit",
        "n_items": int(labels.shape[0]),
        "n_classes": len(classes),
        "class_counts": class_counts,
        "n_splits": effective_splits,
        "seed": seed,
        "severity_thresholds": SEVERITY_THRESHOLDS,
        "worst_feature_set": worst["feature_set"] if worst else None,
        "worst_leakage_score": worst["leakage_score"] if worst else 0.0,
        "worst_provenance_recoverability_score": worst["leakage_score"] if worst else 0.0,
        "worst_severity": worst_severity,
        "recommendation": recommendation,
        "results": [
            {
                "feature_set": r["feature_set"],
                "leakage_score": r["leakage_score"],
                "provenance_recoverability_score": r["leakage_score"],
                "severity": r["severity"],
                "balanced_accuracy": r["balanced_accuracy"]["mean"],
                "chance_balanced_accuracy": r["chance_balanced_accuracy"],
                "accuracy": r["accuracy"]["mean"],
                "features": r["features"],
                "per_class_recall": r["per_class_recall"],
            }
            for r in ranked
        ],
        "detail": results,
        "caveats": [
            "This is an artifact diagnostic, not a source-classification benchmark.",
            "Random folds answer whether the provenance imprint is PRESENT, not whether "
            "it generalizes to unseen sources (use a leave-one-source-out transfer test "
            "for that).",
            "High recoverability means features can encode collection-associated "
            "variation; it does not by itself prove the cause or a downstream shortcut.",
        ],
    }


def control_efficacy(
    report: dict[str, Any], baseline: str, control: str
) -> dict[str, Any]:
    """How much does a control feature set reduce recoverability vs a baseline?

    e.g. baseline=``full_xrd_pca`` vs control=``crop_xrd_derivative_pca`` answers
    "did the preprocessing control actually reduce source recoverability?"
    """
    detail = report["detail"]
    if baseline not in detail or control not in detail:
        missing = [n for n in (baseline, control) if n not in detail]
        raise KeyError(f"feature set(s) not in report: {missing}")
    base_score = detail[baseline]["leakage_score"]
    ctrl_score = detail[control]["leakage_score"]
    absolute = base_score - ctrl_score
    relative = absolute / base_score if base_score > 0 else 0.0
    return {
        "baseline": baseline,
        "control": control,
        "baseline_leakage_score": base_score,
        "control_leakage_score": ctrl_score,
        "absolute_reduction": absolute,
        "relative_reduction": relative,
        "control_severity": detail[control]["severity"],
        "neutralized": detail[control]["severity"] == "clean",
    }
