# Downstream-Failure Compression Program

Status: scope decision and staged research roadmap, 2026-07-11. This document extends the
[task-relevant compression audit](task_relevant_compression_audit.md) from an event-level
representation comparison to delayed, consequential materials outcomes. The current
[CaCO3 pilot](../controlled-collection/pilot_design_prereg.md) remains the audit-calibration
study; it is not retrofitted into an industrial qualification claim.

## Scope decision

The project will no longer treat `raw trace versus label` as the destination. The destination is:

> Which early raw or intermediate signals predict an expensive downstream failure, which
> conventional transformation first destroys their transferable decision value, and what is the
> least costly representation that safely preserves that value?

The first consequential endpoint class is **independent-preparation reproducibility / final-spec
conformance**. It is the bridge from the current event pilot to industrially meaningful outcomes:
it has a real early decision (`continue`, `retest`, `rework`, `route`, or `stop`), shorter feedback
than lifetime qualification, and a natural transfer test across sessions, lots, instruments, and
sites.

Degradation or later functional performance is the preferred flagship after the audit and
reproducibility bridge pass. Pilot-scale yield and formal qualification remain later stages. The
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
3. localize the first edge that violates predeclared risk, support, or collision bounds;
4. require the residual signal to survive held-environment and independent-site evaluation;
5. distinguish an unavailable event from a lossy within-event summary;
6. report whether the upstream artifact remains recoverable; and
7. identify the cheapest adequate intermediate rather than advocating universal raw retention.

The strongest eventual claim is therefore not `raw wins`:

> For outcome $Y$ and cutoff $\tau_s$, the conventional report was not task-adequate under
> held-environment evaluation. Loss localized to transformation $T$. Intermediate representation
> $Z$ retained the native trace's transferable decision value at lower total cost and improved a
> predeclared early decision.

## Program ladder

| phase | primary purpose | endpoint | evidence ceiling |
| --- | --- | --- | --- |
| 0. audit calibration | show the instrument returns the correct verdict on known cases | known-mixture fraction and threshold decisions | validated audit mechanics |
| 1. prospective methods study | test the audit on a real process without industrial overclaim | CaCO3 24-hour phase fraction and failure from state sampled by 60 min | single-site methods proof |
| 2. reproducibility bridge | test whether an early representation forecasts an independent execution falling outside a frozen specification | continuous replicate deviation primary; within-spec status secondary | transferable within-lab or cross-site QC evidence, depending on environments |
| 3. consequential flagship | attach the audit to a slow or expensive functional endpoint | degradation, capacity retention, catalyst lifetime, strength, corrosion, or another partner-native property | high-impact downstream-value claim |
| 4. decision trial | show that retained information changes actions and outcomes | cost, delay, scrap, false accept/reject, yield, or regret | operational/industry claim |
| 5. scale and qualification | test production and certification relevance | pilot-lot yield, field durability, or qualification outcome | domain-specific deployment evidence |

Each phase has a separate preregistration and dataset. A later phase may use an earlier phase for
power planning, but not recycle its outcomes as confirmatory evidence.

## Recommended first two studies

### Study A — reproducibility / final-spec bridge

The operational question is:

> Given evidence available from execution $i$ by cutoff $\tau_s$, should a user trust the process,
> repeat it, rework it, route it to extra characterization, or stop before paying for a later
> independent execution or assay?

The source representation comes only from execution $i$. The target is constructed from a later,
independently prepared execution $j$ or a future batch, never from a group statistic that includes
the held-out target row. Two targets should be frozen:

1. a continuous deviation in the final property, such as $|q_i-q_j|$, with assay uncertainty
   propagated; and
2. a secondary binary decision, such as whether execution $j$ falls inside a practitioner-approved
   tolerance window.

`Repeatability`, `intermediate precision`, and `reproducibility` are not synonyms:

- same apparatus/operator over a short interval tests repeatability;
- changed day, operator, lot, or instrument within one laboratory tests intermediate precision;
- independent sites test reproducibility.

The claim must use the strongest term actually supported by the collection environments.

The current CaCO3 pilot can estimate assay variance and exercise pair construction, but its three
replicates per condition and four sessions are not the confirmatory reproducibility study. A
follow-up should use fewer fixed conditions with more independent executions spread across at least
the planned eight-session extension, then use an external site for a reproducibility claim. Exact
counts follow cluster-aware simulation, not a universal minimum.

### Study B — degradation / functional-performance flagship

