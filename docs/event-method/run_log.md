# Event-Method Run Log

Newest entry on top. Every run is bracketed per the run-log protocol: **hypothesis
(+ logic) → setup → expected result**, written and committed BEFORE the run; then
**result → validated / invalidated / surprising → updated hypothesis**, after.

---

## 2026-06-15 · Run 013 · RRUFF peaks-only vs heavy-blur (closes Run 012 B)

Status: **BEFORE** (expectation on record; result pending).

### Why
Run 012's blur was too gentle to separate the sharp Raman peaks (real fingerprint) from the
broad envelope (possible baseline/provenance). Run 013 splits the spectrum cleanly and tests each.

### Method
Three representations, same specimen-grouped k-NN (8 seeds):
- `full`
- `peaks_only` = full − Gaussian-blur(σ≈15 pts), renormalised — sharp peaks kept, broad shape removed.
- `heavy_blur` = Gaussian-blur(σ≈100 pts), renormalised — broad shape only, fingerprint destroyed.
Cases: garnet species, garnet family, CaCO3, TiO2, distinct-5 (reference). Majority reported.

### Prediction
- `peaks_only` ≈ `full` → the signal IS the Raman fingerprint → provenance/broad-feature worry
  excluded.
- `heavy_blur` ≪ `full`, dropping toward majority → broad shape alone carries little.
If instead peaks_only collapses OR heavy_blur stays high → the signal lives in broad features and
the interpretation must be revised.

---

## 2026-06-15 · Run 012 · RRUFF robustness ablations (provenance, difficulty, error bars)

Status: **DONE** — predictions below left unedited; result follows the prediction block.

### Why
Before locking the Runs 009–011 interpretation, exclude the explanations that could overturn it.

### Tests
A. **Provenance — single wavelength:** re-run polymorph (010) + garnet (011) probes on 532 nm
   only (010/011 had mixed 532+785). Must survive, else a wavelength↔label shortcut was at work.
B. **Provenance — structure-blind control:** classify on a heavily Gaussian-blurred spectrum
   (sharp Raman peaks removed, broad envelope kept). If blurred ≈ full → signal is broad/baseline
   (suspect); if it collapses → signal is in the real peaks (genuine structure).
C. **Multi-class difficulty control:** 5 distinct-structure minerals, 5-way k-NN. If they hit
   ~0.95 while garnet species sit at 0.73, the gap is the continuum, not "5-way is hard".
D. **Error bars + balanced accuracy:** multi-seed mean±std and balanced accuracy for polymorph
   groups, garnet species/family, and Run 009 raw-vs-composition.

### Prediction
A. Polymorph + family separations survive at 532-only (perhaps lower n/acc); garnet species stays
   ~0.7 with within-family errors.
B. Blurred ≪ full (signal is in the sharp peaks → real structure, not provenance).
C. distinct-5 ~0.9–1.0 ≫ garnet species 0.73 → confirms continuum, not difficulty.
D. raw ≈ composition (009) overlaps within error bars; balanced accuracy does not overturn the
   polymorph/family wins.
If instead blurred ≈ full, OR 532-only collapses, OR distinct-5 ≈ garnet species → the
interpretation is threatened and must be revised.

### Result
- **A. Single wavelength (532 only):** CaCO3 0.875±0.10 · TiO2 1.0 · Al2SiO5 1.0 · SiO2 0.946;
  garnet species 0.75±0.08, family 1.0 → all **survive**.
- **B. Structure-blind (full vs blurred, σ≈48 cm⁻¹):** garnet 0.736→0.713 · CaCO3 0.944→0.933 ·
  TiO2 1.0→0.875 → blurred ≈ full (**not** the predicted collapse).
- **C. Difficulty control:** distinct-5 minerals **0.992±0.01** vs garnet 5-way species **0.736**.
- **D. Error bars / balanced acc:** polymorphs CaCO3 0.944 (bal 0.92) · TiO2 1.0 · Al2SiO5 1.0 ·
  SiO2 0.909; garnet species 0.736±0.06 (bal 0.75), family 1.0; run009 raw 0.764±0.024 vs
  composition 0.722±0.016 (273 classes).

