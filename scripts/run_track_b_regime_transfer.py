"""Stress-test Track B active policies under synthetic event-regime shift."""

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

from materials_event_modeling.track_b.synthetic import REGIMES, regime_basis
from materials_event_modeling.track_b.synthetic_field import (
    SyntheticEventField,
    observation_grid,
    shifted_pattern,
)


DEFAULT_TEST_REGIMES = ["matched_smooth", "reversed_time", "random_axis", "abrupt_basin"]


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


NEURAL = load_script_module("track_b_neural_policy", "run_track_b_neural_active_policy.py")
ABLATION = load_script_module("track_b_neural_ablation", "run_track_b_neural_policy_ablation.py")
ACTIVE_LOOP = load_script_module("track_b_active_loop", "run_track_b_active_event_loop.py")
FOREST_POLICY = load_script_module("track_b_learned_forest", "run_track_b_learned_active_policy.py")


def progress_values(
    *,
    coords: np.ndarray,
    regime: str,
    rng: np.random.Generator,
) -> tuple[np.ndarray, str, float, float | None]:
    """Return event-local progress coordinates for a synthetic shifted field."""

    if regime in {"source_smooth", "matched_smooth"}:
        return coords[:, 0].copy(), "x_forward", 9.0, None
    if regime == "reversed_time":
        return 1.0 - coords[:, 0], "x_reverse", 9.0, None
    if regime == "random_axis":
        angle = float(rng.uniform(0.0, np.pi))
        direction = np.array([np.cos(angle), np.sin(angle)], dtype=np.float32)
        projection = coords @ direction
        projection = (projection - projection.min()) / max(float(np.ptp(projection)), 1e-8)
        return projection.astype(np.float32), f"axis_{angle:.3f}", 11.0, None
    if regime == "abrupt_basin":
        boundary = float(rng.uniform(0.35, 0.65))
        return coords[:, 0].copy(), "x_forward_abrupt", 28.0, boundary
    raise ValueError(f"unknown transfer regime: {regime}")


def generate_transfer_event_field(
    *,
    n_events: int,
    observations_per_event: int,
    n_theta: int,
    seed: int,
    transfer_regime: str,
) -> SyntheticEventField:
    """Generate shifted synthetic event fields for policy transfer tests.

    These are not chemistry simulations. They are deliberately controlled worlds that
    stress whether a policy learned on smooth x-forward event fields can transfer when the
    measurement field changes direction, axis, or discontinuity.
    """

    rng = np.random.default_rng(seed)
    theta = np.linspace(15.0, 60.0, n_theta, dtype=np.float32)
    bases = regime_basis(theta)
    low_signal = bases["low_signal_sparse"]
    coords_template = observation_grid(observations_per_event)

    event_ids = []
    coords = []
    spectra = []
    rows = []

    for event_idx in range(n_events):
        event_id = f"{transfer_regime}_event_{event_idx:03d}"
        hidden_regime = REGIMES[event_idx % len(REGIMES)]
        base_pattern = bases[hidden_regime]
        competing_regime = REGIMES[(event_idx + 2) % len(REGIMES)]
        competing_pattern = bases[competing_regime]
        progress, axis_label, steepness, basin_boundary = progress_values(
            coords=coords_template,
            regime=transfer_regime,
            rng=rng,
        )
        transition_center = 0.25 + 0.08 * (event_idx % 5) + float(rng.normal(0.0, 0.015))
        if transfer_regime == "abrupt_basin":
            transition_center = 0.18 + 0.12 * (event_idx % 6) + float(rng.normal(0.0, 0.015))
        field_shift = float(rng.normal(0.0, 0.02))
        if transfer_regime in {"random_axis", "abrupt_basin"}:
            field_shift += float(rng.normal(0.0, 0.015))
        field_background = float(rng.uniform(0.02, 0.07))

        for observation_idx, coord in enumerate(coords_template):
            time_fraction = float(coord[0])
            micro_position = float(coord[1])
            event_progress = float(progress[observation_idx])
            conversion = 1.0 / (1.0 + np.exp(-steepness * (event_progress - transition_center)))

            local_shift = field_shift + 0.07 * (micro_position - 0.5)
            local_pattern = shifted_pattern(theta, base_pattern, local_shift)
            precursor_like = shifted_pattern(theta, low_signal, -0.02 * micro_position)

            basin_weight = 0.0
            if basin_boundary is not None:
                basin_weight = 1.0 / (1.0 + np.exp(-34.0 * (micro_position - basin_boundary)))
                competing_shift = field_shift - 0.04 + 0.03 * time_fraction
                competing_local = shifted_pattern(theta, competing_pattern, competing_shift)
                local_pattern = (1.0 - basin_weight) * local_pattern + basin_weight * competing_local

            amplitude = 0.25 + 0.75 * conversion + 0.08 * np.sin(
                2.0 * np.pi * micro_position + event_idx
            )
            if transfer_regime == "random_axis":
                amplitude += 0.06 * np.sin(2.0 * np.pi * event_progress)
            background = field_background + 0.025 * np.sin(theta / 7.5 + micro_position) ** 2
            if transfer_regime == "abrupt_basin":
                background += 0.018 * basin_weight
            noise = rng.normal(0.0, 0.018, size=theta.shape)
            measured = (
                amplitude * (conversion * local_pattern + (1.0 - conversion) * precursor_like)
                + background
                + noise
            )
            measured = np.clip(measured, 0.0, None)
            measured = measured / max(float(measured.max()), 1e-8)

            event_ids.append(event_id)
            coords.append(coord)
            spectra.append(measured.astype(np.float32))
            rows.append(
                {
                    "event_id": event_id,
                    "observation_id": f"{event_id}_obs_{observation_idx:02d}",
                    "transfer_regime": transfer_regime,
                    "hidden_regime": hidden_regime,
                    "competing_regime": competing_regime,
                    "time_fraction": time_fraction,
                    "micro_position": micro_position,
                    "event_progress": event_progress,
                    "axis_label": axis_label,
                    "transition_center": transition_center,
                    "basin_boundary": basin_boundary,
                    "basin_weight": basin_weight,
                }
            )

    return SyntheticEventField(
        event_ids=np.array(event_ids),
        coords=np.vstack(coords).astype(np.float32),
        spectra=np.vstack(spectra).astype(np.float32),
        theta=theta,
        table=pd.DataFrame(rows),
    )


