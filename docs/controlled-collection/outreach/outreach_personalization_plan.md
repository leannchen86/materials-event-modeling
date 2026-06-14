# Outreach Personalization Plan

Date: 2026-06-14

## Working Boundary

Do not mass-message "everyone" at a lab or company. Use a small, relevant shortlist and
customize each message around a concrete reason that person is being contacted.

Do not send anything without an explicit final approval pass from Leann. Drafting is fine;
sending is separate.

Do not scrape private iMessage, Slack, or email history for tone unless Leann provides a
scoped export or points to a specific approved file. The safest tone source is 20-40
outbound messages Leann actually liked, with private details removed.

## Current Repo-Informed Pitch

The project is not another XRD classifier and not a claim that labels are useless. It is a
proposal to treat the material-making event as the native learning unit:

```text
planned recipe + observed trajectory + raw measurements + provenance
-> predict/retrieve/reconstruct/choose measurements
-> only later audit phase/failure/ambiguity labels as probes
```

The current repo has:

- a material-event schema that separates planned conditions from observed trajectory,
- mock calcium-carbonate event records and a blank event-log template,
- ingestion and readiness audits for event records,
- Track A lessons from NIST, opXRD, HTEM, Durham, Dryad, and OpenCrystalData,
- synthetic Track B stress tests for pilot size, replicate structure, provenance
  counterbalancing, partial-observation budgets, active measurement, and masked event
  modeling,
- Foundry-oriented proposal and outreach drafts.

The current repo does not yet have:

- a real controlled material-making event dataset,
- enough multi-observation real events for masked event reconstruction,
- enough replicate/provenance variation for trustworthy real shortcut tests,
- permissioned raw instrument exports from a partner lab.

## Honest Evidence To Use

- Mock-event audit: 6 calcium-carbonate mock events validate the logging surface, but fail
  most learning-readiness checks. They have 6 XRD references and delayed labels, but 0
  events with at least 3 event-internal observations and only 1 replicate group.
- Pilot-size stress: the healthiest first serious synthetic pilot shape is roughly
  `16 planned conditions x 3 replicates` rather than 48 unrelated one-shot samples.
- Field-budget stress: partial observations need coverage. Space-filling observations are
  more useful than convenience/random sampling in the synthetic event-field setup.
- Event-analysis harness: on the 48-event synthetic bundle, planned/full-event features beat
  label-only baselines under held-out-plan and held-out-batch splits, while provenance
  prediction remains an explicit shortcut audit.
- HTEM lesson: within a public Cu-S-Sn sample library, partial raw XRD observations predict
  missing XRD better than static material-row framing, but the result is event-field
  evidence, not proof of a universal learned ontology.
- opXRD lesson: source identity is easy to recover from raw/metadata features, so raw
  embeddings can silently encode instrument/lab/export artifacts unless those variables
  are logged and split on.

## Tone Target

Based on the current request and existing project docs only, the provisional tone should be:

- lowercase-friendly when casual, but clean in first-contact emails,
- direct and technically curious,
- willing to say "I might be naive here" without underselling the idea,
- allergic to hype: no "revolutionize materials science" posture,
- clear that the ask is feedback first, not lab access on the first message,
- specific about what would make the project useful, impossible, or already solved.

Once approved writing samples are available, replace this with a real style guide.

## Targeting Logic

### LBNL / Molecular Foundry

Primary ask: proposal fit, facility workflow sanity check, raw export/provenance feasibility,
and PI/senior-collaborator routing.

Best first contacts:

- Foundry User Program Office: fit, proposal type, lead facility, staff routing.
- Data Science and Digital Infrastructure: event metadata, FAIR data workflows, raw-file
  lifecycle, automated equipment/data pipelines.
- Inorganic Nanostructures or Organic/Macromolecular Synthesis staff: material-system and
  SOP realism.
- NCEM or Imaging/Manipulation only if microscopy becomes part of the event packet.

Personalization hook:

```text
I am not asking whether this can be made into a clean phase-label dataset. I am trying to
learn whether the raw-event schema is collectable in a normal Foundry workflow, and what
metadata would be missing if we were naive.
```

### LBNL / Materials Project / Hacking Materials