### Validated / invalidated
- ✅ **A** — survives single wavelength → no wavelength↔label provenance shortcut.
- ⚠️ **B — INCONCLUSIVE (prediction wrong):** blurred ≈ full. But σ≈48 cm⁻¹ was too gentle — it
  smears fine splitting yet keeps the major-band envelope (itself real structure), so it neither
  confirms nor excludes a broad-feature/baseline contribution. An imperfect control; needs the
  complement (peaks-only) → Run 013.
- ✅✅ **C** — distinct-5 (0.992) ≫ garnet species (0.736) → the low species accuracy is the
  **continuum, not "5-way is hard"**. Decisively supports the lossy-species claim.
- ✅ **D** — polymorph + family wins robust under error bars AND balanced accuracy (not
  majority-inflated); raw ≈ composition holds (raw a reliable but small ~4-pt edge).

### Conclusion
Three of four controls pass and strengthen the interpretation; the novel lossy-species claim is
**decisively** supported by the difficulty control (C). The one loose end is the structure-blind
control (B): the blur was too gentle to prove the signal lives in the sharp Raman peaks vs broad
features. A (single-wavelength) already gives provenance assurance, but to fully close "Raman
fingerprint vs broad/baseline artifact?" run the complement.

### Next (Run 013)
**Peaks-only (high-pass / derivative) representation:** if peaks-only ≈ full, the Raman fingerprint
carries the signal → provenance/baseline excluded. Pair with a heavier blur (removing major bands)
as the negative control. Closes B; then the interpretation is locked.

---

## 2026-06-15 · Run 011 · RRUFF labels-are-lossy probe (solid-solution species vs family)

Status: **DONE** — predictions below left unedited; result follows the prediction block.

### Why (and a recon finding)
Run 010 showed polymorph labels are natural coordinates of raw Raman. The novel claim is the
opposite — labels that are LOSSY. Recon first ruled out two candidates on RRUFF:
- `##STATUS` ambiguity is **confounded**: unconfirmed specimens are overwhelmingly in rare
  minerals (median 1 specimen/mineral vs 2 for confirmed; only 51/445 in minerals with ≥3
  specimens), so any mis-neighbouring is frequency, not ambiguity. Dropped.
- plagioclase has only endmembers (albite 8, anorthite 9), no intermediates → can't sample a
  continuum.
Garnet is well-populated and has TWO solid-solution sub-families: pyralspite (almandine Fe /
pyrope Mg / spessartine Mn) and ugrandite (grossular Ca-Al / andradite Ca-Fe). Clean lossy-label
test: if species labels are lossy bins on a within-family continuum, raw space should separate
the FAMILIES (a real structural/Ca distinction) but BLEND species within a family.

### Method
Garnet species (5-way) vs family (2-way: pyralspite/ugrandite), specimen-grouped k-NN, 5 seeds.
Metrics: species_acc, family_acc, and the fraction of species-errors that stay WITHIN the true
family. Controls: majority, shuffled. Olivine (forsterite/fayalite/tephroite, one family) as a
secondary confusion check.

### Prediction
1. family_acc HIGH (~0.85–1.0) — Ca vs Fe/Mg/Mn is a natural coordinate.
2. species_acc LOWER than family, species-errors predominantly WITHIN family (>0.7) → species
   labels blend within the continuum = lossy discretisation.
3. Contrast with Run 010 polymorphs (0.91–1.0, labels natural).
Honest caveat: if species_acc is ALSO high (RRUFF endmembers spectrally distinct), the continuum
isn't exposed by endmember labels → the lossy claim would need intermediate-rich compositions /
measured chemistry (a different dataset). That outcome is itself informative.

