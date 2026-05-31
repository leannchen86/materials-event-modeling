"""Train a neural set-encoder acquisition policy for Track B event fields."""

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

from materials_event_modeling.track_b.field_prediction import (
    farthest_first_indices,
    inverse_distance_prediction,
    mean_squared_error,
)
from materials_event_modeling.track_b.synthetic_field import generate_synthetic_event_field


DEFAULT_SEEDS = [17, 29, 41, 53, 67]


@dataclass(frozen=True)
class NeuralExamples:
    observed_spectra: np.ndarray
    observed_coords: np.ndarray
    observed_mask: np.ndarray
    scalar_features: np.ndarray
    targets: np.ndarray
    groups: np.ndarray


class SetAcquisitionNet(nn.Module):
    def __init__(
        self,
        *,
        n_theta: int,
        scalar_dim: int,
        max_observed: int,
        d_model: int = 64,
        n_heads: int = 4,
    ) -> None:
        super().__init__()
        self.max_observed = max_observed
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
        self.scalar_encoder = nn.Sequential(
            nn.Linear(scalar_dim, d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
        )
        self.head = nn.Sequential(
            nn.Linear(2 * d_model, d_model),
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
        token = self.spectrum_encoder(observed_spectra) + self.coord_encoder(observed_coords)
        encoded = self.set_encoder(token, src_key_padding_mask=~observed_mask.bool())
        mask = observed_mask.float().unsqueeze(-1)
        pooled = (encoded * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1.0)
        scalar_embedding = self.scalar_encoder(scalar_features)
        return self.head(torch.cat([pooled, scalar_embedding], dim=-1)).squeeze(-1)


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


def select_device(requested: str) -> torch.device:
    if requested != "auto":
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


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


def scalar_features_for_candidate(
    *,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed: list[int],
    candidate: int,
    budget: int,
    max_budget: int,
    max_observed: int,
) -> list[float]:
    observed_arr = np.array(observed, dtype=int)
    observed_coords = coords[observed_arr]
    observed_spectra = spectra[observed_arr]
    candidate_coord = coords[[candidate]]
    distances = np.linalg.norm(candidate_coord[:, None, :] - observed_coords[None, :, :], axis=2)[0]
    nearest_idx = int(np.argmin(distances))
    prediction = inverse_distance_prediction(observed_coords, observed_spectra, candidate_coord)[0]
    nearest_spectrum = observed_spectra[nearest_idx]
    observed_mean = observed_spectra.mean(axis=0)
    return [
        float(coords[candidate, 0]),
        float(coords[candidate, 1]),
        float(len(observed) / max_observed),
        float(budget / max_budget),
        float(distances.min()),
        float(distances.mean()),
        float(distances.max()),
        float(np.mean((prediction - nearest_spectrum) ** 2)),
        float(np.mean((prediction - observed_mean) ** 2)),
        float(np.mean(observed_mean)),
        float(np.std(observed_mean)),
    ]


def make_example_arrays(
    *,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed: list[int],
    candidate: int,
    budget: int,
    max_budget: int,
    max_observed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    observed_spectra = np.zeros((max_observed, spectra.shape[1]), dtype=np.float32)
    observed_coords = np.zeros((max_observed, 2), dtype=np.float32)
    observed_mask = np.zeros((max_observed,), dtype=bool)
    for row_idx, obs_idx in enumerate(observed):
        observed_spectra[row_idx] = spectra[obs_idx]
        observed_coords[row_idx] = coords[obs_idx]
        observed_mask[row_idx] = True
    scalar = np.asarray(
        scalar_features_for_candidate(
            coords=coords,
            spectra=spectra,
            observed=observed,
            candidate=candidate,
            budget=budget,
            max_budget=max_budget,
            max_observed=max_observed,
        ),
        dtype=np.float32,
    )
    return observed_spectra, observed_coords, observed_mask, scalar


def build_neural_examples(
    *,
    event_ids: np.ndarray,
    coords: np.ndarray,
    spectra: np.ndarray,
    selected_event_ids: set[str],
    budgets: list[int],
    initial_count: int,
    max_observed: int,
) -> NeuralExamples:
    observed_spectra_rows = []
    observed_coord_rows = []
    observed_mask_rows = []
    scalar_rows = []
    targets = []
    groups = []
    max_budget = max(budgets)
    for event_id in sorted(selected_event_ids):
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
                candidate_targets = []
                for candidate in candidates:
                    next_observed = [*observed, candidate]
                    next_heldout = [idx for idx in candidates if idx != candidate]
                    next_error = reconstruction_error(
                        coords=event_coords,
                        spectra=event_spectra,
                        observed=next_observed,
                        heldout=next_heldout,
                    )
                    observed_spectra, observed_coords, observed_mask, scalar = make_example_arrays(
                        coords=event_coords,
                        spectra=event_spectra,
                        observed=observed,
                        candidate=candidate,
                        budget=budget,
                        max_budget=max_budget,
                        max_observed=max_observed,
                    )
                    target = current_error - next_error
                    observed_spectra_rows.append(observed_spectra)
                    observed_coord_rows.append(observed_coords)
                    observed_mask_rows.append(observed_mask)
                    scalar_rows.append(scalar)
                    targets.append(target)
                    groups.append(event_id)
                    candidate_targets.append(target)
                observed.append(int(candidates[int(np.argmax(candidate_targets))]))

    return NeuralExamples(
        observed_spectra=np.asarray(observed_spectra_rows, dtype=np.float32),
        observed_coords=np.asarray(observed_coord_rows, dtype=np.float32),
        observed_mask=np.asarray(observed_mask_rows, dtype=bool),
        scalar_features=np.asarray(scalar_rows, dtype=np.float32),
        targets=np.asarray(targets, dtype=np.float32),
        groups=np.asarray(groups),
    )


def transform_examples(
    examples: NeuralExamples,
    *,
    scalar_scaler: StandardScaler,
    target_mean: float,
    target_std: float,
    include_targets: bool,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor | None]:
    y = None
    if include_targets:
        y = torch.from_numpy(((examples.targets - target_mean) / target_std).astype(np.float32))
    return (
        torch.from_numpy(examples.observed_spectra),
        torch.from_numpy(examples.observed_coords),
        torch.from_numpy(examples.observed_mask),
        torch.from_numpy(scalar_scaler.transform(examples.scalar_features).astype(np.float32)),
        y,
    )


def train_neural_model(
    *,
    train_examples: NeuralExamples,
    test_examples: NeuralExamples,
    n_theta: int,
    max_observed: int,
    seed: int,
    device: torch.device,
    epochs: int,
    batch_size: int,
    learning_rate: float,
) -> tuple[SetAcquisitionNet, StandardScaler, float, float, dict[str, float]]:
    torch.manual_seed(seed)
    scalar_scaler = StandardScaler().fit(train_examples.scalar_features)
    target_mean = float(train_examples.targets.mean())
    target_std = float(train_examples.targets.std() + 1e-8)
    x_spec, x_coord, x_mask, x_scalar, y = transform_examples(
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

    model = SetAcquisitionNet(
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

    diagnostics = evaluate_target_prediction(
        model=model,
        train_examples=train_examples,
        test_examples=test_examples,
        scalar_scaler=scalar_scaler,
        target_mean=target_mean,
        target_std=target_std,
        device=device,
    )
    return model, scalar_scaler, target_mean, target_std, diagnostics


def predict_targets(
    *,
    model: SetAcquisitionNet,
    examples: NeuralExamples,
    scalar_scaler: StandardScaler,
    target_mean: float,
    target_std: float,
    device: torch.device,
    batch_size: int = 512,
) -> np.ndarray:
    model.eval()
    tensors = transform_examples(
        examples,
        scalar_scaler=scalar_scaler,
        target_mean=target_mean,
        target_std=target_std,
        include_targets=False,
    )
    spec, coord, mask, scalar, _ = tensors
    dataset = TensorDataset(spec, coord, mask, scalar)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    predictions = []
    with torch.no_grad():
        for batch in loader:
            batch = [item.to(device) for item in batch]
            pred = model(*batch).cpu().numpy()
            predictions.append(pred)
    return np.concatenate(predictions) * target_std + target_mean


def evaluate_target_prediction(
    *,
    model: SetAcquisitionNet,
    train_examples: NeuralExamples,
    test_examples: NeuralExamples,
    scalar_scaler: StandardScaler,
    target_mean: float,
    target_std: float,
    device: torch.device,
) -> dict[str, float]:
    predictions = predict_targets(
        model=model,
        examples=test_examples,
        scalar_scaler=scalar_scaler,
        target_mean=target_mean,
        target_std=target_std,
        device=device,
    )
    baseline = np.full_like(test_examples.targets, fill_value=train_examples.targets.mean())
    baseline_mse = float(np.mean((test_examples.targets - baseline) ** 2))
    model_mse = float(np.mean((test_examples.targets - predictions) ** 2))
    return {
        "target_baseline_mse": baseline_mse,
        "target_model_mse": model_mse,
        "target_mse_improvement": 1.0 - (model_mse / baseline_mse),
    }


def choose_neural_candidate(
    *,
    model: SetAcquisitionNet,
    scalar_scaler: StandardScaler,
    target_mean: float,
    target_std: float,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed: list[int],
    candidates: list[int],
    budget: int,
    max_budget: int,
    max_observed: int,
    device: torch.device,
) -> int:
    examples = []
    for candidate in candidates:
        examples.append(
            make_example_arrays(
                coords=coords,
                spectra=spectra,
                observed=observed,
                candidate=candidate,
                budget=budget,
                max_budget=max_budget,
                max_observed=max_observed,
            )
        )
    neural_examples = NeuralExamples(
        observed_spectra=np.asarray([item[0] for item in examples], dtype=np.float32),
        observed_coords=np.asarray([item[1] for item in examples], dtype=np.float32),
        observed_mask=np.asarray([item[2] for item in examples], dtype=bool),
        scalar_features=np.asarray([item[3] for item in examples], dtype=np.float32),
        targets=np.zeros(len(examples), dtype=np.float32),
        groups=np.asarray(["deploy"] * len(examples)),
    )
    scores = predict_targets(
        model=model,
        examples=neural_examples,
        scalar_scaler=scalar_scaler,
        target_mean=target_mean,
        target_std=target_std,
        device=device,
    )
    return int(candidates[int(np.argmax(scores))])


def run_neural_loop_for_event(
    *,
    model: SetAcquisitionNet,
    scalar_scaler: StandardScaler,
    target_mean: float,
    target_std: float,
    coords: np.ndarray,
    spectra: np.ndarray,
    budget: int,
    initial_count: int,
    max_budget: int,
    max_observed: int,
    device: torch.device,
) -> dict[str, Any]:
    observed = farthest_first_indices(coords, initial_count).tolist()
    while len(observed) < budget:
        candidates = [idx for idx in range(len(coords)) if idx not in observed]
        next_idx = choose_neural_candidate(
            model=model,
            scalar_scaler=scalar_scaler,
            target_mean=target_mean,
            target_std=target_std,
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
    final_mse = reconstruction_error(coords=coords, spectra=spectra, observed=observed, heldout=heldout)
    return {"observed_indices": observed, "heldout_indices": heldout, "final_mse": final_mse}


def score_observed_set(
    *,
    spectra: np.ndarray,
    observed_idx: np.ndarray,
    heldout_idx: np.ndarray,
    event_mse: float,
    all_observed_spectra: list[np.ndarray],
) -> dict[str, float]:
    event_mean = spectra[observed_idx].mean(axis=0)
    event_prediction = np.tile(event_mean, (len(heldout_idx), 1))
    event_mean_mse = mean_squared_error(spectra[heldout_idx], event_prediction)
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


def evaluate_neural_policy(
    *,
    model: SetAcquisitionNet,
    scalar_scaler: StandardScaler,
    target_mean: float,
    target_std: float,
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
            result = run_neural_loop_for_event(
                model=model,
                scalar_scaler=scalar_scaler,
                target_mean=target_mean,
                target_std=target_std,
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
                    "strategy": "neural_set_encoder",
                    "budget": budget,
                    **score_observed_set(
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
                "event_count": int(len(group)),
                "mse_mean": float(group["mse"].mean()),
                "mse_std": float(group["mse"].std(ddof=0)),
                "improvement_vs_event_mean_mean": float(group["improvement_vs_event_mean"].mean()),
                "improvement_vs_global_mean_mean": float(group["improvement_vs_global_mean"].mean()),
            }
        )
    return summary_rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    device = select_device(args.device)
    active_loop = load_script_module("track_b_active_loop", "run_track_b_active_event_loop.py")
    forest_policy = load_script_module("track_b_learned_forest", "run_track_b_learned_active_policy.py")
    rows = []
    diagnostics = []
    seeds = DEFAULT_SEEDS[: args.seed_count]
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

        train_examples = build_neural_examples(
            event_ids=field.event_ids,
            coords=field.coords,
            spectra=field.spectra,
            selected_event_ids=train_events,
            budgets=args.budgets,
            initial_count=args.initial_count,
            max_observed=max_observed,
        )
        test_examples = build_neural_examples(
            event_ids=field.event_ids,
            coords=field.coords,
            spectra=field.spectra,
            selected_event_ids=test_events,
            budgets=args.budgets,
            initial_count=args.initial_count,
            max_observed=max_observed,
        )
        model, scalar_scaler, target_mean, target_std, target_diag = train_neural_model(
            train_examples=train_examples,
            test_examples=test_examples,
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
                "device": str(device),
                "train_events": len(train_events),
                "test_events": len(test_events),
                "training_examples": int(len(train_examples.targets)),
                "test_target_examples": int(len(test_examples.targets)),
                "target_mean": float(train_examples.targets.mean()),
                "target_std": float(train_examples.targets.std()),
                **target_diag,
            }
        )

        neural_rows = evaluate_neural_policy(
            model=model,
            scalar_scaler=scalar_scaler,
            target_mean=target_mean,
            target_std=target_std,
            event_ids=field.event_ids,
            coords=field.coords,
            spectra=field.spectra,
            test_event_ids=test_events,
            budgets=args.budgets,
            initial_count=args.initial_count,
            max_observed=max_observed,
            device=device,
        )
        for row in neural_rows:
            row["seed"] = seed
            rows.append(row)

        train_mask = np.isin(field.event_ids, list(train_events))
        pca_components = min(args.pca_components, int(train_mask.sum()) - 1)
        pca_model = PCA(n_components=pca_components, random_state=seed)
        pca_model.fit(field.spectra[train_mask])
        forest_features, forest_targets, _ = forest_policy.build_training_examples(
            event_ids=field.event_ids,
            coords=field.coords,
            spectra=field.spectra,
            train_event_ids=train_events,
            budgets=args.budgets,
            initial_count=args.initial_count,
            pca_model=pca_model,
        )
        forest_model = forest_policy.train_model(forest_features, forest_targets, seed=seed)
        forest_rows = forest_policy.evaluate_learned_policy(
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
                    rows.append(row)

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "track_b_neural_active_policy",
        "architecture": {
            "model": "SetAcquisitionNet",
            "event_encoder": "2-layer TransformerEncoder over observed (coordinate, spectrum) tokens with masked mean pooling",
            "spectrum_encoder": "MLP from raw 512-point spectrum to token embedding",
            "candidate_encoder": "MLP over candidate coordinate, budget/state, distance, and IDW-disagreement features",
            "target": "oracle one-step reduction in held-out raw-measurement reconstruction MSE",
            "epochs": args.epochs,
            "device": str(device),
        },
        "events": args.events,
        "observations_per_event": args.observations_per_event,
        "initial_count": args.initial_count,
        "budgets": args.budgets,
        "train_fraction": args.train_fraction,
        "seeds": seeds,
        "hypotheses": [
            "A neural set encoder should predict oracle acquisition targets better than a train-mean baseline.",
            "The neural policy should beat random and naive active selection on held-out events.",
            "The neural policy must beat the random forest baseline before we treat added architecture as useful.",
        ],
        "diagnostics": diagnostics,
        "rows": rows,
        "summary": summarize(rows),
        "caveats": [
            "This is still synthetic and uses completed events to create oracle acquisition targets.",
            "The model is a small set encoder, not a large foundation model.",
            "If the neural model loses to the forest, the right response is better state/data, not architecture worship.",
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
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--device", default="auto")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/track_b_neural_active_policy.json"),
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
