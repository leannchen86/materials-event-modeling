---
name: materials-event-modeling
description: Project operating memo for pre-taxonomic materials event modeling. Use when resuming this repo, choosing next experiments, interpreting results, or deciding whether a proposed analysis stays aligned with the Bitter Lesson framing.
---

# Materials Event Modeling

## Core Stance

The project asks whether inherited materials terms such as `phase`, `two-phase region`,
`phase impurity`, `failure`, `metastability`, and `ambiguous XRD` are useful human
interfaces rather than the native coordinate system for discovery.

Do not require learned representations to be human-interpretable at the beginning. That
would sneak the old ontology back in as the judge. Instead, require objective feedback
tasks: prediction, compression, retrieval, search, or intervention.

## Decision Pivots

1. **Labels are probes, not ground truth.**
   Human and machine labels are useful for auditing learned spaces, but they should not
   be the main objective forever.

2. **Objective tasks come before interpretability.**
   The Bitter Lesson-compatible question is not "can we name the latent axes?" It is
   "does the representation become more useful as data and compute scale?"

3. **Raw/event prediction is the main path.**
   Prefer objectives such as masked XRD reconstruction, neighboring-measurement
   prediction, held-out spectrum prediction, trajectory forecasting, and active-sampling
   usefulness.

4. **Old taxonomies are downstream projections.**
   After training on raw/event objectives, inspect where phase labels, two-phase labels,
   failure labels, and disagreement land inside the representation.

5. **Controls matter without becoming the philosophy.**
   Composition, temperature, sample index, instrument artifacts, and preprocessing can
   explain results. Control for them to avoid fooling ourselves, but do not make them the
   final ontology.

6. **Every run needs a hypothesis and a verdict.**
   Before running an experiment, state the expected outcome and what would validate,
   weaken, or falsify it. After the run, explicitly compare the result to the hypothesis,
   including caveats, next decision implications, and a critique of why the proposed next
   direction is the right move. That critique should name what was learned from the last
   result, what tempting but weaker direction it avoids, what assumption the next test is
   actually probing, and what outcome would make us abandon or revise that direction.

7. **Prefer the A100 on Zeus when available.**
   For GPU runs on Zeus, check GPU availability and prioritize `CUDA_VISIBLE_DEVICES=0`
   for the A100. Fall back to another GPU only if the A100 is busy, unsuitable, or the
   run is just a tiny smoke test.

8. **Do not turn public datasets into a leaderboard.**
   NIST, opXRD, and similar datasets are sandboxes for feasibility checks and artifact
   audits. Do not keep tuning around their metrics as if they were the research target.
   A public-data run is useful when it tests an objective feedback idea, reveals a
   failure mode, or informs Track B. It is drift when it only optimizes dataset-specific
   performance.

9. **Audit whether the feedback signal exists before training another model.**
   Anubhav Jain's feedback sharpened the bottleneck: public experimental datasets are
   often scattered or unavailable, lack metadata, and lack clear metrics/problems for
   judging new ideas. Track B should therefore treat dataset audit and benchmark design as
   first-class research objects. The question is not only "can a model learn from this?"
   but "does this dataset preserve enough of the material-making event to define a real
   feedback task?"

10. **Collect new data only after a structural gap is identified.**
    Do not collect a dataset merely because the physical system is simple or familiar.
    First try to reorganize existing data into the event schema. Collect a small "gold"
    event-native dataset only when existing data lacks something structurally necessary:
    time sequences, failed/ambiguous attempts, process variables, repeated recipes, raw
    files, intervention history, environmental context, provenance, or reusable licensing.

## Research Practice

Standing research-methodology principles adopted 2026-06-14 (memory:
`research-methodology-principles`). These supplement the Decision Pivots above; where a pivot
already covers one, it is noted rather than repeated.

1. **Reason backward from a wanted outcome; do not absorb problems.** Originality comes from
   chasing a result we actually want to exist, not from improving whatever is trending. For
   each direction, state why it matters and what outcome would make us drop it.

2. **Train taste: predict before running.** Extends pivot 6. Before a run, write the
   *expected number*, not just the hypothesis; after, log the miss and update. Guess a
   paper's results from its method before reading its results section.

3. **Tighten the loop; tooling is first-class.** Research speed is the speed of discovering
   we are wrong. Runs should be one command, reproducible from config, with two-run
   comparison in seconds. Shrink a problem until cheap (Shannon), get it right, then spend
   compute. Overfit a single batch before any scaled or neural run (Karpathy) — do this
   before the JEPA / refined-a runs.

