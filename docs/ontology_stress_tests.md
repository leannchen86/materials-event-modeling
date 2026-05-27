# Ontology Stress Tests

These tests ask whether inherited materials labels behave like natural coordinates in a
learned measurement/event space.

## Candidate Tests

1. Label compactness: do labels occupy compact latent regions?
2. Label boundary ambiguity: do disputed labels sit near latent boundaries?
3. Label splitting: do broad labels break into multiple latent neighborhoods?
4. Label merging: do distinct labels overlap when raw measurements and process metadata
   are modeled together?
5. Intervention relevance: do learned embeddings predict the next measurement or useful
   process change better than label-only baselines?

## Baselines

- Composition-only descriptors.
- Classical XRD peak features.
- Human labels.
- Supervised phase-classifier embeddings.
- Self-supervised raw-pattern embeddings.

