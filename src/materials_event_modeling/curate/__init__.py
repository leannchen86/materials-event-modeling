"""LLM-pretraining corpus curation primitives.

From-scratch, dependency-light reference implementations of the core stages a
pretraining-data pipeline runs — deduplication, quality filtering, and benchmark
decontamination — so the mechanics are transparent rather than hidden behind a toolkit.
Production would use datatrove / Dolma / NeMo-Curator; these mirror the same techniques.
"""

from materials_event_modeling.curate.decontamination import (
    fuzzy_contamination,
    ngram_contamination,
)
from materials_event_modeling.curate.dedup import exact_dedup, minhash_dedup
from materials_event_modeling.curate.quality import quality_filter, quality_signals

__all__ = [
    "exact_dedup",
    "fuzzy_contamination",
    "minhash_dedup",
    "ngram_contamination",
    "quality_filter",
    "quality_signals",
]