4. **Stare at the outputs, not the loss curve.** Extends pivot 9 from metadata audit to the
   signals themselves: inspect raw data by hand before modeling, and after a run pull the
   worst cases, sort them into piles, and attack the biggest — never stop at aggregate MSE.
   Most bugs are silent data bugs. One strange transcript beats the next decimal of accuracy.

5. **Upgrade inputs.** Read primary deposits and papers — appendix and limitations are the
   honest parts — not thread summaries. Mine old/underpriced ideas (Bitter Lesson) and borrow
   from neighboring fields (SSL/JEPA, dynamical-systems/Koopman, mechanism design for active
   measurement).

6. **Log and publish.** Keep the dated design-note habit as a running
   hypothesis -> setup -> expectation -> result -> updated-belief log. Treat a clear public
   writeup (e.g. the provenance protocol) as a real deliverable, not overhead.

7. **Baselines until it hurts; ablate to the carrier.** Reinforces the stop rules. Tune
   baselines (event_mean / IDW / coordinate_ridge / RF) until it hurts, and ablate until we
   know the single component carrying a result — usually not the one in the title.

## Current Public Event Dataset Lesson

The first simple-physics audit used the Durham dataset "Evaporation of alcohol droplets on
surfaces in moist air." It is a useful public event-trace smoke test because it includes 9
videos plus spreadsheets, with humidity/nozzle/particle conditions recoverable from the
README and filenames.

The audit validated the expected ceiling:

- event-like traces exist,
- several supporting movies/data are only available under request,
- there are no obvious replicate groups,
- there is no failed/ambiguous attempt log,
- there is no operator/session/run-order provenance,
- the archive is organized around paper figures rather than an event manifest.

The first smoke benchmark tested:

```text
first 25% of video-derived trace -> last 25% trace summary
```

Early traces improved over train mean, but metadata-only baselines still won. Best
metadata nearest-neighbor MSE improvement was about 36.1%; best early-trace nearest-neighbor
improvement was about 33.2%. Interpretation: raw traces contain signal, but this 9-video
release cannot cleanly test whether raw event traces beat compressed conditions. This is
evidence for the benchmark/data-structure gap, not a reason to tune architectures.

The first Dryad gelation audit asked whether a richer active-learning experimental dataset
escapes the same issue. It partially does and partially does not. Top-level metadata shows
useful signals: active learning, pH/temperature/concentration variables, time-dependent
rheology/microrheology/UV-Vis measurements, raw data where applicable, processed CSVs, and
GPR/modeling scripts. But the public release exposes only one 5.14 GB archive plus a
README, and the README says the dataset is organized by figure folders. There is no
top-level event manifest, repeated-condition map, failed/ambiguous attempt log, or
provenance/session/run-order table. Interpretation: Dryad is richer than Durham, but still
paper-shaped at the public interface. The next gain is internal archive/file manifest
inspection or author contact, not architecture tuning.

The first OpenCrystalData audit asked whether a deliberately ML-oriented public
crystallization image database is event-native. It is much more programmatically
inspectable than Dryad: the Kaggle API exposes 4 datasets, about 9 GB total, with in-situ
images, process conditions, raw images in some datasets, and auxiliary measurements such as
CLD or offline particle size distributions. But its public framing is image classification,
segmentation, object detection, anomaly detection, or particle-size measurement. No event
manifest, time-ordered trace definition, failed/ambiguous attempt log, or
provenance/session/run-order table is visible from metadata. Interpretation:
programmatically accessible and ML-ready does not imply event-native.

## Current NIST Lesson

The first NIST baseline shows that human-label disagreement is structured:

- 73 of 192 human-labeled rows have non-unanimous labels.
- Composition/temperature predicts disagreement strongly.
- XRD PCA also predicts disagreement and gives more compact consensus-label structure.
- Adding XRD PCA to composition/temperature improves grouped-by-temperature ROC-AUC.

Interpretation: the phase labels are lossy near structured transition regions, but the
first pass does not yet prove that raw XRD alone has discovered a better ontology.

The first masked-XRD reconstruction baseline is a better Bitter Lesson-style objective:

- Hide contiguous 2-theta regions and predict them from the remaining XRD signal.
- PCA missing-data reconstruction improves masked MSE by about 53-56% over train-mean
  prediction across 64, 256, and 512 point masks.
- Composition/temperature ridge improves about 20-23%.
- Linear interpolation helps only for short masks and fails badly as mask width grows.

