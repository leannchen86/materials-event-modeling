# Ontology Stress Tests

These tests ask how inherited materials labels project onto a learned
measurement/event space. Labels are probes and diagnostics, not the main objective.

## Candidate Tests

1. Functional utility: do raw/event embeddings improve prediction, compression,
   retrieval, or active sampling?
2. Label compactness: after raw/event training, do labels occupy compact latent regions?
3. Label boundary ambiguity: do disputed labels sit near latent boundaries?
4. Label splitting: do broad labels break into multiple latent neighborhoods?
5. Label merging: do distinct labels overlap when raw measurements and process metadata
   are modeled together?
6. Intervention relevance: do learned embeddings predict the next measurement or useful
   process change better than label-only baselines?

## Baselines

- Composition-only descriptors.
- Classical XRD peak features.
- Human labels.
- Supervised phase-classifier embeddings.
- Self-supervised raw-pattern embeddings.

## Initial NIST Baseline

Generated with:

```bash
python3 scripts/preprocess_xrd.py nist_mds2_2301
python3 scripts/run_ontology_tests.py nist_mds2_2301
python3 scripts/run_xrd_reconstruction.py nist_mds2_2301
```

First-pass result on the 192 human-labeled NIST samples:

- 73 rows have non-unanimous human labels.
- Composition/temperature alone predicts human-label disagreement strongly:
  grouped-by-temperature ROC-AUC 0.850.
- XRD PCA alone also predicts disagreement, but more weakly:
  grouped-by-temperature ROC-AUC 0.808 for 10 PCA components.
- Composition/temperature plus XRD PCA improves grouped ROC-AUC to 0.877.
- Consensus-label compactness is negative in composition/temperature space
  (-0.046 silhouette), but positive in XRD PCA space (0.140 for 10 PCA
  components).

Interpretation: this first check does not support a simple "raw XRD beats metadata"
story. It suggests label ambiguity is heavily tied to where samples sit in the
composition-temperature grid, while raw diffraction structure adds some predictive
signal and gives a more label-compact representation. This is a useful guardrail for
the next experiment: control for composition/temperature before claiming ontology-level
structure in raw measurements.

## Why PCA Before UMAP/t-SNE

PCA is the first reconstruction baseline because it defines an explicit linear basis,
supports out-of-sample transforms, and can reconstruct masked signal with a least-squares
fit over the observed 2-theta points. This makes it useful for objective feedback tasks.

UMAP and t-SNE are mainly visualization/neighborhood tools. They are stochastic,
hyperparameter-sensitive, and can make clusters look sharper or stranger than the source
geometry warrants. t-SNE has no natural inverse transform, and UMAP's inverse transform is
approximate rather than a clean reconstruction model. They may be useful later for plots,
but they should not be the first judge of representation quality.

## Initial Masked-XRD Reconstruction

Generated with:

```bash
python3 scripts/run_xrd_reconstruction.py nist_mds2_2301 --mask-widths 64 256 512 --repeats 3 --pca-components 5 10 25
```

Task:

```text
visible XRD regions -> hidden contiguous XRD region
```

Best first-pass results by mask width, using random folds and similar held-out-temperature
performance:

| Mask width | Metadata ridge MSE improvement | Best PCA missing-data MSE improvement | Interpolation behavior |
| --- | ---: | ---: | --- |
| 64 | 23.1% | 55.3% | Helps modestly |
| 256 | 20.2% | 54.4% | Worse than train mean |
| 512 | 21.3% | 53.8% | Much worse than train mean |

Interpretation: this is the first result that is closer to the Bitter Lesson framing.
We are not asking whether the representation matches human labels. We are asking whether
a representation learned from raw measurement structure can predict missing measurement
signal. Even a simple PCA basis does substantially better than metadata-only prediction
and train-mean prediction.

This does not mean PCA is the final model. It gives the minimum bar for future
self-supervised encoders: they must beat PCA missing-data reconstruction on held-out
raw-signal prediction before their latent spaces deserve much interpretation.

## Initial Masked Autoencoder

Generated with:

