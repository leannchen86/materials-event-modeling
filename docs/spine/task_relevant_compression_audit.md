# Task-Relevant Compression Audit

Status: protocol spine, 2026-07-10. Extends
[project_brief.md](project_brief.md),
[capture_vs_representation_design_note.md](capture_vs_representation_design_note.md), and
[data_assumptions_and_limits.md](data_assumptions_and_limits.md). Paper positioning and prior-art
boundaries are assessed in
[compression_audit_publication_assessment.md](compression_audit_publication_assessment.md). The implementation target is
the controlled-collection program; existing public-data results are calibration cases, not a
completed audit under this protocol. The reusable evaluation core is
[`src/materials_event_modeling/eval/compression_audit.py`](../../src/materials_event_modeling/eval/compression_audit.py).

## The question this protocol makes measurable

The project should not ask whether raw traces are intrinsically better than labels. It should ask:

> For a declared downstream task, where does an experimental record first lose transferable,
> decision-relevant information, and was the upstream evidence retained?

A traditional label can be an excellent compression: cheap, stable, sample-efficient, and adequate
for a particular decision. A rich trace can contain additional physical signal, redundant
smoothness, provenance, or all three. Therefore neither `raw` nor `label` receives a global verdict.
Every conclusion is indexed by a task, observation cutoff, collection environment, learner family,
and data scale.

The encompassing object below is the **task-relevant compression audit**. It has separate,
irreducible axes:

1. **TRCL on common support** — does the richer record improve the declared task among events both
   representations can express?;
2. **support retention** — which events or decision instances did the compressed record omit?;
3. **representation collisions** — which retained alternatives did it make impossible to
   distinguish?; and
4. **recoverability** — does the upstream evidence still exist?

Using the first alone as a verdict about all attempted events is selection-biased whenever
paper-shaping deletes failures, censored runs, ambiguous cases, or other hard events. A
representation is not adequate merely because it performs well on the subset it chose to
preserve.

`Coverage` below means **representational support retention**, not a model electing whether to
answer as in selective-prediction risk--coverage analysis. Reports should use the longer term when
the distinction could be ambiguous.

## Audit variables and scope

For event $i$, define:

- $X_i^{\leq \tau}$: the richer event record available by a predeclared cutoff $\tau$, such as
  spectra, video, process logs, notes, and time-resolved measurements. `Raw` here means the richest
  retained record in the audit, not an unmediated view of reality.
- $L_i^{\leq \tau}$: the label, conventional report, scalar summary, or other compressed
  representation under audit. It may be categorical, continuous, structured, or absent.
- $C_i^{\leq \tau}$: allowed context that both arms may use, such as the planned recipe, initial
  conditions, and legitimately available metadata. Context must not include the answer by another
  name.
- $Y_i$: the predeclared downstream target. For a decision audit, also declare action $a$, utility
  $u(a,Y)$, and the decision rule.
- $E_i$: the collection environment or provenance unit relevant to the transfer claim: session,
  operator, reagent lot, instrument, lab, batch, or a declared combination.
- $S_i^L\in\{0,1\}$: whether the compressed representation preserves an observable record for the
  event at the decision point.
- $D_j^L\in\{0,1\}$: whether compressed representation $L$ can express and evaluate decision
  instance $j$. A decision instance may be one event, a ranking pair, a retrieval query, or an
  action set.
- $\mathcal V$: the frozen learner and decision-rule families, including preprocessing,
  hyperparameter search, calibration, and feature budgets.
- $\ell$: the frozen task-native loss, oriented so lower is better.

The audit estimand is always named in full:

> TRCL for $Y$, using information available by $\tau$, under loss $\ell$, contexts $C$,
> environments $E$, learner families $\mathcal V$, and the observed sample size and cluster
> structure.

Changing any of those indices creates a new audit. In particular, a label may be adequate for phase
screening and inadequate for fault diagnosis on the same events.

## Information-availability contract

Every representation must ship with an input and time contract before outcomes are unblinded:

