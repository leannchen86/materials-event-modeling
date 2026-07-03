# Event-Grammar Validation Ladder and Claim Altitude

As of 2026-07-03. Records the lessons and decisions from the 2026-07-02 working discussion on
universal experiment protocols, UMA, and how to prove the event grammar is worth building.
Related: [capture_vs_representation_design_note.md](capture_vs_representation_design_note.md),
[event_native_public_data_strategy.md](event_native_public_data_strategy.md),
[../controlled-collection/universal_event_embedding_scaffold.md](../controlled-collection/universal_event_embedding_scaffold.md),
[../provenance-critique/provenance_leakage_audit.md](../provenance-critique/provenance_leakage_audit.md).

## Lessons Learned

1. **Universality follows protocol; it does not precede it.** UMA-class universal models exist
   because simulation data is born protocol-complete: uniform inputs, logged trajectories,
   failures retained, one shared coordinate system. Experimental synthesis has no equivalent
   substrate, which is why there is no "UMA for synthesis." The highest-leverage move in that
   white space is making experimental data assemblable, not training another model. Cheap
   simulation also shifts the bottleneck toward the un-simulated part: whether a material
   actually synthesizes, by what route, and why attempts fail.

2. **Standardize the envelope, never the payload.** Standards that won (CIF, CloudEvents, FHIR)
   fixed a small outer structure and left domain payloads namespaced. The universal core of an
   experiment is the event grammar — intent, trajectory, outcome (with failed/ambiguous/aborted
   as first-class), provenance axes, labels frozen only after raw — while XRD/rheology/video
   payloads stay domain-specific. Standards that tried to fix instrument semantics top-down
   (Allotrope, SiLA) stalled.

3. **A protocol is schema + conformance test + audit, not a schema alone.** Graded conformance
   levels give labs a gradient instead of a cliff:
   - Level 0: raw payloads, timestamps, event boundaries.
   - Level 1: + provenance axes logged (operator, instrument, session, lot, run order).
   - Level 2: + failures/ambiguous outcomes retained; labels frozen after raw.
   - Level 3: + counterbalanced design (replicate-level, per the pilot stress tests).
   Formats earn legitimacy when the audits they enable catch real problems (checkCIF precedent).

4. **A grammar cannot be proven true; it can only beat a null.** The null hypothesis: paper-shaped
   data (recipe + final measurement + label) is sufficient for every task anyone cares about.
   Each grammar slot is a falsifiable claim against that null. A slot that never changes a
   prediction or a decision on any system is dead weight and gets cut.

5. **The cleanest single experiment is a representation A/B test.** Take one already-rich dataset
   and make two versions: (A) event-grammar-preserved, (B) its paper-shaped projection. Same
   model, pre-registered tasks, provenance-stressed splits. This isolates the grammar's
   contribution in a way an emergence result never can.

6. **Emergence is the endgame confirmation, not the entry proof.** It is confounded with scale and
   architecture, and it is slow. DFT's data conventions were settled by decades of practice; UMA
   harvested them later. The bar for legitimacy is decision relevance (rungs 1-3 below). Leading
   indicator to watch for: the first positive transfer between just two systems that share
   nothing except the grammar.

7. **Groundbreaking is a property of the claim, not the method.** Validation methods are almost
   always incremental; that is what makes them believable (CASP before AlphaFold, ImageNet,
   OC20). The risk to manage is not incrementalism but scatter.

8. **Compounding-vs-scattered test.** For every experiment: if the top claim eventually lands,
   does this experiment appear in its proof? Yes means it is a compounding rung. No means it is a
   scattered increment (for example, a fourth public-dataset audit) and should not run.

9. **Solo-researcher calibration.** Do not select for projects that are groundbreaking at every
   step; that selects for high-variance bets a solo researcher cannot fund. The winning shape is
   cheap, compounding, independently legible rungs beneath one audacious top claim.

## The Validation Ladder

Cheapest first. Each rung names what falsifies it.

1. **Coverage.** Can the grammar express real experiments across material classes without losing
   information someone later needs? Test: adapter study over 5-6 public datasets. Falsified by
   experiments that cannot be encoded, or mappings that destroy needed information. Necessary
   but weak: proves expressiveness, not value.
2. **New questions answerable.** The grammar lets you ask what paper-shaped data structurally
   cannot: "is this failure operator-correlated?", "does performance survive a session-held-out
   split?" Test: run the provenance-leakage audit and readiness checks across all adapted
   datasets; publish the conformance table. Falsified if the enabled audits never catch a real
   problem.
3. **Slot ablations / representation A/B.** The controlled experiment from lesson 5, run per
   slot: drop trajectory, drop provenance, drop failures, drop intent. Falsified per-slot when
   removing the slot never hurts any pre-registered task. This is the scientific core.
4. **Cross-system transfer.** Pool event-grammar data from several systems; test whether a model
   trained on systems A+B beats a from-scratch model on system C, or shows shared structure.
   The emergence-flavored test; run it last, and only after rungs 1-3 supply the substrate.

## Candidate Top Claims

