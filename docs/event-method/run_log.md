# Event-Method Run Log

Newest entry on top. Every run is bracketed per the run-log protocol: **hypothesis
(+ logic) → setup → expected result**, written and committed BEFORE the run; then
**result → validated / invalidated / surprising → updated hypothesis**, after.

---

## 2026-06-15 · Run 005 · Cross-event missing-modality (predict WAXS from SAXS)

Status: **DONE** — predictions below left unedited; result follows the prediction block.

### Why this run (the pivot from Runs 001–004)
"Guess a hidden frame from its time-neighbours" is solved by interpolation on these smooth,
densely-sampled trajectories, so it cannot discriminate any model (Run 004: interp beats the
model 6/6 cross-event). This run changes the *task* to one interpolation cannot do: predict
the WAXS frame (crystalline-structure view) from the SAXS frame (nanostructure view) at the
*same instant*. No before/after to interpolate — only a learned cross-modal mapping helps.

### Hypothesis (+ logic)
SAXS and WAXS evolve together as the material crystallises (coupled physics), so SAXS[t]
should predict WAXS[t] well above the trivial mean — even across unseen events. A nonlinear
model may or may not beat plain linear regression, depending on how nonlinear the coupling is.

### Setup
- SAXS + WAXS for all 6 runs, frame-aligned, area-normalised, z-scored (train-fit, clipped
  to ±15 to fix the Run 004 blow-up). Cross-event leave-one-run-out (6 folds).
- Input: SAXS → PCA(30). Target: WAXS → PCA(8). Score = WAXS z-space MSE on the held-out run.
- Models: `ridge` (linear cross-modal) and a small `mlp` (nonlinear). Baseline = predict the
  train WAXS mean. Time-interpolation cannot enter (no WAXS observed for the test event).

### Expected result (concrete prediction)
1. ridge and mlp both beat the WAXS-mean baseline in ≥4/6 folds (SAXS carries cross-modal
   information that transfers across events). This would be the first positive signal.
2. mlp ≈ ridge or modestly better (coupling likely near-linear in PCA space).
3. If neither beats the mean: SAXS→WAXS coupling does not transfer across these 6 events
   (too few / too diverse) → push to the label-probe and/or more events.

### Result (median over 6 folds; but per-fold matters — it is bimodal)
WAXS z-MSE: waxs_mean 0.557 · ridge 2.54 · mlp 0.984. ridge beats mean **3/6**, mlp **3/6**.
Per fold splits into two groups:
- **Wins** (cross-modal helps a lot): dmhr_25s (mean .407 → ridge .149), dmhr_50s
  (.551 → .124) — ~3–4× better than the mean, which time-interpolation could never achieve.
- **Losses** (the learned map extrapolates badly): dmhr_1s (ridge 4.72), mopv_1s (ridge
  8.32), mopv_50s (.277 → .362). mlp is far less catastrophic than ridge (1.0 vs 4.7; 1.2 vs
  8.3) but still loses on these folds.
- redo fold: scale still inflated (mean 11; ±15 clip helped vs Run 004 but the replicate's
  normalisation is still off).

### Validated / invalidated / surprising
- ❌ #1 — only 3/6 folds beat the mean (predicted ≥4/6). Not the clean positive signal.
- ✅-ish #2 — mlp ≈ ridge where both work, and far more *robust* on the failing folds →
  linear extrapolation is the dominant failure mode.
- 🔎 The real finding: the result is **bimodal** — big, real, interpolation-proof cross-modal
  wins on half the folds, and extrapolation failures on the other half. With only 6 events
  (2 samples × 3 shear) each fold removes a unique condition the others may not cover, so
  cross-event transfer is unreliable. **We have hit the dataset's 6-event ceiling** (flagged
  in the dataset audit).

### Conclusion
The cross-modal task is the *right* kind of test — interpolation cannot do it, and the model
wins big on the folds it transfers to — but **6 events is too thin to establish cross-event
generalisation.** This is the first genuine positive *signal* and, simultaneously, the
empirical case for controlled-collection (more events).

