# Track B Counterbalanced Pilot Stress Test

Generated with:

```bash
.venv/bin/python scripts/run_track_b_counterbalanced_pilot.py \
  --output data/manifests/track_b_counterbalanced_pilot_stress.json
```

## Purpose

The previous provenance ablation found a failure mode: held-out-operator splits can
collapse when operator assignment is confounded with planned-condition coverage.

This run asks which provenance assignment strategy makes a 48-event pilot less vulnerable
to that shortcut.

Tested pilot shape:

```text
16 planned conditions x 3 replicates = 48 material-making events
```

Tested assignment modes:

- `confounded_operator`: deliberately ties operator/batch/lot to hidden regime structure.
- `random_group`: assigns provenance randomly at planned-condition level.
- `balanced_plan`: rotates provenance at planned-condition level.
- `balanced_replicate`: distributes each planned condition's replicates across
  provenance variables.

## Hypotheses

H1: A deliberately confounded operator assignment should fail or become unstable on
held-out-operator splits.

H2: Counterbalanced replicate-level assignment should reduce held-out-operator collapse
while preserving held-out-plan event signal.

H3: Replicate-level counterbalancing should keep provenance-combo and
provenance-residualized performance positive more often than plan-level or confounded
assignment.

## Key Results

Mean over five seeds:

| Assignment | Held-out plan full event | Held-out operator full event | Held-out provenance combo | Residual combo | Operator collapse rate | Shuffle full event |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `confounded_operator` | +64.8% | -326.5% | -738.8% | -224.4% | 100% | +65.5% |
| `random_group` | +63.5% | +62.5% | +63.6% | +60.0% | 0% | -7.7% |
| `balanced_plan` | +64.8% | -2090.6% | -3.4% | -18.5% | 100% | +64.7% |
| `balanced_replicate` | +64.8% | +65.6% | +65.6% | +59.0% | 0% | -9.2% |

Balance diagnostics:

| Assignment | Max hidden-regime share by operator | Max hidden-regime share by lot |
| --- | ---: | ---: |
| `confounded_operator` | 42.9% | 60.0% |
| `random_group` | 26.3% | 30.7% |
| `balanced_plan` | 37.5% | 60.0% |
| `balanced_replicate` | 25.0% | 18.8% |

## Verdict

H1 is validated. The deliberately confounded assignment collapses on held-out operator and
held-out provenance-combo splits. The within-provenance shuffle also stays high at about
65.5%, meaning provenance groups preserved much of the event/regime structure. That is the
signature of a shortcut-prone design.

H2 is validated. Replicate-level counterbalancing preserves the held-out-plan signal and
also survives held-out operator:

```text
held-out plan:      +64.8%
held-out operator:  +65.6%
held-out combo:     +65.6%
residual combo:     +59.0%
```

H3 is validated. Replicate-level counterbalancing keeps provenance-combo and
provenance-residualized performance positive in all five seeds. The within-provenance
shuffle drops below zero, which means event features are no longer just acting as
provenance group labels.

The most interesting failure is `balanced_plan`. It looks balanced superficially, but it
still collapses because rotating provenance at the planned-condition level can align with
structured plan order. Counts alone are not enough. The assignment has to distribute
replicates of the same planned condition across provenance variables.

## Design Lesson

The first serious Track B pilot should not only be:

```text
16 planned conditions x 3 replicates
```

It should be:

```text
16 planned conditions x 3 replicates, with each planned condition's replicates
distributed across operator/session/lot/batch whenever feasible.
```

If multiple operators are not available, use the same logic for whatever provenance axes
are available:

- instrument session,
- measurement day,
- reagent lot,
- sample-preparation batch,
- XRD run order,
- drying/separation batch.

## Outreach Implication

When talking to a lab, do not merely ask:

> Can we collect 48 events?

Ask:

> Can we distribute replicates across batch/session/lot/run order so the dataset can
> support provenance-blocked ablations?

That is a serious experimental-design ask and should make the project sound more rigorous,
not more complicated for its own sake.

## Caveat

This is still synthetic pilot-design evidence. It does not prove that real chemistry will
behave this way. Its value is that it gives us a concrete design constraint before lab
work starts:

> Replicates are not enough; provenance-counterbalanced replicates are the real unit.

