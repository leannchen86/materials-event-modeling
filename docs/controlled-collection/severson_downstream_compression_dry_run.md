# Severson Downstream-Compression Dry Run

Status: **retrospective, post-hoc, nonconfirmatory engineering design**, frozen before the new
implementation and run on 2026-07-11. This document is not a preregistration: the dataset outcomes
and related early-trajectory analyses have already been inspected in this repository. Its purpose
is to exercise the complete downstream audit path before a partner study, not to create a new
battery-lifetime claim.

Amendment history: commit `c6a0b76` froze the initial design. A subsequent provenance review,
before repository implementation, found that five nominal batch-1 targets are resolved from
batch-2 barcode continuations. The primary target universe was therefore changed to exclude those
five cells from **both fitting and scoring**, with the all-observed-EOL analysis retained only as a
contaminated sensitivity. This is a leakage correction, not a result-driven estimand change; the
run remains explicitly nonconfirmatory and the expected-result section below is unchanged.

Program parent:
[downstream_failure_research_program.md](../spine/downstream_failure_research_program.md).
Existing related result:
[severson_heldout_batch_ranking.md](severson_heldout_batch_ranking.md).

## Engineering question

Can the repository produce a reason-coded attempt ledger, strictly held-batch out-of-fold
predictions for a verified compact-summary edge, and a support-aware compression audit for a
delayed outcome without silently deleting censored cells or overstating the retained trace as raw?

The descriptive scientific question is narrower:

> Among cells with observed end of life, does the complete retained early discharge-capacity
> trajectory improve held-batch cycle-life prediction beyond a deterministic seven-scalar summary
> of that same trajectory, under one frozen ridge learner family?

## Known limitations fixed before the run

- `X100` is a per-cycle summary trajectory, not native within-cycle electrochemistry.
- `S100` is a report-shaped engineering proxy, not an actual practitioner QC report.
- The seven S100 formulas and their relationship to cycle life were explored in earlier repo runs.
- Cycle life is derived from the future of the same discharge-capacity channel used in X100; this
  is future-trajectory prediction, not an independent functional assay.
- Severson has three observed collection batches, zero charge-policy overlap across batches, and
  strong batch identity in early trajectories. Held-batch evaluation therefore jointly stresses
  collection shift and unseen-policy extrapolation.
- Seven truncated cells are right-censored. The v0 scalar evaluator cannot use their partial target
  information, but they remain in the attempt and target-support ledger.
- Five long-lived batch-1 cells use later batch-2 barcode continuations for the outcome. If those
  targets train a model whose held environment is batch 2, information from the held environment
  enters through target provenance. Continuation identity and existence are never input features.
  The primary analysis excludes all five continuation-derived targets globally; a separate
  all-observed-EOL sensitivity refits the complete pipeline and is labeled contaminated.

No result from this run enters the headline results ledger or earns `raw`, `industry report`,
`adequate`, `premature compression`, or `transferable across future batches` language.

## Frozen subjects, context, cutoff, target, and environment

- **Attempted subjects:** all 135 adapted physical-cell events in
  `data/interim/event_grammar_v1/severson_battery/events.json`.
- **Context C:** `cell.charge_c_rate_1`, `cell.soc_switch_percent`, and
  `cell.charge_c_rate_2` from the planned charge policy.
- **State cutoff:** end of cycle 100. Only quality-accepted observations at cycles 2--100 may
  enter an arm.
- **Target Y:** `log10(cell.cycle_life_cycles)` for observed-EOL cells.
- **Target support:** 128 observed-EOL cells, of which five have cross-batch continuation-derived
  targets. The primary analysis uses the other 123. Seven truncated/right-censored cells stay in
  the ledger with their lower bound and an unavailable scalar target.
- **Environment E:** primary collection batch from `provenance.batch_id`.
- **Uncertainty cluster:** charge-policy `event_group_id`, not cell or cycle.
- **Primary descriptive loss:** MAE in log10 cycles.
- **Primary transfer design:** leave one complete batch out. The three fixed folds are reported
  separately; no random split is produced by this run.

Expected invariant counts before modeling are 135 attempts, 128 exact observed-EOL targets, five
cross-batch continuation-derived targets, 123 primary scalar-target-eligible cells, seven
right-censored cells, and three held-batch folds. Primary outer train/test target counts are
`87/36`, `80/43`, and `79/44` when holding out batches 1, 2, and 3 respectively. A count mismatch
stops the run.

## Frozen representation graph

Use discharge capacity only so the audited edge is genuinely nested:

```text
C: three planned charge-policy scalars

X100: QDischarge at cycles 2, 3, ..., 100             (99 values)
  |
  +-> S100: deterministic summaries of exactly X100  (7 values)
```

The seven S100 values, in order, are:

1. mean capacity;
2. capacity at cycle 100;
3. OLS slope over cycles 2--100;
4. maximum minus final capacity;
5. final minus first capacity;
6. OLS slope over cycles 51--100 (array indices `49:99`); and
7. `log10(var(first differences, ddof=0) + 1e-12)`.

Frozen arms:

1. `C`;
2. `C_S100`;
3. `C_X100`;
4. `C_S100_X100`.

Frozen comparisons:

- `C -> C_S100`;
- `C -> C_X100`;
- `C_S100 -> C_S100_X100` — conditional value of the trajectory beyond the compact summary;
- `C_X100 -> C_S100_X100` — finite-learner/sample-efficiency value of making the deterministic
  summary explicit; and
- `C_S100 -> C_X100` as a descriptive direct risk contrast, not the conditional TRCL contrast.

## Fixed-grid and availability rule

For each cell:

