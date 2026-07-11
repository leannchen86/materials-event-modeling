# Severson Downstream-Compression Dry-Run Results

Status: **retrospective, post-hoc, nonconfirmatory engineering result**, 2026-07-11. The
[design and leakage amendment](severson_downstream_compression_dry_run.md) were committed before
the repository implementation and formal run. The machine-readable result is
[`severson_downstream_compression_audit.json`](../../data/manifests/severson_downstream_compression_audit.json).

## Bottom line

The engineering path passed, but this dataset does **not** establish that the retained cycle-2--100
trajectory preserves transferable cycle-life information that its seven-number summary destroys.
In the leakage-corrected primary analysis, the compact summary and retained trajectory were nearly
tied, their cluster-bootstrap interval crossed zero, their ordering changed with the risk
weighting, and their per-batch signs were strongly heterogeneous.

The most consequential finding is methodological: five batch-1 cells obtain their long-lived
targets from batch-2 barcode continuations. Excluding those targets from both fitting and scoring
changes tuned models and reverses the pooled S100-versus-X100 ordering. Target provenance can
therefore change an apparent representation ranking even when provenance is never supplied as a
feature.

This dry run should remain an engineering fixture and a paper case study. It is not the partner
study needed for a downstream-failure claim.

## Audit completion

- 135 physical-cell attempts were retained.
- 128 cells have an exact observed-EOL target; the primary universe excludes five cross-batch
  continuation-derived targets and contains 123 cells.
- Seven right-censored cells remain in the row ledger with finite lower bounds of 879--2,238
  cycles; the current scalar loss does not score them.
- All 135 attempts support all four frozen representations.
- Sixteen attempts each require one interior interpolation; no endpoint is imputed.
- `S100=f(X100)` reconstructs with zero numerical discrepancy.
- Every available attempt receives one strictly held-batch prediction from each arm in each
  analysis. Outer event and policy overlap are both zero.
- The clean formal run records code commit `e10824c`, source hash
  `9f5d2148e254a3799672ad127bce4be6a5c5ea31b801ae7132ff905dd8de8d05`, and
  `git_dirty=false`.

The nine new synthetic tests also exercise cutoff-before-interpolation, future-value inertness,
flagged and malformed observations, censor-versus-representation support, policy-grouped inner
tuning, outer policy isolation, held-test preprocessing isolation, and a full continuation
sensitivity refit.

## Primary risks

MAE is in log10 cycles. Policy-macro risk gives every eligible charge policy equal total weight;
cell-micro risk gives every eligible cell equal weight.

| arm | primary policy-macro MAE | primary cell-micro MAE | contaminated all-EOL policy-macro MAE |
| --- | ---: | ---: | ---: |
| `C` | 0.2294 | 0.2210 | 0.2589 |
| `C_S100` | **0.2130** | 0.2106 | 0.2478 |
| `C_X100` | 0.2153 | **0.1976** | **0.2416** |
| `C_S100_X100` | 0.2228 | 0.2022 | 0.2533 |

The primary direct contrast is

```text
MAE(C_S100) - MAE(C_X100) = -0.00226
policy-cluster bootstrap 95% interval = [-0.01875, 0.01423]
```

Thus the policy-macro point estimate slightly favors S100, while the cell-micro point estimate
favors X100 by 0.01297. Neither contrast supports a stable adequacy or information-loss claim.

The context-to-summary and context-to-trajectory policy-macro gaps are +0.01636 and +0.01410,
respectively, but both intervals cross zero and neither transfers consistently across all three
held batches. Adding X100 to S100 also does not help in the pooled primary result: its gap is
-0.00985 with interval [-0.02800, 0.01108].

## Environment heterogeneity

Positive S100-minus-X100 gaps mean X100 has lower risk.

| held batch | targets | policies | S100 minus X100 policy-macro MAE |
| --- | ---: | ---: | ---: |
| 2017-05-12 | 36 | 20 | -0.0230 |
| 2017-06-30 | 43 | 41 | -0.00714 |
| 2018-04-12 | 44 | 8 | +0.0746 |

