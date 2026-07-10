# Controlled Pilot — Run Protocol (lab-facing, execute verbatim)

Companion to [pilot_design_prereg.md](pilot_design_prereg.md) (the why) and
[pilot_assignment.csv](pilot_assignment.csv) (the what: 48 events, pre-assigned to
sessions/operators/lots/run-order — regenerable via
`scripts/generate_pilot_assignment.py`, seed committed). This document is everything the
partner lab needs to execute; the design is ours, the running is theirs. Deviations are
fine — they must be *recorded*, never absorbed.

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
4. **Timed observations** (the clock = first contact):
   - t ≈ 5 min, 15 min, 60 min: withdraw an aliquot (~2 mL), vacuum-filter or
     drop-and-dry on a labeled slide/holder, **rinse briefly with ethanol to arrest
     transformation** (amorphous/vaterite material keeps converting while wet — an
     un-arrested aliquot measures the drying process, not the solution state), then
     dry at ≤40 °C. Note pH and visual state
     (clear/cloudy/precipitate; color) at each pull, with the actual clock time.
   - t = 24 h (±2 h): collect the remaining solid the same way. Record final pH.
   - Throughout: video runs; note any disturbance, spill, hesitation, or deviation as a
     timestamped `human_note` — deviations are data.
5. **XRD scans:** scan all dried aliquots. Scan order is randomized *across* events within
   a measurement batch (do not scan one event's four aliquots back-to-back); log the scan
   order, instrument settings (range, step, dwell), and the measurement date/session.
   File naming: `<event_id>_t<minutes>.xy` (or native format + that stem).

## Outcome rules (pre-stated; apply mechanically, do not judge)

- No visible precipitate at 24 h **and** ≤ noise-level XRD signal → `failure`.
- Precipitate exists but the 24 h XRD is uninterpretable or unassignable → `ambiguous`.
- Event interrupted (spill, power, time) → `aborted`; keep every observation already
  collected. Partial records are first-class.
- **No silent redos, ever.** If an event must be re-attempted, the original keeps its
  record and status; the redo enters as a new event id (`...:r<k>b`) noted in run order.
  A pilot without failures is a failed pilot (it means the record was curated).

## What gets recorded (the data contract)

Every event becomes a grammar-v1 record (`schemas/event_grammar.v1.schema.json`); the
assignment row is the `intent`, the session/operator/lot/run-order go to `provenance`,
every aliquot/note/video segment is an `observation`. A per-session log sheet (CSV or
notebook photo) is sufficient raw input — the adapter script on our side does the JSON.
Labels (calcite/vaterite/aragonite/amorphous/mixed) are assigned **only after** the full
raw set is frozen (hash committed), independently by two people, disagreement kept.

## The one rule that outranks all others

If forced to choose between a cleaner result and a complete record, keep the record.
Failures, ambiguity, deviations, and boring events are the point of this dataset — they
are what every public dataset deleted, and why this one is worth collecting.