1. retain only quality-accepted observations with `2 <= cycle_index <= 100`;
2. require valid observed endpoints at cycles 2 and 100;
3. linearly interpolate only missing interior cycle values from observations inside the cutoff;
4. prohibit cross-cell imputation, learned imputation, extrapolation, or any value after cycle 100;
5. construct S100 from the resulting X100 array, never independently; and
6. record the observed/interpolated 99-bit mask in the ledger but do not use it as a feature.

`S100=f(X100)` must pass an exact helper-level test. Any cell failing the endpoint rule remains an
attempt but marks both S100 and X100 unavailable with a reason code.

## Frozen learner and folds

Use one finite learner family to test the software path:

```text
StandardScaler -> Ridge(alpha selected inside outer training data)
```

For each arm and held-batch outer fold:

- tune `alpha` over `[1e-3, 1e-2, 1e-1, 1, 10, 100, 1000]`;
- use inner `GroupKFold`, grouped by charge policy, with the number of splits capped by the number
  of represented training policies and at most five;
- score each candidate alpha by the mean of its per-policy inner-OOF MAEs and choose the smallest
  alpha on an exact tie;
- fit every scaler and ridge model without sample weights, only on outer-training cells eligible
  for that analysis universe;
- predict every representation-available attempt in the held batch once, including cells without
  an eligible scalar target, but score only the analysis universe;
- record train/test event counts, target counts, batch IDs, policy sets or hashes, chosen alpha,
  and all out-of-fold predictions; and
- assert that no event or policy appears in both sides of an outer fold.

Policy overlap is expected to be zero because the source batches use disjoint policies. That is a
property of this dataset, not a feature of a generally valid batch test.

Run this entire nested procedure twice rather than masking a shared prediction ledger after fit:

1. `primary_no_cross_batch_continuations`, with 123 exact targets; and
2. `all_observed_eol_sensitivity`, with 128 exact targets and an explicit
   `cross_batch_target_provenance=true` contamination flag.

The second analysis is diagnostic only. Any changed alpha, scaler, coefficient, or prediction is
part of the sensitivity and must be retained in the manifest.

## Weighting and audit call

Primary risk is policy-macro: each eligible cell receives weight inversely proportional to the
number of eligible cells in its charge policy, normalized only by the risk aggregator. Cell-micro
risk is a labeled sensitivity. Policy-macro weighting determines inner alpha selection and final
evaluation; it does not weight the ridge fits themselves.

Call `audit_prediction_bundle` with:

- `absolute_error` and `mean_risk`;
- clusters = charge policy;
- environments = batch;
- `environment_evaluation="held_out_environment"`;
- `transfer_rule="all_environments"`;
- `risk_tolerance=0.0` only to obtain directional paired gaps and intervals; and
- `n_boot=2000`, seed 0.

The surrounding manifest overrides inferential wording with:

```text
inference_status = retrospective_posthoc_nonconfirmatory
core_verdict_not_for_scientific_inference = true
```

No zero-tolerance core token is quoted as a scientific adequacy or material-loss verdict.

## Expected result before the run

Based on the already known held-batch difficulty, predict:

- all four arms receive complete held-batch predictions for the 128 observed-EOL cells;
- C is materially weaker than at least one trajectory-derived arm;
- policy-macro held-batch MAE is roughly 0.15--0.30 log10 cycles across arms;
- S100 and X100 are close, with a pooled conditional gap likely between -0.02 and +0.02 log10
  cycles and heterogeneous batch signs;
- C_S100_X100 may beat either constituent under finite-sample ridge, but not consistently enough
  to support a transfer claim; and
- batch 3 produces the widest policy-cluster uncertainty because it has few policy groups.

A large uniform X100 win would be surprising and require raw prediction/worst-case inspection. A
large C win would trigger checks for scaling, interpolation, target alignment, and batch/policy
shift before being interpreted as useful compression.

Back-transform every OOF prediction to cycles for diagnostics. Report, but never clip, predictions
below cycle 101 because all exact observed outcomes occur after the feature cutoff. Also report the
worst absolute-error cells for each analysis and arm so a pooled contrast cannot hide a single
extrapolation failure.

## Stop conditions and interpretation

Stop as an implementation/data failure if:

- invariant counts differ without an explained source-version change;
- any post-cutoff value enters X100 or S100;
- S100 cannot be reproduced exactly from X100;
- an outer fold shares events or policies across train and test;
- any target-derived field, censoring flag, continuation flag, batch ID, or event ID enters a
  predictive arm;
- a prediction is not strictly out of fold; or
- the manifest omits censored cells, availability reasons, or per-batch results.

Interpretation rules:

- `C_S100_X100` better than `C_S100` is descriptive evidence that curve detail helps this finite
  learner on these observed cells, not proof that a conventional report loses industrial value.
- `C_S100` matching or beating trajectory arms is useful evidence that a compact deterministic
  summary is sample-efficient; it does not mean the upstream trajectory contains less Shannon
  information.
- a pooled gain that changes sign by batch is heterogeneous/provenance-sensitive.
- any apparent win disappears from the scientific program unless an actual practitioner report,
  independent downstream assay, and materially adequate transfer design later reproduce it.

## Output contract

Add, without modifying prior Severson artifacts:

- pure helpers in `src/materials_event_modeling/eval/severson_downstream.py`;
- runner `scripts/run_severson_downstream_compression_audit.py`;
- tests in `tests/test_severson_downstream.py`; and
- manifest `data/manifests/severson_downstream_compression_audit.json`.

The manifest contains design status, source/hash and run identity, invariant counts, target/support
reasons, arm definitions and parent DAG, fold metadata, row-level OOF predictions, policy-macro and
cell-micro audit blocks, per-batch results, continuation sensitivity, and an explicit verdict.
