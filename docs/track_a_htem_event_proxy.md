# Track A: HTEM Event-Proxy Audit

## Pre-Run Hypothesis

HTEM should be more event-like than opXRD because it exposes composition, process,
measurement, and provenance fields, but it will probably remain a sample-library snapshot
rather than a full event-trajectory dataset.

This is not a model leaderboard. The point is to test whether a public dataset can stand in
for the material-making-event data structure that Track B needs.

## Command

```bash
python3 scripts/audit_htem_dataset.py --endpoint-sample-ids 2
```

Output manifest:

```text
data/manifests/htem_event_proxy_audit.json
```

## Result

The hypothesis was mostly validated.

HTEM is substantially more event-like than opXRD:

- 1,891 sample-library records were exposed by the public API.
- 1,847 records, or 97.7%, have nonempty composition fields.
- 1,739 records, or 92.0%, have at least one nonempty process field.
- 1,882 records, or 99.5%, have at least one measurement modality.
- 1,510 records, or 79.9%, have nonzero XRD availability.
- 1,403 records, or 74.2%, have composition, process metadata, and XRD availability.

The endpoint probe also shows that selected XRD-bearing sample libraries expose
position-resolved arrays:

- The sampled `prop` endpoint returned 44-position arrays for properties and spatial
  coordinates.
- The sampled `spectra` endpoint returned XRD arrays with 29,084 angle, measurement, and
  position values per selected sample library.
- One sampled optical payload contained 35,200 absorption/energy/position values.

## What Was Weakened

HTEM is still not a full material-making trajectory dataset.

- The primary public records are sample-library rows, not explicit synthesis-event logs.
- Process fields are mostly planned or summarized deposition metadata, not continuous
  process trajectories.
- Provenance is useful but incomplete: sample date plus person id are both present for
  66.1% of records.
- The public API endpoint named `count` appears to return records, and a rough
  `has_xrd=1` query returned the same number of records as the unfiltered endpoint. Treat
  API behavior as a public view, not a guaranteed ground-truth schema.
- Nonempty measurement availability does not prove the raw file is complete, comparable,
  or uniformly preprocessed.

## Verdict

HTEM is a good Track A bridge between opXRD and Track B, but not the destination.

It is useful for asking:

- Can we represent a sample library as many position-level measurement events rather than
  one static material row?
- Do process plus spatial coordinates help predict held-out spectra or properties?
- Do quality, availability, or phase-like labels behave like downstream projections rather
  than training targets?

It is not sufficient for the central Track B claim because it does not preserve the full
material-making event: planned conditions, observed process trajectory, raw measurement
files, failed measurements, operator/session/instrument context, and post-hoc labels as
separate layers.

## Track B Implications

For our own event dataset, we should separate fields that HTEM partially compresses
together:

- planned recipe variables,
- observed process trajectory,
- sample position and spatial context,
- raw measurement files,
- measurement availability and failed measurements,
- instrument/session/operator/date provenance,
- post-hoc human labels.

This audit supports the original direction: the public datasets are placeholders and
stress tests. They help us design the feedback loop, but they should not become the
ontology or the leaderboard.

## Event-Table XRD Prediction Run

### Pre-Run Hypothesis

Position-level HTEM rows should expose event-shaped structure, but random position splits
may overstate success because positions from the same sample library leak context.
Held-out-library and held-out-PDAC splits are the real controls.

Expected result:

- `sample_id_only` should look suspiciously strong on random position splits and collapse
  on held-out-library splits.
- `recipe_plus_position` should be weaker but more meaningful.
- `local_measurements_no_xrd` may help, but those inputs are post-fabrication
  measurements rather than prospective synthesis knowledge.

### Command

```bash
python3 scripts/run_htem_event_proxy.py --max-libraries 32 --min-xrd-positions 40 --chunk-size 4 --n-splits 4 --target-pca-components 8
```

Output manifest:

```text
data/manifests/htem_event_proxy_xrd_prediction.json
```

### Setup

The script selected 32 XRD-bearing sample libraries and built 1,408 position-level event
rows. Each row has sample metadata, deposition metadata, spatial position, local
non-XRD measurement summaries, and a normalized XRD spectrum with 661 angle points.

The objective was not phase classification. It was to predict PCA scores of normalized
position-level XRD spectra:

```text
log1p(nonnegative intensity) -> per-spectrum max normalization -> 8-component PCA target
```

This is a raw-measurement feedback task, not a inherited-label task.

### Results

Mean MSE improvement versus train-mean prediction:

| Feature set | Random position | Held-out library | Held-out PDAC |
|---|---:|---:|---:|
| `local_measurements_no_xrd` | +89.5% | -68.4% | -124.9% |
| `recipe_plus_position` | +86.9% | -17.8% | -131.8% |
| `recipe_only` | +86.7% | -17.0% | -131.3% |
| `sample_id_plus_position` | +83.4% | -0.9% | -0.5% |
| `sample_id_only` | +83.2% | +0.0% | -0.0% |
| `provenance_only` | +67.2% | -61.8% | -252.5% |
| `position_only` | -0.0% | -0.9% | -0.5% |