X100 is substantially better in batch 3 and worse in the other two batches. The batch-3 interval
is positive, but that environment has only eight policy clusters and its policies are absent from
the other batches. Batch, policy, and the new-structure regime are not separable here. The pooled
near-tie is therefore not evidence of uniform summary adequacy, and the batch-3 result is not
evidence of transferable premature compression.

## Continuation sensitivity

The five continuation-resolved targets are all primary batch-1 cells whose records continue into
batch 2; their observed lifetimes are 1,422--2,229 cycles. They are unusually long-lived and can
enter the training set for a model evaluated on batch 2. The sensitivity intentionally refits
every scaler, alpha, and model with all 128 exact targets rather than masking five final losses.

| target universe | S100 policy-macro MAE | X100 policy-macro MAE | S100 minus X100 |
| --- | ---: | ---: | ---: |
| primary, continuations excluded | 0.2130 | 0.2153 | -0.00226 |
| contaminated all-observed-EOL sensitivity | 0.2478 | 0.2416 | +0.00620 |

The sensitivity interval remains inconclusive, [-0.01571, 0.02851], but the point ordering flips
and several selected alphas change. The absolute MAEs across these rows are not directly
comparable because the scored populations differ; the important diagnostic is that a seemingly
minor target-lineage choice changes both fitting and ranking.

## Failure inspection

One batch-2 cell, `severson:el150800460605`, is an extreme extrapolation case. It survives the
100-cycle feature cutoff and has an observed life of 145 cycles, yet the three trajectory-derived
primary models predict approximately 2.2, 2.8, and 5.9 cycles. These physically inconsistent
predictions are retained, not clipped. The context-only model instead predicts about 919 cycles
and also has a large error. This cell dominates the worst-case errors and shows why pooled MAE is
not enough for a decision-facing claim.

This is not a reason to delete the cell post hoc. It is evidence that an eventual prospective
study needs a failure-aware target, a declared extrapolation policy or physical constraint, and
worst-environment/worst-subgroup harm checks.

## Interpretation boundary

The result cannot answer the industry-level question by itself because:

- X100 is a per-cycle discharge-capacity summary, not native within-cycle electrochemistry;
- S100 is a deterministic proxy, not an actual practitioner report;
- cycle life is derived from the future of the same discharge-capacity channel, not an independent
  qualification or functional assay;
- only three collection batches exist, with charge policies nested inside batches;
- censored cells are retained but not used by the scalar learner; and
- one frozen linear learner family cannot establish that no usable information exists in X100.

The defensible conclusion is narrower: the audit software can now localize and expose support,
provenance, transfer, and extrapolation failures, and Severson does not supply stable evidence for
an X100-over-S100 advantage under this frozen learner and estimand.

## Decision and next actions

1. **Stop representation mining on Severson for the main claim.** Keep this run as a regression
   fixture and nonconfirmatory case study; further model selection on the same three batches would
   spend the remaining degrees of freedom without fixing the identification problem.
2. **Start at the partner-entry gate.** Complete the
   [downstream endpoint and decision card](downstream_endpoint_decision_card.md) for candidate
   workflows and request one golden bundle containing native evidence, every intermediate,
   the actual conventional report, a delayed outcome, failures/censors, lineage, and costs.
3. **Require a crossed collection.** The conventional report fields and key process conditions
   must recur across independent material/manufacturing batches; hold out a later batch and then an
   independent site. A design with policies nested in batches cannot identify a batch-transfer
   claim.
4. **Choose an independent, failure-aware endpoint.** Prefer cumulative delivered performance,
   survival/degradation, strength, corrosion, catalyst retention, or final-spec distance with
   explicit censoring—not simply a later value of the same early channel.
5. **Freeze the operational decision and costs.** Define the action, deadline, smallest useful
   risk improvement, harm bound, storage/latency cost, and decision utility before outcome access.
6. **Use the golden bundle only for mechanics.** Validate the unit graph and transformation DAG,
   then run cluster-aware simulation for batches, policies, failures, and censoring before freezing
   the prospective sample and model-family envelope.
7. **Treat a paper as conditional on the next study.** The current framework plus calibrated
   known-loss/known-adequacy controls can support a methods paper; a stronger materials-discovery
   paper needs an actual report edge, an independently measured consequential outcome, and
   replicated held-environment evidence. Severson alone is an appendix-quality demonstration, not
   the novelty claim.

