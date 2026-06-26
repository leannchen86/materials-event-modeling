# Projects Index

This repo is organized by research purpose, not by data source. Only two directions are
active. Completed and synthetic work stays available as evidence, but is not an invitation
to keep extending every exploratory thread.

Code (`src/`, `scripts/`) and data (`data/`) are shared infrastructure and stay in standard
package layout. The branch split lives in `docs/` and this index.

## Legend (old → new)

| Old term | Now |
| --- | --- |
| Track A | **provenance-critique** |
| Track B (modeling) | **event-method** reference archive |
| Track B (dataset/lab/outreach) | **controlled-collection** |
| "refined-a" | archived public-data falsification work, not a new research branch |

---

## Branch: provenance-critique
**Deliverable:** a methods/benchmark protocol for provenance-stressed experimental-XRD
evaluation.
**Status:** active and closest to publishable. The opXRD finding is real, but currently
local: source labels are recoverable from metadata and spectra after normalization. It must
be replicated on a second appropriate dataset and connected to downstream evaluation before
it supports a broad shortcut claim.
**Core claim:** collection provenance can be recoverable from public experimental XRD, so
representation results should report provenance probes, coverage controls, strong simple
baselines, and strict source/session-held-out performance. Recoverability is a risk signal,
not proof that a downstream task is contaminated.

- **Docs:** `docs/provenance-critique/` (`htem_event_proxy.md`,
  `ontology_stress_tests.md`, `anubhav_snap_result.md`), plus the strategy/positioning in
  `docs/spine/provenance_publication_assessment.md`.
- **Scripts:** `audit_opxrd_dataset.py`, `audit_nist_dataset.py`, `audit_htem_dataset.py`,
  `analyze_opxrd_*` (normalization controls, source diagnostics, source predictability),
  `run_opxrd_source_transfer.py`, `run_opxrd_conv_*`, `run_xrd_*`, `train_xrd_encoder.py`,
  `run_ontology_tests.py`, `run_htem_*` (event proxy, spatial field, sampling curve).
- **Manifests/data:** `data/manifests/opxrd_*`, `nist_*`, `htem_*`.
- **Next step:** package source recoverability, coverage-controlled performance,
  interpolation/time baselines, and leave-one-source/session-out evaluation as one
  protocol; apply it to one second experimental dataset. Do not run another model-scaling
  sweep first.

## Reference archive: event-method
**Purpose:** retain the synthetic event-field, active-measurement, and representation
experiments as design evidence.
**Status:** closed to new architecture, policy, JEPA, regime-transfer, and synthetic-scaling
work. These experiments established useful requirements—counterbalancing, provenance
splits, coverage-aware observations, and interpolation/time controls—but they are not
evidence for a materials method.

- **Docs:** `docs/event-method/` — masked event model, event-field model, active-learning
  policies (`*active*`, `*policy*`), regime transfer, synthetic scaffold/field-budget,
  pilot-size & counterbalanced stress, event-analysis harness, provenance ablation, mock
  event review, and the JEPA design sketch (`jepa_event_model.md`, not yet run).
- **Scripts:** `run_track_b_*` (masked event model, event field, active loops, learned /
  neural active policy + ablation, regime / mixed-regime transfer, progress policy,
  synthetic scaffold, field budget, pilot-size, counterbalanced, event analysis).
- **Code:** `src/materials_event_modeling/track_b/`.
- **Reactivation rule:** only reopen a specific method when a real dataset and
  pre-registered task show signal beyond interpolation, a time/recipe prior, event identity,
  and provenance controls. Active measurement is an application layer, not a standalone
  research direction, until then.

## Branch: controlled-collection
**Deliverable:** data paper + the dataset itself — a controlled material-making event
dataset (raw process/measurement trajectories, negatives/ambiguous outcomes, labels frozen
after raw data).
**Status:** active. The schema and audit harness exist; no real material-making events have
yet been collected. Public-data audits identify the structural requirements for collection,
but are not a reason to run another public benchmark.

- **Docs:** `docs/controlled-collection/` — event dataset plan, universal event embedding
  scaffold (schema + ingestion/audit), low-equipment droplet pilot, MPS provenance-store
  evaluation, and public-dataset audits (Durham, Dryad, OpenCrystalData).
- **Outreach (subfolder, logistics not research):** `docs/controlled-collection/outreach/` —
  Foundry application/proposal/emails, PI/collaborator outreach, personalization plan,
  outreach visuals (+ `figures/`), lab-outreach brief, next-steps.
- **Scripts:** `audit_track_b_event_dataset.py`, `audit_durham_ipa_droplets.py`,
  `audit_dryad_gelation_dataset.py`, `audit_opencrystaldata.py`,
  `run_durham_droplet_smoke_test.py`, `download_data.py`.
- **Artifacts:** `schemas/material_event.schema.json`, `templates/`, `examples/track_b/`.
- **Next step:** finalize schema v1, remove transitional duplicate fields, and
  pre-register one pilot objective and its split/baseline rules before collection. The pilot
  needs counterbalanced operator, batch, lot, session, and run-order variation; a high count
  of poorly balanced events is not a substitute.

## Spine (cross-cutting)
`docs/spine/` — concise thesis, strategy, publication assessments, and infrastructure.
The operating memo is `SKILL.md` at the repo root.

## Explicitly out of scope

- Generic text/pretraining-corpus curation and decontamination. It has a different user,
  data model, and validation problem; it remains outside this repository.
- Universal claims about natural kinds, rawness, or a label-free "native coordinate system."
  The project tests task-specific adequacy under stated measurement conditions.
- Further public-dataset or synthetic architecture sweeps that do not change a collection
  decision or test a new provenance/evaluation control.
