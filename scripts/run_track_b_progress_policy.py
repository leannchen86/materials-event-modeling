"""Test explicit latent-progress acquisition policies for Track B event fields."""

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
PROGRESS_POLICIES = ["latent_progress_forest", "oracle_progress_forest"]


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


def progress_array_for_field(field: Any) -> np.ndarray:
    return field.table["event_progress"].to_numpy(dtype=np.float32)


def normalize(values: np.ndarray) -> np.ndarray:
    span = float(np.ptp(values))
    if span < 1e-8:
        return np.zeros_like(values, dtype=np.float32)
    return ((values - float(values.min())) / span).astype(np.float32)


def infer_progress_from_observations(
    *,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed: list[int],
) -> np.ndarray:
    """Infer a 1D event coordinate from partial spectra and observation positions.

    This intentionally avoids the synthetic hidden progress label. It estimates the
    dominant spectral-change score among observed points, then fits the coordinate
    direction that best explains that score.
    """

    if len(observed) < 2:
        return normalize(coords[:, 0])

    observed_arr = np.asarray(observed, dtype=int)
    observed_coords = coords[observed_arr]
    observed_spectra = spectra[observed_arr]
    spectral_centered = observed_spectra - observed_spectra.mean(axis=0, keepdims=True)
    if float(np.linalg.norm(spectral_centered)) < 1e-8:
        return normalize(coords[:, 0])

    _, _, vt = np.linalg.svd(spectral_centered, full_matrices=False)
    scores = spectral_centered @ vt[0]
    scores = scores - scores.mean()
    coord_centered = observed_coords - observed_coords.mean(axis=0, keepdims=True)
    gram = coord_centered.T @ coord_centered + 1e-4 * np.eye(coord_centered.shape[1])
    beta = np.linalg.solve(gram, coord_centered.T @ scores)
    beta_norm = float(np.linalg.norm(beta))
    if beta_norm < 1e-8:
        pairwise = np.linalg.norm(
            observed_coords[:, None, :] - observed_coords[None, :, :],
            axis=2,
        )
        i, j = np.unravel_index(int(np.argmax(pairwise)), pairwise.shape)
        beta = observed_coords[j] - observed_coords[i]
        beta_norm = float(np.linalg.norm(beta))
    if beta_norm < 1e-8:
        return normalize(coords[:, 0])
    projection = coords @ (beta / beta_norm)
    return normalize(projection.astype(np.float32))


def progress_values_for_event(
    *,
    mode: str,
    coords: np.ndarray,
    spectra: np.ndarray,
    progress: np.ndarray,
    observed: list[int],
) -> np.ndarray:
    if mode == "latent":
        return infer_progress_from_observations(coords=coords, spectra=spectra, observed=observed)
    if mode == "oracle":
        return normalize(progress.astype(np.float32))
    raise ValueError(f"unknown progress mode: {mode}")


def one_dim_inverse_distance_prediction(
    observed_progress: np.ndarray,
    observed_spectra: np.ndarray,
    candidate_progress: float,
) -> np.ndarray:
    distances = np.abs(observed_progress - candidate_progress)
    weights = 1.0 / np.maximum(distances, 1e-6) ** 2.0
    weights = weights / weights.sum()
    return weights @ observed_spectra


