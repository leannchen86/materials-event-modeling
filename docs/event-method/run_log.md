# Event-Method Run Log

Newest entry on top. Every run is bracketed per the run-log protocol: **hypothesis
(+ logic) → setup → expected result**, written and committed BEFORE the run; then
**result → validated / invalidated / surprising → updated hypothesis**, after.

---

## 2026-06-14 · Run 003 · Artifact-free density sweep (area-normalised oleogel WAXS)

Status: **BEFORE** (expectation on record; result pending).

### Hypothesis (+ logic)
Removing the period-3 scale artifact (per-frame area-normalisation, shown in Run 002 to
drive total-CV → ~0) makes adjacent frames genuinely smooth in time, so interpolation
should behave as physics expects: error falls monotonically with anchor density, and the
densest interpolation (≈1-frame spacing) becomes the *best* predictor — **beating the raw
reconstruction set-model**. That is the on-data version of the synthetic `random_axis`/IDW
result, and the concrete reason the next objective should predict in *latent* space (JEPA)
rather than reconstruct raw spectra. Normalisation is an explicit, logged preprocessing
flag; the raw loader stays raw.

### Setup
- Same as Run 002 (one run, WAXS, eval every 5th, model trained on k∈[4,48]) plus
  `--normalize area`: each frame scaled to the median total intensity before z-scoring.

### Expected result (concrete prediction)
1. Post-norm total-CV ≈ 0; the artifact's effect on interpolation is gone.
2. `interp_mse` now decreases ~monotonically with k.
3. `interp_dense_full_pool` drops sharply (well below event_mean 0.59 and below the model)
   — likely into ~0.05–0.2.
4. A real crossover appears: model wins at k≈6; interpolation wins by k≈24–48.
5. Net: dense interpolation **beats** the raw reconstruction model → HJ2-relevant
   on-data confirmation of `random_axis`/IDW → motivates the JEPA latent objective.

---

## 2026-06-14 · Run 002 · Density sweep + fair interpolation baseline (oleogel WAXS)

Status: **DONE** — predictions below left unedited; result follows the prediction block.

### Hypothesis (+ logic)
Run 001's model "win" over interpolation was an artifact of a 12-anchor sparse baseline.
With a *fair* baseline, interpolation error should fall monotonically as observed anchor
density rises, cross below the raw set-model at some density, and at full density
(interpolating from immediate ~1-frame neighbours) **beat the raw reconstruction model**.
Logic: a reconstruction objective rewards recovering smooth structure, which dense
interpolation already nails for free; the set-model has a fixed anchor budget and cannot
exploit arbitrarily dense neighbours. This is the synthetic `random_axis`/IDW result
expected to reproduce on real data — and the motivation for the latent (JEPA) objective.

### Setup
- One run (`s_mopv_1s_10Cmin_10c`), WAXS. eval = every 5th frame; pool = the rest.
- One set-model trained on random observed subsets k∈[4,48] (max_obs 48).
- Sweep observed anchor count k ∈ {6,12,24,48}: model vs linear interp vs event_mean,
  **same k evenly-spaced anchors** for model and interp.
- Plus `interp_dense_full_pool` = interpolation from the full pool (~1-frame spacing) —
  the strongest, model-independent baseline.
- Diagnostic: characterise the intensity oscillation (consecutive-frame shape corr,
  detrended total-intensity autocorrelation, area-normalisation check).

### Expected result (concrete prediction)
1. interp MSE decreases monotonically with k.
2. model MSE roughly flat in k (anchor-budget limited).
3. Crossover: model wins at k≈6–12 (reproduces Run 001); interp wins by k≈24–48.
4. `interp_dense_full_pool` is the lowest of all → dense interpolation beats the raw
   model on real data (motivates JEPA over raw reconstruction).
5. Oscillation is multiplicative (high consecutive-frame shape corr + oscillating total)
   → a scale/exposure artifact that area-normalisation largely removes.

### Result
z-space MSE on 60 eval frames; event_mean = 0.590.

| k | spacing (frames) | model | interp |
| ---: | ---: | ---: | ---: |
| 6 | 50.0 | 0.464 | 1.018 |
| 12 | 25.0 | 0.472 | 0.823 |
| 24 | 12.5 | 0.427 | 0.727 |
| 48 | 6.25 | 0.411 | 0.906 |

