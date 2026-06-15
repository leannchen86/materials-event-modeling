"""Run 010: RRUFF polymorph probe — does the raw spectrum separate same-composition polymorphs
that the compositional proxy fundamentally cannot?

Per same-composition group (identical formula), specimen-grouped k-NN classification of the
polymorph label from the raw spectrum, vs the majority baseline (the best a constant-composition
predictor can do) and a shuffled control. Averaged over seeds. See run_log.md (Run 010).
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

GROUPS = {
    "CaCO3": ["Calcite", "Aragonite", "Vaterite"],
    "TiO2": ["Rutile", "Anatase", "Brookite"],
    "FeS2": ["Pyrite", "Marcasite"],
    "C": ["Diamond", "Graphite"],
    "Al2SiO5": ["Kyanite", "Andalusite", "Sillimanite"],
    "SiO2": ["Quartz", "Cristobalite", "Tridymite", "Coesite", "Stishovite", "Moganite"],
    "FeOOH": ["Goethite", "Lepidocrocite", "Akaganeite"],
}


def grouped_acc(X, y, groups, seed, test_size=0.4):
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    tr, te = next(splitter.split(X, y, groups))
    if len(np.unique(y[tr])) < 2:
        return None
    clf = KNeighborsClassifier(n_neighbors=1).fit(X[tr], y[tr])
    return float((clf.predict(X[te]) == y[te]).mean())


def run(args):
    rng = np.random.default_rng(0)
    data = load(args.zip, wavelength="any", filetype="Processed")
    X, y, groups = data.X, data.mineral, data.rruffid

    results = []
    for formula, members in GROUPS.items():
        mask = np.isin(y, members)
        Xg, yg, gg = X[mask], y[mask], groups[mask]
        # keep polymorphs with >= 2 specimens (needed for a grouped split)
        present = [m for m in members
                   if np.sum(yg == m) > 0 and np.unique(gg[yg == m]).size >= 2]
        if len(present) < 2:
            results.append({"formula": formula, "status": "insufficient",
                            "counts": {m: int(np.sum(yg == m)) for m in members if np.sum(yg == m) > 0}})
            continue
        keep = np.isin(yg, present)
        Xk, yk, gk = Xg[keep], yg[keep], gg[keep]
        majority = float(max(np.mean(yk == m) for m in present))
        raw = [a for s in range(args.seeds) if (a := grouped_acc(Xk, yk, gk, s)) is not None]
        shuf = [a for s in range(args.seeds)
                if (a := grouped_acc(Xk, rng.permutation(yk), gk, s)) is not None]
        results.append({
            "formula": formula,
            "polymorphs": present,
            "counts": {m: int(np.sum(yk == m)) for m in present},
            "n_specimens": int(np.unique(gk).size),
            "raw_acc_mean": round(float(np.mean(raw)), 3),
            "majority_baseline": round(majority, 3),
            "shuffled_acc_mean": round(float(np.mean(shuf)), 3),
            "raw_beats_majority": bool(np.mean(raw) > majority + 0.05),
        })

    scored = [r for r in results if "raw_acc_mean" in r]
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "rruff_polymorph_probe",
        "n_spectra_total": int(X.shape[0]),
        "seeds": args.seeds,
        "n_groups_scored": len(scored),
        "n_groups_raw_beats_majority": int(sum(r["raw_beats_majority"] for r in scored)),
        "groups": results,
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    return result


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--seeds", type=int, default=5)
    p.add_argument("--output", type=Path, default=Path("data/manifests/rruff_polymorph_probe.json"))
    return p.parse_args()


def main():
    print(json.dumps(run(parse_args()), indent=2))


if __name__ == "__main__":
    main()
