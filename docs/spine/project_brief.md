# Project Brief

## Working Title

Pre-Taxonomic Materials Event Modeling

## Thesis

Materials ML often learns to predict inherited labels: phase purity, impurity,
metastability, synthesis success, and failure. This project treats those labels as
historical compression layers rather than ground-truth ontology.

The goal is to learn from raw measurement signals and material-making event metadata, then audit
whether conventional reports and labels preserve the evidence needed for a declared downstream
decision. The highest-value extension asks which early signals predict final-spec conformance,
repeatability/intermediate precision, degradation, functional performance, or scale failure, and
at which audited reporting edge those signals fail to be preserved. Cross-site reproducibility
remains a separate claim requiring independent sites.

## First Claim To Test

For a predeclared task, cutoff, and transfer environment, a richer or intermediate event
representation can retain decision value that an inherited report discards. The project must also
be able to conclude that a compact report is adequate. Phase labels and disagreement labels are
comparators and diagnostic probes, not presumed truth or presumed error.

## Public Data Guardrail

Public datasets such as NIST and opXRD are placeholders, feasibility targets, and artifact
audits. They are not the research destination. We should not keep tuning around opXRD or
NIST metrics as if this were a leaderboard. A public-data experiment is useful only when it
tests an objective feedback task, exposes a failure mode, or informs the design of a
controlled event dataset.

The public-data work has already taught one important lesson: raw XRD objectives can learn
nontrivial structure, but source/contributor effects are strong. This is a reason to build
Track B, not a reason to over-optimize opXRD.

## Track B: Controlled Event Dataset

Track B turns these questions into a controlled material-making event dataset. The first
candidate system is calcium carbonate polymorph crystallization, pending lab SOP and safety
review. Each row should be a material-making event with raw process logs, raw measurement
files, and later human labels recorded only as downstream probes.

Detailed plan: [event_dataset.md](../controlled-collection/event_dataset.md)

## Initial Questions

- Can raw XRD objectives learn embeddings useful for held-out measurement prediction?
- Do conventional labels form compact regions after training on raw objectives?
- Are ambiguous or disputed labels predictable as downstream probes rather than primary
  training targets?
- Do broad labels such as `mixed phase` or `failure` split into multiple latent regimes?
- Does adding process metadata reorganize the latent space around material-making events
  rather than static material categories?

## Non-Goals For The MVP

- Discovering a new material.
- Building the largest possible transformer.
- Treating phase classification accuracy as the only success criterion.
- Optimizing around public-dataset metrics after they stop informing the event-dataset
  design.
