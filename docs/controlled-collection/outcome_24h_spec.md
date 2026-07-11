# 24-Hour Outcome Product — Draft Specification

Status: **draft; freeze-blocking until the outcome method, thresholds, uncertainty model, and
eligibility rules are certified**. Companion preregistration:
[pilot_design_prereg.md](pilot_design_prereg.md). The event envelope is
[`schemas/event_grammar.v1.schema.json`](../../schemas/event_grammar.v1.schema.json).

## Purpose and scope

This document defines the two 24-hour targets used by the controlled CaCO3 pilot:

1. binary **no-precipitate failure**; and
2. quantitative **vaterite fraction among crystalline CaCO3 polymorphs**.

These are separate outcomes with separate eligibility sets. A failed event is never assigned a
vaterite fraction of zero. An ambiguous, aborted, missing, or unquantifiable outcome is retained in
the attempt ledger; it is not converted into a convenient numeric target.

This draft fixes the structure of the outcome product but not instrument-dependent numerical
values. Items marked `UNRESOLVED` must be decided using practitioner review, instrument
qualification, blanks, and non-pilot reference specimens before any pilot outcome is inspected.
Until the checklist at the end passes, neither target is a frozen ground-truth product.

## Information and lineage contract

The outcome builder may use only the following 24-hour evidence and frozen external references:

- the actual elapsed collection time for the nominal 24-hour specimen;
- the contemporaneous mechanically recorded visual precipitate assessment;
- the raw/native 24-hour XRD file and its acquisition metadata;
- frozen blank, reference-mixture, instrument-calibration, and phase-reference artifacts; and
- sample-preparation and quality records produced without knowledge of any model prediction.

It may not use `L60`, `S60`, `X60` model outputs, predicted outcomes, or a retrospective narrative
written after viewing pilot-wide associations. The quantification code, reference structures,
thresholds, and eligibility rules must be hashed before pilot outcomes are unblinded to modelers.

Each output row records at least:

| field | required content |
| --- | --- |
| `event_id` | immutable event identifier |
| `outcome_spec_version` | version/hash of this frozen specification |
| `source_observation_ids` | visual and XRD observation IDs used |
| `source_hashes` | content hashes for raw files and external references |
| `actual_collection_time_minutes` | elapsed time from first reagent contact |
| `quantification_method_version` | software, code, reference library, and configuration hashes |
| `created_at` | outcome-product construction time |
| `builder_blinding_attestation` | prohibited information was unavailable during construction |
| `protocol_deviations` | late collection, preparation, scan, or calculation deviations |

The intended endpoint window remains 24 hours ±2 hours. The exact treatment of an observation
outside that window is `UNRESOLVED`: before freeze, choose either a fixed exclusion rule or a
predeclared time-adjustment/sensitivity analysis. The observed time is never rounded to 24 hours.

## Target 1: binary no-precipitate failure

### Estimand

Let `Y_failure_24h = 1` mean that no precipitated solid is detected at 24 hours under the frozen
visual and XRD detection procedure. This is a physical no-precipitate endpoint, not a synonym for
`bad experiment`, low vaterite, an uninterpretable phase pattern, or an aborted run.

For a usable endpoint assessment:

- assign `Y_failure_24h = 1` only when a valid visual record reports no visible precipitate **and**
  a valid 24-hour XRD measurement is at or below the frozen solid-signal threshold;
- assign `Y_failure_24h = 0` when either a valid visual record detects precipitated solid or a valid
  XRD measurement exceeds the frozen solid-signal threshold; and
- assign `failure_target_status = unresolved` when no valid positive exists but the two required
  negative assessments are not both available (for example, one required record is absent or
  invalid).

The rule is deliberately any-positive: a valid visual/XRD disagreement is a nonfailure with a
discordance flag, not an unresolved case. The visual vocabulary, illumination/viewing conditions,
and minimum inspection procedure remain `UNRESOLVED` freeze items. A human phase assignment is not
part of this binary endpoint.

