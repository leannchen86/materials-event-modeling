# Snap Result for Expert Outreach

## The 3-Second Version

In a public HTEM Cu-S-Sn slice, static recipe/material-row prediction failed to transfer
to held-out sample libraries, but a single sample library became self-predictive once we
observed part of its raw XRD field.

With 32 observed positions inside a library, predicting the missing XRD spectra with
within-event spatial interpolation improved MSE by 17.9% versus the observed event mean
and 58.9% versus the train mean, with no phase-purity, failure, or metastability labels.

## Why This Is Sharper

The claim is not:

```text
our neural net discovered a better materials feature
```

The claim is:

```text
the useful feedback signal is inside the material-making event trace, not only in the
final material row or inherited label
```

This is easier to explain because the contrast is concrete:

- Static sample metadata does not honestly generalize across held-out libraries.
- Partial raw measurements inside one experimental field do predict missing measurements.
- The task uses raw XRD reconstruction, not phase labels.
- The strongest result comes from the event objective itself, not from architecture hype.

## What We Should Not Overclaim

This is not yet evidence for a universal materials event embedding.

The HTEM task is still within-library spatial prediction, and inverse-distance weighting
is a strong baseline. That means the current result proves the event-field objective is
real and testable, not that a neural representation has surpassed simple event geometry.

The neural masked-event run is useful mostly as a guardrail:

- `raw_set` beats the collapsed `coord_only` control, so raw spectra do carry signal.
- `raw_residual` nearly matches IDW but does not beat it.
- The public HTEM slice is therefore a bridge dataset, not the final proof.

## Suggested Message

After watching your videos, I realized my earlier wording made this sound like
hand-crafted features versus NN features, which is already mainstream. What I am actually
testing is an event-native objective: given partial raw measurements from a material-making
event, predict the missing measurements, while phase/failure/metastability labels are
kept only as downstream probes.

The clearest early result is from HTEM: static material-row metadata failed to transfer
across held-out Cu-S-Sn libraries, but within one sample library, 32 raw XRD observations
predicted the missing XRD field 17.9% better than the event mean and 58.9% better than
the train mean, without using phase labels. So my question is whether current materials
data infrastructure preserves enough raw event feedback to scale this kind of objective.

## Source Artifacts

- HTEM event-proxy and spatial-field notes: `docs/track_a_htem_event_proxy.md`
- HTEM masked-event script: `scripts/run_htem_masked_event_model.py`
- HTEM masked-event manifest: `data/manifests/htem_masked_event_model_cu_s_sn.json`
