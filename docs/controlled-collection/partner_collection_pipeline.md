# Partner Downstream-Compression Collection Pipeline

Status: active operational contract, revised 2026-07-12. Scientific definitions live in the
[task-relevant compression audit](../spine/task_relevant_compression_audit.md); study ambition and
phase gates live in the
[downstream-failure program](../spine/downstream_failure_research_program.md).

## Strategy

For one real decision at one frozen deadline, collect a matched and versioned chain from
measurement opportunity through native evidence and the actual report to a delayed outcome. Test
which representation preserves held-environment decision value at acceptable support, cost, and
latency.

```text
measurement opportunity / action set
-> human, scripted, or adaptive capture policy
-> retained native artifact X0
-> calibrated or cleaned artifact X1
-> engineered features X2
-> actual report S
-> label or grade L
-> delayed outcome Y
-> action and utility
```

Every node records parents, clocks, versions, hashes, availability, and side inputs. Loss is
localized to an edge only when that parent-child transformation is verified. Human reports with
unrecorded evidence are nonnested branches and receive complementarity, not causal-edge, language.

## Known v1 boundary

The executable v1 schemas begin at `X0`. They validate retained artifacts, transformations,
representations, reports, outcomes, decisions, costs, and physical lineage, but they do not yet
encode the opportunities and actions that determined what became `X0`. A v1 bundle can therefore
pass while selective acquisition remains invisible.

Do not mutate the hash-bound v1 schemas. Before a real partner bundle is accepted, collect a
companion opportunity inventory with:

- policy ID and mode (`fixed`, `human`, `scripted`, or `adaptive_model`);
- allowed inputs and available measurement actions;
- modality, acquisition/state time, selected action, and status (`captured`, `declined`, `failed`,
  or `not_available`);
- output artifact IDs, reason codes, and selection probability when policy evaluation is claimed;
  and
- whether the policy changed the specimen or future measurement process.

After one real golden bundle reveals the minimum fields, issue v1.1 and add validator checks. Until
then, v1 is a below-capture mechanics contract, not permission to begin confirmatory collection.

## Executable v1

- [`partner_study.v1.schema.json`](../../schemas/partner_study.v1.schema.json): decision, unit
  graph, representation DAG, outcome, environments, firewall, retention, and signoffs.
- [`partner_rows.v1.schema.json`](../../schemas/partner_rows.v1.schema.json): assignments,
  attempts, physical nodes/edges, artifacts, transformations, representations, outcomes, costs,
  decisions, and corrections.
- [`partner_bundle.v1.schema.json`](../../schemas/partner_bundle.v1.schema.json): file inventory,
  hashes, denominators, rights, and release state.
- [`validate_partner_bundle.py`](../../scripts/validate_partner_bundle.py): schema, hash, lineage,
  timing, state-machine, denominator, firewall, and readiness checks.
- [`partner_golden_bundle_synthetic`](../../data/examples/partner_golden_bundle_synthetic/README.md):
  permanently nonconfirmatory fixture for testing mechanics only.

```bash
.venv/bin/python scripts/validate_partner_bundle.py \
  data/examples/partner_golden_bundle_synthetic --readiness golden
```

## Three collection roles

### Golden bundle

A small nonconfirmatory packet traverses the whole chain. It includes an ordinary attempt and a
failure, censor, abort, retry, or rework when available; native bytes and portable exports; readers,
units, clocks, transformations, real report, delayed outcome, action, cost, rights, and source
denominators. All golden units remain permanently nonconfirmatory.

Passing proves that files and joins work. It does not estimate an effect, denominator completeness,
power, or transfer.

### Pilot

The pilot estimates assay noise, batch/environment variation, support loss, missingness, censoring,
failure prevalence, cluster concentration, and costs. It is used for hierarchical simulation and
may change the confirmatory design. It is not a weakly labeled confirmatory set.

### Confirmatory collection

