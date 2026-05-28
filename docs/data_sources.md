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

Paper: https://arxiv.org/abs/2503.05577

Latest Zenodo concept record: https://zenodo.org/records/14254270

Local metadata/download:

```bash
python3 scripts/download_data.py opxrd --metadata-only
python3 scripts/download_data.py opxrd
python3 scripts/audit_opxrd_dataset.py --max-patterns 5000
python3 scripts/preprocess_opxrd.py --max-spectra 4096 --points 4096 --selection spread
python3 scripts/run_opxrd_reconstruction.py --max-samples 1024 --mask-widths 256 512 1024 --mask-strategies random peak --repeats 1 --pca-components 4 16 64
python3 scripts/run_opxrd_conv_reconstruction.py --max-samples 512 --mask-width 1024 --train-mask-strategy peak --eval-mask-strategy peak --epochs 25 --batch-size 64 --channels 32 --depth 10 --n-splits 3 --split-kinds random_kfold held_out_top_level_source
python3 scripts/run_opxrd_conv_scaling.py --sample-sizes 256 512 --seeds 0 1 --epochs 25 --n-splits 3 --split-kinds random_kfold held_out_top_level_source --mask-width 1024 --train-mask-strategy peak --eval-mask-strategy peak --channels 32 --depth 10 --batch-size 64
python3 scripts/run_opxrd_conv_scaling.py --sample-sizes 256 512 --seeds 0 1 --epochs 25 --n-splits 3 --split-kinds random_kfold held_out_top_level_source --mask-width 1024 --train-mask-strategy peak --eval-mask-strategy peak --prediction-mode residual --channels 32 --depth 10 --batch-size 64 --output data/manifests/opxrd_masked_xrd_conv_residual_scaling.json
```

Current plan:

- Use opXRD as the larger unlabeled experimental XRD pretraining pool.
- Keep NIST as a small transfer/probe benchmark because it has human disagreement labels.
- Start with fixed-grid raw-pattern objectives before using phase labels as probes.

Initial audit:

- 92,552 JSON diffraction patterns in the current Zenodo archive.
- 90,373 decoded as unlabeled, 1,069 as one-phase, 1,108 as two-phase.
- The archive is contributor-skewed: LBNL and INT dominate, so use deterministic spread or
  stratified sampling for pilots instead of the first files in archive order.

### HTEM DB

High-throughput experimental materials database with composition, synthesis/process
metadata, XRD, and properties. Useful for moving from raw XRD representation to
event-level representation.

Link: https://www.nature.com/articles/sdata201853

Data portal: https://htem.nlr.gov/

NREL submission page: https://data.nrel.gov/submissions/75

Local audit:

```bash
python3 scripts/audit_htem_dataset.py --endpoint-sample-ids 2
```

Current audit:

- 1,891 public sample-library records from the API.
- 1,847 records have nonempty composition fields.
- 1,739 records have at least one nonempty process field.
- 1,510 records have nonzero XRD availability.
- 1,403 records have composition, process metadata, and XRD availability.
- Sampled XRD spectra are position-resolved, but the public records remain
  sample-library snapshots rather than full material-making trajectories.

Track A use:

- Treat HTEM as a bridge dataset for event-proxy tasks, not as the final Track B object.
- Use it to design position-level and process-aware feedback tasks.
- Do not optimize around HTEM metrics as if its public schema were the target ontology.

### Failed Synthesis Dataset

Hydrothermal synthesis outcomes with successful and failed experiments. Useful as a
historical baseline for failure-as-data.

Link: https://www.nature.com/articles/nature17439
