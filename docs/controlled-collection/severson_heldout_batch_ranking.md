# Held-out-batch replicate ranking: does the ranking *rule* transfer across batches?

Started 2026-07-08. Follow-on (a decisive gap) recorded in the Severson A/B and
ranking-robustness verdicts
([severson_representation_ab.md](severson_representation_ab.md),
[severson_ranking_robustness.md](severson_ranking_robustness.md)). Ladder placement:
rung 3, provenance-stress on the rung-3 result itself.

> **Commit this pre-registration BEFORE running `scripts/run_severson_heldout_batch_ranking.py`.**
> The repo's audit trail depends on the prereg commit preceding the results commit
> (see the adversarial-review notes in the A/B doc). Read every number below with
> [../spine/data_assumptions_and_limits.md](../spine/data_assumptions_and_limits.md):
> 3 batches, 160 pairs, 82% from 5 batch-3 policy groups — few independent clusters.

## The gap this closes

The decisive within-policy ranking result (ridge 0.756) is scored by a model trained
**leave-one-policy-out over the pooled dataset** (`eval.severson_ab.loo_policy_scores`,
`train = [c for c in eol if c["policy"] != policy]` — batch is never referenced). Because
**every policy nests in exactly one batch** (verified: 72 policies, 0 offenders) and every
ranking pair is within-policy, the model that scores a batch-3 pair was trained on *other
batch-3 policies* as well as batches 1–2. So it has seen the test batch's collection
style.

Batch identity cannot leak *directly* into a pair — both siblings share a batch, so the
batch fingerprint (0.898 recoverability, balanced accuracy 0.932 — ledger key `severson_batch_recoverability`) is common-mode within the pair and cannot
distinguish them. What is untested is whether the learned **ranking rule** is
batch-*transferable* (cell physics) or batch-*calibrated* (a within-corpus map fit largely
on batch-3, which supplies 85% of the training replicate structure). Held-out-batch
regression (H6r) already showed the *level*-prediction rule transfers for ridge (+0.49
per-fold) but collapses for forest — but the ranking-robustness study proved regression
skill does **not** predict ranking skill (gradient boosting: reg ρ 0.802, rank 0.534), so
H6r cannot stand in for this experiment.

## Design (frozen helpers, one estimator swap)

For each held-out batch `H` of the three:

1. `train = [EOL cells with batch != H]`; fit `make_model` on
   `A_full = policy + trajectory(k=100)` features, target `log10(cycle_life)`. No
   leave-one-policy-out is needed inside `H` because `H`'s policies are absent from
   training by construction (policies nest in batch) — this is a strictly *harder* split
   than the pooled LOO-policy run.
2. Score every cell in `H`; rank the within-policy pairs that live in `H`.
3. Report per-batch accuracy `acc_H` and `n_H`, plus:
   - **pooled** (pair-weighted) held-out-batch accuracy,
   - **macro-average** over the three batches (equal weight per batch),
   - for reference on the *same pairs*, the pooled LOO-policy accuracy (0.779 / 0.667 /
     0.333 for ridge by batch) — the drop `LOO-policy − held-out-batch` on each batch is
     the **cost of not having seen the test batch**, the quantity of interest.

Models: the same five families as the robustness run (`ridge`, `svr_rbf`,
`gradient_boosting`, `forest`, `knn`), 3 seeds, so we see whether the ridge/tree split
survives the harder split. Paper-shape `B_policy` is carried as the structural control and
must stay 0.500 — forced by construction: policy features are constant within a policy
(verified across all 72 policies) and every estimator is deterministic, so identical
inputs give identical scores and every pair ties.

All feature/estimator machinery is imported from the frozen `eval.severson_ab`; only the
train-set partition (batch-exclusion instead of policy-exclusion) is new, and it lives in
the new script, not the frozen module.

## Pre-registered hypotheses (committed before the run)

- **H-transfer (primary, batch-3 only — the one adequately-powered cell).** Held-out-batch
  ridge ranking on batch 3 (`n=136`, train on batches 1+2) stays **≥ 0.65** with a
  cluster-bootstrap CI excluding 0.50. Expected point estimate **0.68–0.75** (most of the
  0.779 LOO-policy accuracy retained), because ridge *level*-transfer already worked
  (H6r). *Falsifier:* CI includes 0.50, or the estimate falls below 0.60 → the ranking
  rule was substantially batch-calibrated, and the 0.756 headline must be requalified as
  within-corpus, not transferable cell physics.
