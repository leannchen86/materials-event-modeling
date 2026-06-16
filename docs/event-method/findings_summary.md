# Findings Summary — Real-Data Campaign (Runs 001–013)

Date: 2026-06-15 · Branch: event-method · Per-run detail: [run_log.md](run_log.md) ·
Audience: collaborator handoff / controlled-collection rationale.

**One-line story:** on a homogeneous *trajectory* dataset, raw data added nothing beyond a simple
time-prior (a *data* limit, proven not a model limit); on a large *labeled* dataset, raw
measurements demonstrably carry — and recover — structural information the inherited label throws
away, precisely where the label bins a continuum. **Raw data's value appears exactly where the
inherited label is lossy.**

## The question
Project thesis: representations learned from **raw** material-making event data can be more
useful than the **inherited human labels** (phase, polymorph, success). The "refined-a" stage
tests this on a real time-resolved trajectory dataset, without building a lab rig.

## Part 1 — Oleogel trajectory data (Runs 001–008): the negative result

### The dataset, and why we chose it
[zenodo 15268752](https://zenodo.org/records/15268752) — in-situ synchrotron SAXS+WAXS of
monoglyceride oleogel **polymorphic transitions**: 6 runs (2 materials × 3 shear settings),
~300 frame-aligned SAXS+WAXS frames each, a replicate, and a d-spacing label table. Chosen as
the best *immediately-runnable, on-thesis, interpolation-resistant, multimodal, open*
trajectory dataset. Known weakness from day one (dataset audit): only 6 events → cross-event
transfer would be thin.

### What we ran, and what each taught (oleogel)
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

### Headline findings (oleogel)
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

The oleogel binding constraint is **event diversity/count**, proven (not assumed) to *not* be
model capacity. So we pivoted to a large *labeled* dataset to test the thesis where it can bite.

## Part 2 — RRUFF labeled minerals (Runs 009–013): the positive result

[RRUFF](https://rruff-2.geo.arizona.edu/) — ~11,400 curated mineral Raman spectra, 1,958 labels,
each with composition and a status flag, including the CaCO3 polymorphs. Capacity-free k-NN,
specimen-grouped, gap-over-controls throughout.

| Run | Test | Outcome |
| --- | --- | --- |
| 009 | label-probe at scale | raw predicts the mineral 0.88 (59 classes) — but **composition does too (0.84)**: for common minerals the label ≈ chemistry |
| 010 | polymorph probe (composition constant) | where composition is constant, raw recovers the polymorph **0.91–1.0** vs majority 0.40–0.74 (**CaCO3 0.975**; + TiO2/Al2SiO5/SiO2) |
| 011 | solid-solution species vs family | garnet **family 1.0** but **species 0.73**, with **100% of species errors within-family** → species labels are lossy bins on a continuum |
| 012 | robustness ablations | survives single-wavelength; distinct-5 minerals 0.99 vs garnet species 0.73 (the gap is the continuum, not difficulty); robust under error bars + balanced accuracy |
| 013 | peaks-only vs heavy-blur | **peaks-only ≈ full** everywhere; broad-shape-only collapses (CaCO3 below majority) → the signal is the genuine Raman fingerprint, not lab/baseline artifacts |

### The three-way taxonomy (the finding)
An inherited label is —
- **redundant** when it merely re-encodes composition (common minerals, Run 009);
- a **natural coordinate** when it marks a real structural discontinuity (polymorphs, Run 010 —
  raw recovers it where chemistry cannot);
- **lossy** when it bins a continuum (solid-solution species, Run 011 — raw keeps the continuous
  axis the discrete name discards).

Fully stress-tested (Runs 012–013): not a laser/provenance shortcut, not multi-class difficulty,
robust to error bars, and reading the real Raman fingerprint.

## The synthesis (the campaign's answer)
**Raw data's value appears precisely where the inherited label is lossy.** On homogeneous
trajectories (oleogel) the label-equivalent — the time-course — already captures everything, so
raw adds nothing. On labeled minerals (RRUFF) raw adds exactly what the label throws away:
structure beyond composition, and the continuous coordinate beneath a discrete name. Direct,
evidence-backed answer to "are labels natural coordinates, lossy projections, or artifacts?":
**it depends, and we now know on what.**

## Where it goes next (kept open on purpose)
We are deliberately **not** committing to a single "prove raw is more *useful*" benchmark —
chasing one fixed usefulness metric risks over-optimising a narrow task and calcifying the work
(the same trap the project's own stop-rules guard against). The taxonomy above is a
*characterisation*, and that is itself a contribution. Usefulness, if pursued, should be
**opportunistic and need-driven** — e.g. surfacing mislabeled/ambiguous specimens, or recovering
continuum coordinates a practitioner actually wants — explored lightly, not optimised. Standing
options, no forced order:
- the structure-vs-continuum taxonomy is handoff-ready as a result on its own;
- **controlled-collection** remains the moat for the *process/event* half of the thesis (the
  oleogel negative is its empirical justification);
- any usefulness probe stays plural and need-driven, not benchmark-driven.
