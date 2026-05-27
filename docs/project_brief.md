# Project Brief

## Working Title

Pre-Taxonomic Materials Event Modeling

## Thesis

Materials ML often learns to predict inherited labels: phase purity, impurity,
metastability, synthesis success, and failure. This project treats those labels as
historical compression layers rather than ground-truth ontology.

The goal is to learn representations from raw measurement signals and material-making
event metadata, then audit whether traditional labels are natural coordinates, lossy
projections, or artifacts of the measurement/interpretation pipeline.

## First Claim To Test

Raw XRD embeddings can reveal label ambiguity, disagreement, or hidden structure that
phase labels and simple peak features do not capture.

## Initial Questions

- Do conventional labels form compact regions in learned XRD space?
- Are ambiguous or disputed labels predictable from raw-pattern embeddings?
- Do broad labels such as `mixed phase` or `failure` split into multiple latent regimes?
- Does adding process metadata reorganize the latent space around material-making events
  rather than static material categories?

## Non-Goals For The MVP

- Discovering a new material.
- Building the largest possible transformer.
- Treating phase classification accuracy as the only success criterion.

