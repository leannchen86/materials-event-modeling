# Quantitative Early-Trace Input — X60 Draft Specification

Status: **draft; freeze-blocking until instrument-specific axes, transformations, timing windows,
quality rules, and feature schema are certified**. Companion preregistration:
[pilot_design_prereg.md](pilot_design_prereg.md). This specification defines both the shared
planned context `C` and the primary `C + X60` arm.

## Purpose and boundary

`X60` is the complete **quantitative** record of the material state sampled during the first
60 minutes for the confirmatory arm: early XRD, contemporaneous pH and temperature, and relative
process/acquisition timing. It excludes video, images, visual-state categories, free-form notes,
human phase labels, `L60`, `S60`, and every 24-hour observation or derivative.

`X60` does not mean an unmediated or literally unprocessed measurement. Native files are retained
as immutable upstream evidence; the confirmatory model receives a deterministic, minimally
processed representation whose exact transformations are frozen below. No feature may be selected
because it correlates with a pilot outcome.

Items marked `UNRESOLVED` depend on the partner instrument or dry run and block the pilot freeze.

## Two clocks: sampled state versus assay availability

The early XRD measurements are ex-situ scans of aliquots withdrawn and arrested during the first
60 minutes. The aliquot's **state time** is completion of its validated arrest/fixation; its XRD
file may be created later after drying and scanning. Therefore every observation must record:

- first-contact timestamp, which defines elapsed time zero;
- aliquot withdrawal timestamp and elapsed time;
- arrest/rinse start and completion timestamps;
- drying completion timestamp when observable;
- XRD acquisition start/end timestamps; and
- feature-construction timestamp.

A later scan is allowed in X60 only as an assay of a specimen fixed by the cutoff. It cannot use
later mother-liquor state, the 24-hour specimen, final labels, or outcome-informed processing. The
resulting task is **prediction from material sampled by 60 minutes**, not necessarily a real-time
decision delivered at 60 minutes. Any operational claim must separately report assay turnaround.

For an ex-situ aliquot, **state time is completion of the validated irreversible arrest/fixation
step**, not withdrawal start. The nominal 60-minute aliquot must be withdrawn early enough that
arrest completes at or before 60:00. An acceptance window permitting later completed arrest changes
the state cutoff and requires a pre-freeze amendment. The maximum withdrawal-to-arrest lag and the
acceptance windows for the nominal 5-, 15-, and 60-minute state times are `UNRESOLVED` freeze items.
Before freeze, non-pilot specimens must demonstrate that the arrest, rinse/dry, storage, and delayed
scan workflow preserves the state to the accuracy required by this task; otherwise ex-situ XRD
cannot support a sampled-by-60-minute claim.

## Shared planned context C

The confirmatory `C` arm contains exactly the four planned factorial variables from
`pilot_assignment.csv`:

| field | unit / encoding |
| --- | --- |
| `concentration_m` | numeric mol/L; the planned common CaCl2/Na2CO3 concentration |
| `temperature_c` | numeric degrees C; planned reaction temperature |
| `mg_ratio` | numeric mol Mg per mol Ca |
| `mixing_route` | fixed one-hot vocabulary: `fast_no_aging`, `slow_30min_aging` |

Numeric scaling is fitted within each training fold. No additional recipe field may enter C without
a committed pre-freeze revision.

The following are explicitly excluded from C and from the confirmatory model matrix:

- `event_id`, `condition`, `event_group_id`, and replicate number;
- session/day, operator, reagent lot, run order, instrument, scan order, filenames, or hashes;
- actual process measurements or deviations; and
- any label, outcome, availability reason, or future quality flag.

These excluded fields remain in the event ledger for splitting, lineage, support reporting, and
provenance audits. The arbitrary integer `condition` is not used as a fifth recipe feature because
the four factorial variables already define the condition.

## Required X60 observation slots

The primary input has three frozen aliquot slots:

| slot | intended specimen state | required quantitative observations |
| --- | --- | --- |
| `t05` | nominal 5-minute completed arrest | XRD, pH, temperature, timing |
| `t15` | nominal 15-minute completed arrest | XRD, pH, temperature, timing |
| `t60` | nominal state irreversibly arrested at or before the 60-minute cutoff | XRD, pH, temperature, timing |

Before freeze, define non-overlapping acceptance windows and a deterministic rule for mapping an
actual aliquot to a slot. If two aliquots qualify, select the primary specimen by a rule fixed
without outcomes—never the cleaner pattern or better model result. Repeats, repackings, and rescans
remain linked observations; the rule designating a primary scan is frozen in advance.

A planned aliquot that produces a valid blank-like/no-solid XRD pattern is still an observed slot.
`No signal` is physical content, not missingness. A slot is unavailable only under the frozen
timing, lineage, preparation, instrument, or file-validity rules.

## XRD source and confirmatory representation

### Immutable source

For every slot, retain the instrument-native file byte-for-byte plus an exported numeric count
table when needed. Hash both and record:

