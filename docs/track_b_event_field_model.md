# Track B Event-Field Model

Generated with:

```bash
.venv/bin/python scripts/run_track_b_event_field_model.py \
  --output data/manifests/track_b_event_field_model.json
```

## Purpose

The progress-policy run showed that a single inferred or oracle 1D progress coordinate is
not enough. This run takes the next step without turning that lesson into a fixed
knowledge graph or named ontology.

Instead of training directly on phase labels or oracle acquisition labels, this run trains
a simple event-field model:

```text
partial event observations + candidate coordinates -> held-out raw measurement embedding
```

The model predicts PCA-compressed spectra for unobserved points in an event. Acquisition is
then derived from the model's random-forest ensemble variance.

The score remains raw held-out spectrum reconstruction. No phase, impurity, failure,
metastability, or hidden-regime label is used.

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
train event-field model on the other 3 regimes -> test field prediction and acquisition on
the held-out regime
```

Focused run settings:

- 3 seeds.
- 32 training events per training regime.
- 48 test events per held-out regime.
- 12 observations per event.
- Budgets 3, 4, 6, and 8.
- PCA target dimension 8.

## Hypotheses

H1: The event-field model should predict held-out measurement spectra better than a
train-mean PCA baseline.

H2: If field modeling is the smarter route, uncertainty-derived acquisition should beat
direct learned acquisition or space-filling in at least one hard held-out regime.

H3: If field prediction is good but uncertainty acquisition is weak, the bottleneck is
uncertainty calibration or acquisition planning, not whether event-field signal exists.

H4: If field prediction itself is weak, the next step should be a stronger event-field
model or richer process context, not another acquisition heuristic.

## Field-Prediction Diagnostic

Mean MSE improvement versus train-mean PCA target prediction:

| Held-Out Regime | Mean | Min | Max |
| --- | ---: | ---: | ---: |
| `abrupt_basin` | +31.7% | +30.0% | +32.9% |
| `random_axis` | +54.1% | +51.7% | +55.4% |
| `reversed_time` | +14.7% | +9.6% | +22.7% |

This validates that partial event observations contain predictive signal for missing raw
measurements, even across held-out synthetic regimes. The signal is strongest on
`random_axis`, useful on `abrupt_basin`, and weaker but still positive on `reversed_time`.

## Budget 8 Policy Results

Mean held-out raw-spectrum reconstruction MSE:

| Held-Out Regime | Space-Filling | Learned Forest | Field Uncertainty | Field Uncertainty + Coverage | Oracle Best |
| --- | ---: | ---: | ---: | ---: | ---: |
| `abrupt_basin` | 0.00890 | 0.00763 | 0.00917 | 0.00856 | 0.00553 |
| `random_axis` | 0.00390 | 0.00399 | 0.00448 | 0.00424 | 0.00281 |
| `reversed_time` | 0.00486 | 0.00428 | 0.00617 | 0.00496 | 0.00291 |

Improvement versus global-mean baseline:

| Held-Out Regime | Space-Filling | Learned Forest | Field Uncertainty | Field Uncertainty + Coverage | Oracle Best |
| --- | ---: | ---: | ---: | ---: | ---: |
| `abrupt_basin` | +39.2% | +43.9% | +36.2% | +40.1% | +54.9% |
| `random_axis` | +67.1% | +64.3% | +62.9% | +64.2% | +73.8% |
| `reversed_time` | +54.2% | +59.8% | +48.3% | +59.3% | +73.7% |

Best non-oracle methods by MSE:

| Held-Out Regime | Budget 3 | Budget 4 | Budget 6 | Budget 8 |
| --- | --- | --- | --- | --- |
| `abrupt_basin` | Active Hybrid | Space-Filling | Space-Filling | Learned Forest |
| `random_axis` | Active Hybrid | Space-Filling | Space-Filling | Space-Filling |
| `reversed_time` | Active Hybrid | Learned Forest | Space-Filling | Active Hybrid |

## Verdict

H1 is validated. The event-field model predicts missing measurement embeddings better than
a train-mean baseline in all held-out regimes.

H2 is not validated. Naive uncertainty acquisition does not beat direct learned
acquisition or space-filling in any consistent way. Adding a coverage multiplier helps, but
mostly makes the strategy approach simple coverage baselines rather than surpass them.

H3 is validated. The model has event-field signal, but random-forest ensemble variance is
not a sufficient acquisition rule.

H4 is not the right diagnosis for this run. Field prediction is not weak overall; the
weaker part is turning field prediction into action selection.

## Interpretation

This result is useful, but it is also a warning against spinning in place.

The productive result:

```text
Missing raw measurements are predictable from partial event context across held-out
synthetic regimes.
```

The negative result:

```text
"Measure the point the field model is most uncertain about" is not the same thing as
"measure the point that best improves reconstruction of the whole event."
```

So the next direction should not be more small tweaks to uncertainty scoring. That would
start to become optimization for its own sake.

The better interpretation is:

```text
Track B needs an event model first. Acquisition should be derived from expected improvement
to the event-level feedback objective, not from pointwise uncertainty alone.
```

## Next Direction

Move from pointwise uncertainty acquisition to masked event modeling:

```text
given a partially observed event, predict the missing event measurements
```

Then compare models by objective feedback:

- missing-spectrum reconstruction,
- held-out event transfer,
- robustness under regime/source shifts,
- and later active selection by expected reduction in whole-event reconstruction error.

This avoids fixing a hand-written relation graph. Relations among observations can be
learned inside the model, while the external objective remains raw/event prediction.

If the next masked event model only improves this synthetic benchmark without transferring
to HTEM-like or lab-like event data, we should stop treating the synthetic loop as evidence
and move more effort into real event data collection.
