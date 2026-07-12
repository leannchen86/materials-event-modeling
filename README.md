# Materials Event Modeling

This repository asks a practical question: for a specified materials decision, which early
experimental signals survive a label or report, which are discarded, and do any gains transfer
across batches, instruments, or laboratories?

The project does **not** assume that raw traces beat labels. A compact report may be the right
compression for a task. The goal is to locate the earliest harmful reporting edge, retain enough
upstream evidence to revisit it, and identify the least costly adequate representation.

## Current program

The only active research program is a prospective, partner-grounded compression audit:

```text
measurement opportunity -> native artifact -> actual report -> delayed outcome -> decision
```

It requires a declared capture policy, physical-unit lineage, real conventional reports, retained
failures and censors, frozen decision deadlines, and held-environment evaluation. The canonical
documents are:

- [capture and representation boundaries](docs/spine/capture_vs_representation_design_note.md)
- [task-relevant compression audit](docs/spine/task_relevant_compression_audit.md)
- [downstream-failure research program](docs/spine/downstream_failure_research_program.md)
- [partner collection pipeline](docs/controlled-collection/partner_collection_pipeline.md)

The current implementation includes strict partner study/row/bundle schemas, an executable bundle
validator, and a synthetic golden bundle used only to test mechanics.

## Evidence status

Public datasets supplied calibration cases, not the final claim:

- collection provenance is often recoverable, so every learned advantage needs provenance-stressed
  evaluation;
- RRUFF spectra show that some inherited categories compress distinctions present in measurements,
  but they do not establish downstream value or a uniquely correct ontology;
- the Severson adapted per-cycle record supports within-corpus distinctions that a recipe summary
  cannot express, but the ranking gain failed held-batch transfer, censored records are not failures,
  and a known within-cycle signal sat above the adapter root;
- dense oleogel trajectories were largely solvable by time and interpolation baselines.

The [results ledger](docs/spine/results_ledger.json) owns load-bearing historical magnitudes. The
[event-method findings](docs/event-method/findings_summary.md) retain the public-data campaign
verdicts; they are not an invitation to resume model sweeps.

## Quick start

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q
.venv/bin/python scripts/check_results_ledger.py
.venv/bin/python scripts/validate_partner_bundle.py \
  data/examples/partner_golden_bundle_synthetic --readiness golden
```

See [PROJECTS.md](PROJECTS.md) for the repository map and [SKILL.md](SKILL.md) for current operating
constraints.

## Layout

```text
docs/spine/                 Current principles, protocols, and decision records
docs/controlled-collection/ Active prospective collection and partner contract
docs/provenance-critique/   Provenance-control methods and completed evidence
docs/event-method/          Frozen public/synthetic calibration record
schemas/                    Event and partner data contracts
src/                        Reusable validation and evaluation code
scripts/                    Reproducible entry points
data/manifests/             Small run receipts and legacy result artifacts
```
