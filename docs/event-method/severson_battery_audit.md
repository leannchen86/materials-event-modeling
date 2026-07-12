# Severson Battery Dataset: Retained Source Audit

Status: historical source note, corrected 2026-07-12.

The Severson corpus contains 124 cell trajectories in four MATLAB/HDF5 batch files (roughly 3 GB
each), charge policy, per-cycle summaries, and within-cycle voltage/capacity/temperature arrays.
The local files are gitignored; download identity is recorded in
[`severson_download.json`](../../data/manifests/severson_download.json).

The representation studies used per-cycle `QDischarge`, `QCharge`, resistance, temperature, and
charge-time summaries. They did **not** carry the within-cycle `Qdlin`/`Vdlin` curves used by the
published early-life ΔQ(V) feature. Those arrays remained recoverable in the HDF5 archives but sat
above the adapter root, so no downstream arm could test their loss. See the
[adapter lesson](../spine/adapter_capture_policy_lesson.md).

`cycle_life` is an observed threshold time for cells reaching end of life. Records ending before
that threshold are right-censored: the adapter now represents them as `status="unknown"` plus
`cell.record_truncated=true`, not as failures or ambiguous outcomes.

The corpus is useful as a calibration case because it has repeated policies, trajectories, and
three collection batches. It cannot establish industrial downstream value: policy and batch are
confounded, the outcome is derived from the same cycling process, the adapted record omitted a
known channel, and the within-corpus ranking gain failed the decisive held-batch test. Current
results and limitations are summarized in the
[public-data findings](findings_summary.md).
