"""Run 009: RRUFF label-probe — does a raw-spectrum representation predict the inherited
mineral label, cross-specimen, beyond the compositional proxy?

Capacity-free (k-NN), gap-over-controls, specimen-grouped split. Plus the CaCO3 polymorph
sub-probe (calcite vs aragonite: identical composition). See docs/event-method/run_log.md (009).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from sklearn.neighbors import KNeighborsClassifier

from materials_event_modeling.data.rruff import element_matrix, load

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "data/raw/rruff/excellent_unoriented.zip"


def knn_grouped_acc(X, y, groups, *, seed, k=1, test_size=0.3):
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    tr, te = next(splitter.split(X, y, groups))
    clf = KNeighborsClassifier(n_neighbors=min(k, len(tr))).fit(X[tr], y[tr])
    return float((clf.predict(X[te]) == y[te]).mean()), len(te)


def run(args):
    rng = np.random.default_rng(args.seed)
    data = load(args.zip)
    X, y, groups = data.X, data.mineral, data.rruffid
    comp, vocab = element_matrix(data.elements)

    # keep minerals with >= min_spectra across >= 2 specimens
    keep_minerals = [
        m for m in np.unique(y)
        if (np.sum(y == m) >= args.min_spectra and np.unique(groups[y == m]).size >= 2)
    ]
    mask = np.isin(y, keep_minerals)
    Xm, ym, gm, compm = X[mask], y[mask], groups[mask], comp[mask]
    n_classes = len(keep_minerals)

    raw_acc, n_test = knn_grouped_acc(Xm, ym, gm, seed=args.seed)
    comp_acc, _ = knn_grouped_acc(compm, ym, gm, seed=args.seed)
    y_shuf = rng.permutation(ym)
    shuf_acc, _ = knn_grouped_acc(Xm, y_shuf, gm, seed=args.seed)
    # chance = predict the most frequent class
    vals, counts = np.unique(ym, return_counts=True)
    chance = float(counts.max() / counts.sum())

    # ---- CaCO3 polymorph sub-probe: calcite vs aragonite (same composition) ----
    poly_mask = np.isin(y, ["Calcite", "Aragonite"])
    Xp, yp, gp = X[poly_mask], y[poly_mask], groups[poly_mask]
    poly_raw_acc, poly_n = knn_grouped_acc(Xp, yp, gp, seed=args.seed, test_size=0.4)
    poly_majority = float(np.mean(yp == "Calcite"))  # composition can't separate -> majority

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "rruff_label_probe",
        "n_spectra_total": int(X.shape[0]),
        "n_spectra_used": int(mask.sum()),
        "n_classes_used": n_classes,
        "min_spectra": args.min_spectra,
        "n_elements_vocab": len(vocab),
        "global_probe": {
            "raw_spectrum_top1": round(raw_acc, 3),
            "composition_top1": round(comp_acc, 3),
            "label_shuffled_top1": round(shuf_acc, 3),
            "chance_majority": round(chance, 4),
            "n_test": n_test,
        },
        "caco3_polymorph_subprobe": {
            "calcite_vs_aragonite_raw_top1": round(poly_raw_acc, 3),
            "composition_majority_baseline": round(max(poly_majority, 1 - poly_majority), 3),
            "n_test": poly_n,
            "n_calcite": int(np.sum(yp == "Calcite")),
            "n_aragonite": int(np.sum(yp == "Aragonite")),
        },
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    return result


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--min-spectra", type=int, default=5)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--output", type=Path, default=Path("data/manifests/rruff_label_probe.json"))
    return p.parse_args()


def main():
    print(json.dumps(run(parse_args()), indent=2))


if __name__ == "__main__":
    main()