### XRD solid-signal threshold

The phrase `noise-level XRD signal` is not operational until all of the following are frozen:

- instrument, scan geometry, 2theta range, step size, dwell/exposure, holder, and preparation;
- blank-holder and blank-preparation replicates collected under the same settings;
- the signal statistic, background treatment, evaluation region, and aggregation over peaks;
- the false-positive operating point or equivalent threshold rule;
- verification on low-mass positive controls; and
- the behavior for detector saturation, holder peaks, fluorescence/background, and corrupt files.

The exact statistic and numerical threshold are `UNRESOLVED`. They must be derived from blanks and
non-pilot controls, not chosen to match the pilot's visible outcomes. A low or blank-like pattern
that passes instrument checks is a valid scientific observation; it is not automatically a bad
scan.

### Failure eligibility and event status

Define the failure-task eligibility set as all attempted events for which the frozen endpoint rule
returns `0` or `1`. All attempted events remain in the support denominator, including those outside
this set. In particular:

- an aborted event without a valid 24-hour endpoint is ineligible, not a nonfailure; an aborted
  event with valid endpoint evidence may be numerically eligible under the same frozen rule, while
  its envelope status remains `aborted`;
- missing or invalid 24-hour evidence is unresolved, not a failure;
- a visible precipitate with phase-uninterpretable XRD is a nonfailure for this binary target but
  may be `ambiguous` for phase quantification; and
- an event with no visible precipitate but a validated above-threshold solid XRD signal is a
  nonfailure, with the visual/XRD discrepancy retained as a quality field.

Map the event envelope independently from numeric-target eligibility. Execution abortion has
precedence so that a later endpoint cannot erase what happened during the run:

| condition | `outcome.status` |
| --- | --- |
| execution meets the frozen interruption/abortion rule | `aborted`, regardless of later numeric-target eligibility |
| otherwise `Y_failure_24h = 1` | `failure` |
| otherwise solid detected and phase target quantifiable | `success` |
| otherwise solid detected but phase evidence uninterpretable/unassignable | `ambiguous` |
| otherwise endpoint cannot be resolved | `unknown` |

The primary binary metric can be computed only if both classes occur and out-of-fold probability
predictions are estimable. If the pilot contains no failures, report the observed prevalence and
support counts; do not manufacture a Brier-score claim or tune a threshold on the same data.

## Target 2: quantitative 24-hour vaterite fraction

### Provisional confirmatory quantity

The provisional confirmatory target is a whole-pattern quantitative phase analysis of the frozen
24-hour XRD pattern, using a validated Rietveld or equivalently defended whole-pattern method. The
exact software, version, structural models, line-shape/background model, refinement sequence,
constraints, convergence criteria, and acceptance thresholds are `UNRESOLVED` freeze items.

Unless a validated internal-standard method is adopted before collection, define:

\[
Y_{V,24h}
=
100\times
\frac{w_{\mathrm{vaterite}}}
{w_{\mathrm{calcite}}+w_{\mathrm{vaterite}}+w_{\mathrm{aragonite}}},
\]

where the weights are the fitted crystalline CaCO3 polymorph weights from the same accepted
refinement. The unit is percentage points on `[0, 100]`.

This denominator deliberately excludes amorphous/unassigned material and therefore must be named
**vaterite share of quantified crystalline CaCO3**, not total-solid vaterite fraction. The outcome
product separately reports fitted calcite, vaterite, and aragonite weights; fit residuals;
unassigned signal; and any evidence for amorphous or other crystalline material.

If an internal standard and preparation protocol can validly quantify amorphous content, a
total-solid vaterite fraction may be added as a separately named secondary target before pilot
collection. It must not silently replace the crystalline-denominator primary target after
unblinding. If another crystalline phase or unassigned contribution exceeds a predeclared
tolerance, the primary target is `unquantifiable` unless the frozen denominator rule explicitly
handles that phase.