### Verdict

The run validated the main warning more than the optimistic version.

Random position splits look excellent, but this is mostly because rows from the same
sample library appear in both train and test. The important twist is that `recipe_only`
also looks excellent on the random split. That means explicit sample id is not the only
shortcut: sample-level recipe/composition fields can become implicit library identifiers
when every library contributes many nearby position rows.

Held-out-library transfer mostly collapses. The best honest sample-level feature sets do
not beat the train-mean baseline on average. Held-out-PDAC transfer is even worse, which
suggests that project/source/family shift is a major confound in this public view.

This does not mean HTEM is useless. It means HTEM is most useful right now as a control
design sandbox:

- Always report random-position and held-out-library splits together.
- Treat random-position wins as within-library interpolation or shortcut diagnostics.
- Avoid claiming event generalization from rows that share a sample library across train
  and test.
- Do not trust public sample-library metadata as a substitute for a true event trajectory.

### Next-Step Implication

The next HTEM test should not be a bigger model. It should be a cleaner question:

1. Restrict to a chemistry family or related element systems with many libraries, then
   repeat held-out-library transfer. This asks whether the previous collapse was mostly
   chemistry/family shift.
2. Separately, define a within-library spatial objective on purpose: predict one position's
   XRD from neighboring positions and process context. This treats a sample library as one
   material-making event field rather than pretending random-position success is broad
   material generalization.

Both are aligned with the project. The first tests prospective transfer. The second tests
whether a material-making event should be represented as a field/trajectory rather than a
static material row.

## Within-Family Control: Cu-S-Sn

### Pre-Run Hypothesis

If the prior held-out-library collapse was mostly caused by mixing unrelated chemistry
families, then restricting to one large element system should improve held-out-library
transfer. If recipe/process features still fail within a fixed element system, then the
public sample-library representation is probably too compressed for prospective event
generalization.

The largest exact element system with full XRD-position coverage was `Cu|S|Sn`: 65
libraries. All 65 are in PDAC `4`, so this run has no held-out-PDAC split.

### Command

```bash
python3 scripts/run_htem_event_proxy.py --element-system Cu,S,Sn --max-libraries 65 --min-xrd-positions 40 --chunk-size 5 --n-splits 5 --target-pca-components 8 --output data/manifests/htem_event_proxy_xrd_prediction_cu_s_sn.json
```

Output manifest:

```text
data/manifests/htem_event_proxy_xrd_prediction_cu_s_sn.json
```

### Setup

The run built 2,860 position-level rows from 65 `Cu|S|Sn` sample libraries. Each XRD
spectrum has 661 angle points. Local non-XRD measurement values, sums, and maxima were
signed-log transformed because the public electrical-property fields include extreme
scale artifacts.

### Results

Mean MSE improvement versus train-mean prediction:

| Feature set | Random position | Held-out library |
|---|---:|---:|
| `sample_id_plus_position` | +75.7% | -0.2% |
| `sample_id_only` | +75.6% | +0.0% |
| `local_measurements_no_xrd` | +41.4% | -1383.5% |
| `recipe_plus_position` | +31.4% | -18.5% |
| `recipe_only` | +31.4% | -18.3% |
| `provenance_only` | +4.8% | +1.8% |
| `position_only` | -0.0% | -0.2% |

### Verdict

The hypothesis that broad chemistry/family shift was the main cause was not validated.

Restricting to `Cu|S|Sn` reduced the random-position recipe shortcut from about +87% to
about +31%, but it did not rescue held-out-library transfer. Recipe/process features were
still worse than train mean by about 18%. This means the previous collapse was not merely
because we mixed many unrelated element systems.

The `sample_id_only` result is a useful sanity check: it still looks strong on random
position splits but becomes train mean on held-out-library, as expected. That confirms the
split is doing what it should.

The `local_measurements_no_xrd` result is a warning rather than a useful predictor. Even
after log-scaling extreme local measurement values, it generalizes very badly to held-out
libraries. These local measurements are post-fabrication derived measurements, not clean
prospective event inputs.

### Next-Step Implication

For HTEM, the better next task is not “make a stronger supervised predictor from public
metadata.” The better next task is to explicitly model the sample library as a spatial
measurement field:

```text
within one library, predict held-out position XRD from neighboring positions,
spatial coordinates, local composition/property traces, and shared recipe metadata
```

That task does not pretend to generalize to unseen material-making events. It asks whether
the event should be represented as a field/trajectory rather than a static row. This is
more aligned with Track B than further tuning held-out-library metadata prediction.
