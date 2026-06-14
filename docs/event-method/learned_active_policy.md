# Track B Learned Active Policy

Generated with:

```bash
.venv/bin/python scripts/run_track_b_learned_active_policy.py \
  --output data/manifests/track_b_learned_active_policy.json
```

## Purpose

This run moves from hand-written active heuristics to a learned event-native acquisition
policy:

```text
past fully observed events -> train acquisition model -> choose next observation in a new
partially observed event
```

The objective is raw measurement feedback. No phase labels, success/failure labels,
impurity labels, or hidden regimes are used by the policy.

## Architecture

This is intentionally simple:

```text
RandomForestRegressor
```

Model settings:

- 250 trees,
- max depth 8,
- minimum leaf size 3.

Input features:

- candidate coordinate,
- current observation budget/state,
- distance from candidate to observed points,
- IDW prediction disagreement,
- observed-spectrum mean/std summaries,
- PCA summaries of the currently observed spectra.

Target:

```text
oracle one-step reduction in held-out raw-measurement reconstruction MSE
```

That target is available in the synthetic scaffold because all observations are known. In
real data, the analogue would come from completed historical events.

## Hypotheses

H1: A learned acquisition regressor should predict oracle improvement better than a
train-mean target baseline.

H2: A learned policy should beat the naive active heuristic and random selection on
held-out events.

H3: If the learned policy cannot beat space-filling, the current state representation is
not strong enough yet.

## Training Diagnostic

Across five seeds:

- 48 synthetic events per seed.
- 32 train events and 16 held-out test events per seed.
- 3,456 acquisition examples per seed.
- The acquisition regressor improves oracle-target MSE by about 59-63% versus a train-mean
  target baseline.

## Key Results

Mean over five seeds and 80 held-out event-policy runs per budget:

| Budget | Random MSE | Space-filling MSE | Naive active MSE | Learned forest MSE | Oracle MSE |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 0.00815 | 0.00758 | 0.00758 | 0.00665 | 0.00643 |
| 4 | 0.00767 | 0.00543 | 0.00750 | 0.00528 | 0.00486 |
| 6 | 0.00707 | 0.00415 | 0.00841 | 0.00397 | 0.00360 |
| 8 | 0.00676 | 0.00418 | 0.01087 | 0.00322 | 0.00296 |

Improvement versus global-mean baseline:

| Budget | Random | Space-filling | Naive active | Learned forest | Oracle |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | +36.1% | +44.1% | +44.1% | +46.7% | +48.1% |
| 4 | +39.0% | +55.6% | +41.2% | +56.2% | +59.0% |
| 6 | +43.0% | +65.2% | +36.4% | +66.1% | +68.5% |
| 8 | +47.5% | +67.9% | +24.1% | +71.9% | +74.5% |

Improvement versus event-mean baseline:

| Budget | Random | Space-filling | Naive active | Learned forest | Oracle |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | +19.3% | +29.4% | +29.4% | +30.4% | +32.5% |
| 4 | +22.9% | +29.7% | +24.8% | +31.4% | +36.8% |
| 6 | +28.8% | +38.1% | +25.6% | +40.5% | +45.6% |
| 8 | +32.9% | +39.2% | +32.0% | +44.3% | +49.7% |

## Verdict

H1 is validated. The acquisition model predicts oracle one-step improvement substantially
better than a train-mean target baseline.

H2 is validated. The learned forest beats random and the naive active heuristic on held-out
events across all tested budgets.

H3 is also answered positively. The learned forest beats static space-filling at budgets
4, 6, and 8, and is close at budget 3. It does not beat oracle, which is exactly the
healthy ordering:

```text
random < naive active < space-filling < learned forest < oracle
```

with a small nuance that space-filling and learned forest are close at the smallest budget.

## Interpretation

This is the first actual learned feedback-loop win in Track B.

The policy is not learning a phase label. It is learning:

> Given what I have already observed inside this material-making event, where should I ask
> reality for the next measurement to improve raw event reconstruction?

That is much closer to the project's north star than label prediction.

The result also explains why the previous heuristic active policy failed. The problem was
not active learning itself; the hand-written uncertainty score was too crude. A learned
policy can combine coverage, current event state, spectral summaries, and candidate
position better than the heuristic.

## Next Direction

The next active-policy step should increase representational ambition without losing the
objective:

1. Replace tabular handcrafted features with a learned event-state encoder.
2. Train the acquisition policy end-to-end or semi-end-to-end.
3. Test transfer to different synthetic field regimes.
4. Later, train on completed real events and deploy on partially observed real events.

Candidate architecture for the next step:

```text
set/transformer event encoder over observed (coordinate, spectrum) pairs
+ candidate coordinate encoder
+ acquisition head predicting expected reconstruction improvement
```

But do not rush there just to use transformers. The current forest is a strong baseline.
The neural model must beat it, not merely sound more modern.

## Caveat

This is synthetic. The learned target uses full observation knowledge that only exists in
completed historical or simulated events. The real version requires completed events first,
then the learned policy can be used on new partial events.

