# Downstream Endpoint and Decision Card

Complete one card per candidate partner workflow before modeling, schema extension, or collection.
This freezes one outcome and one early decision; it is not a menu of possible targets. Program:
[downstream_failure_research_program.md](../spine/downstream_failure_research_program.md).

## Decision

| field | required entry |
| --- | --- |
| study ID/version |  |
| intended user and target population |  |
| decision deadline |  |
| allowed actions |  |
| actual current rule/report |  |
| false-accept and false-reject costs |  |
| assay/delay/action costs |  |
| task-native loss or utility |  |
| smallest worthwhile risk/utility gain |  |

Reject if no named user would change an action at the declared time.

## Outcome

| field | required entry |
| --- | --- |
| outcome ID/version and physical subject |  |
| primary continuous/failure-aware target |  |
| optional threshold or survival target |  |
| horizon/window |  |
| assay, adjudication, software, and blinding |  |
| calibration/repeatability/detection uncertainty |  |
| eligibility and follow-up |  |
| censoring/dropout types |  |
| measured-at environment |  |
| independence from the early report |  |

Reject if measurement uncertainty rivals the worthwhile effect or selective follow-up has no
frozen sampling/sensitivity design.

## Capture and representations

| field | required entry |
| --- | --- |
| state cutoff and decision deadline |  |
| measurement opportunities/actions |  |
| capture-policy mode, inputs, selections, failures, and reasons |  |
| native retained artifacts and reader recipes |  |
| actual intermediate transformations |  |
| conventional report/grade and side inputs |  |
| context shared by all arms |  |
| parent DAG, clocks, hashes, versions, and availability |  |
| retention/recoverability and cost per node |  |

At minimum compare context, actual report, richer/native or genuine intermediate evidence, and
report-plus-richer complementarity. Do not invent a weak report for the study. A human report with
unrecorded evidence is a nonnested branch.

## Physical units and environments

Draw the machine-resolvable graph:

```text
attempt -> material batch -> aliquot/specimen -> device or lot -> outcome evidence
```

For each node record immutable ID, parents, split/merge/consumption, times, amount/state, artifacts,
and provenance. State the highest shared ancestor that defines independence.

| claim | primary held-out unit |
| --- | --- |
| repeatability | repeat execution under short-term same-method conditions |
| intermediate precision | changed day/operator/instrument within one lab |
| process/material robustness | changed lot, batch, or frozen nuisance |
| reproducibility | independent site |
| predictor transfer | frozen held material/manufacturing batch or site |

List counts and overlap at every level. Descendant scans, cycles, aliquots, specimens, or devices do
not substitute for independent material batches.

## Support and firewall

Freeze:

- attempt, target-eligibility, follow-up, assay, and representation denominators;
- failure, ambiguity, abort, retry, rework, censor, and unavailable reason codes;
- capture-opportunity coverage;
- one primary environment split and an external-site mode;
- no-future-state/no-outcome-informed processing checks;
- parent-group isolation across folds;
- fold-local fitting, imputation, tuning, and calibration; and
- provenance probes, risk/support/collision/harm margins, uncertainty, and stop rules.

## Golden-bundle entry gate

Request one ordinary chain and one failure/censor/abort/retry/rework example when available, with
the opportunity inventory, native bytes, transformations, actual report, outcome evidence,
lineage, source denominators, costs, rights, and reader recipes.

All answers below are hard gates:

- Is there a real early action and actual report?
- Are capture opportunities, failed attempts, and censors visible?
- Can every outcome and report be joined to native evidence without a manual guess?
- Are enough crossed independent environments available for simulation and an untouched test?
- Is an external site or instrument available after model freeze?
- Can native evidence be retained and scientific outputs released?

Golden and pilot units are permanently nonconfirmatory.

## Signatures

- scientific owner/date:
- practitioner action owner/date:
- outcome assay owner/date:
- data lineage owner/date:
- preregistration commit:
- first confirmatory outcome-access timestamp:

The card is invalid if any hard gate is blank or the preregistration does not precede outcome
access.
