# Data Assumptions and Limits

Status: current interpretation, revised 2026-07-12. Existing results are public-data calibration
cases; their magnitudes are not estimates of industrial prevalence or value.

## Limits shared by the public datasets

1. **Selection is unknown.** Publication, curation, and benchmark reuse favor clean and successful
   records. Zero logged failures cannot distinguish perfect success from filtered failures. The
   Severson adapter retains right-censored targets, not documented physical failures.
2. **Provenance fields are bundled proxies.** An archive source, date, laser, or channel can combine
   chemistry, lot, instrument, software, operator, and protocol changes. Recoverability signals a
   risk; it does not prove shortcut use.
3. **`Raw` is relative.** Public spectra and cycling files have already passed through acquisition,
   export, processing, and adapter choices. The strongest known Severson within-cycle channel was
   referenced but excluded from the adapted arms.
4. **Independent environments are few.** Many rows can descend from a handful of batches, sources,
   or instruments. Uncertainty and splits must operate at the highest shared unit relevant to the
   claim.
5. **Most records are not synthesis events.** Minerals are characterized, batteries are cycled,
   and HTEM libraries are spatially measured. These can test controls without representing the
   material-making process of interest.
6. **Model assumptions can manufacture wins.** Smoothness favors interpolation and clock baselines;
   low-dimensional or stationary structure favors PCA and linear models; class imbalance and
   cluster concentration distort nominal uncertainty.

## What survives these limits

Structural statements survive when they follow from representation support: a projection that
removes replicate identity cannot rank those replicates, and a table that omits an attempt cannot
support a decision about it. These statements show what a format cannot express, not how useful a
richer signal will be.

Learned risk gaps, provenance accuracy, correlations, and confidence intervals are
sample-dependent. The Severson ranking gain is explicitly bounded to its corpus because it failed
held-batch transfer. RRUFF classification differences motivate a compression hypothesis but do not
establish a continuous true ontology or downstream value.

## Consequence

Public results can calibrate the audit, expose confounds, and reject weak tasks. A claim about
reproducibility, degradation, final-spec conformance, yield, qualification, or functional
performance requires prospective collection with explicit capture opportunities, complete
denominators, physical-unit lineage, actual reports, and held environments.

Canonical historical magnitudes and their manifest pointers live in
[results_ledger.json](results_ledger.json).