def progress_candidate_features(
    *,
    mode: str,
    coords: np.ndarray,
    spectra: np.ndarray,
    progress: np.ndarray,
    observed: list[int],
    candidate: int,
    budget: int,
    max_budget: int,
    max_observed: int,
) -> list[float]:
    z = progress_values_for_event(
        mode=mode,
        coords=coords,
        spectra=spectra,
        progress=progress,
        observed=observed,
    )
    observed_arr = np.asarray(observed, dtype=int)
    observed_z = z[observed_arr]
    observed_spectra = spectra[observed_arr]
    candidate_z = float(z[candidate])
    distances = np.abs(candidate_z - observed_z)
    nearest_idx = int(np.argmin(distances))
    progress_prediction = one_dim_inverse_distance_prediction(
        observed_z,
        observed_spectra,
        candidate_z,
    )
    nearest_spectrum = observed_spectra[nearest_idx]
    observed_mean = observed_spectra.mean(axis=0)
    progress_sorted = np.sort(observed_z)
    if len(progress_sorted) > 1:
        gap_mean = float(np.mean(np.diff(progress_sorted)))
        gap_max = float(np.max(np.diff(progress_sorted)))
    else:
        gap_mean = 0.0
        gap_max = 0.0
    return [
        candidate_z,
        float(len(observed) / max_observed),
        float(budget / max_budget),
        float(distances.min()),
        float(distances.mean()),
        float(distances.max()),
        float(np.mean((progress_prediction - nearest_spectrum) ** 2)),
        float(np.mean((progress_prediction - observed_mean) ** 2)),
        float(np.mean(observed_mean)),
        float(np.std(observed_mean)),
        gap_mean,
        gap_max,
    ]


