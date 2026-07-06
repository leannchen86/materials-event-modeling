"""Ablate neural active-policy inputs for Track B event fields."""

from __future__ import annotations

import argparse
import importlib.util
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from materials_event_modeling.track_b.synthetic_field import generate_synthetic_event_field


@dataclass(frozen=True)
class VariantSpec:
    name: str
    model_kind: str
    scalar_indices: tuple[int, ...]
    use_observed_spectra: bool
    description: str


class ScalarAcquisitionNet(nn.Module):
    """MLP acquisition model that cannot read the observed raw-spectrum set."""

    def __init__(self, *, scalar_dim: int, d_model: int = 64) -> None:
        super().__init__()
        self.head = nn.Sequential(
            nn.Linear(scalar_dim, d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Linear(d_model, 1),
        )

    def forward(
        self,
        observed_spectra: torch.Tensor,
        observed_coords: torch.Tensor,
        observed_mask: torch.Tensor,
        scalar_features: torch.Tensor,
    ) -> torch.Tensor:
        del observed_spectra, observed_coords, observed_mask
        return self.head(scalar_features).squeeze(-1)


class CandidateConditionedSetAcquisitionNet(nn.Module):
    """Set encoder where a candidate token attends to observed event tokens."""

    def __init__(
        self,
        *,
        n_theta: int,
        scalar_dim: int,
        d_model: int = 64,
        n_heads: int = 4,
    ) -> None:
        super().__init__()
        self.spectrum_encoder = nn.Sequential(
            nn.Linear(n_theta, 128),
            nn.GELU(),
            nn.Linear(128, d_model),
        )
        self.coord_encoder = nn.Sequential(
            nn.Linear(2, 32),
            nn.GELU(),
            nn.Linear(32, d_model),
        )
        self.candidate_encoder = nn.Sequential(
            nn.Linear(scalar_dim, d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
        )
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=128,
            dropout=0.05,
            batch_first=True,
            activation="gelu",
            norm_first=True,
        )
        self.set_encoder = nn.TransformerEncoder(encoder_layer, num_layers=2)
        self.head = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Linear(d_model, 1),
        )

    def forward(
        self,
        observed_spectra: torch.Tensor,
        observed_coords: torch.Tensor,
        observed_mask: torch.Tensor,
        scalar_features: torch.Tensor,
    ) -> torch.Tensor:
        observed_tokens = self.spectrum_encoder(observed_spectra) + self.coord_encoder(
            observed_coords
        )
        candidate_token = self.candidate_encoder(scalar_features).unsqueeze(1)
        tokens = torch.cat([observed_tokens, candidate_token], dim=1)
        candidate_mask = torch.ones(
            (observed_mask.shape[0], 1),
            dtype=observed_mask.dtype,
            device=observed_mask.device,
        )
        mask = torch.cat([observed_mask, candidate_mask], dim=1).bool()
        encoded = self.set_encoder(tokens, src_key_padding_mask=~mask)
        candidate_embedding = encoded[:, -1, :]
        return self.head(candidate_embedding).squeeze(-1)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_script_module(name: str, script_name: str) -> Any:
    script_path = project_root() / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NEURAL = load_script_module("track_b_neural_policy", "run_track_b_neural_active_policy.py")
ACTIVE_LOOP = load_script_module("track_b_active_loop", "run_track_b_active_event_loop.py")
FOREST_POLICY = load_script_module("track_b_learned_forest", "run_track_b_learned_active_policy.py")


FEATURE_NAMES = [
    "candidate_x",
    "candidate_y",
    "observed_fraction",
    "budget_fraction",
    "distance_min",
    "distance_mean",
    "distance_max",
    "idw_vs_nearest_mse",
    "idw_vs_observed_mean_mse",
    "observed_mean_intensity",
    "observed_std_intensity",
]

BASIC_STATE = (0, 1, 2, 3)
FULL_SCALAR = tuple(range(len(FEATURE_NAMES)))

