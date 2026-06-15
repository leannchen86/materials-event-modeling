# Findings Summary — Oleogel Real-Data Campaign (Runs 001–008)

Date: 2026-06-15 · Branch: event-method · Per-run detail: [run_log.md](run_log.md) ·
Audience: collaborator handoff / controlled-collection rationale.

## The question
Project thesis: representations learned from **raw** material-making event data can be more
useful than the **inherited human labels** (phase, polymorph, success). The "refined-a" stage
tests this on a real time-resolved trajectory dataset, without building a lab rig.

## The dataset, and why we chose it
[zenodo 15268752](https://zenodo.org/records/15268752) — in-situ synchrotron SAXS+WAXS of
monoglyceride oleogel **polymorphic transitions**: 6 runs (2 materials × 3 shear settings),
~300 frame-aligned SAXS+WAXS frames each, a replicate, and a d-spacing label table. Chosen as
the best *immediately-runnable, on-thesis, interpolation-resistant, multimodal, open*
trajectory dataset. Known weakness from day one (dataset audit): only 6 events → cross-event
transfer would be thin.

## What we ran, and what each taught
| Run | Test | Outcome / lesson |
| --- | --- | --- |
| 001 | overfit-one-event sanity | pipeline OK; "win" over interp was an under-powered (sparse-anchor) baseline |
| 002 | density sweep (fair anchors) | uncovered a **period-3 exposure artifact** poisoning interpolation |
| 003 | remove artifact, re-sweep | artifact gone; model still won within-event BUT **ignored its anchors** → memorised the trajectory curve |
| 004 | cross-event leave-one-run-out | dense interpolation beats the masked model **6/6**; model collapsed to a time-conditioned mean → raw reconstruction is the wrong objective |
| 005 | cross-modal (predict WAXS from SAXS) | a task interpolation can't do; bimodal — wins on 3 folds, extrapolation failures on 3; hit the 6-event ceiling |
| 006 | ablation suite | the **clock dominates**; most of the 005 "win" was the time/material prior; genuine cross-modal only on 2 DMHR folds |
| 007 | model-free distance correlation | looked strong 6/6 — but the time-shuffle null was confounded by shared smoothness |
| 008 | smoothness-controlled (circular-shift + cross-event null) | the apparent signal was shared smooth shape; **only 1/6** events shows genuine cross-modal excess |

## Headline findings
1. **Raw frame-reconstruction is interpolation-solvable** on dense smooth trajectories — a poor
   discriminator for any model (the synthetic `random_axis`/IDW result, confirmed on real data).
2. **The "clock" (normalised-time prior) is a dominant baseline** — beats the mean 6/6 and beats
   SAXS on the median. Many apparent wins were the time-prior in disguise.
3. **SAXS and WAXS are largely time-redundant** on this system — with proper smoothness controls
   only 1/6 events shows genuine cross-modal signal beyond the clock.
4. **This is NOT a model-capacity problem** — shown with a capacity-free dependence measure. It
   is a property of the data: homogeneous (one protocol) and event-poor.
5. **Both open in-situ crystallization deposits are event-poor** (oleogel = 6 near-identical;
   zeolite [18972297](https://zenodo.org/records/18972297) = 1 run). No public deposit we found
   provides many independent, varied events.

## Methodology takeaways (transferable)
- The predict-before / score-after run-log prevented a false-positive interpretation **4+ times**.
- Always include the **time-prior** and a **scrambled negative control**; tune baselines until
  they hurt; measure signal as a **gap over controls**, not absolute accuracy (robust to model
  quality and to small data).
- **Cross-event splits are mandatory** (within-event invites memorisation).
- **Characterise raw signal** (CV, autocorrelation, shape-vs-scale) before modeling — silent
  data artifacts hide here.
- For smooth time-series, significance needs **smoothness-preserving nulls** (circular shift)
  plus a **cross-event baseline**; a plain shuffle null is confounded by autocorrelation.

## Implications & next
The binding constraint is **event diversity/count**, proven (not assumed) to not be model
capacity. Squeezing oleogel further is not the move. Two productive directions:

1. **Label-probe** on a dataset with real labels AND many independent samples:
   - **RRUFF** (~4216 mineral specimens; Raman + XRD + chemistry; XRD/chemistry-validated
     mineral labels) — experimental, multimodal, and large, so cross-modal can also be retried
     at N≈4000 instead of 6. Strongest candidate.
   - **opXRD** ([arXiv 2503.05577](https://arxiv.org/pdf/2503.05577); ~1.4 GB on Zenodo) —
     experimental labeled powder XRD, already in the repo's orbit (provenance-critique).
   - **Avoid SimXRD-4M** — 4M *simulated* patterns; labels are ground-truth by construction, so
     there is no lossy-human-label problem to study (defeats the thesis).
   - Caveat: RRUFF/opXRD are *specimen-identity* classification, not synthesis-trajectory
     events — they test the "labels vs representation" half of the thesis, not the process half.
2. **Controlled-collection** — independent events across varied conditions/outcomes; this
   campaign is the empirical case for it.