| field | required declaration |
| --- | --- |
| representation ID | immutable name and schema/version |
| prediction cutoff | latest event time whose information may enter |
| actual inputs | fields, modalities, and side information used to construct it |
| construction time | when the representation was produced |
| blinding | outcomes, future observations, and provenance identifiers hidden from its producer |
| availability rule | what makes an event representable or unrepresentable |
| upstream retention | retained exactly, approximately recoverable, deleted, or never captured |

Construction time may be later than the prediction cutoff. For example, an early human label may
be assigned offline from a frozen packet after collection, provided the packet contains only
information available by $\tau$, is randomized, and hides the eventual outcome and prohibited
provenance. No representation may consume a datum created after its declared information cutoff.

## Common-support risk

Let the common-support evaluation set in environment $e$ be

\[
\mathcal I_e^{\cap}
=
\{i:E_i=e,\;S_i^L=1,\;X_i,C_i,Y_i\text{ satisfy the frozen availability rules}\}.
\]

For a feature set $Z$, define held-out risk for the frozen learner family as

\[
\mathcal R_{\ell,e}^{\mathcal V}(Z)
=
\mathbb E_e[\ell(Y,\hat f_{Z}^{-\mathrm{eval}}(Z))
\mid i\in\mathcal I_e^{\cap}],
\]

where every prediction is strictly out of fold and all fitting, preprocessing, model selection, and
calibration occur inside the training partition. The superscript is a reminder that the result is
usable information under $\mathcal V$, not unrestricted Bayes information.

The conditional value of the richer record is

\[
\operatorname{TRCL}_{\ell,e}^{\mathcal V}
=
\mathcal R_{\ell,e}^{\mathcal V}(C,L)
-
\mathcal R_{\ell,e}^{\mathcal V}(C,L,X).
\]

Positive TRCL means that $X$ reduces risk after retaining the label and shared context. It is the
empirical counterpart of asking whether

\[
Y\perp X\mid(L,C).
\]

The audit must fit all four nested arms, not only a winner-take-all `label versus raw` comparison:

| arm | question |
| --- | --- |
| $C$ | how much is already determined by allowed context? |
| $(C,L)$ | what does the compressed report add? |
| $(C,X)$ | what does the richer event record add? |
| $(C,L,X)$ | are label and trace complementary? |

The reciprocal conditional increment

\[
\Delta_{L\mid X,e}
=
\mathcal R_{\ell,e}^{\mathcal V}(C,X)
-
\mathcal R_{\ell,e}^{\mathcal V}(C,X,L)
\]

detects expert or side information retained by $L$ but absent from recorded $X$. Robustly
positive values of both TRCL and $\Delta_{L\mid X}$ imply complementarity, not a winning
representation.

For an ideal Bayes predictor under log loss, TRCL equals conditional mutual information,

\[
\mathcal R^*(C,L)-\mathcal R^*(C,L,X)=I(Y;X\mid L,C).
\]

That identity does **not** license the same claim for a finite empirical estimator. If $L=g(X)$, an
unrestricted predictor from $X$ can reproduce $L$; a label win at finite $n$ can instead reflect
sample efficiency, useful nuisance removal, expert inputs missing from $X$, or fit to the chosen
model class. Augmented models should be able to ignore added features, but cross-fitted point
estimates can still be negative from estimation error. Negative empirical TRCL is reported, never
clipped to zero.

For a declared target distribution over environments with frozen weights $\pi_e$, two useful
aggregates are

\[
\operatorname{TRCL}_{\mathrm{average}}
=\sum_e\pi_e\operatorname{TRCL}_e,
\qquad
\operatorname{TRCL}_{\mathrm{worst}}
=\min_{e\in\mathcal E_{\mathrm{target}}}\operatorname{TRCL}_e.
\]

The minimum is only over observed target environments and is not a bound for unseen laboratories.
Neither aggregate may replace the per-environment table. A row-pooled score answers a different
question and can be dominated by the largest environment.

## Support, coverage, and structural blindness

TRCL is computed only on common support and therefore cannot, by itself, detect records removed by
compression. Every audit must report the following denominators from an attempt-level event ledger,
not from the compressed table.

### Event support

For predeclared event weights $w_i$,

