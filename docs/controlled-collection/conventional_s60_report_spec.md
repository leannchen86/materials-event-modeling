# Conventional 60-Minute Report — S60 Draft Specification

Status: **draft; freeze-blocking until a practitioner validates the fields and calculations**.
Companion preregistration:
[pilot_design_prereg.md](pilot_design_prereg.md#pre-freeze-amendment-2026-07-10-task-relevant-compression-audit).

## Purpose

`S60` is a realistic compact quantitative report produced from specimens and observations whose
material state was fixed by 60 minutes. Ex-situ assay/report time is recorded separately, so this
draft does not claim the report is operationally available at minute 60. It is not a feature subset
selected for predictive performance. Its
scientific role is to test whether ordinary quantitative reporting occupies a useful compression
layer between a categorical human label (`L60`) and the full early trace (`X60`).

The final report must be defined with a practicing XRD or CaCO3 scientist. If no credible standard
report exists for this cutoff and system, remove the S60 arm in a committed pre-freeze amendment;
do not manufacture one after collection.

## Provisional report schema

One row per event, with repeated aliquot blocks for nominal 5, 15, and 60-minute measurements:

### Event-level fields

- actual relative material-state time for each included aliquot
- count of expected and available aliquots
- actual pH and temperature at each available timepoint
- cutoff-available process deviations represented by fixed codes, not future free-text review
- explicit missingness/quality flags generated under frozen physical and instrument rules

`report_version`, assay-ready/construction time, source observation IDs/hashes, software/operator
identity, instrument/session, scan order, and other direct provenance fields are required lineage,
but are **never confirmatory model features**.

### Per-aliquot XRD fields

The practitioner must decide which of the following are conventional and defensible:

- detected phase set from a frozen reference library and matching rule;
- dominant phase;
- quantitative or semi-quantitative calcite/vaterite/aragonite fractions, including an
  `unassigned_or_amorphous` component;
- uncertainty or detection-limit field for every reported fraction;
- fit/match quality in a frozen native unit;
- a small frozen list of phase-diagnostic peak positions, widths, and relative intensities; and
- crystallite-size estimate **only** if instrumental broadening, line-shape choice, and the
  calculation's validity are frozen and defended. Otherwise omit it.

The report does not contain learned latent features, the full resampled pattern, arbitrary PCA
components, or variables chosen after testing association with the 24-hour outcome.

### Trajectory summaries

Only summaries whose definitions are frozen before outcome access may be included, for example:

- change in estimated phase fractions from earliest available aliquot to 60 minutes;
- appearance/disappearance of a diagnostic phase under the frozen detection rule;
- pH and temperature changes over the observed window; and
- number and timing of missing or invalid scheduled observations.

These are derived from cutoff-eligible inputs. No extrapolation using the 24-hour observation is
permitted.

## Calculation and uncertainty contract

Before freeze, each retained field must declare:

| item | required content |
| --- | --- |
| scientific meaning | what quantity the field purports to summarize |
| source | exact input observations and reference data |
| method | algorithm/software/manual rubric and version |
| units and precision | including whether rounding is part of the conventional report |
| calibration | standards, instrument-broadening correction, or reference-library version |
| detection behavior | threshold, `not_detected`, `below_quantification`, and `unclassifiable` rules |
| uncertainty | reported interval/error or an explicit statement that none is defensible |
| missingness | whether the event remains representable when an aliquot or field is unavailable |

Nominal weighed or reagent fractions are not substituted for measured early phase fractions. Any
quantitative-phase method must state how preferred orientation, packing, amorphous content, and
sample-preparation variation affect the reported value.

## Representation and support rules

Before freeze, commit an ordered `s60_feature_schema` containing only the practitioner-approved
scientific quantities and cutoff-available flags selected from the event, aliquot, and trajectory
sections above. That exact vector—not the full report/lineage row—is the confirmatory S60 model
input. Relative specimen-state times may be included if the practitioner approves them; assay-ready
time and every lineage-only field above may not. Adding, removing, or reordering a predictive field
after outcome access is prohibited.

- The S60 generator receives only the frozen cutoff-eligible event bundle and frozen external
  references; it cannot read the outcome table.
- Every attempted event enters the S60 ledger. It is marked `report_available`,
  `partially_available`, or `unavailable` under frozen rules.
- The confirmatory S60 arm is representable only for `report_available` rows containing every
  practitioner-designated required field. `partially_available` and `unavailable` therefore have
  `S_i^{S60}=0` and remain in the support denominator. A predeclared missingness encoding for
  partial reports is a sensitivity analysis and does not change the primary support count.
- `Unclassifiable` and below-detection outcomes are retained explicitly.
- S60 generation must be deterministic given its declared inputs, except for identified manual
  steps whose operator and uncertainty are logged.

## Practitioner validation record

The sign-off attached to the freeze commit must answer:

1. Would this report plausibly be delivered or used for an early CaCO3 decision?
2. Which fields are conventional measurements versus research-only additions?
3. Are the phase fractions quantitative enough to compare numerically, or should they be reduced
   to a coarser ordinal field?
4. What changes in vaterite-fraction MAE or failure-probability Brier risk are scientifically
   meaningful enough to set the adequacy risk tolerances?
5. Which fields would be unavailable under the intended scan speed and sample preparation?

Reviewer identity/role, review date, approved schema hash, requested changes, and unresolved
limitations are retained. Approval means the report is realistic and frozen, not that it is
correct for every future task.

## Freeze certification checklist

- [ ] practitioner has approved the purpose and every retained field;
- [ ] one non-pilot example has been rendered end to end;
- [ ] calculation code, reference files, software versions, units, rounding, and thresholds are
      frozen and hashed;
- [ ] quantitative-phase uncertainty and detection behavior are documented;
- [ ] missing/partial/unclassifiable rules are executable;
- [ ] source-lineage manifest, 60-minute state-cutoff check, and any declared decision-deadline
      check pass;
- [ ] ordered confirmatory `s60_feature_schema` is frozen and a prohibited-input test rejects
      lineage versions/hashes, assay/construction time, and direct provenance identifiers;
- [ ] task-native adequacy risk tolerances are elicited and committed;
- [ ] no field was chosen using the pilot's 24-hour outcomes.

Until certification completes, S60 is not a pre-registered representation and cannot be introduced
after unblinding.
