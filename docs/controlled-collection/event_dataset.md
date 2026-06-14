# Track B: Controlled Event Dataset

## Purpose

Track B is the main research direction. Public datasets are useful placeholders, but they
carry unknown collection choices, hidden preprocessing, contributor effects, and asymmetric
context. They should teach us what to control, not become the target.

The unit of learning is the material-making event:

```text
process trajectory -> raw measurements -> optional later human labels
```

The project should not start by predicting labels such as `phase pure`, `phase impurity`,
`metastable`, or `failed synthesis`. Those labels should be recorded, but treated as
downstream projections that we can audit after raw/event representations are learned.

## Guardrail

Do not optimize Track B around public-dataset scores. A public-data result matters only if
it informs one of these:

- how to define objective feedback tasks,
- what artifacts or confounders to track,
- what metadata is missing from public datasets,
- what baselines a controlled event dataset must beat.

If an experiment only improves opXRD reconstruction without changing the event-dataset
design, it is likely drift.

## Candidate System

The first candidate system is calcium carbonate polymorph crystallization, pending lab SOP,
training, and safety review.

Why this system:

- It is process-sensitive and can naturally produce mixtures, partial conversion,
  metastable forms, and ambiguous measurements.
- The interesting outcomes are not just static composition; they depend on event history.
- It can be studied with common measurements such as powder XRD, microscopy, and optional
  Raman or FTIR.

This document is not a chemistry protocol. A partner lab must define the actual procedure,
chemical handling, waste handling, PPE, and instrument SOPs.

## MVP Dataset Shape

Start small: 48 to 96 events is enough for a first controlled dataset if logging is rich.

Each event should include:

- event identity: event id, date, operator, lab, batch, pre-registered plan id,
- process inputs: precursor identities, lots, concentrations or prepared solution ids,
- planned conditions: target temperature, intended aging time, planned mixing mode,
  planned additives, intended separation/drying route,
- observed trajectory: timestamps, actual temperature, pH, mixing/stirring/shaking notes,
  deviations, actual aging time, observed turbidity or visual state,
- raw observations: photos, time-series notes, turbidity or visual state if available,
- raw measurements: XRD raw file, measurement metadata, optional Raman/FTIR/microscopy,
- final human-facing labels: assigned after raw data is frozen,
- data quality notes: deviations, missing fields, instrument warnings, failed/partial
  events.

Negative, ambiguous, and messy events must be kept. They are not noise.

## Minimal Hypotheses

H1: Raw measurement and process-event embeddings predict held-out measurements better than
label-only or composition-only baselines.

H2: Inherited labels do not form clean native clusters; they split, merge, or smear when
projected onto event-trained representations.

H3: Some labels such as `phase impurity`, `metastability`, and `failed synthesis` behave
like projections of process regions rather than independent ground-truth categories.

H4: Event history improves prediction over static final-material representations.

## Objective Feedback Tasks

Use labels only after training. First train/evaluate on objective feedback:

- masked XRD reconstruction,
- process metadata -> held-out measurement prediction,
- early measurement/timepoint -> later measurement prediction,
- replicate retrieval,
- nearest-neighbor retrieval of similar event trajectories,
- active sampling utility after the pilot is stable.

Good metrics:

- held-out measurement error,
- retrieval of true replicates or neighboring process conditions,
- transfer across day, operator, reagent lot, or instrument run,
- calibration of uncertainty on ambiguous outcomes.

Bad metrics as primary objectives:

- phase-classification accuracy,
- purity-label prediction,
- success/failure classification,
- agreement with one expert label.

Those can be probes later, not the native training target.

## Experimental Design Requirements

To make later causal interpretation less fragile:

- pre-register the event variables before running a batch,
- randomize run order where the lab workflow allows it,
- include replicates,
- log deviations instead of deleting them,
- keep raw files before label assignment,
- avoid filtering out ambiguous events,
- record instrument settings and file export settings,
- track operator, date, reagent lot, and instrument session.

Common ways to invalidate the project:

- only collecting clean successes,
- assigning labels before saving raw data,
- allowing labels to decide what data is kept,
- changing procedure without logging the change,
- using one instrument/session without recording that limitation,
- optimizing the model to reproduce the lab's existing labels.

## Resource Ask

For a partner lab, ask for:

- a basic wet-lab bench and approved SOP for the chosen system,
- powder XRD access with raw data export,
- pH and temperature logging,
- basic mixing, aging, separation, and drying capability,
- optional Raman, FTIR, and microscopy,
- permission to save failed, ambiguous, and partial events,
- permission to store raw instrument files and event metadata,
- guidance on chemical safety, waste, PPE, and lab training.

## First Track B Milestone

Before any lab work:

1. Finalize the event schema.
2. Fill 5 to 10 mock events from imagined or historical runs to test the logging surface.
3. Ask a lab whether the fields are realistic to collect.
4. Adjust the schema based on what the lab can actually record.
5. Only then run a tiny pilot batch.

Current working artifacts:

- Event schema: `schemas/material_event.schema.json`
- Universal event embedding scaffold: `docs/universal_event_embedding_scaffold.md`
- Event ingestion/audit utilities: `src/materials_event_modeling/track_b/event_ingest.py`
- Event dataset audit script: `scripts/audit_track_b_event_dataset.py`
- Current mock-event audit: `data/manifests/track_b_event_dataset_audit.json`
- Blank event-log template: `templates/calcium_carbonate_event_log.csv`
- Mock JSON events: `examples/track_b/calcium_carbonate_mock_events.json`
- Mock CSV event log: `examples/track_b/calcium_carbonate_mock_event_log.csv`
- Mock event review: `docs/mock_event_review.md`
- Lab outreach brief: `docs/lab_outreach_brief.md`
- Mock event summary script: `scripts/summarize_track_b_mock_events.py`
- Synthetic event scaffold: `scripts/run_track_b_synthetic_scaffold.py`
- Synthetic scaffold result: `data/manifests/track_b_synthetic_event_scaffold.json`
- Synthetic scaffold notes: `docs/synthetic_scaffold.md`

The first real result should not be "we made pure calcite." It should be:

> We can collect raw material-making events in a way that preserves process history,
> ambiguous outcomes, and downstream labels without letting those labels define the
> representation.
