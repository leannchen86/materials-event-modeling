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
| smallest useful task-risk benefit $\delta_R$ | elicited before outcome access |
| smallest useful utility/cost benefit $\delta_U$ | separate from predictive risk |

Reject the candidate if no real person would take a different action at the declared time.

## B. Downstream outcome

| field | required entry |
| --- | --- |
| outcome ID and version | immutable target specification |
| physical subject | execution, material batch, aliquot, specimen, device, pilot lot, or field unit |
| primary target | continuous and failure-aware where possible; survival/co-primary when needed |
| secondary threshold/status | optional spec-pass, failure, or time-to-threshold target |
| outcome horizon/window | frozen time or interval |
| assay and adjudication | instrument, protocol, software, assessor, blinding |
| uncertainty | repeatability, calibration, detection/quantification limits |
| eligibility | which attempted units have a scientifically defined target |
| censoring/dropout | right, interval, destructive-test, missing, or not-followed reason |
| measured-at environment | site, instrument, session, operator, lot, and configuration |
| outcome independence | why it is not merely the same transformation that produced the early report |

Reject the candidate if target measurement error is comparable to the smallest useful effect. If
follow-up is selective, require one of: all eligible units assayed; predeclared probability sampling
with known inclusion probabilities; or a defensible selection model plus sensitivity bounds. A
recoverable denominator alone does not reveal the missing outcomes of hand-selected units.

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
| acquisition time | when each source artifact becomes available |
| construction time | when each derived representation is produced |
| operational availability | whether construction finishes before $\tau_d$ |
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

Keep online and archival decisions separate. A compact report may be adequate for the declared
real-time action while native evidence remains worth retaining for future tasks or verification.

## E. Environments and independent units

| claim | required held-out unit |
| --- | --- |
| repeatability | repeat execution on the same apparatus under short-term conditions |
| measurement-system intermediate precision | changed day/operator/instrument within one lab |
| process robustness | changed material lot or predeclared process nuisance |
| reproducibility | independent site |
| material transfer | independent material or manufacturing batch |
| chemistry/process transfer | predeclared held formulation, condition, or family |

Record expected counts at every level. Do not treat scans, timepoints, cycles, aliquots, specimens,
or devices as independent when they descend from one material batch relevant to the claim.
Require condition/chemistry overlap across batches when batch transfer is the primary estimand.

For an external site, choose exactly one primary mode: zero-shot frozen-model transport;
predeclared site calibration followed by a frozen test; or protocol replication with site-specific
retraining. The last validates the method, not transfer of the original predictor. Verify whether
the report schema and transformation graph are actually the same at the new site.

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

Predeclare one primary transfer split. Random, held-batch, held-condition, held-chemistry, and
held-site evaluations answer different questions and cannot be selected after seeing results.

## G. Costs and adequacy

Collect from day one:

- acquisition and instrument time;
- storage volume and retention duration;
- processing and compute time;
- annotation/expert time;
- turnaround/decision latency;
- retest, rework, scrap, and false-decision costs; and
- recoverability of the upstream artifact.

Freeze meaningful risk, utility, event-support, decision-support, collision, and harm bounds. The
target is the least costly representation whose worst relevant environment remains inside all
bounds.

## H. Partner-entry checklist: a golden bundle

Before a full agreement, request a small de-identified bundle containing:

- an ordinary event with planned process and actual deviations;
- complete native trace, instrument/process metadata, and every transformation version;
- actual conventional report, final grade, and delayed outcome with uncertainty and lineage;
- a failure, censor, retry, rework, or abstention example where one exists;
- aggregate source-ledger counts for denominator checks; and
- rough cost and turnaround estimates.

Golden-bundle IDs and descendants are permanently nonconfirmatory and listed in the
preregistration, or their outcomes remain firewalled from the analysis team while a data engineer
checks the joins.

Required partner answers:

1. Is the raw upstream artifact legally and technically accessible?
2. Does the report reflect real practice, rather than a feature set invented for this project?
3. Are failed and censored units visible in the source ledger?
4. Are there enough crossed independent material/batch environments for simulation and an
   untouched test, rather than merely one nominal held-out batch?
5. Is an external instrument or site available after the model and claim freeze?
6. Can results or at least aggregate audit outputs be released?

Hard, noncompensable entry gates are: a real early action; an actual report ladder; machine-
resolvable lineage; a complete attempt/failure denominator; enough crossed batches for the planned
transfer estimand; legally usable raw evidence; and publishable outputs. Do not promise a
consequential compression study if any hard gate fails.

## I. Candidate scorecard

Score each item `0` (absent), `1` (partial), or `2` (strong):

| criterion | score |
| --- | ---: |
| delayed outcome is expensive, slow, destructive, or consequential |  |
| real early action exists |  |
| informative, failure-aware outcome with credible uncertainty/censoring |  |
| actual raw-to-report ladder is accessible |  |
| failed/censored attempts remain visible |  |
| physical-unit lineage is machine-resolvable |  |
| multiple independent batches/environments |  |
| external validation path |  |
| storage/latency/action costs measurable |  |
| data rights permit a scientific result |  |

This total is a prioritization heuristic, not scientific evidence and not a substitute for the hard
gates above. `16--20`: strong Phase 2/3 candidate. `12--15`: partner-development candidate with
named gaps. Below `12`: calibration or engineering exercise, not a flagship.

## J. Freeze signatures

- scientific owner and date:
- practitioner/action owner and date:
- outcome-assay owner and date:
- data/lineage owner and date:
- preregistration commit:
- first outcome-access timestamp:

The card is invalid if the preregistration commit does not precede confirmatory outcome access.
Golden-bundle and pilot outcomes must be explicitly identified as permanently nonconfirmatory or
kept firewalled as described above.
