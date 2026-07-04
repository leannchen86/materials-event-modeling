# Provenance protocol, second dataset: RRUFF Raman (+ Severson modality check)

Started 2026-07-03. This is the provenance-critique branch's named milestone
([PROJECTS.md](../../PROJECTS.md)): take the opXRD source-recoverability protocol
(revision 2, in-fold PCA + ablation + seed floor) and apply it to a *second experimental
dataset* so the finding stops being local. Two applications, one shared tool
(`scripts/run_provenance_leakage_audit.py`, core in
`src/materials_event_modeling/audit/provenance_leakage.py`):

1. **RRUFF mineral Raman — the second experimental XRD-like dataset.** Provenance label =
   the laser line (514 / 532 / 780 / 785 nm), the instrument axis. The opXRD result had a
   confound it could not resolve: its "source" was the archive directory, conflating lab
   with chemistry (different labs measured different materials). RRUFF fixes exactly that
   with `--rruff-paired`: restrict to specimens measured at ≥2 wavelengths, so within
   each specimen the *chemistry is identical* across label classes. Any recovery above
   chance there is instrument/laser imprint, not composition — the chemistry-matched
   control opXRD lacked.
2. **Severson battery — modality-generality + the rung-3 follow-on.** The A/B replication
   found trajectory features identify the collection batch at 94.5% via an ad-hoc probe;
   the recorded follow-on was to make that number come from the protocol tool, on exactly
   the A/B feature matrices (imported, not re-implemented). Provenance label = batch date.
   This also tests whether the protocol is XRD-specific or works on any event
   representation.

New tool capability (committed with the pre-registration, before results):
**grouped folds** (`StratifiedGroupKFold`). Without it, multiple rows from one specimen
(RRUFF) or one library straddle train/test and specimen identity inflates recoverability
— the exact leakage this branch exists to catch, so the tool must not commit it. RRUFF
folds group by specimen; Severson is one row per cell (no grouping needed).

## Null and hypotheses (committed before the run)

Null: provenance recoverability is an opXRD-specific artifact; on a second experimental
dataset, and after a chemistry-matched control, it disappears.

- **H1 (replication).** On RRUFF full set, the laser line is recoverable from the Raman
  spectrum PCA well above chance, specimen-grouped: expected leakage_score ≥ 0.50
  (severe), balanced accuracy ≥ 0.6 vs chance 0.25 (4 classes). *Falsifier:* score below
  the elevated band (0.15) → the opXRD provenance finding does not generalize to a second
  experimental dataset, and the branch's central claim is local. Metadata (point count,
  cm⁻¹ range) is expected severe too — different lasers have characteristic ranges.
- **H2 (chemistry-matched, the decisive control).** Under `--rruff-paired` (identical
  chemistry within each specimen group), the laser line is *still* recoverable from the
  spectrum above chance: expected leakage_score ≥ 0.30 (elevated or severe). *Falsifier:*
  paired score drops to clean (< 0.15) → the full-set recovery was chemistry (different
  minerals happen to be measured at different lasers), not instrument imprint, and the
  "models learn the instrument" reading is not supported once chemistry is controlled.
  This is the hypothesis opXRD could not test.
- **H3 (control efficacy).** Crop-to-common-range + derivative reduces spectral
  recoverability but does not neutralize it (stays ≥ elevated), matching the opXRD
  pattern that normalization cannot be trusted to remove provenance.
- **H4 (modality generality, Severson).** Batch date is recoverable from the A/B
  trajectory features above chance (3 batches, chance ≈ 0.36 balanced): expected
  leakage_score ≥ 0.50, reproducing the ad-hoc 94.5% via the protocol tool; and from the
  raw QDischarge curve too. The paper-shape (policy) features also recover batch
  (designed nesting), reported as a measured confound, not a surprise.
- **H5 (grouped-fold necessity).** On RRUFF, ungrouped folds report materially higher
  recoverability than specimen-grouped folds for the spectrum features — demonstrating
  the leakage the grouped-fold fix removes. Reported as a methods result (how much a
  naive audit would over-state).

**Decision this changes:** whether the provenance protocol is publishable as
cross-dataset (the branch's stated bar) or remains an opXRD-local diagnostic — and
whether the chemistry-matched instrument-imprint claim (stronger than opXRD's) is earned.

Run commands:

```
.venv/bin/python scripts/run_provenance_leakage_audit.py --dataset rruff \
  --include-controls --cv-repeats 3 --output data/manifests/provenance_leakage_audit_rruff.json
.venv/bin/python scripts/run_provenance_leakage_audit.py --dataset rruff --rruff-paired \
  --include-controls --cv-repeats 3 \
  --output data/manifests/provenance_leakage_audit_rruff_paired.json
.venv/bin/python scripts/run_provenance_leakage_audit.py --dataset severson_ab --cv-repeats 3 \
  --output data/manifests/provenance_leakage_audit_severson_ab.json
```

## Results

*(to be filled by the run — verdict against H1–H5 goes here)*