Primary ask: whether event-native raw traces fill a real data-infrastructure gap, whether a
contribution route such as MPContribs can support event-level raw files/attachments, and
what minimum metadata makes such a dataset reusable.

Best first contacts:

- Anubhav Jain / Hacking Materials / Materials Project / FORUM-AI direction.
- Materials Project leadership or technical leads only after the first message is sharp
  enough to avoid sounding like a generic database idea.

Personalization hook:

```text
The question is not "can we add another label field?" It is whether current materials data
infrastructure preserves enough experiment feedback to train models on raw/event objectives
before labels are assigned.
```

### SLAC / SSRL

Primary ask: synchrotron/facility perspective on raw XRD/scattering exports, metadata,
beamline/user workflow, and event-level feedback for high-throughput or operando work.

Best first contacts:

- SSRL User Office for routing.
- Materials Science division leadership for fit.
- Beamline staff tied to powder diffraction, thin-film diffraction, WAXS, and materials
  scattering when the ask is concrete.
- Data systems contacts only if the message focuses on streaming, scale, and event data
  lifecycle rather than a wet-lab pilot.

Personalization hook:

```text
SSRL is interesting here because the project treats x-ray measurements as feedback inside
an event, not just as final characterization. I am trying to understand which raw export
and provenance fields are realistic to preserve in a user workflow.
```

### Periodic Labs

Primary ask: feedback on whether autonomous labs already preserve enough raw event context
for future representation learning, and whether an event-native benchmark would be useful.

Best first move:

- Prefer one strong general inbound or warm-intro message over emailing the whole team.
- Individual messages should only be sent when there is a verified reason for that person:
  autonomous labs, materials ML, data infrastructure, experimental feedback loops, or
  scientific agents.

Personalization hook:

```text
Periodic's public framing says autonomous labs generate high-value data, including negative
results. My specific question is whether those traces are stored richly enough to train on
raw feedback tasks, or whether they still get compressed too early into target-achieved /
failed / phase-label records.
```

## Recipient Sheet Fields

Use this structure before drafting:

```text
name
organization
role_or_public_signal
source_url
why_this_person
ask_type
relationship_or_warm_path
message_channel
custom_hook
risk_of_contacting
approval_status
sent_at
reply_status
```

## Drafting Rules

- One ask per message.
- Mention at most one or two repo results.
- Keep the first message under 180 words unless the recipient already knows the project.
- Ask for 20-30 minutes or a pointer to the right person.
- For facility staff, lead with workflow realism.
- For data-infrastructure people, lead with schema/metadata/reuse.
- For autonomous-lab people, lead with feedback loops and negative/ambiguous event traces.
- For senior PIs, lead with proposal/collaborator fit and make clear they do not need to
  own the ML implementation.

## Avoid

- "Can your lab run experiments for us?" as a first message.
- "We discovered the true ontology."
- "Labels are wrong/useless."
- "We just need enough compute."
- "This will revolutionize materials science."
- Sending many messages into the same group before the first reply.

## Sources Checked

- Molecular Foundry staff and User Program Office:
  https://foundry.lbl.gov/about/staff/
  https://foundry.lbl.gov/user-program/user-program-office/
- Molecular Foundry Data Science and Digital Infrastructure:
  https://foundry.lbl.gov/about/facilities/data-science-and-digital-infrastructure/
- Materials Project / Anubhav Jain / FORUM-AI:
  https://eta.lbl.gov/people/anubhav-jain
  https://eta.lbl.gov/news/berkeley-lab-leads-effort-build-ai-assistant-energy-materials-discovery
  https://docs.materialsproject.org/services/mpcontribs
- SSRL contacts, beamlines, and materials-design page:
  https://www-ssrl.slac.stanford.edu/ssrl/web/about/contacts
  https://www-ssrl.slac.stanford.edu/ssrl/web/beam-lines/by-number
  https://www-ssrl.slac.stanford.edu/ssrl/web/materials-design
- SLAC AI/data context:
  https://www6.slac.stanford.edu/research/new-technologies
  https://lcls.slac.stanford.edu/depts/data-systems/projects/lclstream
- Periodic Labs:
  https://periodic.com/
