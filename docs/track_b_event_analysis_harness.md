# Track B Event-Analysis Harness Run

Generated with:

```bash
.venv/bin/python scripts/run_track_b_synthetic_scaffold.py \
  --groups 16 \
  --replicates-per-group 3 \
  --output data/manifests/track_b_synthetic_event_scaffold_16x3.json \
  --events-output data/manifests/track_b_synthetic_event_bundle_16x3.json

.venv/bin/python scripts/run_track_b_event_analysis.py \
  --bundle data/manifests/track_b_synthetic_event_bundle_16x3.json \
  --output data/manifests/track_b_event_analysis_16x3.json \
  --include-only-raw-objective
```

## Purpose

This run rehearses the analysis path we want for real lab data:

```text
event JSON + raw spectra -> schema audit -> missingness audit -> split-sensitive
prediction -> retrieval -> label audit -> provenance audit
```

The input is still synthetic, so this is not chemistry evidence. The point is to make sure
the real-data harness asks the right questions before a lab dataset exists.

## Hypotheses

H1: The harness should reproduce the synthetic event-over-label signal under held-out-plan
splits.

H2: Held-out-batch splits should be reported separately because batch/session structure can
make claims stricter.

H3: Provenance predictability should be visible if raw spectra or event features carry
batch/operator/lot artifacts.

H4: Labels should be audited after raw/event objectives, not used as the primary objective.

## Key Results

Input audit:

- 48 synthetic events.
- 48 XRD file references.
- 0 labels marked as assigned before raw data freeze.
- Missing fields: `final_ph` in 14 events, `early_turbidity` in 7 events.

Held-out spectrum prediction, MSE improvement versus train mean:

| Split | Label only | Planned | Observed | Full event | Provenance only |
| --- | ---: | ---: | ---: | ---: | ---: |
| random event | +25.3% | +64.4% | +60.2% | +64.1% | +5.3% |
| held-out plan | +19.3% | +63.7% | +58.9% | +62.1% | +0.4% |
| held-out batch | +17.9% | +61.4% | +56.0% | +61.5% | -19.1% |

Replicate retrieval hit rate:

| View | Hit rate |
| --- | ---: |
| label only | 27.1% |
| planned conditions | 100.0% |
| observed trajectory | 35.4% |
| full event | 45.8% |
| provenance only | 56.2% |
| raw measurement PCA | 81.2% |

Label audit:

- Raw-PCA label silhouette: 0.066.
- 9 of 16 replicate groups had multiple labels, or 56.25%.
- Four legacy labels split across synthetic hidden regimes:
  `delayed_conversion_possible`, `mixed_or_impure`, `possible_mixture`, `reference_like`.

Provenance audit:

| Target | Feature source | Accuracy | Balanced accuracy | Majority baseline |
| --- | --- | ---: | ---: | ---: |
| batch | raw PCA | 47.9% | 47.9% | 50.0% |
| batch | event features | 54.2% | 54.2% | 50.0% |
| operator | raw PCA | 89.6% | 88.2% | 68.8% |
| operator | event features | 52.1% | 50.5% | 68.8% |
| reagent lot | raw PCA | 75.0% | 80.5% | 62.5% |
| reagent lot | event features | 77.1% | 74.3% | 62.5% |

## Verdict

H1 is validated. Under the held-out-plan split, planned conditions improve MSE by 63.7%
versus train mean, full-event features improve 62.1%, and label-only improves only 19.3%.
The harness reproduces the event-over-label signal.

H2 is validated as a reporting rule, with a caveat. Held-out-batch did not break the
synthetic event signal, but there are only two synthetic batches. For real lab data, batch,
date, operator, instrument session, and reagent lot need enough levels to support honest
held-out splits.

H3 is validated. Raw spectra predict synthetic operator and reagent lot far above simple
baselines. This is not a chemistry claim; it is a leakage warning. Real data may encode
operator, instrument/session, sample-preparation, or export artifacts in the raw
measurement itself.

H4 is validated. The harness uses labels as downstream probes: label silhouette is weak,
replicate groups often contain multiple labels, and label-only prediction is much weaker
than event/process views.

## Design Lesson

The lab packet should include these required provenance fields:

- batch id,
- operator id,
- reagent lot,
- instrument id,
- instrument session,
- raw export format,
- measurement date/time,
- sample-preparation route.

The analysis harness should always report:

- random-event split,
- held-out planned-condition split,
- held-out batch/session split,
- provenance predictability from raw spectra.

The uncomfortable result is useful: even raw measurement embeddings may learn the lab, not
the material-making process. That means provenance logging is part of the research design,
not admin overhead.

## Caveat

This harness currently supports the synthetic bundle format directly. For real lab data,
the same script should be extended to load a directory of event JSON files plus raw XRD
files in the lab's exported format.

