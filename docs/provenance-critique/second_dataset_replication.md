# Provenance protocol, second dataset: RRUFF Raman (+ Severson modality check)

> **Read with [../spine/data_assumptions_and_limits.md](../spine/data_assumptions_and_limits.md).**
> All numbers here are on public data; the effect's *existence* and the chemistry-matched
> *decomposition* are structural, but the specific magnitudes (0.142, 0.765, 0.898) are
> sample-dependent and must not be quoted as representative.

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

## Results (run 2026-07-03, commit `d249223`, three manifests)

**Findings first.** The provenance protocol replicates on a second experimental dataset
and generalizes across modality — but the chemistry-matched control reshapes the claim in
a way opXRD could not. On RRUFF the laser line is strongly recoverable (severe) from
acquisition metadata and spectral coverage, and this *survives chemistry-matching*
(0.765 / 0.709, paired) — but recovery from the spectral *content* is only barely elevated
on the full set (0.155) and drops to **clean (0.142)** once chemistry is matched. So the
RRUFF spectral-content recovery is itself mostly chemistry (it vanishes under the
chemistry-matched control); by analogy the opXRD spectrum→source 0.743 is plausibly
chemistry-loaded too, though that is a cross-dataset inference, not a same-dataset
measurement on opXRD. What IS directly measured: the chemistry-invariant provenance
signal on RRUFF lives in *acquisition geometry* (point count, coverage), not the
fingerprint. On Severson the
protocol reproduces the ad-hoc 94.5% batch probe from the tool (balanced accuracy 0.932)
and works on battery cycling, confirming modality generality.

### RRUFF full set (specimen-grouped folds, 4 laser classes, chance 0.25)

| feature set | leakage | bal-acc ± std | severity |
| --- | ---: | ---: | --- |
| coverage_mask_pca | 0.700 | 0.775 ± 0.008 | severe |
| metadata (range, points) | 0.657 | 0.743 ± 0.010 | severe |
| spectrum_summary | 0.213 | 0.410 ± 0.019 | elevated |
| raman_pca (spectral content) | 0.155 | 0.366 ± 0.010 | elevated |
| crop_raman_derivative_pca (control) | 0.064 | 0.298 ± 0.009 | clean |

Control efficacy: raman_pca 0.155 → 0.064, 59% reduction, **neutralized** (the spectral
content carried little to begin with).

### RRUFF chemistry-matched (`--rruff-paired`: specimens measured at ≥2 wavelengths)

| feature set | leakage | bal-acc ± std | severity |
| --- | ---: | ---: | --- |
| metadata | 0.765 | 0.823 ± 0.009 | severe |
| coverage_mask_pca | 0.709 | 0.782 ± 0.006 | severe |
| spectrum_summary | 0.215 | 0.412 ± 0.018 | elevated |
| raman_pca (spectral content) | **0.142** | 0.357 ± 0.008 | **clean** |
| crop_raman_derivative_pca | 0.054 | 0.290 ± 0.009 | clean |

With chemistry held identical within each specimen group, spectral-content recovery falls
below the elevated threshold while metadata/coverage stay severe — the decomposition
opXRD could not perform. Paired-set class balance (chance 0.25 balanced): 532nm 2198,
780nm 1541, 785nm 625, 514nm 378 over 2,206 specimens — not degenerate.

**Is metadata-severe circular?** Partly — the cm⁻¹ *window* a laser reaches is physics
(514nm can access higher wavenumbers), and `cm_max` alone recovers 0.764, so that one
feature is semi-tautological. But the acquisition-geometry signal survives removing it:
metadata with **all range features dropped** still recovers **0.591 (severe)**, point
count alone recovers **0.534**, and among the three near-identical-range lasers
(532/780/785, dropping 514) non-range metadata still recovers **0.396 (elevated)** — a
separation that cannot be range-tautology at all. Point count (514nm ~1,089 points vs
~2,270–2,400 for the others) is a detector/operator setting, not the wavelength relabeled.
So the acquisition-geometry provenance is a real instrument/operator imprint; the cm-range
is the single strongest metadata feature but it is not what the claim rests on.

### Severson A/B features (batch label, 3 batches, chance ≈ 0.36 balanced)