```bash
python3 scripts/run_xrd_autoencoder.py nist_mds2_2301 --mask-width 256 --repeats 3 --epochs 120 --pca-components 5 --device auto --observed-loss-weight 0.05
```

Result:

| Split | Metadata ridge MSE improvement | PCA missing-data MSE improvement | Masked MLP autoencoder MSE improvement |
| --- | ---: | ---: | ---: |
| Random folds | 20.2% | 54.4% | 7.2% |
| Held-out temperature | 20.4% | 53.3% | 18.9% |

A same-data sanity check with longer training also barely improved over train-mean
prediction. So the correct lesson is not "neural methods are bad"; it is that this
small MLP is a poor imputer for 352 spectra. PCA remains the small-data baseline future
self-supervised models must beat.

## Initial opXRD Scaling Check

After downloading opXRD, the first full audit found 92,552 JSON diffraction patterns.
Most patterns are unlabeled after decoding the bundled phase metadata:

- 90,373 zero-phase/unlabeled patterns.
- 1,069 one-phase patterns.
- 1,108 two-phase patterns.
- 2 patterns with more than two decoded phases.

The archive is strongly contributor-skewed: LBNL and INT dominate. A pilot subset should
therefore not use the first files in archive order. The current preprocessing script uses a
deterministic spread across archive order by default, which produced a 4,096-spectrum,
4,096-point fixed-grid subset.

The first opXRD masked-reconstruction run used a 1,024-spectrum spread sample, random folds,
held-out-top-level-source folds, and mask widths of 256, 512, and 1,024 grid points.

Important first lesson: local interpolation is a very strong baseline on opXRD. For example,
with a 256-point mask it improves MSE by about 61% on random folds and 69% on held-out
top-level-source folds relative to the train mean. With a 1,024-point mask, it still improves
MSE by about 32% on random folds and 48% on held-out-source folds.

PCA did not behave like it did on NIST. A small PCA basis sometimes helped on random folds,
but larger PCA bases became unstable and could be much worse than the train mean, especially
for wide masks or held-out-source splits.

Interpretation: the opXRD objective needs a stricter baseline and probably a better masking
scheme. "Beat train mean" is too weak. A useful self-supervised raw-XRD encoder should beat
local interpolation, handle contributor/instrument shift, and avoid learning only smooth
background interpolation.

## Peak-Focused opXRD Masks

The next stress test added `peak` masks that hide windows centered on each spectrum's high
intensity points. This makes the task less like filling a smooth local background and more
like predicting missing peak structure.

Generated with:

```bash
python3 scripts/run_opxrd_reconstruction.py --max-samples 1024 --mask-widths 256 512 1024 --mask-strategies random peak --repeats 1 --pca-components 4 16 64
```

First result:

- Peak masks are harder than random masks: the train-mean error is much larger because the
  hidden regions contain real signal.
- Local interpolation remains surprisingly strong, especially under held-out-source splits.
- PCA can beat interpolation on random folds for some peak masks, especially 256-point
  peak masks, but it often collapses under held-out-source splits.
- Wide peak masks expose the objective better: for 1,024-point peak masks, interpolation
  gives only about 16% MSE improvement on random folds, while a 4-component PCA gives about
  24%; under held-out source, interpolation still wins.

Interpretation: the next neural encoder should be evaluated on peak-focused masks and
held-out-source splits. A model that only wins on random folds may be learning source- or
instrument-specific structure rather than a robust raw-XRD representation.

## Initial opXRD Convolutional Reconstructor

The first neural opXRD pilot trains a compact dilated 1D CNN on raw spectra only. Labels are
not used. The model receives the masked spectrum plus an observed/missing mask and predicts
the full spectrum, with loss concentrated on the hidden region.

Generated with:

```bash
python3 scripts/run_opxrd_conv_reconstruction.py --max-samples 512 --mask-width 1024 --train-mask-strategy peak --eval-mask-strategy peak --epochs 25 --batch-size 64 --channels 32 --depth 10 --n-splits 3 --split-kinds random_kfold held_out_top_level_source
```

