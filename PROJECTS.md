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
| "refined-a" | archived public-data falsification campaign (Runs 001–015, merged 2026-07-03); record in `docs/event-method/findings_summary.md` + `run_log.md` |

---

## Branch: provenance-critique
**Deliverable:** a methods/benchmark protocol for provenance-stressed experimental-XRD
evaluation.
**Status:** active and closest to publishable. The replication bar is **met** (2026-07-03):
the opXRD source-recoverability finding replicates on RRUFF mineral Raman and generalizes to
a non-spectral modality (Severson battery cycling), and the RRUFF chemistry-matched control
localizes the composition-invariant provenance signal to acquisition geometry (point count,
coverage) — see `docs/provenance-critique/second_dataset_replication.md`. Remaining before a
broad shortcut claim: connect recoverability to a downstream evaluation (leave-one-source-out
task performance), not just probe recoverability.
**Core claim:** collection provenance can be recoverable from public experimental XRD, so
representation results should report provenance probes, coverage controls, strong simple
baselines, and strict source/session-held-out performance. Recoverability is a risk signal,
not proof that a downstream task is contaminated.

- **Docs:** `docs/provenance-critique/` — **`provenance_leakage_audit.md` (the flagship
  result + reusable tool)**, **`second_dataset_replication.md` (RRUFF + Severson
  replication, chemistry-matched control)**, `htem_event_proxy.md`,
  `ontology_stress_tests.md`, `anubhav_snap_result.md`, and
  `provenance_leakage_text_corpus.md` (modality-generality evidence, archived) — plus the
  strategy/positioning in `docs/spine/provenance_publication_assessment.md`, and
`recoverability_vs_transfer.md` (recoverability is a screening signal, not a
downstream-transfer predictor — n=6).
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
experiments as design evidence, plus the completed real-data campaign record.
**Status:** closed to new architecture, policy, JEPA, regime-transfer, and synthetic-scaling
work. These experiments established useful requirements—counterbalancing, provenance
splits, coverage-aware observations, and interpolation/time controls—but they are not
evidence for a materials method.

**Real-data campaign (Runs 001–015, completed 2026-06-16, merged to main 2026-07-03):**
summary in `docs/event-method/findings_summary.md`, per-run log in
`docs/event-method/run_log.md`. Verdicts:

- *Oleogel SAXS/WAXS (Runs 001–008), negative:* masked-frame reconstruction on dense smooth
  trajectories is interpolation/clock-solvable; SAXS/WAXS are largely time-redundant (1/6
  events show genuine cross-modal excess). Shown capacity-free to be a data property
  (homogeneous, 6 near-identical events) — the empirical justification for
  controlled-collection.
- *RRUFF (Runs 009–014), positive:* the three-way label taxonomy — labels are redundant
  (re-encode composition), natural coordinates (polymorphs: raw recovers them 0.91–1.0 where
  composition cannot), or lossy (solid-solution species: garnet family 1.0 vs species 0.73,
  100% of errors within-family — Run 011). Ablation-hardened (Runs 012–013) and reproduced on
  powder XRD (Run 014). This is the first real-data evidence for the lossy-labels thesis and
  the standing basis for claim 3 in `docs/spine/event_grammar_validation_note.md`.
- *Severson battery (Run 015), partial:* early-trajectory predicts lifetime (Spearman 0.61)
  but the lossy signal is confounded by charging policy — extrinsic process labels need
  controlled conditions, reinforcing the controlled-collection design.

The campaign closed with the rawness-floor decision (`docs/spine/ontology_and_rawness_gradient.md`):
public-data discovery is exhausted; the next genuine result requires controlled collection.
A public writeup draft exists at `docs/writeup/when_is_a_label_faithful.md`.

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
**Status:** active. Grammar v1 is frozen (envelope `schemas/event_grammar.v1.schema.json` +
L0–L3 conformance in `src/materials_event_modeling/grammar/`), and the adapter-coverage
study (`docs/controlled-collection/event_grammar_coverage_study.md`, 2026-07-03) graded six
public datasets: Severson L3, HTEM L1, Durham/oleogel/NIST/RRUFF L0 — falsifying the
pre-registered "no public dataset exceeds L1" and identifying Severson + oleogel as the
Phase 2 A/B datasets. No real material-making events have yet been collected; the audits
identify the structural requirements for collection, not a reason to run another public
benchmark.

- **Docs:** `docs/controlled-collection/` — event dataset plan, universal event embedding
  scaffold (schema + ingestion/audit), the grammar coverage study + Severson representation
  A/B, low-equipment droplet pilot, MPS provenance-store evaluation, public-dataset audits
  (Durham, Dryad, OpenCrystalData), and **`experiments.md`** (parked three-tier XRD
  portfolio for a process-recording-lab partner — round-robin, lossy-label intervention,
  born-L3 pilot). The cross-cutting formal object is the task-relevant compression audit in
  `docs/spine/task_relevant_compression_audit.md`; its paper-level novelty and evidence gates
  are recorded in `docs/spine/compression_audit_publication_assessment.md`.
- **Outreach (subfolder, logistics not research):** `docs/controlled-collection/outreach/` —
  Foundry application/proposal/emails, PI/collaborator outreach, personalization plan,
  outreach visuals (+ `figures/`), lab-outreach brief, next-steps.
- **Scripts:** `audit_track_b_event_dataset.py`, `audit_durham_ipa_droplets.py`,
  `audit_dryad_gelation_dataset.py`, `audit_opencrystaldata.py`,
  `run_durham_droplet_smoke_test.py`, `download_data.py`.
- **Artifacts:** `schemas/material_event.schema.json`, `templates/`, `examples/track_b/`.
- **Next step:** execute `docs/controlled-collection/pilot_design_prereg.md` (v0 drafted
  2026-07-09): elicit + freeze the practitioner task, confirm the partner-lab envelope, then
  the freeze commit becomes the pre-registration and collection begins. The design encodes
  every accumulated constraint (16x3 counterbalanced, >=4 sessions with cross-session
  replicate pairs — the held-out-batch falsification's measured requirement — failures
  retained, labels frozen, grammar-native logging at L3).

## Spine (cross-cutting)
`docs/spine/` — concise thesis, strategy, publication assessments, and infrastructure.
The operating memo is `SKILL.md` at the repo root.

## Explicitly out of scope

- Generic text/pretraining-corpus curation and decontamination as a research direction. The
  merged campaign artifacts (`src/materials_event_modeling/curate/`, the `text` adapter in
  `run_provenance_leakage_audit.py`, `docs/provenance-critique/provenance_leakage_text_corpus.md`)
  are retained as archived evidence that the provenance-audit protocol is modality-agnostic,
  not as an invitation to extend corpus work here.
- Universal claims about natural kinds, rawness, or a label-free "native coordinate system."
  The project tests task-specific adequacy under stated measurement conditions.
- Further public-dataset or synthetic architecture sweeps that do not change a collection
  decision or test a new provenance/evaluation control.
