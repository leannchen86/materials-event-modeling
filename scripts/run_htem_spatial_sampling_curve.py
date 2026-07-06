"""Measure how HTEM within-library XRD prediction scales with observation budget."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from run_htem_event_proxy import (
    HTEM_API_BASE_URL,
    build_event_table,
    fetch_properties,
    fetch_records,
    fetch_spectra,
    parse_element_system_filter,
    select_libraries,
)
from run_htem_spatial_field_prediction import (
    ErrorAccumulator,
    coordinate_matrix,
    idw_prediction,
    nearest_prediction,
    ridge_prediction,
)


@dataclass
class BudgetTrial:
    train_count: int
    strategy: str
    repeat: int
    libraries: int = 0
    train_events: int = 0
    test_events: int = 0
    models: dict[str, ErrorAccumulator] = field(default_factory=lambda: defaultdict(ErrorAccumulator))

    def update(self, name: str, truth: np.ndarray, prediction: np.ndarray) -> None:
        self.models[name].update(truth, prediction)

    def metrics(self) -> dict[str, Any]:
        results = {name: accumulator.metrics() for name, accumulator in sorted(self.models.items())}
        global_mse = results["global_observed_mean"]["mse"]
        library_mse = results["observed_library_mean"]["mse"]
        for values in results.values():
            values["relative_mse_vs_global_observed_mean"] = values["mse"] / global_mse
            values["mse_improvement_vs_global_observed_mean"] = 1.0 - values[
                "relative_mse_vs_global_observed_mean"
            ]
            values["relative_mse_vs_observed_library_mean"] = values["mse"] / library_mse
            values["mse_improvement_vs_observed_library_mean"] = 1.0 - values[
                "relative_mse_vs_observed_library_mean"
            ]
        return {
            "train_count": self.train_count,
            "strategy": self.strategy,
            "repeat": self.repeat,
            "libraries": self.libraries,
            "train_events": self.train_events,
            "test_events": self.test_events,
            "models": results,
        }


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def random_train_indices(
    group_indices: np.ndarray,
    train_count: int,
    rng: np.random.Generator,
) -> np.ndarray:
    shuffled = group_indices.copy()
    rng.shuffle(shuffled)
    return np.sort(shuffled[:train_count])


def space_filling_train_indices(
    events: pd.DataFrame,
    group_indices: np.ndarray,
    train_count: int,
) -> np.ndarray:
    coords = coordinate_matrix(events, group_indices)
    center = np.mean(coords, axis=0, keepdims=True)
    first = int(np.argmin(np.linalg.norm(coords - center, axis=1)))
    selected = [first]
    candidates = set(range(group_indices.size))
    candidates.remove(first)

    while len(selected) < train_count and candidates:
        candidate_list = np.array(sorted(candidates), dtype=np.int64)
        candidate_coords = coords[candidate_list]
        selected_coords = coords[np.array(selected)]
        min_distances = np.min(
            np.linalg.norm(candidate_coords[:, None, :] - selected_coords[None, :, :], axis=2),
            axis=1,
        )
        next_local = int(candidate_list[int(np.argmax(min_distances))])
        selected.append(next_local)
        candidates.remove(next_local)

    return np.sort(group_indices[np.array(selected, dtype=np.int64)])


def choose_train_indices(
    events: pd.DataFrame,
    group_indices: np.ndarray,
    *,
    train_count: int,
    strategy: str,
    rng: np.random.Generator,
) -> np.ndarray:
    if strategy == "random":
        return random_train_indices(group_indices, train_count, rng)
    if strategy == "space_filling":
        return space_filling_train_indices(events, group_indices, train_count)
    raise ValueError(f"Unsupported sampling strategy: {strategy}")


def evaluate_trial(
    events: pd.DataFrame,
    xrd: np.ndarray,
    *,
    train_count: int,
    strategy: str,
    repeat: int,
    seed: int,
    idw_power: float,
    ridge_alpha: float,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed + repeat * 7919 + train_count * 313)
    library_splits = {}
    for sample_id, group in events.groupby("sample_library_id", sort=True):
        group_indices = group.index.to_numpy(dtype=np.int64)
        if group_indices.size <= train_count:
            continue
        train_idx = choose_train_indices(
            events,
            group_indices,
            train_count=train_count,
            strategy=strategy,
            rng=rng,
        )
        test_idx = np.setdiff1d(group_indices, train_idx, assume_unique=True)
        library_splits[int(sample_id)] = (train_idx, test_idx)

    train_indices = np.concatenate([train_idx for train_idx, _ in library_splits.values()])
    global_observed_mean = np.mean(xrd[train_indices], axis=0)
    trial = BudgetTrial(train_count=train_count, strategy=strategy, repeat=repeat)
    trial.libraries = len(library_splits)

    for _, (train_idx, test_idx) in sorted(library_splits.items()):
        train_xrd = xrd[train_idx]
        test_xrd = xrd[test_idx]
        train_coords = coordinate_matrix(events, train_idx)
        test_coords = coordinate_matrix(events, test_idx)
        observed_library_mean = np.mean(train_xrd, axis=0)

        predictions = {
            "global_observed_mean": np.repeat(
                global_observed_mean[None, :],
                repeats=test_idx.size,
                axis=0,
            ),
            "observed_library_mean": np.repeat(
                observed_library_mean[None, :],
                repeats=test_idx.size,
                axis=0,
            ),
            "nearest_neighbor": nearest_prediction(train_xrd, train_coords, test_coords),
            "idw_all": idw_prediction(
                train_xrd,
                train_coords,
                test_coords,
                k=None,
                power=idw_power,
            ),
            "xy_ridge_linear": ridge_prediction(
                train_xrd,
                train_coords,
                test_coords,
                degree=1,
                alpha=ridge_alpha,
            ),
        }
        for name, prediction in predictions.items():
            trial.update(name, test_xrd, prediction)
        trial.train_events += int(train_idx.size)
        trial.test_events += int(test_idx.size)

    return trial.metrics()


def summarize(values: list[float]) -> dict[str, float]:
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
    }


def summarize_trials(trials: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for trial in trials:
        grouped[str(trial["train_count"])][trial["strategy"]].append(trial)

    summary = {}
    for train_count, by_strategy in sorted(grouped.items(), key=lambda item: int(item[0])):
        summary[train_count] = {}
        for strategy, strategy_trials in sorted(by_strategy.items()):
            model_names = sorted(strategy_trials[0]["models"])
            summary[train_count][strategy] = {
                "repeats": len(strategy_trials),
                "libraries": summarize([trial["libraries"] for trial in strategy_trials]),
                "train_events": summarize([trial["train_events"] for trial in strategy_trials]),
                "test_events": summarize([trial["test_events"] for trial in strategy_trials]),
                "models": {
                    model_name: {
                        metric_name: summarize(
                            [trial["models"][model_name][metric_name] for trial in strategy_trials]
                        )
                        for metric_name in strategy_trials[0]["models"][model_name]
                    }
                    for model_name in model_names
                },
            }
    return summary


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root()
    cache_dir = root / args.cache_dir
    records = fetch_records(cache_dir=cache_dir, force=args.force_fetch)
    element_system_filter = parse_element_system_filter(args.element_system)
    selected_records = select_libraries(
        records=records,
        max_libraries=args.max_libraries,
        min_xrd_positions=args.min_xrd_positions,
        seed=args.seed,
        element_system_filter=element_system_filter,
    )
    selected_ids = [int(record["id"]) for record in selected_records]
    print(f"selected {len(selected_ids)} HTEM libraries", file=sys.stderr)

    properties = fetch_properties(
        ids=selected_ids,
        cache_dir=cache_dir,
        chunk_size=args.chunk_size,
        force=args.force_fetch,
    )
    spectra = fetch_spectra(
        ids=selected_ids,
        cache_dir=cache_dir,
        chunk_size=args.chunk_size,
        force=args.force_fetch,
    )
    events, xrd, angle = build_event_table(selected_records, properties, spectra)

    trials = []
    for train_count in args.train_counts:
        for strategy in args.strategies:
            repeats = 1 if strategy == "space_filling" else args.repeats
            for repeat in range(repeats):
                print(
                    f"evaluating train_count={train_count} strategy={strategy} repeat={repeat}",
                    file=sys.stderr,
                )
                trials.append(
                    evaluate_trial(
                        events,
                        xrd,
                        train_count=train_count,
                        strategy=strategy,
                        repeat=repeat,
                        seed=args.seed,
                        idw_power=args.idw_power,
                        ridge_alpha=args.ridge_alpha,
                    )
                )

    result = {
        "dataset_id": "htem",
        "task": "within_library_spatial_sampling_budget_curve",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pre_run_hypothesis": (
            "If each HTEM sample library behaves like a spatial measurement field, "
            "prediction of unmeasured positions should improve as the number of observed "
            "positions increases. Space-filling sampling should beat random sampling at "
            "small budgets if spatial coverage matters."
        ),
        "api_base_url": HTEM_API_BASE_URL,
        "element_system_filter": element_system_filter,
        "selected_library_count": len(selected_ids),
        "selected_library_ids": selected_ids,
        "event_count": len(events),
        "xrd_points": int(xrd.shape[1]),
        "angle_min": float(np.min(angle)),
        "angle_max": float(np.max(angle)),
        "normalization": "log1p(nonnegative intensity), then per-spectrum max normalization.",
        "train_counts": args.train_counts,
        "strategies": args.strategies,
        "repeats": args.repeats,
        "idw_power": args.idw_power,
        "ridge_alpha": args.ridge_alpha,
        "summary": summarize_trials(trials),
        "trials": trials,
        "caveats": [
            "This is within-library partial-observation prediction, not unseen-library transfer.",
            "Space-filling is deterministic and therefore has one repeat.",
            "Random strategy means and standard deviations are over repeated random observed-position sets.",
            "The result is a measurement-budget design probe for Track B, not a materials discovery benchmark.",
        ],
    }

    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--element-system", default="Cu,S,Sn")
    parser.add_argument("--max-libraries", type=int, default=65)
    parser.add_argument("--min-xrd-positions", type=int, default=40)
    parser.add_argument("--chunk-size", type=int, default=5)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--train-counts", nargs="+", type=int, default=[4, 8, 12, 16, 24, 32])
    parser.add_argument("--strategies", nargs="+", default=["random", "space_filling"])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--idw-power", type=float, default=2.0)
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    parser.add_argument("--force-fetch", action="store_true")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("data/interim/htem_event_proxy"),
        help="Local cache for HTEM API responses.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/htem_spatial_sampling_curve_cu_s_sn.json"),
    )
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
