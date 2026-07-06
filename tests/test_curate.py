"""Tests for the pretraining-curation primitives (dedup, quality, decontamination)."""

from __future__ import annotations

from materials_event_modeling.curate import (
    exact_dedup,
    fuzzy_contamination,
    minhash_dedup,
    ngram_contamination,
    quality_filter,
)

# --- dedup -----------------------------------------------------------------------------


def test_exact_dedup_normalizes_whitespace_and_case() -> None:
    docs = [
        ("a", "The Quick Brown Fox"),
        ("b", "the   quick brown   fox"),  # same up to case/whitespace
        ("c", "a totally different document about something else entirely"),
    ]
    out = exact_dedup(docs)
    assert out["removed_count"] == 1
    assert out["removed"][0]["doc_id"] == "b"
    assert out["removed"][0]["duplicate_of"] == "a"
    assert set(out["kept_ids"]) == {"a", "c"}


def test_minhash_catches_near_duplicate_not_distinct() -> None:
    base = (
        "The history of cartography traces how humans have represented the world on maps "
        "from ancient clay tablets through medieval portolan charts to modern satellite "
        "imagery. Each era reflected the tools and knowledge available, and every new "
        "projection forced a trade off between preserving area, shape, distance, or "
        "direction across the curved surface of the planet."
    )
    # single-token, same-length edits keep token positions aligned -> high Jaccard
    near = base.replace("humans", "people").replace("modern", "recent")
    distinct = (
        "Quantum chromodynamics describes the strong interaction that binds quarks and "
        "gluons into protons and neutrons, becoming weaker at short distances in a "
        "phenomenon known as asymptotic freedom that earned a Nobel Prize in physics."
    )
    docs = [("base", base), ("near", near), ("distinct", distinct)]
    out = minhash_dedup(docs, num_perm=64, bands=16, threshold=0.5, seed=0)
    removed = {r["doc_id"] for r in out["removed"]}
    assert "near" in removed          # near-dup collapsed
    assert "distinct" not in removed  # genuinely different doc kept
    assert "distinct" in out["kept_ids"]


# --- quality ---------------------------------------------------------------------------


def test_quality_filter_flags_short_and_repetitive() -> None:
    good = (
        "Materials science studies the structure and properties of matter across many "
        "different length scales. Researchers prepare samples under carefully controlled "
        "conditions, measure how crystals form when the material is slowly heated, and "
        "record every result so that other laboratories can reproduce the same experiment "
        "later. Careful documentation of each of these steps is what allows a finding to "
        "be trusted and then built upon by the wider research community over time."
    )
    too_short = "buy now"
    repetitive = "spam spam spam spam spam spam spam spam spam spam " * 8
    out = quality_filter([("good", good), ("short", too_short), ("rep", repetitive)])
    removed = {r["doc_id"] for r in out["removed"]}
    assert "good" not in removed
    assert "short" in removed
    assert "rep" in removed
    assert out["removed_by_rule"]["min_words"] >= 1


# --- decontamination -------------------------------------------------------------------


_EVAL = {
    "q1": "What is the capital of the country whose largest city is Sydney",
    "q2": "If a train travels 60 miles in 90 minutes what is its average speed in mph",
}


def test_ngram_catches_verbatim_misses_paraphrase() -> None:
    verbatim = ("intro text. " + _EVAL["q1"] + " more trailing text here.")
    paraphrase = "Which is the capital city of the nation whose biggest city happens to be Sydney"
    clean = "an unrelated document about gardening and the weather this spring season"
    docs = [("v", verbatim), ("p", paraphrase), ("c", clean)]
    out = ngram_contamination(docs, _EVAL, n=13)
    assert "v" in out["flagged_doc_ids"]      # verbatim caught
    assert "p" not in out["flagged_doc_ids"]  # paraphrase slips past n-gram
    assert "c" not in out["flagged_doc_ids"]


def test_fuzzy_catches_paraphrase() -> None:
    paraphrase = "Which is the capital city of the nation whose biggest city happens to be Sydney"
    clean = "an unrelated document about gardening and the weather this spring season"
    docs = [("p", paraphrase), ("c", clean)]
    out = fuzzy_contamination(docs, {"q1": _EVAL["q1"]}, threshold=0.5)
    assert "p" in out["flagged_doc_ids"]  # fuzzy pass recovers what n-gram missed
