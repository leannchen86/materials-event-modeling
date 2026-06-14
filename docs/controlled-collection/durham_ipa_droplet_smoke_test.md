# Durham IPA Droplet Smoke Test

Source dataset:

```text
Evaporation of alcohol droplets on surfaces in moist air
https://collections.durham.ac.uk/files/r12801pg44n
```

Run:

```bash
.venv/bin/python scripts/run_durham_droplet_smoke_test.py \
  --output data/manifests/durham_ipa_droplet_smoke_test.json
```

## Hypothesis

If the released videos contain usable event traces, early video-derived signals should
predict late trace summaries better than condition metadata alone.

Expected nuance:

- A positive result would only be a smoke-test signal because there are only 9 videos.
- A negative or metadata-dominated result would still be useful because it would show that
  the released dataset cannot cleanly separate raw event signal from condition/provenance
  shortcuts.

## Setup

Each video is decoded with `ffmpeg`, resized to 64x64 grayscale frames, and converted into
a 64-step normalized event trace.

Per-frame trace features:

- mean intensity,
- intensity standard deviation,
- 5th/50th/95th intensity quantiles,
- contrast,
- edge energy,
- dark pixel fraction,
- bright pixel fraction.

Task:

```text
first 25% of trace -> last 25% trace summary
```

Evaluation:

- leave-one-video-out,
- target values standardized inside each training fold,
- report MSE/MAE versus a train-mean baseline.

Baselines:

- train mean,
- metadata ridge,
- metadata nearest neighbor,
- early-trace ridge,
- early-trace nearest neighbor,
- early trace plus metadata ridge,
- copy early summary as late summary.

## Result

| Model | MSE | MSE Improvement Vs Mean | MAE Improvement Vs Mean |
| --- | ---: | ---: | ---: |
| train mean | 2.211 | 0.0% | 0.0% |
| metadata ridge | 1.535 | 30.6% | 30.5% |
| metadata nearest neighbor | 1.413 | 36.1% | 38.0% |
| early-trace ridge | 1.853 | 16.2% | 26.2% |
| early-trace nearest neighbor | 1.477 | 33.2% | 37.1% |
| early trace plus metadata ridge | 1.863 | 15.7% | 25.7% |
| copy early summary | 3.580 | -61.9% | 9.9% |

## Verdict

The result partially validates the event-trace idea, but does not validate the stronger
claim.

What validated:

- early video-derived traces contain signal,
- a raw-trace nearest-neighbor baseline improves MSE by about 33% versus train mean,
- copying the early summary fails, so the task is not just static-frame similarity.

What did not validate:

- early trace did not beat metadata-only baselines,
- adding early trace to metadata did not improve ridge performance,
- the dataset cannot cleanly separate event signal from condition/provenance shortcuts.

## Interpretation

This is a useful negative result.

The dataset is event-like enough to build the first benchmark task, but it is too small
and too condition-coded to be decisive. With only 9 videos, the metadata fields are nearly
an event identifier:

```text
humidity + nozzle + trace-particle condition
```

That means the benchmark cannot yet answer the main question:

```text
Do raw event traces preserve useful learning signal beyond compressed condition labels?
```

It can only say:

```text
The task is implementable, but public figure-shaped data hits a ceiling quickly.
```

## Next Decision

This result argues against more architecture tuning on Durham.

Better next moves:

- audit a larger public dataset to see whether it has many repeated event traces,
- ask authors/labs whether unreleased repeated movies and per-event logs exist,
- design a small gold dataset where repeats, failures, provenance, and raw traces are
  recorded from the start.

For our research direction, the important finding is not that early-trace ridge lost. The
important finding is that a dataset can contain raw videos and still fail to support the
causal/benchmark question because it lacks repeated, fully logged events.
