# Ontology, Natural Kinds, and the Rawness Gradient (thesis deepening)

Date: 2026-06-16 · spine (cross-cutting). Conceptual development from the RRUFF campaign + the
"is chemistry itself a lossy compression?" discussion. Extends [project_brief.md](project_brief.md),
[capture_vs_representation_design_note.md](capture_vs_representation_design_note.md),
[../event-method/findings_summary.md](../event-method/findings_summary.md).

## The reframe: from "is label X lossy?" to "fidelity of charts on a manifold"
The campaign's question — "is inherited label X a lossy projection of the raw measurement?" — is
the *small* version. The bigger one:
> What is the natural coordinate system of materials reality, and how faithful is each human chart
> — species, polymorph, formula, **element** — as a projection onto it?
All labels become charts of varying fidelity on one underlying (largely continuous) manifold. This
dissolves the murky "is it lossy" binary into "where is each chart faithful vs lossy."

## Our result IS an empirical natural-kinds probe
Philosophy's *natural kinds vs conventional kinds* distinction, measured:
- polymorphs / elements = **natural kinds** (real joints; raw recovers them sharply — garnet
  *family* 1.0; calcite/aragonite 0.97).
- solid-solution species = **conventional kinds** (bins on a continuum; raw blends them — garnet
  *species* 0.73, 100% within-family errors).

(*garnet family* = the Ca-bearing [ugrandite] vs Fe/Mg/Mn [pyralspite] structural split, a real
joint; *garnet species* = the names within a family, i.e. cuts on a continuous mixing range.)

## Is chemistry itself lossy? A graded answer
- **Element / atomic number Z: NOT lossy.** Z is genuinely quantized; the periodic table found a
  *real* discrete structure (the natural-joint case). Chemistry's strongest natural kind.
- **Formula / composition (CaCO3): lossy.** Same formula, different reality (polymorphs; proven).
- **Chemical "similarity" / groups: a soft, hand-built embedding** — leaky; learned embeddings
  refine it.
- **The whole edifice: a reduced chart** of a deeper continuous reality (electron density /
  many-body wavefunction).

## The embedding critique: Atom2Vec / Mat2Vec are mirrors, not aliens
Learned element/material embeddings ([Atom2Vec, PNAS 2018](https://www.pnas.org/doi/10.1073/pnas.1801181115);
[Mat2Vec, Nature 2019](https://www.nature.com/articles/s41586-019-1335-8)) recover the periodic
table from data — but they train on **human artifacts**: Atom2Vec on the list of compounds humans
synthesised/catalogued (the table *shaped* that list → circular); Mat2Vec on the text of human
papers (human discourse, not reality). They re-derive the human ontology because their input *is*
the human ontology's output. **Not aliens — mirrors.** A true "alien" representation must learn
from raw physical reality, not curated artifacts. (Newer/transformer embeddings — CrabNet, Roost,
GNN element vectors — are better predictors but do NOT escape this data critique. Architecture is
not the issue; the training data is.)

## The rawness gradient (the operational core)
Rank training data by how much human compression is baked in:
> text (Mat2Vec) → curated compound lists (Atom2Vec / ICSD) → DFT-computed properties (Materials
> Project; human-chosen + approximate) → **raw experimental spectra (RRUFF; our lane)** → raw
> unbiased physical sampling (ideal, ~unobtainable).

Further down: less inherited ontology, higher *possible* fidelity to reality's joints — but
harder/scarcer data. **No view from nowhere:** even raw spectra are human-curated *sampling*
(which minerals / q-range got measured), so the floor is unreachable; rawness is a matter of
degree, not kind. This is the project's founding lossy-at-the-source insight, now applied to the
*training data of representations themselves*.

## The reframed thesis (falsifiable)
> How far down the rawness gradient can a representation be trained, and does it become **more
> faithful** (recovers natural joints, blends conventional bins) as you descend?

Testable on the **same** minerals by building embeddings at different gradient levels and measuring
fidelity to the natural-kind taxonomy.

## Doable now — and its honest ceiling
Without a lab: compare an **unsupervised raw-spectrum embedding** (RRUFF; no labels, no
composition, no text) vs a **composition-derived embedding** — does the raw-physical representation
recover the natural joints (polymorphs) that the human-derived composition representation is
*blind* to, while both place solid-solutions on a continuum? This is the bottom-two rungs (raw vs
composition): doable, novel in framing, and **not a mirror** (the raw side never sees human
ontology). Optional middle rung: DFT (Materials Project, needs an API key).
**Ceiling:** RRUFF *sampling* is still human-curated → a step down the gradient, not the floor; the
true floor needs un-curated raw streams (controlled-collection / operando), which we do not have.

## Decision: where this leaves the program (2026-06-16)

- The recast experiment (unsupervised raw-spectrum embedding vs composition embedding) was
  considered and **rejected as a proxy** of Runs 010/011 — a tidier *restatement* of a known
  result, not a new fact.
- Candidate public-data "discovery" options, and why they fall short:
  - *raw audits the ontology* (flag mislabels / unrecognised sub-structure): discovery-shaped, but
    essentially a known outlier/mislabel-detection technique with a story; hard to validate without
    the physical samples; still sampling-bounded.
  - *raw experiment vs DFT (Materials Project) disagreement*: faithful framing but high-effort, and
    the headline ("DFT has errors") is partly known.
- **Conclusion:** there is **no clean new discovery left in public data**. Genuine,
  maximally-faithful novelty lives at the rawness gradient's **floor** — un-curated raw measurement
  of materials *as they form/exist* — which public datasets (all human-curated sampling) cannot
  provide. So the public-data campaign (Runs 001–015) is treated as **complete**: a validated,
  modality-general finding **plus** this reframe.
- **The sharpened rationale for controlled-collection:** not "collect events because public data
  was thin," but "**the only un-mirrored, faithful representation of reality must be trained on data
  that no human ontology has pre-compressed — and that data does not exist publicly.**" The rawness
  floor and the controlled-collection moat are the same frontier.
- Status: user deliberating between (a) one public-data swing at *raw-audits-ontology* despite the
  ceiling, and (b) resting the public thread and investing in the lab floor. Recommendation on
  record: **(b)** — do not manufacture proxies; the next real discovery needs the rawness floor.
