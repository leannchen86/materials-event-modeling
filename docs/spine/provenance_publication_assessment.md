# Track A Publication Assessment

As of 2026-05-29.

## Bottom Line

Track A has produced one result that is genuinely interesting, but the paperable claim is
not "we built a better XRD model."

That space is already active and moving quickly: automated phase identification, phase
mapping, self-supervised diffraction representations, large simulated-diffraction models,
and LLM-guided experimental planning all exist or are emerging. A plain model-performance
paper on opXRD or HTEM would probably become leaderboard drift.

The stronger contribution is this:

```text
Current public XRD/materials datasets make it easy for raw-measurement models to learn
source, instrument, preprocessing, library, and collection-style structure. Therefore,
pre-taxonomic materials event modeling needs provenance stress tests and partial-event
feedback objectives before label or phase-map claims are trusted.
```

Track A is currently strongest as a methodological critique and design bridge to Track B,
not as a final Nature-level result by itself.

## What Track A Has Actually Learned

### 1. Raw-XRD objectives are viable, but trivial baselines are dangerous

The opXRD residual CNN result is real enough to keep:

- peak-masked raw XRD reconstruction can beat linear interpolation;
- residual-over-interpolation is much cleaner than direct CNN prediction;
- in-distribution reconstruction scales strongly from 512 to 4096 spectra;
- held-out-source transfer improves much less and appears to plateau.

This supports the Bitter Lesson-compatible path: objective feedback from raw measurements
can train useful structure without human phase labels.

But it is not yet a paper by itself. Similar work already exists on self-supervised or
large-scale diffraction representation learning, and newer work is likely to move faster
than our small CNN unless we sharpen the scientific question.

### 2. Source/provenance artifacts are a major hidden variable

The most important Track A result is the artifact diagnostic:

- source identity is strongly recoverable from normalized opXRD metadata and XRD features;
- coverage masks alone are highly predictive of source;
- normalization and cropping reduce, but do not remove, source predictability;
- leave-one-source-out transfer failures are source-specific rather than uniform.

This is more original than "CNN reconstructs XRD." It suggests that future experimental
XRD foundation models may look general while silently organizing around lab/instrument/
preprocessing style.

This could become a serious methods paper if expanded from a local diagnostic into a
benchmark protocol:

```text
Every experimental-XRD representation paper should report source/provenance predictability,
coverage-controlled performance, interpolation baselines, and leave-one-source-out transfer.
```

### 3. HTEM supports "event as field," but only as a proxy

The HTEM results are useful but modest:

- sample libraries behave like event-level spatial fields;
- within-library partial observation predicts held-out XRD better than global/library-only
  baselines once enough positions are observed;
- space-filling observation budgets are better design rules than arbitrary sampling;
- local non-XRD public features did not improve over the spatial XRD field baseline.

The interesting lesson is not that HTEM prediction is good. It is that the unit of learning
should not be a static sample row. It should be a partially observed event field.

But HTEM lacks full event trajectories: planned recipe, observed process, raw measurement
sessions, failed measurements, operator/instrument details, and post-hoc labels separated
cleanly. Therefore HTEM alone cannot prove the pre-taxonomic thesis.

## Nearby Work We Must Not Accidentally Repeat

### Public XRD datasets and label ambiguity

NIST's open combinatorial diffraction dataset already studies human and ML label
disagreement on Nb-doped VO2; it explicitly reports that labels vary strongly near phase
boundaries and preserves uncertainty with consensus labels and Shannon entropy.

Source:
https://www.nist.gov/publications/open-combinatorial-diffraction-dataset-including-consensus-human-and-machine-learning

opXRD already provides 92,552 experimental powder diffractograms, 2,179 labeled, explicitly
aimed at automated pXRD analysis, transfer learning, and self-driving labs.

Source:
https://arxiv.org/abs/2503.05577

### Automated phase identification and phase mapping

There is a long line of work on phase mapping from high-throughput XRD: GRENDEL, GPhase,
PADNet, graph-based/physics-informed solvers, and newer systems that explicitly encode
crystallography, XRD, thermodynamics, kinetics, and chemistry knowledge.

A recent 2025 npj Computational Materials paper is almost the opposite philosophy from our
project: it argues that domain-specific materials knowledge should be encoded into
automated phase mapping.

Source:
https://www.nature.com/articles/s41524-025-01837-6

CrystalShift and Dara are also directly relevant. They treat XRD phase labeling as
probabilistic or multiple-hypothesis inference, with ambiguity handled by search,
refinement, Bayesian/model comparison, and human/further-characterization follow-up.

Sources:
https://arxiv.org/abs/2308.07897
https://arxiv.org/abs/2510.19667

### Self-supervised and foundation-style diffraction models

A 2025 self-supervised powder-diffraction paper uses contrastive learning on simulated XRD
patterns with augmentations for experimental effects and reports improved robustness and
generalizability.

Source:
https://www.mdpi.com/2073-4352/15/5/393

Recent and emerging papers also target single-shot crystallographic prediction,
multiphase identification, and simulation-to-experiment transfer. This means a generic
"transformer/CNN for XRD" project is not enough for originality.

