# Public-Data Run Index

Status: frozen calibration archive. The full contemporaneous preregistrations, predictions, and
results are preserved at Git commit `88940273da6918a11bb49e65ca0dc41d22eda024`; this index keeps
only the conclusions that still constrain the active program. Canonical magnitudes belong to the
[results ledger](../spine/results_ledger.json), and current interpretation belongs to the
[findings summary](findings_summary.md).

| run | question | bounded outcome |
| ---: | --- | --- |
| 015 | Does an early Severson trajectory reveal more than cycle life? | Early summaries predicted lifetime within corpus (LOO Spearman **0.61**), but policy confounding and failed held-batch transfer prevent a transferable-loss claim. |
| 014 | Does the RRUFF coarse/fine-label pattern recur in powder XRD? | On deposited processed XRD, garnet species accuracy was **0.66** versus family accuracy **1.0**; low sample counts and provenance limit interpretation. |
| 013 | Are RRUFF Raman results carried only by broad spectral shape? | High-pass spectra retained much of the classification signal. This is a representation ablation, not proof that the signal is causal or downstream-useful. |
| 012 | Do wavelength, blur, class difficulty, or metric choice explain the Raman result? | Most controls survived; the first blur control was inconclusive and motivated Run 013. |
| 011 | Are coarse and fine garnet labels equally recoverable? | On deposited processed Raman, species accuracy was **0.73**, family accuracy **1.0**, and within-family error fraction **1.0**. This supports structured label-granularity differences, not a continuous or true ontology. |
| 010 | Can Raman distinguish same-composition polymorph labels? | It did in several selected groups, showing measurement information beyond a constant-composition proxy; it did not compare against label utility on a downstream task. |
| 009 | Does Raman add much beyond formula for common mineral labels? | Only a small within-corpus gain appeared, motivating narrower structural controls. |
| 008 | Is SAXS–WAXS dependence larger than smoothness-preserving nulls? | Little excess dependence remained in six similar oleogel events. |
| 007 | Is there model-free SAXS–WAXS dependence beyond time? | An initial positive was weakened by an inadequate null and superseded by Run 008. |
| 006 | Does SAXS improve WAXS prediction beyond clock/interpolation controls? | The apparent gain largely disappeared under stronger controls. |
| 005 | Can SAXS predict missing WAXS across events? | Limited cross-event signal; time and smoothness were strong explanations. |
| 004 | Does masked WAXS reconstruction transfer across events? | Leave-one-event-out performance exposed the weakness hidden by within-event tests. |
| 003 | Did area normalization remove the oleogel amplitude shortcut? | It removed one shortcut but did not establish transferable scientific signal. |
| 002 | Does a fair interpolation baseline explain masked reconstruction? | Much of the task was interpolation-solvable. |
| 001 | Can the model overfit one event? | Yes; this verified mechanics only and supplied no scientific evidence. |

## Lessons retained

1. Deposited `Processed` spectra and standardized exports are not instrument-native evidence.
2. Label recoverability is not label loss, decision value, or ontology recovery.
3. Within-corpus gains require held-environment tests and cheap clock, interpolation, context, and
   provenance baselines.
4. An audit cannot detect a channel omitted before every compared arm.
5. Public-data model sweeps are closed; the next evidence gate is prospective partner collection.
