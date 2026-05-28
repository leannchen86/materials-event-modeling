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

## Current NIST Lesson

The first NIST baseline shows that human-label disagreement is structured:

- 73 of 192 human-labeled rows have non-unanimous labels.
- Composition/temperature predicts disagreement strongly.
- XRD PCA also predicts disagreement and gives more compact consensus-label structure.
- Adding XRD PCA to composition/temperature improves grouped-by-temperature ROC-AUC.

Interpretation: the phase labels are lossy near structured transition regions, but the
first pass does not yet prove that raw XRD alone has discovered a better ontology.

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

