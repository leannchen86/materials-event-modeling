# Reach-Out Targets — Materials Project, Periodic Labs, + Adjacent Autonomous-Lab / Operando

Generated 2026-06-16 via a multi-agent research workflow (web-sourced, 2024–2026). Tied to the
rawness-floor ask (`docs/spine/ontology_and_rawness_gradient.md`): people who can **provide or
collaborate on RAW, un-curated, pre-label measurement of materials as they form**, or who are
intellectually-aligned collaborators. **Re-verify titles/affiliations at outreach time.**

> Provenance caveat: the Materials-Project-specific discovery agent stalled during the run, so MP
> coverage came indirectly (Persson and Horton were still captured via the other paths). A
> dedicated MP pass could deepen it if needed.

## Top people to contact first
The people who actually **generate raw, pre-label measurement of materials as they form**
(autonomous labs / operando), ranked above intellectual-alignment-only contacts.

1. **Gerbrand Ceder** (UC Berkeley/LBNL, on sabbatical at Radical AI) — runs *two* autonomous labs
   (LBNL A-Lab + Radical AI) producing raw time-resolved XRD of inorganics as they form; his 2026
   "Dara" system deliberately emits *multiple* phase hypotheses instead of forcing one label — the
   "don't compress the raw signal too early" thesis, operationalized.
2. **Benji Maruyama** (AFRL) — ARES puts the *raw in-situ Raman growth signal* of carbon nanotubes
   directly inside the learning loop, no human label in between; coined "self-driving laboratory,"
   publicly inviting collaboration (2025 Nat. Commun. perspective).
3. **Milad Abolhasani** (NC State) — "flow-driven data intensification" captures ≥10× more raw
   in-situ spectroscopic data by sampling reactions *mid-formation* — a machine for the rawness-floor
   signal.
4. **Apurva Mehta** (SLAC/SSRL) — CAMEO closes the loop directly on raw synchrotron XRD patterns,
   choosing the next measurement from the diffraction signal itself, not a curated label.
5. **Ekin Dogus Cubuk** (Periodic Labs, co-founder/co-CEO) — built GNoME (largest ML-over-curated-
   data effort), then concluded "what you see in real life is the signal" and went to generate raw
   synthesis+characterization data himself. Both a data source and a deeply aligned interlocutor.
6. **Janosh Riebesell** (Periodic Labs) — spans all three axes: built Matbench Discovery (curated
   labels), did representation learning / MLIPs, and moved to autonomous-lab data because curated
   data is insufficient.

---

## Materials Project

**Matthew Horton** (early/founding team, Periodic Labs; formerly Materials Project lead + pymatgen
co-maintainer) — *Most thesis-embodying person on the list.* Built the canonical curated database
(MP), trained a generative model on it (MatterGen, *Nature* 2025), then moved to Periodic to
generate raw data as materials form. **Raw data:** indirect but high-leverage — computational
himself, but inside the org that owns the instruments and fluent in the curated side we work
against. **Hook:** "You built the curated side — Materials Project, pymatgen, MatterGen — then
moved to Periodic to generate raw data as materials actually form. That curated→raw move *is* what
my project is about." **Priority: high.**
- https://www.linkedin.com/in/mkhorton/ · https://www.nature.com/articles/s41586-025-08628-5

**Kristin Persson** (Director, Materials Project; Distinguished Prof, UC Berkeley; Senior Scientist,
LBNL) — *Highest-value intellectual contact, NOT a raw-data source.* Founded/directs MP (150k+
DFT-computed materials), the canonical inherited-label system the thesis interrogates. **Raw data:**
none (computational; MP "experimental" content is NLP-extracted recipes). For raw streams, pair her
with Ceder. **Hook:** her NAE citation ("stewardship of open materials databases") + May 2026
election to the American Academy of Arts and Sciences — a project asking whether inherited labels
are natural coordinates or lossy bins is, in effect, asking the steward of the canonical database
what happens to the raw measurement when it becomes an MP label. **Priority: medium.**
- https://www.nature.com/articles/s41563-025-02272-0 · https://newscenter.lbl.gov/2026/05/08/berkeley-labs-kristin-persson-elected-to-the-american-academy-of-arts-and-sciences/

---

