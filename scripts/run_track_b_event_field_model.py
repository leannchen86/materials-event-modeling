"""Train an event-field model and derive acquisition from field uncertainty."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


DEFAULT_REGIME_POOL = ["source_smooth", "reversed_time", "random_axis", "abrupt_basin"]
DEFAULT_HELDOUT_REGIMES = ["reversed_time", "random_axis", "abrupt_basin"]
FIELD_STRATEGIES = ["field_model_uncertainty", "field_model_uncertainty_coverage"]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_script_module(name: str, script_name: str) -> Any:
    script_path = project_root() / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TRANSFER = load_script_module("track_b_regime_transfer", "run_track_b_regime_transfer.py")
MIXED = load_script_module("track_b_mixed_regime_transfer", "run_track_b_mixed_regime_transfer.py")
NEURAL = TRANSFER.NEURAL
ACTIVE_LOOP = TRANSFER.ACTIVE_LOOP
FOREST_POLICY = TRANSFER.FOREST_POLICY


def pca_summary(pca_values: np.ndarray, components: int = 4) -> tuple[list[float], list[float]]:
    mean = pca_values.mean(axis=0)[:components].astype(float).tolist()
    std = pca_values.std(axis=0)[:components].astype(float).tolist()
    while len(mean) < components:
        mean.append(0.0)
        std.append(0.0)
    return mean, std


def field_features_for_candidate(
    *,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed: list[int],
    candidate: int,
    pca_model: PCA,
    max_observed: int,
) -> list[float]:
    observed_arr = np.asarray(observed, dtype=int)
    observed_coords = coords[observed_arr]
    observed_spectra = spectra[observed_arr]
    candidate_coord = coords[[candidate]]
    distances = np.linalg.norm(candidate_coord[:, None, :] - observed_coords[None, :, :], axis=2)[0]
    nearest_idx = int(np.argmin(distances))
    idw_prediction = NEURAL.inverse_distance_prediction(
        observed_coords,
        observed_spectra,
        candidate_coord,
    )[0]
    observed_pca = pca_model.transform(observed_spectra)
    idw_pca = pca_model.transform(idw_prediction.reshape(1, -1))[0]
    nearest_pca = observed_pca[nearest_idx]
    observed_mean_pca, observed_std_pca = pca_summary(observed_pca)
    observed_mean = observed_spectra.mean(axis=0)
    coord_span = observed_coords.max(axis=0) - observed_coords.min(axis=0)
    return [
        float(coords[candidate, 0]),
        float(coords[candidate, 1]),
        float(len(observed) / max_observed),
        float(distances.min()),
        float(distances.mean()),
        float(distances.max()),
        float(np.mean((idw_prediction - observed_spectra[nearest_idx]) ** 2)),
        float(np.mean((idw_prediction - observed_mean) ** 2)),
        float(np.mean(observed_mean)),
        float(np.std(observed_mean)),
        float(coord_span[0]),
        float(coord_span[1]),
        *idw_pca[:4].astype(float).tolist(),
        *nearest_pca[:4].astype(float).tolist(),
        *observed_mean_pca,
        *observed_std_pca,
    ]


def observed_indices_for_training_state(
    *,
    coords: np.ndarray,
    count: int,
    mode: str,
    rng: np.random.Generator,
) -> list[int]:
    if mode == "space_filling":
        return NEURAL.farthest_first_indices(coords, count).tolist()
    if mode == "random":
        return rng.choice(len(coords), size=count, replace=False).astype(int).tolist()
    raise ValueError(f"unknown observed-set mode: {mode}")


def build_field_examples(
    *,
    event_ids: np.ndarray,
    coords: np.ndarray,
    spectra: np.ndarray,
    selected_event_ids: set[str],
    pca_model: PCA,
    observed_counts: list[int],
    max_observed: int,
    seed: int,
    random_repeats: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    features = []
    targets = []
    groups = []
    for event_id in sorted(selected_event_ids):
        event_idx = np.flatnonzero(event_ids == event_id)
        event_coords = coords[event_idx]
        event_spectra = spectra[event_idx]
        for observed_count in observed_counts:
            modes = ["space_filling", *["random"] * random_repeats]
            for mode in modes:
                observed = observed_indices_for_training_state(
                    coords=event_coords,
                    count=observed_count,
                    mode=mode,
                    rng=rng,
                )
                candidates = [idx for idx in range(len(event_idx)) if idx not in observed]
                for candidate in candidates:
                    features.append(
                        field_features_for_candidate(
                            coords=event_coords,
                            spectra=event_spectra,
                            observed=observed,
                            candidate=candidate,
                            pca_model=pca_model,
                            max_observed=max_observed,
                        )
                    )
                    targets.append(pca_model.transform(event_spectra[[candidate]])[0])
                    groups.append(event_id)
    return (
        np.asarray(features, dtype=np.float32),
        np.asarray(targets, dtype=np.float32),
        np.asarray(groups),
    )


def train_field_model(features: np.ndarray, targets: np.ndarray, *, seed: int) -> Any:
    return make_pipeline(
        StandardScaler(),
        RandomForestRegressor(
            n_estimators=240,
            max_depth=12,
            min_samples_leaf=2,
            random_state=seed,
            n_jobs=-1,
        ),
    ).fit(features, targets)


def predict_tree_stack(model: Any, features: np.ndarray) -> np.ndarray:
    scaler = model.named_steps["standardscaler"]
    forest = model.named_steps["randomforestregressor"]
    scaled = scaler.transform(features)
    return np.asarray([tree.predict(scaled) for tree in forest.estimators_], dtype=np.float32)


def field_prediction_diagnostic(
    *,
    model: Any,
    train_targets: np.ndarray,
    test_features: np.ndarray,
    test_targets: np.ndarray,
) -> dict[str, float]:
    prediction = model.predict(test_features)
    baseline = np.tile(train_targets.mean(axis=0, keepdims=True), (len(test_targets), 1))
    baseline_mse = float(np.mean((test_targets - baseline) ** 2))
    model_mse = float(np.mean((test_targets - prediction) ** 2))
    return {
        "field_target_baseline_mse": baseline_mse,
        "field_target_model_mse": model_mse,
        "field_target_mse_improvement": 1.0 - (model_mse / baseline_mse),
    }


def choose_field_model_candidate(
    *,
    model: Any,
    pca_model: PCA,
    strategy: str,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed: list[int],
    candidates: list[int],
    max_observed: int,
) -> int:
    features = np.asarray(
        [
            field_features_for_candidate(
                coords=coords,
                spectra=spectra,
                observed=observed,
                candidate=candidate,
                pca_model=pca_model,
                max_observed=max_observed,
            )
            for candidate in candidates
        ],
        dtype=np.float32,
    )
    tree_predictions = predict_tree_stack(model, features)
    uncertainty = tree_predictions.var(axis=0).mean(axis=1)
    if strategy == "field_model_uncertainty":
        score = uncertainty
    elif strategy == "field_model_uncertainty_coverage":
        candidate_arr = np.asarray(candidates, dtype=int)
        observed_arr = np.asarray(observed, dtype=int)
        distances = np.linalg.norm(
            coords[candidate_arr, None, :] - coords[observed_arr][None, :, :],
            axis=2,
        )
        min_distance = distances.min(axis=1)
        score = uncertainty * (min_distance + 1e-6)
    else:
        raise ValueError(f"unknown field strategy: {strategy}")
    return int(candidates[int(np.argmax(score))])


def run_field_model_loop_for_event(
    *,
    model: Any,
    pca_model: PCA,
    strategy: str,
    coords: np.ndarray,
    spectra: np.ndarray,
    budget: int,
    initial_count: int,
    max_observed: int,
) -> dict[str, Any]:
    observed = NEURAL.farthest_first_indices(coords, initial_count).tolist()
    while len(observed) < budget:
        candidates = [idx for idx in range(len(coords)) if idx not in observed]
        next_idx = choose_field_model_candidate(
            model=model,
            pca_model=pca_model,
            strategy=strategy,
            coords=coords,
            spectra=spectra,
            observed=observed,
            candidates=candidates,
            max_observed=max_observed,
        )
        observed.append(next_idx)
    heldout = [idx for idx in range(len(coords)) if idx not in observed]
    final_mse = NEURAL.reconstruction_error(
        coords=coords,
        spectra=spectra,
        observed=observed,
        heldout=heldout,
    )
    return {"observed_indices": observed, "heldout_indices": heldout, "final_mse": final_mse}


def evaluate_field_model_policy(
    *,
    model: Any,
    pca_model: PCA,
    strategy: str,
    event_ids: np.ndarray,
    coords: np.ndarray,
    spectra: np.ndarray,
    test_event_ids: set[str],
    budgets: list[int],
    initial_count: int,
    max_observed: int,
) -> list[dict[str, Any]]:
    rows = []
    for budget in budgets:
        event_results = {}
        observed_spectra = []
        for event_id in sorted(test_event_ids):
            event_idx = np.flatnonzero(event_ids == event_id)
            result = run_field_model_loop_for_event(
                model=model,
                pca_model=pca_model,
                strategy=strategy,
                coords=coords[event_idx],
                spectra=spectra[event_idx],
                budget=budget,
                initial_count=initial_count,
                max_observed=max_observed,
            )
            observed_global_idx = event_idx[np.asarray(result["observed_indices"], dtype=int)]
            heldout_global_idx = event_idx[np.asarray(result["heldout_indices"], dtype=int)]
            event_results[event_id] = {
                "observed_global_idx": observed_global_idx,
                "heldout_global_idx": heldout_global_idx,
                "mse": result["final_mse"],
            }
            observed_spectra.append(spectra[observed_global_idx])

        for event_id, result in event_results.items():
            rows.append(
                {
                    "event_id": event_id,
                    "strategy": strategy,
                    "budget": budget,
                    **NEURAL.score_observed_set(
                        spectra=spectra,
                        observed_idx=result["observed_global_idx"],
                        heldout_idx=result["heldout_global_idx"],
                        event_mse=result["mse"],
                        all_observed_spectra=observed_spectra,
                    ),
                }
            )
    return rows


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    summary_rows = []
    for (heldout_regime, strategy, budget), group in df.groupby(
        ["heldout_regime", "strategy", "budget"],
        sort=True,
    ):
        summary_rows.append(
            {
                "heldout_regime": heldout_regime,
                "strategy": strategy,
                "budget": int(budget),
                "event_count": int(len(group)),
                "mse_mean": float(group["mse"].mean()),
                "mse_std": float(group["mse"].std(ddof=0)),
                "improvement_vs_event_mean_mean": float(group["improvement_vs_event_mean"].mean()),
                "improvement_vs_global_mean_mean": float(group["improvement_vs_global_mean"].mean()),
            }
        )
    return summary_rows


def summarize_diagnostics(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(diagnostics)
    rows = []
    for heldout_regime, group in df.groupby("heldout_regime", sort=True):
        rows.append(
            {
                "heldout_regime": heldout_regime,
                "seed_count": int(len(group)),
                "field_target_mse_improvement_mean": float(
                    group["field_target_mse_improvement"].mean()
                ),
                "field_target_mse_improvement_min": float(
                    group["field_target_mse_improvement"].min()
                ),
                "field_target_mse_improvement_max": float(
                    group["field_target_mse_improvement"].max()
                ),
            }
        )
    return rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    seeds = NEURAL.DEFAULT_SEEDS[: args.seed_count]
    max_observed = max(args.budgets) - 1
    observed_counts = list(range(args.initial_count, max(args.budgets)))
    rows = []
    diagnostics = []

    for seed in seeds:
        for heldout_regime in args.heldout_regimes:
            train_regimes = [regime for regime in args.regime_pool if regime != heldout_regime]
            train_field = MIXED.generate_mixed_train_field(
                train_regimes=train_regimes,
                events_per_regime=args.train_events_per_regime,
                observations_per_event=args.observations_per_event,
                n_theta=args.theta_points,
                seed=seed,
            )
            train_events = TRANSFER.unique_event_ids(train_field)
            pca_components = min(args.pca_components, train_field.spectra.shape[0] - 1)
            pca_model = PCA(n_components=pca_components, random_state=seed)
            pca_model.fit(train_field.spectra)
            train_features, train_targets, _ = build_field_examples(
                event_ids=train_field.event_ids,
                coords=train_field.coords,
                spectra=train_field.spectra,
                selected_event_ids=train_events,
                pca_model=pca_model,
                observed_counts=observed_counts,
                max_observed=max_observed,
                seed=seed,
                random_repeats=args.random_repeats,
            )
            field_model = train_field_model(train_features, train_targets, seed=seed)

            coordinate_forest, coordinate_pca = train_coordinate_forest(
                field=train_field,
                train_events=train_events,
                budgets=args.budgets,
                initial_count=args.initial_count,
                pca_components=args.pca_components,
                seed=seed,
            )

            test_field = TRANSFER.generate_transfer_event_field(
                n_events=args.test_events,
                observations_per_event=args.observations_per_event,
                n_theta=args.theta_points,
                seed=seed + args.test_seed_offset,
                transfer_regime=heldout_regime,
            )
            test_events = TRANSFER.unique_event_ids(test_field)
            test_features, test_targets, _ = build_field_examples(
                event_ids=test_field.event_ids,
                coords=test_field.coords,
                spectra=test_field.spectra,
                selected_event_ids=test_events,
                pca_model=pca_model,
                observed_counts=observed_counts,
                max_observed=max_observed,
                seed=seed + args.test_seed_offset,
                random_repeats=1,
            )
            diagnostics.append(
                {
                    "seed": seed,
                    "heldout_regime": heldout_regime,
                    "train_regimes": train_regimes,
                    "train_events": len(train_events),
                    "test_events": len(test_events),
                    "training_examples": int(len(train_targets)),
                    "test_examples": int(len(test_targets)),
                    **field_prediction_diagnostic(
                        model=field_model,
                        train_targets=train_targets,
                        test_features=test_features,
                        test_targets=test_targets,
                    ),
                }
            )

            for strategy in FIELD_STRATEGIES:
                field_rows = evaluate_field_model_policy(
                    model=field_model,
                    pca_model=pca_model,
                    strategy=strategy,
                    event_ids=test_field.event_ids,
                    coords=test_field.coords,
                    spectra=test_field.spectra,
                    test_event_ids=test_events,
                    budgets=args.budgets,
                    initial_count=args.initial_count,
                    max_observed=max_observed,
                )
                for row in field_rows:
                    row["seed"] = seed
                    row["heldout_regime"] = heldout_regime
                    row["train_regimes"] = train_regimes
                    rows.append(row)

            forest_rows = FOREST_POLICY.evaluate_learned_policy(
                model=coordinate_forest,
                event_ids=test_field.event_ids,
                coords=test_field.coords,
                spectra=test_field.spectra,
                test_event_ids=test_events,
                budgets=args.budgets,
                initial_count=args.initial_count,
                pca_model=coordinate_pca,
            )
            for row in forest_rows:
                row["seed"] = seed
                row["heldout_regime"] = heldout_regime
                row["train_regimes"] = train_regimes
                rows.append(row)

            for budget in args.budgets:
                for strategy in ["random", "space_filling", "active_hybrid", "oracle_best"]:
                    baseline = ACTIVE_LOOP.run_strategy(
                        strategy=strategy,
                        event_ids=test_field.event_ids,
                        coords=test_field.coords,
                        spectra=test_field.spectra,
                        budget=budget,
                        initial_count=args.initial_count,
                        seed=seed + budget * 100 + args.test_seed_offset,
                    )
                    for row in baseline["rows"]:
                        row["seed"] = seed
                        row["heldout_regime"] = heldout_regime
                        row["train_regimes"] = train_regimes
                        rows.append(row)

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "track_b_event_field_model",
        "regime_pool": args.regime_pool,
        "heldout_regimes": args.heldout_regimes,
        "train_events_per_regime": args.train_events_per_regime,
        "test_events": args.test_events,
        "observations_per_event": args.observations_per_event,
        "initial_count": args.initial_count,
        "budgets": args.budgets,
        "observed_counts_for_field_training": observed_counts,
        "random_repeats": args.random_repeats,
        "seeds": seeds,
        "field_model": {
            "model": "RandomForestRegressor over PCA-compressed target spectra",
            "objective": "predict held-out raw measurement PCA coordinates from partial event observations",
            "acquisition": [
                "field_model_uncertainty: select highest ensemble variance",
                "field_model_uncertainty_coverage: ensemble variance times distance to observed coordinates",
            ],
        },
        "hypotheses": [
            "The event field model should predict held-out measurement spectra better than a train-mean PCA baseline.",
            "If field modeling is the smarter route, uncertainty-derived acquisition should beat direct learned acquisition or space-filling in at least one hard held-out regime.",
            "If field prediction is good but uncertainty acquisition is weak, the next bottleneck is uncertainty calibration/acquisition, not representation.",
            "If field prediction itself is weak, the next step should be a stronger event field model or richer process context, not another acquisition heuristic.",
        ],
        "direction_critique": [
            "This avoids calcifying around relation graphs: relations are only implicit features for predicting missing measurements.",
            "It avoids training first on oracle acquisition labels; the primary objective is raw event reconstruction.",
            "It tests whether modeling the event before choosing actions is more robust than direct acquisition-policy learning.",
            "A negative result would tell us to stop looping on acquisition heads and improve the field model or data schema.",
        ],
        "diagnostics": diagnostics,
        "diagnostic_summary": summarize_diagnostics(diagnostics),
        "rows": rows,
        "summary": summarize(rows),
        "caveats": [
            "This is synthetic and uses PCA-compressed target spectra for the field model.",
            "Random-forest ensemble variance is only a crude uncertainty proxy.",
            "The score remains raw held-out measurement reconstruction, not label prediction.",
        ],
    }
    output_path = project_root() / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def train_coordinate_forest(
    *,
    field: Any,
    train_events: set[str],
    budgets: list[int],
    initial_count: int,
    pca_components: int,
    seed: int,
) -> tuple[Any, PCA]:
    pca_count = min(pca_components, field.spectra.shape[0] - 1)
    pca_model = PCA(n_components=pca_count, random_state=seed)
    pca_model.fit(field.spectra)
    features, targets, _ = FOREST_POLICY.build_training_examples(
        event_ids=field.event_ids,
        coords=field.coords,
        spectra=field.spectra,
        train_event_ids=train_events,
        budgets=budgets,
        initial_count=initial_count,
        pca_model=pca_model,
    )
    return FOREST_POLICY.train_model(features, targets, seed=seed), pca_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regime-pool", nargs="+", default=DEFAULT_REGIME_POOL)
    parser.add_argument("--heldout-regimes", nargs="+", default=DEFAULT_HELDOUT_REGIMES)
    parser.add_argument("--train-events-per-regime", type=int, default=32)
    parser.add_argument("--test-events", type=int, default=48)
    parser.add_argument("--observations-per-event", type=int, default=12)
    parser.add_argument("--theta-points", type=int, default=512)
    parser.add_argument("--initial-count", type=int, default=2)
    parser.add_argument("--budgets", type=int, nargs="+", default=[3, 4, 6, 8])
    parser.add_argument("--pca-components", type=int, default=8)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--random-repeats", type=int, default=2)
    parser.add_argument("--test-seed-offset", type=int, default=10000)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/track_b_event_field_model.json"),
    )
    return parser.parse_args()


def main() -> None:
    result = run(parse_args())
    printable = {
        "task": result["task"],
        "hypotheses": result["hypotheses"],
        "direction_critique": result["direction_critique"],
        "diagnostic_summary": result["diagnostic_summary"],
        "summary": result["summary"],
        "caveats": result["caveats"],
    }
    print(json.dumps(printable, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
