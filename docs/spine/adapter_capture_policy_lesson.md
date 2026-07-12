# The Adapter Is a Capture Policy: Lesson from the Severson Within-Cycle Blind Spot

Recorded 2026-07-12, from the post-hoc review of the
[downstream-compression dry run](../controlled-collection/severson_downstream_compression_results.md).
Extends [capture_vs_representation_design_note.md](capture_vs_representation_design_note.md) and
[data_assumptions_and_limits.md](data_assumptions_and_limits.md). The subject is our own code:
[`adapt_severson_battery.py`](../../scripts/adapters/adapt_severson_battery.py).

There is an irony here that is the thesis proving itself: a repo built around "premature
compression destroys downstream value" performed a premature compression at its own adapter —
knowingly, for defensible engineering reasons, with escrow — and its own audit was then blind to
that edge because the edge sat *above* the representation graph the audit was handed. The packet
paradox is not a rhetorical worry; this is a concrete instance of it, in our own pipeline. The
thesis applies to us first.

## What happened

- **2026-06-15** — the [dataset audit](../event-method/severson_battery_audit.md) explicitly
  documents the within-cycle raw curves (`batch.cycles{cell}`, `Qdlin` on the `Vdlin` voltage
  grid) and names them "the basis of the famous ΔQ(V) feature" — the strongest known early-life
  predictor in this dataset. The signal's location was known before any adapter existed.
- **2026-07-03** — the adapter is written for the representation A/B study. Grammar v1
  observation payloads are scalar-shaped, so the adapter keeps one capacity number per cycle and
  references the within-cycle curves by archive path instead of carrying them. The limitation is
  documented in the docstring. For the A/B question (grammar-shaped vs paper-shaped record) this
  granularity was sufficient.
- **2026-07-11** — the downstream-compression dry run audits four arms (C, C+S100, C+X100,
  C+S100+X100), all built from the per-cycle scalars. Result: S100 and X100 are statistically
  tied. The design and results docs both list "X100 is not native within-cycle electrochemistry"
  as their *first* limitation.
- **2026-07-12** — post-hoc review connects three individually-known facts for the first time:
  (1) early per-cycle capacity fade is nearly flat, so the audited 99-value-vs-7-value edge was
  predictably cheap; (2) the strongest known signal lives in the channel the adapter left behind;
  therefore (3) the null was partly preordained, and the discarded channel is a free known-loss
  calibration control the program's phase-0 explicitly calls for. The connection was drawn by an
  outside question, not by the run's own design or review machinery.

The structural fact: an audit is a *differential* instrument. It detects loss by comparing arms.
Information destroyed before the arms' common input was formed is missing from every arm equally
and cancels out of every comparison. The adapter's compression step sat above the audit's DAG
root (X100), so no arm could see it — by construction, not by accident.

## Root cause, honestly ranked

1. **Schema-shaped capture (the real cause).** Grammar v1's observation payload is
   scalar-oriented and the event corpus is inline JSON; carrying ~1,000-point per-cycle arrays
   would have required inventing a sidecar/blob mechanism. The path of least resistance was to
   conform the data to the schema. An envelope designed for uniformity across six heterogeneous
   datasets thereby acted as an implicit capture policy — the ontology decided what counts as an
   observation. This is ontology loss (see the capture-vs-representation note) committed by our
   own format.
2. **Deferral without pricing.** The limitation was disclosed three times (adapter docstring,
   dry-run design bullet 1, results-doc interpretation-boundary bullet 1) and priced zero times.
   Nobody stated at design freeze: "given flat early fade and the known ΔQ(V) signal, this
   limitation predictably forces a near-tie on the audited edge." Known-limitations lists are
   where insights go dormant: once a fact is filed as a caveat, authors and reviewers treat it
   as handled and stop asking what it implies. The 2026-07-11 multi-agent review reproduced this
   failure — critiques adjacent to the blind spot were dismissed because "the doc already
   concedes it," treating disclosure as neutralization.
3. **Not compute.** The raw archives are 8.3 GB; the events file is 77.7 MB. Storage and compute
   were never the constraint. The barrier was a framework convenience. When a scoping decision
   is attributed to "too big," the actual limit must be named; here there wasn't one.

## What was done right

The lesson is precision, not penance. The adapter escrowed everything by reference with exact
HDF5 paths; the limitation was disclosed in three places; the run's nonconfirmatory framing
prevented over-reading the null. Nothing was destroyed and nothing was hidden. The failure was
*invisibility to the instrument* plus *unpriced deferral* — not data loss and not concealment.
A compression shortcut is legitimate when it is **declared, priced, reversible, and visible to
the audit**. This one was declared and reversible; unpriced and invisible. Two of four.

## Rules for future runs

1. **Every adapter is a capture policy.** Its compression edge must appear as an explicit edge
   in any representation DAG audited downstream. Audits root at the native artifact reference,
   not at the adapter's output. "We have not tested above this line" must be something the
   machine-readable manifest says, not something a caveat whispers.
2. **Disclosed is not neutralized.** At design freeze, every known-limitation bullet must be
   priced: state what result it could preordain and what experiment would test it. If a
   limitation predictably forces the primary result, the design must say so before the run.
3. **Never conform evidence to schema silently.** When data exceeds the grammar, grow the
   grammar (array/sidecar-by-reference mechanism) or record an explicit unadapted-edge entry.
   Pointer + content hash + reader recipe beats both inlining and omission.
4. **Name resource limits precisely.** "Too big" must cite the number and the actual binding
   constraint. A framework convenience wearing a resource-limit costume is how premature
   optimization hides.
5. **Reviews need a completeness critic.** Claims-checking asks "is what the doc says true and
   fairly framed?" and structurally treats disclosed limitations as resolved. Every run review
   must also ask: *what edge sits above this graph, and what experiment does the blind spot
   imply?*
6. **The alternative to premature compression is not "carry everything."** Scoping is
   unavoidable; unbounded capture is not a policy. The standard is declared, priced, reversible,
   audit-visible compression — the same standard we intend to hold industrial capture pipelines
   to, applied to our own adapters first.

## Remediations

- **Known-loss control:** rebuild the ΔQ(V) representation from the escrowed within-cycle curves
  and run the identical audit on the within-cycle→per-cycle edge — a test with a known correct
  answer that both validates the instrument (it has so far only ever produced nulls) and
  retroactively makes the S100-vs-X100 tie credible. (Task queued 2026-07-12.)
- **DAG root extension:** future manifests root the representation DAG at the archive reference,
  with the adapter's compression step recorded as an explicit unaudited edge.
- **Grammar v1.1 candidate:** first-class array/sidecar payloads by reference (pointer + hash +
  reader recipe), so richness never again requires either JSON bloat or omission.
- **Results-doc amendment** for the dry run is pending separately (decomposition, censoring
  sensitivity, failed batch-3 width prediction); this note deliberately does not modify the
  frozen run artifacts.
