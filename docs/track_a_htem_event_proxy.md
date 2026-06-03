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

## Within-Library Spatial Field Prediction

### Pre-Run Hypothesis

If HTEM's useful event structure is inside each sample library rather than across
libraries, then within-library spatial predictors should beat a flat library-mean
baseline. Nearest-neighbor or distance-weighted interpolation should be strong on random
held-out positions. Holding out an entire spatial row should be harder and tests whether
the field model extrapolates across the grid.

### Command

```bash
python3 scripts/run_htem_spatial_field_prediction.py
```

Output manifest:

```text
data/manifests/htem_spatial_field_prediction_cu_s_sn.json
```

### Setup

The run used the same 65 `Cu|S|Sn` libraries and 2,860 position-level XRD rows.

The target was the full normalized XRD spectrum, not phase labels and not PCA labels:

```text
log1p(nonnegative intensity) -> per-spectrum max normalization -> full 661-point XRD
```

For each library, the experiment hides positions and predicts their XRD using only other
positions from the same library. Two split types were used:

- `random_positions`: randomly hide about 25% of positions per library.
- `held_out_row`: hide one full spatial row per library.

Baselines:

- `global_mean`: mean XRD over all observed training positions.
- `library_mean`: mean XRD over observed positions from the same library.
- `nearest_neighbor`: XRD from the closest observed position in the same library.
- `idw_3`: inverse-distance weighted average of the 3 closest observed positions.
- `idw_all`: inverse-distance weighted average of all observed positions.
- `xy_ridge_linear`: per-library linear ridge model from `(x, y)` to full XRD.
- `xy_ridge_quadratic`: per-library quadratic ridge model from `(x, y)` to full XRD.

### Results

Mean MSE improvement:

| Split | Model | vs global mean | vs library mean |
|---|---|---:|---:|
| `random_positions` | `library_mean` | +51.7% | +0.0% |
| `random_positions` | `nearest_neighbor` | +34.9% | -34.6% |
| `random_positions` | `idw_3` | +52.1% | +0.9% |
| `random_positions` | `idw_all` | +59.3% | +15.8% |
| `random_positions` | `xy_ridge_linear` | +58.3% | +13.7% |
| `random_positions` | `xy_ridge_quadratic` | +57.6% | +12.4% |
| `held_out_row` | `library_mean` | +50.7% | +0.0% |
| `held_out_row` | `nearest_neighbor` | +29.4% | -43.2% |
| `held_out_row` | `idw_3` | +51.0% | +0.7% |
| `held_out_row` | `idw_all` | +56.7% | +12.1% |
| `held_out_row` | `xy_ridge_linear` | +52.4% | +3.4% |
| `held_out_row` | `xy_ridge_quadratic` | +22.1% | -57.7% |

### Verdict

This validated the field-modeling hypothesis, with an important nuance.

The sample library itself is a strong event unit: `library_mean` cuts MSE by about 51%
versus the global mean. That means the spatial rows inside a library are not independent
static material rows; they share an event-level measurement field.

Spatial modeling adds real information beyond the library mean. `idw_all` improves over
the library mean by about 15.8% on random held-out positions and 12.1% on held-out rows.
Linear ridge also helps, especially on random positions.

But nearest-neighbor is worse than the library mean. So the field is not just locally
copyable from the closest measured point. The useful signal looks smoother and more
global across the library.

The row-holdout split is especially useful: `idw_all` still improves over library mean
when a full spatial row is missing, while quadratic ridge fails badly. This says simple,
stable spatial smoothers are better first baselines than higher-capacity coordinate fits.

### Research Implication

This is the first HTEM Track A result that cleanly supports the "event as field" framing.

The strongest public-data direction is no longer:

```text
sample metadata -> predict XRD for unseen sample libraries
```

It is:

```text
within a material-making event, learn the spatial/measurement field and predict held-out
measurements from partial observations
```

This maps much better to Track B. A lab dataset should be designed so that each event has
multiple partial observations over time, space, process state, or measurement modality.
Then the objective becomes: given partial event observations, predict missing/future event
measurements. The labels come later as probes.

## Multimodal Residual Check

### Pre-Run Hypothesis

