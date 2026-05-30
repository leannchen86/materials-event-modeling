# Materials Event Modeling

Pre-taxonomic materials informatics experiments.

Read [SKILL.md](SKILL.md) first when resuming the project; it tracks the operating
stance and decision pivots.

The working hypothesis is that inherited labels such as `phase pure`, `phase impurity`,
`failed synthesis`, `metastable`, and `ambiguous XRD` are useful human projections, but
not necessarily the native coordinate system for discovery.

This repo has two connected tracks:

Track A uses public datasets as sandboxes for feasibility checks and artifact audits.
Track B builds toward a controlled material-making event dataset, where the event is the
unit of learning and inherited labels are recorded only as downstream probes.

This repo starts with a computational prototype:

1. Learn representations from raw or weakly processed XRD patterns.
2. Add composition and process metadata where available.
3. Stress-test whether conventional materials labels form natural, split, merged, or
   lossy regions in the learned latent space.

## Near-Term Milestone

Do not turn opXRD or NIST into a leaderboard. The near-term milestone is to use public
data only long enough to design Track B: a small controlled event dataset with raw process
logs, raw measurements, negative/ambiguous outcomes, and later human labels as probes.

Current Track A publication-positioning critique:
[docs/track_a_publication_assessment.md](docs/track_a_publication_assessment.md)

## Layout

```text
docs/          Project notes and experiment design.
data/          Local datasets and generated manifests.
notebooks/     Exploratory analysis.
src/           Reusable preprocessing, models, training, and evaluation code.
configs/       Local and Zeus run configs.
scripts/       Thin command-line entrypoints.
```
