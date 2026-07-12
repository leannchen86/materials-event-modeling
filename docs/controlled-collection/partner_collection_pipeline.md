# Partner Downstream-Compression Collection Pipeline

Status: pre-partner strategy and implementation contract, 2026-07-11. This operationalizes the
[downstream-failure research program](../spine/downstream_failure_research_program.md) after the
[Severson dry run](severson_downstream_compression_results.md). It does not authorize collection:
one partner-specific instance must pass the gates below, receive named sign-off, and be committed
before confirmatory outcomes are accessed.

Companion intake instrument:
[downstream endpoint and decision card](downstream_endpoint_decision_card.md).

## Executable v1 contract

The strategy is implemented, not only described. The strict contract consists of:

- [study specification schema](../../schemas/partner_study.v1.schema.json), which freezes the
  decision, unit graph, representation DAG and arms, delayed outcome, environment design,
  firewall, artifact policy, release terms, and sign-offs;
- [row schema](../../schemas/partner_rows.v1.schema.json), covering assignments, attempts,
  physical lineage, artifacts, transformations, representations, outcomes, decisions, costs,
  and append-only corrections;
- [bundle index schema](../../schemas/partner_bundle.v1.schema.json), which binds all twelve
  ledgers and their exact row schemas by path, byte count, row count, and SHA-256;
- [semantic validator](../../scripts/validate_partner_bundle.py), which enforces the cross-file
  properties JSON Schema cannot express; and
- a wholly fictitious, permanently nonconfirmatory
  [synthetic golden bundle](../../data/examples/partner_golden_bundle_synthetic/README.md) with a
  committed [validation receipt](../../data/manifests/partner_golden_bundle_validation.json).

Run the mechanics gate from the repository root:

```bash
.venv/bin/python scripts/validate_partner_bundle.py \
  data/examples/partner_golden_bundle_synthetic/bundle.json \
  --readiness golden
```

The validator rejects nonfinite or duplicate-key JSON, unsafe and symlink-escaping paths, wrong
or reused IDs, schema substitution, hash or byte mismatch, orphaned joins, cyclic physical or
representation lineage, invented parent groups, partition leakage, cutoff/deadline violations,
post-outcome representation freezing, inconsistent censoring, unlinked reports, silent retries,
unreconciled independent source counts, incomplete crossing, invalid corrections, and vacuous
readiness. A readiness result can never be `true` when a core schema, hash, lineage, or semantic
check has failed.

Readiness is deliberately split by lifecycle. A confirmatory-start package is not required to
contain outcomes that do not yet exist, and an otherwise valid confirmatory cohort is not failed
merely because no natural negative occurs. The negative/censor/retry example is mandatory for the
golden mechanics bundle; later gates require complete denominators and explicit outcome states.

| validator readiness | operational gate | what it authorizes |
| --- | --- | --- |
| `golden` | G1 | mechanics audit on permanently nonconfirmatory examples |
| `pilot` | pilot close | use of the permanent development cohort for design estimation |
| `confirmatory_start` | G3 | start collection after frozen assignments, design, rights, external reservation, hashes, and owner signatures |
| `input_close` | G4 | close early inputs after actual crossed environments, native/report chains, decisions, and costs reconcile |
| `outcome_reveal` | G5 | reveal/analyze outcomes after full subject coverage, lineage-aware unit freezes, and blinded outcome evidence pass |
| `external_validation` | G6 | evaluate the prospectively frozen external test population |
| `release` | G7 | release the approved reproducibility product |

For confirmatory gates, `firewall_and_freeze.study_spec_sha256` denotes the detached design-lock
manifest artifact. It must match that artifact and every signed owner hash. It is not a hash of the
self-containing `study_spec.json`, which would be self-referential. Likewise,
`assignment_sha256` must equal the delivered assignment ledger, and every locked freeze manifest,
external site set, and release product is an artifact-ledger ID/hash pair.