- **H-trees.** Forest and gradient boosting stay at or below chance on batch 3
  (≤ 0.60, CI touching 0.50), reproducing their pooled failure under the harder split —
  the tree-ensemble inductive bias cannot resolve continuous within-recipe gaps regardless
  of the split. Expected forest ~0.55, GB ~0.53.
- **H-underpowered (pre-registered null result).** Batches 2 (`2017-06-30`, `n=3`) and 1 (`2017-05-12`, `n=21`) cannot
  settle anything: a 3-pair test admits only accuracies {0, ⅓, ⅔, 1}, and the
  macro-average therefore inherits that noise. We pre-register that the macro-average will
  have a CI so wide it is **inconclusive by construction**, and that the honest read is the
  batch-3 cell plus the explicit statement that Severson lacks the batch count to macro-
  average. This is not a hedge added after seeing the numbers — it is the expected outcome,
  and its confirmation is itself the argument for `controlled-collection` (deliberately
  distributing replicates across ≥4 batches/sessions/operators).

**Decision this changes:** whether the rung-3 ranking claim is stated as "0.756 within
this corpus" (if H-transfer fails or is inconclusive) or "0.756, and it transfers across
collection batches for the linear model" (if H-transfer holds cleanly on batch 3). Either
way, the batch-1/2 cells document that Severson cannot fully settle it — the controlled-
collection pilot is the resolution path.

## Results (run 2026-07-08, manifest `severson_heldout_batch_ranking.json`)

**Findings first.** The within-recipe ranking advantage **does not transfer across
collection batches**. On the only adequately-powered cell — batch 3 (`2018-04-12`, 136
pairs), scored by a ridge model trained only on batches 1+2 (84 EOL cells) — held-out-batch
ranking is **0.522, cluster-CI [0.312, 0.697]**, statistically indistinguishable from the
0.500 chance floor. The same pairs scored leave-one-policy-out (which lets the model see
other batch-3 policies) reach 0.779, so the **transfer cost is 0.257** — that entire margin
was the scorer having seen the test batch's collection style. No family holds a held-out-batch ranking above its own chance CI on batch 3 (knn's
point drop is smallest at −0.099): ridge 0.779→0.522, knn 0.640→0.540, svr 0.632→0.434, forest
0.623→0.466, gradient boosting 0.548→0.423.

Internal consistency (validates the new path against the frozen helpers): the
leave-one-policy-out reference reproduces the committed headline numbers exactly — pooled ridge
0.7562 (= manifest 0.756), batch-3 ridge 0.7794 (= the post-hoc per-batch 0.779), and the
paper-shape B baseline ties at 0.500 by construction under this split too. Only the
train-set partition changed; the reproduction confirms nothing else did.

| model | batch-3 LOO-policy | batch-3 held-out-batch | drop | held-out-batch CI95 |
| --- | ---: | ---: | ---: | --- |
| ridge | 0.779 | **0.522** | −0.257 | [0.312, 0.697] |
| knn | 0.640 | 0.540 | −0.099 | [0.377, 0.675] |
| svr_rbf | 0.632 | 0.434 | −0.199 | [0.281, 0.586] |
| forest | 0.623 | 0.466 | −0.157 | [0.312, 0.622] |
| gradient_boosting | 0.548 | 0.423 | −0.125 | [0.345, 0.496] |

Underpowered cells (as pre-registered): batch 1 (`2017-05-12`, `n=21`) held-out ridge 0.524; batch 2
(`2017-06-30`, `n=3`) held-out ridge 0.667 — but `n=3` admits only {0, ⅓, ⅔, 1}, and across models that
cell swings 0.000 (svr) to 1.000 (gbt). The macro-average over three batches (ridge 0.571)
is therefore dominated by the 3-pair cell's noise and must not be quoted; the pooled
held-out-batch accuracy (ridge 0.525) and the batch-3 cell are the honest reads.

### Verdict against the pre-registered hypotheses

