"""Run 014: cross-modality generalisation — does the RRUFF label taxonomy hold on powder XRD?

Replicates the two load-bearing probes on RRUFF XRD (same minerals/labels as the Raman runs,
different physical measurement): the solid-solution lossy test (garnet species vs family) and
the polymorph test (CaCO3, low power), plus a distinct-5 difficulty reference. If the lossy
pattern (family >> species, within-family errors) reproduces, the taxonomy is modality-general.
See docs/event-method/run_log.md (Run 014).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.neighbors import KNeighborsClassifier

from materials_event_modeling.data.rruff import load

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "data/raw/rruff/xrd_XY_Processed.zip"
SEEDS = list(range(8))

GARNET = {"Almandine": "pyralspite", "Pyrope": "pyralspite", "Spessartine": "pyralspite",
          "Grossular": "ugrandite", "Andradite": "ugrandite"}
DISTINCT5 = ["Diamond", "Beryl", "Muscovite", "Epidote", "Calcite"]


def grouped_eval(X, y, g, test_size=0.35):
    accs, bals = [], []
    for s in SEEDS:
        tr, te = next(GroupShuffleSplit(1, test_size=test_size, random_state=s).split(X, y, g))
        if len(np.unique(y[tr])) < 2:
            continue
        pred = KNeighborsClassifier(n_neighbors=1).fit(X[tr], y[tr]).predict(X[te])
        accs.append(float((pred == y[te]).mean()))
        bals.append(float(balanced_accuracy_score(y[te], pred)))
    if not accs:
        return None
    return {"acc": round(float(np.mean(accs)), 3), "std": round(float(np.std(accs)), 3),
            "bal_acc": round(float(np.mean(bals)), 3), "n": len(y)}


def subset(data, members):
    present = [m for m in members
               if (data.mineral == m).any() and np.unique(data.rruffid[data.mineral == m]).size >= 2]
    mask = np.isin(data.mineral, present)
    return data.X[mask], data.mineral[mask], data.rruffid[mask], present


def within_family_err(X, y, g):
    within, total = 0, 0
    for s in SEEDS:
        tr, te = next(GroupShuffleSplit(1, test_size=0.35, random_state=s).split(X, y, g))
        if len(np.unique(y[tr])) < 2:
            continue
        pred = KNeighborsClassifier(n_neighbors=1).fit(X[tr], y[tr]).predict(X[te])
        err = pred != y[te]
        total += int(err.sum())
        within += int(sum(GARNET[p] == GARNET[t] for p, t in zip(pred[err], y[te][err], strict=False)))
    return round(within / total, 3) if total else None


def run(args):
    data = load(args.zip, gmin=5.0, gmax=70.0, n_grid=1300, wavelength="any", filetype="XY_Processed")

    # garnet species vs family (the key generalisation test)
    Xg, yg, gg, present = subset(data, list(GARNET))
    fam = np.array([GARNET[m] for m in yg])
    garnet = {
        "counts": {m: int(np.sum(yg == m)) for m in present},
        "species_5way": grouped_eval(Xg, yg, gg),
        "family_2way": grouped_eval(Xg, fam, gg),
        "within_family_error_frac": within_family_err(Xg, yg, gg),
    }

    # CaCO3 polymorph (low power)
    Xc, yc, gc, cpres = subset(data, ["Calcite", "Aragonite"])
    caco3 = (grouped_eval(Xc, yc, gc, test_size=0.4) | {"counts": {m: int(np.sum(yc == m)) for m in cpres},
             "majority": round(float(max(np.mean(yc == m) for m in cpres)), 3)}) if len(cpres) >= 2 else "insufficient"

    # distinct-5 difficulty reference
    Xd, yd, gd, dpres = subset(data, DISTINCT5)
    distinct5 = grouped_eval(Xd, yd, gd) | {"minerals": dpres}

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "rruff_xrd_generalization",
        "modality": "powder_xray_diffraction",
        "n_spectra_total": int(data.X.shape[0]),
        "garnet": garnet,
        "caco3_polymorph": caco3,
        "distinct5": distinct5,
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    return result


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--output", type=Path, default=Path("data/manifests/rruff_xrd_generalization.json"))
    return p.parse_args()


def main():
    print(json.dumps(run(parse_args()), indent=2))


if __name__ == "__main__":
    main()
