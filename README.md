# Materials Event Modeling

Pre-taxonomic materials informatics experiments.

Read [SKILL.md](SKILL.md) first when resuming the project; it tracks the operating
stance and decision pivots.

The working hypothesis is that inherited labels such as `phase pure`, `phase impurity`,
`failed synthesis`, `metastable`, and `ambiguous XRD` are useful human projections, but
not necessarily the native coordinate system for discovery.

The work splits into three research branches with distinct deliverables, plus a
cross-cutting spine. See [PROJECTS.md](PROJECTS.md) for the full index (each branch's docs,
scripts, status, and next step).

- **provenance-critique** — "models learn the lab": raw-objective feasibility plus the
  source/provenance stress findings on opXRD/NIST/HTEM. Closest to a publishable methods
  paper. (Formerly "Track A".)
- **event-method** — the event model itself (masked-event, active measurement, JEPA,
  regime transfer); synthetic harness now, real time-resolved trajectory data next.
  (Was the modeling half of "Track B".)
- **controlled-collection** — the lab moat: CaCO₃, Foundry, outreach, low-equipment
  pilots, the event schema/packet, and audits of public datasets. (Was the data half of
  "Track B".)

The computational approach across branches:

1. Learn representations from raw or weakly processed XRD patterns.
2. Add composition and process metadata where available.
3. Stress-test whether conventional materials labels form natural, split, merged, or
   lossy regions in the learned latent space.

## Near-Term Milestone

Do not turn opXRD or NIST into a leaderboard. The near-term milestone is to use public
data only long enough to design controlled-collection: a small controlled event dataset
with raw process logs, raw measurements, negative/ambiguous outcomes, and later human
labels as probes.

Current provenance-critique publication-positioning critique:
[docs/spine/provenance_publication_assessment.md](docs/spine/provenance_publication_assessment.md)

## Layout

```text
docs/spine/                 Thesis, strategy, infra, publication assessments.
docs/provenance-critique/   "Models learn the lab" findings on public XRD data.
docs/event-method/          The event model and its synthetic harness.
docs/controlled-collection/ Dataset collection, schema, audits, and outreach/.
data/                       Local datasets and generated manifests.
notebooks/                  Exploratory analysis.
src/                        Reusable preprocessing, models, training, and evaluation code.
configs/                    Local and Zeus run configs.
scripts/                    Thin command-line entrypoints (prefixed by data source).
```

Code (`src/`, `scripts/`) and data (`data/`) stay in standard package layout and are
shared across branches; the branch split lives in `docs/` and `PROJECTS.md`.