## Strategy in one sentence

For one real decision at one frozen deadline, collect a matched and versioned chain from native
evidence through the actual practitioner report to an independently measured delayed outcome,
while deliberately crossing conditions across future deployment environments and retaining every
attempt, failure, censor, retry, and unavailable representation.

The goal is not to prove that raw data win. The online goal is to identify the least costly
reporting stage that preserves decision value under the environments where the partner intends to
use it. That finding never authorizes deletion: archival retention of native evidence for incident
review, future tasks, verification, or model revision is a separate decision with a separate cost
and utility analysis.

## Five design rules

1. **Decision first.** Name the user, decision time, allowed actions, current rule, smallest useful
   risk benefit, harm bound, and utility/cost function before choosing representations.
2. **Lineage first.** An outcome is unusable until it can be joined without a manual guess to its
   producing event, material parent, descendants, early evidence, report, and assay.
3. **Transfer first.** Repeat shared conditions across independent batches, instruments, and sites.
   Many descendants of one parent do not replace independent environments.
4. **Actual workflow first.** Capture the real report, grade, rounding, abstention, side inputs,
   software, and manual steps. A project-designed feature table is not a conventional report.
5. **Complete denominator first.** Create the attempt row before execution. Never delete failures,
   aborts, partial records, censored outcomes, retries, rework, corrupt files, or boring results.

## The identifying graph

Every attempted or outcome-eligible subject must have a ledger row and an explicit
available/unavailable/not-applicable status at every declared graph node. Complete traversal is not
required—failures and absent reports are part of the estimand—but silent disappearance is forbidden.

The physical-unit graph is:

```text
plan / recipe
  -> execution attempt
    -> material or manufacturing batch
      -> aliquot / specimen
        -> device / pilot lot / qualification subject
          -> delayed assay or terminal outcome
```

The representation graph is:

```text
legitimate context C

native instrument/process artifact X0
  -> calibrated or cleaned trace X1
    -> engineered features / fit and residuals X2
      -> actual practitioner report S
        -> grade or label L

independently measured delayed outcome Y
```

The two graphs meet through immutable subject and artifact identifiers, not filenames or row
position. A stage may be called the earliest lossy edge only when its parent relationship is a
verified deterministic or stochastic transformation. A human report that uses side evidence not
present in X0 is a branch; analyze conditional value and complementarity rather than pretending it
is nested.

Minimum model arms are `C`, `C+L`, `C+S`, every genuine intermediate, `C+X0`, and `C+X0+S`, plus
the current SOP/expert rule. All arms use the same out-of-fold physical subjects and keep
representation availability separate from target availability.

## Three datasets with separate scientific roles

### 1. Golden bundle: mechanics only

Request a small hand-inspected package with at least one ordinary attempt and one failure, censor,
abort, retry, or rework. It contains native bytes, portable exports, every transformation and
report version, lineage, clocks, outcome evidence, uncertainty, and costs.

Golden-bundle IDs and every descendant are permanently nonconfirmatory. Their purposes are to
prove that:

- every physical join reconstructs without guessing;
- native files, decoders, hashes, units, and clocks are usable;
- the actual report and its side inputs are captured;
- report fields can be traced to parents without outcome knowledge;
- outcome status, censoring, failure, and follow-up are distinguishable;
- source-ledger totals reconcile with the delivered attempt ledger; and
- the partner can legally permit the agreed null/negative result and reproducibility package.

A golden bundle validates mechanics, not prevalence, effect size, transfer, or model performance.

### 2. Nonconfirmatory pilot: estimate the design

Collect complete batches under deliberately varied days, operators, instruments/configurations,
and material lots. Pilot outcomes may be used to estimate:

- assay repeatability and target uncertainty;
- within- and between-batch outcome variance;
- failure prevalence, follow-up time, and censoring mechanisms;
- representation availability and reasons for missingness;
- environment shift and concentration of subjects within parents;
- storage, processing, annotation, assay, and decision latency costs; and
- feasible learner capacity and hierarchical power.

