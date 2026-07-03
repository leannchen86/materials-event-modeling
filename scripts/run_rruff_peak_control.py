"""Run 013: RRUFF peaks-only vs heavy-blur control — closes Run 012 B.

Splits each spectrum into its sharp-peak part (the real Raman fingerprint) and its broad-shape
part (possible baseline/provenance), then classifies on each. If peaks_only ~= full and
heavy_blur collapses, the signal lives in the fingerprint and the provenance/broad-feature worry
is excluded. See docs/event-method/run_log.md (Run 013).
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
SEEDS = list(range(8))

POLY = {"CaCO3": ["Calcite", "Aragonite"], "TiO2": ["Rutile", "Anatase", "Brookite"]}
GARNET = {"Almandine": "pyralspite", "Pyrope": "pyralspite", "Spessartine": "pyralspite",
          "Grossular": "ugrandite", "Andradite": "ugrandite"}
DISTINCT5 = ["Diamond", "Calcite", "Beryl", "Muscovite", "Epidote"]


def gauss(X, sigma):
    t = np.arange(-3 * sigma, 3 * sigma + 1)
    k = np.exp(-(t ** 2) / (2 * sigma ** 2))
    k /= k.sum()
    return np.stack([np.convolve(r, k, mode="same") for r in X]).astype(np.float32)


def renorm(X):
    m = np.max(np.abs(X), axis=1, keepdims=True)
    m[m == 0] = 1.0
    return (X / m).astype(np.float32)


def grouped_acc(X, y, g):
    accs = []
    for s in SEEDS:
        tr, te = next(GroupShuffleSplit(1, test_size=0.35, random_state=s).split(X, y, g))
        if len(np.unique(y[tr])) < 2:
            continue
        pred = KNeighborsClassifier(n_neighbors=1).fit(X[tr], y[tr]).predict(X[te])
        accs.append(float((pred == y[te]).mean()))
    return round(float(np.mean(accs)), 3) if accs else None


def run(args):
    data = load(args.zip, wavelength="any", filetype="Processed")
    reps = {
        "full": data.X,
        "peaks_only": renorm(data.X - gauss(data.X, args.hp_sigma)),
        "heavy_blur": renorm(gauss(data.X, args.heavy_sigma)),
    }

    def eval_case(members, family=False):
        present = [m for m in members
                   if (data.mineral == m).any() and np.unique(data.rruffid[data.mineral == m]).size >= 2]
        mask = np.isin(data.mineral, present)
        y = np.array([GARNET[m] for m in data.mineral[mask]]) if family else data.mineral[mask]
        out = {rep: grouped_acc(RX[mask], y, data.rruffid[mask]) for rep, RX in reps.items()}
        out["majority"] = round(float(max(np.mean(y == c) for c in np.unique(y))), 3)
        out["n"] = int(mask.sum())
        return out

    results = {
        "garnet_species": eval_case(list(GARNET)),
        "garnet_family": eval_case(list(GARNET), family=True),
        "CaCO3": eval_case(POLY["CaCO3"]),
        "TiO2": eval_case(POLY["TiO2"]),
        "distinct5": eval_case(DISTINCT5),
    }
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "rruff_peak_control",
        "hp_sigma": args.hp_sigma,
        "heavy_sigma": args.heavy_sigma,
        "cases": results,
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    return result


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--hp-sigma", type=int, default=15)
    p.add_argument("--heavy-sigma", type=int, default=100)
    p.add_argument("--output", type=Path, default=Path("data/manifests/rruff_peak_control.json"))
    return p.parse_args()


def main():
    print(json.dumps(run(parse_args()), indent=2))


if __name__ == "__main__":
    main()