### Result
Garnet (almandine 24 / pyrope 23 / spessartine 14 / grossular 42 / andradite 27; specimen-grouped
k-NN, 5 seeds):
- **family (pyralspite vs ugrandite) acc = 1.000**
- **species (5-way) acc = 0.728** (majority 0.323, shuffled 0.160)
- **within_family_error_frac = 1.000** — every species error stays within the true family
- family − species = 0.272.
Olivine (forsterite 25 / fayalite 9 / tephroite 9): species acc 0.938 (majority 0.581).

### Validated / invalidated
- ✅✅ #1 — family is a perfect natural coordinate (1.0).
- ✅✅ #2 — species labels are lossy: species 0.728 < family 1.0, and **100%** of species errors
  stay within-family (predicted >0.7). The species boundary is fuzzy on a continuum raw Raman
  represents continuously; the family boundary is crisp.
- ✅ #3 — contrast holds: solid-solution species (0.728, within-family blend) are measurably
  lossier than Run 010 polymorph labels (0.91–1.0, clean).
- Olivine: endmembers separate (0.938) — the predicted "endmember caveat": with only endmembers
  the continuum is not exposed. Garnet (with varied/intermediate compositions) is where it shows.

### Conclusion — the campaign's synthesis
The relationship between raw measurement and inherited label is now characterised:
- **Structure-determined labels** (polymorphs, Run 010): *natural coordinates* of raw Raman — raw
  recovers them where composition cannot.
- **Continuum-bin labels** (solid-solution species, Run 011): *lossy* — raw recovers the
  structural family perfectly (1.0) but treats species as fuzzy bins on a continuous axis
  (errors 100% within-family).
So inherited labels are natural coordinates when they track structure, and lossy projections when
they discretise a continuum; the raw representation recovers the underlying coordinate (structural
family + continuous within-family axis) the discrete label compresses. This is the direct,
evidence-backed answer to the project's core question.

### Caveat / not-yet-earned
Garnet "species" correlate with composition (Fe/Mg/Mn/Ca), so within-family confusion is
composition-adjacent — consistent with "species discretise a compositional continuum raw Raman
represents continuously." Still not shown: raw reps are MORE USEFUL than labels for a defined
downstream task with stakes (the strongest claim).

### Next
Closes a coherent arc. Options: (1) fold the RRUFF positive (009–011) into findings_summary.md as
the capstone complement to the oleogel negative; (2) the strongest-claim probe (raw rep more
useful than the label on a real downstream task); (3) controlled-collection.

---

## 2026-06-15 · Run 010 · RRUFF polymorph probe (raw vs constant composition)

Status: **DONE** — predictions below left unedited; result follows the prediction block.

### Why
Run 009 showed the mineral label ≈ composition for common minerals, so raw barely beat the
proxy. The thesis bites only where composition is **constant** — same-composition polymorphs,
where the label encodes structure that only the raw measurement can recover. Run 009's CaCO3
sub-probe was underpowered (n=14). This run powers it up: Processed spectra at **all
wavelengths**, several same-composition groups, specimen-grouped, averaged over seeds.

### Method
Groups (identical formula within each): CaCO3 (calcite/aragonite/vaterite), TiO2
(rutile/anatase/brookite), FeS2 (pyrite/marcasite), C (diamond/graphite), Al2SiO5
(kyanite/andalusite/sillimanite), SiO2 (quartz/cristobalite/tridymite/coesite/...). Per group,
keep polymorphs with ≥2 specimens; raw-spectrum k-NN (k=1), specimen-grouped split, top-1
accuracy averaged over 5 seeds. Baselines: **majority** (= the best a constant-composition
predictor can do) and **label-shuffled**.

### Prediction
1. In well-populated groups (CaCO3 cal/arag, TiO2 rut/ana, FeS2 py/marc, C dia/graph, SiO2),
   raw k-NN ≫ majority — e.g. raw > 0.9 vs majority ~0.5–0.75. Raman is highly structure-
   sensitive, so same-composition polymorphs separate cleanly.