The pilot can repair parsers, schemas, and simulation assumptions. A QC threshold or availability
rule may change only for an outcome-independent engineering reason, preferably under a QC role
firewalled from pilot targets; association with the pilot outcome may never select a QC rule. The
pilot is a permanent development set and never later becomes confirmatory evidence. Its physical
parents, descendants, continuations, lots, and specimens are disjoint from confirmatory subjects,
or any unavoidable shared ancestry is declared and excluded from confirmatory inference.

### 3. Prospective confirmatory collection

Before confirmatory outcomes are visible to representation builders or analysts, freeze:

- endpoint, physical subject, horizon, eligibility, censoring, adjudication, and assay uncertainty;
- state cutoff, acquisition cutoff, construction time, operational deadline, and allowed action;
- exact representation DAG, report fields, side inputs, versions, and availability rules;
- primary adjacent edge, complementary arms, current-rule baseline, and fallback behavior;
- primary held environment and external-site evaluation mode;
- independent grouping unit, nested tuning, metrics, learner envelope, and failure behavior;
- meaningful risk benefit, bounded-adequacy margin, environment harm bound, and utility threshold;
- cluster-aware sample size and extension/stop rules from hierarchical simulation;
- assignment, input, QC, outcome, analysis, and release manifest schemas; and
- code commit, split-assignment hash, sign-offs, and the exact outcome-release procedure.

Confirmatory batch IDs are registered before execution. For every subject, eligible early inputs
and the ordinary report must be immutable before that subject's outcome or outcome-completion
signal becomes accessible to their builders. A later batch-close certificate proves aggregate
completeness but cannot repair reversed unit-level chronology. Delayed outcomes live in a separate
encrypted namespace under a separate custodian until the reveal gate; filenames, hashes,
availability flags, and completion signals are also protected.

The default reveal occurs once after the entire confirmatory cohort closes. If staged reveals are
scientifically necessary, every later stage is a newly registered cohort with its own frozen
assignment, inputs, analysis, and error-spending rule; an early reveal may not silently influence
later QC, transforms, stopping, or collection.

## Collection design: a partner-native stream plus a bridge panel

The design has two synchronized tracks.

### Partner-native stream

Capture the ordinary production, development, or qualification workflow in shadow mode without
changing the current decision. This preserves real report use, authentic failure modes, natural
missingness, and operational costs.

Record the ordinary report, decision, allowed action set, chosen action, timing, rationale,
fallback, and whether any research output was visible. Study models never intervene during shadow
collection. If the ordinary report-driven action can alter Y—for example by stopping, rerouting,
reworking, or changing later processing—the primary estimand must be explicitly one of:

- predictability under the frozen existing policy;
- performance under a fixed post-cutoff protocol;
- a reference outcome measured before action effects; or
- a causal policy estimand with actions, assignment probabilities, positivity, and interference
  assumptions recorded.

Stop if action effects cannot be standardized, measured, or identified for the intended claim.

### Crossed bridge panel

Repeat a small set of scientifically relevant conditions or reference materials in every batch,
instrument configuration, and participating site. Multiple conditions also appear within every
batch. Rotate operators, lots, days, and assay order within feasible blocks. These bridge subjects
make condition effects distinguishable from collection identity.

Freeze whether bridge subjects are calibration-only, a secondary balanced estimand, or part of a
deployment-weighted primary estimand. Their weights may not be chosen after outcomes. A bridge
subject can support a compression claim only when it traverses the same report, action, and
downstream-outcome chain; otherwise it diagnoses acquisition or instrument drift only.

