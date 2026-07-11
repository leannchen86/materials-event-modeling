# Downstream-Failure Compression Program

Status: scope decision and staged research roadmap, 2026-07-11. This document extends the
[task-relevant compression audit](task_relevant_compression_audit.md) from an event-level
representation comparison to delayed, consequential materials outcomes. The current
[CaCO3 pilot](../controlled-collection/pilot_design_prereg.md) remains the audit-calibration
study; it is not retrofitted into an industrial qualification claim.

## Scope decision

The project will no longer treat `raw trace versus label` as the destination. The destination is:

> Do early raw or intermediate signals predict an expensive downstream failure; if so, at which
> earliest audited edge in the declared provenance graph does a conventional representation fail
> to preserve transferable decision value, and what is the least costly adequate representation?

The first consequential endpoint class is **early final-spec conformance for independently
prepared executions**. It is the bridge from the current event pilot to industrially meaningful
outcomes: it has a real early decision (`continue`, `retest`, `rework`, `route`, or `stop`), shorter
feedback than lifetime qualification, and natural measurement-precision or process-robustness tests
across sessions, operators, instruments, and lots. `Reproducibility` is reserved for an
independent-site study.

Degradation or later functional performance is the preferred flagship after the audit and
conformance bridge pass. Pilot-scale yield and formal qualification remain later stages. The
project will not bundle all of these into one small study.

The current CaCO3 program has a narrower role:

- known mixtures and instrument round-robins calibrate whether the audit localizes known loss;
- the 24-hour phase/failure task tests a real process endpoint under a frozen early-state cutoff;
- four sessions provide a fixed-session stress test, not population-level reproducibility;
- results may justify a methods paper, but not an 8--9/10 industry-impact claim by themselves.

## Why this is a distinct contribution

