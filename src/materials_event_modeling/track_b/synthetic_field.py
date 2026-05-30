"""Synthetic event-field generator for Track B partial-observation tests."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from materials_event_modeling.track_b.synthetic import REGIMES, regime_basis


@dataclass(frozen=True)
class SyntheticEventField:
    event_ids: np.ndarray
    coords: np.ndarray
    spectra: np.ndarray
    theta: np.ndarray
    table: pd.DataFrame


def observation_grid(count: int) -> np.ndarray:
    x_count = int(np.ceil(np.sqrt(count)))
    y_count = int(np.ceil(count / x_count))
    xs = np.linspace(0.0, 1.0, x_count)
    ys = np.linspace(0.0, 1.0, y_count)
    coords = np.array([(x, y) for y in ys for x in xs], dtype=np.float32)
    return coords[:count]


def shifted_pattern(theta: np.ndarray, pattern: np.ndarray, shift: float) -> np.ndarray:
    shifted_theta = theta - shift
    return np.interp(theta, shifted_theta, pattern, left=0.0, right=0.0)


def generate_synthetic_event_field(
    *,
    n_events: int,
    observations_per_event: int,
    n_theta: int,
    seed: int,
) -> SyntheticEventField:
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
        event_id = f"synthetic_field_event_{event_idx:03d}"
        regime = REGIMES[event_idx % len(REGIMES)]
        base_pattern = bases[regime]
        transition_center = 0.25 + 0.08 * (event_idx % 5) + float(rng.normal(0.0, 0.015))
        field_shift = float(rng.normal(0.0, 0.02))
        field_background = float(rng.uniform(0.02, 0.07))

        for observation_idx, coord in enumerate(coords_template):
            time_fraction = float(coord[0])
            micro_position = float(coord[1])
            conversion = 1.0 / (1.0 + np.exp(-9.0 * (time_fraction - transition_center)))
            local_shift = field_shift + 0.07 * (micro_position - 0.5)
            local_pattern = shifted_pattern(theta, base_pattern, local_shift)
            precursor_like = shifted_pattern(theta, low_signal, -0.02 * micro_position)
            amplitude = 0.25 + 0.75 * conversion + 0.08 * np.sin(
                2.0 * np.pi * micro_position + event_idx
            )
            background = field_background + 0.025 * np.sin(theta / 7.5 + micro_position) ** 2
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
                    "hidden_regime": regime,
                    "time_fraction": time_fraction,
                    "micro_position": micro_position,
                    "transition_center": transition_center,
                }
            )

    return SyntheticEventField(
        event_ids=np.array(event_ids),
        coords=np.vstack(coords).astype(np.float32),
        spectra=np.vstack(spectra).astype(np.float32),
        theta=theta,
        table=pd.DataFrame(rows),
    )

