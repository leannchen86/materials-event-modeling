# Severson Battery Dataset Audit (process-vs-label, public many-event data)

Date: 2026-06-15 · The "do-it-ourselves" path for the **process/event** half of the thesis
(no lab needed): many independent process trajectories with an inherited summary label.

## Access
[data.matr.io project 5c48dd2b…](https://data.matr.io/1/projects/5c48dd2bc625d700019f3204) ·
CC-BY · Severson et al. 2019, *Nature Energy* ([escholarship](https://escholarship.org/uc/item/9532z8t0)).
Four MATLAB v7.3 (HDF5) batch files, **~3 GB each** (~7–10 GB total). batch1 direct file URL:
`https://data.matr.io/1/api/v1/file/5c86c0b5fa2ede00015ddf66/download`. Downloaded to
`data/raw/severson/batch1.mat` (gitignored). batch1 = **46 cells**; full set = 124 cells.

## Structure (per cell)
- **`cycle_life`** — the inherited label: cycles to 80% of nominal capacity (one scalar;
  batch1 range 636–1227, full set 150–2300).
- **`summary`** (per-cycle scalars = the raw degradation trajectory, ~1000–2300 points/cell):
  `QDischarge`, `QCharge`, `IR` (internal resistance), `Tavg/Tmax/Tmin`, `chargetime`, `cycle`.
- **`cycles`** (within-cycle raw curves per cycle): voltage, Qc, Qd, T, and `Qdlin`/`Tdlin`
  (interpolated discharge capacity / temperature on the `Vdlin` voltage grid — the basis of the
  famous ΔQ(V) feature).
- **`policy`** — the fast-charging protocol (a *planned condition*; varies across cells →
  control/provenance variable).

Parses cleanly with h5py (object-reference dereferencing per cell).

## Why it fits the thesis
- **Many independent events** (46 now, 124 available) — escapes the oleogel 6-event ceiling.
- Each event is a **raw process trajectory**; the label is a **single thresholded summary**.
- **The lossy-label angle:** `cycle_life` = cycles-to-80% is a threshold that collapses a
  continuous, multi-shape degradation curve — the same structure as garnet species (bin on a
  continuum) and metastability (Sun 2016), now in a *process* domain. Candidate lossy label.

## Caveats
- batch1 = 46 cells is enough for a first test; the other 3 batches are 3 GB each — do **not**
  download them until a first signal justifies it.
- Charging `policy` varies → must be a controlled/held-out variable (provenance), per our
  "models learn the lab" discipline.

## Next — proposed Run 015 (lossy-label lens on a process)
1. **Sanity (natural coordinate):** does the raw *early-cycle* trajectory predict `cycle_life`
   cross-cell, above a trivial control? (Severson showed yes — confirms data + pipeline.)
2. **Lossy (the novel part):** at *fixed* `cycle_life`, is there residual raw-trajectory
   structure — distinct degradation *modes/shapes* the single number collapses? If cells with
   the same lifetime split into multiple raw-trajectory clusters, the label is lossy.
Capacity-free, gap-over-controls, cell-grouped, policy held out.
