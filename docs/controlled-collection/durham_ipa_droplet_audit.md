# Durham IPA Droplet Event Audit

Source: https://collections.durham.ac.uk/files/r12801pg44n

Local ignored archive:

```text
data/raw/durham_ipa_droplets/ipa_droplets_in_moist_air.zip
```

Reproducible audit:

```bash
python3 scripts/audit_durham_ipa_droplets.py \
  --output data/manifests/durham_ipa_droplet_audit.json
```

## Pre-Audit Hypothesis

Expected:

- This dataset should be closer to event-native data than final-image classification
  datasets because it contains drying videos and condition-indexed measurements.
- It should still fall short of a real event-learning benchmark because it was organized
  around a paper, figures, and selected movies rather than a reusable event log.

Validation criteria:

- Validate the first part if raw videos/time traces and process conditions are present.
- Validate the second part if repeated attempts, complete metadata, or figure-independent
  event manifests are missing.

## File Inventory

The downloaded archive contains 14 files:

- 9 compressed AVI videos,
- 3 Excel workbooks,
- 1 DAT file,
- 1 README DOCX.

Video inventory from `ffprobe`:

| File | Frames | Duration S | Resolution |
| --- | ---: | ---: | --- |
| `V1-RH38-30umNozzle-onGlass-compressed.avi` | 392 | 13.07 | 316x316 |
| `V2-RH56-30umNozzle-onGlass-compressed.avi` | 304 | 10.13 | 308x308 |
| `V3-RH61-30umNozzle-onGlass-compressed.avi` | 301 | 10.03 | 408x408 |
| `V4-Rh68-30umNozzle-onGlass-compressed.avi` | 305 | 10.17 | 408x408 |
| `V5-Rh74-30umNozzle-onGlass-compressed.avi` | 380 | 12.67 | 440x440 |
| `V6-RH78-50umNozzle-onGlass-compressed.avi` | 1242 | 41.40 | 788x788 |
| `V7-RH46-50umNozzle-onGlass-Particles-compressed.avi` | 155 | 5.17 | 450x450 |
| `V8-RH54-50umNozzle-onGlass-Particles-compressed.avi` | 200 | 6.67 | 500x500 |
| `V9-RH64-50umNozzle-onGlass-Particles-compressed.avi` | 140 | 4.67 | 500x500 |

Spreadsheet inventory:

| File | Sheets | Dimensions |
| --- | ---: | --- |
| `D-t data-Fig.1c.xlsx` | 1 | `A1:W400` |
| `h-r data-Fig.1b.xlsx` | 7 | sheets for `RH=17%`, `38%`, `48%`, `56%`, `61%`, `68%`, `74%` |
| `VLE-IPA-Fig.S2.xlsx` | 1 | `A1:N106` |

## README Signals

The README maps movies to humidity and imaging conditions:

- Movies 1-5: IPA droplet drying at RH 38%, 56%, 61%, 68%, 74%.
- Movie 6: RH 78%.
- Movies 7-9: trace-particle drying at RH 46%, 54%, 64%.
- Movies 1-6 are described as 5000 fps before compression; Movies 7-9 as 1000 fps.
- Nozzle/substrate conditions are embedded in filenames and README text.

The README also says several supporting movies or datasets are available only under
request. That is a direct example of the public-data ceiling: the experiment exists, but
the released package is not a complete event-native benchmark.

## Verdict

The hypothesis is validated.

The generated readiness flags are:

```text
can_smoke_test_early_trace_prediction: true
can_support_decisive_event_benchmark: false
```

This dataset is useful because it preserves more of the event than a final label:

- time-dependent videos,
- humidity as an explicit process/environment condition,
- some extracted time/profile spreadsheets,
- visible morphology/dynamics rather than only a class label.

But it is not yet a strong event-native benchmark:

- only 9 released videos,
- no obvious repeated same-condition event groups,
- several related movies/data are available only by request,
- metadata is partly in filenames and README prose rather than an event manifest,
- no explicit failed/ambiguous attempt log,
- no operator/session/run-order provenance,
- no ready-made early-trace/future-trace split definition.

## Next Benchmark Attempt

Smallest honest run:

```text
early video frames or early extracted profile -> later frames/profile summary
```

Initial baselines:

- humidity/nozzle/particle metadata only,
- nearest neighbor by humidity,
- early scalar profile features,
- early frame embeddings,
- simple temporal interpolation when target is a scalar trace.

Do not overclaim a positive result. With only 9 videos, this is a method smoke test and a
dataset-ceiling demonstration. The sharper result would be:

```text
This dataset has enough raw trace structure to prototype event-learning tasks, but not
enough repeated, fully logged events to make the benchmark decisive.
```

## Design Requirements For Our Own Gold Dataset

If we collect a tiny droplet/crystallization dataset later, it should fix the structural
gaps found here:

- at least 100-300 events,
- repeated recipes across days/sessions,
- raw video for every event,
- extracted traces saved as secondary observations,
- humidity/temperature/substrate/volume/concentration logged in a machine-readable table,
- failed, partial, and visually ambiguous runs retained,
- run order, device, camera settings, lighting, and operator/session recorded,
- labels assigned after raw data is frozen.
