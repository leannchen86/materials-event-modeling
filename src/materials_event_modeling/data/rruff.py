"""Ingest RRUFF Raman spectra (zipped .txt) into labeled feature matrices for the label-probe.

Each RRUFF file has ``##KEY=value`` header lines (NAMES, RRUFFID, IDEAL CHEMISTRY, STATUS,
RAMAN WAVELENGTH) followed by ``wavenumber, intensity`` rows. We keep Processed spectra at one
laser wavelength, resample onto a common grid, and expose mineral label + specimen id +
composition (element-presence) + status, so the probe can test raw-spectrum vs label and
vs the compositional proxy. See docs/event-method/run_log.md (Run 009).
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass

import numpy as np

ELEMENT_RE = re.compile(r"[A-Z][a-z]?")


@dataclass
class RRUFFData:
    X: np.ndarray            # (n, n_grid) spectra on a common grid, max-normalised
    grid: np.ndarray         # (n_grid,)
    mineral: np.ndarray      # (n,) label
    rruffid: np.ndarray      # (n,) specimen id (use as group to avoid leakage)
    status: np.ndarray       # (n,) ##STATUS text
    chemistry: np.ndarray    # (n,) ##IDEAL CHEMISTRY text
    elements: list           # (n,) frozenset of element symbols


def _parse(text: str):
    meta, xs, ys = {}, [], []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("##"):
            if "=" in line:
                k, v = line[2:].split("=", 1)
                meta[k.strip()] = v.strip()
        elif line and "," in line:
            parts = line.split(",")
            try:
                xs.append(float(parts[0]))
                ys.append(float(parts[1]))
            except (ValueError, IndexError):
                pass
    return meta, np.asarray(xs), np.asarray(ys)


def load(zip_path, *, gmin=150.0, gmax=1300.0, n_grid=600, wavelength="532",
         filetype="Processed") -> RRUFFData:
    grid = np.linspace(gmin, gmax, n_grid).astype(np.float32)
    X, mineral, rid, status, chem, elems = [], [], [], [], [], []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            base = name.split("/")[-1]
            if not base.endswith(".txt"):
                continue
            if filetype not in (None, "any") and filetype not in base:
                continue
            if wavelength not in (None, "any") and f"__{wavelength}__" not in base:
                continue
            meta, xs, ys = _parse(zf.read(name).decode("latin-1"))
            if xs.size < 20 or not meta.get("NAMES"):
                continue
            order = np.argsort(xs)
            spec = np.interp(grid, xs[order], ys[order], left=0.0, right=0.0)
            mx = float(np.max(np.abs(spec)))
            if mx <= 0:
                continue
            X.append((spec / mx).astype(np.float32))
            mineral.append(meta["NAMES"])
            rid.append(meta.get("RRUFFID", "?"))
            status.append(meta.get("STATUS", ""))
            ch = meta.get("IDEAL CHEMISTRY", "")
            chem.append(ch)
            elems.append(frozenset(ELEMENT_RE.findall(ch)))
    return RRUFFData(
        X=np.asarray(X, dtype=np.float32),
        grid=grid,
        mineral=np.asarray(mineral),
        rruffid=np.asarray(rid),
        status=np.asarray(status),
        chemistry=np.asarray(chem),
        elements=elems,
    )


def element_matrix(elements: list) -> tuple[np.ndarray, list]:
    """One-hot element-presence matrix (the compositional proxy baseline)."""
    vocab = sorted({e for s in elements for e in s})
    index = {e: i for i, e in enumerate(vocab)}
    M = np.zeros((len(elements), len(vocab)), dtype=np.float32)
    for i, s in enumerate(elements):
        for e in s:
            M[i, index[e]] = 1.0
    return M, vocab