2. shuffled ≈ majority (control).
→ This is the clean, adequately-powered demonstration that the inherited polymorph label carries
structural information **composition fundamentally cannot**, and the raw measurement recovers it
— on CaCO3 among others. Caveat: this confirms a known-chemistry premise of the thesis (raw >
constant-composition proxy); it is not yet the stronger claim (raw reps MORE useful than labels,
or labels are lossy). Those are the next probes (solid-solution continua; `##STATUS` ambiguity).

### Result (Processed, all wavelengths, 5786 spectra; specimen-grouped k-NN, 5 seeds)
| group | polymorphs (n) | raw | majority | shuffled |
| --- | --- | ---: | ---: | ---: |
| CaCO3 | calcite 26 / aragonite 9 | **0.975** | 0.743 | 0.621 |
| TiO2 | rutile 10 / anatase 8 / brookite 7 | **1.000** | 0.400 | 0.275 |
| Al2SiO5 | kyanite 5 / andalusite 11 / sillimanite 7 | **1.000** | 0.478 | 0.412 |
| SiO2 | quartz 21 / cristobalite 6 / tridymite 7 / stishovite 3 | **0.907** | 0.568 | 0.398 |
| C | diamond 30 / graphite 2 | 0.921 | 0.938 | 0.840 |
| FeS2, FeOOH | insufficient (1 marcasite / 2 lepidocrocite) | — | — | — |

raw beats majority in **4/5** scored groups.

### Validated / invalidated
- ✅ #1 — raw ≫ majority in every adequately-populated group (raw 0.91–1.0 vs majority
  0.40–0.74). CaCO3 (the target system): **0.975 vs 0.743**.
- The lone "loss" (C, 0.921 < 0.938) is a 2-graphite class-imbalance artifact
  (majority = predict-all-diamond), not a real failure.
- ✅ #2 — shuffled ≈ or below majority (control behaves).

### Conclusion — first clean, on-thesis positive (adequately powered)
Where composition is constant (same-composition polymorphs), the raw Raman spectrum recovers the
polymorph label near-perfectly (0.91–1.0) while the compositional proxy is stuck at majority
(0.40–0.74), across **4 independent chemical systems incl. CaCO3.** This crisply demonstrates the
thesis *premise*: inherited labels can encode structure the cheap proxy cannot, and the raw
measurement recovers exactly that. Combined with Run 009 (label ≈ composition, raw did not beat
the proxy), we now know **where** raw beats the proxy: labels that are *structure-determined*,
not *composition-determined*.

### Scope / not yet earned
A known-chemistry premise demonstrated rigorously — NOT the stronger claims: (a) raw reps MORE
useful than labels for downstream tasks; (b) labels are LOSSY (raw reveals structure labels
miss). Those are the next, more novel probes.

### Next (Run 011+)
The "labels are lossy" direction: (1) **solid-solution continua** (olivine forsterite–fayalite,
plagioclase) — does raw space show a continuum the discrete labels chop arbitrarily? (2)
**`##STATUS` ambiguity** — are "not yet confirmed" specimens outliers / mis-neighboured? (3)
within-label sub-clusters (polytypes / hydration). These test whether labels are lossy — the
genuinely novel claim.

---

## 2026-06-15 · Run 009 · RRUFF label-probe (representation vs inherited label, at scale)

Status: **DONE** — predictions below left unedited; result follows the prediction block.

### Why
The oleogel campaign (001–008) hit a 6-event ceiling and showed the limit is data, not model.
RRUFF gives thousands of curated Raman spectra across ~1,958 mineral labels (266 with ≥10
spectra), each with composition (`##IDEAL CHEMISTRY`) and an ambiguity flag (`##STATUS`) — and
includes the CaCO3 polymorphs (calcite 52, aragonite 18). First dataset large enough to test
the core thesis: are inherited labels natural coordinates of the raw measurement, and does a
raw representation carry label info beyond the compositional proxy? Capacity-free (kNN),
gap-over-controls, cross-specimen.

