# Track B Next Steps and Outreach Plan

Last updated: 2026-05-30.

## Working Position

Track B should be presented as a research program about event-native feedback for
materials science, not as another XRD classifier, failed-synthesis dataset, or ontology.

Core framing:

> Materials ML often compresses material-making events into labels such as phase pure,
> impurity, failed synthesis, metastable, or ambiguous. We want to preserve the raw event
> first: planned recipe, observed trajectory, raw measurements, failed/partial cases, and
> only later use inherited labels as probes.

The immediate goal is not to discover a new material. The goal is to build a small
controlled dataset and benchmark that tests whether raw/event representations predict,
retrieve, compress, or guide measurements better than inherited labels.

## Offline Work

### 1. Build the Track B analysis harness

Deliverable:

- `scripts/run_track_b_event_analysis.py`

It should accept a folder of event JSON files plus raw XRD/spectra files and produce:

- event-count and missingness report,
- planned-versus-observed field audit,
- provenance/leakage audit by batch, date, operator, and instrument session,
- masked XRD reconstruction,
- held-out measurement prediction,
- replicate retrieval,
- label projection audit after raw/event training,
- split comparisons: random, held-out batch, held-out session, held-out plan family.

Design rule:

> No UMAP/t-SNE-only claims. Every representation plot must be paired with prediction,
> retrieval, transfer, or active-measurement metrics.

### 2. Run synthetic pilot-size stress tests

Deliverable:

- `scripts/run_track_b_pilot_size_stress.py`

Questions:

- Do 12, 24, 48, or 96 events have enough signal for the planned analyses?
- How many replicates are needed before replicate retrieval is meaningful?
- How many partial observations per event are needed before field reconstruction beats an
  event-mean baseline?
- When does label projection become stable enough to inspect?

Hypothesis:

> The first real pilot should probably be 12 to 24 planned conditions, 2 to 4 replicates
> each, and multiple partial observations per event. Forty-eight "independent" one-shot
> samples are less useful than fewer richer events.

### 3. Convert HTEM field modeling into a Track B template

Deliverable:

- `src/materials_event_modeling/track_b/field_prediction.py`

Pattern:

```text
partial event observations -> missing/future raw measurement
```

Baselines to keep:

- global mean,
- event mean,
- nearest neighbor,
- interpolation/smoothing,
- planned-only model,
- observed-trajectory-only model,
- full-event model.

Design rule:

> Additional modalities only count if they beat strong within-event baselines. Multimodal
> is not automatically better.

### 4. Prepare the lab-ready event packet

Deliverable:

- one-page research brief,
- event schema,
- blank event-log CSV,
- raw-file naming convention,
- post-run label form,
- example mock event,
- one-page "what we need from the lab."

Important:

- labels are assigned only after raw files are frozen,
- failed/partial/ambiguous events are explicitly retained,
- planned conditions and observed trajectories are logged separately.

### 5. Decide the first lab pilot shape

Candidate:

- calcium carbonate polymorph crystallization, only if a partner lab says it is safe and
  practical under their SOP.

Better pilot structure:

- 12 to 24 planned conditions,
- 2 to 4 replicates per planned condition,
- multiple time points, droplets/vials, spatial positions, or modalities per event,
- raw XRD export,
- pH/temperature/process logging,
- batch/session/operator tracking.

Success criterion:

> Given partial event data, predict missing or future measurements better than labels,
> composition-only, and event-mean/interpolation baselines.

## Outreach Strategy

Do not start by asking a famous PI for lab access. Start with a crisp technical ask:

> We have a draft event schema and analysis harness. Could you spend 30 minutes telling us
> what would make this useful, impossible, or already solved from your perspective?

### Tier 1: Local feasibility and raw data access

Target people:

- XRD/shared facility scientists,
- lab managers,
- staff scientists who know raw instrument exports and practical sample workflows.

Why:

They can tell us whether the event packet is collectable before we embarrass ourselves in
front of senior PIs.

Bay Area starting points:

- Stanford Nano Shared Facilities X-ray & Surface Analysis Facilities:
  https://snsf.stanford.edu/facilities/xsa
- UC Berkeley Materials Characterization Facility:
  https://mcf.berkeley.edu/
- UC Berkeley Crystalline Materials Facility:
  https://vcresearch.berkeley.edu/facilities/crystalline-materials-facility
- SSRL user office / materials science contacts:
  https://www-ssrl.slac.stanford.edu/ssrl/web/about/contacts

Ask:

> Could this schema be collected without wrecking the workflow? Can raw XRD and metadata be
> exported consistently? Which fields are unrealistic? What failure/ambiguity metadata do
> users usually lose?

### Tier 2: Materials Project / data infrastructure / informatics advice

Target people:

- Anubhav Jain / Hacking Materials,
- Materials Project / MPContribs people,
- Persson group or Materials Project data ecosystem contacts.

Why:

They know where open materials databases succeed and fail, and whether our dataset could
fit MPContribs or a related contribution model.

Relevant current signals:

- Hacking Materials works on Materials Project, FORUM-AI, data-driven synthesis science,
  and collaborations with experimental/autonomous labs:
  https://hackingmaterials.lbl.gov/
- Anubhav Jain is listed by LBNL as Associate Director of the Materials Project program
  and Director of the SciDAC FORUM-AI partnership:
  https://eta.lbl.gov/people/anubhav-jain
- MPContribs supports computational and experimental contributed data, including
  attachments:
  https://docs.materialsproject.org/mpcontribs
- Kristin Persson leads/directs Materials Project-related work at Berkeley/LBNL:
  https://mse.berkeley.edu/people_new/persson/

Ask:

> Does the event-native schema fill a real gap in current materials data infrastructure?
> Would MPContribs-style contribution support event-level raw files and downstream labels?
> What minimum metadata would make the dataset reusable?