### Updated hypothesis / next tests
1. **Time-only ablation (Run 006a):** does SAXS beat a model given only the candidate *time*?
   Cleanly attributes any win to cross-modal info vs the smooth time-prior. Cheap, decisive.
2. **Label-probe (Run 006b):** does a frozen representation predict the d-spacing/polymorph
   label better than baselines — the most direct "representation vs inherited label" test,
   and within-modality, so less exposed to cross-event scarcity.
3. **Dataset ceiling:** more events (controlled-collection) or a richer deposit (zeolite,
   zenodo 18972297) are needed to settle transfer. Also fix the replicate fold's z-scoring.

---

## 2026-06-15 · Run 004 · Leave-one-run-out cross-event (the real HJ2 test)

Status: **DONE** — predictions below left unedited; result follows the prediction block.

### Hypothesis (+ logic)
Cross-event is the only setup that forces the model to *use* its observed anchors: trained
on 5 events, it cannot have memorised the held-out event's time→spectrum curve (Run 003's
confound), so it must read the test event's anchors to predict its missing frames.
Logic + prediction: dense within-test-event interpolation (~1-frame spacing, ≈0.22 in
Run 003) is a strong adversary; a model that must *transfer* across events will likely do
worse than within-event memorisation, so **dense interpolation probably beats the
cross-event model on average** — the `random_axis`/IDW result on real data, motivating the
JEPA latent objective. The alternative (model beats dense interp cross-event) would be
strong positive evidence for event-native representation.

### Setup
- All 6 runs, WAXS, area-normalised. Leave-one-run-out (6 folds). z-scoring + PCA fit on
  *train events only* (no leakage). Model: `train_set_model_multi` on the 5 train events.
- Eval per fold: held-out event, every-5th frame as candidates, rest as pool. model given
  k∈{6,12,24,48} evenly-spaced anchors from the test pool; vs `interp_dense` (full test
  pool, ~1-frame spacing); vs `event_mean` (test-pool mean).

### Expected result (concrete prediction)
1. **Diagnostic:** cross-event model MSE now *decreases with k* (must use context) — unlike
   Run 003's flat curve. If it is still flat, the model is learning a generic time→spectrum
   prior, not using anchors.
2. `interp_dense` ≈ 0.2–0.3 per fold (same as within-event).
3. Cross-event model (k=48) worse than the within-event 0.174 — likely ~0.3–0.5.
4. **Decisive:** dense interpolation beats the cross-event model in ≥4/6 folds on average.
5. Caveat: only 6 folds, 2 samples × 3 shear — suggestive, not conclusive.

### Result (robust = per-fold; aggregate mean corrupted by one degenerate fold)
5 clean folds + 1 degenerate (`mopv_25s_redo`: train-only z-scoring blew up in q-bins where
train variance ≈ 0 → MSE in the 100s; relative ordering unaffected). Median over clean folds
(z-space MSE): **model (any k) 0.173 · interp_dense 0.023 · event_mean 0.261**. Interpolation
beats the model in **6/6** folds. Per clean fold the model MSE was **flat across k = 6→48**
(e.g. dmhr_1s: 0.288 / 0.286 / 0.286 / 0.287).

### Validated / invalidated / surprising
- ✅✅ #4 — dense interpolation beats the model in **6/6** folds (~7× better median). Decisive.
- ❌ #2 — interp far better than predicted (~0.02 vs my 0.2–0.3): dense interpolation on
  smooth, artifact-free trajectories is near-perfect.
- ❌ #1 **+ the key finding** — model MSE is **flat in k even cross-event**: the model ignores
  its anchors entirely. It collapsed to a *time-conditioned population mean* (≈ the average
  spectrum at normalised time t across events) — the easiest way to minimise cross-event
  reconstruction MSE. The raw-reconstruction objective does not use event context at all.
- ⚠️ methodological: guard train-sd / clip z (the degenerate fold) before reusing the harness.

