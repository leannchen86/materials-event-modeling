# Provenance-Recoverability Audit

Status: maintained control module. CLI:
[`run_provenance_leakage_audit.py`](../../scripts/run_provenance_leakage_audit.py); core:
[`provenance_leakage.py`](../../src/materials_event_modeling/audit/provenance_leakage.py).

## Question

How much of an incidental collection label can a simple model recover from a representation?

The answer is a screening signal. High recoverability says that a held-environment task evaluation
and carrier ablations are necessary; it does not prove that a downstream model used the signal or
that the signal harms transfer.

## Procedure

For each representation:

1. define the real provenance unit and the variables bundled by its label;
2. keep preprocessing, PCA, model selection, and calibration inside CV folds;
3. report balanced accuracy, chance, normalized recoverability, fold/seed spread, and class counts;
4. test metadata, coverage/acquisition geometry, measurement content, and physically motivated
   controls separately;
5. use specimen/material groups when descendants could cross folds; and
6. pair the probe with held-source/session task performance.

The normalized score is

\[
\frac{\mathrm{balanced\ accuracy}-1/K}{1-1/K},
\]

where $K$ is the number of provenance classes. The risk bands are heuristic triage thresholds, not
probabilities of contamination.

## opXRD calibration result

The current manifest is
[`provenance_leakage_audit_opxrd_r2.json`](../../data/manifests/provenance_leakage_audit_opxrd_r2.json).
It records repeated fold-local evaluation, curation-flag ablation, coverage controls, and run
identity. Source was recoverable from both metadata and standardized deposited spectra; cropping,
row normalization, and derivatives reduced but did not eliminate recovery.

Terminology matters: opXRD `xrd_pca` is the deposited pattern after fixed-grid interpolation,
minimum shift, and max normalization—not native instrument bytes. `Source` also bundles chemistry,
laboratory, instrument, software, and curation. The archive-to-standardization edge and input content
hashes were not audited in the historical run.

```bash
.venv/bin/python scripts/preprocess_opxrd.py --max-spectra 4096 --points 4096
.venv/bin/python scripts/run_provenance_leakage_audit.py \
  --dataset opxrd --include-controls --feature-ablation --cv-repeats 3 \
  --output data/manifests/provenance_leakage_audit_opxrd_r2.json
```

## Why the second dataset mattered

The [RRUFF and Severson replication](second_dataset_replication.md) separated two mechanisms that
opXRD confounds. In a chemistry-matched RRUFF subset, broad spectral content lost much of its laser-
line recoverability while acquisition geometry/coverage remained strong. Severson showed that
collection recoverability is not limited to spectra.

RRUFF inputs are primarily the archive's `Processed` Raman export. The RAW-to-Processed edge was
not tested. Severson batch/date bundles lot, policy, and collection style. These caveats bound the
mechanism claim without erasing the screening result.

## Downstream interpretation

The [n=6 opXRD comparison](recoverability_vs_transfer.md) found no descriptive relationship between
spectral recoverability and held-source task difficulty. That is the intended discipline:

```text
recoverability -> inspect carriers and require held-environment evaluation
recoverability != demonstrated shortcut use or predicted transfer failure
```

## Adding an active dataset

Add a loader returning named feature matrices, provenance labels, independent-unit groups, and
declared control pairs. Record exact input hashes and the capture/adapter edge above each matrix.
Do not add a dataset merely to increase a replication count; it must test a new carrier or a real
downstream decision.

## Limits

- provenance labels are often bundled proxies rather than clean causal factors;
- public archives are selected and processed before this audit sees them;
- few provenance units make confidence intervals and generalization claims fragile;
- a probe may miss nonlinear or rare provenance signal; and
- removing provenance predictability can remove legitimate physical information.

Use the audit to make evaluation harder and interpretations narrower, not to declare a
representation invariant.