DEFAULT_VARIANTS = [
    VariantSpec(
        name="full_neural",
        model_kind="set",
        scalar_indices=FULL_SCALAR,
        use_observed_spectra=True,
        description="observed raw-spectrum set plus full engineered candidate/state features",
    ),
    VariantSpec(
        name="scalar_full",
        model_kind="scalar",
        scalar_indices=FULL_SCALAR,
        use_observed_spectra=False,
        description="full engineered candidate/state features, no observed raw-spectrum set",
    ),
    VariantSpec(
        name="set_basic",
        model_kind="set",
        scalar_indices=BASIC_STATE,
        use_observed_spectra=True,
        description="observed raw-spectrum set plus only candidate coordinate and budget state",
    ),
    VariantSpec(
        name="candidate_set_basic",
        model_kind="candidate_set",
        scalar_indices=BASIC_STATE,
        use_observed_spectra=True,
        description="candidate token attends to observed raw-spectrum tokens using only basic state",
    ),
    VariantSpec(
        name="coords_basic",
        model_kind="set",
        scalar_indices=BASIC_STATE,
        use_observed_spectra=False,
        description="observed coordinate set plus only candidate coordinate and budget state",
    ),
]


def select_device(requested: str) -> torch.device:
    return NEURAL.select_device(requested)


def select_variants(names: list[str] | None) -> list[VariantSpec]:
    if not names:
        return DEFAULT_VARIANTS
    by_name = {variant.name: variant for variant in DEFAULT_VARIANTS}
    missing = sorted(set(names) - set(by_name))
    if missing:
        raise ValueError(f"unknown variant(s): {missing}; available: {sorted(by_name)}")
    return [by_name[name] for name in names]


def ablate_examples(examples: Any, variant: VariantSpec) -> Any:
    observed_spectra = examples.observed_spectra
    if not variant.use_observed_spectra:
        observed_spectra = np.zeros_like(observed_spectra)
    return NEURAL.NeuralExamples(
        observed_spectra=observed_spectra,
        observed_coords=examples.observed_coords,
        observed_mask=examples.observed_mask,
        scalar_features=examples.scalar_features[:, np.array(variant.scalar_indices, dtype=int)],
        targets=examples.targets,
        groups=examples.groups,
    )


def train_variant_model(
    *,
    train_examples: Any,
    test_examples: Any,
    variant: VariantSpec,
    n_theta: int,
    max_observed: int,
    seed: int,
    device: torch.device,
    epochs: int,
    batch_size: int,
    learning_rate: float,
) -> tuple[nn.Module, StandardScaler, float, float, dict[str, float]]:
    torch.manual_seed(seed)
    scalar_scaler = StandardScaler().fit(train_examples.scalar_features)
    target_mean = float(train_examples.targets.mean())
    target_std = float(train_examples.targets.std() + 1e-8)
    x_spec, x_coord, x_mask, x_scalar, y = NEURAL.transform_examples(
        train_examples,
        scalar_scaler=scalar_scaler,
        target_mean=target_mean,
        target_std=target_std,
        include_targets=True,
    )
    assert y is not None
    dataset = TensorDataset(x_spec, x_coord, x_mask, x_scalar, y)
    generator = torch.Generator()
    generator.manual_seed(seed)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, generator=generator)

    if variant.model_kind == "scalar":
        model: nn.Module = ScalarAcquisitionNet(
            scalar_dim=train_examples.scalar_features.shape[1],
        ).to(device)
    elif variant.model_kind == "candidate_set":
        model = CandidateConditionedSetAcquisitionNet(
            n_theta=n_theta,
            scalar_dim=train_examples.scalar_features.shape[1],
        ).to(device)
    else:
        model = NEURAL.SetAcquisitionNet(
            n_theta=n_theta,
            scalar_dim=train_examples.scalar_features.shape[1],
            max_observed=max_observed,
        ).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    loss_fn = nn.MSELoss()
    model.train()
    for _ in range(epochs):
        for batch in loader:
            spec, coord, mask, scalar, target = [item.to(device) for item in batch]
            optimizer.zero_grad(set_to_none=True)
            prediction = model(spec, coord, mask, scalar)
            loss = loss_fn(prediction, target)
            loss.backward()
            optimizer.step()

    diagnostics = NEURAL.evaluate_target_prediction(
        model=model,
        train_examples=train_examples,
        test_examples=test_examples,
        scalar_scaler=scalar_scaler,
        target_mean=target_mean,
        target_std=target_std,
        device=device,
    )
    return model, scalar_scaler, target_mean, target_std, diagnostics


