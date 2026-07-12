# Task-Relevant Compression Audit

Status: protocol spine, revised 2026-07-12. The
[downstream-failure program](downstream_failure_research_program.md) owns the evidence ladder; the
[partner pipeline](../controlled-collection/partner_collection_pipeline.md) owns collection and
readiness operations. The reusable scoring core is
[`compression_audit.py`](../../src/materials_event_modeling/eval/compression_audit.py).

## Question

> For a declared task, where does an experimental record first lose transferable,
> decision-relevant information, and was the upstream evidence retained?

A label can be an excellent compression: cheap, stable, sample-efficient, and adequate for one
decision. A rich trace can contain useful signal, redundant smoothness, provenance, or all three.
Every verdict is therefore indexed by target, cutoff, action, loss, learner family, sample size, and
collection environments. Neither `raw` nor `label` receives a global verdict.

The audit reports four irreducible objects:

1. **common-support task risk**—which representation predicts or decides better where both exist;
2. **event and decision support**—which attempts or decisions the compression omits;
3. **representation collisions**—which relevant alternatives it makes indistinguishable; and
4. **recoverability and cost**—whether richer evidence remains available and at what burden.

## Start above the adapter

```text
physical process
-> measurement opportunity and capture policy
-> retained native artifact
-> export / adapter
-> analysis representation
-> report or label
-> action
```

A differential audit cannot detect information removed before all arms share a root. Before
defining representations, freeze:

- a **measurement-opportunity ledger**: eligible modalities/actions and what was selected, declined,
  failed, or unavailable;
- a **native-artifact inventory**: what instruments and process systems actually retained; and
- an **adapter policy**: included, reference-only, omitted, and never-captured channels, intervals,
  failures, and metadata.

Every omission states the result it could preordain and the experiment that would test it. If the
audit begins at an adapted table, its verdict says that all upstream edges are untested. Envelope
conformance and observation count do not establish evidence coverage.

## Variables and estimand

For event or physical subject $i$:

- $X_i^{\leq\tau_s}$: the richer audited record whose material state is fixed by cutoff $\tau_s$;
- $L_i^{\leq\tau_s}$: the report, label, scalar summary, or compressed representation;
- $C_i^{\leq\tau_s}$: context legitimately available to both arms;
- $Y_i$: the frozen target; for a decision, also action $a$ and utility $u(a,Y)$;
- $E_i$: the independent environment relevant to transfer—batch, session, instrument, operator,
  lot, lab, or a declared combination;
- $S_i^Z$: whether representation $Z$ is available by its frozen deadline;
- $D_j^Z$: whether $Z$ can express decision instance $j$;
- $\mathcal V$: frozen preprocessing, learner, calibration, and decision-rule families; and
- $\ell$: task-native loss, oriented so lower is better.

An optional decision deadline $\tau_d$ is distinct from state cutoff $\tau_s$. Evidence sampled by
$\tau_s$ but processed later may support a sampled-state claim; it is not an operational input
unless ready by $\tau_d$.

Name the estimand in full:

> task-relevant compression loss for $Y$, state cutoff $\tau_s$, optional deadline $\tau_d$,
> context $C$, loss $\ell$, environments $E$, learner family $\mathcal V$, and the observed
> independent-unit structure.

Changing any index creates a new audit. A label may be adequate for screening and inadequate for
fault diagnosis on the same events.

## Physical-unit lineage and target support

Consequential outcomes often belong to descendants of the execution event:

```text
execution -> material batch -> aliquot/specimen -> device or lot -> outcome Y at horizon h
```

The join to the target subject is immutable and machine-resolvable. Freeze the subject, horizon,
assay, uncertainty, eligibility, follow-up, censoring, destructive-test selection, and target
population before outcome access.

Do not conflate:

- execution status (`success`, `failure`, `ambiguous`, `aborted`, or `unknown`);
- target eligibility and follow-up;
- right/left/interval censoring; and
- representation availability at the decision deadline.

Report attempted, eligible, followed, assayed, and representation-available denominators with
reason codes. Complete-case prediction does not repair informative follow-up. Rows descending from
one material batch are not independent evidence about a material-level signal; splits and
uncertainty use the highest shared ancestor relevant to the claim.

Repeatability means same-method short-interval variation; changed within-lab days, operators, lots,
or instruments test intermediate precision or process robustness as named; independent sites are
required for reproducibility.

## Common-support task risk

The shared evaluation set in environment $e$ is

\[
\mathcal I_e^{\cap}=\{i:E_i=e,\;S_i^L=S_i^X=1,\;C_i,Y_i\text{ satisfy frozen rules}\}.
\]

For features $Z$, define strictly out-of-fold risk under the frozen learner family:

\[
\mathcal R_{\ell,e}^{\mathcal V}(Z)
=\mathbb E_e[\ell(Y,\hat f_Z^{-\mathrm{eval}}(Z))\mid i\in\mathcal I_e^{\cap}].
\]

All preprocessing, selection, tuning, and calibration occur inside training folds. Compare four
arms on identical units:

```text
C          context
C + L      compressed report
C + X      richer record
C + L + X  complementarity
```

Define the task-relevant compression loss

\[
\mathrm{TRCL}_e=\mathcal R_{\ell,e}^{\mathcal V}(C,L)
-\mathcal R_{\ell,e}^{\mathcal V}(C,X),
\]

