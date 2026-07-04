# Friend-XRD Experiment Portfolio (parked — return later)

Context (2026-07-03): a friend can run experiments on their XRD and is standing up a
process-recording lab (records the full experiment, possibly on video) — the kind of
business whose *product is the process record*, unlike existing CROs whose incentives
delete the process and the failures. This note parks the strategy; not started yet.

## Why this partner matters (the "why still barren" answer)

Existing contract labs / cloud labs physically generate huge experimental volume but never
produce an ImageNet moment because: (1) client data is contractually private —
confidentiality *is* the product, so the aggregate corpus is legally shredded into silos;
(2) the billable deliverable is the *answer* (certificate, phase ID, purity), so the
process trace is exhaust and **failed runs are silently redone, never recorded** — CROs are
failure-deletion machines by design; (3) no shared event schema and no agreed task, so even
where volume exists there is no benchmark. Materials Project *did* have its moment, but in
*simulation* (DFT, born protocol-complete, known objectives) — which is why GNoME/UMA
harvested it and why it stops at the lab door: it says nothing about whether a material can
be made, by what route, or why attempts fail. A process-recording lab is the first business
whose incentives point at the missing substrate: it owns the instrument+software (provenance
logged natively, born L1+), sees failures before the client filters them (L2 is a policy
choice, not a culture war), and runs many conditions on one instrument (natural
counterbalancing). This is also the adoption path the grammar needs — standards spread as
the exhaust of tooling people want to use.

## Three-tier portfolio (cheapest first; each gives the friend something they need)

Designs are **system-agnostic on purpose** — the value is in the design (causal provenance,
known continuum, born-L3), not the chemistry. Swap the material to whatever their platform
handles natively; that is the *right* choice because the point is their process record.

### Tier 1 — Instrument-fingerprint round-robin (START HERE; ~1–2 days, no synthesis)

Measure 5–10 stable reference powders (NIST Si/LaB6/corundum + commercial quartz, calcite,
TiO2) — the *same physical samples* — repeatedly under systematically varied collection
conditions: session/day, operator (if two), repacked vs untouched between scans, 2–3
acquisition settings (scan speed, step size, slits). ~60–100 scans.

- **Unique value:** our entire provenance branch is *observational* — we detect lab
  fingerprints in others' data and statistically untangle instrument from chemistry. This
  has **causal ground truth**: we set the factor that varies. Pre-registered question: which
  factors does the audit detect after normalization (repack? session? operator? settings?).
  No such dataset exists anywhere. Upgrades the methods paper from "we observed leakage" to
  "we induced and isolated it."
- **What the friend gets:** a QC characterization of *their own* instrument (drift, session
  effects, operator sensitivity, settings fingerprint) + the audit tool as a client-facing
  measurement-consistency proof. We characterize their machine *for* them.
- **Discipline:** pre-register even though time is "free" — free access is exactly when
  leaderboard-drift returns.

### Tier 2 — Lossy-label intervention (the thesis, made causal; ~40–50 scans)

Weighed physical mixtures of two distinguishable phases (calcite/aragonite or
anatase/rutile) at 0,10,…,100%, each composition prepared 3× independently
(separate weighings/grindings, counterbalanced across sessions per the pilot stress-test).
After the raw data freezes, 2–3 people assign the standard paper labels ("phase pure",
"two-phase", "trace impurity").

- **Unique value:** our strongest real-data result (RRUFF Run 011 — species labels bin a
  continuum raw spectra retain) was *observational* on minerals nature made. Here we
  *manufacture* the continuum with known ground-truth fractions: raw XRD recovers the
  continuous mixing fraction on held-out samples; the labels collapse it into 2–3 bins; we
  state exactly how many percentage points the label discards, because we made the answer.
  Lossy-labels as intervention, not inference.
- **Prior-art guard:** quantitative phase analysis (Rietveld QPA) is mature — frame the
  novelty as *label-lossiness + provenance-stressed evaluation*, NOT "we can quantify
  mixtures."
- **What the friend gets:** a demonstration on their machine that their process-recording
  deliverable captures information the standard report format provably discards — their
  product argument, made citable.

### Tier 3 — Born-conformant making-event pilot (the flagship; weeks, phased)

The full Track B design the repo has been blocked on: CaCO3 crystallization, 16 planned
conditions × 3 replicates, counterbalanced operator/session/reagent-lot/run-order, process
logged **with their video infra as the process log**, failures/ambiguous retained, 3–4 timed
partial observations per event (quenched aliquots), labels frozen after raw. Safe cheap
chemistry (CaCl2 + Na2CO3).

- **Unique value:** the first dataset ever published **born at conformance L3** — designed
  to the grammar, not retrofitted (every public dataset we graded tops out at L1 except
  Severson's incidental L3). The data paper + the on-thesis A/B substrate.
- **What the friend gets:** their launch case study — "first conformance-graded experimental
  event dataset collected on our platform," a Scientific Data paper with their lab named +
  co-authorship + a worked example of their premium tier.

## The incentive frame (they're part of something big — and it's true)

Offer, roughly verbatim usable:

- **Their lab = the reference implementation** of the event grammar — the schema their
  software emits, co-developed, with L0–L3 conformance as their product tiers.
- **Co-authorship** on both papers (methods + data), instrument + platform named —
  legitimacy at launch that money can't buy.
- **Audit tooling transfers to them** — provenance/conformance audits become their internal
  QC + a client-facing trust artifact ("here is the leakage audit of our own instrument").
- **Asks sized to respect their time:** Tier 1 is a couple of days and pays back immediately;
  nothing bigger until Tier 1 proves the collaboration works.

Deliberately NOT doing: (a) leading with the big pilot — Tier 1 is the trust-builder and
spends the least goodwill; (b) running anything un-pre-registered because access is suddenly
free.

Honest caveat (our own `selection_risk` flag raises it): one friend's lab = one provenance
unit, so *cross-lab* claims stay out of reach — but *designed variation within* one lab
(sessions, operators, settings) is exactly what Tier 1 exploits, and intervention at one
site beats observation across six.

## Next artifacts when we return

1. Tier 1 round-robin **pre-registration** (sample list, factor grid, scan budget, what the
   audit must detect, falsifiers) — highest value per unit of goodwill; do first.
2. One-page **partner brief** in business language (event-record-as-deliverable, product
   tiers, co-authorship) for the friend.
