# Ranking robustness: is the forest arm's weakness about trees or the signal?

> **Requalified 2026-07-08:** all ranking accuracies in this doc are LOO-policy
> (within-corpus) numbers; none survive a held-out-collection-batch split (best:
> ridge 0.522, chance). See
> [severson_heldout_batch_ranking.md](severson_heldout_batch_ranking.md).

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

## Results (run 2026-07-03, manifest `severson_ranking_robustness.json`)

160 pairs, A_full, k=100, leave-one-policy-out, 3 seeds, cluster bootstrap:

| model | family | rank accuracy | cluster CI95 | reg. Spearman | clears bar |
| --- | --- | ---: | --- | ---: | --- |
| ridge | linear | 0.756 | [0.678, 0.795] | 0.836 | **yes** |
| knn | instance | 0.625 | [0.559, 0.663] | 0.856 | **yes** |
| svr_rbf | kernel | 0.619 | [0.534, 0.700] | 0.804 | **yes** |
| forest | bagged trees | 0.596 | [0.499, 0.674] | 0.767 | no |
| gradient_boosting | boosted trees | 0.534 | [0.433, 0.604] | 0.802 | no |

### Verdict: H CONFIRMED at the threshold (3/5), but the pattern is sharper — it's
### specifically tree ensembles that fail, and my mechanism guess was wrong

- **The signal is model-general, not linear-only.** Three families with entirely
  different inductive biases — linear (ridge), instance-based (kNN), and kernel (SVR) —
  all rank replicates above 0.60 with cluster-CIs excluding chance. So the A/B's H2r
  "ridge-only" reading was too pessimistic: the within-policy signal is real and recovered
  by non-tree models. The forest weakness is **not** a signal problem.
- **Both tree ensembles fail — and boosting was the *worst*, refuting my prediction.** I
  pre-registered gradient boosting at ~0.62–0.70 on the guess that boosting fits the
  fine within-group differences that bagging averages out. It came in at **0.534 (chance)**,
  below even forest. So the failure is not "bagging washes out the signal" specifically;
  it is the tree-ensemble inductive bias as a class — piecewise-constant predictions
  cannot resolve the small *continuous* lifetime gaps between two cells of the same recipe.
  The falsified prediction is itself the finding: it's about step-function outputs, not the
  bag-vs-boost distinction.
- **Regression skill does not predict ranking skill — the diagnostic gap is large and
  is the thesis-relevant object.** Gradient boosting predicts lifetime *level* well
  (Spearman 0.802) yet ranks same-recipe siblings at chance (0.534); kNN has the best
  regression (0.856) but only middling ranking (0.625); ridge is middling at regression
  (0.836) yet best at ranking (0.756). A model can ace the cross-policy task and be useless
  at the within-recipe discrimination that is exactly what distinguishes the grammar
  representation from the paper-shape. Which model has the discriminative capability is not
  readable off aggregate accuracy — a caution for anyone benchmarking on level-prediction
  alone.

### Decision / how this restates the A/B's H2r

H2r's "both families" bar failed because forest was one of the two chosen families and
forest belongs to the outlier class. The honest restatement: **the within-policy ranking
signal is real and recovered by linear, kernel, and instance-based models (0.62–0.76,
CIs excluding chance); tree ensembles — bagged and boosted — specifically cannot resolve
it.** The structural claim (paper-shape forced to 0.500) is untouched. Future A/B ranking
runs should default to ridge (best ranker here) or report the family spread, and should
NOT use a tree ensemble as the sole ranking model. Still one dataset, 160 pairs from few
clusters — see the data-limits note.
