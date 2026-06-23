"""Deduplication: exact (normalized hash) and near-duplicate (MinHash + LSH).

A from-scratch MinHash-LSH mirroring the datatrove/Dolma approach: word-shingle a
document, build a MinHash signature, band the signature into LSH buckets, then union
documents that share a bucket and exceed an estimated-Jaccard threshold. Keeps one
representative per duplicate cluster.

``docs`` are ``[(doc_id, text), ...]``. Returns kept ids, removed ids, and cluster info.
"""

from __future__ import annotations

import hashlib
import re
import zlib
from typing import Any

import numpy as np

_WORD = re.compile(r"\w+")
_PRIME = (1 << 61) - 1  # Mersenne prime; base shingle hashes are 32-bit so a*x stays < 2**64


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def exact_dedup(docs: list[tuple[str, str]]) -> dict[str, Any]:
    """Remove documents with identical normalized text (keep first seen)."""
    seen: dict[str, str] = {}
    kept, removed = [], []
    for doc_id, text in docs:
        digest = hashlib.sha1(_normalize(text).encode()).hexdigest()
        if digest in seen:
            removed.append({"doc_id": doc_id, "duplicate_of": seen[digest]})
        else:
            seen[digest] = doc_id
            kept.append(doc_id)
    return {"kept_ids": kept, "removed": removed, "removed_count": len(removed)}


def _shingles(text: str, k: int) -> np.ndarray:
    toks = _WORD.findall(text.lower())
    if len(toks) < k:
        joined = [" ".join(toks)] if toks else []
    else:
        joined = [" ".join(toks[i : i + k]) for i in range(len(toks) - k + 1)]
    if not joined:
        return np.empty(0, dtype=np.uint64)
    return np.array([zlib.crc32(s.encode()) for s in joined], dtype=np.uint64)


def _signature(shingles: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if shingles.size == 0:
        return np.full(a.size, _PRIME, dtype=np.uint64)
    # (a[:,None]*shingle + b[:,None]) % P, min over shingles. 32-bit base * <2**31 a -> <2**63.
    hashed = (np.outer(a, shingles) + b[:, None]) % _PRIME
    return hashed.min(axis=1)


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        self.parent[self.find(x)] = self.find(y)


def minhash_dedup(
    docs: list[tuple[str, str]],
    *,
    num_perm: int = 64,
    bands: int = 16,
    shingle_k: int = 5,
    threshold: float = 0.7,
    seed: int = 17,
) -> dict[str, Any]:
    """Cluster near-duplicates via MinHash-LSH; keep one representative per cluster.

    ``bands`` must divide ``num_perm``; rows-per-band = num_perm // bands sets the LSH
    sensitivity (~ (1/bands)**(1/rows) Jaccard). ``threshold`` is the final signature-
    agreement cut applied to LSH candidate pairs.
    """
    if num_perm % bands != 0:
        raise ValueError("num_perm must be divisible by bands")
    rows = num_perm // bands
    rng = np.random.default_rng(seed)
    a = rng.integers(1, 1 << 31, size=num_perm, dtype=np.uint64)
    b = rng.integers(0, 1 << 31, size=num_perm, dtype=np.uint64)

    signatures = np.stack([_signature(_shingles(t, shingle_k), a, b) for _, t in docs])
    n = len(docs)

    # LSH: bucket by each band; only docs sharing a band bucket are candidate pairs.
    uf = _UnionFind(n)
    for band in range(bands):
        buckets: dict[tuple, list[int]] = {}
        chunk = signatures[:, band * rows : (band + 1) * rows]
        for i in range(n):
            buckets.setdefault(tuple(chunk[i].tolist()), []).append(i)
        for members in buckets.values():
            for j in members[1:]:
                # confirm with full-signature agreement (MinHash Jaccard estimate)
                if np.mean(signatures[members[0]] == signatures[j]) >= threshold:
                    uf.union(members[0], j)

    clusters: dict[int, list[int]] = {}
    for i in range(n):
        clusters.setdefault(uf.find(i), []).append(i)

    kept, removed, dup_clusters = [], [], []
    for members in clusters.values():
        rep = members[0]
        kept.append(docs[rep][0])
        if len(members) > 1:
            dup_clusters.append([docs[m][0] for m in members])
            for m in members[1:]:
                removed.append({"doc_id": docs[m][0], "duplicate_of": docs[rep][0]})

    return {
        "kept_ids": kept,
        "removed": removed,
        "removed_count": len(removed),
        "duplicate_clusters": dup_clusters,
        "params": {"num_perm": num_perm, "bands": bands, "rows": rows,
                   "shingle_k": shingle_k, "threshold": threshold},
    }
