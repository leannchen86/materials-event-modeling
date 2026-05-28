# Track A: HTEM Event-Proxy Audit

## Pre-Run Hypothesis

HTEM should be more event-like than opXRD because it exposes composition, process,
measurement, and provenance fields, but it will probably remain a sample-library snapshot
rather than a full event-trajectory dataset.

This is not a model leaderboard. The point is to test whether a public dataset can stand in
for the material-making-event data structure that Track B needs.

## Command

```bash
python3 scripts/audit_htem_dataset.py --endpoint-sample-ids 2
```

Output manifest:

```text
data/manifests/htem_event_proxy_audit.json
```

## Result

The hypothesis was mostly validated.

HTEM is substantially more event-like than opXRD:

- 1,891 sample-library records were exposed by the public API.
- 1,847 records, or 97.7%, have nonempty composition fields.
- 1,739 records, or 92.0%, have at least one nonempty process field.
- 1,882 records, or 99.5%, have at least one measurement modality.
- 1,510 records, or 79.9%, have nonzero XRD availability.
- 1,403 records, or 74.2%, have composition, process metadata, and XRD availability.

The endpoint probe also shows that selected XRD-bearing sample libraries expose
position-resolved arrays:

- The sampled `prop` endpoint returned 44-position arrays for properties and spatial
  coordinates.
- The sampled `spectra` endpoint returned XRD arrays with 29,084 angle, measurement, and
  position values per selected sample library.
- One sampled optical payload contained 35,200 absorption/energy/position values.

## What Was Weakened

HTEM is still not a full material-making trajectory dataset.

- The primary public records are sample-library rows, not explicit synthesis-event logs.
- Process fields are mostly planned or summarized deposition metadata, not continuous
  process trajectories.
- Provenance is useful but incomplete: sample date plus person id are both present for
  66.1% of records.
- The public API endpoint named `count` appears to return records, and a rough
  `has_xrd=1` query returned the same number of records as the unfiltered endpoint. Treat
  API behavior as a public view, not a guaranteed ground-truth schema.
- Nonempty measurement availability does not prove the raw file is complete, comparable,
  or uniformly preprocessed.

## Verdict

HTEM is a good Track A bridge between opXRD and Track B, but not the destination.

It is useful for asking:

- Can we represent a sample library as many position-level measurement events rather than
  one static material row?
- Do process plus spatial coordinates help predict held-out spectra or properties?
- Do quality, availability, or phase-like labels behave like downstream projections rather
  than training targets?

It is not sufficient for the central Track B claim because it does not preserve the full
material-making event: planned conditions, observed process trajectory, raw measurement
files, failed measurements, operator/session/instrument context, and post-hoc labels as
separate layers.

## Track B Implications

For our own event dataset, we should separate fields that HTEM partially compresses
together:

- planned recipe variables,
- observed process trajectory,
- sample position and spatial context,
- raw measurement files,
- measurement availability and failed measurements,
- instrument/session/operator/date provenance,
- post-hoc human labels.

This audit supports the original direction: the public datasets are placeholders and
stress tests. They help us design the feedback loop, but they should not become the
ontology or the leaderboard.
