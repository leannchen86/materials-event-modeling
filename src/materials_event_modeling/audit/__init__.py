"""Dataset-curation audits.

Currently: provenance-leakage auditing — measure how recoverable an *incidental*
provenance label (which lab, instrument, snapshot, or eval-benchmark a record came
from) is from a record's features. This is the modality-agnostic core of
collection-artifact / train-test-contamination detection used in pretraining-corpus
curation, applied here to materials spectra.
"""

from materials_event_modeling.audit.provenance_leakage import (
    audit_feature_sets,
    classify_severity,
    control_efficacy,
    evaluate_recoverability,
    leakage_score,
)

__all__ = [
    "audit_feature_sets",
    "classify_severity",
    "control_efficacy",
    "evaluate_recoverability",
    "leakage_score",
]
