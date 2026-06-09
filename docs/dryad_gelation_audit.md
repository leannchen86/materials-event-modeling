# Dryad Gelation Event-Native Audit

Source dataset:

```text
Data from: Optimizing gelation time for cell shape control through active learning
https://datadryad.org/dataset/doi%3A10.5061/dryad.8w9ghx3xn
```

Run:

```bash
.venv/bin/python scripts/audit_dryad_gelation_dataset.py \
  --check-downloads \
  --output data/manifests/dryad_gelation_audit.json
```

## Why We Did Not Start Here

The project started with XRD/HTEM because the initial question was still anchored in
materials taxonomies: phase labels, impurity, ambiguity, raw diffraction, and whether
learned representations expose structure hidden by labels.

That first path was useful:

- NIST gave label ambiguity and raw-XRD reconstruction baselines.
- opXRD showed raw measurement pretraining, interpolation controls, and source/provenance
  shortcuts.
- HTEM moved us from isolated XRD rows toward spatial measurement fields inside one
  experimental library.

But Anubhav Jain's reply sharpened the real bottleneck:

```text
experimental datasets are scattered/unavailable, lack metadata, and lack clear
metrics/problems
```

So Dryad-style process datasets are now the better next audit target. They are closer to
experiment-as-feedback-loop than final XRD rows.

## Hypothesis

Dryad gelation should be richer than Durham because it comes from an active-learning
experimental workflow with process and response variables.

Expected caveat:

```text
It may still be organized around publication figures rather than reusable
material-making event records.
```

## Top-Level Result

The audit found:

- 2 top-level files,
- `Dryad_Data.zip`, 5.14 GB,
- `README.md`, 4.83 KB,
- CC0 license,
- publication date Jan 10, 2025,
- keywords include TPEG hydrogel, active learning, cell morphology, and microrheology.

The README says the dataset is organized by figure folders, each including some combination
of raw data, processed data, and scripts. It also names microrheology, bulk rheology, and
UV-Vis spectroscopy as experimental contexts.

Keyword hits in the extracted README:

| Keyword | Count |
| --- | ---: |
| figure | 31 |
| pH | 7 |
| time-dependent | 3 |
| GPR | 3 |
| active learning | 2 |
| raw data | 2 |
| processed data | 2 |
| microrheology | 2 |
| UV-Vis | 2 |

## Event-Native Readiness

Positive signs:

- active-learning context,
- process variables such as pH, temperature, and concentration,
- time-dependent measurements,
- raw data included where applicable,
- processed CSVs and modeling scripts,
- public file metadata and CC0 license.

Negative signs:

- one large archive hides the internal event structure,
- no top-level event manifest,
- no top-level repeated-condition map,
- no top-level failed/ambiguous attempt log,
- no top-level provenance/session/run-order table,
- cannot define a benchmark from top-level metadata alone.

## Verdict

The hypothesis is validated.

Dryad gelation is richer than Durham at the study level, but the top-level public release
is still paper-shaped:

```text
one large archive + README + figure folders
```

That does not mean the dataset is bad. It means the event-native structure, if present, is
buried inside figure-specific folders rather than exposed as the primary interface.

## Next Decision

Do not download the full 5.14 GB archive by default.

Better options:

- find a file manifest or archive listing without full download,
- download only if we decide the size is worth it,
- ask authors whether a per-event manifest or subset exists,
- use this as evidence that even active-learning experimental datasets can be released in
  a form that hides the event-learning benchmark.

If we do inspect the archive, the benchmark question should be:

```text
Can partial process/time traces predict later gelation response better than final
condition/response-surface summaries?
```

If the answer cannot be constructed because the data is figure-specific, that is another
useful negative result.