### Method
Excellent unoriented, Processed, 532 nm; resample to 150–1300 cm⁻¹ (600 pts), max-normalise.
Keep minerals with ≥5 spectra across ≥2 specimens. Split by **specimen** (GroupShuffleSplit) to
avoid leakage. k-NN (k=1) top-1 accuracy for: `raw_spectrum` (claim) · `composition`
(element one-hot — trivial-structure baseline) · `label-shuffled` and `chance` (null controls).
Sub-probe — CaCO3 polymorphs: calcite vs aragonite (identical composition), raw-spectrum binary
accuracy vs the majority/composition baseline.

### Prediction
1. raw kNN top-1 ≫ shuffled (~chance) — labels are largely natural coordinates of raw Raman
   (the at-scale positive we could not get at N=6). Expect raw top-1 > 0.7.
2. raw ≥ composition, composition much lower (many minerals share elements).
3. calcite vs aragonite: raw > 0.9, composition ≈ majority chance (~0.74) → raw carries
   structure/label info composition fundamentally cannot (the on-thesis polymorph case, CaCO3).
Caveat: Raman mineral-ID is known-easy, so #1 mainly validates scale/pipeline; the
thesis-advancing parts are #3 (polymorphs) and the later ambiguity (`##STATUS`) probe.

### Result
2910 Processed/532 nm spectra; after ≥5-spectra / ≥2-specimen filter → 450 spectra, 59 minerals.
Global (specimen-grouped k-NN top-1): **raw 0.879 · composition 0.843 · shuffled 0.021 · chance
0.038**. CaCO3 sub-probe: raw 0.833 but only n_test=6 (10 calcite + 4 aragonite in this subset).

### Validated / invalidated
- ✅ #1 — raw ≫ shuffled/chance (0.879 vs 0.021/0.038): mineral labels are largely natural
  coordinates of raw Raman, cross-specimen, at 59-class scale. The at-scale positive we could
  not get at N=6.
- ❌ #2 — INVALIDATED: composition is nearly as good (0.843). For common distinct-chemistry
  minerals the label ≈ composition, so raw barely beats the compositional proxy. (The strong
  baseline did its job again.)
- ⚠️ #3 — inconclusive: the polymorph sub-probe is underpowered (Processed/532 has only 10
  calcite + 4 aragonite; test=6; 0.833 = 5/6, not meaningful).

### Conclusion
At scale, raw Raman predicts the mineral label well — but so does composition, so the global
probe does **not** show raw beating the inherited proxy. The thesis bites only where composition
is *constant*: same-composition polymorphs / solid-solutions, where only structure (raw) can
separate the label. That is exactly the case Run 009 left underpowered.

### Next (Run 010)
**Polymorph / same-composition probe, powered.** Relax filters (all wavelengths + RAW&Processed)
to maximise n, and pool several constant-composition groups (CaCO3 calcite/aragonite/vaterite;
TiO2 rutile/anatase/brookite; FeS2 pyrite/marcasite; C diamond/graphite; Al2SiO5
kyanite/andalusite/sillimanite). Test: raw-spectrum separability within each constant-composition
group vs the composition (= chance) baseline — the clean "raw carries label info composition
cannot". Then the `##STATUS` ambiguity probe.

---

## 2026-06-15 · Run 008 · Smoothness-controlled dependence (fixes Run 007)

Status: **DONE** — predictions below left unedited; result follows the prediction block.

### Why
Run 007's permutation null was confounded by shared temporal smoothness. This run uses two
smoothness-preserving controls so any remaining dependence is genuine cross-modal *alignment*.

### Method
Per event, residualise SAXS and WAXS against the leave-one-event-out time-prior (as Run 007).
Then for each event:
- observed dCor(SAXS_resid, WAXS_resid).
- **circular-shift null**: roll WAXS_resid by random time offsets (preserves its
  autocorrelation exactly; breaks only cross-modal phase alignment); p = P(shifted dCov ≥ obs).
- **cross-event baseline**: dCor(SAXS_resid[E], WAXS_resid[other event, interpolated to E's
  grid]) — same smoothness, no shared event; report the median over other events.
Signal is real for an event only if observed dCor > circular-shift null (p<0.05) AND observed
clearly exceeds the cross-event baseline.

