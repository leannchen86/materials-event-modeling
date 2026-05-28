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

Raw/event-trained representations can support objective feedback tasks such as
prediction, compression, retrieval, or search better than inherited labels alone. Phase
labels and disagreement labels are diagnostic probes, not the final target.

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