The stricter multimodal question is whether local non-XRD measurements add information
beyond the strongest spatial smoother. `idw_all` is the baseline to beat. Local
measurements may help on random held-out positions, but should be treated skeptically
because they are noisy post-fabrication measurements and can overfit badly.

### Command

```bash
python3 scripts/run_htem_spatial_field_prediction.py --output data/manifests/htem_spatial_field_multimodal_cu_s_sn.json
```

Output manifest:

```text
data/manifests/htem_spatial_field_multimodal_cu_s_sn.json
```

### Setup

The script now includes three local-feature probes:

- `local_ridge_direct`: local non-XRD features directly predict full XRD.
- `xy_local_ridge_direct`: spatial coordinates plus local non-XRD features directly
  predict full XRD.
- `idw_all_plus_local_residual`: first predict XRD with `idw_all`, then use local
  non-XRD features to predict the remaining residual.

The local ridge alpha was set to `100000.0`. A weaker local ridge was numerically unstable
because the public local measurement fields include noisy, high-scale derived quantities.

### Results

Mean MSE improvement:

| Split | Model | vs library mean | vs `idw_all` |
|---|---|---:|---:|
| `random_positions` | `idw_all` | +15.8% | +0.0% |
| `random_positions` | `local_ridge_direct` | -1.4% | -20.5% |
| `random_positions` | `xy_local_ridge_direct` | -1.4% | -20.4% |
| `random_positions` | `idw_all_plus_local_residual` | +14.6% | -1.4% |
| `held_out_row` | `idw_all` | +12.1% | +0.0% |
| `held_out_row` | `local_ridge_direct` | -4.1% | -18.4% |
| `held_out_row` | `xy_local_ridge_direct` | -4.1% | -18.4% |
| `held_out_row` | `idw_all_plus_local_residual` | +9.5% | -3.0% |

### Verdict

The multimodal residual hypothesis was not validated.

Local non-XRD features did not beat the spatial smoother. Direct local-feature models were
worse than the library mean, and residual correction over `idw_all` made results slightly
worse: about 1.4% worse on random positions and 3.0% worse on held-out rows.

This does not mean multimodal event modeling is wrong. It means this public HTEM slice
does not yet show usable local-modality signal beyond a simple spatial field baseline.
The next useful move is to change the objective rather than tune the local ridge:

```text
predict missing XRD from partial XRD observations first;
then add other modalities only if they beat the spatial/XRD-only field baseline
```

For Track B, this is a design rule: collect additional modalities, but always compare
them against strong within-event baselines. Otherwise "multimodal" can become another
word for noisy metadata.

## Spatial Sampling Budget Curve

### Pre-Run Hypothesis

If each HTEM sample library behaves like a spatial measurement field, prediction of
unmeasured positions should improve as the number of observed positions increases.
Space-filling sampling should beat random sampling at small budgets if spatial coverage
matters.

### Command

```bash
python3 scripts/run_htem_spatial_sampling_curve.py
```

Output manifest:

```text
data/manifests/htem_spatial_sampling_curve_cu_s_sn.json
```

### Setup

The run used the same 65 `Cu|S|Sn` libraries. For each library, it observed only a fixed
number of positions and predicted all remaining positions. Two observation strategies
were compared:

- `random`: random observed positions, averaged over 5 repeats.
- `space_filling`: deterministic farthest-first spatial coverage, starting near the
  library center.

Models:

- `observed_library_mean`: mean XRD of observed positions in the same library.
- `idw_all`: inverse-distance weighted average of all observed positions.
- `xy_ridge_linear`: per-library linear coordinate model.
- `nearest_neighbor`: closest observed position.

### Results

Mean MSE and improvement versus `observed_library_mean`:

