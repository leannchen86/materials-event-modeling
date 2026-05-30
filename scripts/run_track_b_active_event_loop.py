"""Prototype an active event-learning loop on synthetic Track B event fields.

The loop does not use phase labels. It starts from a tiny set of raw observations inside
each event, chooses the next observation, and is scored by how well the remaining raw
measurements can be reconstructed.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from materials_event_modeling.track_b.field_prediction import (
    farthest_first_indices,
    inverse_distance_prediction,
    mean_squared_error,
)
from materials_event_modeling.track_b.synthetic_field import generate_synthetic_event_field


DEFAULT_SEEDS = [17, 29, 41, 53, 67]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def event_reconstruction_error(
    *,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed_idx: np.ndarray,
    target_idx: np.ndarray,
) -> float:
    if len(target_idx) == 0:
        return 0.0
    prediction = inverse_distance_prediction(
        coords[observed_idx],
        spectra[observed_idx],
        coords[target_idx],
    )
    return mean_squared_error(spectra[target_idx], prediction)


def choose_candidate(
    *,
    strategy: str,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed: list[int],
    candidates: list[int],
    rng: np.random.Generator,
) -> int:
    if strategy == "random":
        return int(rng.choice(candidates))

    observed_arr = np.array(observed, dtype=int)
    candidate_arr = np.array(candidates, dtype=int)

    if strategy == "space_filling":
        distances = np.linalg.norm(
            coords[candidate_arr, None, :] - coords[observed_arr][None, :, :],
            axis=2,
        )
        min_distance = distances.min(axis=1)
        return int(candidate_arr[np.argmax(min_distance)])

    if strategy == "oracle_best":
        remaining_all = np.array(candidates, dtype=int)
        best_idx = None
        best_error = np.inf
        for candidate in candidates:
            next_observed = np.array([*observed, candidate], dtype=int)
            next_remaining = np.array(
                [idx for idx in remaining_all.tolist() if idx != candidate],
                dtype=int,
            )
            error = event_reconstruction_error(
                coords=coords,
                spectra=spectra,
                observed_idx=next_observed,
                target_idx=next_remaining,
            )
            if error < best_error:
                best_error = error
                best_idx = candidate
        assert best_idx is not None
        return int(best_idx)

    if strategy in {"active_error", "active_hybrid"}:
        prediction = inverse_distance_prediction(
            coords[observed_arr],
            spectra[observed_arr],
            coords[candidate_arr],
        )
        distances = np.linalg.norm(
            coords[candidate_arr, None, :] - coords[observed_arr][None, :, :],
            axis=2,
        )
        min_distance = distances.min(axis=1)
        nearest_spectra = spectra[observed_arr[np.argmin(distances, axis=1)]]
        predicted_residual = np.mean((prediction - nearest_spectra) ** 2, axis=1)
        if strategy == "active_error":
            score = predicted_residual
        else:
            score = predicted_residual * (min_distance + 1e-6)
        return int(candidate_arr[np.argmax(score)])

    raise ValueError(f"unknown strategy: {strategy}")


def run_event_loop(
    *,
    coords: np.ndarray,
    spectra: np.ndarray,
    budget: int,
    initial_count: int,
    strategy: str,
    rng: np.random.Generator,
) -> dict[str, Any]:
    if initial_count >= budget:
        raise ValueError("initial_count must be smaller than budget")
    if budget >= len(coords):
        raise ValueError("budget must be smaller than the number of observations")

    initial = farthest_first_indices(coords, initial_count).tolist()
    observed = [int(idx) for idx in initial]
    trajectory = []

    while len(observed) < budget:
        candidates = [idx for idx in range(len(coords)) if idx not in observed]
        heldout = np.array(candidates, dtype=int)
        current_error = event_reconstruction_error(
            coords=coords,
            spectra=spectra,
            observed_idx=np.array(observed, dtype=int),
            target_idx=heldout,
        )
        next_idx = choose_candidate(
            strategy=strategy,
            coords=coords,
            spectra=spectra,
            observed=observed,
            candidates=candidates,
            rng=rng,
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

    remaining = np.array([idx for idx in range(len(coords)) if idx not in observed], dtype=int)
    final_mse = event_reconstruction_error(
        coords=coords,
        spectra=spectra,
        observed_idx=np.array(observed, dtype=int),
        target_idx=remaining,
    )
    return {
        "observed_indices": observed,
        "final_mse": final_mse,
        "trajectory": trajectory,
    }


def global_mean_mse_for_budget(
    *,
    all_observed_spectra: list[np.ndarray],
    event_spectra: np.ndarray,
    heldout_idx: np.ndarray,
) -> float:
    global_mean = np.vstack(all_observed_spectra).mean(axis=0)
    prediction = np.tile(global_mean, (len(heldout_idx), 1))
    return mean_squared_error(event_spectra[heldout_idx], prediction)


def run_strategy(
    *,
    strategy: str,
    event_ids: np.ndarray,
    coords: np.ndarray,
    spectra: np.ndarray,
    budget: int,
    initial_count: int,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    rows = []
    observed_spectra_by_event = []
    unique_events = np.array(sorted(set(event_ids.tolist())))

    per_event_results = {}
    for event_id in unique_events:
        event_idx = np.flatnonzero(event_ids == event_id)
        result = run_event_loop(
            coords=coords[event_idx],
            spectra=spectra[event_idx],
            budget=budget,
            initial_count=initial_count,
            strategy=strategy,
            rng=rng,
        )
        observed_global_idx = event_idx[np.array(result["observed_indices"], dtype=int)]
        heldout_global_idx = np.setdiff1d(event_idx, observed_global_idx, assume_unique=False)
        observed_spectra_by_event.append(spectra[observed_global_idx])
        per_event_results[str(event_id)] = {
            "event_mse": result["final_mse"],
            "heldout_indices": heldout_global_idx.tolist(),
            "observed_indices": observed_global_idx.tolist(),
            "trajectory": result["trajectory"],
        }

    all_observed = list(observed_spectra_by_event)
    for event_id in unique_events:
        event_idx = np.flatnonzero(event_ids == event_id)
        event_result = per_event_results[str(event_id)]
        heldout_idx = np.array(event_result["heldout_indices"], dtype=int)
        event_mean = spectra[np.array(event_result["observed_indices"], dtype=int)].mean(axis=0)
        event_mean_prediction = np.tile(event_mean, (len(heldout_idx), 1))
        event_mean_mse = mean_squared_error(spectra[heldout_idx], event_mean_prediction)
        global_mse = global_mean_mse_for_budget(
            all_observed_spectra=all_observed,
            event_spectra=spectra,
            heldout_idx=heldout_idx,
        )
        rows.append(
            {
                "event_id": str(event_id),
                "strategy": strategy,
                "budget": budget,
                "initial_count": initial_count,
                "mse": event_result["event_mse"],
                "event_mean_mse": event_mean_mse,
                "global_mean_mse": global_mse,
                "improvement_vs_event_mean": 1.0 - (event_result["event_mse"] / event_mean_mse),
                "improvement_vs_global_mean": 1.0 - (event_result["event_mse"] / global_mse),
            }
        )

    return {
        "strategy": strategy,
        "rows": rows,
        "per_event_results": per_event_results,
    }


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    summary_rows = []
    for (strategy, budget), group in df.groupby(["strategy", "budget"], sort=True):
        summary_rows.append(
            {
                "strategy": strategy,
                "budget": int(budget),
                "event_count": int(len(group)),
                "mse_mean": float(group["mse"].mean()),
                "mse_std": float(group["mse"].std(ddof=0)),
                "improvement_vs_event_mean_mean": float(group["improvement_vs_event_mean"].mean()),
                "improvement_vs_event_mean_std": float(group["improvement_vs_event_mean"].std(ddof=0)),
                "improvement_vs_global_mean_mean": float(group["improvement_vs_global_mean"].mean()),
                "improvement_vs_global_mean_std": float(group["improvement_vs_global_mean"].std(ddof=0)),
            }
        )
    return summary_rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    all_rows = []
    all_runs = []
    seeds = DEFAULT_SEEDS[: args.seed_count]
    strategies = ["random", "space_filling", "active_error", "active_hybrid", "oracle_best"]

    for seed in seeds:
        field = generate_synthetic_event_field(
            n_events=args.events,
            observations_per_event=args.observations_per_event,
            n_theta=args.theta_points,
            seed=seed,
        )
        for budget in args.budgets:
            for strategy in strategies:
                result = run_strategy(
                    strategy=strategy,
                    event_ids=field.event_ids,
                    coords=field.coords,
                    spectra=field.spectra,
                    budget=budget,
                    initial_count=args.initial_count,
                    seed=seed + budget * 100,
                )
                for row in result["rows"]:
                    row["seed"] = seed
                    all_rows.append(row)
                all_runs.append(
                    {
                        "seed": seed,
                        "budget": budget,
                        "strategy": strategy,
                        "per_event_results": result["per_event_results"],
                    }
                )

    summary = summarize(all_rows)
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "track_b_active_event_learning_loop",
        "events": args.events,
        "observations_per_event": args.observations_per_event,
        "theta_points": args.theta_points,
        "initial_count": args.initial_count,
        "budgets": args.budgets,
        "seeds": seeds,
        "strategies": strategies,
        "hypotheses": [
            "Active selection should improve missing-measurement reconstruction versus random selection at small budgets.",
            "Coverage-aware active selection should be competitive with static space-filling selection.",
            "The oracle-best strategy should define the current upper bound for this synthetic event field.",
        ],
        "rows": all_rows,
        "summary": summary,
        "runs": all_runs[: args.saved_run_limit],
        "caveats": [
            "This is a synthetic event field; the active policy is a scaffold, not chemistry evidence.",
            "The current active policies use heuristic uncertainty/error scores, not a learned decision policy.",
            "The objective is raw measurement reconstruction, not phase-label or success-label optimization.",
        ],
    }

    output_path = project_root() / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=int, default=24)
    parser.add_argument("--observations-per-event", type=int, default=12)
    parser.add_argument("--theta-points", type=int, default=512)
    parser.add_argument("--initial-count", type=int, default=2)
    parser.add_argument("--budgets", type=int, nargs="+", default=[3, 4, 6, 8])
    parser.add_argument("--seed-count", type=int, default=len(DEFAULT_SEEDS))
    parser.add_argument("--saved-run-limit", type=int, default=4)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/track_b_active_event_learning_loop.json"),
    )
    return parser.parse_args()


def main() -> None:
    result = run(parse_args())
    printable = {
        "task": result["task"],
        "hypotheses": result["hypotheses"],
        "summary": result["summary"],
        "caveats": result["caveats"],
    }
    print(json.dumps(printable, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