and the report's conditional value beyond the richer record

\[
\Delta_{L\mid X,e}=\mathcal R_{\ell,e}^{\mathcal V}(C,X)
-\mathcal R_{\ell,e}^{\mathcal V}(C,X,L).
\]

Positive values mean the second arm reduces loss. Report paired cluster-aware intervals in native
task units. Bits or mutual-information estimates are secondary and only meaningful with calibrated
probabilistic models.

## Support and collisions

Common-support risk cannot describe events the compressed record removed.

Event support is

\[
\mathrm{coverage}_{L,e}=\frac{\sum_i 1[E_i=e]S_i^L}{\sum_i1[E_i=e]}.
\]

Decision support is defined over the predeclared decision ledger:

\[
\mathrm{decision\ coverage}_{L,e}=\frac{\sum_j1[E_j=e]D_j^L}{\sum_j1[E_j=e]}.
\]

Report both overall and by outcome/environment. A ranking representation that maps all replicates
of one recipe to the same vector creates a collision even if every row remains present. For each
task, enumerate equivalence classes induced by the representation and identify decisions forced to
tie or collapse. Structural loss floors remain separate from learned performance.

## Provenance stress and transfer

Random splits answer only an in-corpus question. Choose a primary held-environment split matching
the claim, preserve all descendants of an independent unit in one partition, and report:

- per-environment risks and paired TRCL;
- environment/sample counts and cluster concentration;
- $E\leftrightarrow Y$ association and support overlap;
- recoverability of $E$ from each representation; and
- random/grouped versus held-environment reversal.

Provenance recoverability is a warning, not proof of shortcut use. A richer arm earns transferable
value only when its task increment survives the relevant held environment. External-site evidence
is required for a cross-lab claim.

## Localizing a lossy edge

A ladder such as

```text
native artifact -> calibrated trace -> features -> report -> grade
```

supports edge localization only when every node is a verified transformation of declared parents.
Record parent IDs, side inputs, human roles, code/config versions, clocks, and availability. If a
human used visual observations, memory, or prior samples absent from the trace, the report is a
nonnested branch.

For a verified chain, audit adjacent transitions on the same task and identify the earliest edge
whose risk, support, or collision bound fails. For nonnested nodes, report conditional value and
complementarity; localize only to a bracket of possible inputs. Predictability of a child from a
parent neither proves nor disproves lineage.

## Adequacy and allowed verdicts

Freeze before outcome access:

- $\delta_R$: smallest worthwhile task-risk improvement;
- $\delta_S$: largest acceptable event/decision support loss;
- $\delta_C$: largest acceptable collision burden;
- $\delta_U$: smallest worthwhile decision-utility gain; and
- uncertainty, multiplicity, and harm rules.

A null difference is not proof of sufficiency. Allowed primary verdicts are:

1. **richer value detected**—TRCL clears $\delta_R$ and transfer/harm gates;
2. **compressed representation bounded adequate**—the confidence bound excludes a loss larger than
   $\delta_R$ and support/collision bounds pass;
3. **complementary**—$L$ adds value beyond $X$ or vice versa;
4. **support-destructive**—risk may be adequate on common support but support/collision bounds fail;
5. **nontransferable**—the apparent gain collapses in the frozen held environment; or
6. **inconclusive**—data or uncertainty cannot distinguish value from adequacy.

Every verdict names the target, cutoff, learner family, environments, sample size, and bounds.

## Recoverability and cost

Classify upstream evidence at each edge as:

1. exact and integrity-checked;
2. retained in a known lossy form;
3. approximately reconstructable with measured error;
4. deleted or inaccessible; or
5. never captured.

Analytic compression can harm a decision even when the native artifact remains recoverable.
Retention compression makes that harm irreversible. The final frontier reports worst-environment
risk, support, collisions, decision utility, acquisition/storage/annotation/latency cost, and
recoverability together. Adequacy of an online report does not automatically authorize deletion of
native evidence needed for future tasks, verification, or incident analysis.

## Minimum output contract

Each audit emits a human report and machine-readable manifest containing:

- preregistration and run identity; input hashes and exact artifact/reader versions;
- target, action, utility, cutoffs, contexts, environments, loss, learners, margins, and unit of
  independence;
- opportunity ledger, native inventory, adapter policy, representation DAG, and side inputs;
- attempt/eligibility/follow-up/assay/representation denominators and collision ledger;
- split and leakage assertions, out-of-fold predictions, environment diagnostics, and baselines;
- arm risks, paired TRCL and complementarity intervals, support, cost, and sensitivity analyses;
  and
- one allowed verdict plus unresolved mechanisms and the next result-changing experiment.

The audit is incomplete if it reports an accuracy gap without denominators, calls nonsignificance
adequacy, omits unavailable events, hides an upstream adapter edge, or pools environments in a way
that changes the estimand.

## Claim boundary

TRCL measures usable information under declared conditions. It does not identify a mechanism,
prove causality, reveal when the outcome became physically determined, or recover a true ontology.
Mechanism claims require predeclared temporal/modality predictions, interventions,
counterbalancing, or independent measurement.

The protocol is deliberately capable of concluding that a conventional report is adequate. Its
contribution is an instrument for learning which compression is harmless for which decisions,
which extra signal transfers, and which evidence was discarded before anyone knew to ask for it.
