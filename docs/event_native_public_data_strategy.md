# Event-Native Public Data Strategy

## Updated Thesis

Anubhav Jain's reply calibrates the problem well:

```text
experimental data sets are typically scattered/unavailable, lack metadata, and lack clear
metrics/problems on which to judge new ideas.
```

So Track B should not start by claiming that a new neural architecture solves materials
discovery. The sharper claim is:

```text
Materials AI lacks public event-native datasets and clear tasks for testing whether raw
experimental feedback improves learning beyond compressed final results.
```

That makes the first research object a benchmark frame, not a model leaderboard.

## What Counts As Event-Native

An event-native dataset should preserve enough of the attempt to support objective
feedback tasks without making final labels the organizing backbone.

Minimum useful fields:

- planned conditions or recipe,
- time-indexed or position-indexed raw observations,
- raw file references rather than only processed summaries,
- repeated events under similar planned conditions,
- failed, partial, and ambiguous attempts,
- provenance such as source, instrument/session, run order, and operator/batch when
  available,
- final labels/properties only as probes after raw data is saved.

This is still a compression of reality. The goal is not perfect recording. The goal is
to preserve high-bandwidth feedback before it is collapsed into a final label or property.

## Existing Data First

Before collecting a new dataset, try to convert public datasets into:

```text
event_id -> conditions -> time/space-indexed observations -> final labels/annotations
```

Then ask:

- Can partial traces predict future traces?
- Can raw observations outperform final-label or recipe-only baselines?
- Do labels split or merge in a learned latent space?
- Do source, instrument, session, or processing shortcuts dominate?
- Which required fields are missing for event learning?

A negative result is useful if it says:

```text
This dataset has raw observations, but its structure cannot support event-native learning.
```

That is evidence for the gap, not failure.

## When To Collect Our Own

Collect new data only when public data lacks something structurally necessary:

- no time sequence, only final images,
- no failed or ambiguous attempts,
- no process variables,
- no repeated same-recipe events,
- no raw files, only processed summaries,
- no intervention or control history,
- no environmental context,
- labels are required as the main organizing key,
- provenance is missing,
- data access or license blocks reuse.

The reason to collect our own should be:

```text
we need the dataset to be designed around event-learning tasks from the beginning.
```

Not:

```text
nobody has ever studied this physical system.
```

## First Benchmark Target

The best first task is likely:

```text
early event trace -> future event trace or final raw observation
```

Strong baselines:

- recipe/condition-only,
- final-label-only when labels exist,
- source/provenance-only,
- nearest neighbor in recipe space,
- interpolation or simple physical summary when a time/space grid exists,
- frozen image embeddings plus a small temporal head.

Possible snap-result:

```text
With only the first 20% of the event trace, raw observations predict the final pattern
better than the recipe or final human label.
```

Possible negative snap-result:

```text
The public dataset has images and labels, but no repeated recipes or process trail, so it
cannot test whether event traces beat compressed labels.
```

## Candidate Order

1. Durham IPA droplet evaporation dataset.
   Small, open, includes videos and spreadsheets, and records controlled humidity. This is
   the best first audit target for early-trace prediction.

2. MARCO protein crystallization images.
   Large, public, source-labeled image classification dataset. Useful as a compression
   negative control: many images and labels, but likely not a full time/process event log.

3. VMXi crystallization micrographs.
   Useful for label disagreement because expert agreement metadata exists. Large download,
   more final-image shaped than event-trace shaped.

4. OpenCrystalData.
   Useful process-analytical-technology image resource for crystallization. Audit whether
   it has sequences, raw instrument context, and repeated process conditions.

5. Dryad gelation active-learning dataset.
   Useful because it comes from an active-learning experimental workflow and may preserve
   raw/processed data plus response surfaces.

6. HTEM DB.
   Already audited as an event-proxy bridge. It supports spatial measurement fields but
   not full material-making trajectories.

## Immediate Decision Rule

For each dataset, produce a small audit manifest before any model run:

```text
Can this dataset support early-trace -> future-outcome prediction?
If yes, run the smallest honest benchmark.
If no, document exactly why not and convert that failure into a design requirement for a
small gold dataset.
```
