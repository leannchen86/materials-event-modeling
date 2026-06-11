# Foundry PI / Senior Collaborator Outreach

As of 2026-06-11.

The Molecular Foundry proposal route likely requires a PI or senior collaborator. This file
contains short messages for recruiting that person without overexplaining the entire
project.

## What We Need

A senior collaborator who can help with:

- material-system selection,
- lab feasibility,
- safety/SOP realism,
- Foundry proposal PI role or PI referral,
- characterization workflow,
- materials interpretation.

The collaborator does not need to do the ML implementation. The ask is scientific and
facility-facing guidance.

## Short Message

Subject: Possible Molecular Foundry user proposal on event-native materials data

Hi [Name],

I am preparing a possible Molecular Foundry user proposal around event-native materials
characterization for AI-driven materials discovery. The goal is to preserve fuller
material-making traces: planned conditions, observed deviations, raw XRD/microscopy files,
failed or ambiguous outcomes, provenance, and delayed labels.

The ML question is whether partial event traces predict missing or future measurements
better than final-label or static-metadata baselines. The broader motivation is that many
materials datasets compress experiments too early into final labels or properties, losing
feedback that may matter for AI-driven science.

The main gap before submission is a materials-side PI or senior collaborator who can help
shape the material system, safety/SOP feasibility, and Foundry resource request. Would you
be open to a short call, or is there someone you think would be a better fit?

Best,
Leann

## More Technical Version

Subject: Seeking PI/collaborator for event-native materials characterization proposal

Hi [Name],

I am working on a project at the intersection of materials data infrastructure and ML. The
core idea is that the native learning unit for materials discovery may need to be the
material-making event, not the final material row or phase/success label.

For a small pilot, each event would preserve:

- planned recipe and intended conditions,
- observed deviations and timestamps,
- raw XRD/microscopy/optical files,
- instrument/session provenance,
- failed, partial, and ambiguous outcomes,
- delayed labels assigned only after raw data is frozen.

The ML evaluation would ask whether partial event traces can predict missing/future
measurements, retrieve similar events, or reduce measurement burden better than final-label
or static-metadata baselines. Labels like phase assignment or success/failure would be used
as downstream probes, not the primary training target.

I am exploring a Molecular Foundry user proposal because the project needs reliable
characterization workflows, raw data export, and expert input on a repeatable material
system. The open gap is a PI/senior collaborator who can help make the material system,
safety, and resource request scientifically credible.

Would you be open to a short discussion, or could you suggest someone who might be a good
fit?

Best,
Leann

## Criteria For A Good Collaborator

Prefer someone who:

- understands experimental materials characterization,
- cares about reproducibility, metadata, or autonomous labs,
- can reason about XRD/microscopy ambiguity,
- has enough seniority to be PI or knows who could be PI,
- will not force the project back into phase-label classification only.

Avoid relying only on someone who:

- wants a clean success-only dataset,
- treats failed/ambiguous runs as waste by default,
- cannot support raw data export,
- cannot help with safety/SOP review.