### Prediction
Given the Run 007 confound and the Run 006 model results, I expect the controlled signal to
**shrink from 6/6**: significant and above the cross-event baseline on a *subset* — most
likely the DMHR shear-25s/50s events (consistent with Run 006), not all six. If it survives
there, that is the clean, capacity-free confirmation that real cross-modal signal exists for
*some* conditions but the cross-event **transfer** is the limit (data), not model capacity.
If it vanishes on all events, the apparent signal was smoothness all along.

### Result — n_real_signal = **1/6**
obs_dcor vs cross_event_dcor: dmhr_1s .707/.716 · dmhr_25s .818/.840 · **dmhr_50s .889/.807
(+.082 ✓)** · mopv_1s .847/.842 · mopv_25s_redo .55/.705 · mopv_50s .931/.910. circular-shift
p = 0.005 everywhere (but see below).

### What the controls show
- **Within-event dCor (.7–.93) ≈ cross-event dCor (.7–.91):** SAXS_resid of event E predicts a
  *different* event's WAXS_resid about as well as event E's own → the high dCor is **shared
  smooth residual shape, not event-specific coupling.**
- The circular-shift null says "significant" everywhere, but that only shows SAXS and WAXS
  follow a *similar smooth shape* over the normalised interval — and that shape is shared
  across events, so it is not coupling. **The cross-event baseline is the decisive control**,
  and it removes essentially all the apparent signal. (Lesson: even the circular-shift null
  was not enough; the cross-event baseline was.)
- Only **dmhr_50s** shows a small genuine excess (+0.082).

### Validated / invalidated
- Predicted shrink-from-6/6 to a DMHR subset: directionally right but stronger — shrank to
  **1/6** (only dmhr_50s; dmhr_25s did NOT survive). I over-predicted the surviving signal.
- Run 007's "6/6 strong signal" was almost entirely the smoothness artifact — now excluded.

### Conclusion — the rigorous answer to "model or data?"
**NOT model capacity** (no tunable model was used). And **not "signal exists but won't
transfer"** (Run 007's read) — properly controlled, there is barely any event-specific
cross-modal signal: SAXS and WAXS are **largely time-redundant** on this system (both mostly
track the crystallisation clock). Only 1/6 events shows a whisper of genuine excess. This is
the "more-data-of-the-same-kind won't help" branch — the cross-modal signal we hoped for is
genuinely weak *here*, not hidden by a weak model.

### Scope (do not over-conclude)
This is for SAXS→WAXS on THIS homogeneous oleogel set. It does **not** say "raw data carries no
usable signal" in general. The thesis could still hold via (a) the polymorph/d-spacing
**label-probe**, or (b) a dataset where conditions/outcomes vary (so the clock is not
everything) and modalities are genuinely complementary. The binding issue here is dataset
homogeneity + modality redundancy, not model capacity.

### Wrong causes now excluded (Runs 001–008)
sparse-anchor (001) · data artifact (002) · memorisation (003/004) · time-prior (006) · model
capacity & smoothness artifact (007→008). **What stands:** oleogel SAXS/WAXS are largely
time-redundant; ~1 event shows a faint real excess.

### Next
Evidence points *away* from squeezing this dataset. Best moves: (1) **label-probe** on a
dataset with real labels; (2) a dataset with **diverse conditions/outcomes** (not 6 identical
protocols) and genuinely complementary modalities; (3) controlled-collection. Avoid: more
models on oleogel, more oleogel-like events.

---

## 2026-06-15 · Run 007 · Model-free dependence: SAXS↔WAXS beyond the clock

Status: **DONE (but invalidated by a confound — see fix → Run 008).**

### Why this run
Run 006 used trained models, so "no transferable signal" could *in principle* be a model-
capacity problem, not a data problem. This run removes the model entirely. A capacity-free
dependence measure (**distance correlation** + permutation test) asks: within each event, does
SAXS carry information about WAXS *beyond the shared time-course*? This cleanly separates "does
cross-modal signal EXIST" from "can a tuned model exploit/transfer it".