Important implementation lesson: the first attempt used too small a receptive field for a
1,024-point hidden window. The committed run uses exponentially increasing dilations and an
approximate receptive field of 4,093 points, which can cover the whole mask.

First result:

| Split | Interpolation MSE improvement | CNN MSE improvement | Interpretation |
| --- | ---: | ---: | --- |
| Random folds | 11.2% | 34.6% | CNN clearly beats interpolation on MSE. |
| Held-out source | 29.4% | 33.0% | CNN barely but meaningfully beats interpolation on MSE. |

Caveat: the CNN has worse MAE than interpolation, so it may be improving squared-error-heavy
peak recovery while producing broader small errors. This is a promising pilot signal, not a
claim that the representation is already robust or ontologically meaningful.

Interpretation: this is the first neural result that points in the desired direction: a raw
measurement model can beat local interpolation on a peak-focused task under source shift.
The next scaling step should test whether this improves with more opXRD samples, longer
training, and eventually transfer back to NIST.

## opXRD CNN Replication Curve

The next check repeated the CNN over two sample sizes and two seeds:

```bash
python3 scripts/run_opxrd_conv_scaling.py --sample-sizes 256 512 --seeds 0 1 --epochs 25 --n-splits 3 --split-kinds random_kfold held_out_top_level_source --mask-width 1024 --train-mask-strategy peak --eval-mask-strategy peak --channels 32 --depth 10 --batch-size 64
```

Summary:

| Samples | Split | Interpolation MSE improvement | CNN MSE improvement | CNN MSE win rate vs interpolation |
| ---: | --- | ---: | ---: | ---: |
| 256 | Random folds | 9.9% | 8.6% | 50% |
| 256 | Held-out source | 32.0% | 8.4% | 0% |
| 512 | Random folds | 8.0% | 33.7% | 100% |
| 512 | Held-out source | 27.0% | 28.4% | 50% |

Interpretation: the CNN signal strengthens with more samples on random folds, but it is not
yet robust under source shift. At 512 samples, the held-out-source average MSE is slightly
better than interpolation, but only one of two seeds wins. MAE remains worse than
interpolation in every setting. This supports scaling the raw-XRD neural path, but it also
says the current local pilot is not strong enough for an ontology-level claim.

## Residual-Over-Interpolation CNN

The next experiment asks whether the CNN can learn what local interpolation misses. Instead
of predicting the hidden XRD window directly, the model predicts a correction:

```text
final prediction = linear interpolation + CNN residual
```

This makes interpolation the default answer and forces the neural model to add nonlocal peak
structure only where useful.

Generated with:

```bash
python3 scripts/run_opxrd_conv_scaling.py --sample-sizes 256 512 --seeds 0 1 --epochs 25 --n-splits 3 --split-kinds random_kfold held_out_top_level_source --mask-width 1024 --train-mask-strategy peak --eval-mask-strategy peak --prediction-mode residual --channels 32 --depth 10 --batch-size 64 --output data/manifests/opxrd_masked_xrd_conv_residual_scaling.json
```

Summary:

| Samples | Split | Interpolation MSE improvement | Residual CNN MSE improvement | Residual CNN MSE win rate | Residual CNN MAE win rate |
| ---: | --- | ---: | ---: | ---: | ---: |
| 256 | Random folds | 9.9% | 27.4% | 100% | 100% |
| 256 | Held-out source | 32.0% | 40.7% | 100% | 100% |
| 512 | Random folds | 8.0% | 30.3% | 100% | 100% |
| 512 | Held-out source | 27.0% | 33.8% | 100% | 50% |

Interpretation: residual learning is a much cleaner signal than direct CNN prediction. It
beats interpolation on MSE in every trial, including held-out-source splits, and usually
reduces the MAE penalty. This supports the thesis that there is learnable nonlocal XRD
structure beyond local smooth interpolation. It is still a small local curve, so the next
question is whether the residual signal strengthens at 1,024-4,096 spectra and transfers to
NIST.

## Zeus Residual Scaling Check

Hypotheses before the run:

