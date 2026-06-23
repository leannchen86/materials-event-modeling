# The same question in two fields: is my signal real, or a collection artifact?

*From "models learn the lab" in materials spectra to deduplicating, decontaminating, and
auditing an LLM pretraining corpus — one discipline, two modalities.*

> Exploratory write-up from a data/AI angle. Everything below runs on open data; code and
> reproduction steps are linked inline.

Every data practitioner eventually meets the same worry in different costumes. In
materials science it sounds like: *did my model learn the chemistry, or did it learn which
instrument measured the sample?* In LLM pretraining it sounds like: *did my model learn
language, or did it memorize the benchmark and the source domain?* These are the **same
question** — whether an apparent signal is real or a fingerprint of how the data was
collected — and it turns out the **same diagnostic** answers both.

## Part 1 — Materials: the label can be faithful to the lab, not the world

Public experimental X-ray diffraction (XRD) carries a fingerprint of the lab that produced
it. Train a simple probe to recover the *source institution* from a spectrum and it
succeeds far above chance **even after normalization** — and from the bare metadata it is
nearly perfect. ([provenance_leakage_audit.md](../provenance-critique/provenance_leakage_audit.md))

| feature | recover the lab (balanced acc) |
| --- | ---: |
| trivial metadata | 0.98 |
| coverage mask alone | 0.90 |
| raw spectrum (PCA) | 0.79 |
| strongest preprocessing control | 0.56 (still elevated) |

The lesson: a representation can encode *which lab* rather than *what material*, and
normalization does not remove it. You must treat source as a confound — stratify by it,
don't assume it away.

## Part 2 — The identical audit on a pretraining mix

The audit core is modality-agnostic: give it document features and a provenance label and
it measures recoverability. So point it at a 1,000-document **pretraining mix** —
FineWeb (web), Wikipedia, code, and arXiv — with the document *source* as the provenance
label. ([provenance_leakage_text_corpus.md](../provenance-critique/provenance_leakage_text_corpus.md))

| feature | recover the source (balanced acc) |
| --- | ---: |
| topical content (TF-IDF) | 0.98 |
| character n-grams | 0.96 |
| trivial surface stats | 0.91 |
| **function words only (no topic)** | **0.89** |

Even *function words alone* — pure style, zero topical content — recover the source at
0.89. The same shape as the materials result: the provenance fingerprint is pervasive and
not removable by dropping content. A "balanced" data mix still carries it; a learned
quality classifier is partly just a source classifier; a random train/eval split silently
leaks source.

## Part 3 — So curation is the discipline that addresses it

If provenance leaks everywhere, the response is the standard pretraining-curation stack —
and it is the same instinct as the materials controls, scaled up. Built from scratch and
tested on the same open corpus
([pretraining_curation_pipeline.md](../provenance-critique/pretraining_curation_pipeline.md)):

- **Deduplication** (exact + MinHash-LSH near-dup) — because duplicates inflate a source's
  apparent weight, the textual version of an over-represented instrument.
- **Quality filtering** (Gopher/C4 heuristics) — and the honest finding that prose filters
  *penalize code*, i.e. a filter is not modality-neutral, the same way an XRD control is
  not chemistry-neutral.
- **Decontamination** — n-gram overlap catches verbatim eval items but **misses every
  paraphrase**; a fuzzy pass recovers the close ones; heavy rewordings need embeddings.
  Contamination is a provenance leak between *train* and *eval*.
- **A data card** — per-stage lineage, source distribution before/after, and a content
  hash, so any curated snapshot is auditable. Provenance you can't trace is data you
  can't trust — in both fields.

## The point

"Is this label faithful to reality, or to how we collected the data?" is not a materials
question or an LLM question. It is *the* data-quality question, and the tools — recover
the confound, control for it, dedup it, decontaminate it, and record the lineage — are one
toolkit. The materials setting just happens to be a rare place where "reality" is a
physical measurement, so you can see the artifact cleanly; a pretraining corpus is the
same problem at scale, where the artifact is the source, the duplicate, and the leaked
benchmark.

*Reproduce: `scripts/fetch_text_corpus.py` → `scripts/run_provenance_leakage_audit.py
--dataset text` → `scripts/run_curation_pipeline.py`. Corrections welcome.*
