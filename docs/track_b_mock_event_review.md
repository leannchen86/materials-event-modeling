# Track B Mock Event Review

## Purpose

These mock events are synthetic. They are not a lab protocol and should not be treated as
chemistry instructions. Their job is to stress-test the data model before any lab work.

Files:

- `examples/track_b/calcium_carbonate_mock_events.json`
- `examples/track_b/calcium_carbonate_mock_event_log.csv`
- `templates/calcium_carbonate_event_log.csv`

## What The Mock Events Test

- Can the schema represent process history rather than only final material labels?
- Can raw measurement paths be recorded before labels are assigned?
- Can negative, ambiguous, and partial outcomes remain in the dataset?
- Can replicate-like events be represented without assuming identical outcomes?
- Can missing fields be explicit rather than silently absent?
- Can planned conditions and observed trajectories be logged separately?

## What Looks Awkward Already

- pH is likely important, but the mock records leave it missing. A lab partner should tell
  us whether pH can be measured at useful timepoints without disrupting the workflow.
- `mixing_description` is too free-form. It may need structured fields if the lab can log
  actual settings.
- `drying_route` may be too compressed. The route from wet product to XRD sample can
  strongly affect the measurement.
- Planned and observed fields may duplicate each other in simple runs. That duplication is
  acceptable if it preserves the difference between intended design and actual execution.
- CSV is convenient for humans, but JSON is closer to the event structure. We may need both.

## Questions To Ask A Lab

1. Which fields are realistic to collect for every event?
2. Which fields are likely to be missing or unreliable?
3. What raw XRD file formats can be exported?
4. Can instrument settings be exported with the raw files?
5. Can photos or microscopy be captured without becoming a bottleneck?
6. Can labels be assigned only after raw data is frozen?
7. What small changes would make this schema fit normal lab workflow?

## Next Step

Use these mock events in the first lab conversation. The goal is not approval of the
chemistry; the goal is schema critique.
