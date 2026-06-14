# Capture vs Representation: Design Note

Context: extends [project_brief.md](project_brief.md), [universal_event_embedding_scaffold.md](universal_event_embedding_scaffold.md),
and [track_b_masked_event_model.md](track_b_masked_event_model.md). Working frame unchanged:
pre-taxonomic event modeling — inherited labels are compression layers, not ground truth.

This note records a thread on two questions that kept getting conflated: how we *capture*
trajectories, and what *substrate* we learn on. Plus the near-term a/b decision.

## Two kinds of lossy (the distinction that unblocks the rest)

"Lossy" hides two different failures:

1. **Fidelity loss** — resolution, frame rate, modality coverage. You lose *signal*.
2. **Ontology loss** — collapsing a continuous process into human-named categories. You
   lose signal *and* pre-decide meaning.

Inherited labels (`gel point`, `phase pure`, `failure`) are heavy on *both*. Raw modalities
(video, a spectrum stream, process logs) are heavy on fidelity loss but ~zero on ontology
loss — they impose no interpretation.

Consequence: on the axis this project cares about (the ontology trap), raw capture beats
labels even though it is still "lossy." Video *feeling* lossy is correct, but it is the
*acceptable* kind. Rule of thumb: do not reject a raw modality for being lossy; reject a
representation for being *prematurely interpretive*.

## On capture modality (is video the right record?)

Video is cheap and low-ontology, so it is a good *stream*. Two cautions:

- **Wrong as the sole modality.** A camera sees the optical surface / a 2D projection. The
  governing variable in CaCO3 polymorph selection (local supersaturation, ionic
  environment, a transient amorphous precursor) can be invisible to it. The fix is not
  "better video," it is *multimodal hedging* — video + in-situ structural/chemical probe +
  process logs — because we do not yet know which modality carries the causal signal. This
  is already the schema's multimodal + missing-modality-prediction design.
- **Wrong as a learning substrate if used naively.** Raw pixels spend model capacity on
  perceptually salient but causally irrelevant detail.

So: video is one stream feeding a learned latent, not THE record.

## On representation substrate (the encoder/decoder intuition)

The instinct — store a rich latent the net can use, not a human-interpretable ontology — is
right, and is what the masked event model already is. Family of the right tools:
autoencoders / VAEs / masked autoencoders are *learned lossy compressors optimized for
reconstruction, not for human readability*. Neural compression beats hand-designed codecs in
other domains — evidence the principle generalizes.

**Upgrade worth testing — JEPA (joint-embedding predictive):** predict the *latent* of the
masked part instead of reconstructing the raw signal. Why it matters here specifically:

- Reconstruction objectives reward recovering smooth/predictable raw structure — which is
  exactly why current masked-event results stay partly solvable by coordinate interpolation
  (IDW), e.g. `random_axis`. Predicting in latent space does not reward spatial smoothness
  the same way, so it may be a route *out* of the "geometry already solves it" trap.
- JEPA on time-series has been shown (under near-identity-predictor conditions) to recover
  dynamical-regime structure / Koopman-invariant clustering *without labels* — i.e. discover
  events/regimes without imposing an ontology. That is the pre-taxonomic goal stated in
  model terms.
- Risk: representation collapse (the known JEPA failure). Needs the usual guards
  (target/stop-gradient encoder, variance-covariance terms). Treat as a hypothesis under the
  same strong-baseline + stop-rule discipline as the reconstruction objective.

## The two caveats that keep us honest

1. **You cannot remove choice, only move it.** Dropping the human ontology moves the lossy
   decision into the *objective + architecture + which modalities you feed*. The loss
   function becomes the new ontology (reconstruction keeps what is salient; JEPA keeps what
   is predictable). The goal is a *late, learned, swappable* ontology — not none.
2. **Some interpretation is required for intervention.** Confirming a *driving factor* (not
   just a correlate) needs interventional experiments — and you can only dial a variable in
   the lab if you can name/actuate it. A pure uninterpretable latent dimension cannot be set
   on a syringe pump. So keep the substrate latent, but maintain a *decode-to-actionable-view
   on demand* bridge. Interpret late and disposably; never store the interpretation as the
   substrate. (Consistent with "labels after raw frozen.")

## Near-term decision (a vs b)

- **a:** run the falsifying objective on existing *real trajectory* data (multiple
  feedback-bearing observations per event), not more final-snapshot public XRD.
- **b:** stand up controlled collection (Track B / lab pilot / Foundry).

**Recommendation: refined-a first, b in parallel.** Pure public-snapshot data is already
known to be a feasibility/artifact tool with strong source effects, not a thesis test
([project_brief.md](project_brief.md)). The honest fast test needs event-structured real
data where interpolation/geometry cannot shortcut it — time-resolved / operando synthesis
series (in-situ XRD/SAXS during crystallization; HTEM within-library spatial fields). If
such open data with enough per-event richness exists → run masked-event + a JEPA variant
there now. If it does not exist → that absence *is* the argument for b being the moat. So a's
outcome sets b's urgency.

## Stop rules (unchanged, restated)

- No transformer race. Neural counts as progress only when it beats event-mean / IDW /
  coordinate-ridge / RF on held-out provenance splits.
- Validation is downstream-operational (missing-measurement error, retrieval, transfer,
  active-measurement utility), never "did we recover the human label."
