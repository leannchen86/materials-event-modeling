# Track B Publication Assessment

Literature scan date: 2026-05-30.

## Bottom Line

Track B has a real publication-shaped idea, but the publishable core is not simply
"failed experiments matter" or "XRD labels are ambiguous." Those areas already have
substantial work.

The potentially original contribution is:

> Treat the material-making event as the native learning unit, train on raw/event feedback
> tasks first, and use inherited terms such as phase purity, impurity, ambiguity,
> metastability, and failure only as downstream probes of the learned space.

That is distinct from four common directions:

- predicting success/failure labels from recipes,
- extracting impurity or synthesis labels from literature,
- automating phase-map labels from XRD,
- building ontology/knowledge-graph infrastructure for experimental records.

To become paper-grade, Track B needs a controlled dataset and one clear demonstration that
event-native representations are functionally better than inherited labels for prediction,
compression, retrieval, active measurement, or transfer.

## Nearby Work We Must Not Accidentally Repackage

### Failed Experiments and Negative Data

Raccuglia et al. used archived failed hydrothermal reactions to train models that predict
reaction success, showing the value of "dark" reactions in materials discovery:
https://www.nature.com/articles/nature17439

Moosavi et al. reconstructed partially failed MOF synthesis attempts to model synthesis
intuition:
https://archive.materialscloud.org/records/783j8-8h324

Recent solid-state synthesis work from Lee, Cruse, Baibakova, Ceder, and Jain used LLMs
to extract 80,806 solid-state syntheses, including 18,869 with impurity phases:
https://www.nature.com/articles/s41597-025-06222-y

Other recent work also frames synthesis prediction around success/failure or
synthesizability labels:
https://pubs.rsc.org/en/content/articlehtml/2025/dd/d5dd00065c

Implication: "use failed experiments" is not original enough. Our distinction has to be
that failure/impurity labels are not the target ontology; they are probes after raw-event
representation learning.

### Autonomous Labs and Closed-Loop Synthesis

The A-Lab paper already integrates DFT databases, synthesis heuristics, XRD analysis,
active learning, robotics, and failed-synthesis feedback:
https://www.nature.com/articles/s41586-023-06734-w

The same work also categorizes failed targets into modes such as slow kinetics, precursor
volatility, amorphization, and DFT limitations. A later PRX Energy critique argues that
automated XRD interpretation and claims of new materials require much stricter evidence:
https://journals.aps.org/prxenergy/abstract/10.1103/PRXEnergy.3.011002

Implication: we should not compete by claiming autonomous discovery early. Our safer route
is measurement/representation rigor: build a dataset and benchmark that makes automated
interpretation less brittle.

### Phase Mapping, Label Ambiguity, and XRD Automation

NIST already published a combinatorial diffraction dataset with expert and ML labels,
showing that labels vary strongly near phase boundaries:
https://www.nist.gov/publications/open-combinatorial-diffraction-dataset-including-consensus-human-and-machine-learning

NIST and collaborators also have a human-in-the-loop Bayesian autonomous phase-mapping
direction:
https://www.nist.gov/publications/human-loop-bayesian-autonomous-materials-phase-mapping

Deep reasoning networks and metric-geometry phase-mapping methods already attack XRD
phase maps with unsupervised/weakly supervised tools:
https://www.nature.com/articles/s42256-021-00384-1
https://pubs.rsc.org/en/content/articlehtml/2023/dd/d3dd00105a

Implication: "XRD phase labels are ambiguous" is already established. Our claim must be
about event-native raw feedback and whether old labels are adequate coordinates after that
representation is learned.

### Self-Supervised or Transformer Diffraction Models

Recent XRD representation work includes self-supervised contrastive learning on simulated
powder diffraction patterns and evaluation on real experimental patterns:
https://publications.rwth-aachen.de/record/1012005/files/1012005.pdf

Recent preprints also use transformer/autoregressive models for structure prediction from
diffraction patterns:
https://arxiv.org/abs/2508.08349
https://arxiv.org/abs/2604.23811

Implication: "train a transformer/CNN on XRD" is not enough. Architecture choice is a
baseline issue, not the main novelty.

### Data Infrastructure, Ontologies, and Knowledge Graphs

Materials experiment knowledge graphs already encode provenance and experiment metadata:
https://pubs.rsc.org/en/content/articlelanding/2023/dd/d3dd00067b

Event-driven cloud data management for materials acceleration platforms is also an active
area:
https://authors.library.caltech.edu/records/y0dyj-gv779

OPTIMADE focuses on interoperable database access:
https://www.optimade.org/

Implication: we should not pitch Track B as just another schema or knowledge graph. The
schema is infrastructure for a learning experiment.

## Candid Critique of Our Current Progress

What is strong:

- The conceptual thesis is sharp: labels are probes, not ground-truth objectives.
- The repo has clear guardrails against public-dataset leaderboard drift.
- The public-data work already exposed crucial failure modes: source artifacts in opXRD,
  shortcut leakage in HTEM random-position splits, and the difference between sample rows
  and event/field structure.
- The HTEM spatial-field result is genuinely useful: within a sample library, predicting
  held-out XRD from partial observations behaves more like event-field reconstruction than
  static material-row prediction.
- The Track B schema now separates planned conditions from observed trajectories, which is
  a real design improvement.

What is weak:

- The Track B synthetic scaffold is not evidence about chemistry. It is only a harness for
  analysis logic.
- We do not yet have real material-making events.
- We do not yet have temporal or spatial partial observations from our chosen system.
- We have not shown active measurement value or intervention value.
- We have not proven that a learned representation is better than old labels on a real
  controlled dataset.
- Calcium carbonate is scientifically convenient, not chemically novel. Its role must be
  as a benchmark system for event representation, not as a new chemistry claim.

## Publication-Shaped Contributions

### Paper 1: Data/Benchmark Paper

Working claim:

> We introduce a controlled material-making-event dataset with raw process histories,
> raw measurements, planned/observed fields, negative and ambiguous outcomes, and labels
> recorded only after raw data is frozen.

Likely venue shape: Scientific Data, Data in Brief, or a methods-oriented materials
informatics venue.

This becomes interesting if the dataset is clean, reusable, and contains enough replicate,
session, and partial-observation structure to support objective tasks.

### Paper 2: Methodological Paper

Working claim:

> Event-trained raw-measurement representations predict missing or future measurements
> better than label-only, composition-only, and static-material baselines, while inherited
> labels split, merge, or smear in the learned space.

Likely venue shape: Digital Discovery, npj Computational Materials, Patterns,
Nature Computational Science, or Nature Machine Intelligence if the results are broad and
strong.

This is probably our main research lane.

### Paper 3: Active Measurement / Event-as-Field Paper

Working claim:

> Treating each synthesis as a field or trajectory lets a model choose which partial
> measurements to collect next, reducing characterization cost while preserving or improving
> downstream measurement prediction.

This is the strongest route toward a higher-impact paper because it has an objective,
actionable payoff. It also fits the Bitter Lesson framing: the system improves because it
gets better feedback from reality, not because we renamed labels.

## What Would Make the Work Look Less Legit

- Optimizing around phase-label accuracy as the primary metric.
- Reporting random-split wins where replicates, sample libraries, dates, or instruments
  leak across train and test.
- Deleting ambiguous, partial, or failed events.
- Letting labels decide which raw files are retained.
- Treating synthetic hidden regimes as evidence for real hidden regimes.
- Using UMAP/t-SNE pictures as proof without objective prediction, retrieval, or transfer.
- Failing to compare against boring baselines: composition, planned process variables,
  instrument/session, interpolation, event mean, nearest neighbor, and simple PCA.
- Claiming causal relationships from observational public datasets.

## Offline Work We Can Do Before Lab Data

1. Turn the HTEM spatial-field result into a reusable Track B analysis template.
   The key pattern is: hide partial measurements inside an event, predict them from the
   rest, and compare against event mean and interpolation baselines.

2. Run synthetic pilot-size stress tests.
   Vary 12, 24, 48, and 96 events; vary number of partial observations per event; test how
   many replicates are needed before the ontology audit is even meaningful.

3. Build a lab-ready "event packet."
   Include a one-page schema, blank event log, raw-file naming convention, and a post-run
   label form. The label form should be filled only after raw data is frozen.

4. Build the first real analysis script before real data arrives.
   It should accept a directory of event JSON files and raw XRD files, then run:
   event summary, missingness audit, leakage audit, train/test split by batch/session,
   masked XRD reconstruction, held-out event-measurement prediction, replicate retrieval,
   and label projection audit.

5. Define the minimum viable lab pilot.
   A strong first pilot is not "48 independent samples." It is something like:
   12 to 24 planned conditions, 2 to 4 replicates each, multiple time/space/modality
   observations per event, raw XRD exports, and explicit batch/session tracking.

## Nature-Level Bar

For Nature or a Nature-branded high-impact paper, the story probably needs at least one of:

- a new public dataset other labs actually want to reuse,
- a clear active-learning or active-measurement win on real experiments,
- external validation at a second lab or second material system,
- a demonstrated reduction in experiment/measurement cost,
- a result that changes how autonomous materials labs should store feedback.

The current project is not there yet, but it is pointing at a real gap. The right ambition is:

> Build the benchmark and feedback loop that future self-driving materials labs need before
> they can stop mistaking inherited labels for reality.

