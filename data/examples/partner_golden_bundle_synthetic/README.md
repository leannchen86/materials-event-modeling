# Synthetic partner golden bundle

This fixture is entirely fictitious. It contains no partner, human, or experimental data and is permanently marked `nonconfirmatory`. Its values must not be interpreted as materials-science findings or used as confirmatory evidence.

The two fabricated attempts exercise the partner-bundle contract end to end: one ordinary execution with an exact delayed outcome, and one failed execution with a right-censored delayed outcome. The bundle includes physical lineage, native and portable traces, intermediate representations, conventional reports and labels, outcomes, transformations, decisions, costs, and all twelve required ledgers.

From the repository root, validate it with:

```bash
.venv/bin/python scripts/validate_partner_bundle.py \
  data/examples/partner_golden_bundle_synthetic/bundle.json \
  --readiness golden
```

A successful run prints a JSON report with `"valid": true` and exits with status 0.
The committed clean-run receipt is
[partner_golden_bundle_validation.json](../../manifests/partner_golden_bundle_validation.json).
It certifies mechanics only—not prevalence, effect size, transfer, or materials performance.
