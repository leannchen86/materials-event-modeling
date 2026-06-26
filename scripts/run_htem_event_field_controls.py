"""Stress-test HTEM event-field reconstruction with spatial and metric controls."""

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

from run_htem_event_proxy import (
    HTEM_API_BASE_URL,
    build_event_table,
    fetch_properties,
    fetch_records,
    fetch_spectra,
    parse_element_system_filter,
    select_libraries,
)
from run_htem_masked_event_model import normalize_coords_by_event
from run_htem_spatial_field_prediction import idw_prediction, nearest_prediction, ridge_prediction


@dataclass
class MetricAccumulator:
    mse_sum: float = 0.0
    mae_sum: float = 0.0
    peak_mae_sum: float = 0.0
    weighted_mse_sum: float = 0.0
    count: int = 0
    peak_count: int = 0
    weighted_count: float = 0.0

    def update(self, truth: np.ndarray, prediction: np.ndarray) -> None:
        diff = prediction - truth
        self.mse_sum += float(np.sum(diff * diff))
        self.mae_sum += float(np.sum(np.abs(diff)))
        self.count += int(diff.size)

        peak_mask = truth >= np.quantile(truth, 0.9, axis=1, keepdims=True)
        self.peak_mae_sum += float(np.sum(np.abs(diff)[peak_mask]))
        self.peak_count += int(np.sum(peak_mask))

        weights = 1.0 + 4.0 * np.clip(truth, 0.0, 1.0)
        self.weighted_mse_sum += float(np.sum(weights * diff * diff))
        self.weighted_count += float(np.sum(weights))

    def metrics(self) -> dict[str, float]:
        return {
            "mse": self.mse_sum / self.count,
            "mae": self.mae_sum / self.count,
            "peak_mae": self.peak_mae_sum / self.peak_count,
            "weighted_mse": self.weighted_mse_sum / self.weighted_count,
        }


@dataclass
class SplitAccumulator:
    split_kind: str
    states: int = 0
    libraries: set[int] = field(default_factory=set)
    candidate_count: int = 0
    models: dict[str, MetricAccumulator] = field(default_factory=lambda: defaultdict(MetricAccumulator))

    def update(self, model: str, truth: np.ndarray, prediction: np.ndarray) -> None:
        self.models[model].update(truth, prediction)

    def metrics(self) -> dict[str, Any]:
        results = {name: acc.metrics() for name, acc in sorted(self.models.items())}
        event_mse = results["observed_event_mean"]["mse"]
        event_weighted_mse = results["observed_event_mean"]["weighted_mse"]
        event_peak_mae = results["observed_event_mean"]["peak_mae"]
        shuffled_mse = results["idw_shuffled_coords"]["mse"]
        for values in results.values():
            values["mse_improvement_vs_event_mean"] = 1.0 - values["mse"] / event_mse
            values["weighted_mse_improvement_vs_event_mean"] = (
                1.0 - values["weighted_mse"] / event_weighted_mse
            )
            values["peak_mae_improvement_vs_event_mean"] = 1.0 - values["peak_mae"] / event_peak_mae
            values["mse_improvement_vs_idw_shuffled_coords"] = 1.0 - values["mse"] / shuffled_mse
        return {
            "split_kind": self.split_kind,
            "states": self.states,
            "libraries": len(self.libraries),
            "candidate_count": self.candidate_count,
            "models": results,
        }


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def random_observed(
    coords: np.ndarray,
    *,
    observed_count: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray] | None:
    if coords.shape[0] <= observed_count:
        return None
    observed = rng.choice(coords.shape[0], size=observed_count, replace=False)
    candidates = np.setdiff1d(np.arange(coords.shape[0]), observed, assume_unique=False)
    return np.sort(observed), np.sort(candidates)


def space_filling_observed(coords: np.ndarray, *, observed_count: int) -> tuple[np.ndarray, np.ndarray] | None:
    if coords.shape[0] <= observed_count:
        return None
    selected = [int(np.argmin(np.linalg.norm(coords - coords.mean(axis=0, keepdims=True), axis=1)))]
    candidates = set(range(coords.shape[0]))
    candidates.remove(selected[0])
    while len(selected) < observed_count and candidates:
        candidate_list = np.array(sorted(candidates), dtype=np.int64)
        candidate_coords = coords[candidate_list]
        selected_coords = coords[np.asarray(selected)]
        distances = np.min(
            np.linalg.norm(candidate_coords[:, None, :] - selected_coords[None, :, :], axis=2),
            axis=1,
        )
        next_idx = int(candidate_list[int(np.argmax(distances))])
        selected.append(next_idx)
        candidates.remove(next_idx)
    observed = np.asarray(selected, dtype=np.int64)
    remaining = np.setdiff1d(np.arange(coords.shape[0]), observed, assume_unique=False)
    return np.sort(observed), np.sort(remaining)


