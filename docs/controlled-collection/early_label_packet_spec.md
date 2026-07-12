# Early Human Label Packet — L60 Draft

Status: frozen CaCO3 methods draft; rubric, labelers, rendering, and blinding remain unresolved.
Companion:
[pilot_design_prereg.md](pilot_design_prereg.md).

## Role and information boundary

`L60` is a human compression of material states sampled by 60 minutes, not the 24-hour outcome or a
retrospective explanation. Labeling and ex-situ rendering may occur later under blinding; record
those clocks and do not call the result available at minute 60.

The default packet hides recipe and provenance. If real practice requires a named context field,
add it before freeze and declare that parent edge.

## Packet

Every attempted event receives a randomized packet ID with no event/session encoding. The packet
shows only:

- fixed-axis plots for accepted 5-, 15-, and 60-minute XRD observations with completed-arrest time;
- contemporaneous pH, temperature, elapsed time, and mechanically recorded visual state;
- cutoff-available quality warnings; and
- explicit panels for unavailable observations.

Freeze rendering code, axes, normalization, annotations, hashes, and randomization seed. Exclude
post-60-minute evidence, outcomes, event/file/provenance IDs, scan order, other labelers' answers,
and later free-form notes.

## Response and primary encoding

| field | vocabulary |
| --- | --- |
| precipitate | `none_detected`, `detected`, `uncertain`, `unclassifiable` |
| dominant phase | `calcite`, `vaterite`, `aragonite`, `amorphous_or_unresolved`, `mixed`, `none_detected`, `unclassifiable` |
| secondary phase | fixed multi-select over the same phase set plus `other`/`none` |
| trajectory | `stable`, `changing`, `insufficient_observations`, `unclassifiable` |
| confidence | integer 0–100 under frozen anchors |
| reason | fixed multi-select; free text is secondary |

`Unclassifiable` is a result, not clerical missingness. Preserve every individual response,
confidence, disagreement, and abstention; consensus is a separate derived representation.

Before freeze, designate one qualified primary labeler by role, not performance. `C+L60` uses that
labeler's fixed one-/multi-hot responses and scaled confidence. Reason text is excluded. The primary
arm is available only when all required fields exist and none is `unclassifiable`; other labelers,
disagreement features, distributions, or encoding abstention are predeclared sensitivities.

## Execution and support

1. Freeze packet code, cutoff-eligible sources, rubric, and labeler qualifications.
2. Generate anonymized packets before labelers or representation builders see outcomes.
3. Use at least two independent labelers; freeze exact count and compensation.
4. Collect attestations that event IDs, later evidence, and other answers were unavailable.
5. Freeze one row per `(packet_id, labeler_id)` before joining back to events.

Every attempt remains in the packet ledger. Missing observations are displayed; they do not vanish.
Aborted events with eligible early evidence may receive packets, while unavailable packets remain in
support denominators. Encoding unavailable/unclassifiable as a category does not repair support.

## Freeze blockers

- practitioner approves vocabulary, examples, confidence anchors, and abstention rule;
- labeler count, roles, instructions, compensation, and primary-labeler rule are fixed;
- rendering and quality warnings pass non-pilot and anonymization tests;
- unavoidable prior event knowledge is declared;
- outcome firewall, attestations, provenance probes, and unavailable-event rule operate;
- packet manifests contain source hashes, latest state time, assay/creation time, and rubric version;
  and
- automated checks reject post-cutoff evidence and enforce any decision deadline.

Until these close, L60 is not a preregistered arm.
