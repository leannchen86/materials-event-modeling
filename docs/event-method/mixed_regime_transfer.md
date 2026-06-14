# Track B Mixed-Regime Transfer

Generated with:

```bash
.venv/bin/python scripts/run_track_b_mixed_regime_transfer.py \
  --output data/manifests/track_b_mixed_regime_transfer.json
```

## Purpose

The previous regime-transfer run trained policies only on `source_smooth` and showed a
productive failure: raw-spectrum set policies worked in matched transfer but collapsed
under `random_axis` and `reversed_time` shifts.

This run tests the next hypothesis:

```text
If narrow source-world training caused the collapse, training on multiple event-worlds
should improve held-out-regime acquisition.
```

The score remains raw held-out measurement reconstruction. No phase, impurity, failure, or
hidden-regime label is used.

## Setup

Regime pool:

```text
source_smooth, reversed_time, random_axis, abrupt_basin
```

Held-out regimes:

```text
reversed_time, random_axis, abrupt_basin
```

For each held-out regime, the policies train on the other regimes:

```text
train on 3 regimes -> test on the held-out regime
```

This was a focused run:

- 3 seeds.
- 32 training events per training regime.
- 48 test events per held-out regime.
- 60 epochs.
- 4 neural/scalar variants plus forest and sampling baselines.

## Hypotheses

H1: Mixed-regime training should improve held-out `random_axis` and `reversed_time`
transfer relative to source-smooth-only training.

H2: Raw-spectrum variants should recover more target-prediction signal under held-out
regimes if event diversity was the missing ingredient.

H3: If coordinate/scalar variants still dominate, the task remains solvable through
process-coordinate shortcuts and needs richer event-context inference.

H4: If learned policies remain far behind space-filling or oracle, the next step should be
explicit progress-axis inference rather than architecture tuning.

## Target Diagnostic

Mean oracle-target MSE improvement versus train-mean target baseline:

| Held-Out Regime | Candidate Set | Full Neural | Coords Basic | Scalar Full |
| --- | ---: | ---: | ---: | ---: |
| `abrupt_basin` | +12.6% | +9.5% | +9.4% | +0.4% |
| `random_axis` | -26.7% | -16.6% | -5.7% | -31.5% |
| `reversed_time` | -9.4% | -34.1% | -0.2% | -55.3% |

Compared with source-smooth-only training, mixed-regime training changed target
prediction like this:

| Held-Out Regime | Candidate Set Delta | Full Neural Delta | Coords Basic Delta | Scalar Full Delta |
| --- | ---: | ---: | ---: | ---: |
| `abrupt_basin` | -10.0 pp | -9.4 pp | +1.3 pp | -14.7 pp |
| `random_axis` | +26.7 pp | +22.1 pp | +5.0 pp | -18.0 pp |
| `reversed_time` | +194.3 pp | +114.2 pp | -24.9 pp | -40.1 pp |

Interpretation: mixed training does reduce the raw-event collapse on `random_axis` and
especially `reversed_time`, but it does not recover positive target prediction for the
raw-spectrum variants.

## Budget 8 Policy Results

Mean held-out raw-spectrum reconstruction MSE:

| Held-Out Regime | Space-Filling | Forest | Scalar Full | Coords Basic | Candidate Set | Full Neural | Oracle |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `abrupt_basin` | 0.00890 | 0.00763 | 0.00857 | 0.00899 | 0.00898 | 0.00813 | 0.00553 |
| `random_axis` | 0.00390 | 0.00399 | 0.00389 | 0.00467 | 0.00465 | 0.00401 | 0.00281 |
| `reversed_time` | 0.00486 | 0.00428 | 0.00375 | 0.00328 | 0.00652 | 0.00503 | 0.00291 |

Improvement versus global-mean baseline:

| Held-Out Regime | Space-Filling | Forest | Scalar Full | Coords Basic | Candidate Set | Full Neural | Oracle |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `abrupt_basin` | +39.2% | +43.9% | +40.1% | +39.4% | +39.2% | +41.8% | +54.9% |
| `random_axis` | +67.1% | +64.3% | +65.8% | +59.5% | +60.0% | +64.5% | +73.8% |
| `reversed_time` | +54.2% | +59.8% | +66.8% | +70.0% | +42.7% | +57.7% | +73.7% |

Best non-oracle methods by MSE:

| Held-Out Regime | Budget 3 | Budget 4 | Budget 6 | Budget 8 |
| --- | --- | --- | --- | --- |
| `abrupt_basin` | Candidate Set | Coords Basic | Space-Filling | Forest |
| `random_axis` | Active Hybrid | Coords Basic | Coords Basic | Scalar Full |
| `reversed_time` | Active Hybrid | Forest | Space-Filling | Coords Basic |

## Verdict

H1 is partially validated. Mixed-regime training improves the raw-spectrum variants on the
hardest previous failures, especially `reversed_time`, where `candidate_set_basic` target
prediction improves by about 194 percentage points relative to source-only training. But
the recovered target scores are still not positive.

H2 is partially validated but not enough. Raw-spectrum variants recover some signal under
mixed training, but they do not become the best held-out-regime policies.

H3 is validated. Coordinate/scalar variants still dominate several held-out policy
settings. `coords_basic` wins `reversed_time` at budget 8, and `scalar_full` wins
`random_axis` at budget 8. The problem is not solved by raw spectra plus regime diversity.

H4 is validated. The next step should be explicit event-progress inference, not more
architecture tuning on the same acquisition head.

## Interpretation

Mixed-regime training helps, but it does not solve transfer.

The important nuance:

```text
Source-only raw-event policies failed because they learned a brittle acquisition geometry.
Mixed-regime training makes that brittleness less severe.
But the model still lacks a native mechanism for inferring which process axis matters in
the current event.
```

That is a strong design lesson for the real Track B dataset. We should not just log raw
XRD and coordinates. We need event context that lets models infer progress:

- observation order,
- sampling time,
- spatial position,
- operation sequence,
- mixing path,
- measurement timing,
- batch/session context,
- process perturbations.

The next computational direction should make this explicit:

```text
infer latent event progress/geometry from partial observations
then condition acquisition on that inferred progress state
```

This is still aligned with the project philosophy. We are not adding old material labels
as ground truth. We are adding a better feedback-loop variable: how the material-making
event unfolds.
