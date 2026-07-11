# Downstream Endpoint and Decision Card

Status: pre-partner / pre-preregistration template, 2026-07-11. Complete one card per candidate
study before modeling or collection. The program-level rationale and phase gates live in
[downstream_failure_research_program.md](../spine/downstream_failure_research_program.md).

This card freezes one consequential outcome and one early decision. It is intentionally not a menu
of every property that could later be measured.

## A. Use case and decision

| field | required entry |
| --- | --- |
| study ID and version | immutable identifier |
| intended user | named role that would act on the result |
| target population | material systems, processes, sites, and time period covered by the claim |
| decision time | operational deadline, not only material-state cutoff |
| allowed actions | e.g. continue, repeat, rework, add characterization, route, stop, scrap |
| current decision rule | actual SOP/report/expert rule used today |
| false-accept cost | scientific or operational consequence |
| false-reject cost | scientific or operational consequence |
| measurement/delay cost | cost of waiting for the final outcome |
| utility or loss | task-native function with units |
| smallest useful benefit $\delta_R$ | elicited before outcome access |

Reject the candidate if no real person would take a different action at the declared time.

## B. Downstream outcome

| field | required entry |
| --- | --- |
| outcome ID and version | immutable target specification |
| physical subject | execution, material batch, aliquot, specimen, device, pilot lot, or field unit |
| continuous primary target | preferred where scientifically meaningful |
| secondary threshold/status | optional spec-pass, failure, or time-to-threshold target |
| outcome horizon/window | frozen time or interval |
| assay and adjudication | instrument, protocol, software, assessor, blinding |
| uncertainty | repeatability, calibration, detection/quantification limits |
| eligibility | which attempted units have a scientifically defined target |
| censoring/dropout | right, interval, destructive-test, missing, or not-followed reason |
| measured-at environment | site, instrument, session, operator, lot, and configuration |
| outcome independence | why it is not merely the same transformation that produced the early report |

Reject the candidate if target measurement error is comparable to the smallest useful effect or if
follow-up is available only for hand-selected successes with no recoverable denominator.

## C. Physical-unit lineage

Draw and version the actual graph:

```text
producing event -> material batch -> aliquot/specimen -> device/pilot lot -> outcome assay
```

For every node record:

- immutable ID and type;
- parent IDs and split/merge/consumed relation;
- creation, transfer, preparation, and assay timestamps;
- amount, geometry, storage, and handling state where relevant;
- source artifact hashes;
- process, material-lot, operator, instrument, and site provenance; and
- whether multiple descendants share one independent parent.

Reject the candidate if an outcome cannot be joined to its source evidence without a manual guess.

## D. Input cutoff and representation graph

| field | required entry |
| --- | --- |
| state cutoff $\tau_s$ | latest physical state allowed into any early representation |
| decision deadline $\tau_d$ | when the representation and decision must be ready |
| context $C$ | legitimate shared recipe/process information |
| native evidence $X$ | exact modalities, files, machine state, and process logs |
| intermediate stages | calibration, cleanup, fit, engineered features, residuals |
| conventional report $S$ | actual fields, precision, missingness, and generating SOP |
| label/grade $L$ | category, confidence, abstention, and side inputs |
| parent DAG | actual parents and versions for every representation |
| retention class | exact, lossy, reconstructable, deleted/inaccessible, never captured |

At minimum compare `C`, `C+L`, `C+S`, `C+X`, and `C+L+X`, plus genuine adjacent intermediate
stages. A human label with side evidence absent from $X$ is nonnested and must remain a separate
branch.

## E. Environments and independent units

| claim | required held-out unit |
| --- | --- |
| repeatability | repeat execution on the same apparatus under short-term conditions |
| intermediate precision | changed day/operator/lot/instrument within one lab |
| reproducibility | independent site |
| material transfer | independent material or manufacturing batch |
| chemistry/process transfer | predeclared held formulation, condition, or family |

Record expected counts at every level. Do not treat scans, timepoints, cycles, aliquots, specimens,
or devices as independent when they descend from one material batch relevant to the claim.

## F. Support and leakage contract

Freeze:

- attempted-unit denominator;
- target eligibility and follow-up denominator;
- representation-availability denominator and reason codes;
- handling of failure, ambiguity, abort, retry, rework, and unclassifiable reports;
- censoring model and follow-up schedule;
- no-future-state and no-outcome-informed-processing checks;
- grouping that prevents descendants of one independent parent crossing folds;
- training-only feature learning, imputation, tuning, and calibration; and
- provenance recoverability probes for every representation.

## G. Costs and adequacy

Collect from day one:

- acquisition and instrument time;
- storage volume and retention duration;
- processing and compute time;
- annotation/expert time;
- turnaround/decision latency;
- retest, rework, scrap, and false-decision costs; and
- recoverability of the upstream artifact.

Freeze meaningful risk, event-support, decision-support, collision, and harm bounds. The target is
the least costly representation whose worst relevant environment remains inside all bounds.

## H. Partner-entry checklist: one golden event

Before a full agreement, request one de-identified event containing:

- planned process and actual deviations;
- complete native trace and instrument/process metadata;
- every intermediate transformation with code/SOP version;
- actual conventional report and final grade;
- delayed outcome with uncertainty and subject lineage;
- failures/retries/abstentions if they occurred; and
- rough cost and turnaround estimates.

Required partner answers:

1. Is the raw upstream artifact legally and technically accessible?
2. Does the report reflect real practice, rather than a feature set invented for this project?
3. Are failed and censored units visible in the source ledger?
4. Can at least one material/batch-level environment be held out untouched?
5. Is an external instrument or site available after the model and claim freeze?
6. Can results or at least aggregate audit outputs be released?

If any of questions 1--4 is `no`, do not promise a consequential compression study.

## I. Candidate scorecard

Score each item `0` (absent), `1` (partial), or `2` (strong):

| criterion | score |
| --- | ---: |
| delayed outcome is expensive, slow, destructive, or consequential |  |
| real early action exists |  |
| continuous outcome with credible uncertainty |  |
| actual raw-to-report ladder is accessible |  |
| failed/censored attempts remain visible |  |
| physical-unit lineage is machine-resolvable |  |
| multiple independent batches/environments |  |
| external validation path |  |
| storage/latency/action costs measurable |  |
| data rights permit a scientific result |  |

`16--20`: strong Phase 2/3 candidate. `12--15`: partner-development candidate with named gaps.
Below `12`: calibration or engineering exercise, not a flagship.

## J. Freeze signatures

- scientific owner and date:
- practitioner/action owner and date:
- outcome-assay owner and date:
- data/lineage owner and date:
- preregistration commit:
- first outcome-access timestamp:

The card is invalid if the preregistration commit does not precede outcome access.