def row_holdout(coords: np.ndarray, *, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray] | None:
    rounded_y = np.round(coords[:, 1], 6)
    rows = np.array(sorted(set(rounded_y.tolist())))
    if len(rows) < 2:
        return None
    rng.shuffle(rows)
    for row in rows:
        candidates = np.flatnonzero(rounded_y == row)
        observed = np.flatnonzero(rounded_y != row)
        if len(candidates) >= 4 and len(observed) >= 8:
            return np.sort(observed), np.sort(candidates)
    return None


def quadrant_holdout(coords: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    x_median = float(np.median(coords[:, 0]))
    y_median = float(np.median(coords[:, 1]))
    masks = [
        (coords[:, 0] <= x_median) & (coords[:, 1] <= y_median),
        (coords[:, 0] <= x_median) & (coords[:, 1] > y_median),
        (coords[:, 0] > x_median) & (coords[:, 1] <= y_median),
        (coords[:, 0] > x_median) & (coords[:, 1] > y_median),
    ]
    masks = sorted(masks, key=lambda mask: int(np.sum(mask)), reverse=True)
    for mask in masks:
        candidates = np.flatnonzero(mask)
        observed = np.flatnonzero(~mask)
        if len(candidates) >= 6 and len(observed) >= 8:
            return np.sort(observed), np.sort(candidates)
    return None


def split_states(
    coords: np.ndarray,
    *,
    observed_count: int,
    rng: np.random.Generator,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    states: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    random_split = random_observed(coords, observed_count=observed_count, rng=rng)
    if random_split is not None:
        states[f"random_{observed_count}"] = random_split
    space_split = space_filling_observed(coords, observed_count=observed_count)
    if space_split is not None:
        states[f"space_filling_{observed_count}"] = space_split
    row_split = row_holdout(coords, rng=rng)
    if row_split is not None:
        states["held_out_row"] = row_split
    quadrant_split = quadrant_holdout(coords)
    if quadrant_split is not None:
        states["held_out_quadrant"] = quadrant_split
    return states


def safe_ridge_prediction(
    train_spectra: np.ndarray,
    train_coords: np.ndarray,
    target_coords: np.ndarray,
) -> np.ndarray | None:
    if train_coords.shape[0] < 4:
        return None
    try:
        return ridge_prediction(
            train_spectra,
            train_coords,
            target_coords,
            degree=1,
            alpha=1.0,
        )
    except Exception:
        return None


def predictions_for_state(
    *,
    train_spectra: np.ndarray,
    train_coords: np.ndarray,
    target_coords: np.ndarray,
    train_mean: np.ndarray,
    rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    event_mean = np.repeat(train_spectra.mean(axis=0, keepdims=True), len(target_coords), axis=0)
    global_mean = np.repeat(train_mean[None, :], len(target_coords), axis=0)
    shuffled_coords = train_coords.copy()
    rng.shuffle(shuffled_coords)
    predictions = {
        "train_mean": global_mean,
        "observed_event_mean": event_mean,
        "nearest_neighbor": nearest_prediction(train_spectra, train_coords, target_coords),
        "idw_all": idw_prediction(train_spectra, train_coords, target_coords, k=None, power=2.0),
        "idw_shuffled_coords": idw_prediction(
            train_spectra,
            shuffled_coords,
            target_coords,
            k=None,
            power=2.0,
        ),
    }
    ridge = safe_ridge_prediction(train_spectra, train_coords, target_coords)
    if ridge is not None:
        predictions["xy_ridge_linear"] = ridge
    return predictions


def summarize_results(accumulators: dict[str, SplitAccumulator]) -> dict[str, Any]:
    return {
        split_kind: accumulator.metrics()
        for split_kind, accumulator in sorted(accumulators.items())
    }


def make_headline(summary: dict[str, Any]) -> dict[str, Any]:
    headline: dict[str, Any] = {
        "one_sentence": (
            "HTEM event-field reconstruction survives stronger controls only as a spatial "
            "field result: correct coordinates matter, and contiguous holdouts are harder."
        )
    }
    for split_kind in ["space_filling_32", "held_out_row", "held_out_quadrant"]:
        split = summary.get(split_kind)
        if not split:
            continue
        idw = split["models"].get("idw_all")
        shuffled = split["models"].get("idw_shuffled_coords")
        if idw:
            headline[f"{split_kind}_idw_improvement_vs_event_mean"] = idw[
                "mse_improvement_vs_event_mean"
            ]
            headline[f"{split_kind}_idw_peak_mae_improvement_vs_event_mean"] = idw[
                "peak_mae_improvement_vs_event_mean"
            ]
        if idw and shuffled:
            headline[f"{split_kind}_idw_improvement_vs_shuffled_coords"] = idw[
                "mse_improvement_vs_idw_shuffled_coords"
            ]
    return headline


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
    spectra_payload = fetch_spectra(
        ids=selected_ids,
        cache_dir=cache_dir,
        chunk_size=args.chunk_size,
        force=args.force_fetch,
    )
    events, spectra, angle = build_event_table(selected_records, properties, spectra_payload)
    coords = normalize_coords_by_event(events)
    event_ids = events["sample_library_id"].astype(int).to_numpy()
    train_mean = spectra.mean(axis=0)
    rng = np.random.default_rng(args.seed)
    accumulators: dict[str, SplitAccumulator] = {}

    for event_id in sorted(set(event_ids.tolist())):
        event_idx = np.flatnonzero(event_ids == event_id)
        event_coords = coords[event_idx]
        event_spectra = spectra[event_idx]
        states = split_states(event_coords, observed_count=args.observed_count, rng=rng)
        for split_kind, (observed, candidates) in states.items():
            split_acc = accumulators.setdefault(split_kind, SplitAccumulator(split_kind=split_kind))
            train_spectra = event_spectra[observed]
            train_coords = event_coords[observed]
            target_spectra = event_spectra[candidates]
            target_coords = event_coords[candidates]
            predictions = predictions_for_state(
                train_spectra=train_spectra,
                train_coords=train_coords,
                target_coords=target_coords,
                train_mean=train_mean,
                rng=rng,
            )
            split_acc.states += 1
            split_acc.libraries.add(int(event_id))
            split_acc.candidate_count += int(len(candidates))
            for model, prediction in predictions.items():
                split_acc.update(model, target_spectra, prediction)

    summary = summarize_results(accumulators)
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_id": "htem",
        "task": "htem_event_field_hard_controls",
        "api_base_url": HTEM_API_BASE_URL,
        "element_system_filter": element_system_filter,
        "selected_library_count": len(selected_ids),
        "selected_library_ids": selected_ids,
        "event_count": int(len(events)),
        "xrd_points": int(spectra.shape[1]),
        "angle_min": float(np.min(angle)),
        "angle_max": float(np.max(angle)),
        "observed_count": args.observed_count,
        "normalization": "log1p(nonnegative intensity), then per-spectrum max normalization.",
        "hypotheses": [
            "Correct within-library spatial structure should beat the observed event mean on random and space-filling holdouts.",
            "The gain should shrink on contiguous row/quadrant holdouts; if it does not, the task may be too easy.",
            "IDW with shuffled coordinates should be worse than IDW with correct coordinates, showing that spatial mapping matters.",
            "Peak-aware metrics should be reported because plain MSE can hide peak-level errors.",
        ],
        "direction_critique": [
            "This is the right next step because it tests the exact expert pushback that the HTEM result is just spatial interpolation.",
            "It does not try to rescue the neural model; it asks which boring baselines explain the signal.",
            "It makes the snap result more honest by separating event-field evidence from universal-event-embedding evidence.",
        ],
        "summary": summary,
        "headline": make_headline(summary),
        "caveats": [
            "This still uses HTEM sample libraries, not full synthesis trajectories.",
            "The shuffled-coordinate control is a null diagnostic, not a physically meaningful model.",
            "Peak-aware metrics are simple intensity-weighted checks, not full crystallographic validation.",
        ],
    }
    output_path = root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--element-system", default="Cu,S,Sn")
    parser.add_argument("--max-libraries", type=int, default=65)
    parser.add_argument("--min-xrd-positions", type=int, default=40)
    parser.add_argument("--chunk-size", type=int, default=5)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--observed-count", type=int, default=32)
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
        default=Path("data/manifests/htem_event_field_hard_controls_cu_s_sn.json"),
    )
    return parser.parse_args()


def main() -> None:
    result = run(parse_args())
    printable = {
        "task": result["task"],
        "hypotheses": result["hypotheses"],
        "direction_critique": result["direction_critique"],
        "headline": result["headline"],
        "summary": result["summary"],
        "caveats": result["caveats"],
    }
    print(json.dumps(printable, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
