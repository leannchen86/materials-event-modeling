# Track B Synthetic Field-Budget Stress Test

Generated with:

```bash
.venv/bin/python scripts/run_track_b_synthetic_field_budget.py --output data/manifests/track_b_synthetic_field_budget.json
```

## Purpose

This offline test targets the event-as-field idea:

```text
partial event observations -> missing/future raw measurements
```

It asks how many partial observations per event are needed before missing measurement
prediction becomes meaningful. The partial-observation coordinates are synthetic proxies
for time points, vial positions, spatial positions, droplets, or modalities.

This is not evidence about real chemistry. It is a pre-lab design scaffold.

## Hypotheses

H1: Event-local observations should predict held-out observations better than a global
mean.

H2: Inverse-distance field reconstruction should improve over a flat event mean once
enough observations are available.

H3: Space-filling observation should be more stable than random observation at small
budgets.

## Key Results

Mean over five seeds, using 24 synthetic events with 12 observations per event:

| Strategy | Observed per event | Event mean vs global | IDW vs global | IDW vs event mean |
| --- | ---: | ---: | ---: | ---: |
| random | 1 | -34.9% | -34.9% | 0.0% |
| random | 2 | -2.4% | +6.5% | +8.7% |
| random | 3 | +8.2% | +22.8% | +15.9% |
| random | 4 | +13.1% | +32.6% | +22.5% |
| random | 6 | +19.5% | +43.3% | +29.6% |
| random | 8 | +21.5% | +48.7% | +34.7% |
| space_filling | 1 | +2.0% | +2.0% | 0.0% |
| space_filling | 2 | +23.3% | +34.7% | +14.9% |
| space_filling | 3 | +17.9% | +44.8% | +32.8% |
| space_filling | 4 | +32.8% | +55.4% | +33.7% |
| space_filling | 6 | +38.1% | +65.5% | +44.2% |
| space_filling | 8 | +46.4% | +68.2% | +40.7% |

## Verdict

H1 is partially validated. Event-local observations beat a global mean once they provide
coverage, but random one-point sampling is worse than the global mean. That is the key
caveat.

H2 is validated. Inverse-distance reconstruction beats the flat event mean once at least
two or three observations are available, and the gain grows with budget.

H3 is validated. Space-filling observations are much stronger than random observations at
small budgets. With two space-filling observations, IDW already improves about 34.7%
versus the global mean and 14.9% versus the event mean. Random sampling needs about three
to four observations to become clearly useful.

## Design Lesson

For the real pilot, "multiple observations" should not mean arbitrary convenience
measurements. The observations need to cover the event axis.

Possible event axes:

- time points during aging/conversion,
- multiple vials or droplets under the same planned condition,
- spatial positions on a combinatorial or dried sample,
- modality coverage, such as XRD plus Raman/FTIR/microscopy,
- repeated measurements under controlled sample-preparation variation.

Practical recommendation:

```text
For each planned condition, collect at least 3 to 4 deliberately covered partial
observations if possible. Six to eight observations gives a much cleaner field signal.
```

This strengthens the lab outreach ask. We should not merely ask for 48 final XRD files.
We should ask whether the lab can support a small number of covered partial observations
per planned condition or per material-making event.

## Caveat

The synthetic field is deliberately smooth, so this run may overstate the value of simple
interpolation. A real lab pilot must keep the same baselines: global mean, event mean,
nearest neighbor, interpolation/IDW, and learned residuals only after the simple baselines
are beaten.