\[
\operatorname{Coverage}_{\mathrm{event}}(L)
=
\frac{\sum_{i\in\mathcal I_{\mathrm{attempted}}}w_iS_i^L}
     {\sum_{i\in\mathcal I_{\mathrm{attempted}}}w_i},
\qquad
\operatorname{SupportLoss}_{\mathrm{event}}=1-\operatorname{Coverage}_{\mathrm{event}}.
\]

Report counts and reasons separately for failure, censoring, ambiguity, abortion, missing modality,
quality exclusion, and any other availability rule. A row that was never published is not an
observed `missing` token. Treating omission as a token is valid only when a downstream user really
receives an explicit missing record at deployment.

### Decision support

Let $\mathcal D$ be the full, predeclared set of decision instances generated from the attempt
ledger. For weights $v_j$,

\[
\operatorname{Coverage}_{\mathrm{decision}}(L)
=
\frac{\sum_{j\in\mathcal D}v_jD_j^L}{\sum_{j\in\mathcal D}v_j},
\qquad
\operatorname{SupportLoss}_{\mathrm{decision}}
=1-\operatorname{Coverage}_{\mathrm{decision}}.
\]

This denominator is often more revealing than event coverage. One censored event can create many
otherwise-unavailable ranking comparisons or eliminate a high-cost action. Report both unweighted
and utility-weighted coverage when an explicit utility exists.

### Representation collisions

Some records remain present but the compressed input maps decision-relevant alternatives to the
same value. For a paired task, report

\[
\operatorname{CollisionRate}(L)
=
\frac{\sum_{(a,b)\in\mathcal D_{\cap}}
\mathbf 1[(C_a,L_a)=(C_b,L_b)]}
{|\mathcal D_{\cap}|},
\]

along with the loss floor forced by those ties. This is **collapse loss**, distinct from support
loss. Same-recipe replicates are the canonical example: a recipe-only representation preserves both
rows but cannot distinguish them. Censored runs omitted from a final-results table are support loss.

No single scalar should silently combine risk, coverage, and collision. They have different
mechanisms and remedies. A deployment-specific utility may combine them only after the costs of an
unavailable event, an abstention, and a wrong decision are explicitly declared.

## Task-native loss first; bits second

Choose the primary loss from the actual task:

- continuous outcomes: MAE, RMSE, or a predeclared proper probabilistic score;
- binary/categorical outcomes: Brier score or log loss, with calibration checked;
- ranking: pairwise error or another frozen ranking loss;
- retrieval: a frozen retrieval loss at a meaningful operating point;
- operational decisions: regret under an explicit action set and utility/cost function.

Report arm risks and paired risk differences in native units. `Decision regret` is used only when
an action and utility have actually been specified; ordinary predictive loss is not relabeled as
business or scientific utility.

When calibrated out-of-fold predictive distributions are credible, a secondary common-support
estimate in bits per event is

\[
\widehat{\operatorname{TRCL}}_{\mathrm{bits}}
=
\frac{1}{|\mathcal I^{\cap}|}
\sum_{i\in\mathcal I^{\cap}}
\log_2
\frac{\hat p^{-i}(y_i\mid c_i,l_i,x_i)}
     {\hat p^{-i}(y_i\mid c_i,l_i)}.
\]

It is not called conditional mutual information unless the modeling assumptions needed for that
interpretation are defended. At pilot scale, especially for continuous $Y$ with clustered data,
conditional-density and calibration error can dominate this estimate. Bits remain secondary; wide
or negative estimates are expected possibilities and must be shown.

## Adequacy bounds and allowed verdicts

Before unblinding, declare:

- $\delta_R$: the smallest task-native risk improvement worth preserving;
- $\delta_{\mathrm{event}}$ and $\delta_{\mathrm{decision}}$: maximum tolerable event- and
  decision-support loss;
- an optional maximum collision rate or forced-loss bound;
- the confidence level, cluster unit, multiplicity rule, and whether the claim is per environment,
  average-environment, or worst-environment;
- the learner families $\mathcal V$ and the data scale at which the bounds apply.

The transfer criterion must also be frozen. Examples include clearing the bound in every
adequately powered held-out environment, clearing it for a target-weighted average while no
environment crosses a harm bound, or clearing a lower confidence bound for a hierarchical
environment distribution. These are different claims and are not interchangeable after the run.