Exact counts are not chosen by rule of thumb. The golden bundle establishes feasibility; the pilot
estimates variance, cluster sizes, failures, censoring, and support; hierarchical simulation then
sets the number of independent parents and environments needed both to detect meaningful loss and
to declare bounded adequacy. Additional scans, cycles, aliquots, or devices from one parent improve
measurement precision but do not increase the independent-batch count.

The primary split mimics deployment and contains multiple prospectively held independent material
or manufacturing batches, with the count set by hierarchical simulation. One future batch is a
case study, not a population-level batch-transfer design or a basis for an environment harm bound.
Random-unit splits are diagnostic only. The external site is reserved prospectively and one mode
is named before collection:

1. zero-shot transfer of a frozen model;
2. a frozen model after a predeclared site-calibration subset; or
3. protocol replication with site-specific retraining.

Only mode 1 demonstrates zero-shot model transfer. Mode 3 can still validate the audit protocol.
For a calibrated external mode, calibration and test parents are assigned before external outcomes
are seen; preprocessing cannot adapt on test outcomes. A changed report schema or transformation
DAG is a new pipeline audit, not transport of the original reporting edge. One named external site
establishes replication there, not generalization over a population of sites.

## Outcome and follow-up contract

Prefer a continuous, failure-aware primary outcome; pass/fail may be secondary. The target must
remain meaningful for early physical failures. Examples include cumulative delivered performance,
survival/degradation, activity or strength retention, corrosion loss, or signed distance from an
externally established final specification.

Record exact outcomes, terminal events, right or interval censoring, destructive-test absence,
operational dropout, not-followed status, and missing/invalid assays separately. Preserve lower
bounds and follow-up time. Do not condition the target on surviving to a convenient horizon, and
do not encode a failure as zero unless that value has a physical or decision-utility meaning fixed
in advance.

All eligible confirmatory subjects receive reference follow-up regardless of early evidence,
ordinary report, model prediction, or apparent quality. If the SOP can scrap, consume, reroute, or
rework a unit before reference follow-up, select the audit sample from all eligible units before
the first selection-causing report or action, record known inclusion probabilities, and verify
that reference recovery remains physically feasible. Otherwise narrow the target population and
claim explicitly. Hand-selection of interesting subjects is not repaired by retaining only the
denominator.

Outcome assay order, plate/run, instrument, and operator are randomized or blocked so they do not
identify a production batch, condition, or representation-availability state. Assay operators and
adjudicators are blinded to research predictions and early representations and, where operationally
possible, the ordinary report. Unavoidable inputs are logged. Exposed subjective adjudication or
irreparable assay-batch confounding blocks the corresponding claim.

The delayed outcome is a separate versioned product joined to its physical subject. It does not
overwrite the execution event's status and should not be squeezed into a free-form event summary
when its unit or horizon differs from the producing event.

## Immutable data products

Each partner bundle uses the following logical layout; Parquet, JSONL, CSV, or a database view may
implement a ledger so long as the schema, keys, snapshots, and hashes are fixed.

```text
partner_bundle/
  collection_contract.json
  assignment.csv
  ledgers/
    attempts.*
    lineage_nodes.*
    lineage_edges.*
    artifacts.*
    representations.*
    outcomes.*
    decisions.*
    costs.*
    deviations_and_corrections.*
    source_denominator_counts.*
  raw_native/
  portable_exports/
  derived/
  reports/
  certificates/
    batch_close.*
    input_freeze.*
    outcome_reveal.*
    external_test_release.*
  checksums.sha256
```

Required identity classes are study, plan, attempt, material batch, aliquot/specimen, device or
qualification subject, observation, artifact, transform run, report, assay, and outcome. IDs are
opaque, assigned before the relevant action, never reused, and never encode outcome or provenance.
Retries and rework receive new attempt IDs linked to their parents.

Every artifact records its SHA-256, byte size, native format, portable companion, producer,
instrument/firmware/configuration, acquisition start/end, repository receipt, parent hashes,
transform code/configuration, creation time, operational-ready time, and escrow location. Preserve
vendor-native bytes in append-only storage. A correction creates a successor artifact and lineage
edge; it never replaces the original.