Preferred first domain: a partner workflow where early process or characterization traces are
already compressed into a conventional QC packet and a slow, expensive outcome is routinely
measured. Battery formation-to-degradation is the leading candidate because the repo already has a
Severson baseline and a documented held-batch failure, but access and lineage outrank fashion.

A suitable workflow has:

- native early current/voltage/temperature/time or process traces;
- an actual conventional feature/report/grade used in practice;
- a continuous delayed outcome such as capacity retention, cumulative energy throughput,
  degradation rate, corrosion loss, strength, or catalyst activity retention;
- a real action before that outcome arrives;
- multiple independent material or manufacturing batches and, eventually, a second site; and
- retained failed, censored, interrupted, and retested units.

For batteries, a continuous outcome at a frozen cycle or time is preferable as the primary target.
Time-to-threshold is a secondary censored endpoint, not a scalar obtained by deleting surviving
cells. A planning range such as 150--300 cells across 8--12 batches may be useful for partner
discussions, but it is not a power calculation. Cells, cycles, or spectra do not substitute for
independent material and manufacturing batches.

If no battery partner can supply the complete ladder, use a less fashionable system that can. Ten
well-crossed material batches with native traces and a credible outcome are stronger evidence than
hundreds of cells from three confounded batches.

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

The first partner deliverable is one **golden event** that traverses the entire graph:

- planned context and actual process record;
- native trace and instrument metadata;
- each intermediate representation and its construction version;
- the conventional report and final label/grade;
- the downstream outcome and assay uncertainty;
- all interventions, retries, failures, and exclusions; and
- acquisition, storage, processing, annotation, and turnaround costs.

No model development starts until this one event can be reconstructed without an ambiguous join.

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

The endpoint horizon and input cutoff are frozen independently. The cutoff is the earliest time at
which the declared action could save meaningful cost or delay, not the time that maximizes
retrospective accuracy.

## Evaluation design

All representation arms use the same strictly out-of-fold events and the same target definition.
The split hierarchy is:

1. random-unit split, diagnostic only;
2. held session, operator, instrument, and lot;
3. held material or manufacturing batch;
4. held process condition or chemistry when included in the claim; and
5. frozen independent site.

No scans, cycles, aliquots, or devices descended from the same independent material unit may cross
train/test folds when the claim concerns material transfer. Feature learning, scaling, imputation,
tuning, and calibration occur inside the training partition.

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

## Decision gates

| gate | required evidence | stop or downgrade condition |
| --- | --- | --- |
| G0: identifiable | joined raw/intermediate/report/outcome ladder, physical-unit lineage, retained failures | orphaned outcomes, ambiguous units, or no genuine report |
| G1: valid target | assay precision, target variance, eligibility, censoring, and action utility are frozen | measurement uncertainty is comparable to the useful effect or the action is fictitious |
| G2: calibrated audit | known-loss and known-adequacy controls receive the expected verdicts | the audit cannot distinguish loss from adequacy |
| G3: local task loss | richer representation clears $\delta_R$ or compact stage violates support/collision bounds | conventional report is demonstrably adequate or the estimate is inconclusive |
| G4: transfer | gain survives the relevant held batch/environment with no material harm cell | random-split gain disappears, reverses, or is explained by provenance |
| G5: economical representation | value of the action exceeds acquisition, retention, computation, and latency cost | only an uneconomic native artifact works |
| G6: external replication | frozen result survives an independent site or materially independent pipeline | single-site result only |
| G7: decision value | prospective richer-feedback policy improves utility under an equal budget | prediction gain does not change decisions or outcomes |

Adequacy requires an upper confidence bound that excludes improvements larger than the
predeclared meaningful margin. `Not significant` remains inconclusive.

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

## Immediate execution order

1. Finish and freeze the current known-mixture and CaCO3 audit without changing its primary claim.
2. Run a nonconfirmatory Severson `C / conventional early summary / full early trace -> future
   degradation` dry run to exercise the complete evaluator and expose software gaps. Treat any
   synthetic conventional packet as an engineering control until a practitioner validates it.
3. Use the [downstream endpoint decision card](../controlled-collection/downstream_endpoint_decision_card.md)
   in every partner conversation; require one golden event before promising a study.
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
  censoring.
- Do not count specimens, scans, cycles, or devices as independent material batches.
- Do not claim industry value from early-XRD to later-XRD continuity alone.
- Do not expand the evaluator API before one real physical-unit and outcome graph is known.

The near-term research asset is not a larger model. It is one matched, versioned chain from native
early evidence through the ordinary report to an independently measured delayed outcome across
enough real environments to test transfer.
