# Track B Active Event-Learning Loop

Generated with:

```bash
.venv/bin/python scripts/run_track_b_active_event_loop.py \
  --output data/manifests/track_b_active_event_learning_loop.json
```

## Purpose

This is the first prototype of the feedback-loop idea:

```text
partial raw event observations -> choose next observation -> improve reconstruction of
missing raw measurements
```

The loop does not use phase labels, success labels, impurity labels, or hidden regimes.
It is scored only by raw measurement reconstruction.

The synthetic event field has 24 events, 12 possible observations per event, and 512-point
synthetic XRD-like spectra. Each event starts with 2 space-filling observations, then a
policy chooses additional observations until the budget is reached.

## Tested Strategies

- `random`: choose the next unobserved coordinate randomly.
- `space_filling`: choose the coordinate farthest from already observed coordinates.
- `active_error`: choose where current IDW prediction disagrees most with the nearest
  observed spectrum.
- `active_hybrid`: combine the active-error score with distance from observed points.
- `oracle_best`: use the true hidden spectra to choose the next point that minimizes final
  reconstruction error. This is an upper bound, not a deployable policy.

## Hypotheses

H1: Active selection should improve missing-measurement reconstruction versus random
selection at small budgets.

H2: Coverage-aware active selection should be competitive with static space-filling
selection.

H3: The oracle-best strategy should define the current upper bound for this synthetic
event field.

## Key Results

Mean over five seeds and 120 event-policy runs per budget:

| Budget | Random MSE | Space-filling MSE | Active hybrid MSE | Oracle MSE |
| ---: | ---: | ---: | ---: | ---: |
| 3 | 0.00845 | 0.00782 | 0.00782 | 0.00653 |
| 4 | 0.00796 | 0.00549 | 0.00750 | 0.00496 |
| 6 | 0.00703 | 0.00409 | 0.00822 | 0.00368 |
| 8 | 0.00676 | 0.00417 | 0.01077 | 0.00304 |

Improvement versus event-mean baseline:

| Budget | Random | Space-filling | Active hybrid | Oracle |
| ---: | ---: | ---: | ---: | ---: |
| 3 | +19.7% | +30.7% | +30.7% | +33.8% |
| 4 | +23.4% | +31.1% | +26.1% | +37.7% |
| 6 | +30.6% | +40.7% | +27.6% | +45.6% |
| 8 | +34.4% | +40.0% | +34.3% | +48.8% |

Improvement versus global-mean baseline:

| Budget | Random | Space-filling | Active hybrid | Oracle |
| ---: | ---: | ---: | ---: | ---: |
| 3 | +34.2% | +43.8% | +43.8% | +46.9% |
| 4 | +36.8% | +54.9% | +42.2% | +58.1% |
| 6 | +44.3% | +65.1% | +38.4% | +67.0% |
| 8 | +44.6% | +66.4% | +25.5% | +72.3% |

## Verdict

H1 is partially validated. The active heuristics beat random at the smallest budgets, but
they do not keep improving as the budget grows.

H2 is not validated. Static space-filling is stronger than the current active heuristics
after budget 3. The active heuristic chases high-disagreement regions and loses coverage,
which hurts reconstruction.

H3 is validated. The oracle-best policy is much stronger than both random and
space-filling, especially at larger budgets. That means there is real headroom for a
better active policy.

## Interpretation

This is a good failure.

The important result is not "our first active heuristic wins." It does not. The important
result is:

```text
random < heuristic active < space-filling < oracle, depending on budget
```

More precisely:

- simple active uncertainty helps early,
- coverage is a brutally strong baseline,
- naive active selection can over-focus and become worse than random at larger budgets,
- the oracle gap says there is structure a better policy could exploit.

This keeps the project aligned with the core idea. We are not optimizing labels. We are
asking whether a system can learn where to look next in a material-making event.

## Next Direction

The next active-loop prototype should not be another hand-tuned heuristic. It should learn
a policy from previous events:

```text
past fully observed events -> train acquisition policy -> choose next observation in a new
partially observed event
```

Possible next policies:

- learned acquisition model that predicts expected reconstruction error reduction,
- ensemble disagreement over learned field models,
- model-predictive selection using a latent event representation,
- imitation learning from the oracle-best synthetic policy,
- active policy transfer from synthetic scaffold to real pilot data once available.

The key question becomes:

> Can an event-native system learn where to ask reality for the next useful feedback?

That is more central to the project than phase-label accuracy.

## Caveat

This is still synthetic. The current loop is a scaffold for the feedback objective, not a
claim about a real material system. But it gives us a concrete next research direction:
learn the acquisition policy instead of hand-writing it.

