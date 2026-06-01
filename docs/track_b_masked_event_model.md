# Track B Masked Event Model

Generated with:

```bash
.venv/bin/python scripts/run_track_b_masked_event_model.py \
  --output data/manifests/track_b_masked_event_model.json
```

## Purpose

The previous event-field run showed that missing measurements are predictable from partial
event context, but that pointwise uncertainty is a weak acquisition rule. This run removes
the acquisition step and tests the cleaner objective:

```text
given a partially observed event, predict missing raw measurements
```

No phase, impurity, failure, metastability, or hidden-regime label is used. Old labels are
still outside the training objective.

The neural model is a set-to-point masked event model:

```text
observed measurement tokens + candidate coordinate token -> missing spectrum embedding
```

The relation among observations is not a hand-written graph. It is internal to the set
encoder and judged only by raw measurement prediction.

## Setup

Regime pool:

```text
source_smooth, reversed_time, random_axis, abrupt_basin
```

Held-out regimes:

```text
reversed_time, random_axis, abrupt_basin
```

For each held-out regime:

```text
train on the other 3 regimes -> test on the held-out regime
```

Focused run settings:

- 2 seeds.
- 24 training events per training regime.
- 32 test events per held-out regime.
- 12 observations per event.
- Observed counts 2, 3, 4, 6, and 8.
- Random and space-filling observed masks.
- MPS device.

## Models

Baselines:

- `train_mean`
- `event_mean`
- `nearest_neighbor`
- `idw_all`
- `coordinate_ridge`
- `rf_event_field`

Neural variants:

- `masked_event_coord_only`: sees observed coordinates, but observed spectra are zeroed.
- `masked_event_raw_set`: predicts missing spectrum PCA directly from observed raw spectra.
- `masked_event_raw_residual`: predicts the residual over IDW interpolation.

The residual variant was added because IDW is a strong within-event baseline. This tests
whether the model learns what interpolation cannot already explain.

## Hypotheses

H1: A masked event model should predict missing raw measurement embeddings better than
train-mean PCA.

H2: `raw_set` should beat `coord_only` if observed spectra add event-specific signal.

H3: `raw_residual` should beat `raw_set` if the useful target is the part left unexplained
by interpolation.

H4: On full-spectrum reconstruction, the masked model should be competitive with IDW and
the engineered random-forest event-field baseline.

H5: If the neural masked model only beats train mean but loses to simple within-event
interpolation, the next move should be data/objective design rather than architecture
tuning.

## Target Diagnostic

Mean target-MSE improvement versus train-mean target prediction:

| Held-Out Regime | Coord Only | Raw Residual | Raw Set |
| --- | ---: | ---: | ---: |
| `abrupt_basin` | +0.5% | +23.5% | +30.1% |
| `random_axis` | -3.9% | -18.7% | +39.5% |
| `reversed_time` | -62.0% | +2.9% | +35.6% |

This validates H1 for `raw_set` and H2 strongly. Observed raw spectra carry event-specific
information that coord-only models do not recover. The residual target is not easier in PCA
space, especially for `random_axis`, but its full-spectrum reconstruction behavior is more
important because it is added back to IDW.

## Average Reconstruction

Average full-spectrum MSE across observed counts and mask strategies:

| Held-Out Regime | IDW | Coordinate Ridge | RF Event Field | Raw Set | Raw Residual |
| --- | ---: | ---: | ---: | ---: | ---: |
| `abrupt_basin` | 0.01254 | 0.01234 | 0.01133 | 0.01129 | **0.01042** |
| `random_axis` | 0.00631 | **0.00540** | 0.00589 | 0.00751 | 0.00750 |
| `reversed_time` | 0.00709 | **0.00574** | 0.01099 | 0.00834 | 0.00675 |

Average improvement versus event mean:

| Held-Out Regime | IDW | Coordinate Ridge | RF Event Field | Raw Set | Raw Residual |
| --- | ---: | ---: | ---: | ---: | ---: |
| `abrupt_basin` | +22.0% | +18.3% | +26.9% | +25.7% | **+32.6%** |
| `random_axis` | +29.6% | **+32.6%** | +29.7% | +10.6% | +10.4% |
| `reversed_time` | +29.9% | **+36.2%** | -12.7% | +12.3% | +27.2% |

Best-model win counts across 30 held-out/count/mask settings:

| Held-Out Regime | Coordinate Ridge | IDW | RF Event Field | Raw Set | Raw Residual |
| --- | ---: | ---: | ---: | ---: | ---: |
| `abrupt_basin` | 1 | 0 | 1 | 1 | **7** |
| `random_axis` | **5** | 0 | **5** | 0 | 0 |
| `reversed_time` | **4** | 3 | 0 | 0 | 3 |

## Verdict

H1 is validated for `raw_set`. Raw spectrum observations predict missing measurement
embeddings better than train-mean PCA in all held-out regimes.

H2 is strongly validated. `coord_only` is near zero on `abrupt_basin`, negative on
`random_axis`, and collapses on `reversed_time`. The raw observations are doing real work.

H3 is partially validated. `raw_residual` is usually better than `raw_set` for
full-spectrum reconstruction, especially on `abrupt_basin` and `reversed_time`. But it does
not solve `random_axis`.

H4 is partially validated. `raw_residual` is genuinely competitive and often best on
`abrupt_basin`; it is useful on `reversed_time`, especially random masks; it loses clearly
on `random_axis`.

H5 is the guardrail. We should not keep doing same-shape synthetic neural sweeps. The
current scaffold has too much coordinate/interpolation structure, especially on
`random_axis`.

## Interpretation

This is a better result than the uncertainty-acquisition run.

The positive result:

```text
Raw event observations matter, and residual-over-interpolation is a useful objective in
regimes where simple smooth interpolation is not enough.
```

The negative result:

```text
Some synthetic regimes are still solvable by coordinate geometry, RF features, or IDW.
```

So this does not justify a transformer race. It justifies the objective:

```text
masked event reconstruction, with strong interpolation baselines and residual targets
```

as the right computational assay for Track B.

## Next Direction

Do not keep tuning this exact synthetic benchmark locally. That would start becoming
optimization for its own sake.

The next useful move is to port this masked-event objective to less artificial event-like
data:

- HTEM within-library spatial fields,
- a lab pilot with repeated partial measurements per event,
- or a deliberately harder synthetic scaffold where coordinate interpolation is not
allowed to solve most of the task.

For active learning, wait until the masked event model is stronger on real/event-like data.
Then derive acquisition from expected reduction in whole-event reconstruction error, not
from pointwise uncertainty.
