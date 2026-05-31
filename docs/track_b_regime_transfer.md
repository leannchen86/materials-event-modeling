# Track B Regime Transfer

Generated with:

```bash
.venv/bin/python scripts/run_track_b_regime_transfer.py \
  --output data/manifests/track_b_regime_transfer.json
```

## Purpose

The previous ablation showed that raw observed spectra help in the source synthetic
scaffold. This run asks the harder question:

```text
Does a learned acquisition policy trained on one event-world transfer to shifted
event-worlds where coordinate/spatial shortcuts may break?
```

The policy is still judged only by raw held-out measurement reconstruction. No phase,
failure, impurity, or hidden-regime label is used.

## Setup

Train regime:

```text
source_smooth
```

Test regimes:

| Regime | Shift |
| --- | --- |
| `matched_smooth` | Same smooth x-forward event world, new events |
| `reversed_time` | Conversion runs in the opposite x direction |
| `random_axis` | Event progress follows a random 2D axis per event |
| `abrupt_basin` | Sharp competing-basin discontinuity across the event field |

Policies tested:

- `full_neural`: raw observed-spectrum set plus full engineered scalar features.
- `scalar_full`: full engineered scalar features, no observed raw-spectrum set.
- `set_basic`: raw observed-spectrum set plus only candidate coordinate and budget state.
- `candidate_set_basic`: candidate token attends to raw observed-spectrum tokens.
- `coords_basic`: coordinate set plus candidate coordinate and budget state.
- `learned_forest`: previous random-forest acquisition policy.
- `space_filling`, `active_hybrid`, `random`, and `oracle_best` baselines.

## Hypotheses

H1: `matched_smooth` transfer should resemble the previous in-distribution ablation.

H2: Coordinate/scalar shortcuts should weaken under `reversed_time`, `random_axis`, and
`abrupt_basin`.

H3: If raw event-state learning is more than a shortcut, raw-spectrum set variants should
retain more target-prediction and policy value than `scalar_full` and `coords_basic` under
shifted regimes.

H4: If all learned policies collapse toward space-filling under shift, the next step
should be mixed-regime training or richer event context, not tuning the same architecture.

## Target Diagnostic

Mean oracle-target MSE improvement versus train-mean baseline:

| Test Regime | Full Neural | Candidate Set | Set Basic | Scalar Full | Coords Basic |
| --- | ---: | ---: | ---: | ---: | ---: |
| `matched_smooth` | +78.9% | +78.5% | +78.7% | +58.4% | +53.8% |
| `abrupt_basin` | +18.9% | +22.6% | +21.3% | +15.1% | +8.0% |
| `random_axis` | -38.8% | -53.4% | -91.1% | -13.6% | -10.6% |
| `reversed_time` | -148.3% | -203.7% | -346.1% | -15.2% | +24.8% |

This is the sharpest result. Raw-spectrum set models keep a large target advantage on
matched smooth and a smaller but real advantage on abrupt competing basins. But they fail
badly when the process coordinate is reversed or randomly rotated relative to training.

## Budget 8 Policy Results

Mean held-out raw-spectrum reconstruction MSE:

| Test Regime | Space-Filling | Forest | Scalar Full | Coords Basic | Set Basic | Candidate Set | Full Neural | Oracle |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `matched_smooth` | 0.00419 | 0.00347 | 0.00363 | 0.00332 | 0.00329 | 0.00329 | 0.00330 | 0.00305 |
| `abrupt_basin` | 0.00887 | 0.00781 | 0.00820 | 0.00892 | 0.00851 | 0.00852 | 0.00871 | 0.00545 |
| `random_axis` | 0.00378 | 0.00388 | 0.00440 | 0.00464 | 0.00543 | 0.00505 | 0.00478 | 0.00278 |
| `reversed_time` | 0.00488 | 0.00369 | 0.00357 | 0.00329 | 0.01202 | 0.00905 | 0.00876 | 0.00292 |

Improvement versus global-mean baseline:

| Test Regime | Space-Filling | Forest | Scalar Full | Coords Basic | Set Basic | Candidate Set | Full Neural | Oracle |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `matched_smooth` | +66.1% | +69.5% | +68.0% | +69.6% | +70.6% | +70.4% | +70.2% | +72.1% |
| `abrupt_basin` | +37.4% | +43.3% | +41.8% | +37.9% | +40.4% | +40.4% | +39.2% | +54.8% |
| `random_axis` | +67.8% | +66.0% | +61.2% | +59.7% | +49.5% | +55.6% | +56.9% | +74.0% |
| `reversed_time` | +54.3% | +66.2% | +67.6% | +69.9% | +16.3% | +29.9% | +27.3% | +73.6% |

Best non-oracle methods by MSE:

| Test Regime | Budget 3 | Budget 4 | Budget 6 | Budget 8 |
| --- | --- | --- | --- | --- |
| `matched_smooth` | Forest | Candidate Set | Candidate Set | Candidate Set |
| `abrupt_basin` | Candidate Set | Space-Filling | Forest | Forest |
| `random_axis` | Active Hybrid | Space-Filling | Space-Filling | Space-Filling |
| `reversed_time` | Scalar Full | Coords Basic | Space-Filling | Coords Basic |

## Verdict

H1 is validated. Matched-smooth transfer reproduces the previous story: raw-spectrum set
variants are strong, and `candidate_set_basic` is the best non-oracle policy at budgets 4,
6, and 8.

H2 is partially validated. Coordinate/scalar shortcuts do weaken in some shifted regimes,
especially abrupt basin for `coords_basic`. But they do not universally weaken:
`coords_basic` wins reversed-time at budgets 4 and 8, because the reversed world still has
a coherent coordinate structure.

H3 is only partially validated. Raw-spectrum set variants transfer better than scalar-only
or coordinate-only on matched smooth and target prediction for abrupt basin. But they do
not survive random-axis or reversed-time shift. In those regimes, raw-spectrum policies
trained only on source-smooth learn the wrong acquisition geometry.

H4 is validated. Under process-coordinate shifts, the right next step is not more tuning
on the same source-smooth scaffold. The model needs either mixed-regime training, explicit
process-coordinate uncertainty, or richer event context that lets it infer the event's
actual progress axis.

## Interpretation

This is a productive negative result.

The learned raw-event policy is not fake: it works well in matched transfer and keeps some
signal in abrupt competing-basin fields. But it is not yet Bitter-Lesson-robust. It has
learned a useful policy inside a world where the meaning of coordinates is stable. When the
meaning of coordinates changes, the raw set encoder is not magically invariant.

That matters for the real lab design. A real material-making event dataset should not only
log coordinates or time stamps; it should log enough process context to let a model infer
which axes are actually meaningful:

- time/order of operation,
- spatial position,
- mixing path,
- sampling order,
- batch/session/provenance,
- precursor and additive trajectory,
- instrument and measurement timing.

The next computational step should train on multiple synthetic event worlds and test on a
held-out world:

```text
mixed-regime training -> held-out-regime acquisition
```

If raw-event policies recover under mixed training, that suggests scaling diversity of
material-making events matters more than squeezing a single synthetic ontology.