def build_progress_examples(
    *,
    mode: str,
    event_ids: np.ndarray,
    coords: np.ndarray,
    spectra: np.ndarray,
    progress: np.ndarray,
    train_event_ids: set[str],
    budgets: list[int],
    initial_count: int,
    max_observed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    features = []
    targets = []
    groups = []
    max_budget = max(budgets)
    for event_id in sorted(train_event_ids):
        event_idx = np.flatnonzero(event_ids == event_id)
        event_coords = coords[event_idx]
        event_spectra = spectra[event_idx]
        event_progress = progress[event_idx]
        for budget in budgets:
            observed = NEURAL.farthest_first_indices(event_coords, initial_count).tolist()
            while len(observed) < budget:
                candidates = [idx for idx in range(len(event_idx)) if idx not in observed]
                current_error = NEURAL.reconstruction_error(
                    coords=event_coords,
                    spectra=event_spectra,
                    observed=observed,
                    heldout=candidates,
                )
                candidate_targets = []
                for candidate in candidates:
                    next_observed = [*observed, candidate]
                    next_heldout = [idx for idx in candidates if idx != candidate]
                    next_error = NEURAL.reconstruction_error(
                        coords=event_coords,
                        spectra=event_spectra,
                        observed=next_observed,
                        heldout=next_heldout,
                    )
                    features.append(
                        progress_candidate_features(
                            mode=mode,
                            coords=event_coords,
                            spectra=event_spectra,
                            progress=event_progress,
                            observed=observed,
                            candidate=candidate,
                            budget=budget,
                            max_budget=max_budget,
                            max_observed=max_observed,
                        )
                    )
                    target = current_error - next_error
                    targets.append(target)
                    candidate_targets.append(target)
                    groups.append(event_id)
                observed.append(int(candidates[int(np.argmax(candidate_targets))]))
    return (
        np.asarray(features, dtype=np.float32),
        np.asarray(targets, dtype=np.float32),
        np.asarray(groups),
    )


def train_progress_model(features: np.ndarray, targets: np.ndarray, *, seed: int) -> Any:
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


def target_diagnostic(
    *,
    model: Any,
    train_targets: np.ndarray,
    test_features: np.ndarray,
    test_targets: np.ndarray,
) -> dict[str, float]:
    prediction = model.predict(test_features)
    baseline = np.full_like(test_targets, float(train_targets.mean()))
    baseline_mse = float(np.mean((test_targets - baseline) ** 2))
    model_mse = float(np.mean((test_targets - prediction) ** 2))
    return {
        "target_baseline_mse": baseline_mse,
        "target_model_mse": model_mse,
        "target_mse_improvement": 1.0 - (model_mse / baseline_mse),
    }


def choose_progress_candidate(
    *,
    model: Any,
    mode: str,
    coords: np.ndarray,
    spectra: np.ndarray,
    progress: np.ndarray,
    observed: list[int],
    candidates: list[int],
    budget: int,
    max_budget: int,
    max_observed: int,
) -> int:
    features = [
        progress_candidate_features(
            mode=mode,
            coords=coords,
            spectra=spectra,
            progress=progress,
            observed=observed,
            candidate=candidate,
            budget=budget,
            max_budget=max_budget,
            max_observed=max_observed,
        )
        for candidate in candidates
    ]
    scores = model.predict(np.asarray(features, dtype=np.float32))
    return int(candidates[int(np.argmax(scores))])


def run_progress_loop_for_event(
    *,
    model: Any,
    mode: str,
    coords: np.ndarray,
    spectra: np.ndarray,
    progress: np.ndarray,
    budget: int,
    initial_count: int,
    max_budget: int,
    max_observed: int,
) -> dict[str, Any]:
    observed = NEURAL.farthest_first_indices(coords, initial_count).tolist()
    while len(observed) < budget:
        candidates = [idx for idx in range(len(coords)) if idx not in observed]
        next_idx = choose_progress_candidate(
            model=model,
            mode=mode,
            coords=coords,
            spectra=spectra,
            progress=progress,
            observed=observed,
            candidates=candidates,
            budget=budget,
            max_budget=max_budget,
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


def evaluate_progress_policy(
    *,
    model: Any,
    strategy_name: str,
    mode: str,
    event_ids: np.ndarray,
    coords: np.ndarray,
    spectra: np.ndarray,
    progress: np.ndarray,
    test_event_ids: set[str],
    budgets: list[int],
    initial_count: int,
    max_observed: int,
) -> list[dict[str, Any]]:
    rows = []
    max_budget = max(budgets)
    for budget in budgets:
        event_results = {}
        observed_spectra = []
        for event_id in sorted(test_event_ids):
            event_idx = np.flatnonzero(event_ids == event_id)
            result = run_progress_loop_for_event(
                model=model,
                mode=mode,
                coords=coords[event_idx],
                spectra=spectra[event_idx],
                progress=progress[event_idx],
                budget=budget,
                initial_count=initial_count,
                max_budget=max_budget,
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
                    "strategy": strategy_name,
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
                "event_count": len(group),
                "mse_mean": float(group["mse"].mean()),
                "mse_std": float(group["mse"].std(ddof=0)),
                "improvement_vs_event_mean_mean": float(group["improvement_vs_event_mean"].mean()),
                "improvement_vs_global_mean_mean": float(group["improvement_vs_global_mean"].mean()),
            }
        )
    return summary_rows


def summarize_target_diagnostics(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(diagnostics)
    summary_rows = []
    for (heldout_regime, strategy), group in df.groupby(["heldout_regime", "strategy"], sort=True):
        summary_rows.append(
            {
                "heldout_regime": heldout_regime,
                "strategy": strategy,
                "seed_count": len(group),
                "target_mse_improvement_mean": float(group["target_mse_improvement"].mean()),
                "target_mse_improvement_min": float(group["target_mse_improvement"].min()),
                "target_mse_improvement_max": float(group["target_mse_improvement"].max()),
            }
        )
    return summary_rows


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


def run(args: argparse.Namespace) -> dict[str, Any]:
    seeds = NEURAL.DEFAULT_SEEDS[: args.seed_count]
    max_observed = max(args.budgets) - 1
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
            train_progress = progress_array_for_field(train_field)
            trained_progress = {}
            for strategy_name, mode in [
                ("latent_progress_forest", "latent"),
                ("oracle_progress_forest", "oracle"),
            ]:
                features, targets, groups = build_progress_examples(
                    mode=mode,
                    event_ids=train_field.event_ids,
                    coords=train_field.coords,
                    spectra=train_field.spectra,
                    progress=train_progress,
                    train_event_ids=train_events,
                    budgets=args.budgets,
                    initial_count=args.initial_count,
                    max_observed=max_observed,
                )
                del groups
                trained_progress[strategy_name] = {
                    "mode": mode,
                    "model": train_progress_model(features, targets, seed=seed),
                    "targets": targets,
                    "feature_count": int(features.shape[1]),
                    "training_examples": len(targets),
                }

            coordinate_forest, pca_model = train_coordinate_forest(
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
            test_progress = progress_array_for_field(test_field)

            for strategy_name, bundle in trained_progress.items():
                test_features, test_targets, _ = build_progress_examples(
                    mode=bundle["mode"],
                    event_ids=test_field.event_ids,
                    coords=test_field.coords,
                    spectra=test_field.spectra,
                    progress=test_progress,
                    train_event_ids=test_events,
                    budgets=args.budgets,
                    initial_count=args.initial_count,
                    max_observed=max_observed,
                )
                diagnostics.append(
                    {
                        "seed": seed,
                        "heldout_regime": heldout_regime,
                        "train_regimes": train_regimes,
                        "strategy": strategy_name,
                        "feature_count": bundle["feature_count"],
                        "train_events": len(train_events),
                        "test_events": len(test_events),
                        "training_examples": bundle["training_examples"],
                        "test_target_examples": len(test_targets),
                        **target_diagnostic(
                            model=bundle["model"],
                            train_targets=bundle["targets"],
                            test_features=test_features,
                            test_targets=test_targets,
                        ),
                    }
                )
                progress_rows = evaluate_progress_policy(
                    model=bundle["model"],
                    strategy_name=strategy_name,
                    mode=bundle["mode"],
                    event_ids=test_field.event_ids,
                    coords=test_field.coords,
                    spectra=test_field.spectra,
                    progress=test_progress,
                    test_event_ids=test_events,
                    budgets=args.budgets,
                    initial_count=args.initial_count,
                    max_observed=max_observed,
                )
                for row in progress_rows:
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
                pca_model=pca_model,
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
        "task": "track_b_progress_policy",
        "regime_pool": args.regime_pool,
        "heldout_regimes": args.heldout_regimes,
        "train_events_per_regime": args.train_events_per_regime,
        "test_events": args.test_events,
        "observations_per_event": args.observations_per_event,
        "initial_count": args.initial_count,
        "budgets": args.budgets,
        "seeds": seeds,
        "progress_inference": {
            "latent_progress_forest": "infer a 1D progress coordinate from observed spectral PCA scores regressed on observed coordinates",
            "oracle_progress_forest": "use the synthetic hidden event_progress coordinate as an upper bound",
            "features": [
                "candidate progress",
                "budget/observation state",
                "distance to observed progress coordinates",
                "1D-progress IDW disagreement summaries",
                "observed spectrum mean/std summaries",
                "observed progress gap summaries",
            ],
        },
        "hypotheses": [
            "Oracle progress should improve held-out random_axis and reversed_time acquisition if event progress geometry is useful.",
            "Latent progress should close part of the gap to oracle progress if the hidden progress axis can be inferred from partial raw spectra.",
            "If oracle progress helps but latent progress does not, progress inference is the bottleneck rather than acquisition scoring.",
            "If neither progress policy helps, event progress alone is insufficient under the current reconstruction objective.",
        ],
        "diagnostics": diagnostics,
        "target_summary": summarize_target_diagnostics(diagnostics),
        "rows": rows,
        "summary": summarize(rows),
        "caveats": [
            "This is synthetic and the oracle progress policy uses hidden generator state only as an upper bound.",
            "The latent-progress estimator is deliberately simple and is not yet an end-to-end neural geometry encoder.",
            "The score remains raw held-out measurement reconstruction, not label prediction.",
        ],
    }
    output_path = project_root() / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


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
    parser.add_argument("--pca-components", type=int, default=6)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--test-seed-offset", type=int, default=10000)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/track_b_progress_policy.json"),
    )
    return parser.parse_args()


def main() -> None:
    result = run(parse_args())
    printable = {
        "task": result["task"],
        "hypotheses": result["hypotheses"],
        "progress_inference": result["progress_inference"],
        "target_summary": result["target_summary"],
        "summary": result["summary"],
        "caveats": result["caveats"],
    }
    print(json.dumps(printable, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