### Tier 3: Autonomous labs / high-throughput synthesis groups

Target people:

- Ceder group / A-Lab,
- SLAC/SSRL autonomous characterization/data people,
- NIST autonomous materials metrology people.

Why:

They are closest to the future feedback loop. They may already have event logs, but their
systems may still compress outcomes into success/failure, phase identification, or target
achievement.

Relevant current signals:

- Ceder group describes A-Lab as integrating robotic synthesis, machine-learned
  characterization, and AI decision-making:
  https://ceder.berkeley.edu/research-areas/autonomous-experimentation-for-accelerated-materials-discovery/
- SLAC/SSRL materials science emphasizes multimodal characterization, AI/ML, and automated
  high-throughput experimentation:
  https://www-ssrl.slac.stanford.edu/ssrl/web/research/materials-science
- NIST's autonomous materials metrology program explicitly targets closed-loop autonomous
  systems for experiment design, execution, and analysis:
  https://www.nist.gov/programs-projects/autonomous-systems-materials-research-and-metrology-accelerating-discovery-and

Ask:

> Are current autonomous materials systems storing enough raw event context to train
> future representations, or are they mostly storing labels/decisions? Would an
> event-native benchmark be useful as a stress test for autonomous labs?

### Tier 4: Wet-lab system partner

Target people:

- crystallization labs,
- biomineralization labs,
- soft/hybrid materials labs,
- labs already comfortable with calcium carbonate or similarly safe polymorph systems.

Why:

They can run or advise the first controlled material-making event dataset.

Ask:

> Is calcium carbonate a good first system for process-sensitive, ambiguous, partially
> successful events? If not, what safer or cleaner system would you recommend?

## Message Template: Facility / Staff Scientist

Subject: Quick schema sanity check for raw XRD event dataset?

Hi [Name],

I am exploring a small materials-informatics project in the Bay Area. The idea is to build
a controlled event-level dataset where each record preserves the material-making event:
planned recipe, observed process trajectory, raw XRD files, instrument metadata,
ambiguous/failed/partial outcomes, and later human labels.

The goal is not to optimize phase-label accuracy. We want to test whether raw/event
representations can predict missing or future measurements better than label-only or
composition-only baselines, and then use labels such as phase purity or impurity only as
downstream probes.

Would you be open to a 20-30 minute conversation about whether our draft schema is
realistic from an XRD/facility workflow perspective? The main questions are raw export,
instrument/session metadata, sample naming, and which ambiguity/failure information is
usually lost.

Thanks,
[Name]

## Message Template: Materials Project / Hacking Materials

Subject: Event-native materials dataset idea: raw feedback before labels

Hi [Name],

I have been developing a small research prototype around a question that seems adjacent to
Materials Project / MPContribs / data-driven synthesis work:

What if the native unit for materials ML should be the material-making event, not the
final material label?

The project direction is to collect controlled events with planned recipe, observed
trajectory, raw measurements, failed/partial/ambiguous cases, and post-hoc labels. Models
would first train on objective raw/event tasks such as masked XRD reconstruction,
held-out measurement prediction, replicate retrieval, and active measurement. Only after
that would labels such as phase pure, impurity, ambiguous, or failed be used as probes.

This is motivated by the concern that many materials datasets prematurely compress events
into inherited labels, which are useful for humans but may be lossy coordinates for
learning/search systems.

Would you be open to a short conversation or pointer to the right person? I would mainly
like feedback on whether this fills a real data-infrastructure gap, whether an
MPContribs-style route could support event-level raw files/attachments, and what minimum
metadata would make such a dataset reusable rather than just another small lab dataset.

Thanks,
[Name]

## Message Template: Autonomous Lab / A-Lab Style Group

Subject: Event-native benchmark for autonomous materials feedback loops

Hi [Name],

I am working on a small project about how autonomous/materials-ML systems store feedback
from experiments. The central hypothesis is that many systems compress material-making
events too early into labels such as target achieved, failed synthesis, phase pure,
impure, or ambiguous.

The proposed alternative is an event-native benchmark: preserve planned conditions,
observed trajectory, raw measurements, failed/partial cases, and post-hoc labels, then
evaluate models on objective feedback tasks first:

- missing/future measurement prediction,
- masked XRD reconstruction,
- replicate retrieval,
- active measurement selection,
- transfer across batch/session/operator.

Labels would be audited later as projections, not treated as the primary ontology.

Does this sound like a useful stress test for autonomous lab data systems? I would be very
grateful for a short conversation or a pointer to the right person, especially around what
event context autonomous labs already store and what tends to be lost.

Thanks,
[Name]

## Outreach Order

Week 1:

1. Contact 2 facility/staff scientists for schema sanity checks.
2. Contact 1 Materials Project / Hacking Materials person for data-infrastructure fit.
3. Prepare the event packet before any meeting.

Week 2:

1. Revise schema based on facility feedback.
2. Contact 2 wet-lab candidate partners.
3. Contact 1 autonomous-lab/high-throughput group only after the schema is less naive.

Week 3:

1. Decide whether calcium carbonate is still the right pilot system.
2. If yes, scope the smallest safe pilot.
3. If no, choose the partner-recommended system that still produces ambiguous/partial
   event outcomes.

## How To Avoid Sounding Naive

Say:

- "We are not claiming labels are useless."
- "We are not asking for clean successes."
- "We are not trying to replace expert interpretation."
- "We are asking whether labels should be downstream probes rather than the native training
  target."
- "The first milestone is schema feasibility and raw-data preservation, not discovery."

Do not say:

- "We want to overthrow chemistry."
- "The model will discover the true ontology."
- "We just need enough compute."
- "We can prove this with UMAP."
- "Can your lab run experiments for us?" as the first ask.