### Method (no tunable model)
- Per event, build a **model-free time-prior** (leave-one-event-out: average of the OTHER
  events' spectra interpolated onto this event's normalised times), for SAXS and WAXS.
- Residual = spectra − time-prior (this event's deviation from the population at each instant).
- **Distance correlation** dCor(SAXS_resid, WAXS_resid) within the event, with a 200-perm null
  (shuffle WAXS_resid in time). p = P(permuted dCor ≥ observed). Sanity: raw (un-residualised)
  dCor should be high (both ride the clock).

### Hypothesis + prediction
If "data/transfer limit, not model capacity" is right, cross-modal signal should EXIST beyond
the clock *within* events even though it didn't transfer in Run 006:
1. Raw dCor high & significant in all 6 events (sanity).
2. Residual dCor significant (p<0.05) in several events — clearly the two DMHR shear-25s/50s
   events, weaker/null for MOPV — mirroring Run 006.
→ Significant residual dCor ⇒ the signal EXISTS and the limit is data/transfer (6 events),
NOT model capacity. If residual dCor is null everywhere ⇒ the modalities are largely
time-redundant and the clock genuinely is the story (a more sobering, more-data-won't-help read).

### Result
Residual dCor high in **all 6 events** (0.55–0.93); raw dCor 0.88–0.95; permutation p = 0.005
(the 1/201 floor) everywhere → "6/6 significant".

### The catch — a wrong cause we must exclude
The time-shuffle permutation null is **too weak**. Both residual series are still *smooth in
time*, so each distance matrix is dominated by temporal proximity (near-in-time ⇒ similar).
Two *independent* smooth series would therefore also show high dCor and beat a shuffle null
that destroys autocorrelation. So this result conflates "SAXS↔WAXS coupling" with "both are
smooth in time" — it is **not trustworthy** as evidence of cross-modal signal, and the 6/6 is
likely the smoothness artifact (prediction #2's MOPV-weak guess is moot under the confound).

### Fix → Run 008
Use a smoothness-preserving control: (a) **circular time-shift null** (keeps each series'
autocorrelation, breaks only cross-modal phase alignment) and (b) a **cross-event baseline**
(SAXS_resid of event A vs WAXS_resid of a *different* event B — same smoothness, no shared
event). Real signal only if within-event dCor ≫ shifted / cross-event dCor.

---

## 2026-06-15 · Run 006 · Ablation: is the SAXS→WAXS win real cross-modal signal?

Status: **DONE** — predictions below left unedited; result follows the prediction block.

### Why this run
Run 005 beat the WAXS-mean on 3/6 folds. Before believing that is cross-modal signal, we
must exclude every cheaper explanation. One time-only baseline is not enough — run the full
ablation suite (cross-event leave-one-run-out, same data as Run 005).

### Models (each kills one alternative cause)
- `waxs_mean` — floor.
- `time_only` (input: normalised timestamp) — kills "it's just a clock".
- `time_sample` (timestamp + material one-hot) — kills "it's just the material's typical curve".
- `saxs_only` (SAXS-PCA(30)) — the Run 005 claim, reproduced.
- `saxs_time` (SAXS-PCA + timestamp) — tests whether SAXS adds info *beyond* the clock.
- `saxs_shuffled` (SAXS rows permuted in time within each event) — negative control; kills
  "the signal is in SAXS marginal stats, not the SAXS↔WAXS correspondence".
Both Ridge and MLP fit for each; MLP is the headline (more robust per Run 005).

### Exclusion logic (SAXS is real cross-modal only if ALL hold)
1. `saxs_time` < `time_only` (adds beyond the clock).
2. `saxs_only` < `time_sample` (beyond identifying the material).
3. `saxs_only` < `saxs_shuffled` (signal is in the correspondence).

### Hypothesis (+ logic) and prediction
The trajectories are smooth, so `time_only` will be a *strong* baseline, and material identity
explains a lot of between-event WAXS differences — so I expect **much of Run 005's win to be
the time/material prior**, with only a small, inconsistent genuine cross-modal contribution
across these 6 events. Concrete prediction:
1. `saxs_shuffled` ≈ `waxs_mean` (sanity: scrambling destroys the signal).
2. `time_only` already beats `waxs_mean` on most folds.
3. `saxs_time` beats `time_only` in only ~2–3/6 folds (small, inconsistent).
4. `saxs_only` does **not** consistently beat `time_sample`.
→ Net: the cross-modal signal is real but modest; Run 005's apparent win was largely the
time/material prior. (If instead `saxs_only` cleanly beats `time_sample` and `saxs_shuffled`
on most folds, that is a genuine positive worth chasing.)

### Result — median WAXS z-MSE over 6 folds (MLP)
waxs_mean 0.557 · **time_only 0.360** · time_sample 0.351 · saxs_only 0.984 · saxs_time 0.764
· saxs_shuffled 0.955. **The clock is the best predictor in the median; adding SAXS makes it
worse.** Exclusion checks (folds passing /6): saxs_time<time_only **3** · saxs_only<time_sample
**3** · saxs_only<saxs_shuffled **3** · time_only<mean **6** · saxs_shuffled≈mean **4**.

Per-fold (mean | time | time+samp | saxs | saxs+time | saxs_shuf):
- `dmhr_25s` 0.41 | 0.18 | 0.26 | **0.15** | 0.16 | 0.42 — SAXS wins, all 3 exclusions pass.
- `dmhr_50s` 0.55 | 0.35 | 0.14 | **0.11** | 0.10 | 0.34 — SAXS clearly wins, all 3 pass.
- `dmhr_1s` 0.67 | 0.52 | **0.40** | 1.00 | 0.79 | 0.75 — SAXS hurts; time/sample best.
- `mopv_1s` 0.56 | **0.37** | 0.87 | 1.17 | 1.22 | 1.16 — clock best; SAXS much worse.
- `mopv_50s` 0.28 | **0.08** | 0.30 | 0.97 | 0.73 | 1.19 — clock alone nails it; SAXS terrible.
- `mopv_25s_redo` ~8–11 everywhere — still inflated, uninterpretable.

### Validated / invalidated
- ✅ #1 saxs_shuffled ≈ mean (4/6) — negative control behaves.
- ✅✅ #2 time_only beats mean **6/6** — the time-prior is strong.
- ✅ #3 saxs_time beats time_only only **3/6** — inconsistent, as predicted.
- ✅ #4 saxs_only does not consistently beat time_sample (3/6).
- ✅ **Net prediction confirmed:** Run 005's "win" was largely the time/material prior; the
  genuine cross-modal signal is **narrow — only the two higher-shear DMHR folds** — does not
  transfer to MOPV, and on the median SAXS *hurts* vs the clock.

### Conclusion — we correctly excluded the wrong cause
The ablation did its job: Run 005's apparent cross-modal win shrinks to a narrow,
non-transferable real signal (clean on dmhr_25s/50s), while the **clock is the dominant
predictor**. Across 6 experiments that all follow a similar cool/shear crystallisation,
"fraction of process complete" predicts WAXS better than the actual SAXS does. Fourth time
the discipline prevented a false positive — this time by right-sizing one.

### Standing conclusion after 6 runs (evidence-backed, not a hunch)
This dataset — 6 *similar* experiments — is **too small and too homogeneous** to carry the
thesis. We have now rigorously shown: frame-prediction is time/interpolation-solvable; cross-
modal prediction is mostly the time-prior. Both point to the same need: **more, more-diverse
events.** This is the empirical case for controlled-collection / a richer dataset.

### Next
1. (Cheap confirm) Run 007: time-*residual* cross-modal — predict (WAXS − time_only) from
   SAXS, isolating "does SAXS explain what the clock cannot." Expect small / DMHR-only.
2. Move to a larger, more-diverse deposit (zeolite, zenodo 18972297) — check event count.
3. Treat the 6-event ceiling as a finding: the empirical argument for controlled-collection.

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
