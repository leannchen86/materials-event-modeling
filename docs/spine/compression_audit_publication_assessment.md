# Publication Assessment — Task-Relevant Compression Audit

Date: 2026-07-10. Status: **paper-worthy protocol hypothesis; prospective validation not yet
complete**. Companion formalism:
[task_relevant_compression_audit.md](task_relevant_compression_audit.md). Prospective test:
[pilot_design_prereg.md](../controlled-collection/pilot_design_prereg.md).

## Verdict

This is not a new information-theory result. Conditional decision risk, task-specific
sufficiency, information bottlenecks, missing-data selection, provenance, and environment-held-out
evaluation all have mature literatures. A paper that presents the TRCL equation as the novelty will
be rejected correctly.

The defensible contribution is an experimental-science **audit protocol** that puts five pieces
together at the raw-to-report boundary:

1. conditional usable risk on events retained by both representations;
2. attempted-event and decision support lost when reports omit failures, censoring, or ambiguity;
3. provenance-held-out evaluation before residual signal is called transferable;
4. stage localization only along a declared input-provenance graph, with human side information
   made explicit; and
5. recoverability of the upstream record, turning a model result into a storage and governance
   decision.

The strongest credible positioning is:

> We introduce and prospectively validate a support-aware, provenance-stressed audit of
> task-specific information loss across the raw-to-report pipeline in experimental materials
> science.

`First` should appear only as a qualified `to our knowledge` claim after a formal literature
review. The current search found no primary paper combining all five elements, but absence from a
search is not proof of priority.

## Closest prior work and the remaining gap

