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

## Revision 1 result on opXRD (reproduces the prior runs — superseded, see Revision 2)

> **Methodological caveat (found 2026-07-02, fixed in Revision 2):** these numbers were
> produced with PCA fit on the full matrix *before* cross-validation (transductive), so
> test rows shaped the basis and PCA-based scores are somewhat inflated; the `metadata`
> set also included `is_labeled`, a dataset-curation flag that is near-deterministic per
> source. Retained for the record; quote Revision 2 numbers externally.

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

## Revision 2 (pre-registered 2026-07-03): in-fold PCA, curation-flag ablation, seed floor

Ladder placement: rung 2 (audit-power) of `docs/spine/event_grammar_validation_note.md`;
serves the evidence hygiene of the provenance protocol before second-dataset replication.
Null attacked: the Revision 1 numbers survive honest evaluation unchanged.

Three defects to fix (surfaced by external review 2026-07-02):

1. **Transductive PCA.** PCA was fit on all 4,093 spectra before `StratifiedKFold`; only
   scaler + logistic regression sat inside the fold. Fix: PCA now fits inside each fold
   on the train split only (`pca_components` in the audit core).
2. **Curation-flag tautology.** `is_labeled` (labeled fraction per source:
   1.0/1.0/1.0/0.04/0.0/0.0) nearly dichotomizes the sources by bookkeeping, not physics.
   Fix: default `metadata` drops it; `metadata_plus_curation` keeps the old 8-feature set
   for transparency; `--feature-ablation` audits every metadata feature alone.
3. **Single-seed, threshold-adjacent verdict.** The quotable "elevated, not severe" call
   (0.467 vs the 0.50 cutoff) rested on one CV seed, 3 folds. Fix: `--cv-repeats 3` pools
   folds across shifted seeds; verdicts near a band boundary must be reported as
   mean ± std.

Pre-registered hypotheses and expected numbers (written and committed before the run):

- **H1 (in-fold PCA):** spectral recoverability drops slightly but stays severe.
  Expected: `xrd_pca` bal-acc 0.786 → 0.70–0.79, score ≥ 0.50. *Falsifier:* score below
  0.50 means the "recoverable from spectra" claim was substantially a CV artifact →
  retract the spectra claim (metadata claim unaffected) and re-report everywhere it is
  quoted.
- **H2 (drop `is_labeled`):** metadata stays severe without the curation flag. Expected:
  score 0.974 → ≥ 0.85 (theta range/points are near-deterministic per source).
  *Falsifier:* score < 0.50 means the headline metadata number was mostly bookkeeping.
- **H3 (feature ablation):** `theta_min` / `theta_max` / `theta_span` and `is_labeled`
  are each individually elevated-or-severe; intensity features are weaker.
- **H4 (seed floor):** `crop_xrd_derivative_pca` mean ± std straddles or approaches the
  0.50 boundary → the published claim downgrades from "elevated, not severe" to
  "borderline elevated/severe (≈0.40–0.55)".
- **Decision this changes:** whether the tool can be applied as-is to the second dataset
  (protocol replication) and quoted externally.

Run command:

```
.venv/bin/python scripts/run_provenance_leakage_audit.py --dataset opxrd \
  --include-controls --feature-ablation --cv-repeats 3 \
  --output data/manifests/provenance_leakage_audit_opxrd_r2.json
```

### Revision 2 results

*(to be filled by the run — verdict against H1–H4 goes here)*

## Adding a dataset

Write one adapter returning `{feature_sets, labels, control_pairs, pca_spec, meta}` and
register it in `DATASETS` in the CLI. Matrices named in `pca_spec` are reduced by PCA
*inside* each fold. No change to the core. Natural next target: NIST or HTEM (both
already audited in `data/manifests/`), to make this a *protocol applied across ≥2
datasets* rather than a single-dataset diagnostic.

## Scope / honest limits

- Random folds answer whether the imprint is **present**, not whether it **generalizes
  to unseen sources**. The leave-one-source-out *reconstruction* transfer
  (`run_opxrd_source_transfer.py`, needs torch) is the deeper layer and can be folded in
  as a third audit stage later.
- A high score flags collection-associated variation, not a proven downstream failure or
  a causal attribution to instrumentation.