def unique_event_ids(field: SyntheticEventField) -> set[str]:
    return set(np.array(sorted(set(field.event_ids.tolist()))).tolist())


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    summary_rows = []
    for (test_regime, strategy, budget), group in df.groupby(
        ["test_regime", "strategy", "budget"],
        sort=True,
    ):
        summary_rows.append(
            {
                "test_regime": test_regime,
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


def summarize_target_diagnostics(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(diagnostics)
    summary_rows = []
    for (test_regime, variant), group in df.groupby(["test_regime", "variant"], sort=True):
        summary_rows.append(
            {
                "test_regime": test_regime,
                "variant": variant,
                "seed_count": int(len(group)),
                "target_mse_improvement_mean": float(group["target_mse_improvement"].mean()),
                "target_mse_improvement_min": float(group["target_mse_improvement"].min()),
                "target_mse_improvement_max": float(group["target_mse_improvement"].max()),
            }
        )
    return summary_rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    device = ABLATION.select_device(args.device)
    variants = ABLATION.select_variants(args.variants)
    seeds = NEURAL.DEFAULT_SEEDS[: args.seed_count]
    max_observed = max(args.budgets) - 1
    rows = []
    diagnostics = []

    for seed in seeds:
        train_field = generate_transfer_event_field(
            n_events=args.train_events,
            observations_per_event=args.observations_per_event,
            n_theta=args.theta_points,
            seed=seed,
            transfer_regime=args.train_regime,
        )
        train_events = unique_event_ids(train_field)
        train_examples_base = NEURAL.build_neural_examples(
            event_ids=train_field.event_ids,
            coords=train_field.coords,
            spectra=train_field.spectra,
            selected_event_ids=train_events,
            budgets=args.budgets,
            initial_count=args.initial_count,
            max_observed=max_observed,
        )

        trained_variants = {}
        for variant in variants:
            train_examples = ABLATION.ablate_examples(train_examples_base, variant)
            model, scalar_scaler, target_mean, target_std, _ = ABLATION.train_variant_model(
                train_examples=train_examples,
                test_examples=train_examples,
                variant=variant,
                n_theta=args.theta_points,
                max_observed=max_observed,
                seed=seed,
                device=device,
                epochs=args.epochs,
                batch_size=args.batch_size,
                learning_rate=args.learning_rate,
            )
            trained_variants[variant.name] = {
                "variant": variant,
                "model": model,
                "scalar_scaler": scalar_scaler,
                "target_mean": target_mean,
                "target_std": target_std,
                "train_examples": train_examples,
            }

        pca_components = min(args.pca_components, train_field.spectra.shape[0] - 1)
        pca_model = PCA(n_components=pca_components, random_state=seed)
        pca_model.fit(train_field.spectra)
        forest_features, forest_targets, _ = FOREST_POLICY.build_training_examples(
            event_ids=train_field.event_ids,
            coords=train_field.coords,
            spectra=train_field.spectra,
            train_event_ids=train_events,
            budgets=args.budgets,
            initial_count=args.initial_count,
            pca_model=pca_model,
        )
        forest_model = FOREST_POLICY.train_model(forest_features, forest_targets, seed=seed)

        for test_regime in args.test_regimes:
            test_field = generate_transfer_event_field(
                n_events=args.test_events,
                observations_per_event=args.observations_per_event,
                n_theta=args.theta_points,
                seed=seed + args.test_seed_offset,
                transfer_regime=test_regime,
            )
            test_events = unique_event_ids(test_field)
            test_examples_base = NEURAL.build_neural_examples(
                event_ids=test_field.event_ids,
                coords=test_field.coords,
                spectra=test_field.spectra,
                selected_event_ids=test_events,
                budgets=args.budgets,
                initial_count=args.initial_count,
                max_observed=max_observed,
            )

            for variant_name, bundle in trained_variants.items():
                variant = bundle["variant"]
                test_examples = ABLATION.ablate_examples(test_examples_base, variant)
                target_diag = NEURAL.evaluate_target_prediction(
                    model=bundle["model"],
                    train_examples=bundle["train_examples"],
                    test_examples=test_examples,
                    scalar_scaler=bundle["scalar_scaler"],
                    target_mean=bundle["target_mean"],
                    target_std=bundle["target_std"],
                    device=device,
                )
                diagnostics.append(
                    {
                        "seed": seed,
                        "train_regime": args.train_regime,
                        "test_regime": test_regime,
                        "variant": variant_name,
                        "device": str(device),
                        "train_events": len(train_events),
                        "test_events": len(test_events),
                        "training_examples": int(len(bundle["train_examples"].targets)),
                        "test_target_examples": int(len(test_examples.targets)),
                        **target_diag,
                    }
                )
                variant_rows = ABLATION.evaluate_variant_policy(
                    model=bundle["model"],
                    scalar_scaler=bundle["scalar_scaler"],
                    target_mean=bundle["target_mean"],
                    target_std=bundle["target_std"],
                    variant=variant,
                    event_ids=test_field.event_ids,
                    coords=test_field.coords,
                    spectra=test_field.spectra,
                    test_event_ids=test_events,
                    budgets=args.budgets,
                    initial_count=args.initial_count,
                    max_observed=max_observed,
                    device=device,
                )
                for row in variant_rows:
                    row["seed"] = seed
                    row["train_regime"] = args.train_regime
                    row["test_regime"] = test_regime
                    rows.append(row)

            forest_rows = FOREST_POLICY.evaluate_learned_policy(
                model=forest_model,
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
                row["train_regime"] = args.train_regime
                row["test_regime"] = test_regime
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
                        row["train_regime"] = args.train_regime
                        row["test_regime"] = test_regime
                        rows.append(row)

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "track_b_regime_transfer",
        "train_regime": args.train_regime,
        "test_regimes": args.test_regimes,
        "train_events": args.train_events,
        "test_events": args.test_events,
        "observations_per_event": args.observations_per_event,
        "initial_count": args.initial_count,
        "budgets": args.budgets,
        "seeds": seeds,
        "device": str(device),
        "epochs": args.epochs,
        "variants": ABLATION.variant_metadata(variants),
        "hypotheses": [
            "Matched-smooth transfer should resemble the previous in-distribution ablation.",
            "Coordinate/scalar shortcuts should weaken under reversed-time, random-axis, and abrupt-basin shifts.",
            "If raw event-state learning is more than a shortcut, raw-spectrum set variants should retain more target-prediction and policy value than scalar_full and coords_basic under shifted regimes.",
            "If all learned policies collapse toward space-filling under shift, the next step should be training on mixed regimes or collecting richer event context, not tuning the same architecture.",
        ],
        "diagnostics": diagnostics,
        "target_summary": summarize_target_diagnostics(diagnostics),
        "rows": rows,
        "summary": summarize(rows),
        "caveats": [
            "This is still synthetic; the shifted regimes are controlled stress tests, not materials evidence.",
            "The policies are trained only on source_smooth events, so failures under shift are expected and informative.",
            "The score is still raw held-out measurement reconstruction, not label prediction.",
        ],
    }
    output_path = project_root() / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-regime", default="source_smooth")
    parser.add_argument("--test-regimes", nargs="+", default=DEFAULT_TEST_REGIMES)
    parser.add_argument("--train-events", type=int, default=48)
    parser.add_argument("--test-events", type=int, default=48)
    parser.add_argument("--observations-per-event", type=int, default=12)
    parser.add_argument("--theta-points", type=int, default=512)
    parser.add_argument("--initial-count", type=int, default=2)
    parser.add_argument("--budgets", type=int, nargs="+", default=[3, 4, 6, 8])
    parser.add_argument("--pca-components", type=int, default=6)
    parser.add_argument("--seed-count", type=int, default=len(NEURAL.DEFAULT_SEEDS))
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--variants", nargs="+", default=None)
    parser.add_argument("--test-seed-offset", type=int, default=10000)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/track_b_regime_transfer.json"),
    )
    return parser.parse_args()


def main() -> None:
    result = run(parse_args())
    printable = {
        "task": result["task"],
        "device": result["device"],
        "epochs": result["epochs"],
        "hypotheses": result["hypotheses"],
        "target_summary": result["target_summary"],
        "summary": result["summary"],
        "caveats": result["caveats"],
    }
    print(json.dumps(printable, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
