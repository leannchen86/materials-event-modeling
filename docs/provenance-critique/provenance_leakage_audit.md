# Provenance-leakage audit

A reusable, dataset-agnostic diagnostic that answers one question: **how much of an
*incidental* provenance label can a simple model recover from a record's features?**

- **Core:** [`src/materials_event_modeling/audit/provenance_leakage.py`](../../src/materials_event_modeling/audit/provenance_leakage.py) — modality-agnostic, `numpy` + `scikit-learn` only.
- **CLI / adapters:** [`scripts/run_provenance_leakage_audit.py`](../../scripts/run_provenance_leakage_audit.py)
- **Tests:** [`tests/test_provenance_leakage.py`](../../tests/test_provenance_leakage.py)

It unifies the four ad-hoc opXRD scripts (`analyze_opxrd_source_predictability`,
`analyze_opxrd_normalization_controls`, `analyze_opxrd_source_diagnostics`,
`run_opxrd_source_transfer`) behind one tool with a normalized 0–1 leakage score, a
`clean / elevated / severe` verdict, and a control-efficacy check.

## Why this is two things at once

- **For materials (this repo's thesis):** it is the "models learn the lab" diagnostic —
  source/instrument/preprocessing identity is recoverable from public experimental XRD
  even after normalization, so apparent representation gains can be silent *collection
  artifacts*.
- **For LLM-pretraining data curation:** it is mechanically a **contamination /
  collection-artifact detector**. The provenance label is "which source/snapshot/
  benchmark did this record come from"; if a feature representation recovers it well
  above chance, a model trained on it can shortcut — the failure mode benchmark
  *decontamination* exists to prevent. Records here are spectra; on a text corpus they
  would be document embeddings or hashed n-grams. The audit is the same.

## What it measures

For each feature representation, a balanced logistic-regression probe (vs a
most-frequent baseline) under stratified k-fold recovers the provenance label. The
balanced accuracy is normalized against chance:

```
leakage_score = (balanced_accuracy − chance) / (1 − chance)   # 0 at chance, 1 at perfect recovery
```

Verdict bands (heuristic, tunable): `clean < 0.15 ≤ elevated < 0.50 ≤ severe`.

With `--include-controls` it also asks the **remediation** question — does a
preprocessing control neutralize the confound? — by comparing the raw representation to
the strongest control (coverage-crop + row z-score + derivative).

## Result on opXRD (reproduces the prior runs)

```
.venv/bin/python scripts/run_provenance_leakage_audit.py --dataset opxrd --include-controls
```

6 sources, 4093 spectra, chance balanced-acc 0.167:

| feature set | leakage | bal-acc | severity |
| --- | ---: | ---: | --- |
| metadata | 0.974 | 0.978 | severe |
| coverage_mask_pca | 0.878 | 0.898 | severe |
| xrd_pca (raw spectra) | 0.743 | 0.786 | severe |
| spectrum_summary | 0.602 | 0.668 | severe |
| crop_xrd_derivative_pca (strongest control) | 0.467 | 0.556 | elevated |

**Control efficacy:** raw `full_xrd_pca` (0.743) → `crop_xrd_derivative_pca` (0.467) =
37% leakage reduction, **still elevated**. Read: even coverage-just metadata recovers the
lab almost perfectly (0.97), and aggressive preprocessing only partially removes the
confound — so source must be treated as a confound (stratify / leave-one-source-out),
not assumed away by normalization.

## Adding a dataset

Write one adapter returning `{feature_sets, labels, control_pairs, meta}` and register it
in `DATASETS` in the CLI. No change to the core. Natural next target: NIST or HTEM (both
already audited in `data/manifests/`), to make this a *protocol applied across ≥2
datasets* rather than a single-dataset diagnostic.

## Scope / honest limits

- Random folds answer whether the imprint is **present**, not whether it **generalizes
  to unseen sources**. The leave-one-source-out *reconstruction* transfer
  (`run_opxrd_source_transfer.py`, needs torch) is the deeper layer and can be folded in
  as a third audit stage later.
- A high score flags a contamination *risk*, not a proven downstream failure.
