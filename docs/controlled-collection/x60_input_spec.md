# Frozen Quantitative X60 Arm — Draft

Status: freeze-blocking draft. Instrument-specific transformations, timing, quality rules, and
feature schema must be certified before collection. Companion:
[pilot_design_prereg.md](pilot_design_prereg.md).

## Boundary

`X60` is a fixed quantitative comparison arm, not the complete early record and not native truth.
It contains three early ex-situ XRD patterns, contemporaneous pH/temperature, and relative timing
for material states irreversibly arrested by 60 minutes.

| capture class | content |
| --- | --- |
| model input | frozen XRD arrays/scale, pH, temperature, relative timing |
| retained by reference | native instrument files, calibration, scan metadata, QC and transform lineage |
| recorded but excluded | video/images, visual categories, notes, labels, provenance IDs, post-cutoff assay scheduling |
| prohibited | `L60`, `S60`, 24-hour observations/outcomes, outcome-selected features |
| not yet known | partner instrument channels and measurement opportunities omitted from this draft |

The real partner must complete a measurement-opportunity and native-artifact inventory. Anything
outside it is above the audit root and cannot be called tested.

## State and availability clocks

For an ex-situ aliquot, state time is completion of validated irreversible arrest—not withdrawal
start. Record first contact, withdrawal, arrest start/end, drying completion, XRD start/end, feature
construction, and operational availability.

A scan made later can assay a state fixed by the cutoff. That supports **sampled by 60 minutes**,
not a real-time decision at 60 minutes. A real-time claim additionally needs a frozen decision
deadline and demonstrated turnaround.

Before freeze, non-pilot specimens must show that arrest, rinse/dry, storage, and delayed scanning
preserve state at task-relevant resolution. The allowed slot windows and maximum withdrawal-to-
arrest lag remain unresolved.

## Shared context C

`C` contains only the four planned factors in `pilot_assignment.csv`:

- `concentration_m`;
- `temperature_c`;
- `mg_ratio`; and
- one-hot `mixing_route` (`fast_no_aging` or `slow_30min_aging`).

Fit numeric scaling inside training folds. Event/condition/replicate IDs, session/day/operator,
lots, instruments, run/scan order, filenames, hashes, deviations, actual measurements, labels,
quality outcomes, and availability reasons are excluded from model features but retained for
lineage, splitting, and support audits.

## Required slots

| slot | intended state | quantitative input |
| --- | --- | --- |
| `t05` | nominal 5-minute completed arrest | XRD, pH, temperature, timing |
| `t15` | nominal 15-minute completed arrest | XRD, pH, temperature, timing |
| `t60` | completed arrest at or before 60 minutes | XRD, pH, temperature, timing |

Freeze non-overlapping acceptance windows and a deterministic primary-aliquot/scan rule. Never
select the cleaner pattern. Rescans and repackings remain linked observations. A valid blank-like
pattern is physical content; it is not missingness.

## XRD source and transformation

Retain instrument-native bytes plus a portable numeric export, both hashed. Record instrument and
configuration, radiation, geometry, range, step, exposure, optics, detector, holder, packing,
calibration, native units, instrument-software corrections, export profile, and versions.

The provisional per-slot representation is:

1. exposure/monitor-corrected intensity on one frozen common $2\theta$ grid, clipped under a frozen
   negative-value rule and normalized to unit nonnegative area; and
2. `log_integrated_intensity` computed before unit-area normalization.

\[
A=\int\max(I_{corr}(\theta),0)d\theta,\qquad
I_{shape}(\theta)=\frac{\max(I_{corr}(\theta),0)}{\max(A,\epsilon)}.
\]

Freeze the axis/radiation, supported common range, grid, correction order, interpolation,
extrapolation prohibition, duplicate handling, integration, epsilon, and invalid-file rules from
instrument qualification. No smoothing, baseline fitting, peak alignment/picking, phase matching,
Rietveld result, global PCA, or outcome-selected interval belongs in primary X60. Retain each
intermediate so the transform is inspectable and reversible where possible.

If integrated scale is not comparable because packing, amount, or geometry is uncontrolled, revise
the arm before outcomes; do not decide from pilot performance.

## pH, temperature, and timing

For each slot, record value, elapsed measurement time, sensor/meter and calibration IDs, precision,
validity, and sampling location/procedure. Also retain pre-contact temperature. The feature vector
uses three pH values, three slot temperatures, pre-contact temperature, actual slot/arrest times,
and a fixed relative-timing schema.

Freeze calibration limits, stabilization, physical bounds, allowed sensor-to-aliquot lag, units,
precision, and `not_applicable` versus `not_recorded`. Never carry a value forward from another
time. Wall-clock time, sensor identity, assay delay, and scan order remain lineage/provenance fields,
not predictive features.

## Fixed feature layout

```text
xrd_shape[3, G]
xrd_log_integrated_intensity[3]
ph[3]
temperature_c[4]
actual_slot_time_minutes[3]
relative_timing[fixed schema]
```

Freeze `G` and timing length before collection. Array order is `t05`, `t15`, `t60`. Any fitted
scaling, PCA, feature selection, calibration, or imputation occurs inside the outer training fold.
Peaks, phase fractions, learned embeddings, modality ablations, and partial-trace models are
separately named sensitivity/exploratory arms.

## Quality and availability

Outcome-blind executable rules cover nonfinite/physical bounds, corrupt or incomplete XRD,
nonmonotonic axes, missing calibration, saturation, slot/arrest violations, sensor timing,
identity mismatches, and duplicate designation. Retain valid low signal, unusual outcomes, and
process deviations. Every excluded observation keeps its native file, original flag, rule version,
and reason code.

Primary `C+X60` is available only when C is valid and all three slots have a valid primary XRD
shape/scale plus every required pH, temperature, time, hash, cutoff, and lineage check. Otherwise
$S_i^{X60}=0$ with frozen reasons. Do not silently substitute C, a later specimen, an alternate
aliquot, or imputation. Report coverage and reasons over all attempts and by outcome status.

## Required bundle metadata

Each X60 bundle records event/version, selected source observation IDs and hashes, state and assay
times, ordered transform code/config hashes, availability reasons, quality flags, and a prohibited-
input assertion. Deterministic transforms may precede CV; learned transforms remain fold-local.

## Freeze blockers

- practitioner and instrument scientist approve physical meaning and achievable latency;
- opportunity/native-artifact inventory and explicit exclusions are complete;
- arrest stability, slot windows, cutoff, lag, and primary-observation rules are validated;
- native export, scan metadata, readers, hashes, restore test, and transform lineage work end to end;
- grid, corrections, normalization, scale channel, and file-validity rules are hashed;
- pH/temperature/timing procedures and calibration rules are executable;
- missingness, low-signal, duplicate, and partial-trace policies are frozen;
- a non-pilot event renders into the exact fixed-shape bundle; and
- automated leakage checks reject labels, notes/video, direct provenance, later state, outcomes,
  and globally fitted preprocessing.

Until all blockers close without pilot-outcome access, `C+X60` is not a confirmatory arm.
