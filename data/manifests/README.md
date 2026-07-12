# Result Artifacts

This directory contains a historical mix of run receipts, result summaries, download inventories,
and legacy row outputs. A filename here is not evidence that a run captured complete inputs or is
fully reproducible.

Current rules:

- `docs/spine/results_ledger.json` identifies the manifests behind load-bearing historical numbers.
- New receipts record run identity and input artifact hashes; run identity alone does not verify
  data lineage.
- Large deterministic row tables do not belong inline. Keep a summary plus row count and content
  hash, and store the table in an external artifact or an identified Git snapshot.
- Bare `NaN` is not valid JSON; use `null` with an explicit missing-value reason.

The closed synthetic event-method manifests were removed from the live tree. Their compact final
snapshot is commit `8efe5bb`; the full row-bearing snapshot is commit `c137a89`. Inspect either
without restoring it into the checkout:

```bash
git show <commit>:<path>
```

They are calibration history, not active inputs.

Retired NIST, HTEM, Durham, and one-off opXRD/RRUFF commands and manifests are available at commit
`12e7d7f`. The live directory keeps only current inputs/receipts and manifests referenced by the
results ledger or maintained protocols.