Interpretation: even a simple low-dimensional raw-XRD basis is functionally useful for
predicting unseen measurement signal. This is stronger evidence for the raw-measurement
path than label-disagreement prediction alone.

The first neural attempt was intentionally small and did not beat PCA:

- A masked MLP autoencoder trained only on NIST reaches about 7% MSE improvement on
  random folds and 19% on held-out-temperature folds for 256-point masks.
- PCA missing-data reconstruction reaches about 54% and 53% on the same masks/splits.
- A same-data sanity check showed the MLP barely improves over train-mean reconstruction,
  so this is an architecture/training failure, not a deep result against neural methods.

Interpretation: NIST is too small for this naive MLP to learn robust imputation. Treat PCA
as the small-data floor. Neural scaling should probably wait for opXRD pretraining or a
more data-efficient architecture/objective.

## Current Scaling Direction

Use NIST as the pilot assay, not the training universe. Its job is to expose baselines,
failure modes, and transfer probes. Use opXRD as the larger raw experimental XRD pool for
self-supervised pretraining, then transfer learned representations back to NIST.

The first opXRD audit found 92,552 JSON diffraction patterns in the current Zenodo archive.
Most are unlabeled: 90,373 have zero decoded phases, 1,069 have one phase, 1,108 have two
phases, and only two have more. The archive is heavily contributor-skewed, especially LBNL
and INT, so pilot subsets should use a deterministic spread or stratified sampling rather
than the first files in archive order.

The first opXRD masked-reconstruction pilot showed that local interpolation is a very strong
baseline on fixed-grid opXRD. PCA is not automatically the floor here: small PCA sometimes
helps on random folds, but larger PCA bases can become unstable and much worse than train
mean, especially for wide masks and held-out-source splits. Future neural encoders should
beat interpolation, not just train mean, and the masking scheme should hide meaningful peak
regions instead of only rewarding smooth background interpolation.

The peak-mask stress test hides windows centered on high-intensity diffraction regions.
It makes train-mean prediction much worse and gives a sharper objective. PCA can beat
interpolation on some random-fold peak masks, but interpolation remains much more robust on
held-out-source splits. Treat random-fold wins as weak evidence; robust progress should show
up on peak masks and contributor/source shift.

The first opXRD neural pilot uses a dilated 1D CNN trained on peak-mask reconstruction. A
too-small receptive field failed for 1,024-point masks; the useful run uses depth 10 with an
approximate receptive field of 4,093 points. On a 512-spectrum pilot, it improves MSE by
34.6% on random folds and 33.0% on held-out-source splits, beating interpolation on MSE in
both cases. It still has worse MAE than interpolation, so treat this as a promising pilot
signal for peak recovery, not a mature representation claim.

The first replication curve weakens and clarifies that pilot. With two seeds and 25 epochs:
at 256 spectra, the CNN does not beat interpolation; at 512 spectra, it reliably wins random
folds on MSE and only barely wins held-out-source on average, with a 50% seed win rate. MAE
still loses to interpolation. Treat this as evidence that scale helps, not evidence that the
current CNN is robust enough.

The residual-over-interpolation CNN is the clearest neural result so far. It predicts a
correction to linear interpolation rather than the whole hidden region. With 256/512 spectra
and two seeds, it beats interpolation on MSE in every random and held-out-source trial; MAE
also improves in most settings. Interpretation: the model is learning structure beyond
local smoothness, but this is still a small local curve that must be scaled and transferred
before making stronger claims.

The first Zeus GPU scaling check extended residual learning to 1,024/2,048 spectra with two
seeds and 40 epochs. The run validates the MSE hypothesis: residual CNNs beat interpolation
on MSE in every random and held-out-source trial. The random-fold signal scales strongly
with sample count, reaching about 56.1% MSE improvement at 2,048 spectra versus about 13.4%
for interpolation. The held-out-source signal is positive but less scale-sensitive, staying
around 41% MSE improvement. MAE is mostly improved, but held-out-source remains mixed at
2,048 spectra. Interpretation: the residual model is learning real nonlocal peak structure,
but source-shift transfer, not in-distribution reconstruction, is now the main bottleneck.

The A100 4,096-spectrum check sharpened this lesson. Random-fold MSE improvement climbed
to about 71.2%, while held-out-source MSE stayed essentially flat at about 41.5%. MAE won in
both held-out-source seeds, which is encouraging, but the main causal story did not change:
scaling more spectra from the same mixed archive helps in-distribution reconstruction much
more than it helps source transfer. The next experiment should test source diversity and
transfer directly rather than only increasing sample count.

