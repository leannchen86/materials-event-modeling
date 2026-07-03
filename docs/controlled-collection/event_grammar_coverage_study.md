# Event-Grammar Adapter-Coverage Study (rung 1 + rung 2)

Started 2026-07-03. Ladder placement: rungs 1 (coverage) and 2 (audit power) of
[../spine/event_grammar_validation_note.md](../spine/event_grammar_validation_note.md).
Null attacked: paper-shaped public data already records what the event grammar demands, so
the grammar adds nothing a schema-less audit would not show.

## Setup

Grammar v1 is frozen before this study:

- Envelope: [`schemas/event_grammar.v1.schema.json`](../../schemas/event_grammar.v1.schema.json)
  — five slots (intent, observations, outcome, provenance, labels-after-raw), domain
  payloads namespaced inside observations. The CaCO3 pilot schema stays as a domain
  instance.
- Conformance ladder: [`src/materials_event_modeling/grammar/conformance.py`](../../src/materials_event_modeling/grammar/conformance.py)
  — L0 raw trace, L1 provenance, L2 negatives + frozen labels, L3 counterbalanced;
  graded by [`scripts/audit_event_grammar.py`](../../scripts/audit_event_grammar.py).

One adapter per locally available public dataset maps the source into envelope events
(`scripts/adapters/adapt_<dataset>.py` → `data/interim/event_grammar_v1/<dataset>/events.json`),
then the conformance audit grades it. Adapters must not fabricate: a slot the source does
not record stays null/unknown and is logged as a mapping gap — the gaps are the data.

Datasets: Durham droplets, oleogel SAXS/WAXS, Severson battery, HTEM (processed
event-proxy tables), NIST combinatorial XRD, RRUFF (deliberate stress case: a
measurement archive, not an event archive). Not locally available — documented as
access-friction findings, not graded: Dryad gelation (5.14 GB single zip, never
downloaded; figure-shaped), OpenCrystalData (Kaggle-gated).

## Pre-registered hypotheses (committed before writing any adapter)

Predicted conformance levels:

| dataset | predicted level | expected blockers |
| --- | --- | --- |
| durham_droplets | L0 | no provenance axes; no outcome status; no failure log |
| oleogel | L0 | intent exists (material × shear) but ≤1 provenance axis; no negatives |
| severson_battery | **L1** | batch date + channel are real axes; intent = charge policy; no failed/aborted cells marked |
| htem | L0 | intent = deposition recipe; provenance axes absent from public records |
| nist | L0 | multi-labeler labels (showcase) but freezing unverifiable; no negatives |
| rruff | L0 (degenerate) | grades L0 but multi-observation fraction ≈ 0 — richness exposes it as a measurement archive |

- **H1 (coverage).** All six map into the envelope with no structural change to the
  schema. *Falsifier:* any dataset that cannot be expressed without modifying the
  envelope → grammar v1.1 finding, weakens the universality claim.
- **H2 (ceiling).** No public dataset exceeds L1. *Falsifier:* any dataset reaches L2 —
  public data is more event-native than assumed, which weakens the case for controlled
  collection.
- **H3 (gap pattern).** The dominant blockers, in order: negative outcomes never
  recorded; provenance axes missing; intent absent except where the dataset was born
  from a designed sweep (Severson policies, oleogel shear settings, HTEM recipes).
- **H4 (degenerate case).** RRUFF grades L0 with trace richness ≈ 1 observation/event —
  the grammar distinguishes measurement archives from event archives by *richness*, not
  by failing to express them.
- **Decision this changes:** whether grammar v1 freezes as-is for the Phase 2
  representation A/B test, and which datasets qualify for it (predicted: oleogel and
  Severson — the only ones with both traces and any provenance/intent).

## Results

*(to be filled after the adapters run — conformance table, per-dataset mapping gaps,
verdict against H1–H4)*
