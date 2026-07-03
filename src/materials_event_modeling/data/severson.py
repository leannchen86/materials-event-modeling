"""Load Severson battery cells from a MATLAB v7.3 (HDF5) batch file.

Each cell = a degradation trajectory (per-cycle summary scalars) + the inherited cycle_life
label (cycles to 80% capacity). See docs/event-method/severson_battery_audit.md.
"""

from __future__ import annotations

import h5py
import numpy as np


def load_cells(path):
    f = h5py.File(path, "r")
    b = f["batch"]
    n = b["cycle_life"].shape[0]
    cells = []
    for i in range(n):
        try:
            cl = float(np.array(f[b["cycle_life"][i, 0]]).ravel()[0])
            s = f[b["summary"][i, 0]]
            qd = np.array(s["QDischarge"]).ravel().astype(float)
            ir = np.nan_to_num(np.array(s["IR"]).ravel().astype(float))
            ct = np.nan_to_num(np.array(s["chargetime"]).ravel().astype(float))
            try:
                pol = "".join(chr(int(c)) for c in np.array(f[b["policy"][i, 0]]).ravel() if 0 < int(c) < 128)
            except Exception:
                pol = "?"
            if qd.size < 50:
                continue
            cells.append({"cycle_life": cl, "qd": qd, "ir": ir, "chargetime": ct, "policy": pol})
        except Exception:
            continue
    return cells


def _seg(a, n):
    a = np.nan_to_num(a[1 : n + 1])
    if a.size == n:
        return a
    return np.interp(np.linspace(0, 1, n), np.linspace(0, 1, a.size), a)


def early_features(cell, n=100):
    """First-n-cycle trajectory of discharge capacity, internal resistance, charge time."""
    return np.concatenate([_seg(cell["qd"], n), _seg(cell["ir"], n), _seg(cell["chargetime"], n)]).astype(np.float32)


def life_shape(cell, m=100):
    """Discharge capacity vs fraction-of-life (lifetime normalised out → the aging shape)."""
    qd = cell["qd"]
    qd = qd[qd > 0.1] if (qd > 0.1).any() else qd[1:]
    s = np.interp(np.linspace(0, 1, m), np.linspace(0, 1, qd.size), qd)
    return (s / s[0]).astype(np.float32)
