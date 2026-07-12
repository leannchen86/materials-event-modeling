# Molecular Foundry Application Draft — CaCO3 Methods Pilot

Status: unsubmitted draft; program requirements, contacts, and facility fit must be reverified before
use. This proposal concerns the CaCO3 methods pilot, not the separate downstream-value program.

## Working title

**Capture-Aware Experimental Records for Early-to-Late Materials Decisions**

## One-sentence proposal

Collect a small counterbalanced CaCO3 crystallization dataset that preserves measurement
opportunities, native characterization, process history, failures/ambiguity, conventional reports,
and blinded labels, then test which early representation predicts a frozen 24-hour outcome across
held sessions.

## Why facility access is needed

- practitioner review of whether the collection and report arms reflect real XRD workflow;
- approved wet-lab SOP, safety training, and staff oversight;
- stable powder XRD with native export and configuration metadata;
- optional microscopy/optical support when it does not compromise the frozen design; and
- instrument, calibration, sample-preparation, and data-lineage expertise.

## Study boundary

The preregistered design assigns 48 events across 16 factorial conditions and four sessions. It is
a single-site methods/calibration study. It does not claim cross-site reproducibility, degradation,
pilot-scale yield, qualification, or industrial performance.

The lab executes the frozen plan after partner review and analysis freeze. Chemistry, handling,
waste, PPE, and instrument procedures remain subject to facility SOP and approval.

## Data products

Each attempt records:

- assignment, actual process, deviations, and complete status;
- eligible measurement actions and the fixed/human/scripted policy selecting them;
- native files, portable exports, readers, hashes, calibrations, and acquisition clocks;
- early quantitative X60, conventional S60, and blinded human L60 arms;
- a separately built 24-hour no-precipitate and quantitative phase outcome;
- session/operator/lot/instrument provenance; and
- cost, latency, missingness, failure, ambiguity, and censor reasons.

Labels and outcomes do not determine what evidence is retained. `Raw` is not treated as unmediated
truth; every capture and transformation edge is declared.

## Evaluation

Compare context, L60, S60, X60, and complementarity on identical out-of-fold units. Report task
risk, event/decision support, collisions, held-session performance, provenance recoverability,
measurement uncertainty, and collection/processing cost. Strong clock, recipe, interpolation, and
provenance baselines are mandatory. A compact report may be the winning result.

## Expected output

- an openly documented capture/event protocol and validated dataset, subject to rights;
- a support-aware compression audit with positive, adequate, and failure cases;
- reusable bundle/lineage validation; and
- a methods paper or dataset note at the altitude earned by the study.

## Application gates

Before submission:

- confirm proposal type, lead facility, eligibility, cycle deadline, and review criteria;
- identify facility scientist and senior materials/safety collaborator;
- confirm that the exact pilot is feasible under Foundry SOP and available equipment;
- complete instrument-specific X60/S60/outcome freeze items;
- define capture opportunities, native exports, readers, storage, and rights;
- remove any promise of a downstream/industry outcome not measured by this pilot; and
- ensure the design lock and analysis freeze precede the first event.

## Short User Office note

> I am preparing a small methods proposal on capture-aware materials experiments. The project would
> collect counterbalanced CaCO3 crystallization attempts with native XRD/process records, explicit
> capture policy, failures and ambiguity retained, and later reports/labels as comparison arms. The
> first study asks which early representation predicts a frozen 24-hour laboratory outcome across
> held sessions; it does not claim industrial qualification. Could you advise whether this fits the
> user program, which facility should lead, and what staff contact should review feasibility before
> submission?

## Current artifacts

- [pilot design preregistration](../pilot_design_prereg.md)
- [pilot run protocol](../pilot_run_protocol.md)
- [X60 draft](../x60_input_spec.md)
- [24-hour outcome draft](../outcome_24h_spec.md)
- [event grammar](../../../schemas/event_grammar.v1.schema.json)

Program pages to reverify:
[Molecular Foundry User Program](https://foundry.lbl.gov/user-program/) and
[Applying for Access](https://foundry.lbl.gov/user-program/applying-for-access/).
