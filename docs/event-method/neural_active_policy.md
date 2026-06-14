# Track B Neural Active Policy

Generated with:

```bash
.venv/bin/python scripts/run_track_b_neural_active_policy.py \
  --output data/manifests/track_b_neural_active_policy.json
```

## Purpose

This run asks whether a learned event-state encoder earns its complexity over the
previous random-forest acquisition policy.

The objective stays pre-taxonomic:

```text
partial raw event observations -> choose next observation -> improve held-out raw spectra
```

No phase label, failure label, impurity label, or hidden-regime label is used by the
policy.

## Hypotheses

H1: A neural set encoder should predict oracle acquisition targets better than a
train-mean baseline.

H2: The neural policy should beat random and naive active selection on held-out events.

H3: The neural policy must beat the random forest baseline before we treat added
architecture as useful.

## Architecture

The model is intentionally small:

```text
SetAcquisitionNet
```

Main pieces:

- 2-layer `TransformerEncoder` over observed `(coordinate, raw spectrum)` tokens.
- Spectrum MLP: raw 512-point spectrum to token embedding.
- Coordinate MLP: 2D observation coordinate to token embedding.
- Masked mean pooling over the currently observed event tokens.
- Candidate/state MLP over coordinate, budget/state, distance, and IDW-disagreement
  features.
- Acquisition head predicting one-step improvement in held-out reconstruction MSE.

Training target:

```text
oracle one-step reduction in held-out raw-measurement reconstruction MSE
```

The target exists in this synthetic scaffold because every event is fully observed. In a
real Track B dataset, the analogue would be learned from completed historical events and
then deployed on partial new events.

## Target Diagnostic

Across five seeds:

- 48 synthetic events per seed.
- 32 train events and 16 held-out test events per seed.
- 3,456 acquisition examples per seed.
- 1,728 held-out target examples per seed.
- The neural acquisition model improves target-prediction MSE by about 76.5% versus a
  train-mean target baseline.

Per-seed target MSE improvement:

| Seed | Improvement |
| ---: | ---: |
| 17 | 75.1% |
| 29 | 72.5% |
| 41 | 80.1% |
| 53 | 74.8% |
| 67 | 80.0% |

## Key Results

Mean over five seeds and 80 held-out event-policy runs per budget:

| Budget | Random MSE | Space-filling MSE | Naive active MSE | Forest MSE | Neural MSE | Oracle MSE |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 0.00815 | 0.00758 | 0.00758 | 0.00665 | 0.00668 | 0.00643 |
| 4 | 0.00767 | 0.00543 | 0.00750 | 0.00528 | 0.00524 | 0.00486 |
| 6 | 0.00707 | 0.00415 | 0.00841 | 0.00397 | 0.00420 | 0.00360 |
| 8 | 0.00676 | 0.00418 | 0.01087 | 0.00322 | 0.00318 | 0.00296 |

Improvement versus global-mean baseline:

| Budget | Random | Space-filling | Naive active | Forest | Neural | Oracle |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | +36.1% | +44.1% | +44.1% | +46.7% | +46.6% | +48.1% |
| 4 | +39.0% | +55.6% | +41.2% | +56.2% | +56.9% | +59.0% |
| 6 | +43.0% | +65.2% | +36.4% | +66.1% | +64.3% | +68.5% |
| 8 | +47.5% | +67.9% | +24.1% | +71.9% | +72.3% | +74.5% |

## Verdict

H1 is validated. The neural model predicts oracle acquisition improvement substantially
better than a train-mean target baseline, with about 76.5% target-MSE improvement.

H2 is validated. The deployed neural policy beats random and the naive active heuristic at
every budget.

H3 is partially validated. The neural policy is competitive with the random forest and
beats it at budgets 4 and 8, but loses very slightly at budget 3 and more noticeably at
budget 6. It is also not uniformly better than static space-filling, because space-filling
slightly wins at budget 6.

So the honest ordering is:

```text
random and naive active lag; space-filling is strong; forest ~= neural set encoder < oracle
```

with the caveat that the neural policy has the best score among non-oracle methods at
budgets 4 and 8, but not at every budget.

## Interpretation

This is a real but modest architecture win.

The neural model is not merely sounding more modern: it predicts the acquisition target
better than the simpler forest and can match or slightly beat the forest after deployment.
But the deployment advantage is not large enough to declare the transformer-style event
encoder the obvious next default.

The useful lesson is narrower and cleaner:

> Learned event-state policies are viable, but architecture only matters when it improves
> the raw feedback loop.

That keeps the project aligned with the Bitter Lesson framing. The model is judged by
whether it converts partial observations into better next measurements, not by whether its
latent space is easy to name.

## Next Direction

The next neural-policy work should stress whether the model is learning event state or
leaning on engineered scalar shortcuts:

1. Run ablations with and without the candidate/state scalar features.
2. Test transfer across synthetic regimes, not just held-out events from the same
   generator.
3. Compare policies under counterbalanced provenance shifts.
4. Scale only after these stress tests show that the learned set representation transfers
   better than the forest.

Do not turn this into a transformer leaderboard. The active-loop objective is the point.
