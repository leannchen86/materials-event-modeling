# Track B Lab Outreach Brief

## Short Pitch

We are building a small event-level materials dataset. The goal is not to optimize a
known phase label or make a clean success-only dataset. The goal is to preserve raw
material-making events: process history, raw measurements, ambiguous outcomes, failed or
partial events, and later human labels as probes.

The first candidate system is calcium carbonate polymorph crystallization, but the exact
procedure, safety review, chemical handling, waste handling, and instrument SOPs must come
from the partner lab.

## What We Are Asking For

- Feedback on whether our event schema is realistic to collect.
- Permission to save raw measurement files, not only processed summaries.
- Powder XRD access with raw export metadata.
- Basic event metadata logging: date, operator, batch, reagent lot, instrument session.
- Separate logging for planned conditions versus observed trajectory:
  planned settings before execution, and actual pH/temperature/timing/deviations during
  execution.
- Permission to keep negative, ambiguous, partial, and messy runs.
- Optional access to microscopy, Raman, or FTIR if already available.
- A lab-approved SOP and safety guidance before any actual experiment.

## What We Are Not Asking For

- We are not asking the lab to guarantee clean phase-pure products.
- We are not asking for labels before raw files are frozen.
- We are not asking to discard ambiguous or failed runs.
- We are not treating the lab's phase labels as the ground truth objective.

## Why This Is Different

Most materials ML datasets compress events into labels: `phase pure`, `impure`,
`failed`, `metastable`, `ambiguous`, and so on. We want to preserve the richer event first,
then ask whether those labels are clean coordinates, lossy projections, or artifacts of
how data was collected and interpreted.

## Pilot Size

The first pilot can be small: 48 to 96 events if logging is rich. The purpose is to test
the data model and measurement loop, not to discover a new material.

## Questions For The Lab

1. Which fields in the schema are realistic to collect without slowing the lab too much?
2. Which fields are missing from the schema but crucial for interpreting the measurements?
3. Can raw XRD files and instrument metadata be exported consistently?
4. Can failed, partial, or ambiguous events be saved rather than filtered out?
5. Can labels be assigned after raw data is frozen?
6. What SOP, PPE, training, and waste-handling requirements apply?
7. Are there safer or more convenient candidate systems than calcium carbonate for this
   first event-dataset pilot?
8. Can planned conditions and observed trajectory be logged separately, or would that be
   too burdensome for normal workflow?

## Success Criterion For The First Lab Conversation

We are successful if we learn whether the event schema is collectable, what fields must
change, and what constraints the lab workflow imposes. We do not need a commitment to run
experiments in the first conversation.
