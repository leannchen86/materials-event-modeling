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

## Results (2026-07-03)

Six adapters built (`scripts/adapters/adapt_*.py`), each independently verified by an
adversarial agent that traced slot values back to the raw source and re-ran the grading
CLI. One fabrication was caught and fixed (Severson outcomes, below); several silent
field drops were disclosed or repaired. Conformance manifests:
`data/manifests/event_grammar_conformance_<dataset>.json` (with run identity); events are
regenerable deterministically from `data/raw/` via the adapters.

| dataset | events | median obs/event | multi-obs | level | predicted |
| --- | ---: | ---: | ---: | --- | --- |
| durham_droplets | 9 | 305 | 1.00 | L0 | L0 ✓ |
| oleogel | 9 | 596 | 1.00 | L0 | L0 ✓ |
| severson_battery | 46 | 857.5 | 1.00 | **L3** | L1 ✗ |
| htem | 95 | 131 | 1.00 | **L1** | L0 ✗ |
| nist | 44 | 8 | 1.00 | L0 | L0 ✓ |
| rruff | 3,230 | 2 | 0.69 | L0 | L0 ~ |

Selection-risk (from the conformance tool's `selection_risk` block): 5 of 6 datasets flag
`high_no_negatives_recorded`, and even L3 Severson flags `few_provenance_units` (3 batches)
— see [../spine/data_assumptions_and_limits.md](../spine/data_assumptions_and_limits.md)
for the full data-limitations treatment.

Not graded (access friction, the finding itself): **Dryad gelation** — one 5.14 GB
monolithic zip organized by paper figures, never locally downloadable in this study; no
event manifest at the public interface. **OpenCrystalData** — Kaggle-auth-gated; framed
as image-ML tasks, no event structure visible from metadata.

### Verdict against the pre-registered hypotheses

- **H1 (coverage) validated.** All six datasets mapped into the envelope with zero
  changes to the schema — including the stress case. The grammar's five slots were
  sufficient; every gap was a *content* gap in the source, not a *structure* gap in the
  envelope. Grammar v1 freezes as-is.
- **H2 (no dataset exceeds L1) FALSIFIED — the study's most informative result.**
  Severson grades L3: real intent (the charging-policy sweep, 22 replicated policy
  groups), two logged provenance axes (batch date, cycler channel), and — after honest
  outcome derivation — retained negatives (10 of 46 cells whose records end 0.913–1.04 Ah,
  well above the 0.88 Ah EOL criterion: truncated runs, distinguishable from the file's
  own capacity data). HTEM also beat its prediction, reaching L1: its public records
  carry real `operator_id` and `instrument_id` fields. Public data is not uniformly
  provenance-blind; *designed sweeps born on automated equipment* (cyclers, combinatorial
  deposition) record more of the grammar than manual-experiment deposits.
- **H3 (gap pattern) partially validated.** Negative outcomes and provenance axes are
  indeed the modal blockers (Durham, oleogel, NIST, RRUFF all fail L1 on axes and L2 on
  negatives). But intent was derivable in 4 of 6 datasets (Durham's README/filename
  conditions, oleogel's material×shear sweep, Severson's policies, HTEM's deposition
  recipes) — more than predicted. The scarce slots are outcome and provenance, not
  intent.
- **H4 (RRUFF degenerate) partially validated.** RRUFF grades L0 as predicted, but it is
  richer than predicted: 69% of specimens have ≥2 observations (multiple laser
  wavelengths — genuine measurement multiplicity), median 2 obs/event, not ~1. It is a
  *shallow-trace* archive, not a single-shot one; the richness metrics (not the level)
  are what separates it from true event traces (median 305–857 obs/event).

### What the verification stage caught (rung-2 evidence that audits have teeth)

1. **A fabricated outcome (fixed).** The Severson adapter initially marked all 46 cells
   `success`, "cycled to the 80% EOL criterion" — but 10 records end far above the
   criterion. Fixed by deriving status from the capacity data (clean gap: completed runs
   end 0.880–0.883 Ah, truncated runs 0.913+). The counterintuitive consequence: honest
   outcome derivation *raised* the dataset's grade (L1 → L3), because truncated runs are
   retained negatives. Honesty about outcomes is rewarded by the ladder, by design.
2. **Silent drops (disclosed or repaired):** RRUFF's non-matching filenames (94 → 4,
   now counted and printed, including the archive's only anomalous-outcome annotation,
   `laser_phase_change`, now preserved on its observation), UTF-8 headers decoded as
   latin-1 (fixed), dropped header fields (measured chemistry, cell parameters,
   description — now carried), Durham scalebars and payload prose (documented), oleogel
   docstring counts and zip-mtime dates (documented).

### Checker lessons (v1.1 candidates — recorded, not retro-applied)

- **L3 is satisfiable by incidental variation.** Severson's within-group provenance
  variation is the cycler's channel assignment — recorded, real, but not *deliberate*
  counterbalancing, and only one axis varies (batch is constant). A v1.1 candidate:
  require ≥2 varying axes, or distinguish "incidentally counterbalanced" from
  "deliberately counterbalanced". The lab pilot should be held to the deliberate bar
  regardless.
- **Richness needs a reporting tier.** L0 admits both 857-obs traces and 2-obs archives;
  the richness metrics carry the distinction but no level does. Keep richness as
  reported metrics for now; revisit after the Phase 2 A/B shows which richness floor the
  tasks actually need.

### Decision

Grammar v1 is frozen (H1 held). Phase 2 (representation A/B + slot ablations) proceeds
with **Severson** as the primary dataset (L3, real intent, retained negatives, 857
obs/event, 46 events) and **oleogel** as the trajectory-rich secondary (596 obs/event,
real intent, but only 9 events); HTEM (95 events, L1, spatial fields) is the transfer
stretch. The pre-registered prediction named oleogel + Severson; the study confirms the
pair but reverses their order.
