# Universal Event Embedding Scaffold

## Purpose

This repo is no longer positioned as "replace hand-crafted features with neural features."
That framing is too close to mainstream materials ML.

The current target is:

```text
universal event embeddings for materials experiments
```

Meaning:

```text
any subset of event evidence -> internal event state -> predict, retrieve, or choose the
next feedback-bearing measurement
```

Human labels remain useful, but they are downstream probes rather than the native training
ontology.

## Current Prototype Surface

The first practical scaffold now has three pieces:

- schema: `schemas/material_event.schema.json`
- ingestion/audit utilities: `src/materials_event_modeling/track_b/event_ingest.py`
- audit script: `scripts/audit_track_b_event_dataset.py`

The schema now supports:

- planned process conditions,
- observed process trajectory,
- raw measurement files,
- event-internal observations,
- provenance/session/source fields,
- labels assigned only after raw data is frozen,
- data-quality and missingness notes.

The audit script turns a folder or JSON array of events into readiness checks for the
core research tasks.

Run:

```bash
.venv/bin/python scripts/audit_track_b_event_dataset.py \
  --output data/manifests/track_b_event_dataset_audit.json
```

## Audit Result On Current Mock Events

The current calcium-carbonate mock set has 6 events.

It preserves some useful structure:

- 6 XRD references,
- 1 spectroscopy reference,
- 1 microscopy reference,
- 2 photo references,
- 2 operators,
- 2 batches,
- 6 labels assigned after raw data is frozen,
- 5 ambiguity-like labels kept as probes.

But it fails most readiness criteria:

| Task | Ready? | Current Signal |
| --- | --- | --- |
| Masked event reconstruction | No | 0 events with at least 3 event-internal observations |
| Missing-modality prediction | No | 4 events with at least 2 modalities |
| Provenance shortcut tests | No | only 6 events |
| Failure/ambiguity as data | Yes | 5 ambiguity-like labels, 0 failure-like labels |
| Replicate retrieval | No | 1 replicate group |
| Event-native vs label baseline | No | only 6 events |

This is good as a mock-schema test, but not as a learning dataset.

## What This Tells The Lab Ask

The lab ask should not be:

```text
Can we get some final XRD files?
```

It should be:

```text
Can each material-making event contain multiple feedback-bearing observations?
```

Useful forms:

- multiple time points from the same synthesis,
- multiple spatial positions from the same sample/library,
- multiple modalities from the same event,
- replicate events under the same planned condition,
- deliberately retained ambiguous and failed runs,
- counterbalanced operator/session/batch/instrument context.

## Seven Workstreams

### 1. Event Schema And Ingestion

Status: first pass implemented.

Next:

- add real example event folders once a lab or public event-like source is available,
- validate raw file existence with `--file-base-dir`,
- add parsers for XRD/Raman/FTIR files after actual formats are known.

### 2. Masked Event Reconstruction

Status: synthetic objective implemented.

Next:

- run the same objective on HTEM within-library fields,
- require strong baselines: event mean, nearest neighbor, IDW, coordinate ridge,
- use residual-over-interpolation targets where interpolation is strong.

### 3. Missing-Modality Prediction

Status: schema/audit readiness only.

Next:

- define tasks such as `process + XRD -> Raman`, `process + image -> XRD embedding`, or
  `early measurements -> later measurement`,
- do not count multimodal as progress unless it beats strong single-modality baselines.

### 4. Provenance/Shortcut Stress Tests

Status: first audit fields implemented.

Next:

- split by operator, batch, instrument session, measurement day, source dataset,
- add metadata-only and provenance-only baselines,
- require learned representations to survive held-out provenance splits.

### 5. Failure/Ambiguity As Data

Status: audit counts ambiguity/failure-like labels.

Next:

- make lab forms explicitly retain failed, partial, and ambiguous events,
- store labeler disagreement and confidence,
- use these labels only as probes after raw/event objectives train.

### 6. Lab-Ready Data Collection Protocol

Status: docs and schema are close enough for sanity-check outreach.

Next:

- turn the schema into a one-page event packet,
- ask staff scientists which fields are unrealistic,
- ask whether raw instrument exports and metadata can be saved consistently.

### 7. Event-Native Versus Label/Material-Row Baselines

Status: implemented in synthetic runs, not yet real data.

Next:

- compare event-native objectives against label-only, composition/process-only,
  final-material-row, and provenance-only baselines,
- report functional metrics first: missing measurement error, retrieval, transfer, and
  active measurement utility.

## Stop Rule

Do not keep optimizing the synthetic event benchmark unless the run changes the design of
the event schema, lab ask, or evaluation protocol.

At this point, the main gain is better event data, not another local architecture sweep.
