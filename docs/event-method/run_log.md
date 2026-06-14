# Event-Method Run Log

Newest entry on top. Every run is bracketed per the run-log protocol: **hypothesis
(+ logic) → setup → expected result**, written and committed BEFORE the run; then
**result → validated / invalidated / surprising → updated hypothesis**, after.

---

## 2026-06-14 · Run 001 · Overfit-one-event sanity (oleogel WAXS)

Status: **BEFORE** (expectation on record; result pending).

### Hypothesis (+ logic)
The oleogel WAXS frames (zenodo 15268752) parse into clean per-frame diffraction
patterns that evolve over time through the cool/shear polymorph transition, and a
masked-frame model can reconstruct a held-out frame from other frames *within one
event*, clearly beating the event-mean baseline.
Logic: a single ~10 °C/min cooling ramp sampled at ~1 s is locally smooth, so the
information to reconstruct a missing frame sits in its temporal neighbours.

### The real sub-question
Will a learnable model beat **linear-time-interpolation**? Logic: at ~1 s spacing
the ramp is so densely sampled that per-q time interpolation should be *very strong*
almost everywhere and only fail across the sharp polymorph transition. So we expect
interpolation to be hard to beat on average — which would mirror the synthetic
`random_axis`/IDW result and motivate the latent (JEPA) objective over raw
reconstruction.

### Setup
- Data: one run (default `s_mopv_1s_10Cmin_10c`), WAXS only; frames → (n_q) spectra,
  coordinate = normalized time. Loader: `oleogel_ingest.load_run`.
- Task: within-event masked-frame. Observed pool = frames off the eval grid; eval
  candidates = every 5th frame. Target = PCA(8) of the z-scored spectrum.
- Models: `TinySetModel` (mean-pool set encoder) vs `event_mean` vs
  `linear_time_interp`. Metric: z-space MSE on eval candidates; plus training MSE
  (overfit check).

### Expected result (concrete prediction)
1. Pipeline runs end to end; spectra ≈ (≈300, ≈600), values look like evolving
   diffraction (not NaN/garbage). [parsing sanity]
2. Training MSE drops near zero (model can memorize). [learnability]
3. Eval: model ≪ event_mean (easily). [signal present]
4. Eval: linear_time_interp competitive with or better than the model on average.
   If the model clearly beats interpolation, that is a surprise worth probing at the
   transition.
