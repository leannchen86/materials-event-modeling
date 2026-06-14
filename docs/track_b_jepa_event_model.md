# Track B JEPA Event Model (design sketch)

Status: design sketch, not yet run. Extends [track_b_masked_event_model.md](track_b_masked_event_model.md)
and [capture_vs_representation_design_note.md](capture_vs_representation_design_note.md).

## Purpose

The current masked event model reconstructs the raw missing measurement (or its PCA, or a
residual over IDW). That objective is partly solvable by coordinate interpolation — `random_axis`
stays geometry-solvable and IDW is a strong baseline by construction. A reconstruction loss
*rewards* recovering smooth, interpolable structure, which is exactly the structure we do not
want the representation to spend capacity on.

JEPA (joint-embedding predictive architecture) changes the target from "the raw missing
measurement" to "the *latent* of the missing measurement." Predicting in latent space does not
reward raw smoothness, so it is a candidate route out of the geometry/IDW trap; and per the
time-series JEPA literature it tends to organize trajectories by dynamical regime without labels —
pre-taxonomic event discovery stated as an objective.

## Mapping to the event setting

Event = a set of (coordinate/time token, measurement) observations. Split each event into a
context subset (observed) and a target subset (masked), exactly as today.

- Context encoder `f_theta`: set encoder over observed tokens -> context state. (Reuse current encoder.)
- Target encoder `f_xi`: encodes the masked measurement(s) -> `z_target`. **Stop-gradient**; `xi` is an
  EMA of `theta` (no gradient flows into the target branch).
- Predictor `g_phi`: (context state, target coordinate/time token) -> predicted latent `z_hat`.
- Loss: latent distance `d(z_hat, z_target)` (smooth-L1 or `1 - cosine`). **No raw reconstruction in
  the training loss.**

Only the target and loss change vs the existing masked model; the set encoder and masking carry over.

## Why this targets the IDW trap

- IDW/ridge live in raw-measurement space and win when the missing value is a smooth function of
  coordinates. The JEPA target is a *learned* latent; if `f_xi` learns to discard the smoothly
  interpolable component (low event-discriminative value), the predictor is no longer scored on
  reproducing it, and capacity moves to the event-specific, non-interpolable part.
- Decisive question: does JEPA beat IDW / coordinate_ridge specifically on `random_axis` — the
  regime that stayed geometry-solvable under reconstruction? That is the falsification that matters.

## Collapse guards (mandatory — JEPA's known failure mode)

Predicting in latent space invites trivial constant solutions. Use at least one, ideally two:

- EMA target encoder + stop-gradient (I-JEPA / BYOL style), momentum ~0.99-0.999.
- Asymmetric predictor (only the online/context branch has the predictor head).
- VICReg-style variance + covariance terms on embeddings (explicit anti-collapse).

A collapsed run can manufacture a fake "win," so every JEPA result must report a collapse
diagnostic (embedding std / effective rank across a batch) next to the task metric.

## Evaluation (must satisfy existing stop rules)

JEPA's native loss is in latent space and is NOT comparable to IDW's raw MSE — so do not compare
losses. Freeze the trained context encoder, then run the SAME downstream-operational probes as
today, against the SAME baselines:

- missing-measurement prediction via a small decoder head on frozen embeddings,
- replicate retrieval,
- held-out provenance-split transfer (operator / batch / instrument / source),
- inherited label as a downstream probe (compactness / predictability), never a training target.

Baselines unchanged: `event_mean`, `nearest_neighbor`, `idw_all`, `coordinate_ridge`,
`rf_event_field`, and the existing `raw_set` / `raw_residual` masked models. JEPA must beat these
on held-out provenance splits to count.

## Hypotheses

- HJ1: Frozen JEPA embeddings predict missing measurements better than train-mean and at least
  match `raw_set` on held-out regimes.
- HJ2: On `random_axis`, JEPA beats `coordinate_ridge` / IDW. (The geometry-trap falsification —
  the one that matters.)
- HJ3: JEPA embeddings give better replicate retrieval and provenance-split transfer than the
  raw-reconstruction embeddings (representation gain, not just reconstruction).
- HJ4: Collapse diagnostics stay healthy; ablating the anti-collapse term degrades the task metric
  (proves the win is not collapse).

## Risks / honesty

- Data scarcity raises collapse risk; small synthetic / early Track B sets may not support JEPA.
  Test on a real trajectory dataset with enough events first.
- The loss function is now the ontology (it defines what "predictable" means). Document the masking
  distribution and latent-distance choice as design commitments, not neutral defaults.
- A latent representation is not directly actionable for intervention — keep a decode-to-measurement
  head for the human/actionable view, used at eval/inspection time only.

## Next

Run on a real time-resolved trajectory dataset, not the current synthetic scaffold (stop rule).
Primary candidate: oleogel polymorphic-transition data (1 s time-resolved WAXS + SAXS + microscopy
+ DSC, zenodo 15268752); thesis-cleanest backup: zeolite crystallization (in situ Raman trajectory
+ PXRD endpoint, zenodo 18972297). See the dataset hunt in
[capture_vs_representation_design_note.md](capture_vs_representation_design_note.md).
