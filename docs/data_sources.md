# Data Sources

## Candidate Public Datasets

### NIST Open Combinatorial Diffraction Dataset

Useful for label ambiguity and human/machine consensus questions.

Link: https://catalog.data.gov/dataset/dataset-an-open-combinatorial-diffraction-dataset-including-consensus-human-and-machine-le-0de06

Local download:

```bash
python3 scripts/download_data.py nist_mds2_2301
python3 scripts/audit_nist_dataset.py
python3 scripts/preprocess_xrd.py nist_mds2_2301
python3 scripts/run_ontology_tests.py nist_mds2_2301
python3 scripts/run_xrd_reconstruction.py nist_mds2_2301
python3 scripts/run_xrd_autoencoder.py nist_mds2_2301
python3 scripts/plot_nist_diagnostics.py nist_mds2_2301
```

Initial shape:

- 352 XRD spectra, each with 3,841 2-theta intensity points.
- 352 aligned composition/temperature rows.
- 192 human-labeled rows from five human labelers.
- 152 machine-labeled rows from four machine-labeling methods.

### opXRD

Large open experimental powder XRD dataset. Useful for self-supervised XRD pretraining.

Link: https://arxiv.org/abs/2503.05577

### HTEM DB

High-throughput experimental materials database with composition, synthesis/process
metadata, XRD, and properties. Useful for moving from raw XRD representation to
event-level representation.

Link: https://www.nature.com/articles/sdata201853

### Failed Synthesis Dataset

Hydrothermal synthesis outcomes with successful and failed experiments. Useful as a
historical baseline for failure-as-data.

Link: https://www.nature.com/articles/nature17439
