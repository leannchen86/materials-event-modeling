"""Train Track B acquisition policies on mixed synthetic regimes and test held-out regimes."""

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

from materials_event_modeling.track_b.synthetic_field import SyntheticEventField

DEFAULT_REGIME_POOL = ["source_smooth", "reversed_time", "random_axis", "abrupt_basin"]
DEFAULT_HELDOUT_REGIMES = ["reversed_time", "random_axis", "abrupt_basin"]
DEFAULT_VARIANTS = ["candidate_set_basic", "scalar_full", "coords_basic", "full_neural"]


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
NEURAL = TRANSFER.NEURAL
ABLATION = TRANSFER.ABLATION
ACTIVE_LOOP = TRANSFER.ACTIVE_LOOP
FOREST_POLICY = TRANSFER.FOREST_POLICY


def concat_fields(fields: list[SyntheticEventField]) -> SyntheticEventField:
    if not fields:
        raise ValueError("need at least one field to concatenate")
    theta = fields[0].theta
    if any(not np.array_equal(field.theta, theta) for field in fields):
        raise ValueError("all fields must use the same theta grid")
    return SyntheticEventField(
        event_ids=np.concatenate([field.event_ids for field in fields]),
        coords=np.vstack([field.coords for field in fields]).astype(np.float32),
        spectra=np.vstack([field.spectra for field in fields]).astype(np.float32),
        theta=theta,
        table=pd.concat([field.table for field in fields], ignore_index=True),
    )


def generate_mixed_train_field(
    *,
    train_regimes: list[str],
    events_per_regime: int,
    observations_per_event: int,
    n_theta: int,
    seed: int,
) -> SyntheticEventField:
    fields = []
    for regime_idx, regime in enumerate(train_regimes):
        fields.append(
            TRANSFER.generate_transfer_event_field(
                n_events=events_per_regime,
                observations_per_event=observations_per_event,
                n_theta=n_theta,
                seed=seed + 1000 * (regime_idx + 1),
                transfer_regime=regime,
            )
        )
    return concat_fields(fields)


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
    for (heldout_regime, variant), group in df.groupby(["heldout_regime", "variant"], sort=True):
        summary_rows.append(
            {
                "heldout_regime": heldout_regime,
                "variant": variant,
                "seed_count": len(group),
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
        for heldout_regime in args.heldout_regimes:
            train_regimes = [regime for regime in args.regime_pool if regime != heldout_regime]
            train_field = generate_mixed_train_field(
                train_regimes=train_regimes,
                events_per_regime=args.train_events_per_regime,
                observations_per_event=args.observations_per_event,
                n_theta=args.theta_points,
                seed=seed,
            )
            train_events = TRANSFER.unique_event_ids(train_field)
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

            test_field = TRANSFER.generate_transfer_event_field(
                n_events=args.test_events,
                observations_per_event=args.observations_per_event,
                n_theta=args.theta_points,
                seed=seed + args.test_seed_offset,
                transfer_regime=heldout_regime,
            )
            test_events = TRANSFER.unique_event_ids(test_field)
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
                        "heldout_regime": heldout_regime,
                        "train_regimes": train_regimes,
                        "variant": variant_name,
                        "device": str(device),
                        "train_events": len(train_events),
                        "test_events": len(test_events),
                        "training_examples": len(bundle["train_examples"].targets),
                        "test_target_examples": len(test_examples.targets),
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
                    row["heldout_regime"] = heldout_regime
                    row["train_regimes"] = train_regimes
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
        "task": "track_b_mixed_regime_transfer",
        "regime_pool": args.regime_pool,
        "heldout_regimes": args.heldout_regimes,
        "train_events_per_regime": args.train_events_per_regime,
        "test_events": args.test_events,
        "observations_per_event": args.observations_per_event,
        "initial_count": args.initial_count,
        "budgets": args.budgets,
        "seeds": seeds,
        "device": str(device),
        "epochs": args.epochs,
        "variants": ABLATION.variant_metadata(variants),
        "hypotheses": [
            "Mixed-regime training should improve held-out random_axis and reversed_time transfer relative to source_smooth-only training.",
            "Raw-spectrum variants should recover more target-prediction signal under held-out regimes if event diversity is the missing ingredient.",
            "If coordinate/scalar variants still dominate, the task remains solvable through process-coordinate shortcuts and needs richer event-context inference.",
            "If all learned policies remain behind space-filling or oracle by a large margin, the next step should be explicit progress-axis inference rather than architecture tuning.",
        ],
        "diagnostics": diagnostics,
        "target_summary": summarize_target_diagnostics(diagnostics),
        "rows": rows,
        "summary": summarize(rows),
        "caveats": [
            "This is still synthetic; held-out regimes are controlled stress tests, not materials evidence.",
            "The run intentionally focuses on failed or hard transfer regimes rather than a broad leaderboard.",
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
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--variants", nargs="+", default=DEFAULT_VARIANTS)
    parser.add_argument("--test-seed-offset", type=int, default=10000)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/track_b_mixed_regime_transfer.json"),
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
