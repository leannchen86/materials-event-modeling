"""Heuristic quality filtering (Gopher / C4 / RefinedWeb style).

Computes per-document quality signals and applies tunable rules, returning *which* rule
each failing document tripped (signals stored as tags, not silent hard drops) so the
filter is ablatable. This is the rule-based layer that precedes a learned quality
classifier in a production pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_WORD = re.compile(r"\w+")

# A small set of high-frequency English function words (Gopher uses presence of common
# stop words as a "is this natural prose" signal).
_COMMON_STOPWORDS = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "is", "are", "was",
}


@dataclass
class QualityThresholds:
    min_words: int = 50
    max_words: int = 100_000
    min_mean_word_len: float = 3.0
    max_mean_word_len: float = 10.0
    max_symbol_word_ratio: float = 0.10   # '#' and '...' density vs words
    min_stopwords_present: int = 2        # at least N distinct common stop words
    min_alpha_ratio: float = 0.60         # fraction of alphabetic characters
    min_unique_word_ratio: float = 0.30   # type-token ratio (repetition guard)
    rules: tuple[str, ...] = field(default=(
        "min_words", "max_words", "mean_word_len", "symbol_word_ratio",
        "stopwords_present", "alpha_ratio", "unique_word_ratio",
    ))


def quality_signals(text: str) -> dict[str, float]:
    words = _WORD.findall(text)
    n_words = len(words)
    n_chars = max(len(text), 1)
    word_lens = [len(w) for w in words]
    n_symbols = text.count("#") + text.count("...")
    stopwords_present = len({w.lower() for w in words} & _COMMON_STOPWORDS)
    return {
        "n_words": float(n_words),
        "mean_word_len": (sum(word_lens) / n_words) if n_words else 0.0,
        "symbol_word_ratio": n_symbols / max(n_words, 1),
        "stopwords_present": float(stopwords_present),
        "alpha_ratio": sum(c.isalpha() for c in text) / n_chars,
        "unique_word_ratio": (len(set(w.lower() for w in words)) / n_words) if n_words else 0.0,
    }


def _failed_rules(sig: dict[str, float], t: QualityThresholds) -> list[str]:
    failed = []
    checks = {
        "min_words": sig["n_words"] >= t.min_words,
        "max_words": sig["n_words"] <= t.max_words,
        "mean_word_len": t.min_mean_word_len <= sig["mean_word_len"] <= t.max_mean_word_len,
        "symbol_word_ratio": sig["symbol_word_ratio"] <= t.max_symbol_word_ratio,
        "stopwords_present": sig["stopwords_present"] >= t.min_stopwords_present,
        "alpha_ratio": sig["alpha_ratio"] >= t.min_alpha_ratio,
        "unique_word_ratio": sig["unique_word_ratio"] >= t.min_unique_word_ratio,
    }
    for rule in t.rules:
        if not checks[rule]:
            failed.append(rule)
    return failed


def quality_filter(
    docs: list[tuple[str, str]], thresholds: QualityThresholds | None = None
) -> dict[str, Any]:
    """Partition docs into kept / removed and tally which rule removed each."""
    t = thresholds or QualityThresholds()
    kept, removed = [], []
    rule_counts: dict[str, int] = {rule: 0 for rule in t.rules}
    for doc_id, text in docs:
        failed = _failed_rules(quality_signals(text), t)
        if failed:
            removed.append({"doc_id": doc_id, "failed_rules": failed})
            for rule in failed:
                rule_counts[rule] += 1
        else:
            kept.append(doc_id)
    return {
        "kept_ids": kept,
        "removed": removed,
        "removed_count": len(removed),
        "removed_by_rule": rule_counts,
        "thresholds": {k: getattr(t, k) for k in vars(t) if k != "rules"},
    }