Use paired uncertainty estimates because all arms score the same held-out instances. Resampling and
splitting must respect the true independent unit. Rows are not substitutes for sessions, policies,
preparations, specimens, or batches.

Allowed verdicts are:

| evidence pattern | permitted statement |
| --- | --- |
| lower confidence bound for TRCL exceeds $\delta_R$, with the transfer criterion met | **material task-relevant loss under the declared scope** |
| upper confidence bound is below $\delta_R$, event and decision support losses are within their bounds, and collision constraints pass | **bounded task-specific adequacy under $\mathcal V$, $n$, and the observed environments** |
| uncertainty crosses $\delta_R$ without satisfying either bounded adequacy or material loss, or coverage uncertainty crosses its bound | **inconclusive magnitude** |
| common-support TRCL is small but a support or collision bound fails | **structurally lossy despite no detected common-support gain** |
| random-split gain disappears or reverses under held-out environment | **within-corpus or provenance-sensitive gain; no transferable-loss claim** |
| both conditional increments clear their bounds under transfer | **label and trace are complementary** |

`Not significant` is never translated into `faithful`, `sufficient`, or `the right layer`.
The strongest null-side statement is of the form:

> Under losses $\ell$, learner families $\mathcal V$, $n$ events in the named environments,
> and the frozen cutoff, the upper confidence bound excludes an improvement larger than
> $\delta_R$, while event and decision support loss remain below their declared bounds.

This is finite-data, model-constrained evidence of adequacy, not proof of statistical sufficiency.

## Environment and provenance stress

Transfer claims live at the environment level. There is no universal minimum such as four
environments that converts a result into general evidence. Four deliberately counterbalanced
sessions can make a useful pilot split; they are still only four draws if the target claim concerns
future labs or manufacturing sites. The required number and balance follow from the effect size,
between-environment variance, cluster structure, and target population.

Before quoting an environment-robust TRCL, report:

1. **units, balance, and effective sample size** — events and decision instances per environment,
   independent clusters, concentration of weight, and whether uncertainty is estimable;
2. **outcome association** — $E\leftrightarrow Y$ prevalence, location, and conditional changes,
   not only a single omnibus score;
3. **representation recoverability** — how well $E$ is recovered from $C$, $L$, $X$, and
   declared feature families under leakage-safe grouped folds;
4. **support overlap** — whether contexts, labels, target ranges, and decision instances overlap
   across environments;
5. **shift diagnosis** — evidence consistent with covariate, outcome-prevalence, or conditional
   shift, plus known physical differences between environments;
6. **paired random and blocked results** — ordinary grouped cross-fitting and held-out-environment
   evaluation, with per-environment estimates before any pooled or macro summary.

Association between $E$ and $Y$ does not automatically invalidate held-out-environment TRCL.
It says the portability test includes real distribution shift and must be interpreted that way.
Nor should environment be automatically residualized away: session, lot, or instrument may
causally change the material. Matching, stratification, residualization, or invariant modeling must
correspond to a stated estimand and be fitted inside training folds.

When there are too few independent environments, report the blocked result descriptively for those
observed environments and label population transfer unresolved. Do not rescue the claim with more
rows from the same units or a noisy macro-average.

## A ladder only where the pipeline is genuinely nested

A compression ladder

```text
full multimodal event
-> cleaned or decimated trace
-> peaks and scalar summaries
-> conventional report
-> categorical label
-> paper-shaped record
```

supports localizing the first lossy transition only when each edge is a verified transformation of
the preceding representation (plus explicitly shared context). Real laboratory pipelines often
form a directed acyclic graph instead:

```text
recorded XRD -------------------> quantitative report -----> paper table
        |                                  |
recipe -+-------------------------------> human label
visual observation ----------------------> human label
technician memory / prior samples -------> human label
```

For every node $Z_k$, record its actual parents, timestamps, unavailable inputs, human roles, and
transformation version. Predicting $Z_k$ from $Z_{k-1}$ is neither a necessary nor a sufficient
test that the edge is Markov: a genuine transformation can be stochastic, and a side-informed
stage can remain highly predictable from its predecessor. Lineage and controlled construction, not
predictability alone, establish nesting.

