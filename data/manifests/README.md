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

For the five archived synthetic row tables, each compact manifest has an `archived_rows` block. The
full table can be inspected without restoring it into the checkout:

```bash
git show <source_commit>:<source_path> | jq '.rows'
```

The synthetic event-method branch is closed; these artifacts are retained only as calibration
history.