Choose explicitly; do not drift. All three are reachable from the same rungs 1-3.

1. **Failed experiments have quantifiable value.** First public demonstration, with numbers, of
   how much search space a failure eliminates. Changes the field's incentive to record
   negatives. Blocked on failure data existing (collection or partnership).
2. **Cross-process transfer exists in experimental materials.** A model trained on making gels
   helps predict making crystals — two systems sharing only the grammar. Nobody has shown this.
3. **Inherited labels are the wrong coordinates, shown on real data.** A learned event
   representation reorganizes a system better than its labels: labels split into regimes with
   different process behavior, and the split predicts something labels cannot. Run 011 (RRUFF,
   on `origin/provenance-leakage-audit`) is the first small real-data instance.

Current lean: aim near-term at claim 3 (real-data evidence already exists; cheapest), keep
claim 2 as the rung-4 stretch. Finalize the choice in a committed decision memo after the
adapter study, stating what evidence would reverse it.

## Run Discipline v2

Extends operating-memo pivot 6 (every run needs a hypothesis and a verdict). Checklist per
experiment:

1. **Hypothesis first, committed first.** State the hypothesis, expected outcome, what would
   validate/weaken/falsify it, and which decision the result changes. Commit this BEFORE the
   run, in a separate commit, so pre-registration is verifiable from git history.
2. **Name the null.** Every experiment states the null it attacks (default here: paper-shaped
   data suffices).
3. **Verdict against hypothesis.** After the run: validated/weakened/falsified, caveats, how the
   belief evolves, and a critique of why the proposed next direction is right.
4. **No early conclusions — exhaust ablations.** Enumerate plausible confounds before running;
   execute the ablation grid (parallelize with subagents where possible); write the verdict only
   after the grid completes. A headline claim with an unrun ablation is a hypothesis, not a
   result.
5. **Strongest cheap baseline.** Compare against the best non-learned baseline for the task
   (interpolation, nearest-neighbor retrieval, metadata-only, event/library mean, masked PCA).
   Beating train-mean or a straw baseline is not a result.
6. **Uncertainty floor.** At least 3 seeds for any verdict; report mean and spread; a difference
   within seed noise is a tie. Claims adjacent to a threshold need repeated cross-validation.
7. **Leakage hygiene.** Every fitted transform (PCA, scalers, feature selection) goes inside the
   CV fold. Always report a provenance-stressed split (source/session/operator-held-out)
   alongside random splits.
8. **Run identity.** Every manifest records git commit, argv, seeds, and environment; result docs
   cite manifest paths inline.
9. **Findings first.** Result docs open with a findings block of at most 10 lines (claim, key
   numbers, verdict, caveat); the chronological run log goes below it. Negative results get the
   same prominence.
10. **Ladder placement.** Every experiment names its rung and the top claim it serves. If it
    serves none, it is scatter — do not run it.

## Next Steps

Phase 0 — reconcile the record (blocks everything; about one session):

- Merge or archive-with-verdict `origin/provenance-leakage-audit` (47 commits ahead) and
  `origin/docs-reorg-by-project` (44 ahead); record in PROJECTS.md what Runs 001-015 showed.
  Run 011 is standing evidence for claim 3 and must be visible from main.
- Fix the audit tool before any external use: move PCA inside the CV folds, drop `is_labeled`
  from the metadata features, add a per-feature ablation, re-run and re-report.
- Add run-identity capture (git commit, argv, seeds) to the manifest writer before new runs.

Phase 1 — grammar v1 + adapter-coverage study (rungs 1-2; one to two weeks):

- Freeze grammar v1 against `schemas/material_event.schema.json`: envelope fields plus
  namespaced domain packs; encode conformance levels L0-L3 in the audit tool.
- Write adapters for 5-6 datasets: Durham droplets, Dryad gelation, OpenCrystalData, HTEM,
  Severson battery, oleogel WAXS (branch). Parallelize adapter writing and auditing with
  subagents, one dataset each.
- Deliverable: conformance table + coverage report; every mapping failure documented as a
  finding. This is a publishable artifact on its own (Scientific Data / Digital Discovery tier).

Phase 2 — representation A/B + slot ablations (rung 3; two to three weeks):

- Pick the one or two richest adapted datasets (likely Dryad gelation and Severson).
- Pre-register hypothesis, null, tasks, splits, and baselines per Run Discipline v2; commit
  before running.
- Run the A/B (grammar-preserved vs paper-shaped projection, same model) plus the per-slot
  ablation grid, fanned out across subagents; at least 3 seeds; strongest cheap baselines.
- Write the verdict findings-first.

Phase 3 — claim decision and stretch (after Phase 2):

- Commit the decision memo choosing the top claim (current lean: claim 3, claim 2 as stretch).
- If claim 3: scale the Run 011 pattern to two or three systems. If claim 2: run the
  two-system transfer probe on the adapted datasets.

Parallel track — the non-coding critical path from existing milestones; do not let it slip:

- Run the low-equipment droplet pilot. It doubles as the first dataset born at Level 3
  conformance and feeds rungs 3-4 directly.
- Send the three already-drafted outreach messages.