`interp_dense_full_pool` (≈1-frame spacing) = **0.869**. Oscillation: total CV 10%,
**period-3** (detrended autocorr lag3 = 0.89; every 3rd frame ~52k vs ~80k counts),
consecutive-frame *shape* corr = 0.9999 (identical shape, pure scale). Area-normalisation
drives total CV → ~0 and consecutive-frame L2 → ~5e-4.

### Validated / invalidated / surprising
- ✅ #5 — multiplicative scale artifact removed by area-normalisation; pinned as
  **period-3** (one low frame in every three; shapes identical → exposure/normalisation,
  not a different measurement).
- ✅ #2 — model MSE ~flat in k (0.46 → 0.41).
- ❌ #1 (interp monotonic) and ❌ #3 (crossover): invalidated — interp is non-monotonic
  and the model beats interp at *every* density.
- ❌❌ #4 — the decisive surprise: **dense full-pool interpolation scored 0.869, worse
  than even event_mean (0.59).** Dense interpolation cannot fail that badly on a smooth
  signal; it only does because the period-3 scale artifact makes adjacent frames jump ~35%
  in scale, and per-q z-scoring does not remove a per-frame *global* scale.

### The real conclusion (repeated lesson)
The density sweep is **confounded**: the interpolation baseline is poisoned by the
period-3 artifact, so "model beats interpolation" is *again* not evidence for the thesis —
Run 001 because anchors were sparse, Run 002 because the baseline and the z-metric are
corrupted by a data artifact. HJ2 still untested. ("Most ML bugs live in the data and fail
silently" — confirmed twice now.)

### Updated hypothesis / next test (Run 003)
Remove the artifact first: **area-normalise each frame** (proven to work), as a loader
option. Then re-run the sweep. Prediction: with the scale artifact gone, dense
interpolation becomes very strong and should *beat the raw reconstruction model*, and a
real crossover appears — finally making HJ2 testable. If dense interp then beats the raw
model, that is the on-data confirmation of the `random_axis`/IDW result and the motivation
to move to the JEPA latent objective. Also confirm whether SAXS shows the same period-3.

---

## 2026-06-14 · Run 001 · Overfit-one-event sanity (oleogel WAXS)

Status: **DONE** — predictions above left unedited; result below.

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

### Result
- Parsing: 300 frames × 2000 q-bins (q 0.53–5.12 Å⁻¹), all finite, 0 zero-frames;
  dominant peak q≈1.51 with slight drift = real polymorph evolution. PCA(8) keeps 92%.
- Eval z-space MSE (60 held-out frames, 12 observed anchors): **model 0.422**,
  event_mean 0.590, **linear_time_interp 0.823**.
- Training: model explains most PCA-target variance (train MSE 58 vs ~230 mean-baseline)
  but did not reach ~0.

### Validated / invalidated / surprising
- ✅ #1 parsing sanity — clean, real evolution.
- ⚠️ #2 learnability — the model *learns* (explains most train variance) but did NOT
  memorize to ~0. Reframe: each example has a *random* observed subset, so it's a learned
  function, not a lookup — "memorize to zero" was the wrong expectation for a
  stochastic-input task. Learnability holds.
- ✅ #3 model ≪ event_mean — yes (0.42 < 0.59), but modest (~28%): the persistent
  amorphous halo dominates variance and event_mean already captures it.
- ❌ #4 INVALIDATED (surprise) — linear interpolation was the *worst* baseline
  (0.82 > 0.59), not competitive; the model beat it handily.

### Why the surprise (and the catch)
The eval gives baselines only **12 sparse anchors** (~25-frame spacing), not the dense
~1 s neighbours my logic assumed — so this is NOT yet the "dense interpolation is strong"
regime. Sparse linear interpolation across an oscillating/transitioning signal
underperforms even the mean, so the model's win is partly an artifact of an
under-powered interpolation baseline. Also flagged: early frames show a total-intensity
oscillation (~80k/52k counts) at sub-anchor spacing that aliases and penalises
interpolation — origin unknown (beam/exposure normalisation? interleaved acquisition?).

### Updated hypothesis / next test
Pipeline + within-event learnability confirmed, but **the interpolation baseline is not
yet tuned hard enough to be a fair adversary** (article: tune baselines until it hurts).
Run 002: sweep observed *density* and plot model vs interpolation MSE against anchor
spacing — find where dense interpolation wins; that is the honest setting for HJ2. Also
investigate the intensity oscillation. Only after a tuned interpolation baseline do we
move to leave-one-run-out (cross-event) and the JEPA latent objective.
