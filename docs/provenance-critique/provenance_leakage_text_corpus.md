# Provenance leakage in a pretraining corpus (the text demo)

The same modality-agnostic audit ([provenance_leakage.py](../../src/materials_event_modeling/audit/provenance_leakage.py))
that catches instrument fingerprints in opXRD spectra, pointed at an **LLM pretraining
mix**. The provenance label is now the document **source**; the finding is the text
analog of "models learn the lab."

This is the decontamination-relevant version of the result: if an *incidental* source
label is trivially recoverable from a corpus, then (a) a "balanced" data mix still lets a
model shortcut on source identity, (b) a learned quality filter is partly just a source
classifier, and (c) a random train/eval split silently leaks source — you must stratify.

## Corpus

A ~1,000-document mix pulled from four genuinely distinct pretraining sources, ~250 each,
via public APIs (no `datasets` dependency):

| source | origin | endpoint |
| --- | --- | --- |
| `web` | FineWeb (CommonCrawl) sample-10BT | HF datasets-server `/rows` |
| `wikipedia` | `wikimedia/wikipedia` 20231101.en | HF datasets-server `/rows` |
| `code` | `Nan-Do/code-search-net-python` | HF datasets-server `/rows` |
| `science` | arXiv abstracts (cond-mat, cs.LG, …) | arXiv Atom API |

Rebuild: `.venv/bin/python scripts/fetch_text_corpus.py --per-source 250`
(writes `data/raw/text_corpus/mix.jsonl`; raw data is git-ignored, the audit result is
committed under `data/manifests/`).

## Feature sets — escalating from trivial to topical

| feature set | what it is | why it matters |
| --- | --- | --- |
| `surface_metadata` | ~12 cheap stats (length, punctuation/digit/upper rates, type-token ratio, code-symbol rate, sentence length) | the trivial-features baseline — the text analog of opXRD `metadata` |
| `function_words` | per-doc rate of each English stop word | **topic-agnostic** style/register fingerprint (no content words) |
| `char_ngram_svd` | char 3–5gram TF-IDF → SVD(64) | orthographic/byte style |
| `content_tfidf_svd` | word 1–2gram TF-IDF (stopwords removed) → SVD(64) | topical content |

## Result

```
.venv/bin/python scripts/run_provenance_leakage_audit.py --dataset text
```

4 sources, 1000 docs, chance balanced-acc 0.250:

| feature set | leakage | bal-acc | severity |
| --- | ---: | ---: | --- |
| content_tfidf_svd | 0.971 | 0.978 | severe |
| char_ngram_svd | 0.952 | 0.964 | severe |
| surface_metadata | 0.881 | 0.911 | severe |
| function_words | 0.849 | 0.887 | severe |

**Every** level is severe. Topical content recovering the source (0.98) is unsurprising.
The point is the bottom two rows: **pure function-word style (0.89) and twelve trivial
surface statistics (0.91) recover the source almost as well** — with zero topical
information. The source fingerprint is pervasive and not removable by dropping content,
exactly as opXRD's lab identity survived spectral normalization. The remediation is
therefore not a normalization knob; it is to **stratify by source** for any held-out
eval and to treat quality/dedup filters as source-confounded.

## Why this is the pretraining-curation artifact

- It is mechanically a **collection-artifact / contamination detector** on real
  pretraining text, reusing the identical core that produced the materials result — so
  it demonstrates the audit abstraction was real, not bolted on.
- It maps to the curation tasks a frontier-lab data pipeline owns: source-aware
  dedup/decontamination, leak-proof eval splits, and not mistaking a source classifier
  for a quality classifier.

## Scope / honest limits

- Random folds show the source imprint is **present**; a leave-one-source-out split
  measures whether a downstream model actually shortcuts on it.
- The mix is small (~1k docs) and the sources are deliberately distinct, so high
  recoverability is expected — the contribution is the *tool and the framing*, a reusable
  audit that quantifies and ranks leakage across feature levels on any labeled corpus.
- This audit detects *source/provenance* leakage; n-gram **benchmark** decontamination
  (train text containing eval items) is a complementary check and a separate tool.
