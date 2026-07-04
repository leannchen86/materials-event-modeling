# Snap Result for Expert Outreach

## The 3-Second Version

In a public HTEM Cu-S-Sn slice, static recipe/material-row prediction failed to transfer
to held-out sample libraries, but a single sample library became self-predictive once we
observed part of its raw XRD field.

With 32 observed positions inside a library, predicting the missing XRD spectra with
within-event spatial interpolation improved MSE by 17.9% versus the observed event mean
and 58.9% versus the train mean, with no phase-purity, failure, or metastability labels.

After hard controls, the cleaner version is:

```text
The result survives as event-field evidence, not as neural ontology evidence: correct
within-library coordinates improve missing-XRD prediction, shuffled coordinates go
negative, and contiguous row/quadrant holdouts are harder but still predictable.
```

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

The hard-control run makes the demystification sharper:

- `space_filling_32`: IDW improves MSE by 19.9% versus event mean and 30.3% versus
  shuffled-coordinate IDW.
- `held_out_row`: IDW improves MSE by 11.3% versus event mean and 13.7% versus shuffled
  coordinates.
- `held_out_quadrant`: IDW improves MSE by 10.5% versus event mean and 12.3% versus
  shuffled coordinates.
- Peak-aware MAE improvements remain positive: 56.7% for `space_filling_32`, 23.5% for
  `held_out_row`, and 19.4% for `held_out_quadrant`.

That makes the honest statement:

```text
HTEM confirms that partial raw observations inside an experimental field are a useful
feedback signal. It does not yet prove that a learned event embedding has beaten simple
event geometry.
```

## Suggested Message

After watching your videos, I realized my earlier wording made this sound like
hand-crafted features versus NN features, which is already mainstream. What I am actually
testing is an event-native objective: given partial raw measurements from a material-making
event, predict the missing measurements, while phase/failure/metastability labels are
kept only as downstream probes.

The clearest early result is from HTEM: static material-row metadata failed to transfer
across held-out Cu-S-Sn libraries, but within one sample library, partial raw XRD
observations predicted missing XRD without phase labels. In hard controls, correct
spatial coordinates beat shuffled-coordinate controls, and contiguous row/quadrant
holdouts remained predictable but harder. So my question is whether current materials data
infrastructure preserves enough raw event feedback to scale this kind of objective beyond
spatial interpolation.

## Source Artifacts

- HTEM event-proxy and spatial-field notes: `docs/provenance-critique/htem_event_proxy.md`
- HTEM masked-event script: `scripts/run_htem_masked_event_model.py`
- HTEM masked-event manifest: `data/manifests/htem_masked_event_model_cu_s_sn.json`
- HTEM hard-control script: `scripts/run_htem_event_field_controls.py`
- HTEM hard-control manifest: `data/manifests/htem_event_field_hard_controls_cu_s_sn.json`