- H1: residual CNNs should continue beating interpolation on MSE at larger sample sizes.
- H2: held-out-source behavior should become more stable as sample count increases.
- H3: MAE should mostly improve or at least stop degrading, because interpolation is the
  starting prediction and the model only learns a residual correction.

Generated on Zeus with:

```bash
CUDA_VISIBLE_DEVICES=4 .venv/bin/python scripts/run_opxrd_conv_scaling.py --sample-sizes 1024 2048 --seeds 0 1 --epochs 40 --n-splits 3 --split-kinds random_kfold held_out_top_level_source --mask-width 1024 --train-mask-strategy peak --eval-mask-strategy peak --prediction-mode residual --channels 32 --depth 10 --batch-size 64 --device cuda --output data/manifests/opxrd_masked_xrd_conv_residual_scaling_zeus.json
```

Summary:

| Samples | Split | Interpolation MSE improvement | Residual CNN MSE improvement | Residual CNN MSE win rate | Residual CNN MAE win rate |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1,024 | Random folds | 11.7% | 39.7% | 100% | 100% |
| 1,024 | Held-out source | 31.4% | 41.4% | 100% | 100% |
| 2,048 | Random folds | 13.4% | 56.1% | 100% | 100% |
| 2,048 | Held-out source | 32.8% | 41.2% | 100% | 50% |

Verdict:

- H1 validated. The residual CNN beats interpolation on MSE in every trial at both larger
  sample sizes and both split types.
- H2 partially validated. Held-out-source MSE is stable and consistently positive, but it
  does not noticeably improve from 1,024 to 2,048 spectra. Scale helps random folds much
  more than source-shift transfer.
- H3 partially validated. MAE improves on random folds and at 1,024 held-out-source, but
  remains mixed at 2,048 held-out-source.

Interpretation: this is stronger evidence that the model learns nonlocal peak structure
beyond interpolation. It is not yet evidence that the learned representation has escaped
source or contributor bias. The next useful stress test should target transfer: either a
larger held-out-source sweep, source-balanced sampling, or pretrain-on-opXRD then evaluate
on NIST without making phase labels the training objective.

## A100 4,096-Spectrum Residual Check

Hypothesis before the run:

- Random-fold MSE should improve beyond the 2,048-spectrum result if sample scale is still
  helping in-distribution reconstruction.
- Held-out-source MSE may plateau near the earlier 41% improvement if source shift is the
  current bottleneck.
- MAE should continue winning on random folds, but may remain fragile under held-out-source
  evaluation.

Generated on Zeus A100 with:

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/run_opxrd_conv_scaling.py --sample-sizes 4096 --seeds 0 1 --epochs 40 --n-splits 3 --split-kinds random_kfold held_out_top_level_source --mask-width 1024 --train-mask-strategy peak --eval-mask-strategy peak --prediction-mode residual --channels 32 --depth 10 --batch-size 64 --device cuda --output data/manifests/opxrd_masked_xrd_conv_residual_scaling_4096_a100.json
```

Summary:

| Samples | Split | Interpolation MSE improvement | Residual CNN MSE improvement | Residual CNN MSE win rate | Residual CNN MAE win rate |
| ---: | --- | ---: | ---: | ---: | ---: |
| 4,096 | Random folds | 14.3% | 71.2% | 100% | 100% |
| 4,096 | Held-out source | 32.4% | 41.5% | 100% | 100% |

Verdict:

- The random-scale hypothesis is validated strongly. Random-fold residual reconstruction
  improves monotonically from 512 to 4,096 spectra.
- The source-shift plateau hypothesis is also validated. Held-out-source MSE remains
  positive but essentially flat from 1,024 to 4,096 spectra.
- The MAE hypothesis is better than expected at 4,096: the residual model beats
  interpolation on MAE for both held-out-source seeds.

Interpretation: the current model has passed the "beat interpolation on peak-masked raw XRD"
test. The next bottleneck is no longer generic neural capacity on opXRD; it is transfer
across sources, contributors, instruments, and experimental styles. The next experiment
should ask whether source-balanced sampling or leave-one-source-out pretraining improves
held-out-source performance more than simply adding more spectra.
