# 24-Hour Outcome Product — Draft

Status: frozen CaCO3 methods draft; methods, thresholds, uncertainty, and eligibility are unresolved.
Companion: [pilot_design_prereg.md](pilot_design_prereg.md).

## Targets

The draft has two separate 24-hour targets:

1. binary **no-precipitate failure**; and
2. quantitative **vaterite share of quantified crystalline CaCO3**.

They have different eligibility sets. A no-precipitate event is never assigned zero vaterite.
Ambiguous, aborted, missing, censored, or unquantifiable outcomes remain explicit ledger states.

The nominal endpoint window is 24 hours ±2 hours. Freeze exclusion or time-adjustment rules before
collection; never round observed time to 24 hours.

## Inputs and lineage

The outcome builder may use only actual endpoint time, contemporaneous visual assessment, native
24-hour XRD and acquisition metadata, frozen blanks/references/calibrations, and outcome-blind
preparation/QC records. It may not use `L60`, `S60`, `X60` model outputs, predictions, or later
retrospective narratives.

Each row records event ID, outcome-spec hash, source observation IDs/hashes, actual endpoint time,
method/software/reference hashes, construction time, builder blinding, and deviations. Numeric nulls
always carry a reason code.

## Target 1: no-precipitate failure

`Y_failure_24h = 1` means no precipitated solid under a frozen visual-plus-XRD detection procedure.
It does not mean low vaterite, uninterpretable phase, aborted execution, or a generally bad run.

For valid evidence:

- assign `1` only when visual inspection reports no precipitate **and** XRD is at or below the
  frozen solid-signal threshold;
- assign `0` when either valid source detects solid; and
- assign `unresolved` when no positive exists but both required negative assessments are not valid.

Thus visual/XRD disagreement is a nonfailure with a discordance flag. Freeze visual vocabulary,
illumination, minimum inspection, scan geometry, blanks, signal statistic, evaluation region,
threshold operating point, low-mass controls, and corrupt/saturated/holder-background handling from
non-pilot materials.

Failure-task eligibility includes attempts with a frozen `0` or `1`; all attempts stay in support
counts. Missing endpoint evidence is unresolved, not failure. Execution status remains distinct:

| condition | event `outcome.status` |
| --- | --- |
| frozen interruption/abort rule met | `aborted` |
| otherwise no-precipitate target = 1 | `failure` |
| solid detected and phase target quantifiable | `success` |
| solid detected but phase evidence unassignable | `ambiguous` |
| endpoint unresolved | `unknown` |

If only one binary class occurs, report prevalence and support; do not manufacture a predictive
metric or tune a threshold on the same pilot.

## Target 2: crystalline-CaCO3 vaterite share

The provisional primary target uses validated whole-pattern quantitative phase analysis:

\[
Y_{V,24h}=100\frac{w_{vaterite}}
{w_{calcite}+w_{vaterite}+w_{aragonite}}.
\]

This is percentage of quantified crystalline CaCO3, not total-solid fraction. Report each phase
weight, residuals, unassigned signal, and evidence for amorphous/other phases. A total-solid target
requires a validated internal-standard method and a separately named pre-freeze specification.

Freeze:

| component | required decision |
| --- | --- |
| collection/preparation | time, arrest/rinse/dry, grinding, amount, holder, packing, orientation control |
| scan | instrument/configuration, geometry, range, step, exposure, calibration, native format |
| phase library | exact structures and allowed other phases |
| fit | software/version, background/line shape, sequence, parameters, constraints |
| acceptance | convergence, residual, mass balance, unassigned/artifact thresholds |
| replication | repacking/rescan plan and deterministic primary result |
| precision | output resolution justified by uncertainty |

Human phase labels are not fit inputs. A failed refinement stays failed; it is not repaired after
viewing prediction error.

### Detection and uncertainty

Measure phase-specific LOD/LOQ under the frozen preparation/scan protocol using independent
non-pilot reference mixtures. Freeze definitions, values, error criterion, replicate structure,
dependence on solid amount/orientation/composition, and handling of `not_detected`,
`detected_below_quantification`, and `quantified`.

Freeze one below-limit scoring rule: validated numeric use, interval-censored scoring, or target
unavailability. Fit covariance alone is insufficient. The uncertainty model considers calibration
bias, preparation/packing/orientation, repeat scan/session, model choice, and low-fraction
censoring, and reports point estimate plus interval/coverage.

### Eligibility

The quantitative target is available only when solid is detected, endpoint time/preparation meet
frozen rules, native XRD/calibration pass, the method converges and passes acceptance, and the
LOD/LOQ rule yields an eligible value.

| event | quantitative target |
| --- | --- |
| accepted single/mixed polymorph QPA | eligible |
| no-precipitate failure | ineligible; never zero |
| precipitate but rejected/uninterpretable QPA | ineligible, `ambiguous` |
| aborted with no valid endpoint | ineligible; remains `aborted` |
| aborted with valid accepted endpoint | eligible numerically; remains `aborted` |
| missing/corrupt evidence | ineligible |
| other/unassigned contribution above tolerance | ineligible unless frozen rule supports it |

Report target coverage over all attempts and by event status. The quantitative risk estimand is
conditional on this frozen eligible set.

## Ranking outcome

Within-condition ranking uses eligible quantitative vaterite outcomes, not failure status or human
labels. Candidate pairs are all planned replicate pairs. A failure-success pair is not ranked by
inventing a zero.

Freeze

\[
\delta_{rank}=\max(\delta_{scientific},\delta_{measurement}),
\]

where terms are practitioner-meaningful difference and measurement resolution. A pair is
outcome-resolvable only when both targets are eligible, the difference exceeds the threshold, and
the uncertainty rule excludes a tie. Report planned, outcome-resolvable, representation-available,
and common-support pairs in that order. Equal predicted scores earn 0.5.

## Minimum product

- nullable failure and vaterite values with separate statuses/reasons;
- execution-abort status and precedence-preserving event mapping;
- visual/XRD detection results and threshold versions;
- phase weights, denominator, other/unassigned contribution, residuals, and acceptance codes;
- LOD/LOQ category and uncertainty interval/coverage;
- ranking resolution status;
- source IDs/hashes, methods, actual time, builder blinding, and creation time.

## Freeze blockers

- practitioner approves both targets and their use;
- timing/out-of-window and visual/XRD discordance rules are executable;
- blanks/low-mass controls validate the solid threshold;
- preparation, scan, phase library, QPA, and acceptance are hashed;
- denominator and other/amorphous/unassigned behavior are approved;
- LOD/LOQ and below-limit scoring come from non-pilot materials;
- uncertainty includes preparation and scan components;
- failure, ambiguity, abort, and target-eligibility invariants are tested;
- ranking threshold/tie rule and all denominators are executable; and
- no method choice or numerical threshold used pilot outcomes or predictions.

Until these close, the outcome product is not frozen ground truth.