Native escrow specifies encryption and key custody, replica count and independent failure domains,
object-lock duration, decoder/license preservation, retention and deletion/return rules, access
triggers, restore tests, and proof that the captured bytes preceded any overwrite or project
transform. Transform provenance also records runtime/container/dependencies, ordered parameters,
calibration and reference-library parent hashes, deterministic status and random seed, and any
manual-edit attestation.

Every report snapshot is retained in original and structured form with schema/SOP version, units,
rounding, uncertainty, missingness, confidence, abstention, side inputs, author/software, and
creation/ready times.

## Four clocks and one event origin

Define event `t0` physically. Keep these concepts separate for every representation:

1. latest material-state time used;
2. acquisition start/end;
3. transformation or report construction time; and
4. operational-ready time.

Also record outcome horizon/assay time, repository receipt, input-freeze time, and outcome-release
time. Wall clocks use UTC ISO-8601 while retaining the original timezone, relative elapsed time,
synchronization method, and known drift.

Clock records include authoritative source, synchronization event, measured uncertainty/drift,
maximum allowable timing error, and correction history. Exceeding the bound makes the operational
timing claim unavailable even when a timestamp is present.

A specimen arrested before the state cutoff but measured later can support an early-state
scientific claim. It supports an early operational decision only when the result was ready before
the decision deadline.

## Complete attempt and support ledger

Create an attempt row when work is scheduled, before the outcome is known. Its state machine keeps
at least:

```text
planned -> cancelled_or_withdrawn_before_start
        -> resource_unavailable_or_declined
        -> started -> completed
                   -> physical_failure
                   -> aborted
                   -> partial
                   -> retry_or_rework_linked

delayed follow-up: eligible -> observed_exact
                              -> right_or_interval_censored
                              -> not_followed_by_design
                              -> lost_or_invalid_assay
```

Planned conditions and actual observed conditions are separate fields. Missing artifact, invalid
measurement, below-detection result, genuine physical failure, operator deviation, and target
censoring use different reason codes.

Reconcile the attempt ledger against an independent source—scheduler, LIMS, inventory, instrument
log, or order system—at least weekly and at batch close. Report counts by batch, session, operator,
condition, and status, not only overall. Golden, pilot, calibration, and confirmatory roles are
immutable.

Each delivered bundle includes a strict `partner_source_denominator.v1` snapshot of that
independent source. Its source system, extract ID/time, assignment/attempt/follow-up state counts,
and domain-stratified counts must equal the bundle declaration and its bytes must equal the
artifact-ledger hash. Pointing at an arbitrary file with the expected hash field is not
reconciliation; the validator parses and compares the snapshot contents.

Every batch and outcome handoff is transactional: sender and receiver sign the file/schema/hash
manifest, transport method, acceptance or rejection, discrepancy list and resolution deadline,
and supersession chain. Batch close fails while denominator, lineage, checksum, or clock
discrepancies remain unresolved.

## Outcome-blind QC and transformation firewall

QC rules come from manuals, calibration standards, physical bounds, and permanently
nonconfirmatory examples. QC staff, early-representation builders, and their compute environment
cannot access confirmatory outcomes or model residuals.

Input code uses an allowlist and rejects post-cutoff state, outcome, downstream label, prohibited
provenance, and future-derived quality fields. Unusual or low-signal observations remain present;
rarity or model error is not an invalidity rule. Every exclusion preserves the artifact, flag,
reason, ruleset version, and timestamp.

Scaling, imputation, dimensionality reduction, feature selection, calibration, and learned
transformations fit inside the training partition. Deterministic project-wide transforms may be
frozen before outcome release only when they are outcome blind and their parents and versions are
fully recorded.

## Access gates

