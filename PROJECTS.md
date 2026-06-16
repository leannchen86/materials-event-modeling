# Projects Index

This repo is organized by **research branch** (what each thread is trying to ship), not by
data source. The old "Track A / Track B" axis is retired because it cut across the real
seams — in particular "Track B" was two unrelated projects (building the method vs.
collecting the dataset).

Code (`src/`, `scripts/`) and data (`data/`) are shared infrastructure and stay in standard
package layout. The branch split lives in `docs/` and this index.

## Legend (old → new)

| Old term | Now |
| --- | --- |
| Track A | **provenance-critique** (+ the HTEM event-field work that bridges to event-method) |
| Track B (modeling) | **event-method** |
| Track B (dataset/lab/outreach) | **controlled-collection** |
| "refined-a" | a *stage* of event-method (real-trajectory falsification), not its own branch |

---

## Branch: provenance-critique
**Deliverable:** methods/benchmark paper — *"When experimental XRD models learn the
laboratory."*
**Status:** closest to publishable. Findings are real but currently a local diagnostic on
one dataset; needs to become a reusable protocol applied across ≥2 datasets / ≥2 model
families.
**Core claim:** source/instrument/preprocessing identity is strongly recoverable from public
experimental XRD even after normalization, so representation gains can be silent collection
artifacts. Raw-objective reconstruction is viable but source-transfer plateaus.

- **Docs:** `docs/provenance-critique/` (`htem_event_proxy.md`,
  `ontology_stress_tests.md`, `anubhav_snap_result.md`), plus the strategy/positioning in
  `docs/spine/provenance_publication_assessment.md`.
- **Scripts:** `audit_opxrd_dataset.py`, `audit_nist_dataset.py`, `audit_htem_dataset.py`,
  `analyze_opxrd_*` (normalization controls, source diagnostics, source predictability),
  `run_opxrd_source_transfer.py`, `run_opxrd_conv_*`, `run_xrd_*`, `train_xrd_encoder.py`,
  `run_ontology_tests.py`, `run_htem_*` (event proxy, spatial field, sampling curve).
- **Manifests/data:** `data/manifests/opxrd_*`, `nist_*`, `htem_*`.
- **Next step:** package the provenance checks (source-predictability, coverage-controlled
  perf, interpolation baseline, leave-one-source-out) as a standalone diagnostic and run it
  on a second dataset.

## Branch: event-method
**Deliverable:** the core methodological paper — *event-native representations predict
missing/future measurements better than inherited labels.*
**Status:** **public-data campaign (Runs 001–015) complete.** Oleogel (001–008): raw recon is
interpolation/clock-solvable, SAXS↔WAXS time-redundant — a *data* limit, not a model limit
(capacity-free test). RRUFF (009–014): the validated, modality-general finding — inherited labels
are *natural coordinates* where they track structure (polymorphs; raw 0.91–1.0 on Raman AND XRD)
and *lossy* where they bin a continuum (solid-solution species; family 1.0 / species 0.73, errors
100% within-family); stress-tested against provenance, difficulty, error bars, and structure-blind
controls. Battery (015): the process-domain extension — lossy signal is weak and confounded by an
extrinsic planned variable (charging policy). **Conclusion:** no clean new discovery left in
public data; genuine faithful novelty needs the *rawness floor* (un-curated raw measurement). See
`docs/event-method/findings_summary.md`, `run_log.md`, and the reframe in
`docs/spine/ontology_and_rawness_gradient.md`.

- **Docs:** `docs/event-method/` — masked event model, event-field model, active-learning
  policies (`*active*`, `*policy*`), regime transfer, synthetic scaffold/field-budget,
  pilot-size & counterbalanced stress, event-analysis harness, provenance ablation, mock
  event review, and the JEPA design sketch (`jepa_event_model.md`, not yet run).
- **Scripts:** `run_track_b_*` (masked event model, event field, active loops, learned /
  neural active policy + ablation, regime / mixed-regime transfer, progress policy,
  synthetic scaffold, field budget, pilot-size, counterbalanced, event analysis).
- **Code:** `src/materials_event_modeling/track_b/`.
- **Public-data stage: done (Runs 001–015).** refined-a (oleogel) → label-probe + ablations
  (RRUFF, Raman + XRD) → battery process probe. The label taxonomy (redundant / natural / lossy)
  is validated and modality-general; the public-data discovery ceiling is reached (a candidate
  raw-vs-composition embedding run was rejected as a proxy of Runs 010/011). Genuine new discovery
  now requires the **rawness floor** = un-curated raw measurement (controlled-collection /
  operando). Summary: `docs/event-method/findings_summary.md`; reframe + decision:
  `docs/spine/ontology_and_rawness_gradient.md`. (Materials Project key is available for an
  optional DFT gradient-rung, env-var only — not committed.)
- **Candidate to promote later:** *active-measurement* (own assessment calls it the
  highest-impact paper). Split into its own branch only once it has a real result.

## Branch: controlled-collection
**Deliverable:** data paper + the dataset itself — a controlled material-making event
dataset (raw process/measurement trajectories, negatives/ambiguous outcomes, labels frozen
after raw data).
**Status:** outreach in flight; schema + harness exist; **no real material-making events
collected yet.** Public-data audits keep failing the event-nativeness bar — which is the
argument for collecting our own.

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
- **Next step / sharpened rationale (2026-06-16):** this is no longer just "public data is thin."
  Per the rawness-gradient reframe (`docs/spine/ontology_and_rawness_gradient.md`), controlled,
  un-curated raw measurement is **where the only remaining genuine, faithful-to-reality discovery
  lives** — the rawness floor that public datasets (all human-curated sampling) cannot reach. The
  public-data campaign closing (Runs 001–015) elevates this from "fallback" to "the frontier."

## Spine (cross-cutting)
`docs/spine/` — thesis & framing (`project_brief.md`, `capture_vs_representation_design_note.md`),
data strategy (`event_native_public_data_strategy.md`), publication assessments
(`provenance_publication_assessment.md`, `event_publication_assessment.md`), and infra
(`data_sources.md`, `compute.md`). The operating memo
is `SKILL.md` at the repo root.
