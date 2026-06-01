# Track B Progress Policy

Generated with:

```bash
.venv/bin/python scripts/run_track_b_progress_policy.py \
  --output data/manifests/track_b_progress_policy.json
```

## Purpose

The mixed-regime transfer run suggested that raw-event policies still lack a mechanism for
inferring event progress or geometry. This run tests the simplest version of that idea:

```text
infer or provide a 1D event-progress coordinate
then train an acquisition policy on progress-space features
```

The policy is still scored by raw held-out spectrum reconstruction. No phase, impurity,
failure, or hidden-regime label is used.

## Policies

`latent_progress_forest`:

- Infers a 1D progress coordinate from partial observations.
- Method: take dominant observed spectral-change score with SVD/PCA, then regress that
  score onto observed 2D coordinates.
- Uses progress-space distances, 1D progress IDW disagreement, observed spectrum summaries,
  and progress gap features.

`oracle_progress_forest`:

- Same policy class and features.
- Uses synthetic hidden `event_progress` as an upper-bound coordinate.
- This is not a real deployable policy; it asks whether progress alone would be enough if
  we knew it.

Baselines:

- `learned_forest`: coordinate/PCA acquisition forest from prior runs.
- `space_filling`, `active_hybrid`, `random`, and `oracle_best`.

## Hypotheses

H1: Oracle progress should improve held-out `random_axis` and `reversed_time` acquisition
if event progress geometry is useful.

H2: Latent progress should close part of the gap to oracle progress if the hidden progress
axis can be inferred from partial raw spectra.

H3: If oracle progress helps but latent progress does not, progress inference is the
bottleneck rather than acquisition scoring.

H4: If neither progress policy helps, event progress alone is insufficient under the
current reconstruction objective.

## Target Diagnostic

Mean oracle-target MSE improvement versus train-mean target baseline:

| Held-Out Regime | Latent Progress | Oracle Progress |
| --- | ---: | ---: |
| `abrupt_basin` | +2.4% | +6.6% |
| `random_axis` | -0.7% | -5.0% |
| `reversed_time` | -46.0% | -52.6% |

This is the most important result. Even true synthetic progress is not enough to predict
oracle acquisition improvement robustly.

## Budget 8 Policy Results

Mean held-out raw-spectrum reconstruction MSE:

| Held-Out Regime | Space-Filling | Learned Forest | Latent Progress | Oracle Progress | Oracle Best |
| --- | ---: | ---: | ---: | ---: | ---: |
| `abrupt_basin` | 0.00890 | 0.00763 | 0.00979 | 0.00851 | 0.00553 |
| `random_axis` | 0.00390 | 0.00399 | 0.00447 | 0.00391 | 0.00281 |
| `reversed_time` | 0.00486 | 0.00428 | 0.00396 | 0.00398 | 0.00291 |

Improvement versus global-mean baseline:

| Held-Out Regime | Space-Filling | Learned Forest | Latent Progress | Oracle Progress | Oracle Best |
| --- | ---: | ---: | ---: | ---: | ---: |
| `abrupt_basin` | +39.2% | +43.9% | +30.2% | +37.9% | +54.9% |
| `random_axis` | +67.1% | +64.3% | +58.4% | +64.1% | +73.8% |
| `reversed_time` | +54.2% | +59.8% | +64.1% | +63.5% | +73.7% |

Best non-oracle methods by MSE:

| Held-Out Regime | Budget 3 | Budget 4 | Budget 6 | Budget 8 |
| --- | --- | --- | --- | --- |
| `abrupt_basin` | Active Hybrid | Space-Filling | Space-Filling | Learned Forest |
| `random_axis` | Oracle Progress | Space-Filling | Oracle Progress | Space-Filling |
| `reversed_time` | Active Hybrid | Learned Forest | Space-Filling | Latent Progress |

## Verdict

H1 is only weakly validated. `oracle_progress_forest` helps in a few cases, especially
`random_axis` at budgets 3 and 6, but it does not dominate `space_filling` or
`learned_forest`. True 1D progress is not a sufficient acquisition coordinate.

H2 is weakly validated at one point and mostly not validated. `latent_progress_forest`
wins `reversed_time` at budget 8, but it does not close a consistent gap to oracle
progress and its target prediction is poor.

H3 is not the right diagnosis. Since oracle progress itself is weak, the main bottleneck
is not merely inferring the progress scalar.

H4 is validated. A single progress coordinate is insufficient under the current objective.
The event geometry that matters for acquisition is richer than one monotonic axis.

## Interpretation

This is a useful falsification.

The previous result said:

```text
The model needs event-progress or geometry inference.
```

This run refines that:

```text
Not just a 1D progress scalar.
```

Why? The acquisition decision is not only "where am I along progress?" It also depends on:

- local spatial coverage,
- competing basins,
- discontinuities,
- how spectra change across nearby positions,
- whether the reconstruction model can use the chosen observation,
- and whether progress is monotonic, folded, reversed, or multi-axis.

So the next geometry should be relational, not scalar.

## Next Direction

Move from:

```text
infer scalar progress z
```

to:

```text
learn an event field from partial observations
```

This should not become a hand-written relation graph or a new symbolic ontology. The
relations among observations should be learned through objective feedback, such as missing
raw-measurement prediction and whole-event reconstruction.

Concretely, the next experiment should first model:

- candidate measurements from partial event context,
- local coverage and observed-state summaries,
- changes in spectra across the event,
- and reconstruction-aware value.

In research terms:

> The unit is not only a material-making event; it is the feedback field inside the event.
