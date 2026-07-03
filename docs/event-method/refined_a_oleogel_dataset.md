# Refined-a Target Dataset: Oleogel Polymorphic Transitions (zenodo 15268752)

Real-trajectory target for the event-method **refined-a** falsification. See
[../spine/capture_vs_representation_design_note.md](../spine/capture_vs_representation_design_note.md),
[jepa_event_model.md](jepa_event_model.md), [masked_event_model.md](masked_event_model.md).
Downloaded to `data/raw/oleogel_zenodo_15268752/` (gitignored). License CC-BY-4.0.

## What it is

Time-resolved in-situ synchrotron SAXS/WAXS of two monoglyceride oleogel systems (DMHR,
MOPV) crystallizing and undergoing **polymorphic transitions under shear** during a 10 °C/min
cool. Polymorph selection is a direct analog of CaCO3 polymorph choice. Headline modality:
**simultaneous SAXS (nanostructure / lamellar d-spacing) + WAXS (crystalline polymorph),
frame-aligned time series.**

## Structure (`SR-SAXS-WAXS.zip`, 3789 files, ~179 MB unzipped)

6 runs = **6 events**, laid out `MAGs/<run>/{SAXS,WAXS}/..._NNNN_sub.csv`:

| run (event) | sample | shear | frames (SAXS = WAXS) |
| --- | --- | --- | ---: |
| s_dmhr_1s_10Cmin_10c | DMHR | 1s | 307 |
| s_dmhr_25s_10Cmin_10c | DMHR | 25s | 298 |
| s_dmhr_50s_10Cmin_10c | DMHR | 50s | 280 |
| s_mopv_1s_10Cmin_10c | MOPV | 1s | 300 |
| s_mopv_25s_10Cmin_10C_redo | MOPV | 25s | 400 (**replicate**) |
| s_mopv_50s_10Cmin_10c | MOPV | 50s | 300 |

- SAXS and WAXS frame counts match per run → **two synchronized modalities per event**
  (~1.8k frames/modality total).
- Per-frame CSV = long `q,I` (comma-delimited); `NaN` at masked/edge q; negative I from
  background subtraction.
- Standalone `WAXS_*_1s_follow-up*.csv` = a **second, different format**: wide,
  `;`-delimited, `q`(605 points) × repeating `(I_subtracted, Sigma_I)` pairs = 120/120/60
  timepoints. The isothermal-hold WAXS follow-up.
- `d-spacings_MAGs.xlsx` = a tiny (7×9) hand-curated d-spacing/polymorph summary with merged
  cells = **the inherited label layer** (lossy, late, human). Use as a downstream probe only.
- **No per-frame time/temperature log is deposited** → frame index IS the time coordinate;
  absolute T can be inferred from the 10 °C/min rate if needed.

## Why it fits the thesis

- **Event-native:** planned conditions (sample × shear) + raw multimodal trajectory +
  replicate (`_redo`) + inherited label (d-spacings) frozen after raw. Maps cleanly onto
  `schemas/material_event.schema.json`.
- **Interpolation-resistant:** real polymorphic transitions (sharp nucleation / transition
  events) mean temporal smoothness does NOT trivially solve the masked-frame task — the
  property HTEM lacked. This is what makes HJ2 (JEPA beats IDW/ridge on the hard regime) a
  real test here.

## Caveats (from staring at the data)

- **Small event count** (6 runs, 2 samples × 3 shear). The frame-level masked task is
  well-powered (~300 timepoints/run); event-level transfer is thin (leave-one-run-out = 6
  folds). State this in any result; it is also the JEPA collapse-risk flagged in the sketch.
- Two CSV formats; NaN/negative-intensity handling; the label xlsx is messy (merged cells) —
  parse later, it is only a probe.
- Microscopy (129 MB) and DSC zips not yet pulled = extra modalities for the missing-modality
  task.

## Next

Write ingestion `MAGs/<run>` → `material_event` events (reuse
`src/materials_event_modeling/track_b/event_ingest.py`). First task: **within-event
masked-frame prediction on SAXS+WAXS**, baselines (`event_mean`/IDW/`coordinate_ridge`/RF)
tuned hard, then the JEPA variant; d-spacings used as a label probe only. Overfit a single
event first (Karpathy) before any scale-up.

## Dataset scouting update (2026-06-15, after Runs 001–008)

The zeolite backup ([zenodo 18972297](https://zenodo.org/records/18972297)) was inspected: its
NeXus groups (`data_S0h`, `S16h`, … `S144h`) are **timepoints of a single crystallization
run**, monitored by Raman (cryst/aging × solid/liquid) + ex-situ PXRD — i.e. **one event, not
many.** So it is *worse* than oleogel for cross-event work.

**Conclusion:** both open candidates we found are modality- and time-rich but **event-poor**
(oleogel = 6 near-identical runs; zeolite = 1 run). This is the empirical case for
**controlled-collection** — independent events across varied conditions/outcomes — which no
public in-situ crystallization deposit we found provides. See run_log Runs 006–008: on oleogel,
SAXS↔WAXS is largely time-redundant (not a model-capacity limit), so squeezing it further is
not the move.
