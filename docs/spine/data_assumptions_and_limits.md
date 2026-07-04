# Data Assumptions and Limits

As of 2026-07-03. Every result in this repo so far is on **public data**, which carries
assumptions that the strong-sounding numbers must be read against. This note states them
plainly and, per result, marks what is **structural** (robust to the data being imperfect)
versus **sample-dependent** (a magnitude that must not be quoted as representative).

Two of these are now machine-measured — the conformance report's `selection_risk` block
flags success-bias and provenance-unit scarcity (`src/materials_event_modeling/grammar/
conformance.py`). The other four are not visible in the data and live here as prose. That
split is the point: **absence of a flag is not absence of bias.**

## The assumptions

### 1. Selection / survivorship bias (the largest, and it cuts against our thesis)

Public data is what got published and deposited. That filter is especially awkward for a
project arguing that failed/ambiguous outcomes are informative:

- The coverage study found **5 of 6 datasets record zero negative outcomes** (`selection_
  risk.success_bias_risk = high_no_negatives_recorded` for Durham, oleogel, NIST, RRUFF,
  HTEM). From the outside, "all successes" and "failures filtered out" are
  indistinguishable. Only Severson has retained negatives, and only because we
  reconstructed them from capacity curves (7 of 135).
- **RRUFF is a pre-filtered subset by name** — `excellent_unoriented`. The low-SNR,
  ambiguous spectra that would most stress "labels are lossy near hard cases" are already
  gone.
- These are **popular ML benchmarks** (Severson especially), curated with modeling in
  mind, which can smooth the exact pathologies we study.

*Not machine-measurable beyond the success-bias flag; publication/pre-filtering bias is
invisible in the events.*

### 2. Provenance labels are bundled proxies, not clean axes

Every "source" label is a bundle wearing one name:

- **opXRD "source" = the archive folder** — conflates lab, instrument, and chemistry. This
  confound is why the RRUFF chemistry-matched control mattered.
- **Severson "batch" = a date** — also bundles manufacturing lot, calendar aging, and
  protocol refinement. "Trajectory recovers batch at 0.898" is partly cell-lot, not only
  instrument style.
- **RRUFF "laser line"** correlates with era and with which minerals get run at which
  laser; the chemistry-matched control removed the chemistry part (which is why that result
  is the exception that got *sharper*).

### 3. "Raw" measurements are already processed

Everything called raw passed through a stranger's pipeline (background subtraction,
normalization, peak-finding, gridding) before we saw it; for RRUFF we took the "Processed"
export. So the raw-measurement thesis is really "lightly-cooked-by-someone-else," and the
provenance we detect is partly the lab's *software* fingerprint. The acquisition-geometry
finding (point count separates lasers) is a clean example: a config/detector artifact,
legitimate as provenance but not physics.

### 4. Few independent units

Claims rest on a handful of actual sources: **~6 opXRD contributors, 4 RRUFF lasers, 3
Severson batches.** The `selection_risk.few_provenance_units_risk` flag catches this —
notably it fires **high on Severson (min 3 units)** even though Severson is our *best*
dataset (L3): held-out-batch was a 3-fold split, and the ranking result leaned on ~24
replicate pairs, 82% from 5 policy groups. Lots of rows, few independent clusters, and
provenance claims live at the cluster level.

### 5. Most datasets aren't "making" events

The thesis targets material-*making* trajectories. But minerals (RRUFF) are collected, not
made; batteries (Severson) are only *cycled*, not synthesized; HTEM is finished-library
characterization. Even the richest data is often repeated measurement of a finished object,
which the grammar's `trace_richness` metric flags. On-thesis data (logged synthesis with
retained failures) is exactly what public repos lack — the reason `controlled-collection`
exists.

### 6. Method-side distributional assumptions

The models assume things the data may violate: PCA/ridge assume low intrinsic dimension and
roughly linear, stationary feature–target relationships; interpolation assumes smoothness
(the oleogel campaign already showed the "clock" baseline dominates on smooth trajectories);
the cluster bootstrap assumes exchangeable groups (Severson's 5 big batch-3 groups dominate,
so few effective clusters). Balanced accuracy vs chance assumes meaningful class structure;
RRUFF wavelength classes are imbalanced (532nm dominant).

## Structural vs sample-dependent, per result

| result | claim | robustness |
| --- | --- | --- |
| Severson A/B | paper-shape forced to 0.500 on replicate ranking; can't hold censored runs | **Structural** — true by construction on any dataset with replicates + censoring |
| Severson A/B | grammar ranks replicates at 0.756 [0.68, 0.80] (ridge) | **Sample-dependent** — selection-biased, few clusters, forest arm at chance edge |
| Severson A/B | trajectory transfers across policies/batches; recipe anti-predicts | **Mostly structural** (direction) / magnitude sample-dependent |
| Provenance protocol | recoverability replicates on a 2nd experimental dataset + a 2nd modality | **Structural** (existence) — the effect is present on independent data |
| Provenance protocol | chemistry-matched control: spectral recovery → clean, geometry stays severe | **Structural decomposition**, but the specific 0.142/0.765 values are RRUFF-specific |
| Provenance protocol | opXRD 0.743 spectrum→source is plausibly chemistry-loaded | **Inference, not measured** — cross-dataset, never controlled on opXRD |
| Coverage study | grammar expresses 6 datasets with no schema change | **Structural** — expressiveness, not sample |
| Any effect size | the actual magnitudes (0.756, 0.898, 0.492…) | **Sample-dependent** — do not quote as representative of the world |

## What this implies

The public-data work shows these effects **exist** and, in several cases, are **structurally
forced** — on data cleaner and more success-biased than reality. It does **not** show the
magnitudes are representative, and cannot, with this data. That is not a defect of the
analysis; it is the stated reason the project treats public datasets as
sandboxes/feasibility checks and holds `controlled-collection` (where selection, failure
retention, and provenance logging are under our control) as the destination. Read every
sample-dependent number in the repo with this note attached.