## Periodic Labs
Single clearest external source of rawness-floor data — robotic powder synthesis + XRD producing
"gigabytes of proprietary experimental data," *explicitly including failed/negative runs* public
datasets discard. **Caveat across all Periodic contacts:** as of late-2025 the robots were "not yet
up and running," and the data is an explicit proprietary moat — **lead with intellectual
collaboration, not a data-dump request.**

**Ekin Dogus Cubuk** (Co-founder & Co-CEO) — *Highest-tier match on both axes.* Led GNoME at
DeepMind (~380k structures added to MP), now building Periodic's autonomous powder-synthesis labs.
**Raw data:** YES — directs an autonomous synthesis+characterization pipeline producing raw
pre-label streams incl. negatives. **Hook:** "You built GNoME — the largest ML effort over curated
data — then concluded you had to generate raw experimental data because 'what you see in real life
is the signal.' My work is the formal articulation of *why* — where labels are faithful natural
coordinates vs lossy bins of a continuum." **Priority: high.**
- https://physicstoday.aip.org/news/ekin-dogus-cubuk-runs-a-startup-to-accelerate-physics-r-d-using-ai · https://a16z.com/announcement/investing-in-periodic-labs/

**Janosh Riebesell** (Member of Technical Staff, ML for materials) — *Highest-fit contact for this
campaign.* Lead author of Matbench Discovery (*Nat. Mach. Intell.* 2025); maintains
pymatviz/matterviz/TorchSim; wired MLIPs into robotic labs at Radical AI before Periodic (Sep 2025).
**Raw data:** intellectual-alignment AND proximate to raw generation — an unusually well-placed
door. **Hook:** "FROM Matbench Discovery (standardizing inherited stability labels) TO integrating
MLIPs with robotic labs — if curated targets are lossy compressions, your autonomous-lab data is
exactly the pre-label substrate to test whether labels are natural coordinates or lossy bins."
**Priority: high.**
- https://janosh.dev/cv · https://www.rdworldonline.com/how-radical-ai-is-building-a-self-driving-materials-lab/

**Eric Toberer** (senior experimental materials scientist; formerly Prof of Physics, Colorado
School of Mines) — *Strongest experimentalist at Periodic.* Discovered the AV₃Sb₅ kagome
superconductor family (*Phys. Rev. Mater.* 2019). **Raw data:** HIGH/direct — hands-on synthesis +
transport/beamline characterization. **Caveat:** a hire, not a data-policy decision-maker. **Hook:**
"Your AV₃Sb₅ kagome discovery illustrates the thesis — superconductivity + charge-density-wave order
lives in the raw structural/transport measurement and emerges from the geometry, while a composition
label ('a vanadium antimonide') is blind to it." **Priority: high.**
- https://www.linkedin.com/in/eric-toberer-20785889/ · https://www.osti.gov/pages/biblio/1594783-new-kagome-prototype-materials-discovery-kv3sb5-rbv3sb5-csv3sb5

**Liam Fedus (William Fedus)** (Co-founder & CEO) — *High strategic relevance, AI-leadership access.*
Co-created ChatGPT, ex-VP post-training at OpenAI; trained as a physicist. **Raw data:** YES via the
company, but frontier-model side, not a bench scientist (Cubuk is the better first technical contact).
**Hook:** he argues scientific AI needs "highly specialized, sparse, complex" data unlike language
models, and that failed/negative experiments matter — precisely the rawness floor. **Priority: high**
(as access/strategy, behind Cubuk technically).
- https://techcrunch.com/2025/10/20/top-openai-google-brain-researchers-set-off-a-300m-vc-frenzy-for-their-startup-periodic-labs/