For a verified chain, audit every adjacent transition on the same task and identify the earliest
edge whose risk, support, or collision bound fails. For nonnested nodes, report conditional value,
coverage, and complementarity; attribute loss only to a bracket of possible inputs. Whenever
feasible, promote technician observations and other side information into timestamped event fields
rather than leaving them latent.

## Compression timing and irreversibility

Task-relevant loss and recoverability are separate axes:

- **analytic compression:** a working summary discards useful variation, but the immutable upstream
  record is retained and can be reanalyzed;
- **retention compression:** the upstream record is deleted, overwritten, never captured, or made
  inaccessible, so the loss cannot be repaired from the archive.

For each edge, classify upstream evidence as:

1. retained exactly and integrity-checked;
2. retained in a known lossy form;
3. approximately reconstructable, with a measured reconstruction error;
4. deleted or inaccessible;
5. never captured.

Do not call approximate model reconstruction `recovery` without its uncertainty and failure modes.
Premature analytic compression can still cause wrong decisions even when repair is possible;
irreversible retention compression raises the cost and industrial consequence. The final design
frontier therefore reports worst-environment task risk, acquisition/storage/annotation cost, and
recoverability together. The preferred representation is the least costly one whose risk, support,
and collision measures remain inside their bounds, with upstream evidence retained when future
tasks are not yet known.

## TRCL is an instrument, not a mechanism claim

TRCL measures whether the declared representation preserves usable information. It does not show
why the information exists, whether a feature is causal, or when the outcome became physically
determined. Mechanism hypotheses are a separate layer and should predict an audit profile before
the run:

| mechanism hypothesis | predicted audit pattern |
| --- | --- |
| recipe or initial state determines the outcome | $C$ is strong; early $X$ has little conditional value |
| decisive physics unfolds during the observed window | TRCL rises as the cutoff includes that interval or modality |
| decisive transition occurs after the window | early TRCL is small; a later window may be positive |
| governing cause is unmeasured | all recorded arms remain weak despite high irreducible error |
| clock, interpolation, or provenance supplies the apparent signal | gain appears under easy splits and disappears under the relevant control or held-out environment |
| labeler used unrecorded expert evidence | $\Delta_{L\mid X}>0$, and the input-provenance DAG exposes a side parent |

Temporal windows and modality groups must be predeclared at physically meaningful granularity;
post-hoc pointwise feature importance is not a mechanism test. Interventions, counterbalancing, and
independent measurements are needed to distinguish causal explanations.

## What the existing repo does and does not establish

### Oleogel: a negative calibration case, not proof of sufficiency

Across six oleogel events, dense interpolation beat the masked model in all six leave-one-run-out
folds, the normalized clock dominated, and only one of six events retained cross-modal SAXS/WAXS
dependence beyond smoothness and clock controls. For the tested reconstruction and cross-modal
tasks, the added detail was mostly redundant or baseline-solvable. With six homogeneous events,
this is not evidence that a traditional label is generally sufficient; it is a warning that a
rich trace and an impressive reconstruction score need not contain incremental decision value.
See [findings_summary.md](../event-method/findings_summary.md).

### RRUFF: ontology evidence, but not yet a TRCL task

RRUFF spectra distinguish same-composition polymorphs, and garnet spectra recover structural family
more sharply than named species: family accuracy was 1.0, species accuracy approximately 0.73, and
the recorded species errors stayed within family. This supports the diagnosis that some species
names bin a continuous solid-solution region. However, the continuous garnet coordinate was
inferred rather than independently measured, RRUFF is curated, and no separate downstream $Y$
demonstrated decision value discarded by the species label. RRUFF motivates the audit and the
known-mixture intervention; it is not a completed TRCL estimate.

### Severson: structural loss, within-corpus gain, failed batch transfer

The full adapted record contains 135 cells across three collection batches, including seven
censored events. A recipe-only input is forced to tie same-policy replicates. On 160 resolvable
within-policy pairs, the early trajectory representation reached 0.756 under the within-corpus
leave-one-policy-out ridge analysis, while the recipe-only arm was fixed at 0.500; thirteen pairs
were resolvable only because censored records were retained. These establish representation
collisions and paper-shape support loss.