| gate | validator readiness | evidence required | release |
| --- | --- | --- | --- |
| G0 legal and operational | intake only | rights, security, release mode, named roles, real action/report | de-identified schema/examples |
| G1 golden bundle | `golden` | ordinary and failure/censor lineage reconstruct; source counts reconcile | permanently nonconfirmatory bundle |
| G2 capture qualification | `pilot` plus qualification review | native export, escrow, hashes, clocks, decoder, report DAG pass | blinded input dry run |
| G3 scientific freeze | `confirmatory_start` | endpoint, cutoff, assignment, QC, transforms, analysis, costs, release signed and committed | confirmatory early inputs only |
| G4 batch/input close | `input_close` | attempts reconciled; native artifacts, reports, QC, and corrections frozen | read-only input snapshot |
| G5 outcome reveal | `outcome_reveal` | horizon complete; target hash, eligibility counts, access review, joins, reveal certificate signed | exact confirmatory outcomes |
| G6 external validation | `external_validation` | model and claim frozen; external mode and calibration IDs declared | independent-site data |
| G7 release | `release` | fixed confidentiality/patent review complete; hashes verified | agreed reproducibility package |

The reveal certificate records the preregistration commit, assignment hash, input-manifest hash,
target hash, eligibility/censor counts, unresolved corrections, access-log review, and exact first
analyst access time.

## Roles that must remain access-separated

At minimum name scientific, operations, instrument/data-steward, lineage-trustee, outcome-custodian,
blinded-QC, analysis, security/legal, and publication/release owners. A small partner may assign
several roles to one person, but the outcome custodian, input-QC function, and confirmatory modeler
must not share pre-reveal outcome access.

Freeze an artifact-class × role × gate access-control matrix. Identity crosswalks and outcomes use
separate stores and credentials, immutable access logs, periodic recertification, and explicit
offboarding. Access to a hash, filename, row count, or follow-up-completion signal counts as access
when it can reveal target status.

Publication review is limited to removing confidential information and a fixed patent-filing
delay. It cannot suppress unfavorable results. Rights must explicitly cover native evidence,
portable exports, intermediates, reports, outcomes, metadata, derived features, audit results,
code/model artifacts, retention, and the selected public/controlled/enclave/aggregate release
mode. Aggregate-only access without an independent verifier downgrades the project to internal
engineering.

The rights schedule names owner/licensee, permitted purpose, derivative/model/IP rights, term,
termination handling, security jurisdiction, subprocessors, maximum review/embargo duration, and
the minimum release. An aggregate release enumerates attempt and support denominators, reason
codes, per-environment estimates and intervals, null results, code/hashes, and independent-verifier
access rather than promising an undefined summary.

## Corrections and deviations

Corrections are append-only.

- Before input freeze: correct, document, re-run qualification, and issue a new version.
- After input freeze but before outcome reveal: apply only an objective predeclared rule with
  two-person approval. A material change requires a new preregistered version and fresh subjects;
  otherwise affected subjects are permanently downgraded to sensitivity/nonconfirmatory status.
- After outcome reveal: preserve the frozen primary data. A correction enters a separately
  versioned sensitivity or invalidates the affected claim.
- Target corrections are made by the outcome custodian without model predictions.
- A protocol deviation remains a deviation; it is never rewritten as the planned condition.

Every correction notice records affected IDs and hashes, discoverer/time, reveal state, proposed
change, approvals, before/after hashes, and impact on eligibility, support, analysis, and claims.

## Evaluation and decision gates

Report common-support task risk, representation availability, target/follow-up support, decision
support, structural collisions, per-environment results, and total workflow utility separately.
Missing reports do not disappear: evaluate a frozen fallback policy and include their operational
cost.

