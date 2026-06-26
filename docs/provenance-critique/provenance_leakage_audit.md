# Provenance-recoverability audit

A reusable, dataset-agnostic diagnostic that answers one question: **how much of an
*incidental* provenance label can a simple model recover from a record's features?**

- **Core:** [`src/materials_event_modeling/audit/provenance_leakage.py`](../../src/materials_event_modeling/audit/provenance_leakage.py) — modality-agnostic, `numpy` + `scikit-learn` only.
- **CLI / adapters:** [`scripts/run_provenance_leakage_audit.py`](../../scripts/run_provenance_leakage_audit.py)
- **Tests:** [`tests/test_provenance_leakage.py`](../../tests/test_provenance_leakage.py)

It unifies the four ad-hoc opXRD scripts (`analyze_opxrd_source_predictability`,
`analyze_opxrd_normalization_controls`, `analyze_opxrd_source_diagnostics`,
`run_opxrd_source_transfer`) behind one tool with a normalized 0–1 recoverability score,
a heuristic `clean / elevated / severe` risk band, and a control-efficacy check.

## Scope

This is a materials-measurement diagnostic. It asks whether source-associated variation is
recoverable from a spectrum or its metadata. A high score warrants coverage controls,
source/session-held-out evaluation, and a downstream sensitivity check. It does **not**
by itself establish contamination, an instrument effect, or a downstream shortcut.

## What it measures

For each feature representation, a balanced logistic-regression probe (vs a
most-frequent baseline) under stratified k-fold recovers the provenance label. The
balanced accuracy is normalized against chance:

```
recoverability_score = (balanced_accuracy − chance) / (1 − chance)   # 0 at chance, 1 at perfect recovery
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

| feature set | recoverability | bal-acc | risk |
| --- | ---: | ---: | --- |
| metadata | 0.974 | 0.978 | severe |
| coverage_mask_pca | 0.878 | 0.898 | severe |
| xrd_pca (raw spectra) | 0.743 | 0.786 | severe |
| spectrum_summary | 0.602 | 0.668 | severe |
| crop_xrd_derivative_pca (strongest control) | 0.467 | 0.556 | elevated |

**Control efficacy:** raw `full_xrd_pca` (0.743) → `crop_xrd_derivative_pca` (0.467) =
37% recoverability reduction, **still elevated**. Read: coverage-related metadata
distinguishes sources strongly, and aggressive preprocessing only partially reduces that
association. Treat source as a risk factor to control and test, not as an effect that
normalization has removed.

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
- A high score flags collection-associated variation, not a proven downstream failure or
  a causal attribution to instrumentation.