### Sample and quantification method contract

Before freeze, the method must declare:

| component | required frozen decision |
| --- | --- |
| 24-hour collection | actual timing, arrest/rinse/dry procedure, and allowed deviations |
| powder preparation | grinding/homogenization, amount, holder, packing, orientation mitigation |
| scan | instrument/configuration, geometry, range, step, exposure, calibration, and raw format |
| phase library | exact structures for calcite, vaterite, aragonite, and allowed other phases |
| fit | software/version, background and peak model, parameters, constraints, and fit sequence |
| acceptance | convergence, residual, mass-balance, unassigned-signal, and artifact thresholds |
| replication | repacking/rescan plan and which result is primary rather than retrospectively best |
| output precision | numeric precision justified by the uncertainty study |

Human phase labels may be compared with this product, but they are not inputs to its refinement or
acceptance rule. A failed refinement is retained with its failure code and is never manually
repaired after looking at the prediction error.

### Detection limit, quantification limit, and non-detects

Phase-specific limits of detection and quantification must be measured under the frozen scan and
preparation protocol using blanks and non-pilot reference mixtures spanning the low-vaterite
region. The freeze record must contain:

- the definitions and numerical values of `LOD_vaterite` and `LOQ_vaterite`;
- the false-positive/false-negative or error criterion used to set them;
- the number and independence of preparations, repackings, and scans;
- any dependence on total solid amount, preferred orientation, or mixture composition; and
- the rules for `not_detected`, `detected_below_quantification`, and `quantified`.

The quantification method must still emit its native point estimate and uncertainty when
scientifically defensible. The confirmatory MAE treatment of below-LOD or below-LOQ estimates is
`UNRESOLVED`: freeze one rule before outcome access—validated numeric use, interval-censored
scoring, or target unavailability. Do not switch among these choices after seeing model results,
and do not equate `not_detected` with a failed synthesis.

### Uncertainty

Fit covariance alone is not accepted as total measurement uncertainty. The frozen uncertainty
model must address, where applicable:

- calibration bias on reference mixtures;
- repeat preparation, grinding, packing, and preferred orientation;
- repeat scan and instrument-session variation;
- refinement/model-choice variation; and
- low-fraction censoring at the LOD/LOQ boundary.

Report a point estimate, standard uncertainty or interval, method/coverage level, and all component
terms retained by the frozen method. The number of reference mixtures and replicate
preparations/scans is `UNRESOLVED` and must be justified before freeze. Pilot-wide empirical
variance cannot be substituted post hoc for an outcome-measurement uncertainty study.

### Vaterite eligibility

An event is eligible for the primary quantitative target only when all of the following hold:

- a precipitated/crystalline solid is detected under the frozen endpoint rule;
- the 24-hour specimen falls within the frozen timing and preparation rules, or passes a
  predeclared deviation rule;
- the raw XRD file and required calibration/reference artifacts pass instrument checks;
- the frozen quantitative-phase method converges and passes all acceptance criteria; and
- the method returns a numeric vaterite target under the frozen LOD/LOQ rule.

Handling by event type:

| event type | quantitative vaterite target |
| --- | --- |
| successful single- or mixed-polymorph precipitate with accepted QPA | eligible |
| no-precipitate failure | **ineligible; never encode as zero** |
| visible precipitate but uninterpretable/unaccepted QPA | ineligible, `ambiguous` |
| aborted before valid 24-hour endpoint | ineligible; envelope remains `aborted` |
| aborted execution with valid accepted QPA | eligible under the ordinary quantitative rule; envelope remains `aborted` |
| missing/corrupt endpoint evidence | ineligible, `unknown` or frozen quality status |
| amorphous/unassigned/other-phase contribution above its frozen tolerance | ineligible unless the frozen denominator rule explicitly supports it |

