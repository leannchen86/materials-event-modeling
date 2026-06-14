# MPS Event-Provenance Data Path

## Why This Matters

HTEM is a useful bridge, but it leaves a major pushback open:

```text
Your current result is a spatial interpolation result, not a material-making event result.
```

The Materials Provenance Store (MPS) is a better public-data target for the next phase
because it was designed around experimental provenance: raw materials, synthesis,
processes, samples, and downstream characterization.

## Source Check

The Scientific Data paper describes MPS as a database from high-throughput materials
experiments that manages metadata and experimental provenance "from acquisition of raw
materials, through synthesis, to a broad range of materials characterization techniques."

The paper also reports:

- over 30 million experiments,
- over 12 million samples,
- sample histories modeled through process/sample relationships,
- process types including print, anneal, optical imaging, electrochemistry, XRD, SSRL,
  XRF, and UV-vis,
- a 4.5 GB compressed PostgreSQL database dump,
- roughly 1.1 TB of compressed raw and analyzed data in separate DOI packages.

The public CaltechDATA dataset page confirms the downloadable MPS release is a 4.5 GB
PostgreSQL dump.

Sources:

- `https://www.nature.com/articles/s41597-023-02107-0`
- `https://data.caltech.edu/records/4kk39-69x76`
- `https://github.com/modelyst/mps-client`

## Why We Did Not Immediately Benchmark It

This is not a small CSV/API benchmark.

Local check:

```text
pg_restore: unavailable
psql: unavailable
docker: available
```

The practical path is to restore the database in a Docker Postgres container, query a
focused subset, then optionally fetch raw/analyzed data packages by DOI.

We should avoid downloading the full 1.1 TB raw/analyzed data universe. The right first
step is a metadata/provenance query that identifies a small event-like subset with useful
process sequence and characterization coverage.

## Proposed First MPS Experiment

Goal:

```text
move from spatial event fields to process-provenance event histories
```

Minimum query target:

- samples with `print -> anneal -> xrds` process histories,
- ideally also `xrfs` and/or `uvis`,
- repeated characterization or multiple downstream measurements,
- raw/analyzed data DOI pointers available,
- enough samples in a related chemistry family to avoid pure chemistry-family confounds.

Event representation:

```text
sample provenance sequence + process metadata + partial characterization
-> missing/future characterization
```

Candidate objectives:

- `prefix -> future`: given print/anneal/process metadata plus early characterization,
  predict later XRD/XRF/UV-vis.
- `missing modality`: given process sequence plus XRF/UV-vis, predict XRD embedding.
- `provenance shortcut stress`: compare process-only, source/provenance-only,
  characterization-only, and full event inputs.
- `label-as-probe`: only after the representation is trained, inspect whether existing
  material labels or analysis tags align with, split, or blur in latent space.

## What Would Count As A Stronger Result

Weak result:

```text
process metadata predicts a curated label
```

That falls back into label/ontology optimization.

Better result:

```text
partial process + raw/analyzed measurement history predicts held-out measurements better
than material-row, provenance-only, and nearest-neighbor baselines
```

Best public-data result:

```text
early event history predicts a later measurement or missing modality in a way that
survives held-out chemistry family, held-out campaign/operator/provenance, and strong
nearest-neighbor controls
```

## Why This Mitigates The HTEM Pushbacks

HTEM pushback:

```text
This is just spatial interpolation.
```

MPS response:

```text
The prediction axis becomes process history or measurement sequence, not only x-y spatial
position.
```

HTEM pushback:

```text
This is not a true material-making event.
```

MPS response:

```text
MPS explicitly tracks sample/process provenance across synthesis and characterization.
```

HTEM pushback:

```text
You only have final characterization fields.
```

MPS response:

```text
The event can include print, anneal, characterization sequence, and links to raw/analyzed
data packages.
```

## Next Engineering Step

Create a Docker-based MPS restore workflow only when we are ready to spend the download
and disk budget:

```text
download 4.5 GB PostgreSQL dump
restore into local Postgres container
run schema inventory
query focused process-history subsets
export a compact event table into this repo
```

The immediate offline work should stay on HTEM hard controls and outreach framing unless
we deliberately decide to allocate disk/time for the MPS restore.
