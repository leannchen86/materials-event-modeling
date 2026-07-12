# Controlled Pilot — Frozen Run-Protocol Draft

> **Frozen methods-design draft; do not execute.** It requires an observed partner workflow,
> opportunity/action inventory, practitioner-report validation, and capture-aware re-preregistration.

Companion to [pilot_design_prereg.md](pilot_design_prereg.md) (the why) and
[pilot_assignment.csv](pilot_assignment.csv) (the what: 48 events, pre-assigned to
sessions/operators/lots/run-order — regenerable via
`scripts/generate_pilot_assignment.py`, seed committed). This document is everything the
partner lab needs to execute; the design is ours, the running is theirs. Deviations are
fine — they must be *recorded*, never absorbed.

## Do-not-start gate

Before D1, the lab lead and study lead must record and verify all three values below. A blank,
placeholder, dirty-worktree description, or uncommitted file is a **stop**; do not begin an event.

- `design_lock_commit`: commit containing confirmed dates and certified assignment;
- `analysis_freeze_commit`: later commit in the same history certifying every preregistration,
  representation, outcome, and statistical freeze blocker; and
- `pilot_assignment_sha256`: hash of the exact CSV loaded for execution, matching the analysis-
  freeze manifest.

Both commits must precede the first event timestamp. Record the three values in the session-D1
header and have both leads sign the check. The current draft specifications do not satisfy this
gate merely by existing.

## Materials (per the whole pilot)

- CaCl2 and Na2CO3 (reagent grade). Prepare **two independent stock batches per reagent**
  (= lots L1, L2): separate weighings, separate bottles, prepared on different days,
  labeled. Record supplier, catalog number, batch/lot codes, prep date per bottle.
- MgCl2 for the additive factor (one stock is fine; record lot).
- Deionized water (record source), disposable cuvettes/vials, filter paper or 0.45 µm
  filters, drying oven or desiccator, pH meter (calibrated at session start — record the
  calibration), thermometer/hotplate with temperature control, timer.
- XRD sample holders for dried powders; camera/video rig running for the full session.

## Session structure (4 sessions, D1–D4, ~12 events each)

At session start, record once: date, operator(s) present, ambient temperature/humidity,
pH-meter calibration values, instrument warm-up state. Then execute the session's 12
events **in the run_order given by the table** (do not resort for convenience — run order
is a controlled axis).

## Per-event procedure

1. **Announce the event** on video: say the `event_id` aloud and show the printed table
   row (this timestamps intent before execution).
2. Prepare solutions per the row: `concentration_m` for both reagents from the row's
   `lot`; add MgCl2 at the row's `mg_ratio` (molar, vs Ca) to the CaCl2 solution;
   equilibrate both at the row's `temperature_c` (verify with thermometer, record actual).
3. Mix per `mixing_route`: **fast_no_aging** = pour Na2CO3 into CaCl2 in one motion,
   stir 10 s, stop; **slow_30min_aging** = add dropwise over ~2 min with gentle stirring,
   then leave undisturbed for 30 min. **In both routes the clock starts at first contact
   of the two solutions** — aging is part of the recorded event, so the t=5 and t=15
   aliquots fall *inside* the aging window for the slow route (withdraw them gently from
   the top without stirring; that is the intended design, capturing the aging trajectory).
4. **Timed observations** (the clock = first contact; the stated time is completed arrest,
   not withdrawal start):
   - t ≈ 5 min, 15 min, 60 min: begin withdrawing an aliquot (~2 mL) early enough to
     vacuum-filter or drop-and-dry on a labeled slide/holder and **rinse briefly with ethanol
     to arrest transformation** (amorphous/vaterite material keeps converting while wet — an
     un-arrested aliquot measures the drying process, not the solution state), then
     dry at ≤40 °C. The t60 arrest must complete at or before 60:00. Record withdrawal
     start, arrest start/completion, and pH/visual state (clear/cloudy/precipitate; color)
     for every pull. The exact arrest procedure/windows remain analysis-freeze items in
     [x60_input_spec.md](x60_input_spec.md).
   - t = 24 h (±2 h): collect the remaining solid the same way. Record final pH.
   - Throughout: video runs; note any disturbance, spill, hesitation, or deviation as a
     timestamped `human_note` — deviations are data.
5. **XRD scans:** scan all dried aliquots. Scan order is randomized *across* events within
   a measurement batch (do not scan one event's four aliquots back-to-back); log the scan
   order, instrument settings (range, step, dwell), and the measurement date/session.
   File naming: `<event_id>_t<minutes>.xy` (or native format + that stem).

## Outcome rules (apply the frozen product mechanically, do not judge)

- No visible precipitate at 24 h **and** ≤ the frozen XRD solid-signal threshold → `failure`.
- Either valid visual precipitate or valid above-threshold XRD solid signal → nonfailure for the
  binary endpoint; retain any visual/XRD discordance.
- Precipitate exists but the 24 h XRD is uninterpretable or unassignable → `ambiguous`.
- Event interrupted under the frozen execution rule → envelope status `aborted`; keep every
  observation already collected. A later valid 24-hour endpoint may remain eligible for its
  numeric task, but never erases the execution interruption. Partial records are first-class.
- **No silent redos, ever.** If an event must be re-attempted, the original keeps its
  record and status; the redo enters as a new event id (`...:r<k>b`) noted in run order.
  Zero observed failures makes the binary endpoint unestimable in this pilot; it does not by
  itself prove curation. Silent deletion or redo of a failure does constitute a protocol breach.

## What gets recorded (the data contract)

Every event becomes a grammar-v1 record (`schemas/event_grammar.v1.schema.json`); the assignment is
`intent`, session/operator/lot/run-order are `provenance`, and aliquots/notes/video segments are
`observations`. Independently retain the opportunity/action ledger, instrument-native artifacts,
reader recipes, portable exports, and explicit omissions. Labels
(calcite/vaterite/aragonite/amorphous/mixed) are assigned **only after** that declared source-evidence
inventory is frozen and hashed, independently by two people with disagreement retained.

## The one rule that outranks all others

If forced to choose between a cleaner result and a complete record, keep the record.
Failures, ambiguity, deviations, and boring events are the point of this dataset — they
are what every public dataset deleted, and why this one is worth collecting.