| Area | What is established | Consequence for this paper |
| --- | --- | --- |
| comparison of information sources | Blackwell orders experiments by attainable decision risk ([Blackwell, 1953](https://doi.org/10.1214/aoms/1177729032)) | do not claim decision-relative informativeness as new |
| task-relevant compression | the information bottleneck formalizes short codes that retain information about a target ([Tishby, Pereira & Bialek](https://arxiv.org/abs/physics/0004057)) | the reporting channel, not rate--distortion itself, is the object |
| model-usable conditional information | predictive V-information incorporates learner constraints ([Xu et al.](https://arxiv.org/abs/2002.10689)); conditional probing measures representation value beyond a baseline ([Hewitt et al.](https://aclanthology.org/2021.emnlp-main.122/)) | TRCL is an applied conditional-risk instrument, not a new information measure |
| scientific compression audits | optical-microscopy work measures downstream prediction distortion relative to raw sensor uncertainty ([Pomarico et al.](https://www.nature.com/articles/s41598-022-07445-4)); CryoEM work derives stage-specific precision and compression requirements ([Fluty & Ludtke](https://doi.org/10.1016/j.jsb.2022.107875)) | never claim the first task-aware audit of scientific compression; distinguish human reporting, deleted attempts, and provenance transfer |
| missingness and selection | complete-case inference under nonrandom omission is a mature problem ([Rubin, 1976](https://doi.org/10.1093/biomet/63.3.581); [Heckman, 1979](https://doi.org/10.2307/1912352)) | support retention is a required denominator, not a new missing-data theory |
| materials lineage | the Materials Provenance Store retains experimental histories and raw outputs for purpose-specific validation ([Statt et al.](https://www.nature.com/articles/s41597-023-02107-0)); ESAMP models event-sourced material state and analyses ([Statt et al.](https://doi.org/10.1039/D3DD00054K)) | claim quantitative diagnosis on top of provenance infrastructure, not invention of provenance graphs |
| environment robustness | domain-generalization and group-robust evaluation are established; materials [LOCO-CV](https://arxiv.org/abs/2206.08841) already warns against random-CV optimism | the contribution is making operator/session/instrument/lot stress a requirement of a reporting audit |

The closest empirical challenge is Pomarico et al.: they already compare processed and raw
scientific data through downstream prediction distortion and explicitly describe extension to
processing pipelines. The distinction must be visible in the abstract and experiments:

> Numerical codecs and instrument-processing stages alter values for records that remain present.
> Scientific reporting can additionally merge distinct events, omit entire failed/censored
> attempts, incorporate undocumented human evidence, and preserve lab-specific signal that fails
> to transfer.

## What the paper must demonstrate

### Study 1 — causal calibration on known mixtures

Run the two-phase XRD mixture intervention as the positive control:

- independent preparations across the full fraction range;
- denser sampling near anticipated `pure` / `trace impurity` / `two-phase` boundaries;
- blinded human reports with confidence and `unclassifiable` retained;
- frozen stages from raw counts through calibrated pattern, scalar report, human category, and
  paper-shaped record;
- continuous fraction estimation plus at least one declared threshold decision;
- counterbalanced preparation and measurement sessions, with the instrument round-robin first.

Nominal weighed fraction and realized XRD fraction are not silently treated as identical. Packing,
grinding, orientation, and preparation variability need an independent uncertainty statement or a
reference quantification method.

### Study 2 — prospective process test

Use the CaCO3 pilot to compare `C`, `C+L60`, `C+S60`, `C+X60`, and `C+L60+X60` for predicting
24-hour vaterite fraction and failure. The pre-freeze amendment defines the arms, information
cutoff, support denominators, and verdict rules. Four sessions test robustness across those four
sessions; they do not establish population-level lab invariance.

### Study 3 — negative and shortcut controls

A credible audit must return more than `raw wins`. Include deliberately different regimes:

- an adequate compact summary for a narrow task;
- a deliberately lossy summary;
- a raw signal with recoverable session/instrument identity but no transferable target increment;
- a nonnested human label containing explicit side information;
- failures or `unclassifiable` cases that create support loss.

Oleogel, RRUFF, and Severson are retrospective instrument checks, not three completed prospective
TRCL studies: oleogel supplies redundancy/baseline-solvability; RRUFF motivates continuum
calibration but lacks an independent downstream target; Severson supplies collision, support-loss,
and failed-transfer cases.

### Study 4 — independent replication

An independent laboratory/site or a materially independent collection pipeline is needed before
an industry-wide claim. A second instrument or modality at the same site adds instrument or
modality breadth, but does not establish industry transfer by itself. A single-site prospective
pilot can support a methods proof; it cannot show generality across the industry.

## Required software and released artifacts

The paper should ship an audit package rather than only figures:

- representation manifests with exact fields, parents, state/assay/construction timestamps, and
  availability rules;
- attempted-event and decision denominators;
- strictly out-of-fold predictions and common-support masks;
- task-native paired risk gaps with clustered uncertainty;
- environment-specific results and provenance-recoverability probes;
- bounded-adequacy risk tolerances committed before outcome access;
- upstream retention/recoverability classifications; and
- storage, acquisition, and annotation cost metadata where available.

The initial reusable evaluator lives in
[`src/materials_event_modeling/eval/compression_audit.py`](../../src/materials_event_modeling/eval/compression_audit.py).
It audits out-of-fold prediction bundles rather than silently choosing models, which keeps the
learner family and cross-fitting design visible in each task's preregistration.

## Paper shape

Working title:

> **When Does an Experimental Report Throw Away Too Much? A Support-Aware,
> Provenance-Stressed Compression Audit for Materials Experiments**

Proposed figures:

1. input-provenance graph from raw event to conventional report, with analytic versus retention
   compression;
2. audit decomposition: common-support risk, event/decision support, collision, and recoverability;
3. known-mixture positive control across reporting stages and detection thresholds;
4. CaCO3 prospective task results by held-out session;
5. negative/shortcut controls, including the Severson random-versus-batch reversal;
6. task risk versus collection/storage cost, annotated by recoverability.

The paper's intellectual claim is not `raw is better`. It is that reporting adequacy is measurable,
task-specific, and jointly constrained by what a report predicts, what it omits, where its signal
transfers, and whether discarded evidence still exists.

## Venue and ambition calibration

- **Digital Discovery**: strongest initial fit for materials data, provenance, and ML methodology.
- **Machine Learning: Science and Technology**: good fit for protocol plus benchmark/software.
- **npj Computational Materials**: plausible with strong controlled-materials results and
  independent validation.
- **Patterns**: plausible if the released audit spans several experimental domains.
- **Metrologia**: attractive if round-robin uncertainty and adequacy/non-inferiority become the
  center.
- **Scientific Data**: appropriate if the born-conformant dataset and benchmark are the main
  product.

A theory-first ML venue would require more than this protocol: for example, an environment-indexed
reporting channel with an observability indicator, a decomposition of retained-event risk and
omitted-event decision cost, conditions for valid adjacent-stage localization, and finite-sample
inference guarantees. Without a new estimator or theorem, do not pitch this as general ML theory.

## Go / no-go gates

Proceed toward a methods paper if:

1. the audit correctly distinguishes positive, adequate, support-loss, and shortcut controls;
2. the known-mixture result survives held-out preparation/measurement provenance;
3. the prospective pilot produces an interpretable verdict even if the early trace loses;
4. all attempted events and `unclassifiable` cases remain in the denominator; and
5. the software and manifests reproduce every reported contrast.

Downgrade to a dataset/protocol note if the only positive result is structural deletion by
construction, every learned increment is batch-local, or the adequacy analysis is too
underpowered to distinguish adequacy from absence of evidence.
