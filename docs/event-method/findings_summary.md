# Public-Data Campaign: Bounded Findings

Status: completed calibration archive. Detailed chronology and preregistered verdicts remain in
[run_log.md](run_log.md); canonical magnitudes point to manifests through the
[results ledger](../spine/results_ledger.json).

## What the campaign established

### Oleogel trajectories

Dense masked-frame reconstruction was a weak scientific task: time and interpolation explained most
of the apparent signal, and cross-modal dependence beyond smoothness was limited in six similar
events. This was a data/task limitation, not evidence that a larger model was needed.

Reusable lesson: characterize the signal first, split across events, and include clock,
interpolation, and smoothness-preserving nulls before training a representation.

### RRUFF mineral spectra

Deposited processed Raman spectra distinguished same-composition polymorph labels where composition
could not, while species-level garnet errors largely stayed inside broader structural families. The
pattern also appeared in deposited processed powder XRD.

This supports a bounded statement: some inherited categories compress distinctions present in the
selected spectra. It does **not** prove a continuous latent coordinate, a natural or true ontology,
downstream usefulness, or superiority of raw data. The primary Raman input was RRUFF's `Processed`
export, so the RAW-to-Processed edge was not audited.

### Severson battery cycling

Early per-cycle summaries contained within-corpus lifetime signal beyond a charge-policy label, but
the result was policy-confounded and did not survive the decisive held-batch ranking test. Later
review found that the adapter excluded the known within-cycle channel used by the strongest published
early-life feature. Right-censored cells were also initially misdescribed as negative outcomes.

Reusable lesson: a representation audit sees only edges below its common root; within-corpus signal
is not transferable evidence.

## What follows

The campaign justifies four controls for prospective work:

1. declare measurement opportunities, native artifacts, and adapter omissions;
2. distinguish support deletion from common-support prediction risk;
3. require clock/interpolation/context/provenance baselines and held environments; and
4. ask whether extra signal improves a real delayed decision.

It does not justify further public-dataset, JEPA, synthetic-policy, or architecture sweeps. The
active program is the prospective
[partner collection pipeline](../controlled-collection/partner_collection_pipeline.md).
