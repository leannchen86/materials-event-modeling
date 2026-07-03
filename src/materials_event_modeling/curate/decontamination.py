"""Benchmark decontamination: detect training docs that contain eval-set items.

Two passes, mirroring production practice:

* ``ngram_contamination`` — exact n-gram overlap (the GPT-3/GPT-4/FineWeb approach).
  Fast and precise, but **defeated by paraphrase**: a reworded eval item shares no long
  n-gram with the original (arXiv 2311.04850).
* ``fuzzy_contamination`` — a char-n-gram TF-IDF cosine pass that catches paraphrased /
  reformatted contamination the n-gram pass misses. Stands in for the embedding-similarity
  step a real pipeline would run.

Eval items are passed as ``{eval_id: text}``; docs as ``[(doc_id, text), ...]``.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_WORD = re.compile(r"\w+")


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    if len(tokens) < n:
        return set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def ngram_contamination(
    docs: list[tuple[str, str]], eval_items: dict[str, str], n: int = 13
) -> dict[str, Any]:
    """Flag docs whose text shares an n-gram with any eval item.

    Short eval items (fewer than ``n`` tokens) are matched at their full length so they
    are not silently skipped.
    """
    # Group eval n-grams by their effective length so docs are scanned at matching n.
    index_by_n: dict[int, dict[tuple[str, ...], set[str]]] = defaultdict(lambda: defaultdict(set))
    for eid, text in eval_items.items():
        toks = _tokens(text)
        eff = min(n, len(toks))
        if eff == 0:
            continue
        for gram in _ngrams(toks, eff):
            index_by_n[eff][gram].add(eid)

    flagged: set[str] = set()
    matched_evals: set[str] = set()
    per_doc = []
    for doc_id, text in docs:
        toks = _tokens(text)
        hits: set[str] = set()
        for eff, index in index_by_n.items():
            for gram in _ngrams(toks, eff):
                if gram in index:
                    hits |= index[gram]
        if hits:
            flagged.add(doc_id)
            matched_evals |= hits
        per_doc.append({"doc_id": doc_id, "matched_eval_ids": sorted(hits)})

    return {
        "method": "ngram",
        "n": n,
        "contaminated_doc_count": len(flagged),
        "flagged_doc_ids": sorted(flagged),
        "eval_items_caught": len(matched_evals),
        "eval_recall": len(matched_evals) / max(len(eval_items), 1),
        "per_doc": per_doc,
    }


def fuzzy_contamination(
    docs: list[tuple[str, str]], eval_items: dict[str, str], threshold: float = 0.8
) -> dict[str, Any]:
    """Flag docs near an eval item by char-n-gram TF-IDF cosine (catches paraphrase)."""
    doc_ids = [d for d, _ in docs]
    doc_texts = [t for _, t in docs]
    eval_ids = list(eval_items)
    eval_texts = [eval_items[e] for e in eval_ids]

    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
    matrix = vec.fit_transform(eval_texts + doc_texts)
    eval_mat = matrix[: len(eval_texts)]
    doc_mat = matrix[len(eval_texts) :]
    sims = cosine_similarity(eval_mat, doc_mat)  # (n_eval, n_doc)

    matches = []
    caught_evals: set[str] = set()
    flagged_docs: set[str] = set()
    for ei, eid in enumerate(eval_ids):
        best = int(np.argmax(sims[ei])) if sims.shape[1] else -1
        score = float(sims[ei, best]) if best >= 0 else 0.0
        if score >= threshold:
            caught_evals.add(eid)
            flagged_docs.add(doc_ids[best])
            matches.append({"eval_id": eid, "doc_id": doc_ids[best], "cosine": round(score, 3)})

    return {
        "method": "fuzzy_char_cosine",
        "threshold": threshold,
        "contaminated_doc_count": len(flagged_docs),
        "flagged_doc_ids": sorted(flagged_docs),
        "eval_items_caught": len(caught_evals),
        "eval_recall": len(caught_evals) / max(len(eval_items), 1),
        "matches": matches,
    }
