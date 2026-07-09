"""Held-out-batch replicate ranking: does the within-policy ranking RULE transfer
across collection batches, or is it calibrated to the pair-rich batch it was largely
trained on?

The A/B and ranking-robustness runs score every cell leave-one-POLICY-out over the
pooled dataset, so the scorer has always seen the test batch's collection style (policies
nest in batches). This run holds out a whole BATCH: train on the other two batches, then
rank the held-out batch's within-policy pairs. The drop from the pooled LOO-policy
accuracy on the same pairs is the cost of not having seen the test batch.

All feature/estimator machinery is the frozen `eval.severson_ab`; only the train-set
partition (batch-exclusion) is new. Pre-reg:
docs/controlled-collection/severson_heldout_batch_ranking.md (commit before this runs).

Output: data/manifests/severson_heldout_batch_ranking.json (with run identity).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from materials_event_modeling.eval.severson_ab import (
    cluster_bootstrap_ci,
    load_cells,
    loo_policy_scores,
    make_model,
    per_pair_correct,
    ranking_pairs,
    representation,
)
from materials_event_modeling.run_identity import run_identity

EVENTS_REL = Path("data/interim/event_grammar_v1/severson_battery/events.json")
MODELS = ("ridge", "svr_rbf", "gradient_boosting", "forest", "knn")
SEEDS = (0, 1, 2)
K = 100


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def held_out_batch_scores(
    cells: list[dict], held_batch: str, rep: str, k: int, model_name: str, seed: int
) -> dict:
    """Score every cell in `held_batch` with a model trained on the OTHER batches' EOL
    cells. No leave-one-policy-out is needed inside the held batch: its policies are
    absent from training because policies nest in batch (strictly harder than pooled LOO).
    """
    train = [c for c in cells if not c["censored"] and c["batch"] != held_batch]
    X = np.array([representation(c, rep, k) for c in train])
    y = np.log10([c["cycle_life"] for c in train])
    model = make_model(model_name, seed)
    model.fit(X, y)
    held = [c for c in cells if c["batch"] == held_batch]
    return {
        c["event_id"]: float(model.predict(np.array([representation(c, rep, k)]))[0])
        for c in held
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, default=EVENTS_REL)
    parser.add_argument("--output", type=Path,
                        default=Path("data/manifests/severson_heldout_batch_ranking.json"))
    args = parser.parse_args()
    root = project_root()

    cells = load_cells(root / args.events)
    pairs_all, counts = ranking_pairs(cells)
    batch_of = {c["event_id"]: c["batch"] for c in cells}
    policy_of = {c["event_id"]: c["policy"] for c in cells}
    batches = sorted({c["batch"] for c in cells})

    # Sanity: every pair is within a single batch (both members share a batch).
    assert all(batch_of[w] == batch_of[l] for w, l in pairs_all), "cross-batch pair!"
    pairs_by_batch = {b: [(w, l) for w, l in pairs_all if batch_of[w] == b] for b in batches}
    eol_by_batch = {b: sum(not c["censored"] and c["batch"] == b for c in cells)
                    for b in batches}

    # Structural control: paper-shape B must tie (0.500) on every pair, any split.
    b_scores = {c["event_id"]: 0.0 for c in cells}  # constant within policy -> forced tie
    b_pooled = float(per_pair_correct(pairs_all, {**b_scores}).mean()) if pairs_all else 0.5

    results = {}
    for model_name in MODELS:
        # Reference: pooled LOO-policy scores (what the 0.756 headline uses), sliced by
        # batch -> reproduces 0.779 / 0.667 / 0.333 for ridge as an internal check.
        loo_seed_correct = []
        hob_seed_scores: list[dict] = []
        for seed in SEEDS:
            loo_seed_correct.append(
                per_pair_correct(pairs_all, loo_policy_scores(cells, "A_full", K, model_name, seed))
            )
            merged: dict = {}
            for b in batches:
                merged.update(held_out_batch_scores(cells, b, "A_full", K, model_name, seed))
            hob_seed_scores.append(merged)
        loo_correct = np.mean(loo_seed_correct, axis=0)
        hob_correct = np.mean(
            [per_pair_correct(pairs_all, s) for s in hob_seed_scores], axis=0
        )

        pair_index = {(w, l): i for i, (w, l) in enumerate(pairs_all)}

        per_batch = {}
        macro = []
        for b in batches:
            idxs = [pair_index[p] for p in pairs_by_batch[b]]
            loo_acc = float(loo_correct[idxs].mean()) if idxs else float("nan")
            hob_acc = float(hob_correct[idxs].mean()) if idxs else float("nan")
            clusters_b = [policy_of[pairs_all[i][0]] for i in idxs]
            if len(set(clusters_b)) >= 2:
                clo, chi = cluster_bootstrap_ci(hob_correct[idxs], clusters_b)
            else:
                clo, chi = float("nan"), float("nan")
            per_batch[b] = {
                "n_pairs": len(idxs),
                "n_train_eol": sum(v for k, v in eol_by_batch.items() if k != b),
                "loo_policy_accuracy": loo_acc,
                "held_out_batch_accuracy": hob_acc,
                "transfer_cost": loo_acc - hob_acc,
                "held_out_batch_cluster_ci95": [clo, chi],
            }
            macro.append(hob_acc)

        clusters_all = [policy_of[w] for w, _ in pairs_all]
        pooled_lo, pooled_hi = cluster_bootstrap_ci(hob_correct, clusters_all)
        results[model_name] = {
            "per_batch": per_batch,
            "pooled_held_out_batch_accuracy": float(hob_correct.mean()),
            "pooled_held_out_batch_cluster_ci95": [pooled_lo, pooled_hi],
            "macro_avg_held_out_batch_accuracy": float(np.nanmean(macro)),
            "pooled_loo_policy_accuracy": float(loo_correct.mean()),
        }

    report = {
        "task": "severson_heldout_batch_ranking",
        "pre_registration": "docs/controlled-collection/severson_heldout_batch_ranking.md",
        "representation": "A_full",
        "k": K,
        "seeds": list(SEEDS),
        "pair_counts": counts,
        "n_pairs": len(pairs_all),
        "pairs_per_batch": {b: len(pairs_by_batch[b]) for b in batches},
        "eol_cells_per_batch": eol_by_batch,
        "paper_shape_b_pooled_accuracy": b_pooled,
        "results": results,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_identity": run_identity(),
    }
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print(f"\nHeld-out-batch ranking — {len(pairs_all)} pairs, A_full, k={K}")
    print(f"  pairs/batch: {report['pairs_per_batch']}  |  paper-shape B pooled: {b_pooled:.3f}\n")
    for m in MODELS:
        r = results[m]
        print(f"  {m}")
        for b in batches:
            pb = r["per_batch"][b]
            lo, hi = pb["held_out_batch_cluster_ci95"]
            ci = f"[{lo:.3f}, {hi:.3f}]" if lo == lo else "[n/a — <2 clusters]"
            print(f"    {b}  n={pb['n_pairs']:>3}  train_eol={pb['n_train_eol']:>3}  "
                  f"LOO-policy={pb['loo_policy_accuracy']:.3f}  "
                  f"held-out-batch={pb['held_out_batch_accuracy']:.3f}  {ci}")
        print(f"    pooled held-out-batch={r['pooled_held_out_batch_accuracy']:.3f}  "
              f"macro-avg={r['macro_avg_held_out_batch_accuracy']:.3f}  "
              f"(pooled LOO-policy ref={r['pooled_loo_policy_accuracy']:.3f})\n")


if __name__ == "__main__":
    main()
