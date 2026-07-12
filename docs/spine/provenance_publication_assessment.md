# Publication Assessment — Provenance Recoverability

Status: completed public-data methods result and maintained control module; revised 2026-07-12.
Primary evidence:
[provenance_leakage_audit.md](../provenance-critique/provenance_leakage_audit.md),
[second_dataset_replication.md](../provenance-critique/second_dataset_replication.md), and
[recoverability_vs_transfer.md](../provenance-critique/recoverability_vs_transfer.md).

## Verdict

The publishable result is not a better XRD model. It is a protocol-level warning:

> Collection source, instrument/acquisition geometry, processing, and curation can be recoverable
> from experimental records. Representation papers should therefore report provenance probes,
> coverage controls, strong simple baselines, and held-source/session performance.

The existence result replicated on a second experimental spectral archive and a nonspectral
battery dataset. A chemistry-matched RRUFF control showed that spectral-content recovery was
largely chemistry while acquisition geometry remained a provenance carrier. Separate analysis
found that recoverability does not reliably predict downstream transfer across the small set of
available cases.

Therefore:

- recoverability is a screening signal, not proof that a task model used a shortcut;
- a low probe score is not proof that provenance is absent;
- effect sizes from a few bundled public sources are not population estimates; and
- the module earns its keep only inside a real downstream evaluation.

## Scientific boundary

The opXRD arm uses deposited patterns after fixed-grid interpolation, minimum shift, and
normalization—not native instrument bytes. `Source` bundles laboratory, chemistry, instrument,
software, and curation. RRUFF primarily uses its `Processed` export. Severson batch bundles date,
lot, protocol, and collection style. None of these archives exposes a clean causal provenance axis.

HTEM adds a useful negative lesson: within-library spatial smoothness supports interpolation and
sampling controls, but it is not evidence about a synthesis-event representation. Do not fold HTEM
field prediction into the headline provenance claim.

## Nearby work and novelty limit

Public XRD datasets, phase ambiguity, automated phase mapping, self-supervised diffraction,
simulation-to-experiment transfer, autonomous XRD, and event-driven materials data systems already
exist. A generic CNN/transformer, phase-classification, masked-XRD, or event-schema paper is not
original on that basis.

The differentiated contribution is a reusable audit sequence:

1. define the provenance unit and its confounding bundle;
2. measure recoverability from metadata, coverage, standardized measurement, and controls;
3. keep dimensionality reduction and tuning inside folds;
4. compare random/grouped and held-source/session task performance;
5. diagnose whether recovery comes from chemistry, geometry, processing, or missingness where
   matched controls permit; and
6. state that recoverability and task transfer are separate estimands.

## Paper shape

A focused methods/benchmark paper is defensible if it releases the audit, fold-level predictions,
source definitions, matched controls, and limitations. Possible title:

> **When Experimental Models Learn the Laboratory: Provenance Recoverability as a Required
> Materials-ML Control**

The strongest paper combines this module with a prospective compression audit where a richer arm's
apparent gain either survives or collapses under held batch/site evaluation. Another public dataset
or model-scaling sweep does not materially strengthen the claim.

## Go/no-go

Proceed with a standalone provenance paper only if:

- every headline value is manifest-backed and fold-local;
- source/chemistry/coverage confounding is explicit;
- the RRUFF matched control and cross-modality replication reproduce from released code;
- held-source task performance is reported beside probe accuracy; and
- claims stay at screening/control altitude.

Otherwise keep provenance as a maintained module in the prospective partner paper. Do not call it
lab invariance, causal shortcut identification, or industry-wide prevalence.
