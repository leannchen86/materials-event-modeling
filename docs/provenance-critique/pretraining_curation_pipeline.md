# Pretraining-corpus curation pipeline + decontamination

From-scratch, dependency-light reference implementations of the core stages an LLM
pretraining-data pipeline runs, so the mechanics are transparent rather than hidden
behind a toolkit. Production would use datatrove / Dolma / NeMo-Curator; these mirror the
same techniques and let the audit results be reproduced on open data.

- **Primitives:** [`src/materials_event_modeling/curate/`](../../src/materials_event_modeling/curate/) — `dedup.py` (exact + MinHash-LSH), `quality.py` (Gopher/C4 heuristics), `decontamination.py` (n-gram + fuzzy).
- **Scripts:** [`run_curation_pipeline.py`](../../scripts/run_curation_pipeline.py), [`run_decontamination_demo.py`](../../scripts/run_decontamination_demo.py)
- **Tests:** [`tests/test_curate.py`](../../tests/test_curate.py) (5 cases)
- Corpus: the multi-source mix from [`fetch_text_corpus.py`](../../scripts/fetch_text_corpus.py) — see [provenance_leakage_text_corpus.md](provenance_leakage_text_corpus.md).

## 1. Decontamination — n-gram is defeated by paraphrase

```
.venv/bin/python scripts/run_decontamination_demo.py
```

200 clean web docs + 6 verbatim and 6 paraphrased eval-item injections:

| pass | verbatim caught | paraphrase caught | false-pos on clean |
| --- | ---: | ---: | ---: |
| n-gram (13-gram) | 6 / 6 | 0 / 6 | 0 |
| fuzzy (char-cosine ≥ 0.35) | 6 / 6 | 2 / 6 | 0 |

n-gram overlap catches every verbatim copy and **misses every paraphrase**. A char-cosine
fuzzy pass recovers the lexically-close paraphrases, but ~4 heavily-reworded ones still
evade it — the residual that motivates an **embedding/semantic** decontamination pass
(arXiv 2311.04850, "rephrased samples"). This escalation gradient (exact → fuzzy →
semantic) is the honest shape of contamination detection.

## 2. Full pipeline → versioned data card

```
.venv/bin/python scripts/run_curation_pipeline.py
```

The 1,000-doc mix plus a controlled injection of duplicates, near-dups, junk, and
benchmark-contaminated docs (so each stage is scored against ground truth):

| stage | input | removed | output |
| --- | ---: | ---: | ---: |
| exact_dedup | 1038 | 10 | 1028 |
| minhash_dedup | 1028 | 18 | 1010 |
| quality_filter | 1010 | 108 | 902 |
| decontamination | 902 | 11 | 891 |

**Self-check (planted → removed):** exact_dup 10/10, near_dup 10/10, low_quality 6/6,
contamination 12/12 — every planted defect is caught.

The pipeline emits a machine-readable **data card** (`data/manifests/curation_pipeline_card.json`):
per-stage removals, per-source distribution before/after, thresholds, and a content hash
of the final doc set for reproducibility — the lineage/versioning artifact a frontier-lab
data buyer asks for.

### A real teaching point in the output

The source mix shifts `code 250 → 175`: **prose quality heuristics penalize code** (low
stop-word density, high symbol ratio). That is not a bug — it is the well-known lesson
that a single quality filter is not modality-neutral; production routes code through
code-specific filters. The data card surfaces this in `source_distribution_after` instead
of hiding it.

## Scope / honest limits

- Reference implementations at hobby scale (~1k docs), not a tuned production system; the
  contribution is transparent, tested mechanics + a reproducible data card.
- The fuzzy pass is char-cosine, a stand-in for the embedding-similarity step a real
  decontamination stage would run.
- Injections are clearly labeled in the data card (`injected_demo_records: true`); pass
  `--no-inject` to curate the raw corpus only.
