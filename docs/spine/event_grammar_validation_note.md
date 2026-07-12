# Event-Grammar Validation Ladder

Status: current interpretation, revised 2026-07-12. Historical adapter and A/B records remain in
`docs/controlled-collection/`.

## Purpose

The event grammar standardizes a small envelope—intent, observations, outcome, provenance, and
labels-after-recording—while leaving scientific payloads domain-specific. It is useful only when it
enables a question or control that a paper-shaped record cannot support.

## Validation ladder

1. **Envelope coverage:** can selected source records be represented without fabricating fields?
2. **Audit enablement:** do explicit event boundaries, outcomes, and provenance expose a real data
   problem?
3. **Representation ablation:** does removing a slot change frozen task risk, support, or
   collisions?
4. **Cross-system transfer:** does shared event structure improve a held-out system?

Each rung is conditional on the capture policy. Adapter compatibility is not evidence coverage,
and observation count is not capture completeness.

## Conformance levels

- **L0:** the adapted record has unique events and orderable payload-bearing observations;
- **L1:** at least two provenance axes are logged;
- **L2:** outcome states include a genuine failed, aborted, or ambiguous attempt, and labels are
  frozen after the record where labels exist;
- **L3:** replicated plan groups have within-group provenance variation.

The levels are cumulative record checks, not scores of scientific quality or deliberate design.
They do not inspect channels omitted before adaptation. Censoring is target incompleteness, not a
negative experimental outcome.

### Severson correction

The original coverage study mapped right-censored records to `ambiguous` and reported Severson as
L3. The corrected adapter maps them to `unknown`; no physical failures are documented, so the
cumulative grade is L1. The non-cumulative L3 structure check still passes, but its channel
variation was incidental. Within-cycle arrays also sat above the adapter root. See the dated
requalification in
[event_grammar_coverage_study.md](../controlled-collection/event_grammar_coverage_study.md).

## Current claim altitude

The grammar has demonstrated envelope compatibility and useful structural checks. It has not shown
cross-system transfer or that raw/event representations are generally better coordinates. Public
RRUFF, oleogel, and Severson results are calibration cases for the broader
[compression audit](task_relevant_compression_audit.md); the consequential test is prospective.

## Admission rules for another run

A run proceeds only when it has a committed task and reversal condition, an explicit capture root,
real denominators, a strongest cheap baseline, an independent-environment split, leakage-safe
cross-fitting, run identity, and a decision that the result can change. New architecture or public
dataset sweeps that do not close a prospective design uncertainty are out of scope.