The first source-balanced sampling test did not fix source transfer. It added a
`source_balanced` sampling option that keeps rare opXRD sources represented and caps the
dominant LBNL/INT skew. At 1,024 spectra, held-out-source performance was essentially tied
with spread sampling; at 2,048 spectra it was worse, about 38.1% MSE improvement versus
41.2% for spread. Interpretation: simple source rebalancing is not enough. The transfer
bottleneck likely needs per-source diagnostics, source-aware normalization, or explicit
domain-transfer objectives.

The first leave-one-source-out diagnostic validates that source shift is not uniform. The
residual CNN beats interpolation clearly on INT and LBNL, barely on CNRS and USC by MSE
while losing MAE, and loses to interpolation on EMPA and HKUST. Interpretation: the
aggregate held-out-source score hides source-specific failure modes. Next investigate why
EMPA/HKUST differ: source size, instrument/preprocessing, material family, peak density, or
background/scale statistics.

The first source artifact diagnostic partially explains the split. HKUST and USC are sparse,
low-signal, interpolation-friendly sources; CNN wins there are tiny or negative. EMPA is a
different failure mode: it is small, fully labeled as two-phase, low raw-intensity scale,
and has dense local peaks after preprocessing. Interpretation: Track A public-data failures
are not one thing. For Track B, collect metadata that can expose source/session/instrument
style, theta coverage, peak density, and sample-preparation route before labels are used.

The source-predictability diagnostic shows that source identity is easy to recover from the
opXRD data itself. Eight metadata features predict source with about 98.7% accuracy, and 32
PCA components of normalized XRD alone reach about 91.2% accuracy and 78.6% balanced
accuracy across six sources. Interpretation: raw measurement embeddings can silently encode
lab/instrument/preprocessing provenance. Track B must log and split by session/source-like
variables so representation gains do not merely reflect collection artifacts.

The normalization-control diagnostic shows theta coverage is a major source artifact:
coverage masks alone predict source with about 95.0% accuracy and 89.8% balanced accuracy.
Cropping to theta bins covered by at least 95% of samples and using derivative features
reduces source predictability, but balanced accuracy remains about 55.6% versus a 16.7%
dummy baseline. Interpretation: normalization can reduce public-data provenance signals,
but cannot be trusted to remove them. Track B should log raw theta coverage, export format,
instrument/session, and preprocessing before any learned representation is interpreted.

The HTEM event-proxy audit validates HTEM as a useful bridge from raw XRD archives toward
event-shaped data. The public API exposed 1,891 sample-library records: 97.7% have
composition fields, 92.0% have at least one process field, 79.9% have nonzero XRD
availability, and 74.2% have composition plus process metadata plus XRD availability. A
small endpoint probe showed position-resolved property arrays and XRD arrays. However, HTEM
still looks like a sample-library snapshot, not a full material-making trajectory log. Use
HTEM to design Track B schemas and event-proxy objectives; do not turn it into another
leaderboard target.

The first HTEM event-table run built 1,408 position-level rows from 32 XRD-bearing sample
libraries and predicted 8-component XRD PCA targets. Random-position splits looked very
strong: recipe-plus-position improved MSE by about 86.9%, local non-XRD measurements by
about 89.5%, and sample-id-only by about 83.2% versus train mean. But held-out-library
transfer collapsed: recipe-plus-position was about 17.8% worse than train mean, and local
measurements were about 68.4% worse. Interpretation: random position splits mostly measure
within-library leakage/shortcut structure. Sample-level recipe fields can act as implicit
library identifiers when many positions from the same library are split across train and
test. Next HTEM work should either restrict to a chemistry family for cleaner held-out
library transfer, or explicitly frame the task as within-library spatial/event-field
modeling.

The first within-family HTEM control used all 65 `Cu|S|Sn` libraries with full XRD-position
coverage, producing 2,860 position-level rows. This did not rescue held-out-library
transfer: recipe-plus-position improved random-position MSE by about 31.4%, but was about
18.5% worse than train mean on held-out-library. Sample-id-only still improved
random-position MSE by about 75.6% and collapsed to train mean on held-out-library, which
confirms the split is exposing shortcut structure. Interpretation: the previous
held-out-library failure was not just broad chemistry/family mixing. For HTEM, the next
better-aligned task is within-library spatial/event-field modeling rather than stronger
supervised prediction from compressed sample-library metadata.

