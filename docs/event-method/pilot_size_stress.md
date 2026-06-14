# Track B Pilot-Size Stress Test

Generated with:

```bash
.venv/bin/python scripts/run_track_b_pilot_size_stress.py --output data/manifests/track_b_pilot_size_stress.json
```

## Purpose

This is an offline pre-lab design test. It does not provide evidence about calcium
carbonate or any real chemistry. It asks whether different small pilot shapes are likely
to support the Track B analyses before asking a lab for time.

The stress test varies:

- planned condition count,
- replicates per planned condition,
- total event count,
- random seed.

Each synthetic run evaluates:

- held-out synthetic spectrum prediction,
- event/process features versus label-only features,
- replicate retrieval,
- label projection behavior,
- silhouette gap between hidden regimes and legacy labels.

## Hypotheses

H1: Event/process features should usually beat label-only features on held-out synthetic
spectrum prediction.

H2: Replicated pilot designs should unlock replicate retrieval; one-shot designs cannot
test it.

H3: Very small pilots should be unstable, especially for label projection and
event-over-label gains.

H4: At fixed event count, richer replicated events may be more useful for Track B than
more one-shot planned conditions, even if prediction alone does not monotonically improve.

## Key Results

Mean over five seeds:

| Config | Events | Planned conditions | Reps | Event gain over label | Gain positive rate | Planned retrieval | Split labels |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `12_one_shot_12x1` | 12 | 12 | 1 | +0.300 | 1.0 | 0.000 | 2.6 |
| `12_replicated_6x2` | 12 | 6 | 2 | -0.126 | 0.0 | 1.000 | 2.4 |
| `24_one_shot_24x1` | 24 | 24 | 1 | +0.249 | 1.0 | 0.000 | 3.0 |
| `24_replicated_8x3` | 24 | 8 | 3 | -0.083 | 0.0 | 1.000 | 3.2 |
| `48_one_shot_48x1` | 48 | 48 | 1 | +0.098 | 1.0 | 0.000 | 4.0 |
| `48_replicated_16x3` | 48 | 16 | 3 | +0.310 | 1.0 | 1.000 | 4.0 |
| `48_rich_replicates_12x4` | 48 | 12 | 4 | +0.250 | 1.0 | 1.000 | 4.0 |
| `96_replicated_32x3` | 96 | 32 | 3 | +0.265 | 1.0 | 1.000 | 4.0 |
| `96_rich_replicates_24x4` | 96 | 24 | 4 | +0.229 | 1.0 | 1.000 | 4.0 |

Candidate pilot shapes selected by the script:

- `48_replicated_16x3`
- `48_rich_replicates_12x4`
- `96_replicated_32x3`
- `96_rich_replicates_24x4`

## Verdict

H1 is partially validated. Event/process features beat label-only in one-shot designs and
in replicated designs at 48+ events. But they do not beat label-only in the 12- and
24-event replicated designs. That is the most useful warning from the run.

H2 is validated. One-shot designs cannot support replicate retrieval. Replicated designs
retrieve planned-condition replicates perfectly in this scaffold.

H3 is validated. Very small replicated pilots are undercovered. They have replicate
structure, but too few planned conditions for held-out prediction to generalize.

H4 is mostly validated. At 48 events, the replicated designs are more useful than the
48 one-shot design because they preserve both coverage and replicate structure. The
16x3 shape is stronger than 12x4 here, suggesting that planned-condition coverage matters
as much as replicate depth.

## Design Lesson

Do not ask a lab for 12 to 24 richly logged events and expect a strong representation
claim. That scale may be useful for debugging the schema, but not for the main analysis.

The first serious pilot should be closer to:

```text
16 planned conditions x 3 replicates = 48 material-making events
```

If resources allow:

```text
24 to 32 planned conditions x 3 to 4 replicates = 96 material-making events
```

The run also argues against 48 independent one-shot samples. They may show prediction
signal, but they cannot test replicate retrieval, batch/session stability, or whether
labels are stable projections across repeated material-making events.

## Caveat

This result should guide lab design, not become a claim in a paper. The hidden regimes are
synthetic and known by construction. A real pilot must use the same analysis discipline
without pretending that synthetic hidden regimes are real chemistry.