- instrument and configuration identifiers;
- radiation/wavelength, geometry, 2theta range, step, dwell/exposure, optics, and detector mode;
- holder, packing/preparation route, calibration state, and scan order;
- native units and every correction already applied by instrument software; and
- raw-export software/profile and version.

These metadata support audit and reconstruction. Direct provenance identifiers are not model
features unless a later, separately preregistered analysis says otherwise.

### Provisional confirmatory numeric channels

The provisional XRD input for each slot is:

1. an exposure/monitor-corrected intensity pattern linearly resampled to one frozen common
   2theta grid and normalized to unit nonnegative integrated area; and
2. one scalar `log_integrated_intensity` calculated before unit-area normalization, so the model
   does not silently lose all measured scale information.

For corrected intensity `I_corr(theta)`, the provisional transformation is

\[
A=\int_{\theta_{\min}}^{\theta_{\max}}\max(I_{\mathrm{corr}}(\theta),0)\,d\theta,
\qquad
I_{\mathrm{shape}}(\theta)=\frac{\max(I_{\mathrm{corr}}(\theta),0)}{\max(A,\epsilon)},
\]

with `log_integrated_intensity = log1p(A)`. The epsilon, integration method, exposure/monitor
correction, and treatment of negative corrected values must be fixed from instrument behavior.

This is a provisional choice, not permission to improvise. Before freeze, the instrument dry run
must fill and hash the following table:

| item | required frozen value |
| --- | --- |
| axis | `2theta` in degrees and radiation/wavelength metadata |
| common range | numeric `theta_min`, `theta_max`, using the supported overlap across all planned scans |
| grid | numeric step and endpoint convention; no finer than justified by native sampling/resolution |
| correction | exact dark/dead-time/monitor/exposure operations and their order |
| resampling | interpolation method, extrapolation prohibition, and duplicate-axis handling |
| normalization | exact area, epsilon, negative-value rule, and scale-scalar formula |
| invalid-file rule | monotonicity, finite values, minimum points, corruption, saturation, and calibration checks |

No baseline subtraction, smoothing, peak alignment, peak picking, phase matching, Rietveld result,
PCA learned on the full dataset, or outcome-selected interval is part of confirmatory X60. If the
instrument requires another correction for physical validity, it must be justified, frozen, and
versioned before outcome access. Raw and each intermediate array remain retained so the transform
is reversible where mathematically possible.

If instrument qualification shows that integrated scale is not comparable because of uncontrolled
packing, amount, or geometry, removing or replacing the scale channel is a freeze-blocking design
change. It is not decided after viewing pilot outcomes.

## pH and temperature channels

For each accepted aliquot slot, record:

- actual pH value, measurement timestamp/elapsed time, meter ID, calibration ID, native precision,
  and validity flag; and
- actual sample/reaction temperature in degrees C, measurement timestamp/elapsed time, sensor ID,
  calibration ID, native precision, and validity flag.

Also record the actual pre-contact/equilibration temperature as a separate quantitative value. The
confirmatory feature vector contains the three slot pH values, three slot temperature values, and
pre-contact temperature; wall-clock timestamps and sensor IDs stay in provenance only.

The exact sampling procedure, location in the vessel, calibration acceptance limits, physical
bounds, sensor stabilization rule, and maximum allowed time difference between the aliquot pull and
the pH/temperature reading are `UNRESOLVED`. They must be set from instrument manuals and a dry run,
not from the target relationship.

The final 24-hour pH is excluded. A value copied forward from another time is missing, not a
measurement.

## Relative timing channels

All confirmatory timing features are pre-cutoff elapsed durations relative to first reagent
contact, never wall-clock dates or run order. The provisional required numeric fields are:

- actual addition/stirring duration only to the extent complete and observed by the state cutoff;
  and
- for each slot, withdrawal time, completed-arrest time, withdrawal-to-arrest lag, and
  pH/temperature measurement times.

Arrest-to-dry delay, dry-to-scan delay, scan schedule/order, and exposure/dwell settings are
post-cutoff assay/lineage fields. Exposure may enter the frozen physical intensity correction, but
none of these post-cutoff fields enters the predictive feature vector.

Before freeze, the run dry test must decide which of these can be measured reliably, their units and
precision, and how `not_applicable` differs from `not_recorded`. A required timing field that cannot
be recorded reproducibly must be removed in a committed revision, not filled using its planned
value. Absolute scan date, session, scan order, operator, and instrument ID remain available only to
the provenance audit.

## Primary feature layout

After deterministic observation-level processing, one primary X60 event bundle contains:

```text
xrd_shape[3, G]
xrd_log_integrated_intensity[3]
ph[3]
temperature_c[4]              # pre-contact plus three slots
relative_timing[fixed schema]
actual_slot_time_minutes[3]
```

`G` and the timing-schema length are frozen before collection. Array order is always `t05`, `t15`,
`t60`. Train-fold-only standardization may be applied by the model pipeline; no global scaling,
feature selection, dimensionality reduction, calibration, or imputation may see an outer test fold.

