"""Run 011: RRUFF labels-are-lossy probe — are solid-solution *species* labels lossy bins on a
continuum that raw Raman blends, while the structural *family* is a natural coordinate?

Garnet has two solid-solution sub-families (pyralspite: almandine/pyrope/spessartine; ugrandite:
grossular/andradite). If species labels are lossy, specimen-grouped k-NN should separate the
families but blend the species within a family (species errors stay within-family). Olivine is a
secondary single-family confusion check. See run_log.md (Run 011).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from sklearn.neighbors import KNeighborsClassifier

from materials_event_modeling.data.rruff import load

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "data/raw/rruff/excellent_unoriented.zip"

GARNET_FAMILY = {
    "Almandine": "pyralspite", "Pyrope": "pyralspite", "Spessartine": "pyralspite",
    "Grossular": "ugrandite", "Andradite": "ugrandite",
}


def split(X, y, groups, seed, test_size=0.35):
    tr, te = next(GroupShuffleSplit(1, test_size=test_size, random_state=seed).split(X, y, groups))
    return tr, te


def knn_acc(X, ylabel, groups, seeds):
    accs = []
    for s in seeds:
        tr, te = split(X, ylabel, groups, s)
        if len(np.unique(ylabel[tr])) < 2:
            continue
        pred = KNeighborsClassifier(n_neighbors=1).fit(X[tr], ylabel[tr]).predict(X[te])
        accs.append(float((pred == ylabel[te]).mean()))
    return float(np.mean(accs)) if accs else None


def run(args):
    rng = np.random.default_rng(0)
    seeds = list(range(args.seeds))
    data = load(args.zip, wavelength="any", filetype="Processed")
    X, y, groups = data.X, data.mineral, data.rruffid

    # ---- Garnet: species (5-way) vs family (2-way) ----
    gmask = np.isin(y, list(GARNET_FAMILY))
    keep = [m for m in GARNET_FAMILY if np.unique(groups[y == m]).size >= 2]
    gmask &= np.isin(y, keep)
    Xg, yg, gg = X[gmask], y[gmask], groups[gmask]
    fam = np.array([GARNET_FAMILY[m] for m in yg])

    species_acc = knn_acc(Xg, yg, gg, seeds)
    family_acc = knn_acc(Xg, fam, gg, seeds)
    shuffled_species = knn_acc(Xg, rng.permutation(yg), gg, seeds)
    maj_species = float(max(np.mean(yg == m) for m in keep))
    maj_family = float(max(np.mean(fam == f) for f in np.unique(fam)))

    # fraction of species errors that stay WITHIN the true family
    within, total_err = 0, 0
    for s in seeds:
        tr, te = split(Xg, yg, gg, s)
        if len(np.unique(yg[tr])) < 2:
            continue
        pred = KNeighborsClassifier(n_neighbors=1).fit(Xg[tr], yg[tr]).predict(Xg[te])
        err = pred != yg[te]
        total_err += int(err.sum())
        within += int(sum(GARNET_FAMILY[p] == GARNET_FAMILY[t] for p, t in zip(pred[err], yg[te][err])))
    within_family_err_frac = round(within / total_err, 3) if total_err else None

    # ---- Olivine (single family) secondary ----
    olv = ["Forsterite", "Fayalite", "Tephroite"]
    okeep = [m for m in olv if np.unique(groups[y == m]).size >= 2]
    omask = np.isin(y, okeep)
    olivine_acc = knn_acc(X[omask], y[omask], groups[omask], seeds)
    olivine_maj = float(max(np.mean(y[omask] == m) for m in okeep)) if okeep else None

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "rruff_lossy_probe",
        "seeds": args.seeds,
        "garnet": {
            "species_kept": keep,
            "counts": {m: int(np.sum(yg == m)) for m in keep},
            "species_acc_5way": round(species_acc, 3) if species_acc else None,
            "family_acc_2way": round(family_acc, 3) if family_acc else None,
            "majority_species": round(maj_species, 3),
            "majority_family": round(maj_family, 3),
            "shuffled_species": round(shuffled_species, 3) if shuffled_species else None,
            "within_family_error_frac": within_family_err_frac,
            "family_minus_species": round((family_acc or 0) - (species_acc or 0), 3),
        },
        "olivine": {
            "species_kept": okeep,
            "counts": {m: int(np.sum(y[omask] == m)) for m in okeep},
            "species_acc_3way": round(olivine_acc, 3) if olivine_acc else None,
            "majority": round(olivine_maj, 3) if olivine_maj else None,
        },
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    return result


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--seeds", type=int, default=5)
    p.add_argument("--output", type=Path, default=Path("data/manifests/rruff_lossy_probe.json"))
    return p.parse_args()


def main():
    print(json.dumps(run(parse_args()), indent=2))


if __name__ == "__main__":
    main()