**Wei Chen** (early employee #2, software/ML & systems) — *Engineering-side door to the data
pipeline.* Spans large-scale software (TikTok, Twitter) and national-lab nanomaterials (Brookhaven
CFN). **Raw data:** strongly enabling but indirect. **Hook:** his bits-to-atoms arc is exactly the
"software-at-scale meets raw instrumentation" needed to capture measurement before labelling.
**Priority: high (organizational), confidence: medium** — name disambiguation: verified target is
LinkedIn `wchen89`; re-confirm before outreach.
- https://www.linkedin.com/in/wchen89/ · https://davidtsong.com/periodic-labs

**Abhijeet Gangan** (founding-team, materials simulation) — *Intellectual alignment, indirect data.*
Core TorchSim contributor; author of "Surprisingly High Redundancy in Electronic Structure Data"
(arXiv 2507.09001) — ~99% of electronic-structure training data is prunable. **Hook:** his redundancy
result mirrors the finding that curated representations carry less independent info than assumed —
pivot to: where does the *non-redundant*, pre-label raw signal live? **Priority: medium.**
- https://arxiv.org/html/2507.09001v1 · https://github.com/abhijeetgangan

**Alexandre Passos** (founding-team / early AI-ML researcher) — *Alignment/credibility, one step from
data.* Co-creator of OpenAI o1/o3; original scikit-learn co-author. **Hook:** his arc from
scikit-learn ("ML as natural coordinates of data") to reasoning models makes the
representation-faithfulness question one he's equipped to appreciate; it bears on Periodic's physical
RL loop where reward comes from un-compressed experimental data. **Priority: medium.**
- https://scholar.google.com/citations?user=P3ER6nYAAAAJ&hl=en

---

## Adjacent autonomous-lab / operando
Strongest *direct raw-data* generators outside the two target orgs — several rank above the
computational-only Periodic contacts on the raw-measurement axis.

**Gerbrand Ceder** (UC Berkeley/LBNL; CSO & co-founder, Radical AI) — *Arguably the single most
relevant raw-data contact.* Built the LBNL A-Lab (*Nature* 2023); now drives Radical AI's NYC
self-driving lab (SEM/XRD/XRF; ~$55M Seed+ July 2025). **Raw data:** YES, strong — two facilities
continuously producing raw time-resolved XRD/SEM/XRF of inorganics as they form, and he builds the
ML that turns raw streams into phase calls (owns both raw-signal and labelling layers — the seam the
project studies). **Caveat:** mid-sabbatical at a VC-funded startup → collaboration may run through
Radical AI (IP). **Hook:** "Your 'Dara' system (Jan 2026) emits *multiple* phase hypotheses from a
raw powder-XRD pattern when the signal is ambiguous rather than collapsing to one label — exactly the
'don't let the label compress the raw measurement too early' principle my project is built on."
**Priority: high.**
- https://www.nature.com/articles/s41586-023-06734-w · https://arxiv.org/pdf/2510.19667

**Benji Maruyama** (Principal Materials Research Engineer; Autonomous Materials Lead, AFRL) —
*Bullseye on both axes.* Creator of ARES (first fully autonomous materials research robot). **Raw
data:** strongest possible fit — ARES reads the raw in-situ Raman growth signal of CNTs during
synthesis and uses it *inside* the decision loop before any label; open-sourced ARES OS; 2025 *Nat.
Commun.* perspective inviting collaboration. **Caveat:** AFRL gov-lab data constraints, but an
open-source track record. **Hook:** "In ARES, the growth rate the optimizer chases is read straight
out of the in-situ Raman spectrum — the raw growth signal IS the training target, with no human
synthesis-label in between. That's the canonical existence-proof for closing the loop on raw signal
before compression." **Priority: high.**
- https://www.nature.com/articles/npjcompumats201631 · https://www.nature.com/articles/s41467-025-59231-1

**Milad Abolhasani** (ALCOA Prof, ChemBioEng, NC State) — *Highest-relevance academic target for the
raw/pre-label ask.* Self-driving fluidic labs (quantum dots, perovskite nanocrystals) in continuous
flow with real-time in-situ spectroscopy. **Raw data:** YES — July 2025 *Nat. Chem. Eng.* "flow-driven
data intensification" yields ≥10× more raw in-situ data by sampling *mid-formation*; "Rainbow"
multi-robot SDL up to 1,000 exp/day; $2.99M ARPA-E (Apr 2026). **Hook:** "Your flow-driven data
intensification reframes an SDL not as a faster endpoint-label generator but as a way to capture ≥10×
more data DURING formation — the move from compressed endpoint label back toward the raw forming-
material signal." **Priority: high.**
- https://www.nature.com/articles/s44286-025-00249-z · https://news.ncsu.edu/2025/08/rainbow-multi-robot-lab/

**Apurva Mehta** (Senior Scientist, SLAC/SSRL) — *Top-tier on the raw-measurement axis.* Pioneered
closed-loop autonomous synchrotron experimentation; lead/co-author of CAMEO (*Nat. Commun.* 2020).
**Raw data:** YES — physical synchrotron beamlines running autonomous closed-loop experiments.
**Caveat:** CAMEO is composition-spread *screening*, not time-resolved *as-they-form* operando —
probe his in-situ capacity explicitly. **Hook:** "CAMEO closes the loop directly on the raw SSRL XRD
beamline, choosing the next measurement from the diffraction patterns themselves rather than a curated
label — could the autonomous beamline expose that pre-label stream, pushed toward in-situ capture of
materials as they form?" **Priority: high.**
- https://www.nature.com/articles/s41467-020-19597-w · https://profiles.stanford.edu/apurva-mehta

**John Gregoire** (SVP Materials Sciences / Chief Autonomous Science Officer, Lila Sciences; Research
Prof, Caltech) — *Top-tier match on both axes.* One of the longest-running HT + autonomous programs;
"Event-Driven Data Management… for Materials Acceleration Platforms" (*Digital Discovery* 2024) —
infrastructure for streaming raw measurement at scale; "Probabilistic phase labeling… for autonomous
materials research" operates on raw XRD streams. **Raw data:** YES, strong — controls raw HT
measurement + the event-driven plumbing to stream it before labelling, at two institutions. **Hook:**
his Dec 2025 line "there's zero problems we can ever solve in the real world with simulation alone"
is the same critique behind "labels compress the process too early/too lossily" — paired with his
own event-driven raw-measurement infrastructure. **Priority: high.**
- https://www.osti.gov/pages/biblio/2275013-event-driven-data-management-cloud-computing-extensible-materials-acceleration-platforms · https://www.technologyreview.com/2025/12/15/1129210/ai-materials-science-discovery-startups-investment/

**Alán Aspuru-Guzik** (Prof Chemistry & CS; Director, Acceleration Consortium, U Toronto / Vector) —
*Best gateway into the global SDL community; partial direct-data fit.* Directs the largest global SDL
hub; landmark 2024 *Chem. Rev.* SDL review; AFION closed-loop nanochemistry lab (*Nat. Commun.* 2025).
**Raw data:** partial — AFION produces in-flow optical/UV-vis of nanoparticles as they form, but a
*different modality/material class* (solution-phase) than the solid-state operando-XRD/Raman ideal.
**Best use:** conceptual sounding board + pointers to consortium groups running operando
diffraction/scattering on inorganics as they crystallize. **Priority: high** (gateway + partial source).
- https://www.nature.com/articles/s41467-025-56788-9 · https://acceleration.utoronto.ca/people/alan-aspuru-guzik

---

## Notes / caveats
- **Cubuk** title resolved as **Co-founder & Co-CEO** (Physics Today / SiliconANGLE), not CTO.
- **Periodic raw data is a guarded proprietary moat AND robots were "not yet up and running" as of
  late-2025** — lead with intellectual collaboration, not data access; the raw stream is being stood
  up, not yet available.
- **Wei Chen — identity confidence medium** (several people share the name); verified target is
  LinkedIn `wchen89`; re-confirm before outreach.
- **Ceder and Gregoire have a startup/IP layer** (Radical AI; Lila Sciences) — raw-data collaboration
  may run through the commercial entity; frame asks accordingly.
- **Mehta:** CAMEO is composition-spread *screening*, not time-resolved *formation* — confirm operando
  capability explicitly.
- **Toberer, Horton, Gangan, Passos, Wei Chen are hires, not decision-makers** — great technical/
  intellectual entry points; pair with a founder (Cubuk/Fedus) for any actual data conversation.
- **Persson and Aspuru-Guzik are partial/non-fits on raw solid-state operando data** — best used as
  high-value intellectual/gateway contacts, paired with a true raw-XRD/Raman source (Ceder, Mehta,
  Maruyama).
- Re-verify at outreach time: Cubuk/Fedus exact "CEO vs Co-CEO" usage, Riebesell/Horton current
  Periodic roles, and whether Ceder remains on sabbatical at Radical AI.