The broad premise is not new. Recent work explicitly describes an experimental-materials
`information loss cascade` from physical reality through characterization, reporting, and training
features ([Iwata, 2026](https://doi.org/10.1002/csc3.70016)), while another recent viewpoint argues
for raw instrument files as a verification layer
([Reeves-McLaren, 2026](https://doi.org/10.1021/acsomega.6c04971)). Early traces predicting later
materials performance are also established in domains such as batteries.

The defensible contribution is operational and prospective:

1. name one downstream decision and its native utility before outcome access;
2. retain the actual raw-to-report transformation graph and attempted-event denominator;
3. localize the earliest audited failing edge only along a verified nested transformation chain;
4. require the residual signal to survive held-environment and independent-site evaluation;
5. distinguish an unavailable event from a lossy within-event summary;
6. report whether the upstream artifact remains recoverable; and
7. identify the cheapest adequate intermediate rather than advocating universal raw retention.

The strongest eventual claim is therefore not `raw wins`:

> For outcome $Y$ and cutoff $\tau_s$, the conventional report was not task-adequate under
> held-environment evaluation. Along the verified transformation chain, the earliest audited
> failure occurred at edge $T$. Intermediate representation $Z$ retained the native trace's
> transferable value at lower total cost and improved estimated utility under a frozen decision
> rule.

Actual improvement in actions, yield, scrap, or other outcomes is claimed only after the
prospective decision trial in phase 4. For nonnested human/report stages, the result is conditional
value, complementarity, or a bracket of possible sources—not localization to one causal edge.

## Program ladder

| phase | primary purpose | endpoint | evidence ceiling |
| --- | --- | --- | --- |
| 0. audit calibration | show the instrument returns the correct verdict on known cases | known-mixture fraction and threshold decisions | validated audit mechanics |
| 1. prospective methods study | test the audit on a real process without industrial overclaim | CaCO3 24-hour phase fraction and failure from state sampled by 60 min | single-site methods proof |
| 2. independent-preparation conformance bridge | test whether an early representation forecasts the delayed final property of the same independently prepared execution | continuous final property or distance from an external specification primary; within-spec status secondary | early-QC evidence under declared intermediate-precision environments |
| 3. consequential flagship | attach the audit to a slow or expensive functional endpoint | failure-aware degradation/lifetime, catalyst lifetime, strength, corrosion, or another partner-native property | high-impact downstream-value claim |
| 4. decision trial | show that retained information changes actions and outcomes | cost, delay, scrap, false accept/reject, yield, or regret | operational/industry claim |
| 5. scale and qualification | test production and certification relevance | pilot-lot yield, field durability, or qualification outcome | domain-specific deployment evidence |

Each phase has a separate preregistration and dataset. A later phase may use an earlier phase for
power planning, but not recycle its outcomes as confirmatory evidence.

## Recommended first two studies

### Study A — independent-preparation final-spec bridge

Two estimands must remain separate.

#### A1. Run-local early quality control

The first bridge asks:

> Given evidence available from independently prepared execution $i$ by cutoff $\tau_s$, should a
> user continue, retest, rework, route, or stop before paying for the delayed final assay of that
> same execution?

The primary target is the continuous final property $q_i$ or its signed/absolute distance from a
specification fixed independently of this sample. A secondary target is whether $q_i$ lies inside
that pre-existing specification. This is an early-QC/conformance task; repeating it across changed
sessions, operators, instruments, or material lots tests declared robustness axes, not cross-site
reproducibility.

#### A2. Future-process qualification

A different question is whether a process or recipe is reliable for future independent
executions. Its input is a frozen commissioning set $D_g$ for process $g$, and its target is a
predictive distribution for a future $q_j$ or $P(q_j\in W)$ for an externally defined window $W$.
It is not estimated by treating every overlapping $|q_i-q_j|$ pair as independent.

Anchor/confirmation roles, the future execution, and whole-process train/test groups must be
assigned before outcome access. If pairwise repeatability appears as a descriptive diagnostic,
freeze its pair ledger, prevent any execution from entering both train and test through another
pair, and resample the shared process/preparation cluster.

`Repeatability`, `intermediate precision`, and `reproducibility` are not synonyms:

- same apparatus/operator over a short interval tests repeatability;
- changed day, operator, or instrument within one laboratory tests measurement-system intermediate
  precision;
- changed material lot or process condition may instead test process robustness and must be named
  as such; and
- independent sites test reproducibility.

The claim must use the strongest term actually supported by the collection environments.

The current CaCO3 pilot can estimate assay variance and exercise A1. Its three replicates per
condition and four sessions are not a confirmatory A2 process-qualification or reproducibility
study. A follow-up may use fewer fixed conditions with more independent executions and a prospectively
held future set, but exact process groups, sessions, and counts follow cluster-aware simulation. An
external site is required before using `reproducibility`.

### Study B — degradation / functional-performance flagship

Preferred first domain: a partner workflow where early process or characterization traces are
already compressed into a conventional QC packet and a slow, expensive outcome is routinely
measured. Battery formation-to-degradation is the leading candidate because the repo already has a
Severson baseline and a documented held-batch failure, but access and lineage outrank fashion.

A suitable workflow has:

- native early current/voltage/temperature/time or process traces;
- an actual conventional feature/report/grade used in practice;
- a failure-aware delayed outcome such as cumulative energy throughput, survival/degradation,
  corrosion loss, strength, or catalyst activity retention;
- a real action before that outcome arrives;
- multiple independent material or manufacturing batches and, eventually, a second site; and
- retained failed, censored, interrupted, and retested units.

For batteries, the endpoint must remain defined for early failures. Capacity retention at a frozen
cycle selects survivors when cells fail before that cycle. Prefer a failure-aware continuous
quantity such as cumulative delivered energy under a frozen rule, a survival endpoint with explicit
censoring, or co-primary continuous and survival estimands. Do not encode an early failure as zero
without a physical or utility justification. Cells, cycles, or spectra do not substitute for
independent material and manufacturing batches; all counts follow pilot-informed hierarchical
simulation rather than an unsupported planning anchor.

If no battery partner can supply the complete ladder, use a less fashionable system that can.
Several well-crossed material batches with native traces and a credible outcome are stronger
evidence than many descendants of a few confounded batches.

## Required unit and lineage graph

Delayed outcomes often belong to a different physical unit than the synthesis event. Before code
or collection, freeze the real graph:

```text
planned process
    -> execution event
        -> material batch
            -> aliquot / specimen
                -> device or pilot lot
                    -> delayed assay / qualification decision
```

Every edge needs immutable identifiers, timestamps, split/merge/consumption semantics, source
hashes, and environment metadata. `Event.outcome.status` remains the execution result. A delayed
performance or qualification endpoint is a separate versioned outcome product joined to its
physical subject; it is not inserted into a free-form event summary and mistaken for the same
unit.

The first partner deliverable is a small **golden bundle** that traverses the entire graph:

- at least one ordinary event with planned context and actual process record;
- native trace, instrument metadata, and every intermediate transformation/version;
- the conventional report, final grade, downstream outcome, and assay uncertainty;
- a failure, censor, abort, retry, or rework example where one exists;
- source-ledger aggregate counts needed to evaluate denominator completeness; and
- acquisition, storage, processing, annotation, and turnaround costs.

All golden-bundle IDs and descendants are permanently nonconfirmatory and listed in the later
preregistration, or their outcomes remain firewalled from the analysis team while a data engineer
verifies the joins. No model development starts until the bundle can be reconstructed without an
ambiguous join. A bundle validates lineage mechanics; it does not establish denominator
completeness or estimate an effect.

## Representation ladder

The ladder must be derived from the partner's actual workflow, not invented to make raw data win.
A generic candidate is:

```text
C: planned formulation, process setpoints, and legitimately available lot context
-> native instrument and process traces
-> calibrated / cleaned full traces
-> engineered features and fit residuals
-> practitioner conventional report
-> categorical quality grade or pass/fail
-> lot-level or publication-shaped record
```

Required arms include `C`, every genuine intermediate, the actual conventional report, the native
trace, and `trace + report` for complementarity. A human report with side information absent from
the trace is a nonnested branch and must be analyzed as such.

For every representation, record four clocks separately: material-state time, acquisition time,
construction time, and operational availability time. The endpoint horizon, input cutoff, and
decision deadline are frozen independently. The cutoff is the earliest time at which the declared
action could save meaningful cost or delay, not the time that maximizes retrospective accuracy.
Evidence processed after the deadline may support a sampled-state scientific claim but is not an
eligible operational input.

A compact online representation and archival retention answer different questions. The online
controller may safely use a compact report while immutable native evidence remains worth retaining
for future tasks, verification, or incident analysis.

## Evaluation design

All representation arms use the same strictly out-of-fold events and the same target definition.
Before outcome access, declare one primary transfer split. Other splits are named secondary
estimands rather than a hierarchy from which the best result can be selected:

1. random-unit split, diagnostic only;
2. held session, operator, instrument, and lot;
3. held material or manufacturing batch;
4. held process condition or chemistry when included in the claim; and
5. frozen independent site.

No scans, cycles, aliquots, or devices descended from the same independent material unit may cross
train/test folds when the claim concerns material transfer. Feature learning, scaling, imputation,
tuning, and calibration occur inside the training partition. Conditions and chemistries must
overlap across batches when `batch transfer` is the claim; otherwise batch and formulation shift
cannot be separated.

External evaluation distinguishes:

1. zero-shot transport of a frozen model to an untouched site;
2. transport after a predeclared site-calibration set; and
3. protocol replication with site-specific retraining.

Only the first is zero-shot model transfer. The third can validate the audit protocol without
showing that the original predictor transferred. At every site, verify whether the report schema
and transformation graph are actually the same; otherwise the study audits a new pipeline.

Minimum baselines are:

- context/recipe only;
- train mean or prevalence;
- the current SOP or expert rule;
- actual conventional report and strongest conventional engineered features;
- a simple trend/extrapolation baseline;
- provenance-only inputs;
- native trace alone and trace plus report;
- nuisance-matched or structure-preserving nulls; and
- an outcome-adjacent late assay as a ceiling, never as an eligible early input.

The audit reports separately:

- target eligibility and follow-up/censoring support;
- representation availability support;
- common-support risk and conditional increments;
- decision support and representation collisions;
- environment recoverability and held-environment transfer;
- outcome-assay uncertainty; and
- acquisition, storage, latency, annotation, and decision costs.

Selective downstream follow-up is acceptable only when all eligible units are assayed, a
predeclared probability sample has known inclusion probabilities, or a defensible selection model
and sensitivity bounds are part of the estimand. Merely knowing which outcomes were not observed
does not recover them.

## Decision gates

| gate | required evidence | stop or downgrade condition |
| --- | --- | --- |
| G0: identifiable | joined raw/intermediate/report/outcome ladder, physical-unit lineage, actual report, retained attempt ledger, and a nonconfirmatory golden bundle | orphaned outcomes, ambiguous units, or invented report |
| G1: valid target | assay precision, target variance, eligibility, censoring, follow-up design, and action utility are frozen | measurement uncertainty is comparable to the useful effect, follow-up is undefended, or the action is fictitious |
| G2: calibrated audit | a known-loss control and a known-adequacy control defined independently of fitted results receive the expected verdicts | the audit cannot distinguish loss from adequacy |
| G3: local task loss | common-support risk, structural support/collision, and downstream utility are reported separately | apparent gain is only deletion by construction, or uncertainty crosses the relevant bound |
| G4: transfer | gain survives the predeclared primary held environment and no held environment crosses its harm bound | random-split gain disappears, reverses, or is explained by provenance |
| G5: economical representation | estimated decision benefit exceeds acquisition, retention, computation, and latency cost by $\delta_U$ | only an uneconomic native artifact works |
| G6: external replication | frozen zero-shot/site-calibrated transport or protocol replication at an independent site, with the mode named | single-site result only |
| G7: decision value | shadow-mode safety followed by a prospective randomized/concurrent policy trial | prediction gain does not improve the declared causal policy estimand |

Orient the risk gap as compact-arm risk minus richer-arm risk. A useful richer-representation result
requires the appropriate simultaneous lower confidence bound to exceed the frozen task-risk benefit
$\delta_R$. Compact-stage adequacy requires the upper bound to exclude improvements larger than
$\delta_R$ while support/collision bounds pass. Everything between is inconclusive. The utility
threshold $\delta_U$ is separate from predictive risk. `Not significant` establishes neither loss
nor adequacy.

## Closed-loop extension

For autonomous laboratories, an event-level predictive gain is necessary but not sufficient. The
compressed state changes which experiment is selected next:

```text
X_t -> L_t -> action A_{t+1} -> support of future observations X_{t+1}.
```

If two raw states map to one report but have different optimal next actions, the report creates an
action collision. It can remove the counterevidence that would reveal its own error. A later-stage
study must therefore compare budget-matched policies driven by a conventional report, an
intermediate representation, and richer evidence. The endpoint is policy value or regret under an
independent assay, not experiments per day or one-step prediction accuracy.

Acting on a policy can itself delete outcomes: a stopped, scrapped, or rerouted unit may never
receive the reference assay. Begin in shadow mode, then use randomized or concurrent policy
assignment with logged probabilities and a declared causal estimand. Continue reference follow-up
on all units or a randomized audit subset, and model interference/adaptive collection where it is
plausible. Equal budget alone does not identify policy value.

## Immediate execution order

1. Finish and freeze the current known-mixture and CaCO3 audit without changing its primary claim.
2. **Completed 2026-07-11:** the nonconfirmatory Severson
   [`C / S100 / X100 -> cycle life` dry run](../controlled-collection/severson_downstream_compression_results.md)
   now exercises the complete evaluator. The leakage-corrected primary result finds no stable
   X100-over-S100 advantage, exposes a cross-batch target-provenance reversal, and remains an
   engineering control rather than a practitioner-report result.
3. Use the [downstream endpoint decision card](../controlled-collection/downstream_endpoint_decision_card.md)
   in every partner conversation; require one nonconfirmatory golden bundle before promising a
   study.
4. Select one real endpoint, cutoff, action, physical-unit graph, and transfer population.
5. Estimate assay, batch, missingness, and censoring components from nonconfirmatory pilot units.
6. Simulate the full hierarchical design for both material-loss and bounded-adequacy power.
7. Preregister the Phase 2 ladder, models, environment splits, costs, and go/no-go gates.
8. Collect at one site, freeze the independent-site test, and only then run a prospective decision
   trial.

## Explicit non-goals

- Do not add five downstream targets to the 48-event CaCO3 pilot.
- Do not call within-lab session variation cross-lab reproducibility.
- Do not define a conventional report after inspecting which features make the trace win.
- Do not let only promising units receive the expensive follow-up without auditing informative
  censoring and using a defensible follow-up design.
- Do not count specimens, scans, cycles, or devices as independent material batches.
- Do not claim industry value from early-XRD to later-XRD continuity alone.
- Do not expand the evaluator API before one real physical-unit and outcome graph is known.

The near-term research asset is not a larger model. It is one matched, versioned chain from native
early evidence through the ordinary report to an independently measured delayed outcome across
enough real environments to test transfer.