Report quantitative-target coverage over all attempted events and by final event status. The MAE
estimand is conditional on this frozen eligible set; it is not silently generalized to failures or
unquantifiable material.

## Within-condition ranking target

The confirmatory ranking outcome is the 24-hour crystalline-CaCO3 vaterite fraction defined above,
not failure status and not a human phase label. Candidate pairs are all unordered pairs of planned
replicates within each of the 16 factorial conditions. Failure–success pairs are not converted into
vaterite rankings by assigning the failure a zero.

Before freeze, set a resolution threshold

\[
\delta_{\mathrm{rank}}
=
\max(\delta_{\mathrm{scientific}},\delta_{\mathrm{measurement}}),
\]

where the first term is the smallest practitioner-meaningful difference in percentage points and
the second is derived from the frozen repeatability/uncertainty study. Exact values and the
confidence level for a difference are `UNRESOLVED`.

A pair is outcome-resolvable only when both events have eligible quantitative targets, the absolute
difference exceeds `delta_rank`, and the frozen uncertainty rule for the difference excludes a
tie. All other planned pairs remain in the ranking ledger as `outcome_tie`,
`outcome_unquantifiable`, or `outcome_missing`; they are not representation failures. Report, in
order:

1. all planned within-condition pairs;
2. outcome-resolvable pairs;
3. pairs representable by each model arm; and
4. pairwise accuracy on the common, outcome-resolvable support.

Exactly equal predicted scores earn 0.5 in pairwise accuracy. No outcome-dependent tie-breaking is
permitted.

## Outcome product fields

The machine-readable product should include at least:

- `failure_target_status` and nullable `y_failure_24h`;
- `execution_aborted`, its frozen reason code, and the precedence-preserving envelope status;
- visual and XRD solid-detection results plus the frozen threshold versions;
- `vaterite_target_status` and nullable `y_vaterite_crystalline_pct`;
- fitted crystalline phase weights and the denominator used;
- amorphous/unassigned/other-phase status without silently renormalizing it away;
- LOD/LOQ category, fit/acceptance codes, uncertainty estimate, interval, and coverage level;
- event-status mapping and all non-eligibility reason codes; and
- source IDs/hashes, method versions, actual endpoint time, and creation timestamp.

Null numeric values are accompanied by a reason code. A downstream table must never infer failure,
zero vaterite, or exclusion merely from a blank cell.

## Freeze certification checklist

- [ ] practitioner has approved the physical meaning of both targets and their deployment use;
- [ ] 24-hour timing and out-of-window rules are frozen;
- [ ] visual precipitate vocabulary, inspection conditions, and fixed any-positive discordance
      rule are executable;
- [ ] XRD solid-signal statistic and threshold are validated on blanks and low-mass controls;
- [ ] sample preparation, scan settings, phase library, QPA software/configuration, and acceptance
      criteria are frozen and hashed;
- [ ] the crystalline-CaCO3 denominator and behavior for amorphous, unassigned, and other phases
      are approved;
- [ ] LOD/LOQ values and below-limit scoring rule are frozen from non-pilot materials;
- [ ] the uncertainty model includes justified preparation/packing/scan components;
- [ ] failure, ambiguous, aborted, mixed, and uninterpretable cases pass executable eligibility
      tests, including the invariant that failure never maps to vaterite zero;
- [ ] ranking outcome, `delta_rank`, outcome uncertainty/tie rule, and the fixed 0.5
      equal-prediction score are executable;
- [ ] all attempted-event, target-eligible, and pair denominators are emitted automatically;
- [ ] source lineage, hashes, builder blinding, and no-prediction-input checks pass;
- [ ] one or more non-pilot specimens have been processed end to end without manual repair; and
- [ ] no numerical threshold or method choice used a pilot target or model result.

Until every item is resolved, the 24-hour product is a draft outcome definition and the pilot must
not claim that vaterite fraction or no-precipitate failure was measured under a frozen procedure.
