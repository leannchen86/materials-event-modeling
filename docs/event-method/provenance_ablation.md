# Track B Provenance Ablation Run

Generated with:

```bash
.venv/bin/python scripts/run_track_b_event_analysis.py \
  --bundle data/manifests/track_b_synthetic_event_bundle_16x3.json \
  --output data/manifests/track_b_event_analysis_16x3_ablation.json \
  --include-only-raw-objective
```

## Purpose

This run tests whether the event/process signal could be a provenance shortcut.

Provenance means the context of data production, such as batch, operator, reagent lot,
instrument, session, export format, or sample-preparation route.

The ablation adds three controls:

1. **Held-out-provenance splits:** train on some provenance groups and test on unseen
   groups, such as held-out operator or held-out reagent lot.
2. **Provenance-only baselines:** ask whether provenance alone predicts spectra.
3. **Provenance residualization:** first regress spectra on provenance fields, then test
   whether labels or event/process features still predict the remaining residual signal.
4. **Within-provenance feature shuffle:** shuffle event features within provenance groups
   while leaving spectra fixed. If performance survives, the model may be using provenance
   structure rather than row-level event/process signal.

## Hypotheses

H1: If provenance is the whole shortcut, event/process performance should collapse under
held-out-provenance splits.

H2: If event/process variables carry signal beyond provenance, they should still predict
provenance-residualized spectra.

H3: Shuffling event features within provenance groups should reduce held-out-plan
performance if row-level event/process values matter.

## Key Results

### Original Prediction

MSE improvement versus train mean:

| Split | Label only | Planned | Observed | Full event | Provenance only |
| --- | ---: | ---: | ---: | ---: | ---: |
| held-out plan | +19.3% | +63.7% | +58.9% | +62.1% | +0.4% |
| held-out batch | +17.9% | +61.4% | +56.0% | +61.5% | -19.1% |
| held-out reagent lot | +15.5% | +22.1% | +18.2% | +18.5% | -5.9% |
| held-out provenance combo | +17.6% | +47.1% | +44.0% | +45.3% | -31.2% |
| held-out operator | +17.1% | -3782.2% | +2.8% | -3101.1% | -30.8% |

### Provenance-Residualized Target

MSE improvement versus residual train mean after removing provenance-predictable spectral
signal:

| Split | Label only | Planned | Observed | Full event |
| --- | ---: | ---: | ---: | ---: |
| held-out plan | +14.7% | +52.6% | +48.9% | +51.1% |
| held-out batch | +12.0% | +51.0% | +47.5% | +52.8% |
| held-out reagent lot | +12.9% | +20.5% | +17.4% | +18.5% |
| held-out provenance combo | +12.0% | +39.0% | +36.9% | +39.1% |
| held-out operator | +11.3% | -2290.4% | +9.6% | -1736.7% |

### Within-Provenance Feature Shuffle

Held-out-plan MSE improvement after shuffling event features within provenance groups:

| View | Original | Shuffled mean |
| --- | ---: | ---: |
| planned conditions | +63.7% | +15.1% |
| observed trajectory | +58.9% | +12.3% |
| full event | +62.1% | +15.3% |

## Verdict

H1 is mostly validated against the shortcut-only explanation, with one important failure
case. Event/process features remain much stronger than provenance-only under held-out
plan, held-out batch, held-out reagent lot, and held-out provenance-combo splits.
Provenance-only is near zero or negative on the grouped splits.

The held-out-operator split is a red flag. Planned/full-event models collapse badly when
one operator is held out. In this synthetic bundle, there are only two operators and the
operator assignment is confounded with planned-condition/regime coverage. The ablation is
doing its job: it found a design that would be unacceptable in a real pilot.

H2 is validated for held-out plan, batch, reagent lot, and provenance combo. Event/process
features still predict residual spectra after provenance-predictable signal is removed.
That weakens the claim that the model is only using provenance.

H3 is validated. Shuffling event features within provenance groups drops held-out-plan
performance from roughly 59-64% improvement to roughly 12-15%. That means the original
event/process signal is not explained only by provenance group membership.

## Design Lesson

This run does not prove shortcuts are impossible. It shows how to catch them.

For real data, the pilot must counterbalance provenance:

- do not let one operator run only one part of the planned-condition space,
- do not let one reagent lot correspond to one chemistry regime,
- do not put all difficult/ambiguous cases in one batch,
- do not collect only one instrument session if we want to claim session transfer,
- log provenance so it can be split, residualized, and audited.

The immediate design consequence:

```text
48 events should not be 16 plans x 3 replicates run in one hidden order by one person.
They should be counterbalanced across operator/session/lot/batch as much as the lab allows.
```

## Stronger Claim We Can Eventually Make

Not:

> The model definitely cannot use shortcuts.

Better:

> Event/process representations remain predictive under provenance-blocked splits,
> provenance-only baselines, provenance-residualized targets, and within-provenance feature
> shuffles.

That is the paper-grade form of the claim.

