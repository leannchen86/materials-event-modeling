# Low-Equipment Event-Trace Pilot

Date: 2026-06-09

## Why This Exists

Lab outreach is slow because real materials equipment and operator time are scarce. The
project should not stall while waiting for access. A low-equipment pilot can test the
same core data question on simpler systems:

> Does preserving the full material-making event trace create learning tasks that final
> labels or final observations cannot support?

The point is not to claim that salt droplets, frozen brines, or drying films are
technologically important materials. The point is to practice the dataset discipline that
the larger project needs: raw traces first, labels later, and objective feedback tasks
instead of inherited categories as the training target.

## Current Best Pilot

Start with drying droplets.

Example systems:

- water + salt,
- water + sugar,
- water + citric acid,
- coffee or food dye solutions,
- simple mixtures on glass, plastic, paper, or foil.

These systems are cheap, safe, visual, and fast. They are also process-sensitive: the same
nominal ingredients can produce rings, crystals, branching patterns, smooth films, cracks,
or ambiguous mixed morphologies depending on humidity, substrate, droplet size,
concentration, disturbance, contamination, and drying path.

The useful framing:

> A dried droplet is not just a final sample. It is a fossilized process history.

## Minimum Setup

- phone camera,
- stable tripod or stand,
- consistent light source,
- cheap USB microscope or phone macro lens,
- temperature and humidity sensor,
- pipettes or droppers,
- labeled substrates: glass, plastic, paper, foil,
- event ID labels,
- raw file directory with no manual deletion of failed/weird runs.

## Data Rule

For every event, save the raw trace before assigning any human label.

Suggested event record:

```text
event_id
date_time_start
recipe
concentration
droplet_volume
substrate
temperature
humidity
time_lapse_video_path
final_phone_image_path
final_microscope_image_path
notes
post_hoc_label
post_hoc_label_confidence
```

The label is allowed, but only after raw files and metadata are frozen.

## First Hypothesis

H1: Early event traces plus simple process metadata will predict final morphology or final
image embeddings better than recipe-only, final-label-only, or one-still-image baselines.

This is a small version of the larger materials-event claim:

> Full traces preserve learning signal that is lost when an experiment is compressed into
> a final result or inherited label.

## First Pilot Size

Start with 20-30 events.

Do not vary every factor at once. Suggested first variables:

- concentration: low / medium / high,
- substrate: glass / paper / plastic,
- droplet volume: small / medium,
- ambient humidity and temperature logged passively.

Failures, disturbances, malformed droplets, and ambiguous outcomes are kept.

## First Evaluation Tasks

Use the pilot data to test:

1. Early trace -> final image embedding.
2. Early trace + metadata -> final morphology label assigned after the fact.
3. Early trace retrieval: given the first part of a new drying event, retrieve prior
   events with similar final outcomes.
4. Missing observation prediction: given the time-lapse and metadata, predict final
   microscope/macro image embedding.
5. Label compression audit: test whether labels such as `ring`, `crystal`, `cracked`,
   `uniform`, or `failed` split into multiple event-history regimes.

Baselines must include:

- recipe-only,
- metadata-only,
- final-label-only when labels exist,
- single early frame,
- simple image features before neural models.

## Decision Discipline

This pilot is valuable if it creates a clean event-learning benchmark, even if the first
model is simple. It is not valuable if it becomes aesthetic pattern collection or a
leaderboard on droplet labels.

The north star remains:

> The unit of learning is the material-making event, and labels are downstream probes.

