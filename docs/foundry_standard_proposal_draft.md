# Molecular Foundry Standard Proposal Draft

As of 2026-06-11.

This is a paste-ready working draft organized around the Molecular Foundry proposal review
categories. It is not yet submission-ready because it needs:

- PI/senior collaborator,
- confirmed Lead Facility,
- confirmed material system and SOP,
- final resource estimates from Foundry staff.

## Project Title

Event-Native Materials Characterization for AI-Driven Materials Discovery

## Short Abstract

AI-driven materials discovery depends on experimental feedback, but many materials datasets
compress experiments into final labels, final properties, or success/failure outcomes. This
project asks whether richer material-making event traces provide better learning signals.
We propose a small controlled pilot dataset in which each event preserves planned
conditions, observed deviations, raw characterization files, provenance, failed or
ambiguous outcomes, and delayed labels. The core evaluation is whether models trained on
partial event traces can predict missing or future measurements better than models trained
on static metadata or final labels alone.

## Project Goals And Significance

### Long-Term Goal

The long-term goal is to develop an event-native data model for AI-driven materials
discovery. Instead of treating `phase pure`, `impure`, `failed`, or `ambiguous` as the
native training targets, the project treats those labels as downstream interpretations of a
richer material-making event.

### Scientific Motivation

Materials ML has made progress using curated labels, computed properties, and final
characterization summaries. However, experimental materials data often omits attempts,
failures, raw measurements, process deviations, instrument/session context, and uncertainty.
This can make models learn from a compressed record of the experiment rather than from the
actual feedback loop that produced the material.

The project tests a concrete hypothesis:

```text
Partial event traces predict missing or future measurements better than final-label or
static-material records.
```

If validated, this would support a more useful data standard for autonomous and AI-assisted
materials discovery: record the experiment as an event first, then use human labels as
auditable probes rather than primary ground truth.

### Immediate One-Year Goal

The one-year goal is to build and analyze a small controlled event-trace dataset using a
simple, repeatable material-making system. The system should be selected with Foundry staff
based on safety, feasibility, characterization fit, and ability to produce nontrivial
process-sensitive outcomes.

Candidate systems include:

- calcium carbonate polymorph crystallization,
- another safe, repeatable crystallization or thin-film/nanoscale assembly system proposed
  by Foundry staff,
- a Foundry-relevant system where XRD/microscopy/optical measurements can be collected
  consistently with raw file export.

The scientific output is not primarily the discovery of a new material. The output is a
validated event-trace dataset and evaluation protocol.

## Project Plan And Timeline

### Work Before Foundry Access

- Finalize event schema and raw-file naming convention.
- Run software ingestion checks on mock events.
- Prepare analysis scripts for missingness audit, leakage audit, masked reconstruction,
  held-out measurement prediction, replicate retrieval, and label projection audit.
- Coordinate with PI/collaborator and Foundry staff on feasible material system, SOP, and
  measurement workflow.

### Foundry Work

Phase 1: Workflow design and feasibility

- Select material system and measurement modalities.
- Confirm sample preparation, safety, instrument settings, raw data export, and metadata
  fields.
- Run a tiny feasibility set of events to test logging and raw-data capture.

Phase 2: Controlled pilot dataset

- Collect a small event dataset with planned and observed variables separated.
- Preserve raw XRD/microscopy/optical files before label assignment.
- Keep failed, partial, ambiguous, and messy events unless safety or instrument constraints
  require exclusion.
- Record instrument/session/operator/date/provenance fields.

Phase 3: ML analysis

- Train/evaluate objective feedback tasks:
  - early trace -> later measurement prediction,
  - partial measurements -> missing measurement reconstruction,
  - replicate/similar-event retrieval,
  - ambiguity or uncertainty prediction,
  - measurement-budget simulation.
- Compare against static metadata, final-label, composition-only, event-mean, and simple
  interpolation baselines.
- Use human labels only after raw/event objectives are evaluated.

### Estimated Timeline

- Months 1-2: finalize workflow and feasibility events.
- Months 3-6: collect controlled pilot dataset.
- Months 6-8: run initial ML evaluation and diagnose missingness/provenance issues.
- Months 9-12: refine dataset, write benchmark/protocol report, prepare publication or
  follow-on proposal.

## Resource Request

The project requests Foundry guidance and access for a small event-trace pilot. Exact
resources should be finalized after staff consultation.

Likely needed:

- powder or thin-film XRD with raw data export,
- optical microscopy or electron microscopy if useful for the selected system,
- staff guidance on repeatable sample preparation and characterization workflow,
- advice on instrument metadata, sample naming, and provenance capture,
- optional theory/data-analysis support for representation learning and benchmark design.

Possible lead/support facility structure:

- Lead Facility: Inorganic Nanostructures or Organic and Macromolecular Synthesis,
  depending on chosen system.
- Support Facilities: Imaging/Manipulation, NCEM, or Theory, depending on measurement and
  analysis needs.

## Relevant Experience

Leann Chen will lead the ML/data side:

- event schema design,
- raw-file and metadata ingestion,
- benchmark construction,
- model evaluation,
- public-data provenance stress tests,
- documentation and reproducibility.

The project needs a PI or senior collaborator to lead or co-lead:

- material-system selection,
- lab feasibility and safety,
- sample preparation workflow,
- instrument access and training,
- materials interpretation.

This is the main open staffing gap before submission.

## Data Management Plan

The project will preserve raw and processed layers separately:

- raw instrument files,
- raw images or measurement files,
- event metadata,
- planned conditions,
- observed deviations,
- post-hoc labels,
- analysis-ready derived arrays.

Labels will be delayed until after raw files are frozen. Failed or ambiguous events will be
retained and flagged rather than removed by default.

## Risks And Mitigations

Risk: The selected system is too simple or too clean.

Mitigation: choose a process-sensitive system with known ambiguity, mixtures, partial
conversion, morphology variation, or measurement uncertainty.

Risk: Dataset is too small for high-capacity neural models.

Mitigation: use simple baselines first and evaluate sample efficiency. The first claim is
about event trace utility, not model scale.

Risk: Measurements become label-first despite the intended design.

Mitigation: freeze raw data before labels and preserve labels as downstream probes.

Risk: Foundry access is not the right mechanism.

Mitigation: ask User Office for fit guidance before submitting and adjust route to Standard,
Rapid Access, Instrument Only, or partnership path as recommended.

## Open Questions For Foundry Staff

1. Which Lead Facility is most appropriate for this project?
2. Is a Standard Proposal the right route, or would Rapid Access or Instrument Only be
   more appropriate?
3. Which material system would best fit a safe, repeatable, process-sensitive event-trace
   pilot?
4. Can raw XRD and microscopy files be exported consistently with instrument settings?
5. What sample throughput is realistic for a small pilot?
6. What metadata can be captured automatically versus manually?
7. What safety/SOP constraints should shape the initial design?
8. Does the project need a Foundry staff collaborator before submission?

