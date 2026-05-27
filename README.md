# Materials Event Modeling

Pre-taxonomic materials informatics experiments.

The working hypothesis is that inherited labels such as `phase pure`, `phase impurity`,
`failed synthesis`, `metastable`, and `ambiguous XRD` are useful human projections, but
not necessarily the native coordinate system for discovery.

This repo starts with a computational prototype:

1. Learn representations from raw or weakly processed XRD patterns.
2. Add composition and process metadata where available.
3. Stress-test whether conventional materials labels form natural, split, merged, or
   lossy regions in the learned latent space.

## Near-Term Milestone

Load one public XRD dataset, train a small self-supervised encoder, and evaluate whether
the latent space predicts human-label ambiguity or disagreement better than simple
baselines.

## Layout

```text
docs/          Project notes and experiment design.
data/          Local datasets and generated manifests.
notebooks/     Exploratory analysis.
src/           Reusable preprocessing, models, training, and evaluation code.
configs/       Local and Zeus run configs.
scripts/       Thin command-line entrypoints.
```

