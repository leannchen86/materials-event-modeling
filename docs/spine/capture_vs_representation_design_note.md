# Capture and Representation Boundaries

Status: current design rule, revised 2026-07-12. The formal test is the
[task-relevant compression audit](task_relevant_compression_audit.md); the concrete failure that
forced this revision is the
[Severson adapter lesson](adapter_capture_policy_lesson.md).

## The pipeline

```text
physical process
-> measurement opportunity
-> instrument-native artifact
-> adapter / export
-> analysis representation
-> report or label
-> downstream decision
```

`Raw` is relative to an edge in this pipeline. A native instrument file is already a selective
measurement of the physical process, and an adapter can discard channels before a representation
audit begins. Therefore the project distinguishes:

- **capture loss:** a relevant modality, interval, failure, or context was never recorded;
- **retention loss:** recorded evidence was deleted, overwritten, or made inaccessible;
- **representation loss:** a retained input was projected into a poorer summary; and
- **ontology loss:** a representation imposed categories that collapse task-relevant variation.

These can coexist. A camera may preserve a low-ontology trajectory while missing chemistry; a
categorical label may be highly compressed yet exactly adequate for one decision. Neither rawness
nor compression has a global quality ordering.

## Governing question

For a declared task and environment, compare actual pipeline nodes and ask:

> What is the least costly representation that stays within frozen risk, support, collision, and
> transfer bounds, and is richer upstream evidence recoverable when the task changes?

This requires strong context, interpolation, clock, recipe, event-identity, and provenance
baselines. A richer input earns value only through a held-out prediction or decision; recovering a
human label is not sufficient. A null gap establishes only bounded adequacy for the tested task,
cutoff, learner family, environments, and sample size.

## Capture-policy rules

1. Root the outer capture audit at the opportunity/action ledger; root representation comparisons
   at the earliest retained artifact.
2. Inventory planned, captured, retained, and adapted channels separately. Anything omitted by
   every comparison arm is invisible to a differential audit.
3. Record every transformation, side input, version, hash, and availability rule. If lineage is
   not verified, compare nodes but do not attribute loss to a particular edge.
4. Price every omission before outcomes are opened: state the result it could preordain and the
   experiment that would test it.
5. Prefer pointer + content hash + reader recipe over either inlining large arrays or silently
   dropping them.
6. Keep labels and reports as serious comparator arms. The objective is late, task-specific,
   reversible compression—not maximal capture for its own sake.

## Current research decision

The public-data campaign established useful positive and negative calibration cases, but it cannot
settle downstream industrial value. The active target is a matched chain from native early evidence
through the actual intermediate report to a delayed outcome and action, evaluated across independent
environments. The [partner collection pipeline](../controlled-collection/partner_collection_pipeline.md)
implements that target; the [downstream-failure program](downstream_failure_research_program.md)
defines its evidence ladder.

Historical dataset search, model trials, and run-level lessons are retained in
[event-method findings](../event-method/findings_summary.md) rather than repeated here.
