"""Train a lightweight learned acquisition policy for Track B event fields.

The model learns from fully observed synthetic events which next observation would reduce
future raw-measurement reconstruction error. Labels such as phase or success are not used.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from materials_event_modeling.track_b.field_prediction import (
    farthest_first_indices,
    inverse_distance_prediction,
    mean_squared_error,
)
from materials_event_modeling.track_b.synthetic_field import generate_synthetic_event_field

DEFAULT_SEEDS = [17, 29, 41, 53, 67]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_active_loop_module() -> Any:
    script_path = project_root() / "scripts" / "run_track_b_active_event_loop.py"
    spec = importlib.util.spec_from_file_location("track_b_active_loop", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reconstruction_error(
    *,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed: list[int],
    heldout: list[int],
) -> float:
    if not heldout:
        return 0.0
    prediction = inverse_distance_prediction(
        coords[np.array(observed, dtype=int)],
        spectra[np.array(observed, dtype=int)],
        coords[np.array(heldout, dtype=int)],
    )
    return mean_squared_error(spectra[np.array(heldout, dtype=int)], prediction)


def candidate_features(
    *,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed: list[int],
    candidate: int,
    budget: int,
    pca_model: PCA,
) -> list[float]:
    observed_arr = np.array(observed, dtype=int)
    observed_coords = coords[observed_arr]
    observed_spectra = spectra[observed_arr]
    candidate_coord = coords[[candidate]]
    distances = np.linalg.norm(candidate_coord[:, None, :] - observed_coords[None, :, :], axis=2)[0]
    nearest_idx = int(np.argmin(distances))
    min_distance = float(distances[nearest_idx])
    mean_distance = float(np.mean(distances))
    max_distance = float(np.max(distances))
    prediction = inverse_distance_prediction(observed_coords, observed_spectra, candidate_coord)[0]
    nearest_spectrum = observed_spectra[nearest_idx]
    observed_mean = observed_spectra.mean(axis=0)
    predicted_residual = float(np.mean((prediction - nearest_spectrum) ** 2))
    mean_residual = float(np.mean((prediction - observed_mean) ** 2))
    observed_pca = pca_model.transform(observed_spectra)
    pca_mean = observed_pca.mean(axis=0)
    pca_std = observed_pca.std(axis=0)

    return [
        float(coords[candidate, 0]),
        float(coords[candidate, 1]),
        float(len(observed)),
        float(budget),
        min_distance,
        mean_distance,
        max_distance,
        predicted_residual,
        mean_residual,
        float(np.mean(observed_mean)),
        float(np.std(observed_mean)),
        *pca_mean[:4].astype(float).tolist(),
        *pca_std[:4].astype(float).tolist(),
    ]


def build_training_examples(
    *,
    event_ids: np.ndarray,
    coords: np.ndarray,
    spectra: np.ndarray,
    train_event_ids: set[str],
    budgets: list[int],
    initial_count: int,
    pca_model: PCA,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    features = []
    targets = []
    groups = []
    for event_id in sorted(train_event_ids):
        event_idx = np.flatnonzero(event_ids == event_id)
        event_coords = coords[event_idx]
        event_spectra = spectra[event_idx]
        for budget in budgets:
            observed = farthest_first_indices(event_coords, initial_count).tolist()
            while len(observed) < budget:
                candidates = [idx for idx in range(len(event_idx)) if idx not in observed]
                current_error = reconstruction_error(
                    coords=event_coords,
                    spectra=event_spectra,
                    observed=observed,
                    heldout=candidates,
                )
                for candidate in candidates:
                    next_observed = [*observed, candidate]
                    next_heldout = [idx for idx in candidates if idx != candidate]
                    next_error = reconstruction_error(
                        coords=event_coords,
                        spectra=event_spectra,
                        observed=next_observed,
                        heldout=next_heldout,
                    )
                    features.append(
                        candidate_features(
                            coords=event_coords,
                            spectra=event_spectra,
                            observed=observed,
                            candidate=candidate,
                            budget=budget,
                            pca_model=pca_model,
                        )
                    )
                    targets.append(current_error - next_error)
                    groups.append(event_id)

                best_candidate = max(
                    candidates,
                    key=lambda idx: targets[
                        len(targets) - len(candidates) + candidates.index(idx)
                    ],
                )
                observed.append(int(best_candidate))
    return (
        np.asarray(features, dtype=np.float32),
        np.asarray(targets, dtype=np.float32),
        np.asarray(groups),
    )


def choose_learned_candidate(
    *,
    model: Any,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed: list[int],
    candidates: list[int],
    budget: int,
    pca_model: PCA,
) -> int:
    feature_rows = [
        candidate_features(
            coords=coords,
            spectra=spectra,
            observed=observed,
            candidate=candidate,
            budget=budget,
            pca_model=pca_model,
        )
        for candidate in candidates
    ]
    scores = model.predict(np.asarray(feature_rows, dtype=np.float32))
    return int(candidates[int(np.argmax(scores))])


def run_learned_loop_for_event(
    *,
    model: Any,
    coords: np.ndarray,
    spectra: np.ndarray,
    budget: int,
    initial_count: int,
    pca_model: PCA,
) -> dict[str, Any]:
    observed = farthest_first_indices(coords, initial_count).tolist()
    trajectory = []
    while len(observed) < budget:
        candidates = [idx for idx in range(len(coords)) if idx not in observed]
        heldout = list(candidates)
        current_error = reconstruction_error(
            coords=coords,
            spectra=spectra,
            observed=observed,
            heldout=heldout,
        )
        next_idx = choose_learned_candidate(
            model=model,
            coords=coords,
            spectra=spectra,
            observed=observed,
            candidates=candidates,
            budget=budget,
            pca_model=pca_model,
        )
        trajectory.append(
            {
                "observed_count_before": len(observed),
                "chosen_index": int(next_idx),
                "chosen_coord": coords[next_idx].tolist(),
                "heldout_mse_before": current_error,
            }
        )
        observed.append(next_idx)

    remaining = [idx for idx in range(len(coords)) if idx not in observed]
    final_mse = reconstruction_error(
        coords=coords,
        spectra=spectra,
        observed=observed,
        heldout=remaining,
    )
    return {
        "observed_indices": observed,
        "heldout_indices": remaining,
        "final_mse": final_mse,
        "trajectory": trajectory,
    }


def score_observed_set(
    *,
    spectra: np.ndarray,
    observed_idx: np.ndarray,
    heldout_idx: np.ndarray,
    event_mse: float,
    all_observed_spectra: list[np.ndarray],
) -> dict[str, float]:
    event_mean = spectra[observed_idx].mean(axis=0)
    event_mean_prediction = np.tile(event_mean, (len(heldout_idx), 1))
    event_mean_mse = mean_squared_error(spectra[heldout_idx], event_mean_prediction)
    global_mean = np.vstack(all_observed_spectra).mean(axis=0)
    global_prediction = np.tile(global_mean, (len(heldout_idx), 1))
    global_mean_mse = mean_squared_error(spectra[heldout_idx], global_prediction)
    return {
        "mse": event_mse,
        "event_mean_mse": event_mean_mse,
        "global_mean_mse": global_mean_mse,
        "improvement_vs_event_mean": 1.0 - (event_mse / event_mean_mse),
        "improvement_vs_global_mean": 1.0 - (event_mse / global_mean_mse),
    }


def evaluate_learned_policy(
    *,
    model: Any,
    event_ids: np.ndarray,
    coords: np.ndarray,
    spectra: np.ndarray,
    test_event_ids: set[str],
    budgets: list[int],
    initial_count: int,
    pca_model: PCA,
) -> list[dict[str, Any]]:
    rows = []
    for budget in budgets:
        event_results = {}
        observed_spectra = []
        for event_id in sorted(test_event_ids):
            event_idx = np.flatnonzero(event_ids == event_id)
            result = run_learned_loop_for_event(
                model=model,
                coords=coords[event_idx],
                spectra=spectra[event_idx],
                budget=budget,
                initial_count=initial_count,
                pca_model=pca_model,
            )
            observed_global_idx = event_idx[np.array(result["observed_indices"], dtype=int)]
            heldout_global_idx = event_idx[np.array(result["heldout_indices"], dtype=int)]
            event_results[event_id] = {
                "observed_global_idx": observed_global_idx,
                "heldout_global_idx": heldout_global_idx,
                "mse": result["final_mse"],
            }
            observed_spectra.append(spectra[observed_global_idx])

        for event_id, result in event_results.items():
            score = score_observed_set(
                spectra=spectra,
                observed_idx=result["observed_global_idx"],
                heldout_idx=result["heldout_global_idx"],
                event_mse=result["mse"],
                all_observed_spectra=observed_spectra,
            )
            rows.append(
                {
                    "event_id": event_id,
                    "strategy": "learned_forest",
                    "budget": budget,
                    **score,
                }
            )
    return rows


def train_model(features: np.ndarray, targets: np.ndarray, *, seed: int) -> Any:
    return make_pipeline(
        StandardScaler(),
        RandomForestRegressor(
            n_estimators=250,
            max_depth=8,
            min_samples_leaf=3,
            random_state=seed,
            n_jobs=-1,
        ),
    ).fit(features, targets)


def target_cross_validation(
    features: np.ndarray,
    targets: np.ndarray,
    groups: np.ndarray,
    *,
    seed: int,
) -> dict[str, float]:
    unique_groups = np.unique(groups)
    splits = min(4, len(unique_groups))
    cv = GroupKFold(n_splits=splits)
    baseline_errors = []
    model_errors = []
    for train_idx, test_idx in cv.split(features, groups=groups):
        model = train_model(features[train_idx], targets[train_idx], seed=seed)
        prediction = model.predict(features[test_idx])
        train_mean = float(targets[train_idx].mean())
        baseline = np.full_like(targets[test_idx], train_mean)
        baseline_errors.append(float(np.mean((targets[test_idx] - baseline) ** 2)))
        model_errors.append(float(np.mean((targets[test_idx] - prediction) ** 2)))
    baseline_mse = float(np.mean(baseline_errors))
    model_mse = float(np.mean(model_errors))
    return {
        "target_baseline_mse": baseline_mse,
        "target_model_mse": model_mse,
        "target_mse_improvement": 1.0 - (model_mse / baseline_mse),
    }


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    summary_rows = []
    for (strategy, budget), group in df.groupby(["strategy", "budget"], sort=True):
        summary_rows.append(
            {
                "strategy": strategy,
                "budget": int(budget),
                "event_count": len(group),
                "mse_mean": float(group["mse"].mean()),
                "mse_std": float(group["mse"].std(ddof=0)),
                "improvement_vs_event_mean_mean": float(group["improvement_vs_event_mean"].mean()),
                "improvement_vs_global_mean_mean": float(group["improvement_vs_global_mean"].mean()),
            }
        )
    return summary_rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    active_loop = load_active_loop_module()
    all_rows = []
    diagnostics = []
    seeds = DEFAULT_SEEDS[: args.seed_count]
    for seed in seeds:
        field = generate_synthetic_event_field(
            n_events=args.events,
            observations_per_event=args.observations_per_event,
            n_theta=args.theta_points,
            seed=seed,
        )
        unique_events = np.array(sorted(set(field.event_ids.tolist())))
        split_rng = np.random.default_rng(seed + 3000)
        shuffled_events = unique_events.copy()
        split_rng.shuffle(shuffled_events)
        split_point = int(round(len(shuffled_events) * args.train_fraction))
        train_events = set(shuffled_events[:split_point].tolist())
        test_events = set(shuffled_events[split_point:].tolist())

        pca_components = min(args.pca_components, len(train_events) * args.observations_per_event - 1)
        train_mask = np.isin(field.event_ids, list(train_events))
        pca_model = PCA(n_components=pca_components, random_state=seed)
        pca_model.fit(field.spectra[train_mask])

        features, targets, groups = build_training_examples(
            event_ids=field.event_ids,
            coords=field.coords,
            spectra=field.spectra,
            train_event_ids=train_events,
            budgets=args.budgets,
            initial_count=args.initial_count,
            pca_model=pca_model,
        )
        model = train_model(features, targets, seed=seed)
        target_cv = target_cross_validation(features, targets, groups, seed=seed)
        diagnostics.append(
            {
                "seed": seed,
                "train_events": len(train_events),
                "test_events": len(test_events),
                "training_examples": len(targets),
                "target_mean": float(targets.mean()),
                "target_std": float(targets.std()),
                **target_cv,
            }
        )

        learned_rows = evaluate_learned_policy(
            model=model,
            event_ids=field.event_ids,
            coords=field.coords,
            spectra=field.spectra,
            test_event_ids=test_events,
            budgets=args.budgets,
            initial_count=args.initial_count,
            pca_model=pca_model,
        )
        for row in learned_rows:
            row["seed"] = seed
            all_rows.append(row)

        test_mask = np.isin(field.event_ids, list(test_events))
        for budget in args.budgets:
            for strategy in ["random", "space_filling", "active_hybrid", "oracle_best"]:
                baseline = active_loop.run_strategy(
                    strategy=strategy,
                    event_ids=field.event_ids[test_mask],
                    coords=field.coords[test_mask],
                    spectra=field.spectra[test_mask],
                    budget=budget,
                    initial_count=args.initial_count,
                    seed=seed + budget * 100,
                )
                for row in baseline["rows"]:
                    row["seed"] = seed
                    all_rows.append(row)

    summary = summarize(all_rows)
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "track_b_learned_active_policy",
        "architecture": {
            "model": "RandomForestRegressor",
            "n_estimators": 250,
            "max_depth": 8,
            "min_samples_leaf": 3,
            "feature_type": "candidate coordinate, observation budget/state, distance-to-observed, IDW disagreement, observed-spectrum PCA summary",
            "target": "oracle one-step reduction in held-out raw-measurement reconstruction MSE",
        },
        "events": args.events,
        "observations_per_event": args.observations_per_event,
        "initial_count": args.initial_count,
        "budgets": args.budgets,
        "train_fraction": args.train_fraction,
        "seeds": seeds,
        "hypotheses": [
            "A learned acquisition regressor should predict oracle improvement better than a train-mean target baseline.",
            "A learned policy should beat the naive active heuristic and random selection on held-out events.",
            "If the learned policy cannot beat space-filling, the current state representation is not strong enough yet.",
        ],
        "diagnostics": diagnostics,
        "rows": all_rows,
        "summary": summary,
        "caveats": [
            "This is a tabular acquisition model, not a neural event foundation model.",
            "The policy is trained on synthetic fully observed events; real transfer is unknown.",
            "The target uses oracle improvement available only in the synthetic scaffold or completed historical events.",
        ],
    }

    output_path = project_root() / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=int, default=48)
    parser.add_argument("--observations-per-event", type=int, default=12)
    parser.add_argument("--theta-points", type=int, default=512)
    parser.add_argument("--initial-count", type=int, default=2)
    parser.add_argument("--budgets", type=int, nargs="+", default=[3, 4, 6, 8])
    parser.add_argument("--train-fraction", type=float, default=0.67)
    parser.add_argument("--pca-components", type=int, default=6)
    parser.add_argument("--seed-count", type=int, default=len(DEFAULT_SEEDS))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/track_b_learned_active_policy.json"),
    )
    return parser.parse_args()


def main() -> None:
    result = run(parse_args())
    printable = {
        "task": result["task"],
        "architecture": result["architecture"],
        "hypotheses": result["hypotheses"],
        "diagnostics": result["diagnostics"],
        "summary": result["summary"],
        "caveats": result["caveats"],
    }
    print(json.dumps(printable, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
