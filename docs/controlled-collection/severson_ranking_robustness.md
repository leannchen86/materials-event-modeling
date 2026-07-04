# Ranking robustness: is the forest arm's weakness about trees or the signal?

Started 2026-07-03. Follow-on (b) recorded in the Severson A/B replication verdict
([severson_representation_ab.md](severson_representation_ab.md)). The A/B's decisive
within-policy ranking result was model-split: ridge 0.756 (cluster-CI [0.68, 0.80],
robust) but forest only 0.596 (CI touching 0.499). H2r's "both families" bar therefore
did not clear. This isolates the cause.

> Read with [../spine/data_assumptions_and_limits.md](../spine/data_assumptions_and_limits.md):
> 160 pairs, 82% from 5 batch-3 policy groups — few independent clusters, one dataset.

## Design

Exactly the A/B ranking sub-task (within-policy replicate ranking, k=100,
leave-one-policy-out scoring, A_full representation, 3 seeds, cluster bootstrap over
policy groups) run across **five model families with genuinely different inductive
biases**: `ridge` (linear), `svr_rbf` (kernel), `gradient_boosting` (boosted shallow
trees), `forest` (bagged trees), `knn` (instance-based). All share the frozen
`eval.severson_ab` helpers, so the only thing that varies is the estimator. Null: the
ranking signal is a linear-model artifact (only ridge sees it).

## Pre-registered hypothesis (committed before the run)

- **H — the ranking signal is model-general; forest is the outlier.** A *majority* (≥3 of
  5) families rank replicates at ≥0.60 with a cluster-CI excluding 0.50. Expected point
  estimates: ridge ~0.76 (known), svr_rbf ~0.68–0.75 (kernel should see it), gradient
  boosting ~0.62–0.70 (boosting fits fine within-group differences bagging averages out),
  forest 0.596 (known), knn ~0.55–0.65 (uncertain — few neighbors across policies).
  *Confirmed →* forest's weakness is a bagging artifact (averaging deep trees washes out
  the small within-policy lifetime gaps), NOT a signal problem; H2r reads as "confirmed,
  forest is the outlier." *Falsified (only ridge, or only ridge+one, clears the bar) →*
  the signal is linear-and-thin; H2r stays honestly "ridge-only" and the effect size is
  the branch's, not a general claim.
- **Diagnostic (not a hypothesis):** report each model's regression skill (held-out-policy
  Spearman) alongside its ranking accuracy — a model can predict lifetime level well yet
  rank same-recipe siblings poorly. That gap is the interesting object.

**Decision this changes:** how the A/B's H2r is finally stated (both-families vs
ridge-outlier), and whether the ranking task in future A/B runs should default to a model
family other than forest.

Run command:

```
.venv/bin/python scripts/run_severson_ranking_robustness.py
```

## Results

*(to be filled by the run — verdict against H goes here)*