def choose_variant_candidate(
    *,
    model: nn.Module,
    scalar_scaler: StandardScaler,
    target_mean: float,
    target_std: float,
    variant: VariantSpec,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed: list[int],
    candidates: list[int],
    budget: int,
    max_budget: int,
    max_observed: int,
    device: torch.device,
) -> int:
    examples = [
        NEURAL.make_example_arrays(
            coords=coords,
            spectra=spectra,
            observed=observed,
            candidate=candidate,
            budget=budget,
            max_budget=max_budget,
            max_observed=max_observed,
        )
        for candidate in candidates
    ]
    neural_examples = NEURAL.NeuralExamples(
        observed_spectra=np.asarray([item[0] for item in examples], dtype=np.float32),
        observed_coords=np.asarray([item[1] for item in examples], dtype=np.float32),
        observed_mask=np.asarray([item[2] for item in examples], dtype=bool),
        scalar_features=np.asarray([item[3] for item in examples], dtype=np.float32),
        targets=np.zeros(len(examples), dtype=np.float32),
        groups=np.asarray(["deploy"] * len(examples)),
    )
    ablated = ablate_examples(neural_examples, variant)
    scores = NEURAL.predict_targets(
        model=model,
        examples=ablated,
        scalar_scaler=scalar_scaler,
        target_mean=target_mean,
        target_std=target_std,
        device=device,
    )
    return int(candidates[int(np.argmax(scores))])