### The conclusion — HJ2 answered (a clean, expected negative result)
On real artifact-free cross-event data, the raw-reconstruction masked-event objective (a) is
decisively beaten by dense time-interpolation and (b) collapses to a population-mean prior
that ignores observed context. **Raw reconstruction is the wrong objective** — the synthetic
`random_axis`/IDW result, now confirmed on real data. Green light for the latent (JEPA)
objective.

### Updated hypothesis / next test — and a task pivot
Deeper realisation: **the masked-frame task is interpolation-solvable on densely-sampled
smooth trajectories** (interp ≈ 0.02), so it is a poor discriminator for *any* model —
including JEPA — because there is little event-specific, non-interpolable signal at ~1 s
spacing. The thesis-relevant tasks are the ones interpolation *cannot* do:
1. **Missing-modality** — predict the WAXS frame from the same-timepoint SAXS frame (and
   vice versa). Time-interpolation is irrelevant; only a cross-modal representation helps.
2. **Label-probe** — does a frozen event representation predict the d-spacing / polymorph
   label better than baselines? (The actual "representation vs inherited label" question.)
3. **Replicate retrieval** (the `_redo` pair).
Run 005: run the JEPA objective (per `jepa_event_model.md`) but **evaluate on
missing-modality + label-probe, not masked-frame reconstruction**, and fix the z-score
guard. This pivots from "predict a held-out frame" (interpolation wins) to "use cross-modal /
cross-event structure" (interpolation has nothing to say).

---

## 2026-06-14 · Run 003 · Artifact-free density sweep (area-normalised oleogel WAXS)

Status: **DONE** — predictions below left unedited; result follows the prediction block.

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

### Result
Post-norm: total-CV ≈ 0, lag-3 autocorr 0.043 (period-3 artifact gone), shape corr 0.9999.
event_mean = 0.596; `interp_dense_full_pool` = **0.224** (was 0.869 pre-norm).

| k | spacing | model | interp |
| ---: | ---: | ---: | ---: |
| 6 | 50.0 | 0.176 | 0.313 |
| 12 | 25.0 | 0.174 | 0.289 |
| 24 | 12.5 | 0.174 | 0.266 |
| 48 | 6.25 | 0.174 | 0.272 |

### Validated / invalidated / surprising
- ✅ artifact removed — `interp_dense` 0.869 → 0.224, total-CV → 0. The fix worked.
- ✅ #2 — interpolation improves with density (0.313 → 0.266).
- ❌ #4 / #5 — INVALIDATED: interpolation did **not** win. The model beats interp at every
  density and beats dense full-pool interp (0.174 vs 0.224).
- 🔎 The real catch: **model MSE is essentially constant (0.176 → 0.174) across anchor
  counts 6 → 48** — the model barely uses its observed set. It has learned a within-event
  *time → spectrum* regression and maps candidate-time → spectrum (a *learned within-event
  interpolation*, smoother than piecewise-linear). That beats interpolation but is NOT
  "event-context representation" — it is effectively a memorised trajectory curve.

### The conclusion (third honest non-result)
With a fair, artifact-free, densely-tuned interpolation baseline the model wins — but the
within-event setup **cannot distinguish a useful representation from a memorised
time → spectrum curve** (the model ignores its anchors). So this is still not the HJ2 test.
The within-event design is exhausted.

### Updated hypothesis / next test (Run 004)
**Leave-one-run-out across the 6 events.** Train on 5 runs, test on the held-out run: the
model cannot memorise the test event's curve, so it must use the test event's *observed
anchors* to predict its held-out frames. Predictions: (a) cross-event model MSE now varies
with anchor count (forced to use context); (b) dense within-test-event interpolation is the
strong adversary; (c) if the cross-event model still beats dense interpolation → genuine
evidence for event-native representation; if interpolation wins → the `random_axis`/IDW
result on real data → go to the JEPA latent objective. Either way, finally a real HJ2 test.

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