Predeclare representation-appropriate but bounded learner families, tuning/compute budgets,
decoder checks, learning-curve diagnostics, and behavior when the richer arm is not estimable. A
high-dimensional arm failing from inadequate independent parents is a design failure, not evidence
of adequate compression. Simultaneous inference covers the frozen family of adjacent edges,
endpoints, held environments, and harm tests. Outcome-dependent extension is allowed only through
a fully specified group-sequential design; blinded re-estimation may use nuisance quantities only.

Orient every adjacent risk gap as compressed risk minus richer risk. A premature-compression claim
requires the simultaneous lower bound to exceed the meaningful benefit threshold in the primary
held environment and no held environment to cross its harm bound. Adequate compression requires
the upper bound to exclude improvements larger than that threshold while coverage and collision
bounds pass. Everything between is inconclusive.

Prediction utility in shadow mode is identifiable only when every candidate action's payoff is a
frozen function of a uniformly observed reference outcome and costs. If actions alter outcomes,
unchosen-action utility is counterfactual and requires causal assumptions, logged propensities and
positivity, or the later randomized trial. Yield, scrap, delay, or cost claims require a randomized
or concurrent policy trial with continued reference outcomes on all subjects or a randomized
audit subset.

## Partner cadence

- Per acquisition: native upload, hash receipt, and ledger link within 24 hours.
- Per day/shift: automated duplicate-ID, missing-file, hash, schema, and clock checks.
- Weekly: denominator reconciliation and unresolved-deviation review.
- Per batch: signed batch-close package and immutable input snapshot within two business days.
- Monthly: access, storage integrity, corrections, support counts, and partner-burden review—never
  representation performance on confirmatory outcomes.
- Before reveal: QC freeze, access-log review, lineage validation, target snapshot, and signed
  certificate.
- Quarterly: escrow restore test and access recertification.
- Incident: security, lineage, hash, or accidental-unblinding notice within 24 hours.

## Stop conditions

Do not begin a confirmatory collection if any of the following remains true:

- no real early decision or actual conventional report exists;
- native evidence or a usable decoder cannot be retained;
- outcomes require ambiguous or manual joins;
- failures, retries, or not-followed subjects are absent from the source denominator;
- the target is only a later transformation of the same channel without an independent purpose;
- conditions are nested inside batches for a claimed batch-transfer result;
- QC/report builders/modelers cannot be firewalled from outcomes;
- files, reports, or corrections can overwrite the frozen record;
- assay uncertainty is comparable to the smallest useful effect;
- the pilot lacks enough target, report, action, failure, or collision variation and overlap to
  identify either material loss or bounded adequacy;
- ordinary post-cutoff actions affect the outcome but cannot be standardized or identified;
- outcome adjudication is exposed or assay environment is irreparably confounded with production;
- unit-level input/report freeze occurs after outcome access or an outcome-completion signal;
- the planned richer-arm learner cannot be estimated reliably at the available independent-parent
  count and bounded compute budget;
- hierarchical simulation cannot support both meaningful-loss and bounded-adequacy conclusions;
- an external validation population cannot be reserved; or
- the partner cannot permit a meaningful null or unfavorable release.

## Immediate execution order

1. Screen candidate workflows with the endpoint/decision card and hard stop conditions.
2. Select one workflow; do not hedge across several endpoints or material systems.
3. Instantiate the machine-readable collection contract and name owners, units, IDs, clocks,
   representations, outcome, environments, rights, and release mode.
4. Receive and audit the golden bundle, including one negative/censored/reworked case and source
   denominator totals.
5. Price the pilot only after lineage, native escrow, report capture, outcome construction, and
   publishability pass.
6. Run the nonconfirmatory pilot and hierarchical design simulation.
7. Freeze the assignment, analysis, QC, outcome, cost, and reveal manifests in one commit.
8. Start confirmatory collection only after all G3 sign-offs and hashes pass automatically.

The paper strategy follows the same gates. The framework and public engineering controls can form
a methods spine; the central materials claim requires the partner's actual report edge, an
independently measured consequential outcome, crossed held environments, and external replication.