def run_variant_loop_for_event(
    *,
    model: nn.Module,
    scalar_scaler: StandardScaler,
    target_mean: float,
    target_std: float,
    variant: VariantSpec,
    coords: np.ndarray,
    spectra: np.ndarray,
    budget: int,
    initial_count: int,
    max_budget: int,
    max_observed: int,
    device: torch.device,
) -> dict[str, Any]:
    observed = NEURAL.farthest_first_indices(coords, initial_count).tolist()
    while len(observed) < budget:
        candidates = [idx for idx in range(len(coords)) if idx not in observed]
        next_idx = choose_variant_candidate(
            model=model,
            scalar_scaler=scalar_scaler,
            target_mean=target_mean,
            target_std=target_std,
            variant=variant,
            coords=coords,
            spectra=spectra,
            observed=observed,
            candidates=candidates,
            budget=budget,
            max_budget=max_budget,
            max_observed=max_observed,
            device=device,
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


def evaluate_variant_policy(
    *,
    model: nn.Module,
    scalar_scaler: StandardScaler,
    target_mean: float,
    target_std: float,
    variant: VariantSpec,
    event_ids: np.ndarray,
    coords: np.ndarray,
    spectra: np.ndarray,
    test_event_ids: set[str],
    budgets: list[int],
    initial_count: int,
    max_observed: int,
    device: torch.device,
) -> list[dict[str, Any]]:
    rows = []
    max_budget = max(budgets)
    for budget in budgets:
        event_results = {}
        observed_spectra = []
        for event_id in sorted(test_event_ids):
            event_idx = np.flatnonzero(event_ids == event_id)
            result = run_variant_loop_for_event(
                model=model,
                scalar_scaler=scalar_scaler,
                target_mean=target_mean,
                target_std=target_std,
                variant=variant,
                coords=coords[event_idx],
                spectra=spectra[event_idx],
                budget=budget,
                initial_count=initial_count,
                max_budget=max_budget,
                max_observed=max_observed,
                device=device,
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
            rows.append(
                {
                    "event_id": event_id,
                    "strategy": variant.name,
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


def variant_metadata(variants: list[VariantSpec]) -> list[dict[str, Any]]:
    return [
        {
            "name": variant.name,
            "model_kind": variant.model_kind,
            "scalar_features": [FEATURE_NAMES[idx] for idx in variant.scalar_indices],
            "use_observed_spectra": variant.use_observed_spectra,
            "description": variant.description,
        }
        for variant in variants
    ]


def run(args: argparse.Namespace) -> dict[str, Any]:
    device = select_device(args.device)
    variants = select_variants(args.variants)
    rows = []
    diagnostics = []
    seeds = NEURAL.DEFAULT_SEEDS[: args.seed_count]
    max_observed = max(args.budgets) - 1

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

        train_examples_base = NEURAL.build_neural_examples(
            event_ids=field.event_ids,
            coords=field.coords,
            spectra=field.spectra,
            selected_event_ids=train_events,
            budgets=args.budgets,
            initial_count=args.initial_count,
            max_observed=max_observed,
        )
        test_examples_base = NEURAL.build_neural_examples(
            event_ids=field.event_ids,
            coords=field.coords,
            spectra=field.spectra,
            selected_event_ids=test_events,
            budgets=args.budgets,
            initial_count=args.initial_count,
            max_observed=max_observed,
        )

        for variant in variants:
            train_examples = ablate_examples(train_examples_base, variant)
            test_examples = ablate_examples(test_examples_base, variant)
            model, scalar_scaler, target_mean, target_std, target_diag = train_variant_model(
                train_examples=train_examples,
                test_examples=test_examples,
                variant=variant,
                n_theta=args.theta_points,
                max_observed=max_observed,
                seed=seed,
                device=device,
                epochs=args.epochs,
                batch_size=args.batch_size,
                learning_rate=args.learning_rate,
            )
            diagnostics.append(
                {
                    "seed": seed,
                    "variant": variant.name,
                    "device": str(device),
                    "train_events": len(train_events),
                    "test_events": len(test_events),
                    "training_examples": len(train_examples.targets),
                    "test_target_examples": len(test_examples.targets),
                    "target_mean": float(train_examples.targets.mean()),
                    "target_std": float(train_examples.targets.std()),
                    **target_diag,
                }
            )

            variant_rows = evaluate_variant_policy(
                model=model,
                scalar_scaler=scalar_scaler,
                target_mean=target_mean,
                target_std=target_std,
                variant=variant,
                event_ids=field.event_ids,
                coords=field.coords,
                spectra=field.spectra,
                test_event_ids=test_events,
                budgets=args.budgets,
                initial_count=args.initial_count,
                max_observed=max_observed,
                device=device,
            )
            for row in variant_rows:
                row["seed"] = seed
                rows.append(row)

        if args.include_forest:
            train_mask = np.isin(field.event_ids, list(train_events))
            pca_components = min(args.pca_components, int(train_mask.sum()) - 1)
            pca_model = PCA(n_components=pca_components, random_state=seed)
            pca_model.fit(field.spectra[train_mask])
            forest_features, forest_targets, _ = FOREST_POLICY.build_training_examples(
                event_ids=field.event_ids,
                coords=field.coords,
                spectra=field.spectra,
                train_event_ids=train_events,
                budgets=args.budgets,
                initial_count=args.initial_count,
                pca_model=pca_model,
            )
            forest_model = FOREST_POLICY.train_model(forest_features, forest_targets, seed=seed)
            forest_rows = FOREST_POLICY.evaluate_learned_policy(
                model=forest_model,
                event_ids=field.event_ids,
                coords=field.coords,
                spectra=field.spectra,
                test_event_ids=test_events,
                budgets=args.budgets,
                initial_count=args.initial_count,
                pca_model=pca_model,
            )
            for row in forest_rows:
                row["seed"] = seed
                rows.append(row)

        if args.include_baselines:
            test_mask = np.isin(field.event_ids, list(test_events))
            for budget in args.budgets:
                for strategy in ["random", "space_filling", "active_hybrid", "oracle_best"]:
                    baseline = ACTIVE_LOOP.run_strategy(
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
                        rows.append(row)

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "track_b_neural_policy_ablation",
        "events": args.events,
        "observations_per_event": args.observations_per_event,
        "initial_count": args.initial_count,
        "budgets": args.budgets,
        "train_fraction": args.train_fraction,
        "seeds": seeds,
        "device": str(device),
        "epochs": args.epochs,
        "variants": variant_metadata(variants),
        "hypotheses": [
            "If raw observed-event spectra matter, full_neural should beat scalar_full.",
            "If engineered scalar shortcuts dominate, scalar_full should match or beat full_neural.",
            "If candidate-conditioned raw event attention helps, candidate_set_basic should beat set_basic and coords_basic.",
        ],
        "diagnostics": diagnostics,
        "rows": rows,
        "summary": summarize(rows),
        "caveats": [
            "This is still synthetic and uses completed events to define oracle acquisition targets.",
            "The ablation separates inputs, not causal mechanisms inside the trained network.",
            "A scalar_full win would not invalidate Track B; it would say this synthetic scaffold is too easy to solve through engineered acquisition features.",
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
    parser.add_argument("--seed-count", type=int, default=len(NEURAL.DEFAULT_SEEDS))
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--variants", nargs="+", default=None)
    parser.add_argument("--include-forest", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--include-baselines", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/track_b_neural_policy_ablation.json"),
    )
    return parser.parse_args()


def main() -> None:
    result = run(parse_args())
    printable = {
        "task": result["task"],
        "device": result["device"],
        "epochs": result["epochs"],
        "hypotheses": result["hypotheses"],
        "variants": result["variants"],
        "diagnostics": result["diagnostics"],
        "summary": result["summary"],
        "caveats": result["caveats"],
    }
    print(json.dumps(printable, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
