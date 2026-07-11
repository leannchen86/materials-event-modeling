# Materials Event Modeling

Materials-event modeling with provenance-stressed evaluation.

## Headline results (as of 2026-07-03; all pre-registered + adversarially verified)

- **Collection provenance is recoverable from public experimental XRD, and it replicates.**
  Source/lab identity is recoverable from opXRD spectra + metadata even after normalization;
  the finding replicates on a second experimental dataset (RRUFF Raman) and a second modality
  (battery cycling), and a chemistry-matched control localizes the invariant signal to
  acquisition geometry. →
  [provenance_leakage_audit.md](docs/provenance-critique/provenance_leakage_audit.md),
  [second_dataset_replication.md](docs/provenance-critique/second_dataset_replication.md)
- **Paper-shaped data structurally loses information a grammar-preserved event record keeps.**
  On real battery data, the recipe+final-label projection cannot rank replicates of one recipe
  or represent failed runs; the grammar representation can. →
  [severson_representation_ab.md](docs/controlled-collection/severson_representation_ab.md),
  [event grammar v1](schemas/event_grammar.v1.schema.json) + the L0–L3 conformance ladder
- **A validation ladder + a candidate top claim**, with the honest data caveats attached. →
  [event_grammar_validation_note.md](docs/spine/event_grammar_validation_note.md),
  [data_assumptions_and_limits.md](docs/spine/data_assumptions_and_limits.md)

Every headline number above is sourced once in
[`docs/spine/results_ledger.json`](docs/spine/results_ledger.json) (a pointer into its run
manifest), kept honest by `python scripts/check_results_ledger.py`. Edit magnitudes there,
not in prose.

Read [SKILL.md](SKILL.md) first when resuming the project; it tracks the operating
stance and decision pivots.

The working hypothesis is conditional: inherited labels such as `phase pure`, `phase
impurity`, `failed synthesis`, `metastable`, and `ambiguous XRD` can be useful, lossy, or
insufficient depending on the measurement task and collection context. The repository
tests that claim with raw measurements, strong non-neural baselines, and provenance-aware
splits; it does not assume that labels or raw measurements are intrinsically privileged.
The formal audit separates common-support task risk (TRCL), event/decision support retention,
representation collisions, and upstream recoverability; it is defined in
[task_relevant_compression_audit.md](docs/spine/task_relevant_compression_audit.md).

The work has two active directions and one retained reference archive. See
[PROJECTS.md](PROJECTS.md) for the current decision record.

- **provenance-critique** *(active)* — turn the opXRD/NIST/HTEM findings into a reusable
  protocol for detecting and controlling collection-provenance shortcuts.
- **controlled-collection** *(active)* — create the smallest real, counterbalanced
  material-making pilot capable of testing one pre-registered partial-event task.
- **event-method** *(reference archive)* — synthetic policy, field, and representation
  experiments retained for their design lessons, plus the completed real-data campaign
  (Runs 001–015; see
  [docs/event-method/findings_summary.md](docs/event-method/findings_summary.md)); no new
  architecture work proceeds there before real data changes the question.

The computational approach across branches:

1. Measure how provenance and collection choices affect raw-measurement models.
2. Define a real partial-event prediction task that cannot be solved by interpolation,
   a time prior, a recipe, or an event identifier.
3. Compare raw measurements, process context, and inherited labels only under those
   controls.

## Near-Term Milestone

Do not turn opXRD, NIST, HTEM, or the synthetic scaffold into leaderboards. The near-term
milestone is a small controlled event dataset with raw process logs, raw measurements,
negative/ambiguous outcomes, counterbalanced provenance, and labels retained as
comparators. New public-data or synthetic experiments need to test a new capture or
evaluation requirement; architecture sweeps are out of scope.

Current provenance-critique publication-positioning critique:
[docs/spine/provenance_publication_assessment.md](docs/spine/provenance_publication_assessment.md)

## Layout

```text
docs/spine/                 Thesis, strategy, infra, publication assessments.
docs/provenance-critique/   "Models learn the lab" findings on public XRD data.
docs/event-method/          Archived method and synthetic-harness record.
docs/controlled-collection/ Dataset collection, schema, audits, and outreach/.
data/                       Local datasets and generated manifests.
notebooks/                  Exploratory analysis.
src/                        Reusable preprocessing, models, training, and evaluation code.
configs/                    Local and Zeus run configs.
scripts/                    Command-line experiment entrypoints; many archived runs still need consolidation.
```

Code (`src/`, `scripts/`) and data (`data/`) stay in standard package layout and are
shared across branches; the branch split lives in `docs/` and `PROJECTS.md`.