| Observed positions | Strategy | `observed_library_mean` MSE | `idw_all` MSE | `idw_all` vs library mean | `xy_ridge_linear` vs library mean |
|---:|---|---:|---:|---:|---:|
| 4 | random | 0.03099 | 0.03159 | -1.9% | -58.2% |
| 4 | space_filling | 0.03054 | 0.03061 | -0.2% | -1.1% |
| 8 | random | 0.02775 | 0.02714 | +2.2% | -6.1% |
| 8 | space_filling | 0.02674 | 0.02676 | -0.1% | +5.0% |
| 12 | random | 0.02666 | 0.02515 | +5.7% | +3.7% |
| 12 | space_filling | 0.02569 | 0.02495 | +2.9% | +8.6% |
| 16 | random | 0.02625 | 0.02417 | +7.9% | +7.3% |
| 16 | space_filling | 0.02522 | 0.02347 | +6.9% | +11.6% |
| 24 | random | 0.02548 | 0.02248 | +11.8% | +11.1% |
| 24 | space_filling | 0.02528 | 0.02176 | +13.9% | +14.7% |
| 32 | random | 0.02562 | 0.02172 | +15.2% | +13.1% |
| 32 | space_filling | 0.02596 | 0.02138 | +17.6% | +16.2% |

### Verdict

The hypothesis was mostly validated.

More observed positions improve prediction. The strongest spatial smoother, `idw_all`,
goes from roughly no improvement over the observed library mean at 4 positions to about
15-18% improvement at 32 positions.

Space-filling helps, but the lesson is nuanced. It usually lowers absolute MSE relative to
random sampling, especially as the observed budget grows. At tiny budgets, however, the
observed library mean is very hard to beat: with only 4 observations, `idw_all` is slightly
worse than the mean even with space-filling. That means we need enough partial observations
before a field model has real leverage.

Linear coordinate models are fragile under random low-budget sampling, but become useful
with space-filling. At 4 random points, linear ridge is much worse than the library mean;
at 8 space-filling points, it already improves over the mean by about 5%.

### Track B Design Rule

For a real event dataset, do not merely ask for "more measurements." Ask for partial
observations that cover the event field.

This result suggests a practical starting rule:

```text
For each material-making event, collect enough partial observations to support field
reconstruction, and prefer space-filling coverage over arbitrary convenience sampling.
```

For the calcium carbonate pilot, the analogue may not be spatial positions. It could be
time points, pH/temperature perturbations, repeated droplets/vials, or measurement
modalities. The important structure is the same: a material-making event should have
multiple partial observations so the model can learn to predict missing/future
measurements before we ask about labels.

## HTEM Masked-Event Reconstruction

### Pre-Run Hypothesis

The sharpest public-data test of Track B is not another static metadata predictor. It is:

```text
given partial raw XRD observations from one HTEM sample library, predict the missing XRD
spectra from that same library
```

Expected result:

- Partial raw observations should make the sample library self-predictive without phase
  labels.
- Raw-set neural models should beat coord-only controls if observed spectra carry
  event-specific signal.
- IDW may remain very strong because HTEM libraries are spatially smooth; a neural win
  over IDW is not assumed.

### Command

```bash
.venv/bin/python scripts/run_htem_masked_event_model.py \
  --folds 3 \
  --max-libraries 65 \
  --observed-counts 8 16 32 \
  --epochs 12 \
  --variants raw_set coord_only raw_residual \
  --train-random-repeats 1 \
  --eval-random-repeats 1 \
  --output data/manifests/htem_masked_event_model_cu_s_sn.json
```

Output manifest:

```text
data/manifests/htem_masked_event_model_cu_s_sn.json
```

### Setup

The run used 65 `Cu|S|Sn` sample libraries with 2,860 position-level XRD spectra. Each
fold held out entire sample libraries for evaluation. For each held-out library, the model
observed 8, 16, or 32 raw XRD spectra and predicted the remaining spectra.

Models and controls:

- `observed_event_mean`: average of observed XRD spectra from the same library.
- `idw_all`: inverse-distance weighted interpolation from observed positions.
- `xy_ridge_linear`: per-library linear coordinate model.
- `masked_event_coord_only`: neural model with observed spectra zeroed.
- `masked_event_raw_set`: neural model using observed spectra and coordinates.
- `masked_event_raw_residual`: neural model predicting the residual over IDW.

### Results

At 32 space-filling observed positions:

| Model | Improvement vs Train Mean | Improvement vs Event Mean | Improvement vs IDW |
|---|---:|---:|---:|
| `idw_all` | +58.9% | +17.9% | +0.0% |
| `masked_event_raw_residual` | +58.9% | +17.7% | -0.3% |
| `xy_ridge_linear` | +57.9% | +16.6% | -3.0% |
| `observed_event_mean` | +48.9% | +0.0% | -27.4% |
| `masked_event_raw_set` | +40.2% | -32.1% | -63.3% |
| `masked_event_coord_only` | -0.1% | -138.8% | -194.9% |

