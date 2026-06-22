# Rawness-Floor Outreach Drafts (controlled-collection)

The rawness-gradient reframe (`docs/spine/ontology_and_rawness_gradient.md`) sharpens the ask:
we need **raw, un-curated measurement of material-making events — *before* human labels/
compression.** Public data can't provide it; autonomous labs, operando beamlines, and controlled
collection can. Personalise names/specifics per `outreach_personalization_plan.md`. Keep every
message short, one genuine specific detail, one low-friction ask.

---
## A. Self-driving-lab / autonomous-experimentation PI (the ideal raw-stream source)

**Subject:** raw per-experiment measurement streams from [platform] — a representation question

Hi [Name],

I've been following [their lab / specific paper] — [one specific, genuine detail].

I work on materials representation learning from a data/AI angle. Short version of what I'm
chasing: I've been testing *when* inherited materials labels (phase, polymorph, "success") are
faithful coordinates of the raw measurement vs. lossy bins on a continuum. On public mineral data
(Raman + XRD) the answer is clean and holds across both techniques — but the question I actually
care about needs data *before* human labelling: the **raw, per-experiment trajectories** your
autonomous platform records, not just the final outcomes.

Would you be open to a 15-minute call on whether [platform]'s raw per-run streams (the un-curated
time-series + metadata) could support this, and whether there's a small collaboration in it? I'd
come with specific, low-lift asks — not "send me everything."

Thanks,
[You] · [one-line credential / the public finding link]

---
## B. Operando / in-situ beamline scientist

**Subject:** in-situ raw time-series for a labels-vs-raw materials study

Hi [Name],

[Specific detail about their operando/in-situ work.]

I'm studying how faithfully inherited materials labels capture what the *raw* measurement sees —
on public mineral spectra it's clean, but the sharp version of the question needs **in-situ raw
time-series of a process as it happens** (the per-frame data + conditions), which is exactly what
your operando setup produces. Is there a subset of raw, condition-annotated runs you'd consider
sharing or co-analysing? Happy to start with one system and a 15-minute call.

[You]

---
## C. ML-for-materials peer (feedback / pointers / amplification)

**Subject:** when is a materials label a faithful coordinate vs a lossy bin — and is chemistry itself lossy?

Hi [Name],

Quick one you might enjoy. We measured *when an inherited materials label is a natural coordinate
of the raw measurement vs. a lossy discretisation of a continuum* — minerals, Raman **and** XRD,
capacity-free, stress-tested. Clean result: labels are faithful where they track structure
(polymorphs — raw recovers them, composition is blind) and lossy where they bin a solid-solution
continuum. It generalises one level up: the chemical formula / periodic table are themselves lossy
charts, and learned embeddings (Atom2Vec) only *mirror* the human ontology because they train on
human-curated data.

Two asks: (1) would love your read on the framing; (2) do you know any **raw, un-curated**
measurement datasets (pre-label, ideally process/operando) we could test the "rawness gradient" on?

[You] · [link to findings_summary]

---
## Notes
- Lead audience for the *frontier* (genuine new discovery) = anyone who can provide measurement
  **before** human compression. That is the entire sharpened thesis for these asks.
- Existing Foundry-specific drafts: `berkeley_lab_foundry_user_application_packet.md`,
  `foundry_pi_collaborator_outreach.md`, `foundry_user_office_email.md`,
  `next_steps_and_outreach.md` — these can be re-toned with the rawness-floor framing above.

---
## Personalized first-contact drafts — top 3 (2026-06-16)
Per the first-message principles in `outreach_personalization_plan.md`: their-work-first, light,
one soft ask. Each is ~80 words by design. Fill [Name]. Do not send without Leann's approval.

### Gerbrand Ceder (UC Berkeley/LBNL — A-Lab / Radical AI)
> **Subject:** Dara's multiple phase hypotheses
>
> Hi Professor Ceder,
>
> Dara stuck with me — surfacing *several* phase hypotheses when a powder pattern is genuinely
> ambiguous, instead of forcing one best-match label, feels like exactly the right instinct: don't
> let the label compress the raw measurement before the data has had its say.
>
> I've been poking at the same seam from the data side, and it turns out to be measurable on public
> mineral spectra — labels are faithful coordinates of the raw signal where they mark real
> structure, and lossy bins where they cut up a continuum.
>
> Could I grab 20 minutes sometime? Mostly I'd love to hear how you think about that raw-stream →
> phase-call boundary.
>
> — [Name]

### Ekin Dogus Cubuk (Periodic Labs — co-founder/co-CEO)
> **Subject:** "what you see in real life is the signal"
>
> Hi Dogus,
>
> Your line — "theory and simulations are not enough; what you see in real life is the signal" — is
> basically the thesis I've been testing from the other direction. On public mineral data it turns
> out you can *measure* when an inherited label is a faithful coordinate of the raw signal vs. a
> lossy bin of a continuum (cleanly, across both Raman and XRD).
>
> Your move from GNoME to generating real data is the answer to the "why" I keep bumping into. Up
> for a short call sometime — genuinely just to compare notes, no data ask?
>
> — [Name]

### Benji Maruyama (AFRL — ARES)
> **Subject:** ARES reading the raw growth signal
>
> Hi Dr. Maruyama,
>
> ARES is the example I keep pointing to — the CNT growth rate the optimizer chases comes straight
> out of the in-situ Raman during synthesis, so the raw signal *is* the target, with no human label
> in between.
>
> I've been studying, from the data side, exactly what gets lost when a label *does* sit in the
> middle — and on public mineral spectra it's measurable. Your 2025 perspective mentioned welcoming
> collaboration; could I grab 20 minutes to hear how you think about keeping the loop on the raw
> signal?
>
> — [Name]