- **H-transfer — FALSIFIED.** Predicted batch-3 held-out ridge ranking ≥ 0.65 with CI
  excluding 0.50; actual **0.522 [0.312, 0.697]**, CI straddling chance. The pre-registered
  prior (0.68–0.75, reasoning that ridge *level*-transfer under H6r would carry the
  ranking) was **wrong in an informative way**: H6r's held-out-batch regression Spearman
  (ridge +0.49) measures coarse cross-policy lifetime ordering, which a constant per-batch
  level shift leaves intact; within-recipe sibling ranking depends on the *sign of the
  weight vector on trajectory-feature differences*, and that direction, learned on batches
  1+2, does not apply to batch 3. This is exactly the "regression skill ≠ ranking skill"
  decoupling from [severson_ranking_robustness.md](severson_ranking_robustness.md), now
  shown to also govern batch transfer — which is why H6r could not have stood in for this.
- **H-trees — CONFIRMED.** Forest (0.466, CI spanning 0.50 as registered) and gradient
  boosting (0.423 — CI entirely below 0.50, more extreme than the registered "touching")
  stay at/below chance on batch 3, reproducing their pooled failure under the harder split. But the
  finding is broader than "trees fail": under held-out-batch *no* family clears its CI, so
  the tree-vs-linear split that mattered within-corpus is washed out — nothing transfers.
- **H-underpowered — CONFIRMED in substance.** (The registered form predicted a
  too-wide macro-average CI; no macro CI was computed — the cross-model swing on the
  tiny cells carries the same conclusion by a different route.) The `n=3` (2017-06-30) and
  `n=21` (2017-05-12) cells are inconclusive by construction — and the `n=3` cell's
  pairs come from a SINGLE policy cluster, so a cluster CI is not even definable there, and the macro-average inherits the
  3-pair noise (ridge 0.571 vs pooled 0.525; gbt macro 0.622 inflated by the `n=3` cell
  hitting 1.000). Severson has too few batches to macro-average a batch-transfer claim.

### Belief update and decision

The rung-3 ranking magnitude is **within-corpus, substantially batch-calibrated — not
demonstrated transferable cell physics**. What survives, unchanged, is the **structural**
claim: the paper shape B is forced to 0.500 on replicate ranking (and cannot represent
censored runs) *by construction*, on any split; that claim is provenance-immune and this
experiment does not touch it. What is now measured, and must be stated wherever 0.756 is
quoted: the 0.756/0.779 advantage does not survive holding out the collection batch (batch
3: 0.522 [0.312, 0.697]).

This is **not** a reclassification of the A/B as "provenance leakage" in the leakage-into-
the-pair sense — batch is constant within every pair and cannot separate siblings directly.
It is the sharper, correct finding: the learned ranking *rule* is batch-local. The three
distinct rung-3 claims now read: (1) structural A>B separation — **provenance-immune,
stands**; (2) A's 0.756 ranking magnitude — **within-corpus, does not transfer across
batches** (this run); (3) trajectory *level*-prediction transfers linearly across batches
(H6r) while *ranking* does not (this run) — the decoupling is real and directional.

Decision (per the registered rule): the rung-3 ranking claim is stated as "0.756 **within
this corpus**," with the held-out-batch collapse attached. Severson cannot settle transfer
(3 batches, one pair-rich); a deliberately counterbalanced collection with ≥4 batches ×
sessions × operators is the resolution path — the `controlled-collection` branch's reason
to exist, now with a measured gap it is designed to close rather than an asserted one.

> **Adversarial verification (completed 2026-07-09):** an independent scoring loop with
> hard leakage assertions in every fold reproduced the batch-3 headline bit-for-bit
> (0.522059, CI [0.312, 0.697]); the full re-run is bit-identical; the LOO-policy
> reference matches the committed robustness manifest exactly for all five models
> (0.7562 pooled ridge; the 0.779 batch-3 slice is a post-hoc cut, consistent but not a
> committed headline); B's 0.500 is a theorem (constant within-policy features, verified),
> not an executed fit; policy→batch nesting confirmed from raw events (72 policies, 0
> offenders). All three hypothesis verdicts survive.
>
> **Pre-registration ordering breach (recorded, not repairable):** this doc's own
> instruction to commit the prereg before running was NOT followed — prereg and results
> enter git in the same commit, so the before/after ordering cannot be proven from
> history for this run (unlike the A/B and robustness runs, where it was verified). What
> is pinned: the run executed at committed code state `8609bf6` with a clean tracked
> tree (manifest `run_identity`), and the frozen `eval.severson_ab` helpers were exactly
> the committed ones. Weight the pre-registered-expectation claims accordingly; the
> *numbers* are independently reproduced regardless.
