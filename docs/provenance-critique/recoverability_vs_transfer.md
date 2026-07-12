# Recoverability is a risk signal, not a transfer predictor (opXRD, n=6)

As of 2026-07-03. Correlates, per opXRD source, how identifiable the source is against how
hard the historical residual CNN transfers to it when held out. Analysis over two committed
manifests; no model run. The retired analysis command and source manifests are available at Git
commit `12e7d7f`; the compact result manifest remains live.

The opXRD inputs are standardized deposited patterns after interpolation, intensity shifting, and
normalization—not instrument-native bytes.

> Read with [../spine/data_assumptions_and_limits.md](../spine/data_assumptions_and_limits.md):
> **n=6 sources** — every correlation here is descriptive, not inferential.

## The data

| source | n | spectral recoverability | metadata recoverability | transfer badness (CNN−interp MSE) | CNN wins |
| --- | ---: | ---: | ---: | ---: | --- |
| INT | 876 | 0.696 | 0.959 | −0.01036 | yes |
| LBNL | 3098 | 0.979 | 0.995 | −0.00450 | yes |
| CNRS | 47 | 0.723 | 0.957 | −0.00056 | yes |
| USC | 15 | 0.867 | 1.000 | −0.00023 | yes |
| HKUST | 23 | 0.565 | 0.957 | +0.00132 | **no** |
| EMPA | 34 | 0.882 | 1.000 | +0.00506 | **no** |

Transfer badness > 0 means the CNN loses to interpolation on that held-out source.

## Finding

- **Spectral recoverability does not predict transfer difficulty**: Spearman **0.03**
  (unrounded +0.029)
  (essentially zero). The most recoverable source (LBNL, 0.979) transfers *well*; a
  poorly recoverable one (HKUST, 0.565) transfers *badly*.
- **Metadata recoverability barely predicts it**: +0.203 (weak).
- **Source size has the larger descriptive association in this six-source table**:
  Spearman(log n, badness) = **-0.71**
  (unrounded -0.714). The
  two sources the CNN loses on (EMPA n=34, HKUST n=23) are the small ones; the strong
  winners are the two largest (INT, LBNL). This matches the branch's earlier per-source
  diagnostic (EMPA: small, low intensity, dense peaks; HKUST: sparse, interpolation-friendly).
  With n=6 this does not establish size as a predictor or identify a cause.

## Why this matters

The intuitive story — *a source is highly identifiable → the model latches its fingerprint
→ it transfers badly* — is **not present in this data**. Recoverability and transfer
difficulty are distinct axes here. So the branch's long-standing framing is now backed
rather than asserted: **recoverability is a screening / risk signal that says "audit and
control this," not a forecast that a given source will hurt downstream performance.** It
tells you where to *look*, not what you will *find*. Over-reading a high recoverability
score as "this source is contaminated" would be exactly the error this result guards
against — including for us.

Hard limits: 6 sources, one architecture, one mask width, 2 seeds, and size confounds both
axes (Spearman(recoverability, log n) = +0.314) without being deconfounded at this n. The
clean test is a second multi-source dataset with more sources and a paired
recoverability + held-out-source-task run — which the round-robin design in
[../controlled-collection/experiments.md](../controlled-collection/experiments.md) (Tier 1)
could provide with *causal* control over the provenance axis.