The learned margin is not transferable evidence. On the only pair-rich held-out-batch cell, batch 3
with 136 pairs, ridge ranking fell from 0.779 with other batch-3 policies available during training
to 0.522 with batch 3 excluded, cluster CI [0.312, 0.697]. The dataset has only three batches and
highly concentrated pair structure. The correct audit reading is therefore: structural blindness
is demonstrated; within-corpus usable information was found; a provenance-stressed transferable
increment was not. See
[severson_representation_ab.md](../controlled-collection/severson_representation_ab.md) and
[severson_heldout_batch_ranking.md](../controlled-collection/severson_heldout_batch_ranking.md).

These three cases are not contradictory. A valid audit must be capable of returning redundancy,
task-relevant loss, complementarity, support loss, and shortcut sensitivity.

## Compression-audit output contract

Every completed audit must produce a human-readable report and a machine-readable manifest with the
same frozen content. At minimum they contain:

### 1. Identity and preregistration

- audit ID, protocol version, dataset/event-schema version, code commit, and artifact hashes;
- preregistration commit and proof that it preceded outcome access or the run, or a visible ordering
  breach;
- named primary task, secondary tasks, and status of each as confirmatory or exploratory.

### 2. Estimand and availability

- $Y$, optional action/utility, $\tau$, $C$, $E$, loss $\ell$, model suite $\mathcal V$,
  target population, and unit of independence;
- all four arm definitions with exact fields;
- the input-provenance DAG, node timestamps, side inputs, availability rules, and no-future-
  information checks;
- upstream retention/recoverability classification for every audited edge.

### 3. Denominators and support

- attempted events, observed events, common-support events, and counts by exclusion reason;
- event coverage and support loss, overall and by environment/outcome status;
- the rule generating all decision instances, decision coverage, utility-weighted coverage where
  relevant, and lost-instance reasons;
- collision counts/rates and any forced loss floor.

### 4. Evaluation and diagnostics

- split generator, seeds, train/test counts, group constraints, nested tuning/calibration, and
  leakage assertions;
- per-environment unit counts, cluster concentration/effective sample size, $E\leftrightarrow Y$
  diagnostics, representation-to-$E$ recoverability, support overlap, and shift diagnosis;
- baselines appropriate to the modality: context-only, mean/majority, clock, interpolation,
  extrapolation, provenance-only, and scrambled or structure-preserving nulls as applicable.

### 5. Results

- out-of-fold risks for $C$, $C+L$, $C+X$, and $C+L+X$, by fold and environment before
  aggregation;
- TRCL and $\Delta_{L\mid X}$ with paired confidence intervals in native task units;
- random/grouped and held-out-environment contrasts;
- predeclared risk-adequacy and support-retention bounds, sensitivity analyses, and bits per event only when
  calibration supports them;
- all negative, null, failed-transfer, and underpowered cells; no clipping or selective pooling.

### 6. Verdict and mechanism boundary

- exactly one allowed verdict per predeclared claim, written with its task, $\mathcal V$, $n$,
  environments, cutoff, bounds, and support qualifications;
- separate statements for common-support risk, event support, decision support, collision, and
  recoverability;
- mechanism hypotheses labeled as supported, falsified, unresolved, or exploratory, never inferred
  from feature importance alone;
- limitations and the next experiment that could change the verdict.

The audit is incomplete if it reports an accuracy gap without its denominator, calls a
nonsignificant result faithful, pools provenance folds in a way that changes the estimand, or omits
events the compressed representation could not express.

## Protocol-level thesis

> Experimental labels are candidate task-specific summaries, not ground truth. For each declared
> task, cutoff, environment, learner family, and data scale, we measure both the incremental usable
> value and the representational coverage of the event record beyond the label. Where the pipeline
> is genuinely nested, we localize the earliest compression step whose risk, support, or collision
> exceeds predeclared bounds; we then report separately whether the upstream evidence remains
> recoverable.

This formulation is deliberately capable of concluding that a conventional report is adequate.
The contribution is not a prior that raw always wins. It is an instrument for learning which
compression is harmless for which decisions, which signal survives collection shift, and which
information was discarded before anyone knew to ask for it.
