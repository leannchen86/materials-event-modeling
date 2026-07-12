"""Ranking-robustness follow-on: within-policy replicate ranking across 5 model families.

Settles whether the A/B's forest ranking weakness (0.596 vs ridge 0.756) is a
tree-ensemble artifact or a signal limit, by running the SAME leave-one-policy-out
ranking sub-task across linear / kernel / boosted-tree / bagged-tree / instance-based
models. All machinery is the frozen `eval.severson_ab` (identical to the A/B). Pre-reg:
docs/controlled-collection/severson_ranking_robustness.md (committed before this ran).

Output: data/manifests/severson_ranking_robustness.json (with run identity).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from materials_event_modeling.eval.severson_ab import (
    cluster_bootstrap_ci,
    load_cells,
    loo_policy_scores,
    per_pair_correct,
    ranking_pairs,
)
from materials_event_modeling.run_identity import run_identity

EVENTS_REL = Path("data/interim/event_grammar_v1/severson_battery/events.json")
MODELS = ("ridge", "svr_rbf", "gradient_boosting", "forest", "knn")
SEEDS = (0, 1, 2)
K = 100


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def held_out_policy_spearman(cells: list[dict], model_name: str) -> float:
    """Regression skill under the same LOO-policy scoring, for the diagnostic gap."""
    eol = [c for c in cells if not c["censored"]]
    ids = [c["event_id"] for c in eol]
    y = {c["event_id"]: float(np.log10(c["cycle_life"])) for c in eol}
    rhos = []
    for seed in SEEDS:
        scores = loo_policy_scores(cells, "A_full", K, model_name, seed)
        pred = np.array([scores[i] for i in ids])
        true = np.array([y[i] for i in ids])
        rhos.append(float(spearmanr(pred, true).statistic))
    return float(np.mean(rhos))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, default=EVENTS_REL)
    parser.add_argument("--output", type=Path,
                        default=Path("data/manifests/severson_ranking_robustness.json"))
    args = parser.parse_args()
    root = project_root()

    cells = load_cells(root / args.events)
    pairs_all, counts = ranking_pairs(cells)
    policy_of = {c["event_id"]: c["policy"] for c in cells}
    clusters = [policy_of[w] for w, _ in pairs_all]

    results = {}
    for model_name in MODELS:
        per_seed = []
        for seed in SEEDS:
            scores = loo_policy_scores(cells, "A_full", K, model_name, seed)
            per_seed.append(per_pair_correct(pairs_all, scores))
        mean_per_pair = np.mean(per_seed, axis=0)
        clo, chi = cluster_bootstrap_ci(mean_per_pair, clusters)
        acc = float(mean_per_pair.mean())
        results[model_name] = {
            "pairwise_accuracy": acc,
            "per_seed_accuracy": [float(p.mean()) for p in per_seed],
            "cluster_ci95": [clo, chi],
            "clears_bar": acc >= 0.60 and clo > 0.50,
            "held_out_policy_spearman": held_out_policy_spearman(cells, model_name),
        }

    n_clear = sum(r["clears_bar"] for r in results.values())
    report = {
        "task": "severson_ranking_robustness",
        "pre_registration": "docs/controlled-collection/severson_ranking_robustness.md",
        "representation": "A_full",
        "k": K,
        "pair_counts": counts,
        "n_pairs": len(pairs_all),
        "models_clearing_bar": n_clear,
        "hypothesis_confirmed": n_clear >= 3,
        "results": results,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_identity": run_identity(),
    }

    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")

    print(f"\nRanking robustness — {len(pairs_all)} pairs, A_full, k={K}\n")
    print(f"  {'model':<20}{'rank_acc':>9}{'cluster_CI':>18}{'reg_rho':>9}  clears")
    for m, r in sorted(results.items(), key=lambda kv: -kv[1]["pairwise_accuracy"]):
        lo, hi = r["cluster_ci95"]
        print(f"  {m:<20}{r['pairwise_accuracy']:>9.3f}   [{lo:.3f}, {hi:.3f}]"
              f"{r['held_out_policy_spearman']:>9.3f}  {'YES' if r['clears_bar'] else 'no'}")
    print(f"\n  {n_clear}/5 families clear the bar -> hypothesis "
          f"{'CONFIRMED' if n_clear >= 3 else 'FALSIFIED'}\n  wrote {args.output}\n")


if __name__ == "__main__":
    main()
