"""Train masked event models for Track B missing-measurement prediction."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from sklearn.decomposition import PCA
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from materials_event_modeling.track_b.field_prediction import (
    coordinate_ridge_prediction,
    inverse_distance_prediction,
    mean_squared_error,
)


DEFAULT_REGIME_POOL = ["source_smooth", "reversed_time", "random_axis", "abrupt_basin"]
DEFAULT_HELDOUT_REGIMES = ["reversed_time", "random_axis", "abrupt_basin"]
DEFAULT_OBSERVED_COUNTS = [2, 3, 4, 6, 8]
DEFAULT_VARIANTS = ["raw_set", "coord_only", "raw_residual"]


@dataclass(frozen=True)
class MaskedExamples:
    observed_spectra: np.ndarray
    observed_coords: np.ndarray
    observed_mask: np.ndarray
    candidate_coords: np.ndarray
    observed_fraction: np.ndarray
    targets: np.ndarray
    groups: np.ndarray


class MaskedEventNet(nn.Module):
    """Set-to-point event model: partial observations plus candidate coordinate -> spectrum PCA."""

    def __init__(
        self,
        *,
        n_theta: int,
        target_dim: int,
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
        self.candidate_encoder = nn.Sequential(
            nn.Linear(3, 32),
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
        self.head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Linear(d_model, target_dim),
        )

    def forward(
        self,
        observed_spectra: torch.Tensor,
        observed_coords: torch.Tensor,
        observed_mask: torch.Tensor,
        candidate_coords: torch.Tensor,
        observed_fraction: torch.Tensor,
    ) -> torch.Tensor:
        observed_tokens = self.spectrum_encoder(observed_spectra) + self.coord_encoder(
            observed_coords
        )
        candidate_features = torch.cat([candidate_coords, observed_fraction], dim=-1)
        candidate_token = self.candidate_encoder(candidate_features).unsqueeze(1)
        tokens = torch.cat([observed_tokens, candidate_token], dim=1)
        candidate_mask = torch.ones(
            (observed_mask.shape[0], 1),
            dtype=torch.bool,
            device=observed_mask.device,
        )
        token_mask = torch.cat([observed_mask.bool(), candidate_mask], dim=1)
        encoded = self.set_encoder(tokens, src_key_padding_mask=~token_mask)
        return self.head(encoded[:, -1, :])


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
EVENT_FIELD = load_script_module("track_b_event_field", "run_track_b_event_field_model.py")
NEURAL = TRANSFER.NEURAL


def observed_indices_for_state(
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
    raise ValueError(f"unknown observation mode: {mode}")


def make_masked_arrays(
    *,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed: list[int],
    candidate: int,
    max_observed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    observed_spectra = np.zeros((max_observed, spectra.shape[1]), dtype=np.float32)
    observed_coords = np.zeros((max_observed, 2), dtype=np.float32)
    observed_mask = np.zeros((max_observed,), dtype=bool)
    for row_idx, obs_idx in enumerate(observed):
        observed_spectra[row_idx] = spectra[obs_idx]
        observed_coords[row_idx] = coords[obs_idx]
        observed_mask[row_idx] = True
    candidate_coords = coords[candidate].astype(np.float32)
    observed_fraction = np.asarray([len(observed) / max_observed], dtype=np.float32)
    return observed_spectra, observed_coords, observed_mask, candidate_coords, observed_fraction


def variant_target_mode(variant: str) -> str:
    if variant == "raw_residual":
        return "idw_residual"
    if variant in {"raw_set", "coord_only"}:
        return "spectrum"
    raise ValueError(f"unknown variant: {variant}")


def target_signal_for_candidate(
    *,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed: list[int],
    candidate: int,
    target_mode: str,
) -> np.ndarray:
    if target_mode == "spectrum":
        return spectra[candidate]
    if target_mode == "idw_residual":
        observed_arr = np.asarray(observed, dtype=int)
        baseline = inverse_distance_prediction(
            coords[observed_arr],
            spectra[observed_arr],
            coords[[candidate]],
        )[0]
        return spectra[candidate] - baseline
    raise ValueError(f"unknown target mode: {target_mode}")


def collect_target_signals(
    *,
    event_ids: np.ndarray,
    coords: np.ndarray,
    spectra: np.ndarray,
    selected_event_ids: set[str],
    observed_counts: list[int],
    seed: int,
    random_repeats: int,
    target_mode: str,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    targets = []
    for event_id in sorted(selected_event_ids):
        event_idx = np.flatnonzero(event_ids == event_id)
        event_coords = coords[event_idx]
        event_spectra = spectra[event_idx]
        for observed_count in observed_counts:
            modes = ["space_filling", *["random"] * random_repeats]
            for mode in modes:
                observed = observed_indices_for_state(
                    coords=event_coords,
                    count=observed_count,
                    mode=mode,
                    rng=rng,
                )
                candidates = [idx for idx in range(len(event_idx)) if idx not in observed]
                for candidate in candidates:
                    targets.append(
                        target_signal_for_candidate(
                            coords=event_coords,
                            spectra=event_spectra,
                            observed=observed,
                            candidate=candidate,
                            target_mode=target_mode,
                        )
                    )
    return np.asarray(targets, dtype=np.float32)


def build_masked_examples(
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
    target_mode: str,
) -> MaskedExamples:
    rng = np.random.default_rng(seed)
    observed_spectra_rows = []
    observed_coord_rows = []
    observed_mask_rows = []
    candidate_coord_rows = []
    observed_fraction_rows = []
    targets = []
    groups = []
    for event_id in sorted(selected_event_ids):
        event_idx = np.flatnonzero(event_ids == event_id)
        event_coords = coords[event_idx]
        event_spectra = spectra[event_idx]
        for observed_count in observed_counts:
            modes = ["space_filling", *["random"] * random_repeats]
            for mode in modes:
                observed = observed_indices_for_state(
                    coords=event_coords,
                    count=observed_count,
                    mode=mode,
                    rng=rng,
                )
                candidates = [idx for idx in range(len(event_idx)) if idx not in observed]
                for candidate in candidates:
                    obs_spectra, obs_coords, obs_mask, cand_coord, obs_fraction = (
                        make_masked_arrays(
                            coords=event_coords,
                            spectra=event_spectra,
                            observed=observed,
                            candidate=candidate,
                            max_observed=max_observed,
                        )
                    )
                    observed_spectra_rows.append(obs_spectra)
                    observed_coord_rows.append(obs_coords)
                    observed_mask_rows.append(obs_mask)
                    candidate_coord_rows.append(cand_coord)
                    observed_fraction_rows.append(obs_fraction)
                    target_signal = target_signal_for_candidate(
                        coords=event_coords,
                        spectra=event_spectra,
                        observed=observed,
                        candidate=candidate,
                        target_mode=target_mode,
                    )
                    targets.append(pca_model.transform(target_signal.reshape(1, -1))[0])
                    groups.append(event_id)
    return MaskedExamples(
        observed_spectra=np.asarray(observed_spectra_rows, dtype=np.float32),
        observed_coords=np.asarray(observed_coord_rows, dtype=np.float32),
        observed_mask=np.asarray(observed_mask_rows, dtype=bool),
        candidate_coords=np.asarray(candidate_coord_rows, dtype=np.float32),
        observed_fraction=np.asarray(observed_fraction_rows, dtype=np.float32),
        targets=np.asarray(targets, dtype=np.float32),
        groups=np.asarray(groups),
    )


def ablate_examples(examples: MaskedExamples, *, variant: str) -> MaskedExamples:
    if variant in {"raw_set", "raw_residual"}:
        return examples
    if variant == "coord_only":
        return MaskedExamples(
            observed_spectra=np.zeros_like(examples.observed_spectra),
            observed_coords=examples.observed_coords,
            observed_mask=examples.observed_mask,
            candidate_coords=examples.candidate_coords,
            observed_fraction=examples.observed_fraction,
            targets=examples.targets,
            groups=examples.groups,
        )
    raise ValueError(f"unknown variant: {variant}")


def tensors_from_examples(
    examples: MaskedExamples,
    *,
    target_mean: np.ndarray,
    target_std: np.ndarray,
    include_targets: bool,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor | None]:
    y = None
    if include_targets:
        y = torch.from_numpy(((examples.targets - target_mean) / target_std).astype(np.float32))
    return (
        torch.from_numpy(examples.observed_spectra),
        torch.from_numpy(examples.observed_coords),
        torch.from_numpy(examples.observed_mask),
        torch.from_numpy(examples.candidate_coords),
        torch.from_numpy(examples.observed_fraction),
        y,
    )


def train_masked_model(
    *,
    train_examples: MaskedExamples,
    test_examples: MaskedExamples,
    n_theta: int,
    target_dim: int,
    max_observed: int,
    seed: int,
    device: torch.device,
    epochs: int,
    batch_size: int,
    learning_rate: float,
) -> tuple[MaskedEventNet, np.ndarray, np.ndarray, dict[str, float]]:
    torch.manual_seed(seed)
    target_mean = train_examples.targets.mean(axis=0, keepdims=True).astype(np.float32)
    target_std = (train_examples.targets.std(axis=0, keepdims=True) + 1e-8).astype(np.float32)
    obs_spec, obs_coord, obs_mask, cand_coord, obs_frac, y = tensors_from_examples(
        train_examples,
        target_mean=target_mean,
        target_std=target_std,
        include_targets=True,
    )
    assert y is not None
    dataset = TensorDataset(obs_spec, obs_coord, obs_mask, cand_coord, obs_frac, y)
    generator = torch.Generator()
    generator.manual_seed(seed)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, generator=generator)
    model = MaskedEventNet(
        n_theta=n_theta,
        target_dim=target_dim,
        max_observed=max_observed,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    loss_fn = nn.MSELoss()
    model.train()
    for _ in range(epochs):
        for batch in loader:
            spec, coord, mask, candidate, fraction, target = [item.to(device) for item in batch]
            optimizer.zero_grad(set_to_none=True)
            prediction = model(spec, coord, mask, candidate, fraction)
            loss = loss_fn(prediction, target)
            loss.backward()
            optimizer.step()

    diagnostics = evaluate_target_prediction(
        model=model,
        train_examples=train_examples,
        test_examples=test_examples,
        target_mean=target_mean,
        target_std=target_std,
        device=device,
    )
    return model, target_mean, target_std, diagnostics


def predict_targets(
    *,
    model: MaskedEventNet,
    examples: MaskedExamples,
    target_mean: np.ndarray,
    target_std: np.ndarray,
    device: torch.device,
    batch_size: int = 1024,
) -> np.ndarray:
    model.eval()
    obs_spec, obs_coord, obs_mask, cand_coord, obs_frac, _ = tensors_from_examples(
        examples,
        target_mean=target_mean,
        target_std=target_std,
        include_targets=False,
    )
    dataset = TensorDataset(obs_spec, obs_coord, obs_mask, cand_coord, obs_frac)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    predictions = []
    with torch.no_grad():
        for batch in loader:
            spec, coord, mask, candidate, fraction = [item.to(device) for item in batch]
            pred = model(spec, coord, mask, candidate, fraction).cpu().numpy()
            predictions.append(pred)
    return np.concatenate(predictions, axis=0) * target_std + target_mean


def evaluate_target_prediction(
    *,
    model: MaskedEventNet,
    train_examples: MaskedExamples,
    test_examples: MaskedExamples,
    target_mean: np.ndarray,
    target_std: np.ndarray,
    device: torch.device,
) -> dict[str, float]:
    predictions = predict_targets(
        model=model,
        examples=test_examples,
        target_mean=target_mean,
        target_std=target_std,
        device=device,
    )
    baseline = np.tile(
        train_examples.targets.mean(axis=0, keepdims=True),
        (len(test_examples.targets), 1),
    )
    baseline_mse = float(np.mean((test_examples.targets - baseline) ** 2))
    model_mse = float(np.mean((test_examples.targets - predictions) ** 2))
    return {
        "target_baseline_mse": baseline_mse,
        "target_model_mse": model_mse,
        "target_mse_improvement": 1.0 - (model_mse / baseline_mse),
    }


def single_state_examples(
    *,
    coords: np.ndarray,
    spectra: np.ndarray,
    observed: list[int],
    candidates: list[int],
    pca_model: PCA,
    max_observed: int,
    target_mode: str,
) -> MaskedExamples:
    observed_spectra_rows = []
    observed_coord_rows = []
    observed_mask_rows = []
    candidate_coord_rows = []
    observed_fraction_rows = []
    targets = []
    for candidate in candidates:
        obs_spectra, obs_coords, obs_mask, cand_coord, obs_fraction = make_masked_arrays(
            coords=coords,
            spectra=spectra,
            observed=observed,
            candidate=candidate,
            max_observed=max_observed,
        )
        observed_spectra_rows.append(obs_spectra)
        observed_coord_rows.append(obs_coords)
        observed_mask_rows.append(obs_mask)
        candidate_coord_rows.append(cand_coord)
        observed_fraction_rows.append(obs_fraction)
        target_signal = target_signal_for_candidate(
            coords=coords,
            spectra=spectra,
            observed=observed,
            candidate=candidate,
            target_mode=target_mode,
        )
        targets.append(pca_model.transform(target_signal.reshape(1, -1))[0])
    return MaskedExamples(
        observed_spectra=np.asarray(observed_spectra_rows, dtype=np.float32),
        observed_coords=np.asarray(observed_coord_rows, dtype=np.float32),
        observed_mask=np.asarray(observed_mask_rows, dtype=bool),
        candidate_coords=np.asarray(candidate_coord_rows, dtype=np.float32),
        observed_fraction=np.asarray(observed_fraction_rows, dtype=np.float32),
        targets=np.asarray(targets, dtype=np.float32),
        groups=np.asarray(["eval"] * len(candidates)),
    )


def event_rows_for_prediction(
    *,
    heldout_regime: str,
    seed: int,
    event_id: str,
    observed_count: int,
    mask_strategy: str,
    repeat: int,
    truth: np.ndarray,
    predictions: dict[str, np.ndarray],
    train_mean_prediction: np.ndarray,
    event_mean_prediction: np.ndarray,
) -> list[dict[str, Any]]:
    train_mean_mse = mean_squared_error(truth, train_mean_prediction)
    event_mean_mse = mean_squared_error(truth, event_mean_prediction)
    rows = []
    for model_name, prediction in predictions.items():
        mse = mean_squared_error(truth, prediction)
        mae = float(np.mean(np.abs(truth - prediction)))
        rows.append(
            {
                "heldout_regime": heldout_regime,
                "seed": seed,
                "event_id": event_id,
                "observed_count": observed_count,
                "mask_strategy": mask_strategy,
                "repeat": repeat,
                "model": model_name,
                "mse": mse,
                "mae": mae,
                "train_mean_mse": train_mean_mse,
                "event_mean_mse": event_mean_mse,
                "improvement_vs_train_mean": 1.0 - (mse / train_mean_mse),
                "improvement_vs_event_mean": 1.0 - (mse / event_mean_mse),
            }
        )
    return rows


def predict_with_masked_models(
    *,
    model_bundles: dict[str, dict[str, Any]],
    device: torch.device,
) -> dict[str, np.ndarray]:
    predictions = {}
    for variant, bundle in model_bundles.items():
        examples = ablate_examples(bundle["examples"], variant=variant)
        pca_prediction = predict_targets(
            model=bundle["model"],
            examples=examples,
            target_mean=bundle["target_mean"],
            target_std=bundle["target_std"],
            device=device,
        )
        predicted_signal = bundle["pca_model"].inverse_transform(pca_prediction)
        if bundle["target_mode"] == "spectrum":
            prediction = predicted_signal
        elif bundle["target_mode"] == "idw_residual":
            prediction = bundle["idw_prediction"] + predicted_signal
        else:
            raise ValueError(f"unknown target mode: {bundle['target_mode']}")
        predictions[f"masked_event_{variant}"] = prediction
    return predictions


def evaluate_missing_measurement_models(
    *,
    heldout_regime: str,
    seed: int,
    model_bundles: dict[str, dict[str, Any]],
    rf_model: Any,
    pca_model: PCA,
    train_mean_spectrum: np.ndarray,
    event_ids: np.ndarray,
    coords: np.ndarray,
    spectra: np.ndarray,
    test_event_ids: set[str],
    observed_counts: list[int],
    random_repeats: int,
    max_observed: int,
    device: torch.device,
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    rows = []
    for event_id in sorted(test_event_ids):
        event_idx = np.flatnonzero(event_ids == event_id)
        event_coords = coords[event_idx]
        event_spectra = spectra[event_idx]
        for observed_count in observed_counts:
            modes = [("space_filling", 0), *[("random", repeat) for repeat in range(random_repeats)]]
            for mode, repeat in modes:
                observed = observed_indices_for_state(
                    coords=event_coords,
                    count=observed_count,
                    mode=mode,
                    rng=rng,
                )
                candidates = [idx for idx in range(len(event_idx)) if idx not in observed]
                if not candidates:
                    continue
                observed_arr = np.asarray(observed, dtype=int)
                candidate_arr = np.asarray(candidates, dtype=int)
                truth = event_spectra[candidate_arr]
                train_mean_prediction = np.tile(train_mean_spectrum, (len(candidates), 1))
                event_mean = event_spectra[observed_arr].mean(axis=0)
                event_mean_prediction = np.tile(event_mean, (len(candidates), 1))

                distances = np.linalg.norm(
                    event_coords[candidate_arr, None, :] - event_coords[observed_arr][None, :, :],
                    axis=2,
                )
                nearest_prediction = event_spectra[observed_arr[np.argmin(distances, axis=1)]]
                idw_prediction = inverse_distance_prediction(
                    event_coords[observed_arr],
                    event_spectra[observed_arr],
                    event_coords[candidate_arr],
                )
                predictions = {
                    "train_mean": train_mean_prediction,
                    "event_mean": event_mean_prediction,
                    "nearest_neighbor": nearest_prediction,
                    "idw_all": idw_prediction,
                }
                ridge_prediction = coordinate_ridge_prediction(
                    event_coords[observed_arr],
                    event_spectra[observed_arr],
                    event_coords[candidate_arr],
                )
                if ridge_prediction is not None:
                    predictions["coordinate_ridge"] = ridge_prediction

                rf_features = np.asarray(
                    [
                        EVENT_FIELD.field_features_for_candidate(
                            coords=event_coords,
                            spectra=event_spectra,
                            observed=observed,
                            candidate=candidate,
                            pca_model=pca_model,
                            max_observed=max_observed,
                        )
                        for candidate in candidates
                    ],
                    dtype=np.float32,
                )
                rf_pca_prediction = rf_model.predict(rf_features)
                predictions["rf_event_field"] = pca_model.inverse_transform(rf_pca_prediction)

                state_bundles = {}
                for variant, bundle in model_bundles.items():
                    target_mode = bundle["target_mode"]
                    state_bundles[variant] = {
                        **bundle,
                        "examples": single_state_examples(
                            coords=event_coords,
                            spectra=event_spectra,
                            observed=observed,
                            candidates=candidates,
                            pca_model=bundle["pca_model"],
                            max_observed=max_observed,
                            target_mode=target_mode,
                        ),
                        "idw_prediction": idw_prediction,
                    }
                predictions.update(
                    predict_with_masked_models(
                        model_bundles=state_bundles,
                        device=device,
                    )
                )
                rows.extend(
                    event_rows_for_prediction(
                        heldout_regime=heldout_regime,
                        seed=seed,
                        event_id=event_id,
                        observed_count=observed_count,
                        mask_strategy=mode,
                        repeat=repeat,
                        truth=truth,
                        predictions=predictions,
                        train_mean_prediction=train_mean_prediction,
                        event_mean_prediction=event_mean_prediction,
                    )
                )
    return rows


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    summary = []
    for (heldout_regime, observed_count, mask_strategy, model), group in df.groupby(
        ["heldout_regime", "observed_count", "mask_strategy", "model"],
        sort=True,
    ):
        summary.append(
            {
                "heldout_regime": heldout_regime,
                "observed_count": int(observed_count),
                "mask_strategy": mask_strategy,
                "model": model,
                "event_count": int(len(group)),
                "mse_mean": float(group["mse"].mean()),
                "mae_mean": float(group["mae"].mean()),
                "improvement_vs_train_mean_mean": float(
                    group["improvement_vs_train_mean"].mean()
                ),
                "improvement_vs_event_mean_mean": float(
                    group["improvement_vs_event_mean"].mean()
                ),
            }
        )
    return summary


def summarize_diagnostics(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(diagnostics)
    rows = []
    for (heldout_regime, variant), group in df.groupby(["heldout_regime", "variant"], sort=True):
        rows.append(
            {
                "heldout_regime": heldout_regime,
                "variant": variant,
                "seed_count": int(len(group)),
                "target_mse_improvement_mean": float(group["target_mse_improvement"].mean()),
                "target_mse_improvement_min": float(group["target_mse_improvement"].min()),
                "target_mse_improvement_max": float(group["target_mse_improvement"].max()),
            }
        )
    return rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    device = NEURAL.select_device(args.device)
    seeds = NEURAL.DEFAULT_SEEDS[: args.seed_count]
    max_observed = max(args.observed_counts)
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
            spectrum_pca = PCA(n_components=pca_components, random_state=seed)
            spectrum_pca.fit(train_field.spectra)
            residual_signals = collect_target_signals(
                event_ids=train_field.event_ids,
                coords=train_field.coords,
                spectra=train_field.spectra,
                selected_event_ids=train_events,
                observed_counts=args.observed_counts,
                seed=seed,
                random_repeats=args.train_random_repeats,
                target_mode="idw_residual",
            )
            residual_pca = PCA(n_components=pca_components, random_state=seed)
            residual_pca.fit(residual_signals)
            pca_by_target_mode = {
                "spectrum": spectrum_pca,
                "idw_residual": residual_pca,
            }
            rf_features, rf_targets, _ = EVENT_FIELD.build_field_examples(
                event_ids=train_field.event_ids,
                coords=train_field.coords,
                spectra=train_field.spectra,
                selected_event_ids=train_events,
                pca_model=spectrum_pca,
                observed_counts=args.observed_counts,
                max_observed=max_observed,
                seed=seed,
                random_repeats=args.train_random_repeats,
            )
            rf_model = EVENT_FIELD.train_field_model(rf_features, rf_targets, seed=seed)

            test_field = TRANSFER.generate_transfer_event_field(
                n_events=args.test_events,
                observations_per_event=args.observations_per_event,
                n_theta=args.theta_points,
                seed=seed + args.test_seed_offset,
                transfer_regime=heldout_regime,
            )
            test_events = TRANSFER.unique_event_ids(test_field)

            model_bundles = {}
            for variant in args.variants:
                target_mode = variant_target_mode(variant)
                variant_pca = pca_by_target_mode[target_mode]
                base_train_examples = build_masked_examples(
                    event_ids=train_field.event_ids,
                    coords=train_field.coords,
                    spectra=train_field.spectra,
                    selected_event_ids=train_events,
                    pca_model=variant_pca,
                    observed_counts=args.observed_counts,
                    max_observed=max_observed,
                    seed=seed,
                    random_repeats=args.train_random_repeats,
                    target_mode=target_mode,
                )
                base_test_examples = build_masked_examples(
                    event_ids=test_field.event_ids,
                    coords=test_field.coords,
                    spectra=test_field.spectra,
                    selected_event_ids=test_events,
                    pca_model=variant_pca,
                    observed_counts=args.observed_counts,
                    max_observed=max_observed,
                    seed=seed + args.test_seed_offset,
                    random_repeats=1,
                    target_mode=target_mode,
                )
                train_examples = ablate_examples(base_train_examples, variant=variant)
                test_examples = ablate_examples(base_test_examples, variant=variant)
                model, target_mean, target_std, target_diag = train_masked_model(
                    train_examples=train_examples,
                    test_examples=test_examples,
                    n_theta=args.theta_points,
                    target_dim=pca_components,
                    max_observed=max_observed,
                    seed=seed,
                    device=device,
                    epochs=args.epochs,
                    batch_size=args.batch_size,
                    learning_rate=args.learning_rate,
                )
                model_bundles[variant] = {
                    "model": model,
                    "target_mean": target_mean,
                    "target_std": target_std,
                    "pca_model": variant_pca,
                    "target_mode": target_mode,
                }
                diagnostics.append(
                    {
                        "seed": seed,
                        "heldout_regime": heldout_regime,
                        "train_regimes": train_regimes,
                        "variant": variant,
                        "device": str(device),
                        "train_events": len(train_events),
                        "test_events": len(test_events),
                        "training_examples": int(len(train_examples.targets)),
                        "test_examples": int(len(test_examples.targets)),
                        **target_diag,
                    }
                )

            rows.extend(
                evaluate_missing_measurement_models(
                    heldout_regime=heldout_regime,
                    seed=seed,
                    model_bundles=model_bundles,
                    rf_model=rf_model,
                    pca_model=spectrum_pca,
                    train_mean_spectrum=train_field.spectra.mean(axis=0),
                    event_ids=test_field.event_ids,
                    coords=test_field.coords,
                    spectra=test_field.spectra,
                    test_event_ids=test_events,
                    observed_counts=args.observed_counts,
                    random_repeats=args.eval_random_repeats,
                    max_observed=max_observed,
                    device=device,
                )
            )

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "track_b_masked_event_model",
        "regime_pool": args.regime_pool,
        "heldout_regimes": args.heldout_regimes,
        "train_events_per_regime": args.train_events_per_regime,
        "test_events": args.test_events,
        "observations_per_event": args.observations_per_event,
        "observed_counts": args.observed_counts,
        "train_random_repeats": args.train_random_repeats,
        "eval_random_repeats": args.eval_random_repeats,
        "seeds": seeds,
        "device": str(device),
        "architecture": {
            "model": "MaskedEventNet",
            "objective": "predict PCA-compressed missing raw measurements from partial events",
            "event_encoder": "TransformerEncoder over observed measurement tokens plus candidate token",
            "variants": {
                "raw_set": "observed coordinates and observed raw spectra",
                "coord_only": "observed coordinates only; spectra zeroed as shortcut control",
                "raw_residual": "predict IDW residuals from observed coordinates and raw spectra",
            },
            "epochs": args.epochs,
        },
        "hypotheses": [
            "A masked event model should predict missing raw measurement embeddings better than train-mean PCA.",
            "The raw-set variant should beat coord-only if observed spectra add event-specific signal.",
            "The raw-residual variant should beat raw-set if the useful target is what interpolation cannot already explain.",
            "On full-spectrum missing-measurement reconstruction, the masked model should be competitive with IDW and the engineered random-forest event-field baseline.",
            "If the neural masked model only beats train mean but loses to simple within-event interpolation, the next move should be data/objective design rather than architecture tuning.",
        ],
        "direction_critique": [
            "This is the right next step because the previous event-field run found representation signal but weak uncertainty-to-action conversion.",
            "It avoids hand-written relation graphs by making relations internal to the set encoder and judging only raw missing-measurement prediction.",
            "It avoids leaderboard drift because the main question is whether partial event context predicts unseen event measurements under held-out regime shift.",
            "If it cannot beat strong within-event baselines, we should stop polishing synthetic acquisition heuristics and move toward real event data collection or richer event objectives.",
        ],
        "diagnostics": diagnostics,
        "diagnostic_summary": summarize_diagnostics(diagnostics),
        "rows": rows,
        "summary": summarize_rows(rows),
        "caveats": [
            "This is synthetic and uses PCA-compressed spectra as the neural target.",
            "IDW is a strong baseline when event fields are spatially smooth.",
            "A win here is evidence for event-native objective design, not evidence that current synthetic taxonomies map to chemistry.",
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
    parser.add_argument("--train-events-per-regime", type=int, default=24)
    parser.add_argument("--test-events", type=int, default=32)
    parser.add_argument("--observations-per-event", type=int, default=12)
    parser.add_argument("--theta-points", type=int, default=512)
    parser.add_argument("--observed-counts", type=int, nargs="+", default=DEFAULT_OBSERVED_COUNTS)
    parser.add_argument("--pca-components", type=int, default=8)
    parser.add_argument("--seed-count", type=int, default=2)
    parser.add_argument("--train-random-repeats", type=int, default=2)
    parser.add_argument("--eval-random-repeats", type=int, default=2)
    parser.add_argument("--variants", nargs="+", default=DEFAULT_VARIANTS)
    parser.add_argument("--epochs", type=int, default=35)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--test-seed-offset", type=int, default=10000)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/track_b_masked_event_model.json"),
    )
    return parser.parse_args()


def main() -> None:
    result = run(parse_args())
    printable = {
        "task": result["task"],
        "device": result["device"],
        "hypotheses": result["hypotheses"],
        "direction_critique": result["direction_critique"],
        "diagnostic_summary": result["diagnostic_summary"],
        "summary": result["summary"],
        "caveats": result["caveats"],
    }
    print(json.dumps(printable, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
