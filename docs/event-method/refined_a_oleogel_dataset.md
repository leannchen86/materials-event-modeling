# Oleogel SAXS/WAXS Calibration Dataset

Status: frozen source note. The original scouting plan is preserved at Git commit
`be750d33df2932c14e1022dcc0b67f9d78ab6bb1`; its JEPA recommendation and
interpolation-resistant premise were rejected by Runs 001–008.

Zenodo record 15268752 contains six in-situ oleogel runs: two materials by three shear conditions,
with one run marked as a redo. Each has roughly 280–400 frame-aligned SAXS and WAXS measurements.
The local download is gitignored under `data/raw/oleogel_zenodo_15268752/` (CC-BY-4.0).

Important source limits:

- six runs, not thousands of independent events;
- frame index is the only deposited cross-frame clock;
- negative intensities and masked `NaN` values reflect preprocessing;
- a small hand-curated d-spacing workbook is a separate report layer, not proof of label loss; and
- microscopy/DSC files were not part of the evaluated representation.

The masked-frame experiments were largely explained by time, interpolation, and
smoothness-preserving nulls. SAXS added little transferable WAXS information in leave-one-run-out
tests. This is a useful negative calibration case: many correlated frames do not compensate for
few independent events, and model capacity does not repair a weak task.

Current interpretation is in [findings_summary.md](findings_summary.md); the compact run index is
[run_log.md](run_log.md). The retired ingestion/model machinery is available at commit `8efe5bb`.