The first within-library spatial-field HTEM run is the cleanest support so far for the
event-as-field framing. Using the same 65 `Cu|S|Sn` libraries and 2,860 position-level rows,
predicting full held-out XRD spectra from other positions in the same library showed that
the library mean improves MSE by about 51% versus a global mean. Spatial smoothers add
signal beyond that: inverse-distance weighting over all observed positions improves about
15.8% versus library mean on random held-out positions and 12.1% on held-out rows. Nearest
neighbor is worse than library mean, so the useful structure is not just copying the closest
point; it is a smoother event-level field. This suggests Track B should create events with
multiple partial observations over time, space, process state, or modality, then predict
missing/future event measurements from partial event context.

The HTEM multimodal residual check did not validate local non-XRD measurements as useful
beyond the spatial XRD field baseline. With strong regularization, direct local-feature
ridge models were worse than library mean, and adding a local-feature residual correction
to `idw_all` made MSE about 1.4% worse on random held-out positions and 3.0% worse on
held-out rows. Interpretation: in this public slice, "multimodal" does not automatically
mean better. Track B should collect additional modalities, but always compare them against
strong within-event baselines such as library/event mean and spatial/temporal interpolation.

The HTEM spatial sampling budget curve supports an active-measurement design lesson. In
65 `Cu|S|Sn` libraries, observing more positions improved prediction of unmeasured
positions. With only 4 observations, `idw_all` was about tied with or slightly worse than
the observed library mean; with 32 observations, it improved about 15.2% under random
sampling and 17.6% under space-filling sampling. Space-filling generally lowered absolute
MSE and made coordinate models less fragile. Track B should therefore collect enough
partial observations per event to support field reconstruction, and prefer coverage over
convenience sampling.

## Track B Direction

Track B is the real pre-taxonomic event dataset. The unit is a material-making event, not a
material label. A controlled pilot should log process trajectories, raw measurements,
negative/ambiguous outcomes, and downstream human labels only as probes.

The first candidate system is calcium carbonate polymorph crystallization, pending lab SOP
and safety review. The goal is not to make pure calcite or optimize phase classification.
The goal is to create a small, richly logged event dataset where raw measurement/process
objectives can be tested before inherited labels are used.

The first Track B synthetic scaffold is now in place. It is not chemistry evidence; it is a
pre-lab test harness. In the two-view synthetic setup, planned, observed, and full-event
features all predict held-out synthetic spectra better than label-only features; planned
conditions retrieve replicates perfectly; and legacy labels split across multiple hidden
regimes. Design rule: real Track B data should separate planned condition fields from
observed trajectory fields.

The Track B pilot-size stress test adds a practical design constraint. Across five
synthetic seeds, 12- and 24-event replicated pilots had useful replicate retrieval but did
not beat label-only prediction on held-out spectra, because they covered too few planned
conditions. The first healthy region was around 48 events with replicate structure:
`16 planned conditions x 3 replicates` gave the best event-over-label gain among tested
48-event designs, while 48 one-shot samples could not test replicate retrieval at all.
Interpretation: use 12-24 events for schema debugging only; ask for roughly 48 events as
the first serious pilot, and 96 if resources allow.

The Track B synthetic field-budget test adds a second design constraint: partial
observations need coverage, not convenience sampling. In a 24-event synthetic field with
12 observations per event, one random observation per event was worse than a global mean;
space-filling observations were useful almost immediately. IDW field reconstruction beat
the event mean by about 15% with two space-filling observations, about 34% with four, and
about 44% with six. Interpretation: for a real pilot, do not merely ask for final XRD
files. Ask whether each planned condition or event can have at least 3-4 deliberately
covered partial observations, and preferably 6-8 if feasible.

The first real-data-style Track B event-analysis harness is now in place. On a 48-event
synthetic bundle, held-out-plan prediction reproduced the event-over-label signal:
planned conditions improved held-out spectrum MSE by about 63.7% versus train mean, while
label-only improved about 19.3%. The harness also flagged provenance leakage: raw spectral
PCA predicted synthetic operator at about 89.6% accuracy and reagent lot at about 75.0%.
Interpretation: always report random-event, held-out-plan, and held-out-batch/session
splits, and always audit whether raw embeddings encode operator, reagent lot, instrument,
or export artifacts.

The first provenance-ablation run adds shortcut tests to the harness. On the 48-event
synthetic bundle, event/process features remained strong after provenance residualization:
under held-out-plan splits, planned features improved residual-spectrum MSE by about 52.6%
while label-only improved about 14.7%. Shuffling event features within provenance groups
dropped held-out-plan gains from about 59-64% to about 12-15%, showing the synthetic signal
is not explained only by provenance group membership. But held-out-operator splits
collapsed for planned/full-event features because only two synthetic operators were
confounded with planned-condition coverage. Interpretation: ablations cannot prove no
shortcut exists, but they can expose bad pilot design. Real experiments should
counterbalance operator, reagent lot, batch, and instrument session across planned
conditions whenever possible.