### Verdict

The event-field hypothesis was validated; the neural-architecture headline was not.

The clean result is:

```text
In HTEM Cu-S-Sn libraries, partial raw XRD observations inside one sample library can
predict the library's missing XRD field without phase labels.
```

This is stronger than saying "we trained a neural feature model" because it identifies the
unit of learning: the experimental field/event. The sample library is not just a set of
independent material rows.

The neural result is a useful guardrail. `coord_only` collapses, so coordinates alone are
not enough for the masked neural model. `raw_residual` nearly matches IDW, but does not
beat it. That means this public HTEM slice is still dominated by spatial field structure;
it should be used as a bridge and baseline test, not as evidence that universal event
embeddings have already been proven.

### Outreach Implication

The short expert-facing phrasing should be:

```text
Static material-row metadata failed to transfer across held-out Cu-S-Sn HTEM libraries,
but within one sample library, 32 raw XRD observations predicted the missing XRD field
17.9% better than the event mean and 58.9% better than the train mean, without phase
labels. This is why I am asking whether materials data infrastructure preserves enough
raw event feedback to scale event-native learning objectives.
```

## HTEM Event-Field Hard Controls

### Pre-Run Hypothesis

The strongest expert pushback against the HTEM result is:

```text
This is just spatial interpolation on a combinatorial library.
```

So the next useful run should not try to make the neural model look better. It should test
the boring explanation directly:

- Does correct spatial structure beat the observed event mean?
- Does the gain shrink on contiguous row/quadrant holdouts?
- Does IDW collapse or weaken when coordinates are shuffled?
- Do peak-aware metrics tell a different story than plain MSE?

### Command

```bash
.venv/bin/python scripts/run_htem_event_field_controls.py \
  --max-libraries 65 \
  --observed-count 32 \
  --output data/manifests/htem_event_field_hard_controls_cu_s_sn.json
```

Output manifest:

```text
data/manifests/htem_event_field_hard_controls_cu_s_sn.json
```

### Setup

The run used the same 65 `Cu|S|Sn` HTEM sample libraries. It compared:

- `random_32`: observe 32 random positions, predict the rest.
- `space_filling_32`: observe 32 spatially spread positions, predict the rest.
- `held_out_row`: observe all but one spatial row, predict the held-out row.
- `held_out_quadrant`: observe three quadrants, predict a contiguous held-out quadrant.

Models:

- `observed_event_mean`
- `idw_all`
- `idw_shuffled_coords`
- `nearest_neighbor`
- `xy_ridge_linear`
- `train_mean`

Metrics:

- plain MSE and MAE,
- intensity-weighted MSE,
- top-10%-intensity peak MAE.

### Results

| Split | `idw_all` MSE vs Event Mean | `idw_all` MSE vs Shuffled Coords | `idw_all` Peak MAE vs Event Mean |
|---|---:|---:|---:|
| `space_filling_32` | +19.9% | +30.3% | +56.7% |
| `random_32` | +15.1% | +25.4% | +41.5% |
| `held_out_row` | +11.3% | +13.7% | +23.5% |
| `held_out_quadrant` | +10.5% | +12.3% | +19.4% |

### Verdict

The hard controls validate the modest claim and weaken the overclaim.

Validated:

```text
HTEM sample libraries behave like experimental measurement fields. Correct within-event
spatial structure helps predict missing raw XRD, including on contiguous holdouts and
peak-aware metrics.
```

Weakened:

```text
This is not evidence that a neural event embedding has beaten simple event geometry.
```

The coordinate-shuffle null is especially useful. `idw_shuffled_coords` is worse than the
observed event mean on all four splits, while correct-coordinate IDW is better. That means
the result is not merely "all spectra in a library are similar." The spatial organization
of the event matters.

But row and quadrant holdouts are harder than space-filling prediction, so the original
snap result should be phrased as event-field evidence, not as a broad representation
learning breakthrough.
