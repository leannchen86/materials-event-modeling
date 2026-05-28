# Track B Synthetic Event Scaffold

## Purpose

This scaffold is not a chemistry result. It is a pre-lab computational test that asks
whether our Track B analysis logic can handle the kind of data we want to collect:
event histories, raw measurements, replicate structure, missing fields, and downstream
labels that may be lossy projections.

The synthetic world deliberately includes hidden process regimes. We use those hidden
regimes only because this is a scaffold; real Track B data will not have them.

Generated with:

```bash
.venv/bin/python scripts/run_track_b_synthetic_scaffold.py --output data/manifests/track_b_synthetic_event_scaffold.json
```

## Hypotheses

H1: Event-process features should predict held-out synthetic spectra better than
label-only features.

H2: Replicate retrieval should improve when using event-process or raw-measurement
features instead of labels alone.

H3: Legacy labels should split across multiple hidden regimes, showing that labels are
lossy projections in this synthetic world.

## Result

Dataset:

- 96 synthetic events.
- 32 replicate groups.
- 512-point synthetic XRD-like measurements.
- Labels are downstream projections, not training targets.

Held-out spectrum prediction:

| Feature view | MSE improvement vs train mean | MSE |
| --- | ---: | ---: |
| Label only | 36.7% | 0.00791 |
| Coarse planned process | 28.3% | 0.00895 |
| Event process | 58.0% | 0.00525 |

Replicate retrieval hit rate:

| Feature view | Hit rate |
| --- | ---: |
| Label only | 13.5% |
| Coarse planned process | 39.6% |
| Event process | 12.5% |
| Raw measurement PCA | 71.9% |

Label projection audit:

- Labels that split across hidden regimes:
  `delayed_conversion_possible`, `mixed_or_impure`, `possible_mixture`, `reference_like`.
- Spectral silhouette for hidden regimes: 0.784.
- Spectral silhouette for legacy labels: 0.026.

Missingness:

- `final_ph`: 23 events.
- `early_turbidity`: 9 events.

## Verdict

H1 validated. Event-process features predict held-out synthetic spectra better than
label-only features.

H2 partially validated. Raw measurement PCA retrieves replicates strongly, and coarse
planned-process features beat labels. Full event-process features do not retrieve
replicates well, probably because noisy observed trajectory fields distinguish replicates
rather than grouping them.

H3 validated. Several inherited labels split across hidden regimes, and hidden regimes are
much more compact in spectral space than legacy labels.

## Design Lesson

The scaffold exposed an important Track B design issue: planned conditions and observed
trajectory fields should probably be represented separately.

Examples:

- planned condition view: target temperature, intended aging time, planned additive level,
  planned mixing mode;
- observed trajectory view: measured pH, turbidity, deviations, actual temperature,
  operator notes.

For real data, replicate retrieval may be better evaluated on planned-condition embeddings,
while held-out measurement prediction may need observed trajectory embeddings.
