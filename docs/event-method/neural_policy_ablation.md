# Track B Neural Policy Ablation

Generated with:

```bash
.venv/bin/python scripts/run_track_b_neural_policy_ablation.py \
  --output data/manifests/track_b_neural_policy_ablation.json
```

## Purpose

The previous neural active policy was promising, but it mixed two things:

- a learned set encoder over observed raw event spectra,
- engineered candidate/state features such as distance and IDW disagreement.

This run asks whether the raw observed event set actually helps, or whether the policy is
mostly riding shortcut-like scalar features.

## Variants

| Variant | What It Can See |
| --- | --- |
| `full_neural` | Observed raw-spectrum set plus all engineered scalar features |
| `scalar_full` | All engineered scalar features, no observed raw-spectrum set |
| `set_basic` | Observed raw-spectrum set plus only candidate coordinate and budget state |
| `candidate_set_basic` | Candidate token attends to observed raw-spectrum tokens using only basic state |
| `coords_basic` | Observed coordinate set plus only candidate coordinate and budget state |

The objective remains:

```text
partial raw event observations -> choose next observation -> improve held-out raw spectra
```

No phase, impurity, failure, or hidden-regime label is used.

## Hypotheses

H1: If raw observed-event spectra matter, `full_neural` should beat `scalar_full`.

H2: If engineered scalar shortcuts dominate, `scalar_full` should match or beat
`full_neural`.

H3: If candidate-conditioned raw event attention helps, `candidate_set_basic` should beat
`set_basic` and `coords_basic`.

## Target Diagnostic

Mean oracle-target MSE improvement versus train-mean target baseline:

| Variant | Target MSE Improvement |
| --- | ---: |
| `full_neural` | 76.5% |
| `candidate_set_basic` | 75.0% |
| `set_basic` | 74.8% |
| `scalar_full` | 52.6% |
| `coords_basic` | 52.2% |

This is the cleanest ablation signal: raw observed spectra nearly add another 22-24
percentage points of target-prediction improvement beyond scalar-only or coordinate-only
variants.

## Policy Results

Mean MSE over five seeds and 80 held-out event-policy runs per budget:

| Budget | Space-filling | Forest | Scalar Full | Coords Basic | Set Basic | Candidate Set | Full Neural | Oracle |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 0.00758 | 0.00665 | 0.00686 | 0.00732 | 0.00674 | 0.00675 | 0.00668 | 0.00643 |
| 4 | 0.00543 | 0.00528 | 0.00544 | 0.00530 | 0.00533 | 0.00506 | 0.00524 | 0.00486 |
| 6 | 0.00415 | 0.00397 | 0.00436 | 0.00423 | 0.00419 | 0.00401 | 0.00420 | 0.00360 |
| 8 | 0.00418 | 0.00322 | 0.00335 | 0.00319 | 0.00313 | 0.00315 | 0.00318 | 0.00296 |

Improvement versus global-mean baseline:

| Budget | Space-filling | Forest | Scalar Full | Coords Basic | Set Basic | Candidate Set | Full Neural | Oracle |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 44.1% | 46.7% | 45.9% | 45.0% | 46.3% | 46.6% | 46.6% | 48.1% |
| 4 | 55.6% | 56.2% | 55.8% | 56.8% | 56.6% | 58.3% | 56.9% | 59.0% |
| 6 | 65.2% | 66.1% | 63.4% | 63.8% | 64.6% | 66.0% | 64.3% | 68.5% |
| 8 | 67.9% | 71.9% | 70.6% | 71.6% | 72.8% | 72.3% | 72.3% | 74.5% |

## Verdict

H1 is validated. `full_neural` beats `scalar_full` at every deployed budget, and the
target diagnostic shows a much larger gap: 76.5% versus 52.6% target-MSE improvement.

H2 is weakened. Engineered scalar features are useful, but they do not fully explain the
neural policy result. A scalar-only policy is not enough.

H3 is partially validated. `candidate_set_basic` beats `coords_basic` at every deployed
budget and beats pooled `set_basic` at budgets 4 and 6. But it does not dominate
`set_basic` at budgets 3 and 8. Candidate-conditioned attention looks useful, not
decisive.

## Interpretation

This is an important anti-shortcut check for Track B.

The raw observed spectra are not just decorative. When they are removed, target prediction
drops sharply. When they are kept but engineered distance/IDW features are removed, the
models remain competitive with the full model and the forest.

That supports the event-state direction:

> A policy can learn useful next-measurement behavior from partial raw event observations,
> not only from inherited labels or hand-built acquisition features.

The caveat is equally important. `coords_basic` becomes strong at larger budgets, which
means this synthetic scaffold has a spatial-smoothness shortcut. That does not invalidate
the result, but it tells us the next synthetic regime should be harder: nonstationary
fields, discontinuous process transitions, and provenance/counterbalance shifts where
coordinate coverage alone is not enough.

## Next Direction

Do not tune these models endlessly on the same scaffold.

The next useful step is a regime-transfer stress test:

```text
train acquisition policy on one family of synthetic event fields
test on shifted fields with different smoothness, discontinuities, provenance effects, or hidden regimes
```

If raw-event policies still beat scalar/coordinate shortcuts under those shifts, the
learned event-state claim becomes much stronger.
