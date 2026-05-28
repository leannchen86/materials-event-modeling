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
