# The Adapter Is an Inclusion Policy

Status: current lesson from the Severson downstream audit, revised 2026-07-12. The full original
narrative is preserved at Git commit `eb21481acd7b3065d775fd8fd1b5f6b428441c27`.

## Correction in terms

An adapter is not the acquisition capture policy: it cannot recover opportunities never taken or
artifacts never produced. It is a post-acquisition inclusion and representation policy that can
make retained evidence invisible to every later arm.

Use two roots:

```text
capture audit:         opportunity/action ledger -> native artifacts and failures
representation audit: earliest retained artifact -> adapter -> features -> report
```

The first tests selective acquisition. The second tests loss among evidence that exists. Starting
at the adapter output tests neither edge above it.

## Severson case

The native HDF5 files contain within-cycle `Qdlin`/`Vdlin` curves used by the published ΔQ(V)
feature. The event adapter retained per-cycle scalars and archive pointers but omitted those arrays
from its JSON payload. The later S100-versus-X100 audit compared only descendants of that adapted
record, so it could not test the known within-cycle signal.

This omission was documented and reversible, but not priced at design freeze. Given nearly flat
early per-cycle capacity and a known signal above the root, the near-tie was partly foreseeable.
The run remains a valid nonconfirmatory engineering test of the edge it actually represented; it
is not evidence that the omitted channel lacks value.

## Rules

1. Inventory opportunities, acquisition actions, failures, native artifacts, and adapter omissions
   separately.
2. Put every tested transformation in the representation DAG. If parentage is unverified, report
   complementarity rather than localizing loss to an edge.
3. Before outcomes open, state what result each omission could preordain and the experiment that
   would test it.
4. Retain large evidence by pointer, content hash, and reader recipe instead of inlining it or
   dropping it silently.
5. Treat schema fit as an expressibility check, never a completeness certificate.

## Consequences

- The queued known-loss control reconstructs ΔQ(V) from the native archives and tests the
  within-cycle-to-per-cycle edge with the same downstream audit.
- Prospective partner collection needs an opportunity/action inventory above the current v1 bundle.
- A later schema may add first-class sidecar arrays, but v1 remains hash-bound and is not mutated.

The governing design note is
[capture_vs_representation_design_note.md](capture_vs_representation_design_note.md); the operational
gate is the [partner collection pipeline](../controlled-collection/partner_collection_pipeline.md).
