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
   including caveats and next decision implications.

7. **Prefer the A100 on Zeus when available.**
   For GPU runs on Zeus, check GPU availability and prioritize `CUDA_VISIBLE_DEVICES=0`
   for the A100. Fall back to another GPU only if the A100 is busy, unsuitable, or the
   run is just a tiny smoke test.

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

The small-scale work is allowed to be vibe-sensing only if the vibes are converted into
objective checks: masked reconstruction, held-out measurement prediction, retrieval, or
transfer improvement. If opXRD pretraining cannot beat the strongest simple baselines on
these checks, including local interpolation where relevant, scale alone has not yet earned a
stronger claim.

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

## Claim Discipline

Safe current claim:

> In NIST, label disagreement is systematic and related to both experimental coordinates
> and raw diffraction structure.

Not yet earned:

> A learned raw/event representation has discovered the true materials ontology.

Target claim:

> Raw/event-trained representations become more useful than inherited labels for
> prediction, compression, retrieval, or search, while inherited labels remain useful as
> human-facing probes.
