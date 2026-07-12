# Berkeley Lab Molecular Foundry User Application Packet

As of 2026-06-11.

## Decision

Apply through the Molecular Foundry user program first, not ALS beamtime first.

Reason:

- The current project needs characterization access, staff expertise, raw data export,
  and workflow/schema feedback.
- The Foundry explicitly supports XRD, microscopy, synthesis, theory/simulation, and
  data-management/data-analysis capabilities.
- Synchrotron beamtime at ALS may become useful later, but it is probably too specialized
  for the first event-trace pilot.

## Immediate Gating Items

1. Create a Foundry User Portal account:
   https://foundry-proposals.lbl.gov/

2. Email the User Office for fit and proposal-type guidance:
   foundry-useroffice@lbl.gov

3. Identify a PI or senior collaborator.

   The Foundry proposal guidance says the PI is usually a faculty member or senior-level
   scientist heading a research group, program, or lab; the PI cannot be a student or
   postdoctoral scholar. The hands-on project lead can be the Primary Researcher.

4. Decide proposal type.

   Likely route:

   - Standard Proposal if we can wait for the next regular call.
   - Rapid Access only if Foundry staff agree the project is time-sensitive and high-impact.
   - Instrument Only only if staff say a narrow XRD/microscopy request is enough and the
     user-training assumptions are realistic.

## Working Proposal Title

Event-Native Materials Characterization for AI-Driven Materials Discovery

## One-Sentence Version

We propose to create and analyze a small controlled materials-event dataset that preserves
planned conditions, observed deviations, raw characterization files, failed/ambiguous
outcomes, provenance, and delayed labels, then test whether partial event traces predict
missing or future measurements better than final-label or static-metadata baselines.

## Fit With Foundry Capabilities

Likely requested capabilities:

- powder or thin-film XRD with raw data export,
- optical/electron microscopy if appropriate,
- staff input on a repeatable material-making and measurement workflow,
- data-management feedback for provenance, raw file naming, and event metadata,
- optional theory/data-analysis support for event-trace representation learning.

Possible lead/support facility framing:

- Lead Facility: Inorganic Nanostructures or Organic/Macromolecular Synthesis, depending
  on the material system.
- Support Facility: Imaging/Manipulation or Theory, depending on the final design.

This must be confirmed with the User Office or a Foundry staff scientist.

## Draft Email To User Office

Subject: Fit question for possible Molecular Foundry user proposal on event-native materials characterization

Hi Foundry User Office,

I am preparing a possible user proposal on event-native materials characterization for
AI-driven materials discovery. The goal is to preserve fuller material-making traces:
planned conditions, observed process deviations, raw XRD/microscopy files, failed or
ambiguous outcomes, provenance, and delayed labels.

The scientific question is whether models trained on partial event traces can predict
missing or future measurements better than final-label or static-metadata baselines. The
broader motivation is that many materials datasets compress experiments too early into
final labels or properties, losing feedback that may be important for AI-driven science.

I am trying to determine whether this is a good fit for the Molecular Foundry, and if so,
which Lead Facility and proposal type would be most appropriate. The likely needs are
powder/thin-film XRD with raw data export, microscopy or optical characterization where
useful, and advice on structuring repeatable experimental traces and provenance.

Would you recommend pursuing this as a Standard Proposal, Rapid Access proposal, Instrument
Only proposal, or another mechanism? I would also appreciate guidance on whether the scope
needs a senior PI or Foundry staff collaborator before submission.

Best,
Leann

## One-Page Concept Note Draft

### Project Goal

Materials ML often starts from compressed records: final labels, phase assignments,
properties, or success/failure outcomes. This project asks whether the native learning unit
should instead be the material-making event: planned conditions, observed deviations, raw
measurements, provenance, failed/ambiguous outcomes, and delayed interpretation.

### Immediate One-Year Goal

Build and analyze a small controlled event-trace dataset using a simple, repeatable
materials system. Each event will preserve raw characterization files and process metadata
before downstream labels are assigned. The core test is whether partial event traces predict
missing or future measurements better than final labels or static metadata alone.

### Why Foundry Access Is Needed

The project needs access to reliable characterization workflows, raw data export, and
expert feedback on experimental design. Foundry capabilities such as XRD, microscopy,
synthesis support, and data-management/data-analysis expertise are directly relevant to
building a dataset that is useful for machine learning rather than only human-readable
reporting.

### Proposed Data Structure

Each material-making event should include:

- planned recipe and intended conditions,
- observed deviations and timestamps,
- raw XRD/microscopy/optical files,
- instrument settings and session provenance,
- failed, partial, or ambiguous outcomes,
- delayed human labels recorded after raw data is frozen.

### ML Evaluation

Labels are not the primary training target. They are downstream probes.

Primary objective tasks:

- early trace -> later measurement prediction,
- partial measurements -> missing measurement reconstruction,
- replicate or similar-event retrieval,
- uncertainty or ambiguity prediction,
- measurement-budget simulation.

Baselines:

- static recipe/process metadata,
- final labels only,
- composition-only features,
- simple interpolation or event-mean baselines,
- label-first supervised models.

### Expected Output

The output is not primarily a new material. The output is a reusable event-trace dataset
and evaluation protocol showing whether richer experimental traces provide better learning
signals than final-label datasets.

## Proposal Review Points To Address

Foundry proposal review asks for:

- project goals and significance,
- project plan and timeline,
- resource request,
- relevant experience.

Draft response logic:

- Significance: AI-driven materials discovery is bottlenecked by sparse/compressed
  experimental records; event-native datasets preserve learning feedback.
- Plan: run a small controlled dataset, freeze raw traces before labels, evaluate objective
  partial-observation prediction tasks.
- Resources: XRD/microscopy/raw export/staff guidance are necessary to make the data
  reliable and reusable.
- Experience: position Leann as ML/data lead; add a senior PI or materials collaborator for
  materials workflow, lab safety, and instrument expertise.

## Practical Next Steps

1. Send User Office fit email.
2. Create Foundry User Portal account.
3. Ask User Office which facility should be Lead Facility.
4. Identify a senior PI/collaborator.
5. Convert this packet into the portal proposal structure.
6. Attach or reference current Track B artifacts:
   - `docs/controlled-collection/pilot_design_prereg.md`
   - `schemas/event_grammar.v1.schema.json`
   - `schemas/partner_study.v1.schema.json`
   - `docs/controlled-collection/outreach/lab_outreach_brief.md`

Supporting drafts:

- Portal-style proposal draft: `docs/controlled-collection/outreach/foundry_standard_proposal_draft.md`
- PI/collaborator outreach: `docs/controlled-collection/outreach/foundry_pi_collaborator_outreach.md`
- User Office email draft: `docs/controlled-collection/outreach/foundry_user_office_email.md`

## Sources

- Molecular Foundry User Program:
  https://foundry.lbl.gov/user-program/
- Applying for Access:
  https://foundry.lbl.gov/user-program/applying-for-access/
- User Proposal Types:
  https://foundry.lbl.gov/user-program/user-program-overview/user-proposal-types/
- Proposal Questions and Evaluation Criteria:
  https://foundry.lbl.gov/user-program/applying-for-access/criteria-examples/
- X-Ray Diffractometer:
  https://foundry.lbl.gov/instrumentation/x-ray-diffractometer-xrd/
- Porous/Crystalline Materials Characterization:
  https://foundry.lbl.gov/instrumentation/porous-crystalline-materials-characterization/