Examples:
https://arxiv.org/abs/2603.23367
https://arxiv.org/abs/2605.12478

### Autonomous experiments and event pipelines

Adaptive XRD has already been used for autonomous phase identification, showing that
ML-guided XRD can detect minority phases faster than conventional scans.

Source:
https://www.nature.com/articles/s41524-023-00984-y

Event-driven data management for materials acceleration platforms also exists. It argues
that synthesis, characterization, evaluation, raw data recording, metadata entry, and
analysis can all be represented as events.

Source:
https://pubs.rsc.org/en/content/articlehtml/2024/dd/d3dd00220a

LLM-guided phase-diagram construction is now appearing too: a 2026 preprint uses LLMs as
experimental planners in a closed loop with high-throughput synthesis and XRD phase
identification.

Source:
https://arxiv.org/abs/2604.20304

## Where Our Angle Is Still Different

Existing work mostly asks:

```text
Can we identify phases, map phase diagrams, classify symmetry, or plan experiments better?
```

Our strongest differentiated question is:

```text
Before using inherited labels as targets, can raw/event feedback objectives reveal which
parts of the measurement/process space those labels compress, split, merge, or obscure?
```

That difference matters. We are not trying to win phase-label classification. We are trying
to build a learning loop where labels are downstream probes of a representation trained on
raw event feedback.

The phrase that may survive as the paper's central concept:

```text
provenance-stressed pre-taxonomic event representation learning
```

Maybe less awkward later, but the ingredients are right:

- pre-taxonomic: do not train primarily on phase/failure/purity labels;
- event representation: model partially observed making-and-measuring events;
- provenance-stressed: prove that the representation is not mostly source/instrument style;
- feedback objective: predict missing/future raw measurements, not just inherited labels.

## Publication Potential

### Not enough yet for Nature

Track A alone is not Nature-level. It is too dependent on public datasets with compressed
metadata, and several obvious nearby literatures already exist.

The Nature-level path likely needs Track B:

- a new controlled event dataset;
- raw process and measurement trajectories;
- failed/ambiguous outcomes retained;
- labels recorded after raw data, not used as the main training target;
- objective feedback tasks where event embeddings improve missing/future measurement
  prediction or active measurement selection;
- ontology stress tests showing inherited labels split, merge, or lose predictive utility.

### Possible methods paper from Track A

Track A could become a solid methods/benchmark paper if expanded:

Working title:

```text
When Experimental XRD Models Learn the Laboratory: Provenance Stress Tests for
Pre-Taxonomic Diffraction Representation Learning
```

Possible claims:

- source identity is strongly encoded in public experimental XRD, even after normalization;
- random splits and within-library splits can greatly overstate generalization;
- interpolation and coverage baselines are essential for masked-XRD objectives;
- residual learning can recover nonlocal peak structure, but source transfer plateaus;
- public HTEM sample libraries are useful event-field proxies but insufficient as true
  material-making event logs.

This would fit better as npj Computational Materials, Digital Discovery, Patterns,
Machine Learning: Science and Technology, Scientific Data plus methods, or a workshop/
conference route. It is not yet a broad Nature claim unless paired with Track B.

### Stronger combined paper with Track B

Working title:

```text
Are Phase Labels the Right Coordinates? Pre-Taxonomic Representation Learning for
Materials-Making Events
```

Core experimental claim:

```text
Event-trained raw/process representations predict missing or future measurements and
active-sampling value better than inherited labels, while inherited labels appear as
lossy downstream projections of the learned event space.
```

Track A would provide the cautionary prelude and baselines. Track B would provide the
controlled evidence.

## What Would Strengthen Track A Before Outreach

1. **Provenance ablation benchmark**
   Repeat opXRD representation tests under increasingly strict controls:
   full XRD, common theta crop, derivative features, row-normalized spectra, coverage-mask
   removal, source-balanced splits, and leave-one-source-out.

2. **Transfer to a different dataset without labels as targets**
   Pretrain on opXRD masked/peak reconstruction, freeze embeddings, and test on NIST or
   HTEM using raw-measurement tasks first. Only after that, inspect label entropy or phase
   labels as probes.

3. **Active partial-measurement simulation**
   Use HTEM and/or opXRD to ask: which next measurement location/window/timepoint should be
   acquired to best reduce uncertainty about the rest of the event field? Compare random,
   space-filling, greedy uncertainty, and model-based selection.

4. **Label-as-probe analysis**
   After training on raw objectives, measure whether labels are compact, split, merged, or
   boundary-like. The evaluation should never make phase labels the primary training goal.

5. **Dataset-design requirements for Track B**
   Convert Track A failures into lab requirements: log source/session/instrument, raw theta
   coverage, calibration, operator/date, failed scans, repeats, timepoints, process history,
   and raw post-hoc labels as separate layers.

## Decision

Keep Track A, but narrow its role:

```text
Track A is the artifact-and-objective sandbox.
Track B is the publishable scientific experiment.
```

The best next move is not to chase a higher opXRD score. It is to turn Track A into a
provenance-stress and measurement-budget protocol, then use that protocol to design and
defend the Track B lab dataset.