Any alternative representation—peaks only, background-subtracted patterns, phase fractions,
learned embeddings, or modality ablations—is a separately labeled sensitivity/exploratory arm and
cannot replace primary X60 after unblinding.

## Quality rules

Quality rules operate at observation level and distinguish physical low signal from invalid
measurement. Before freeze, executable rules must cover:

- impossible/nonfinite pH, temperature, time, or intensity values;
- XRD file corruption, nonmonotonic/duplicate axes, missing calibration, saturation, and incomplete
  acquisition;
- completed arrest outside its slot, excessive withdrawal-to-arrest lag, preparation/drying
  deviations, and
  specimen/scan identity mismatch;
- sensor calibration failure or a reading outside the allowed temporal relation to its slot; and
- duplicate/repeated observations and designation of the primary observation.

No rule may depend on the 24-hour outcome, human phase label, model residual, or pilot-wide feature
distribution inspected after outcome access. A valid low-intensity trace, unusual polymorph, or
process deviation is retained. Every excluded observation keeps its raw file, flag, reason code,
rule version, and original `include_in_raw_objective` value.

## Availability and missingness

### Confirmatory availability

`C` is representable only when all four planned factorial values are present and valid.

The confirmatory `X60` arm is representable only when:

- all three aliquot slots are mapped under the frozen timing rule;
- every slot has one valid primary XRD array and integrated-intensity scalar;
- all required pH, temperature, slot-time, and relative-timing fields are present and valid; and
- all source hashes, cutoff checks, and preprocessing-lineage checks pass.

Then `S_i^{X60}=1`; otherwise it is `0` with one or more frozen reason codes. This strict rule keeps
the primary feature matrix fixed-shape and makes support loss visible.

Missingness masks, train-fold imputation, partial-trace models, dropping a modality, or using an
alternate aliquot are sensitivity analyses that must be declared before freeze. They do not change
primary X60 coverage. An unavailable trace is never silently replaced by C alone, and a missing
60-minute measurement is never filled from the 24-hour specimen.

Report attempted-event coverage and reasons by final outcome status. Because missing observations
may be informative, performance on complete X60 events is always accompanied by the support
denominator and a comparison of available versus unavailable events using only legitimately known
fields.

## Preprocessing and lineage manifest

Every generated X60 bundle must carry:

| field | required content |
| --- | --- |
| `event_id` / `x60_version` | immutable identity and schema/configuration hash |
| `source_observation_ids` | selected aliquot, sensor, and XRD observations |
| `source_hashes` | native files, numeric exports, calibration, and reference artifacts |
| `state_times` | first contact, withdrawal, and arrest times |
| `assay_times` | drying, scan, and construction times |
| `transform_chain` | ordered code/version/configuration for correction, resampling, normalization, and assembly |
| `availability` | primary boolean plus complete reason-code list |
| `quality_flags` | original flags, ruleset version, and whether each source entered the bundle |
| `prohibited_input_check` | no 24-hour, label, note/video, or direct provenance field entered features |

Deterministic transforms may run before cross-validation. Any data-fitted transform—including
centering/scaling, PCA, feature selection, imputation, or probability calibration—is fitted inside
the training partition and recorded per fold.

## Freeze certification checklist

- [ ] practitioner and instrument scientist approve the meaning and operational latency of X60;
- [ ] the claim is worded as sampled-by-60-minutes unless the assay is genuinely available by then;
- [ ] exact C fields and encodings are frozen, with identifiers/provenance excluded from features;
- [ ] `t05`, `t15`, and `t60` completed-arrest windows, cutoff, arrest-lag limit, and
      duplicate-selection rules are executable;
- [ ] non-pilot stability evidence validates that arrest, drying/storage, and delayed assay
      preserve the pre-cutoff state to the required accuracy;
- [ ] native XRD retention/export, scan metadata, and source hashing pass end to end;
- [ ] numeric 2theta range, grid, correction order, resampling, normalization, epsilon, scale
      channel, and invalid-file rules are frozen and hashed;
- [ ] pH/temperature procedures, calibrations, bounds, temporal alignment, units, and precision are
      frozen;
- [ ] relative timing schema and `not_applicable`/missing rules are frozen;
- [ ] observation-level quality rules distinguish genuine blank/low signal from invalid files;
- [ ] primary X60 availability and every reason code are executable;
- [ ] partial-trace/missingness analyses are labeled sensitivity analyses and cannot replace the
      confirmatory arm;
- [ ] source-to-feature lineage and state-time/assay-time manifests are emitted automatically;
- [ ] leakage checks reject 24-hour observations, outcomes, labels, video/notes, wall-clock IDs,
      session/operator/lot/run-order fields, and globally fitted preprocessing;
- [ ] at least one non-pilot event has been rendered into the exact fixed-shape bundle; and
- [ ] no grid, correction, feature, quality threshold, or availability choice used a pilot outcome.

Until every item is resolved, `C + X60` is not a frozen primary input arm and the pilot must not
claim a confirmatory early-trace comparison under this representation.
