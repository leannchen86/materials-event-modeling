"""Run masked-event reconstruction on HTEM within-library XRD fields."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from run_htem_event_proxy import (
    HTEM_API_BASE_URL,
    build_event_table,
    fetch_properties,
    fetch_records,
    fetch_spectra,
    parse_element_system_filter,
    select_libraries,
)
from run_htem_spatial_field_prediction import idw_prediction, nearest_prediction, ridge_prediction
from run_track_b_masked_event_model import (
    NEURAL,
    ablate_examples,
    build_masked_examples,
    collect_target_signals,
    predict_targets,
    single_state_examples,
    train_masked_model,
    variant_target_mode,
)


DEFAULT_VARIANTS = ["raw_set", "coord_only", "raw_residual"]


@dataclass
class TrainedBundle:
    variant: str
    target_mode: str
    pca_model: PCA
    model: Any
    target_mean: np.ndarray
    target_std: np.ndarray


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize_coords_by_event(events: pd.DataFrame) -> np.ndarray:
    coords = events[["x_mm", "y_mm"]].to_numpy(dtype=np.float32)
    normalized = np.zeros_like(coords)
    for _, group in events.groupby("sample_library_id", sort=True):
        idx = group.index.to_numpy(dtype=np.int64)
        event_coords = coords[idx]
        center = np.nanmean(event_coords, axis=0, keepdims=True)
        scale = np.nanstd(event_coords, axis=0, keepdims=True)
        scale = np.maximum(scale, 1e-6)
        normalized[idx] = np.nan_to_num((event_coords - center) / scale, nan=0.0)
    return normalized.astype(np.float32)


def split_event_ids(event_ids: np.ndarray, *, n_folds: int, seed: int) -> list[set[str]]:
    unique_ids = np.asarray(sorted(set(event_ids.tolist())))
    rng = np.random.default_rng(seed)
    rng.shuffle(unique_ids)
    folds = np.array_split(unique_ids, n_folds)
    return [set(fold.tolist()) for fold in folds if len(fold)]


def observed_indices_for_state(
    *,
    coords: np.ndarray,
    observed_count: int,
    strategy: str,
    rng: np.random.Generator,
) -> list[int]:
    if observed_count >= len(coords):
        return list(range(len(coords)))
    if strategy == "space_filling":
        return NEURAL.farthest_first_indices(coords, observed_count).tolist()
    if strategy == "random":
        return rng.choice(len(coords), size=observed_count, replace=False).astype(int).tolist()
    raise ValueError(f"unknown strategy: {strategy}")


def mse(truth: np.ndarray, prediction: np.ndarray) -> float:
    diff = prediction - truth
    return float(np.mean(diff * diff))


def mae(truth: np.ndarray, prediction: np.ndarray) -> float:
    return float(np.mean(np.abs(prediction - truth)))


def make_pca_by_target_mode(
    *,
    event_ids: np.ndarray,
    coords: np.ndarray,
    spectra: np.ndarray,
    train_event_ids: set[str],
    observed_counts: list[int],
    seed: int,
    random_repeats: int,
    pca_components: int,
) -> dict[str, PCA]:
    train_mask = np.asarray([event_id in train_event_ids for event_id in event_ids])
    train_spectra = spectra[train_mask]
    spectrum_components = min(pca_components, train_spectra.shape[0] - 1, train_spectra.shape[1])
    spectrum_pca = PCA(n_components=spectrum_components, random_state=seed)
    spectrum_pca.fit(train_spectra)

    residual_signals = collect_target_signals(
        event_ids=event_ids,
        coords=coords,
        spectra=spectra,
        selected_event_ids=train_event_ids,
        observed_counts=observed_counts,
        seed=seed,
        random_repeats=random_repeats,
        target_mode="idw_residual",
    )
    residual_components = min(pca_components, residual_signals.shape[0] - 1, residual_signals.shape[1])
    residual_pca = PCA(n_components=residual_components, random_state=seed)
    residual_pca.fit(residual_signals)
    return {"spectrum": spectrum_pca, "idw_residual": residual_pca}


def train_variant(
    *,
    variant: str,
    event_ids: np.ndarray,
    coords: np.ndarray,
    spectra: np.ndarray,
    train_event_ids: set[str],
    test_event_ids: set[str],
    pca_model: PCA,
    observed_counts: list[int],
    max_observed: int,
    seed: int,
    train_random_repeats: int,
    device: Any,
    epochs: int,
    batch_size: int,
    learning_rate: float,
) -> tuple[TrainedBundle, dict[str, Any]]:
    target_mode = variant_target_mode(variant)
    train_examples = build_masked_examples(
        event_ids=event_ids,
        coords=coords,
        spectra=spectra,
        selected_event_ids=train_event_ids,
        pca_model=pca_model,
        observed_counts=observed_counts,
        max_observed=max_observed,
        seed=seed,
        random_repeats=train_random_repeats,
        target_mode=target_mode,
    )
    test_examples = build_masked_examples(
        event_ids=event_ids,
        coords=coords,
        spectra=spectra,
        selected_event_ids=test_event_ids,
        pca_model=pca_model,
        observed_counts=observed_counts,
        max_observed=max_observed,
        seed=seed + 1009,
        random_repeats=1,
        target_mode=target_mode,
    )
    train_examples = ablate_examples(train_examples, variant=variant)
    test_examples = ablate_examples(test_examples, variant=variant)
    model, target_mean, target_std, diagnostics = train_masked_model(
        train_examples=train_examples,
        test_examples=test_examples,
        n_theta=spectra.shape[1],
        target_dim=pca_model.n_components_,
        max_observed=max_observed,
        seed=seed,
        device=device,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
    )
    bundle = TrainedBundle(
        variant=variant,
        target_mode=target_mode,
        pca_model=pca_model,
        model=model,
        target_mean=target_mean,
        target_std=target_std,
    )
    return bundle, {
        "variant": variant,
        "target_mode": target_mode,
        "training_examples": int(len(train_examples.targets)),
        "test_examples": int(len(test_examples.targets)),
        **diagnostics,
    }


def predict_bundle(
    *,
    bundle: TrainedBundle,
    event_coords: np.ndarray,
    event_spectra: np.ndarray,
    observed: list[int],
    candidates: list[int],
    idw_baseline: np.ndarray,
    max_observed: int,
    device: Any,
) -> np.ndarray:
    examples = single_state_examples(
        coords=event_coords,
        spectra=event_spectra,
        observed=observed,
        candidates=candidates,
        pca_model=bundle.pca_model,
        max_observed=max_observed,
        target_mode=bundle.target_mode,
    )
    examples = ablate_examples(examples, variant=bundle.variant)
    pca_prediction = predict_targets(
        model=bundle.model,
        examples=examples,
        target_mean=bundle.target_mean,
        target_std=bundle.target_std,
        device=device,
    )
    signal = bundle.pca_model.inverse_transform(pca_prediction)
    if bundle.target_mode == "idw_residual":
        return idw_baseline + signal
    return signal


def evaluate_fold(
    *,
    fold: int,
    event_ids: np.ndarray,
    coords: np.ndarray,
    spectra: np.ndarray,
    train_event_ids: set[str],
    test_event_ids: set[str],
    bundles: dict[str, TrainedBundle],
    observed_counts: list[int],
    eval_random_repeats: int,
    max_observed: int,
    seed: int,
    device: Any,
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed + fold * 997)
    train_mask = np.asarray([event_id in train_event_ids for event_id in event_ids])
    train_mean = spectra[train_mask].mean(axis=0)
    rows = []
    for event_id in sorted(test_event_ids):
        event_idx = np.flatnonzero(event_ids == event_id)
        event_coords = coords[event_idx]
        event_spectra = spectra[event_idx]
        for observed_count in observed_counts:
            states = [("space_filling", 0), *[("random", repeat) for repeat in range(eval_random_repeats)]]
            for strategy, repeat in states:
                observed = observed_indices_for_state(
                    coords=event_coords,
                    observed_count=observed_count,
                    strategy=strategy,
                    rng=rng,
                )
                candidates = [idx for idx in range(len(event_idx)) if idx not in observed]
                if not candidates:
                    continue
                observed_arr = np.asarray(observed, dtype=np.int64)
                candidate_arr = np.asarray(candidates, dtype=np.int64)
                truth = event_spectra[candidate_arr]
                observed_spectra = event_spectra[observed_arr]
                observed_coords = event_coords[observed_arr]
                candidate_coords = event_coords[candidate_arr]
                event_mean = np.repeat(observed_spectra.mean(axis=0, keepdims=True), len(candidates), axis=0)
                global_mean = np.repeat(train_mean[None, :], len(candidates), axis=0)
                idw_all = idw_prediction(
                    observed_spectra,
                    observed_coords,
                    candidate_coords,
                    k=None,
                    power=2.0,
                )
                predictions: dict[str, np.ndarray] = {
                    "train_mean": global_mean,
                    "observed_event_mean": event_mean,
                    "nearest_neighbor": nearest_prediction(observed_spectra, observed_coords, candidate_coords),
                    "idw_all": idw_all,
                }
                ridge = ridge_prediction(
                    observed_spectra,
                    observed_coords,
                    candidate_coords,
                    degree=1,
                    alpha=1.0,
                )
                predictions["xy_ridge_linear"] = ridge
                for variant, bundle in bundles.items():
                    predictions[f"masked_event_{variant}"] = predict_bundle(
                        bundle=bundle,
                        event_coords=event_coords,
                        event_spectra=event_spectra,
                        observed=observed,
                        candidates=candidates,
                        idw_baseline=idw_all,
                        max_observed=max_observed,
                        device=device,
                    )

                train_mean_mse = mse(truth, global_mean)
                event_mean_mse = mse(truth, event_mean)
                idw_mse = mse(truth, idw_all)
                for model_name, prediction in predictions.items():
                    model_mse = mse(truth, prediction)
                    rows.append(
                        {
                            "fold": fold,
                            "event_id": event_id,
                            "observed_count": observed_count,
                            "strategy": strategy,
                            "repeat": repeat,
                            "candidate_count": len(candidates),
                            "model": model_name,
                            "mse": model_mse,
                            "mae": mae(truth, prediction),
                            "train_mean_mse": train_mean_mse,
                            "event_mean_mse": event_mean_mse,
                            "idw_mse": idw_mse,
                            "improvement_vs_train_mean": 1.0 - model_mse / train_mean_mse,
                            "improvement_vs_event_mean": 1.0 - model_mse / event_mean_mse,
                            "improvement_vs_idw": 1.0 - model_mse / idw_mse,
                        }
                    )
    return rows


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frame = pd.DataFrame(rows)
    summary = []
    for (observed_count, strategy, model), group in frame.groupby(
        ["observed_count", "strategy", "model"], sort=True
    ):
        summary.append(
            {
                "observed_count": int(observed_count),
                "strategy": strategy,
                "model": model,
                "state_count": int(len(group)),
                "mse_mean": float(group["mse"].mean()),
                "mae_mean": float(group["mae"].mean()),
                "improvement_vs_train_mean_mean": float(group["improvement_vs_train_mean"].mean()),
                "improvement_vs_event_mean_mean": float(group["improvement_vs_event_mean"].mean()),
                "improvement_vs_idw_mean": float(group["improvement_vs_idw"].mean()),
            }
        )
    return summary


def make_headline(summary: list[dict[str, Any]]) -> dict[str, Any]:
    frame = pd.DataFrame(summary)
    idw_32 = frame[
        (frame["model"] == "idw_all")
        & (frame["observed_count"] == 32)
        & (frame["strategy"] == "space_filling")
    ]
    raw_32 = frame[
        (frame["model"] == "masked_event_raw_set")
        & (frame["observed_count"] == 32)
        & (frame["strategy"] == "space_filling")
    ]
    coord_32 = frame[
        (frame["model"] == "masked_event_coord_only")
        & (frame["observed_count"] == 32)
        & (frame["strategy"] == "space_filling")
    ]
    headline: dict[str, Any] = {
        "one_sentence": (
            "In HTEM Cu-S-Sn libraries, partial raw XRD observations inside one sample "
            "library can predict the library's missing XRD map without phase labels."
        )
    }
    if not idw_32.empty:
        headline["idw_32_space_filling_improvement_vs_event_mean"] = float(
            idw_32.iloc[0]["improvement_vs_event_mean_mean"]
        )
    if not raw_32.empty:
        headline["masked_raw_32_space_filling_improvement_vs_event_mean"] = float(
            raw_32.iloc[0]["improvement_vs_event_mean_mean"]
        )
    if not raw_32.empty and not coord_32.empty:
        headline["raw_minus_coord_improvement_vs_event_mean_at_32"] = float(
            raw_32.iloc[0]["improvement_vs_event_mean_mean"]
            - coord_32.iloc[0]["improvement_vs_event_mean_mean"]
        )
    return headline


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root()
    device = NEURAL.select_device(args.device)
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
    event_ids = events["sample_library_id"].astype(str).to_numpy()
    folds = split_event_ids(event_ids, n_folds=args.folds, seed=args.seed)
    max_observed = max(args.observed_counts)

    all_rows = []
    diagnostics = []
    for fold, test_event_ids in enumerate(folds):
        train_event_ids = set(event_ids.tolist()) - test_event_ids
        print(
            f"fold={fold} train_libraries={len(train_event_ids)} test_libraries={len(test_event_ids)}",
            file=sys.stderr,
        )
        pca_by_target_mode = make_pca_by_target_mode(
            event_ids=event_ids,
            coords=coords,
            spectra=spectra,
            train_event_ids=train_event_ids,
            observed_counts=args.observed_counts,
            seed=args.seed + fold,
            random_repeats=args.train_random_repeats,
            pca_components=args.pca_components,
        )
        bundles = {}
        for variant in args.variants:
            target_mode = variant_target_mode(variant)
            bundle, diagnostic = train_variant(
                variant=variant,
                event_ids=event_ids,
                coords=coords,
                spectra=spectra,
                train_event_ids=train_event_ids,
                test_event_ids=test_event_ids,
                pca_model=pca_by_target_mode[target_mode],
                observed_counts=args.observed_counts,
                max_observed=max_observed,
                seed=args.seed + fold,
                train_random_repeats=args.train_random_repeats,
                device=device,
                epochs=args.epochs,
                batch_size=args.batch_size,
                learning_rate=args.learning_rate,
            )
            bundles[variant] = bundle
            diagnostics.append(
                {
                    "fold": fold,
                    "train_libraries": len(train_event_ids),
                    "test_libraries": len(test_event_ids),
                    "device": str(device),
                    **diagnostic,
                }
            )
        all_rows.extend(
            evaluate_fold(
                fold=fold,
                event_ids=event_ids,
                coords=coords,
                spectra=spectra,
                train_event_ids=train_event_ids,
                test_event_ids=test_event_ids,
                bundles=bundles,
                observed_counts=args.observed_counts,
                eval_random_repeats=args.eval_random_repeats,
                max_observed=max_observed,
                seed=args.seed,
                device=device,
            )
        )

    summary = summarize_rows(all_rows)
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_id": "htem",
        "task": "htem_masked_event_xrd_reconstruction",
        "api_base_url": HTEM_API_BASE_URL,
        "element_system_filter": element_system_filter,
        "selected_library_count": len(selected_ids),
        "selected_library_ids": selected_ids,
        "event_count": int(len(events)),
        "xrd_points": int(spectra.shape[1]),
        "angle_min": float(np.min(angle)),
        "angle_max": float(np.max(angle)),
        "folds": args.folds,
        "observed_counts": args.observed_counts,
        "variants": args.variants,
        "device": str(device),
        "architecture": {
            "model": "MaskedEventNet",
            "objective": "given partial raw XRD observations from a sample library, predict missing XRD spectra",
            "controls": [
                "coord_only zeros observed spectra",
                "idw_all tests spatial interpolation shortcut",
                "observed_event_mean tests whether event identity alone is enough",
            ],
            "epochs": args.epochs,
            "pca_components": args.pca_components,
        },
        "hypotheses": [
            "Partial raw XRD inside one HTEM sample library should predict missing XRD without phase labels.",
            "Raw-set should beat coord-only if the observed spectra carry event-specific signal.",
            "IDW may remain very strong because HTEM composition libraries are spatially smooth; a neural win over IDW is not assumed.",
            "If all raw-event models lose to coordinate-only or event mean, the HTEM bridge is too shortcut-heavy for the snap-result.",
        ],
        "direction_critique": [
            "This is the right next direction because it ports the Track B masked-event objective from synthetic fields to public event-like data.",
            "The question is intentionally simple enough to explain in one sentence: observe part of an experimental field, predict the unobserved measurements.",
            "It still guards against premature excitement by comparing against event mean, coordinate-only, and IDW baselines.",
        ],
        "diagnostics": diagnostics,
        "rows": all_rows,
        "summary": summary,
        "headline": make_headline(summary),
        "caveats": [
            "HTEM sample libraries are event proxies, not full synthesis trajectories.",
            "Within-library XRD prediction can be spatial interpolation, so IDW is a required baseline.",
            "This is not a material-discovery claim; it is evidence that event-native missing-measurement objectives are testable on public data.",
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
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--observed-counts", type=int, nargs="+", default=[8, 16, 32])
    parser.add_argument("--pca-components", type=int, default=12)
    parser.add_argument("--train-random-repeats", type=int, default=1)
    parser.add_argument("--eval-random-repeats", type=int, default=1)
    parser.add_argument("--variants", nargs="+", default=DEFAULT_VARIANTS)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--device", default="auto")
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
        default=Path("data/manifests/htem_masked_event_model_cu_s_sn.json"),
    )
    return parser.parse_args()


def main() -> None:
    result = run(parse_args())
    printable = {
        "task": result["task"],
        "device": result["device"],
        "hypotheses": result["hypotheses"],
        "direction_critique": result["direction_critique"],
        "headline": result["headline"],
        "summary": result["summary"],
        "caveats": result["caveats"],
    }
    print(json.dumps(printable, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
