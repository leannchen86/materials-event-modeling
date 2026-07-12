# Conventional 60-Minute Report — S60 Draft

Status: frozen CaCO3 methods draft; a practicing XRD/CaCO3 scientist has not validated the workflow
or fields. Companion: [pilot_design_prereg.md](pilot_design_prereg.md).

## Role

`S60` is the compact quantitative report a practitioner would plausibly use from material states
sampled by 60 minutes. It sits between the human packet `L60` and quantitative arm `X60`. It is not
a feature subset selected to make the study work, and later ex-situ construction does not imply
availability at minute 60.

If no credible conventional report exists for this cutoff/system, remove the arm before freeze.
Never invent one after collection.

## Provisional content

One row per event contains repeated 5-, 15-, and 60-minute blocks plus trajectory summaries.
Practitioner-approved predictive fields may include:

- actual state time, pH, temperature, fixed deviation/quality/missingness codes;
- detected/dominant phases under a frozen reference and matching rule;
- defensible quantitative or ordinal calcite/vaterite/aragonite estimates, with
  `unassigned_or_amorphous`, uncertainty, and detection status;
- fit/match quality in native units;
- a short frozen list of diagnostic peak positions, widths, or relative intensities; and
- predeclared changes across the three aliquots.

Crystallite size is included only when instrumental broadening and model validity are certified.
The report excludes full patterns, learned latents, arbitrary PCA, outcome-selected fields, and any
24-hour information.

Report version, source IDs/hashes, construction/availability time, software/operator,
instrument/session, and scan order are required lineage but prohibited model features.

## Field contract

For every retained field freeze:

| item | declaration |
| --- | --- |
| meaning and units | scientific quantity, precision, and rounding |
| parents | exact observations and external references |
| method | code/software/manual rubric and version |
| calibration | standards, broadening correction, and reference library |
| detection | thresholds and `not_detected`, `below_quantification`, `unclassifiable` behavior |
| uncertainty | interval/error or explicit lack of defensible uncertainty |
| availability | effect of missing aliquots or fields |

Nominal recipe fractions never substitute for measured phase fractions. Quantification must address
packing, preferred orientation, amorphous content, and preparation variation.

## Support and firewall

Commit an ordered `s60_feature_schema` before outcome access. The generator reads only frozen
cutoff-eligible inputs and external references. Every attempt receives `report_available`,
`partially_available`, or `unavailable` plus reasons. The primary arm uses only fully available rows;
partial-report encodings are predeclared sensitivities and do not erase support loss.

Retain unclassifiable and below-detection results. Manual steps record operator and uncertainty.
No predictive field, order, threshold, or missingness rule changes after unblinding.

## Freeze blockers

- practitioner approves realism, fields, units, and meaningful adequacy margins;
- a non-pilot example renders end to end;
- code, references, software, rounding, thresholds, and ordered feature schema are hashed;
- uncertainty, detection, partial, missing, and unclassifiable rules are executable;
- source lineage, state-cutoff, and any decision-deadline checks pass;
- prohibited-input tests reject provenance/lineage identifiers and later evidence; and
- no field was chosen from pilot outcomes.

Until these close, S60 is not a preregistered representation.
