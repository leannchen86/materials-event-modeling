# When is a label faithful to reality?
*A lens from minerals — and a question about chemistry itself.*

> Draft for review. Audience: ML / science-curious readers (no materials background needed).
> Honest exploration, not a peer-reviewed result. Credits prior work inline.

Every ML practitioner has felt the worry: **are my labels signal, or a lossy human prior?** We
hand models categories — "cat," "toxic," "stable" — and quietly hope they carve the data at real
joints. Sometimes they do. Often they're a convenient human bucketing of something continuous, and
we never find out.

Materials science turns out to be a great place to actually *measure* this, because two things sit
side by side at scale: a **raw physical measurement** (how a material scatters X-rays or laser
light — its structural fingerprint) and a **human label** (the material's name). So you can ask,
concretely: how faithful is the label as a coordinate of the raw signal?

We did, on thousands of minerals. Here's what fell out.

## The hook: same formula, different thing

Calcite and aragonite have the *identical* chemical formula — CaCO₃. One is blackboard chalk; the
other is what seashells and pearls are made of. The formula literally cannot tell them apart. But
their raw spectra separate them instantly, because they're different *arrangements* of the same
atoms (different crystal structures — "polymorphs").

So "CaCO₃" is a **lossy label**: one token standing for two genuinely different things. The cheap
human feature (composition) is blind to the difference; the raw measurement isn't.

## Two regimes

Give a method only the raw fingerprints of thousands of minerals — no names, no formulas — and ask
how the human labels relate to the structure. Two clean regimes appear:

**1. The label is a faithful coordinate** when it marks a *real discontinuity.* Polymorphs
(calcite/aragonite — and the same story for TiO₂, SiO₂, Al₂SiO₅) separate cleanly in
raw-measurement space (~0.9–1.0) while the compositional shortcut is stuck at chance. The label is
"real": it tracks a genuine joint in nature.
*(In ML terms: two classes with identical hand-features but separable raw input — the feature is
lossy, the raw is faithful.)*

**2. The label is a lossy bin** when it's an arbitrary cut on a *continuum.* Garnet species —
almandine, pyrope, spessartine — are just names for where you sit on a smooth iron–magnesium–
manganese mixing dial. The raw signal recovers the real *structural family* perfectly (1.0) but
**blends the species** (0.73) — and the tell: *every* misclassification stays inside the right
family, never crossing the real structural line. The species boundaries are human conveniences on
a gradient.
*(In ML terms: discretizing a continuous latent into classes — the boundary is noise.)*

Philosophers have a name for this split — *natural kinds vs. conventional kinds.* We stumbled into
a way to measure it.

## We tried hard to kill it

A skeptic's reflexes (good ones): overfitting? instrument artifact? "more classes are just harder"?
We checked:
- It reproduces on **two unrelated measurements** — X-ray diffraction *and* Raman — so it's about
  reality, not the device.
- It survives **capacity-free** methods (nearest-neighbour; no model to overfit) and a
  **structure-blind control** (the signal lives in the sharp spectral fingerprint, not in broad
  features that could leak provenance).
- Five *distinct* minerals classify at 0.99 while garnet species sit at 0.73 — so the blending is
  the *continuum*, not multi-class difficulty.

It held. And where it *didn't* generalise cleanly — battery degradation data, where a single
"lifetime" number is a threshold on a continuous fade curve — we found out *why*: an **extrinsic**
variable (the charging recipe) confounds everything, so the clean version of the question needs
**intrinsic** labels. That boundary is itself part of the finding.

## The part that zooms out

Here's where it stops being about minerals. **Chemistry itself is one of these label systems.**

The chemical formula is a lossy compression of reality — calcite ≠ aragonite proved it. And the
periodic table? It behaves like a *learned embedding.* People literally ran word2vec on chemical
compounds — a method called **Atom2Vec** (Zhou et al., PNAS 2018) — and it **re-derived the
periodic table from data alone**, no physics input: alkali metals cluster, halogens cluster, the
groups fall out.

So is the periodic table "real"? *Partly.* Atomic number is genuinely quantized — you can't have
6.5 protons — so *elements* are a real joint, a natural kind. But the formula throws away structure
(polymorphs), and the "similarity" groupings are a soft, leaky compression a continuous embedding
refines.

And here's the catch that matters most. Atom2Vec recovered the periodic table — but it trained on
**human-curated compound databases.** It's GPT-trained-on-human-text: it *mirrors* human knowledge,
it doesn't transcend it. To get a representation faithful to *reality* rather than to *us*, you'd
need data no human ontology ever pre-compressed — raw measurement of matter as it forms and exists,
before anyone names or catalogues it. That data mostly doesn't exist publicly.

Which leaves a genuinely fun question: **an alien civilisation that recorded reality as embeddings
instead of element-boxes might have no periodic table at all — and might be more right than us.**

## Why this might matter beyond rocks

Strip away the minerals and it's a question that haunts all of ML:
- Are my labels signal, or a lossy human prior?
- When does a representation learned from raw data beat the human-engineered feature?
- Does the *provenance* of my training data cap how faithful my model can be — mirror, or alien?

Materials is a rare place where the "raw signal" is a *physical measurement*, not another human
artifact — so you can actually separate "faithful to reality" from "faithful to humans," which you
usually can't in language or vision. That makes it a clean testbed for one of the deepest questions
in representation learning.

## What's new, what's known, what's open
- **Solid:** the natural-kind / lossy-bin distinction is real, measured, and holds across two
  measurement types.
- **Already known** (and credited): Raman/XRD distinguish polymorphs (textbook); learned embeddings
  recover the periodic table ([Atom2Vec, 2018](https://www.pnas.org/doi/10.1073/pnas.1801181115);
  [Mat2Vec, 2019](https://www.nature.com/articles/s41586-019-1335-8)); metastability is a continuum
  ([Sun et al., 2016](https://www.science.org/doi/10.1126/sciadv.aaq0148)).
- **The contribution:** a *measurable criterion* for when a label is a faithful coordinate vs. a
  lossy bin — and the reframe that chemistry's own labels (formula, periodic table) sit on the same
  spectrum.
- **The frontier:** getting data *below* human curation — raw, un-curated measurement of materials
  as they form — which is where any genuinely new, faithful-to-reality representation has to come
  from.

*This is exploratory work from a data/AI angle; corrections and pointers welcome.*
