# Early Human Label Packet — L60 Draft Specification

Status: **draft; freeze-blocking until labeler count, rubric, and packet rendering are certified**.
Companion preregistration:
[pilot_design_prereg.md](pilot_design_prereg.md#pre-freeze-amendment-2026-07-10-task-relevant-compression-audit).

## Purpose

`L60` is the conventional human compression of material state sampled by 60 minutes. It is not the
24-hour outcome label and it is not a retrospective explanation. A labeler may work after the
experiment, but sees a frozen, anonymized packet containing no material-state evidence from after
the 60-minute cutoff. Ex-situ assays and packet rendering may occur later under blinding; their
timestamps are retained, and L60 is not represented as a real-time minute-60 decision.

The intended estimand is the value of the quantitative early trace conditional on this human
summary, with planned recipe/context supplied separately to every prediction arm. Therefore the
default packet hides the planned factorial settings as well as provenance. If a practitioner says
that real early phase assessment necessarily uses a named recipe field, that field must be added
here before freeze and the resulting input-provenance edge must be declared.

## One packet per eligible event

Each rendered packet contains only:

- a randomized `packet_id` with no recoverable event/session/run-order encoding;
- fixed-axis XRD plots for every successfully measured aliquot at approximately 5, 15, and
  60 minutes, with actual completed-arrest state time printed;
- a small table of contemporaneous pH, measured temperature, elapsed time, and mechanically
  recorded visual state (`clear`, `cloudy`, `precipitate`, or missing), when available by cutoff;
- visible quality warnings generated from cutoff-available instrument checks; and
- an explicit `observation unavailable` panel for a missing or unusable early measurement.

The rendering code, axes, normalization, peak annotations (if any), file hashes, and packet order
seed must be frozen. A plot generated using a 24-hour reference pattern, final label, or
future-derived quality decision violates the information contract.

Packets exclude:

- all observations after 60 minutes, including the 24-hour XRD;
- final phase fractions, success/failure status, and downstream adjudication;
- event ID, filename, session/day, operator, lot, run order, instrument session, and scan order;
- other labelers' answers; and
- free-form notes written after the cutoff.

## Frozen response form

Every labeler returns the following fields without adjudication:

| field | provisional vocabulary |
| --- | --- |
| `early_precipitate_assessment` | `none_detected`, `detected`, `uncertain`, `unclassifiable` |
| `dominant_early_phase` | `calcite`, `vaterite`, `aragonite`, `amorphous_or_unresolved`, `mixed`, `none_detected`, `unclassifiable` |
| `secondary_phase_suspected` | zero or more of `calcite`, `vaterite`, `aragonite`, `amorphous_or_unresolved`, `other`, `none`, `unclassifiable` |
| `trajectory_assessment` | `stable`, `changing`, `insufficient_observations`, `unclassifiable` |
| `confidence` | integer 0–100 with anchors frozen below |
| `reason_code` | fixed multi-select rubric; free text is secondary |

Provisional confidence anchors:

- `0–20`: packet cannot support the requested assessment;
- `21–49`: weak or conflicting evidence;
- `50–79`: likely assignment with a meaningful alternative;
- `80–100`: clear under the frozen rubric.

`Unclassifiable` is a scientific result, not missing clerical work. It must be selected when the
rubric cannot be applied; labelers must not guess to improve coverage. Disagreement, confidence,
and abstention remain as separate entries in the event record. Any consensus summary is a derived
representation and never replaces the individual labels.

### Primary model encoding and deployment rule

Before freeze, designate one qualified `primary_labeler_id` by role, not by observed agreement or
performance. The confirmatory `C+L60` arm uses only that labeler's frozen response:

- one-hot encodings of `early_precipitate_assessment`, `dominant_early_phase`, and
  `trajectory_assessment`;
- a fixed multi-hot encoding of `secondary_phase_suspected`; and
- confidence scaled to `[0,1]`.

Reason codes and free text are excluded from the confirmatory arm. An event is primary-L60
representable only when the designated labeler returns every required field and none is
`unclassifiable`; otherwise `S_i^L=0` and it remains in the support denominator. Encoding
`unclassifiable`, using another labeler, averaging labelers, label-disagreement features, or an
empirical distribution over labels are sensitivity analyses declared separately before freeze.

The deployment analogue therefore requires one qualified practitioner applying the frozen packet
rubric. Additional labelers measure reliability; they do not silently substitute for an unavailable
primary response.

## Blinding and execution

1. Freeze and hash the packet-generation code and all cutoff-eligible source files.
2. Generate randomized packets before exposing labelers or representation builders to 24-hour
   outcomes.
3. Use at least two independent labelers; the exact number and eligibility criteria are
   **unresolved freeze items**.
4. Labelers certify that they did not access event IDs, later observations, or other responses.
5. Export one immutable row per `(packet_id, labeler_id)` plus a signed rubric version.
6. Join packets back to event IDs only after every L60 response and manifest is frozen.

## Coverage rules

- Every attempted event with any cutoff-eligible record appears in the packet ledger.
- An aborted event remains eligible if it contains at least one observation that the frozen packet
  rule accepts; otherwise it remains in the attempted-event denominator as `packet_unavailable`.
- Missing 5- or 15-minute aliquots do not automatically remove a packet; the absence is displayed.
- The audit reports event retention by final status and the number of ranking decisions that each
  L60 representation can express.
- Treating `unclassifiable` or an unavailable packet as a model category is allowed only as a
  declared sensitivity analysis and does not erase support loss.

## Freeze certification checklist

- [ ] practicing CaCO3/XRD scientist has reviewed the vocabulary and example packets;
- [ ] labeler count, qualifications, instructions, and compensation are fixed;
- [ ] plot normalization, axes, annotations, and quality-warning rules are fixed in code;
- [ ] confidence anchors and `unclassifiable` rule survive a dry run on non-pilot examples;
- [ ] anonymization test confirms packet IDs/graphics do not reveal provenance directly;
- [ ] labelers have no prior event/session knowledge where feasible, and any unavoidable knowledge
      is declared;
- [ ] leakage-safe provenance probes are specified for rendered packet features and joined L60
      outputs;
- [ ] `primary_labeler_id`, confirmatory encoding, and unavailable-event rule are frozen;
- [ ] outcome-access controls and labeler attestations are operational;
- [ ] packet generator emits source hashes, latest material-state time, assay-ready time, rubric
      version, and creation time;
- [ ] audit code rejects any packet whose latest material-state time exceeds 60 minutes and checks
      any separately declared decision deadline.

Until every item is resolved, `L60` remains a draft arm and the pilot must not claim its rubric was
pre-registered.
