# Ontology Stress Tests

These tests ask how inherited materials labels project onto a learned
measurement/event space. Labels are probes and diagnostics, not the main objective.

## Candidate Tests

1. Functional utility: do raw/event embeddings improve prediction, compression,
   retrieval, or active sampling?
2. Label compactness: after raw/event training, do labels occupy compact latent regions?
3. Label boundary ambiguity: do disputed labels sit near latent boundaries?
4. Label splitting: do broad labels break into multiple latent neighborhoods?
5. Label merging: do distinct labels overlap when raw measurements and process metadata
   are modeled together?
6. Intervention relevance: do learned embeddings predict the next measurement or useful
   process change better than label-only baselines?

## Baselines

- Composition-only descriptors.
- Classical XRD peak features.
- Human labels.
- Supervised phase-classifier embeddings.
- Self-supervised raw-pattern embeddings.

## Initial NIST Baseline

Generated with:

```bash
python3 scripts/preprocess_xrd.py nist_mds2_2301
python3 scripts/run_ontology_tests.py nist_mds2_2301
python3 scripts/run_xrd_reconstruction.py nist_mds2_2301
```

First-pass result on the 192 human-labeled NIST samples:

- 73 rows have non-unanimous human labels.
- Composition/temperature alone predicts human-label disagreement strongly:
  grouped-by-temperature ROC-AUC 0.850.
- XRD PCA alone also predicts disagreement, but more weakly:
  grouped-by-temperature ROC-AUC 0.808 for 10 PCA components.
- Composition/temperature plus XRD PCA improves grouped ROC-AUC to 0.877.
- Consensus-label compactness is negative in composition/temperature space
  (-0.046 silhouette), but positive in XRD PCA space (0.140 for 10 PCA
  components).

Interpretation: this first check does not support a simple "raw XRD beats metadata"
story. It suggests label ambiguity is heavily tied to where samples sit in the
composition-temperature grid, while raw diffraction structure adds some predictive
signal and gives a more label-compact representation. This is a useful guardrail for
the next experiment: control for composition/temperature before claiming ontology-level
structure in raw measurements.

## Why PCA Before UMAP/t-SNE

PCA is the first reconstruction baseline because it defines an explicit linear basis,
supports out-of-sample transforms, and can reconstruct masked signal with a least-squares
fit over the observed 2-theta points. This makes it useful for objective feedback tasks.

UMAP and t-SNE are mainly visualization/neighborhood tools. They are stochastic,
hyperparameter-sensitive, and can make clusters look sharper or stranger than the source
geometry warrants. t-SNE has no natural inverse transform, and UMAP's inverse transform is
approximate rather than a clean reconstruction model. They may be useful later for plots,
but they should not be the first judge of representation quality.

## Initial Masked-XRD Reconstruction

Generated with:

```bash
python3 scripts/run_xrd_reconstruction.py nist_mds2_2301 --mask-widths 64 256 512 --repeats 3 --pca-components 5 10 25
```

Task:

```text
visible XRD regions -> hidden contiguous XRD region
```

Best first-pass results by mask width, using random folds and similar held-out-temperature
performance:

| Mask width | Metadata ridge MSE improvement | Best PCA missing-data MSE improvement | Interpolation behavior |
| --- | ---: | ---: | --- |
| 64 | 23.1% | 55.3% | Helps modestly |
| 256 | 20.2% | 54.4% | Worse than train mean |
| 512 | 21.3% | 53.8% | Much worse than train mean |

Interpretation: this is the first result that is closer to the Bitter Lesson framing.
We are not asking whether the representation matches human labels. We are asking whether
a representation learned from raw measurement structure can predict missing measurement
signal. Even a simple PCA basis does substantially better than metadata-only prediction
and train-mean prediction.

This does not mean PCA is the final model. It gives the minimum bar for future
self-supervised encoders: they must beat PCA missing-data reconstruction on held-out
raw-signal prediction before their latent spaces deserve much interpretation.
