"""Run 012: RRUFF robustness ablations for the Runs 009-011 interpretation.

A. provenance — single wavelength (532 only): polymorph + garnet probes must survive.
B. provenance — structure-blind: classify a heavily-blurred spectrum (peaks removed); should
   collapse if the signal is in real Raman peaks (not broad/baseline artifacts).
C. multi-class difficulty control: 5 distinct-structure minerals vs garnet 5-way species.
D. error bars + balanced accuracy across the key numbers (incl. Run 009 raw vs composition).
See docs/event-method/run_log.md (Run 012).
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

from materials_event_modeling.data.rruff import element_matrix, load

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "data/raw/rruff/excellent_unoriented.zip"
SEEDS = list(range(8))

POLY = {"CaCO3": ["Calcite", "Aragonite"], "TiO2": ["Rutile", "Anatase", "Brookite"],
        "Al2SiO5": ["Kyanite", "Andalusite", "Sillimanite"],
        "SiO2": ["Quartz", "Cristobalite", "Tridymite", "Stishovite"]}
GARNET = {"Almandine": "pyralspite", "Pyrope": "pyralspite", "Spessartine": "pyralspite",
          "Grossular": "ugrandite", "Andradite": "ugrandite"}
DISTINCT5 = ["Diamond", "Calcite", "Beryl", "Muscovite", "Epidote"]


def grouped_eval(X, y, groups, test_size=0.35):
    accs, bals = [], []
    for s in SEEDS:
        tr, te = next(GroupShuffleSplit(1, test_size=test_size, random_state=s).split(X, y, groups))
        if len(np.unique(y[tr])) < 2:
            continue
        pred = KNeighborsClassifier(n_neighbors=1).fit(X[tr], y[tr]).predict(X[te])
        accs.append(float((pred == y[te]).mean()))
        bals.append(float(balanced_accuracy_score(y[te], pred)))
    if not accs:
        return None
    return {"acc": round(float(np.mean(accs)), 3), "acc_std": round(float(np.std(accs)), 3),
            "balanced_acc": round(float(np.mean(bals)), 3), "n": len(y)}


def members_present(data, members, min_spec=2):
    return [m for m in members
            if (data.mineral == m).any() and np.unique(data.rruffid[data.mineral == m]).size >= min_spec]


def subset(data, members):
    present = members_present(data, members)
    mask = np.isin(data.mineral, present)
    return data.X[mask], data.mineral[mask], data.rruffid[mask], present


def blur(X, sigma=25):
    t = np.arange(-3 * sigma, 3 * sigma + 1)
    k = np.exp(-(t ** 2) / (2 * sigma ** 2))
    k /= k.sum()
    return np.stack([np.convolve(row, k, mode="same") for row in X]).astype(np.float32)


def garnet_probe(data):
    X, y, g, present = subset(data, list(GARNET))
    fam = np.array([GARNET[m] for m in y])
    return {"species": grouped_eval(X, y, g), "family": grouped_eval(X, fam, g),
            "counts": {m: int(np.sum(y == m)) for m in present}}


def run(args):
    full = load(args.zip, wavelength="any", filetype="Processed")
    w532 = load(args.zip, wavelength="532", filetype="Processed")

    # A. single-wavelength survival
    poly_532 = {}
    for f, members in POLY.items():
        X, y, g, present = subset(w532, members)
        poly_532[f] = (grouped_eval(X, y, g) | {"polymorphs": present}) if len(present) >= 2 else "insufficient"
    A = {"polymorph_532only": poly_532, "garnet_532only": garnet_probe(w532)}

    # B. structure-blind (blurred) control
    def full_vs_blur(members):
        X, y, g, _ = subset(full, members)
        return {"full": grouped_eval(X, y, g), "blurred": grouped_eval(blur(X), y, g)}
    B = {"garnet_species": full_vs_blur(list(GARNET)), "CaCO3": full_vs_blur(POLY["CaCO3"]),
         "TiO2": full_vs_blur(POLY["TiO2"])}

    # C. multi-class difficulty control (5 distinct-structure minerals) vs garnet species
    Xd, yd, gd, dpresent = subset(full, DISTINCT5)
    Xg, yg, gg, _ = subset(full, list(GARNET))
    C = {"distinct5": grouped_eval(Xd, yd, gd) | {"minerals": dpresent},
         "garnet_species5": grouped_eval(Xg, yg, gg)}

    # D. error bars + balanced accuracy: polymorphs, garnet, run009 raw vs composition
    poly_full = {}
    for f, members in POLY.items():
        X, y, g, present = subset(full, members)
        poly_full[f] = grouped_eval(X, y, g) if len(present) >= 2 else "insufficient"
    keep = [m for m in np.unique(full.mineral)
            if np.sum(full.mineral == m) >= 5 and np.unique(full.rruffid[full.mineral == m]).size >= 2]
    mask = np.isin(full.mineral, keep)
    comp, _ = element_matrix([full.elements[i] for i in np.where(mask)[0]])
    D = {
        "polymorphs": poly_full,
        "garnet": garnet_probe(full),
        "run009_raw": grouped_eval(full.X[mask], full.mineral[mask], full.rruffid[mask]),
        "run009_composition": grouped_eval(comp, full.mineral[mask], full.rruffid[mask]),
        "run009_n_classes": len(keep),
    }

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "rruff_ablations",
        "seeds": len(SEEDS),
        "A_single_wavelength": A,
        "B_structure_blind": B,
        "C_difficulty_control": C,
        "D_error_bars": D,
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    return result


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--output", type=Path, default=Path("data/manifests/rruff_ablations.json"))
    return p.parse_args()


def main():
    print(json.dumps(run(parse_args()), indent=2))


if __name__ == "__main__":
    main()