Before outcomes are accessible, freeze the outcome and subject, action and utility, state cutoff
and decision deadline, capture policy, representation DAG, actual report, availability rules,
costs, learner family, split, margins, sample size, external-site plan, and stop rules. No pilot or
golden unit enters confirmatory evaluation.

## Unit and denominator rules

The machine-resolvable physical graph is:

```text
assignment -> attempt -> material batch -> aliquot/specimen -> device or lot -> outcome evidence
```

Every split, merge, consumption, retry, rework, and assay link is explicit. The unit of inference
is the highest shared ancestor relevant to the claim; cycles, scans, spectra, aliquots, and devices
do not become independent material batches by occupying separate rows.

Keep these states separate:

- planned, released, initiated, completed, failed, ambiguous, aborted, and not started attempts;
- target eligibility, follow-up, assay, and outcome missingness;
- right/left/interval censoring;
- representation availability at the decision deadline; and
- corrections, retries, and reworks.

Source-ledger aggregates must reconcile with bundle rows. Knowing a selected denominator does not
identify unobserved outcomes; informative follow-up needs a frozen sampling or sensitivity design.

## Artifact and clock rules

Retain vendor-native bytes in immutable storage with SHA-256, byte count, exact locator, native
format, portable companion, reader recipe, producer, parents, and retention class. Corrections
create successors and tombstones; they never overwrite history. Restore tests, decoder licensing,
encryption, access roles, and independent replicas are part of the retention policy.

Record four clocks separately:

1. material-state time;
2. acquisition time;
3. construction time; and
4. operational availability time.

Evidence sampled by a cutoff but processed later may support a sampled-state claim. It is not an
eligible real-time input unless ready by the frozen decision deadline.

## Firewall and roles

Outcome-blind QC may check identity, readability, units, clocks, ranges, missingness, and frozen
rules. It may not invent outcome-favorable features, exclusions, or corrections. Separate, named
owners cover scientific design, practitioner action, outcome assay, data lineage, representation
building, analysis, and release. The representation builder cannot see outcomes; the outcome team
cannot tune the input representation.

## Readiness lifecycle

| readiness | purpose | minimum evidence |
| --- | --- | --- |
| `golden` | mechanics | valid files, hashes, joins, report/outcome/action examples, costs |
| `pilot` | design estimation | multiple independent units and usable native/report/outcome chains |
| `confirmatory_start` | authorize collection | assignments, locks, signoffs, firewall, frozen environments and external test |
| `input_close` | close early inputs | attempts and representations reconciled; native/report chains frozen |
| `outcome_reveal` | open outcomes | independent assay evidence and complete freeze-before-outcome checks |
| `external_validation` | test transfer | untouched external partition and frozen adaptation policy |
| `release` | publish | rights, release approval, corrections, hashes, and reproducible analysis |

The validator reports all readiness states but only the requested one authorizes a transition.
Capture-opportunity completion is an additional manual block until v1.1 makes it executable.

## Evaluation and go/no-go

Use identical out-of-fold units and a shared target across context, report, native/intermediate, and
complementarity arms. Report common-support risk, event/decision support, collisions, held-batch or
held-site transfer, provenance recoverability, uncertainty at the independent-unit level, and the
cost/latency frontier.

Proceed only if a known-loss and known-adequacy control classify correctly, the real golden bundle
and opportunity inventory reconcile, the pilot supports cluster-aware power, and confirmatory gains
survive the frozen environment split. Stop or narrow if native evidence/readers cannot be retained,
the real report cannot be reconstructed, outcomes are irreparably selected, too few independent
environments exist, or only an uneconomic artifact works.

## Immediate order

1. Obtain one real workflow packet and opportunity inventory without promising a study.
2. Make its v1 golden bundle pass; record every above-root edge as untested.
3. Freeze one decision, outcome, cutoff, unit graph, and transfer population.
4. Issue the minimal capture-aware v1.1 from observed needs.
5. Pilot, simulate, preregister, collect, close inputs, reveal outcomes, and test the external site.