| feature set | leakage | bal-acc ± std | severity |
| --- | ---: | ---: | --- |
| a_trajectory_k100 (A/B features) | 0.898 | 0.932 ± 0.032 | severe |
| qd_curve_pca (raw discharge curve) | 0.830 | 0.886 ± 0.079 | severe |
| b_policy (paper-shape recipe) | 0.440 | 0.626 ± 0.054 | elevated |

### Verdict against the pre-registered hypotheses

- **H1 — replicates, but reshaped.** Provenance IS recoverable severe on a second
  experimental dataset, satisfying the branch's replication bar — but from metadata
  (0.657) and coverage (0.700), not from the spectral content (0.155, barely elevated;
  predicted ≥0.50 severe). The falsifier (below elevated) did not fire, so the finding
  generalizes; but the *locus* differs from opXRD, where the spectrum itself scored
  0.743. Read together with H2, that opXRD spectral number is *plausibly* chemistry-loaded
  too — but that is a cross-dataset inference, not a same-dataset measurement on opXRD (no
  chemistry-matched control was ever run there); the directly measured claim is only that
  on RRUFF, chemistry-matching removes spectral recovery.
- **H2 — falsifier FIRES for the spectral claim; the geometry claim survives and is
  stronger.** Predicted paired spectral recovery ≥0.30; actual 0.142, clean. So once
  chemistry is matched, the Raman *fingerprint* does not carry the laser line above
  threshold — the "models learn the instrument from the spectrum" reading is NOT
  supported by the control. What *is* supported, and is new: metadata and coverage stay
  severe under chemistry-matching (0.765 / 0.709), driven substantially by point count (a
  detector setting, not wavelength physics — see above), so labs/instruments imprint via
  *acquisition geometry* independent of what was measured. This is a more precise claim
  than opXRD's, which could not separate instrument from chemistry at all.
- **H3 — partially falsified, informatively.** The spectral control *neutralizes*
  (predicted: reduces-but-not-neutralize) — but only because the spectrum barely carried
  provenance. At the dataset level the opXRD lesson holds for a sharper reason:
  spectral normalization cannot touch the severe signal because that signal lives in
  coverage/metadata, not the spectrum. The protocol recommendation updates: report and
  control *acquisition geometry* first, not just spectral normalization.
- **H4 — CONFIRMED.** Batch date is recovered severe from the A/B trajectory features
  (0.898, balanced accuracy 0.932 — the ad-hoc 94.5% probe, now produced by the protocol
  tool as its recorded follow-on) and from the raw discharge curve (0.830). The
  paper-shape recipe also recovers batch at elevated (0.440), the designed policy→batch
  nesting, reported as a measured confound. The protocol is not XRD-specific.
- **H5 — FALSIFIED, with a clarifying mechanism.** Grouped vs ungrouped folds made no
  material difference on RRUFF (raman_pca 0.145 ungrouped vs 0.155 grouped; metadata
  0.658 vs 0.657). Reason: a RRUFF specimen is measured at *several* laser lines, so the
  specimen group spans multiple label classes — specimen identity does not predict the
  label, so there is no memorization shortcut to remove. Grouped folds matter when a
  group nests *within* one provenance class (HTEM positions within a library, one
  library = one lab); they are correct-by-construction here and load-bearing for future
  within-library audits, but not for this design. Kept in the tool; the pre-registered
  expectation was simply wrong about where it bites.

### Decision

The provenance-critique branch's stated bar — replicate the opXRD finding on a second
appropriate experimental dataset before it supports a broad shortcut claim — is **met**:
provenance recoverability replicates on RRUFF Raman (severe) and generalizes to a
non-spectral modality on Severson (severe). The replication also *upgrades* the claim: the
chemistry-matched control localizes the robust, composition-invariant provenance signal to
acquisition geometry/coverage/metadata, and shows that spectral-content recovery can be
mostly chemistry — a decomposition the single-dataset opXRD result could not make and a
sharper recommendation for representation papers (audit and control coverage/acquisition
metadata, report leave-one-source-out, and do not assume spectral normalization removes
provenance). Publishability: this is now a genuine cross-dataset methods result with a
control that strengthens rather than merely repeats it.

Current decision (2026-07-12): the public-data branch is closed. The chemistry-matched-control
framing now lives in `provenance_leakage_audit.md`; HTEM model extensions and one-off replication
scripts were retired to Git history. Provenance recoverability remains a maintained control inside
the prospective compression program, not a reason to add a third public leaderboard.
