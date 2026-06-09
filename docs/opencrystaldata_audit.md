# OpenCrystalData Event-Native Audit

Sources:

```text
OpenCrystalData Kaggle organization
https://www.kaggle.com/opencrystaldata/datasets

OpenCrystalData paper
https://doi.org/10.1016/j.dche.2024.100150
```

Run:

```bash
.venv/bin/python scripts/audit_opencrystaldata.py \
  --output data/manifests/opencrystaldata_audit.json
```

## Hypothesis

OpenCrystalData should be more ML-ready than Durham or Dryad, but likely more
image-analysis-ready than event-learning-ready.

Expected validation:

- programmatic dataset metadata is available,
- datasets contain in-situ crystallization/process images,
- metadata exposes conditions and auxiliary measurements,
- public framing centers image classification, segmentation, detection, or anomaly tasks,
- no event manifest or time-ordered event trace is visible at metadata level.

## Top-Level Result

The Kaggle API exposes 4 public OpenCrystalData datasets:

| Dataset | Size | Public Framing |
| --- | ---: | --- |
| `easyviewer-based-image-characterization` | 448 MB | segmentation/classification |
| `agcrystal-images` | 5.34 GB | object detection/segmentation |
| `cephalexin-reactive-crystallization` | 1.48 GB | classification/anomaly detection |
| `standard-polystyrene-microspheres-polys` | 1.72 GB | object detection/instance segmentation |

All four are CC BY-SA 4.0.

Positive event-like signals:

- in-situ images,
- process conditions such as concentration, solid loading, batch, seeded slurry, or
  incremental impurity addition,
- auxiliary measurements such as chord length distributions or offline particle size
  distributions,
- raw images in some datasets,
- batch/incremental-process language in some datasets.

Missing at metadata level:

- machine-readable event manifest,
- time-ordered trace or sequence definition,
- failed/ambiguous attempt log,
- provenance/session/run-order table,
- benchmark task like early event trace -> future measurement.

## Verdict

The hypothesis is validated.

OpenCrystalData is much more programmatically inspectable than Dryad and clearly useful
for ML image-analysis baselines. But the public metadata frames the datasets around image
classification, segmentation, object detection, anomaly detection, or particle-size tasks.

That makes it:

```text
image-task-ready, but not obviously event-native
```

This is a different ceiling from Durham and Dryad:

- Durham: raw traces exist, but there are too few repeated events.
- Dryad: rich active-learning experiment, but structure is hidden in one large figure
  archive.
- OpenCrystalData: clean public ML metadata, but the native interface is image-task
  benchmark data, not material-making event records.

## Next Decision

Use OpenCrystalData as a comparison case, not yet as the main event benchmark.

The optional concrete next step is:

```text
download the smallest 448 MB EasyViewer dataset and inspect whether files can be
reorganized into condition-indexed events
```

This would answer whether the event structure is absent, or merely hidden below the Kaggle
metadata layer.

Do not train an image classifier yet. That would drift into the existing task framing.