The counterbalanced-pilot stress test compared provenance assignment strategies for the
48-event design. Deliberately confounded and plan-level "balanced" assignments collapsed
on held-out-operator/provenance splits, even though held-out-plan performance stayed high.
Replicate-level counterbalancing was robust: held-out-plan, held-out-operator, and
held-out-provenance-combo full-event prediction all stayed around 65% MSE improvement,
and provenance-residualized combo prediction stayed around 59%. Interpretation: the lab
ask should be `16 planned conditions x 3 replicates`, with each planned condition's
replicates distributed across available provenance axes such as operator, session, lot,
batch, run order, or measurement day. Counts alone are not enough.

The first active event-learning loop is in place. It does not use phase/failure labels:
it starts from partial raw event observations, chooses the next observation, and is scored
by missing raw-measurement reconstruction. The first heuristic active policies beat random
at tiny budgets but do not beat static space-filling after budget 3; they over-focus on
high-disagreement regions and lose coverage. The oracle-best policy is much stronger,
reaching about 72% improvement versus global mean at budget 8 versus about 66% for
space-filling and 26% for the active heuristic. Interpretation: this is a productive
failure. The next active-loop step should learn an acquisition policy from prior fully
observed events, rather than hand-tuning a heuristic.

The first learned active policy validates the feedback-loop direction. A
RandomForestRegressor trained on completed synthetic events predicts oracle one-step
reconstruction improvement from candidate/state features. It improves oracle-target MSE by
about 59-63% versus a train-mean target baseline. On held-out events, it beats random,
naive active, and static space-filling at budgets 4, 6, and 8, reaching about 71.9%
improvement versus global mean at budget 8 versus 67.9% for space-filling and 74.5% for
oracle. Interpretation: this is the first learned event-feedback win. The next step can be
a learned event-state encoder plus acquisition head, but only if it beats the forest.

The first neural active policy is a modest architecture win, not a transformer coronation.
A small set encoder with a 2-layer TransformerEncoder over observed coordinate/spectrum
tokens predicts oracle acquisition targets about 76.5% better than a train-mean baseline.
As a deployed held-out-event policy, it beats random and naive active selection at every
budget, beats the forest at budgets 4 and 8, loses slightly to the forest at budget 3, and
loses more noticeably at budget 6. Interpretation: learned event-state policies are
viable, but the architecture has not yet earned default status. Next test whether the set
encoder survives feature ablations, regime transfer, and provenance shifts before scaling.

The neural policy ablation strengthens the event-state claim while exposing a synthetic
shortcut. Removing the observed raw-spectrum set and using only engineered scalar features
cuts target-MSE improvement from about 76.5% to about 52.6%. Using raw-spectrum set models
with only basic candidate/budget state still reaches about 74.8-75.0% target-MSE
improvement, and these policies remain competitive with the full neural model and forest.
So raw event observations are doing real work. Caveat: coordinate-only policies become
strong at larger budgets, which means the current synthetic field is partly solvable by
spatial smoothness. Next stress test regime transfer and discontinuous/nonstationary event
fields rather than tuning this scaffold.

The first regime-transfer stress test is a productive negative result. Policies trained on
`source_smooth` transfer well to `matched_smooth`: raw-spectrum set variants reach about
78-79% target-MSE improvement, and `candidate_set_basic` is the best non-oracle policy at
budgets 4, 6, and 8. They retain smaller target signal on `abrupt_basin` fields, about
19-23% target-MSE improvement, but they collapse under `random_axis` and `reversed_time`
process-coordinate shifts. Coordinate/scalar shortcuts also do not vanish universally:
`coords_basic` wins reversed-time at budgets 4 and 8. Interpretation: raw-event policies
are real but not invariant. The next step should be mixed-regime training and held-out
regime testing, plus richer process-context fields that let a model infer event progress
axes, rather than tuning the same source-smooth scaffold.

The focused mixed-regime transfer run tested whether training on multiple synthetic
event-worlds fixes the source-only collapse. It helps but does not solve transfer. Holding
out `random_axis`, `reversed_time`, and `abrupt_basin`, mixed training improves raw
target-prediction collapse for `candidate_set_basic` by about +26.7 percentage points on
`random_axis` and +194.3 points on `reversed_time` relative to source-only training, but
the raw-spectrum target scores remain negative on both. At budget 8, `full_neural` improves
MSE versus source-only on `random_axis` and `reversed_time`, but best non-oracle policies
are still scalar/coordinate/forest methods: `scalar_full` wins random-axis and
`coords_basic` wins reversed-time. Interpretation: regime diversity reduces brittleness,
but the model still needs explicit latent event-progress/geometry inference. Next build a
policy that infers the current event's progress axis from partial observations, rather
than only feeding coordinates and spectra into an acquisition head.

The first explicit progress-policy test falsifies the simplest version of that idea. A
`latent_progress_forest` infers a 1D progress coordinate from observed spectral-change PCA
regressed on coordinates, while `oracle_progress_forest` gets the synthetic hidden
`event_progress` coordinate as an upper bound. Oracle progress is not enough: target-MSE
improvement is only about +6.6% on `abrupt_basin`, -5.0% on `random_axis`, and -52.6% on
`reversed_time`. At budget 8, latent progress wins `reversed_time` among non-oracle
methods, but progress policies do not dominate overall. Interpretation: the missing object
is not a scalar progress axis; it is a learned event field. Do not turn this into a fixed
knowledge graph or named relation ontology. The relations among observations should be
learned internally through objective feedback.

The first event-field model validates the representation direction while weakening naive
uncertainty acquisition. A RandomForestRegressor trained to predict PCA-compressed missing
spectra from partial event observations beats a train-mean PCA target baseline by about
31.7% on `abrupt_basin`, 54.1% on `random_axis`, and 14.7% on `reversed_time`. But
selecting the point with highest forest ensemble variance does not reliably beat
`space_filling`, `learned_forest`, or `active_hybrid`; the coverage-multiplied variant is
only competitive in a few budget/regime settings. Interpretation: event-field signal
exists, but pointwise uncertainty is not the same as expected improvement in whole-event
reconstruction. Do not keep tuning this heuristic in place. The next better direction is
masked event modeling: predict missing raw/event measurements from partial observations,
then derive acquisition from expected reduction in event-level reconstruction error.

The first masked event model validates that next step, but also warns against looping on
the synthetic scaffold. A Transformer-style set-to-point model trained on partial events
predicts missing spectrum embeddings from observed measurements and candidate coordinates.
The `raw_set` variant beats train-mean target prediction in every held-out regime, about
+30.1% on `abrupt_basin`, +39.5% on `random_axis`, and +35.6% on `reversed_time`, while
`coord_only` is weak or collapses. Observed raw spectra therefore carry event-specific
signal beyond coordinates. A `raw_residual` variant that predicts the residual over IDW
interpolation is strongest on full-spectrum reconstruction for `abrupt_basin`, winning
7 of 10 budget/mask settings and averaging about +32.6% improvement over event mean. It
also helps `reversed_time`, but it does not solve `random_axis`, where coordinate ridge
and the engineered RF baseline dominate. Interpretation: masked event reconstruction with
strong interpolation baselines is the right objective, but this synthetic benchmark still
contains coordinate/interpolation shortcuts. Do not keep doing same-shape local neural
sweeps. Next port the objective to HTEM-like or lab event data, or create a deliberately
harder scaffold only if it tests a data-design question.

The repo is now positioned as a universal event embedding scaffold rather than a
hand-crafted-feature replacement project. The first event-ingestion audit layer adds
`observations` and `provenance` to the event schema and introduces
`scripts/audit_track_b_event_dataset.py`. On the current 6-event calcium-carbonate mock
set, the audit validates labels-as-probes and some provenance logging, but marks masked
event reconstruction, missing-modality prediction, provenance stress tests, replicate
retrieval, and event-native-vs-label baselines as not ready. This is the intended failure:
the mock set has mostly one final XRD per event. The lab ask must therefore be multiple
feedback-bearing observations per material-making event, not merely final XRD files.

The small-scale work is allowed to be vibe-sensing only if the vibes are converted into
objective checks: masked reconstruction, held-out measurement prediction, retrieval, or
transfer improvement. If opXRD pretraining cannot beat the strongest simple baselines on
these checks, including local interpolation where relevant, scale alone has not yet earned a
stronger claim.

The low-equipment physical-pilot pivot is now part of Track B, not a side quest. Because
lab outreach is slow, the project can start curating fuller material-making traces with
cheap process-sensitive systems such as drying droplets, frozen brines, or drying films.
The first recommended pilot is drying droplets because it is safe, visual, fast, and rich
in process history: nominally simple recipes can yield rings, crystals, cracks, branching
patterns, smooth films, or ambiguous mixed outcomes depending on substrate, concentration,
humidity, disturbance, and drying path. The point is not that droplets are the final
materials system of interest. The point is to practice and test the core dataset claim:
early event traces plus process metadata should predict later/final observations better
than recipe-only, label-only, or single-still baselines. Labels such as `ring`, `crystal`,
`cracked`, `uniform`, and `failed` should be assigned only after raw video, final images,
environmental metadata, and notes are frozen. See
`docs/controlled-collection/low_equipment_event_trace_pilot.md`.

## Next Experiment Direction

Move from label-prediction diagnostics to raw measurement objectives:

1. Train simple self-supervised XRD baselines on NIST:
   - masked-region reconstruction,
   - full-spectrum autoencoding,
   - neighboring-sample spectrum prediction.
2. Compare embeddings by functional usefulness:
   - reconstruction error,
   - held-out spectrum prediction,
   - nearest-neighbor retrieval of adjacent measurements,
   - residual label-ambiguity prediction after composition/temperature controls.
3. Use old labels only after training:
   - project consensus labels onto the learned space,
   - inspect high-disagreement regions,
   - test whether labels split, merge, or smear.

## Oleogel Real-Data Campaign — Lessons (Runs 001–008, 2026-06-15)

The refined-a stage ran 8 logged runs on the oleogel SAXS/WAXS set (zenodo 15268752); detail in
`docs/event-method/run_log.md`, summary in `docs/event-method/findings_summary.md`. Lessons:

1. **The masked-frame task is interpolation/clock-solvable** on dense smooth trajectories → a
   poor discriminator for any model. Do not headline it.
2. **The normalised-time "clock" is a dominant baseline** for trajectory data — it beat the mean
   6/6 and beat SAXS on the median. Always include it; many apparent wins are the time-prior in
   disguise. (Extends "baselines until it hurts".)
3. **Cross-event (leave-one-run-out) is mandatory.** Within-event lets the model memorise the
   trajectory curve and ignore its observed context (Run 003: flat across anchor counts).
4. **Characterise raw signal before modeling.** A silent period-3 exposure artifact poisoned
   interpolation in Run 002; caught via total-intensity CV + autocorrelation + shape-vs-scale.
5. **Smooth time-series need smoothness-preserving nulls.** A plain shuffle/permutation null is
   confounded by autocorrelation (Run 007); use a circular-shift null AND a cross-event baseline
   (Run 008) — the cross-event baseline was the decisive control.
6. **Use capacity-free dependence measures to answer "model vs data".** Distance correlation
   with proper controls separated "signal exists" from "model good enough" with no tunable model.
7. **Empirical result:** on oleogel, SAXS↔WAXS are largely *time-redundant* — only 1/6 events
   shows genuine cross-modal excess. A data property (homogeneous, event-poor), NOT model capacity.
8. **Open in-situ crystallization deposits are event-poor** (oleogel 6 near-identical; zeolite
   18972297 = 1 run) → the empirical case for controlled-collection / a labeled, diverse dataset.

## Claim Discipline

Safe current claim:

> In NIST, label disagreement is systematic and related to both experimental coordinates
> and raw diffraction structure.

Newly established (oleogel real-data campaign, Runs 001–008):

> On the oleogel SAXS/WAXS set, raw masked-frame reconstruction is beaten by time-interpolation,
> and SAXS/WAXS are largely time-redundant (1/6 events show genuine cross-modal excess). A
> capacity-free test shows this is a property of the data (homogeneous, event-poor), NOT a
> model-capacity limit.

Newly established (RRUFF label-probe, Runs 009–010):

> Mineral labels are largely natural coordinates of raw Raman (k-NN top-1 0.88, 59 classes,
> cross-specimen) — but for common minerals the label ≈ composition, so raw does not beat the
> compositional proxy globally. Where composition is *constant* (same-composition polymorphs:
> CaCO3, TiO2, Al2SiO5, SiO2), the raw spectrum recovers the polymorph label near-perfectly
> (0.91–1.0) while the proxy is stuck at majority (0.40–0.74) — i.e. raw carries structure/label
> information the compositional proxy fundamentally cannot.

Not yet earned:

> A learned raw/event representation has discovered the true materials ontology.

Target claim:

> Raw/event-trained representations become more useful than inherited labels for
> prediction, compression, retrieval, or search, while inherited labels remain useful as
> human-facing probes.
